import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import auto_reject as ar  # noqa: E402
import board_sync  # noqa: E402
from jobradar import application_mail as am  # noqa: E402

TODAY = date(2026, 11, 27)
A, B = "a" * 16, "b" * 16


def make(tmp_path, days=15, log=(), mail=(), checked=None, holds=None):
    for d in ("data", "state", "profile/applications/x"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / "profile" / "config.json").write_text(json.dumps({"board": {"auto_reject_days": days}}))
    (tmp_path / "data" / "pipeline_log.jsonl").write_text(
        "".join(json.dumps({"ref": r, "field": "Stage", "value": v, "by": by, "at": at}) + "\n" for r, v, by, at in log))
    (tmp_path / "state" / "application_mail.jsonl").write_text("".join(json.dumps(m) + "\n" for m in mail))
    (tmp_path / "state" / "inbox_checked.json").write_text(json.dumps(checked or {}))
    (tmp_path / ar.HOLDS).write_text(json.dumps(holds or {}))
    (tmp_path / "profile" / "applications" / "x" / "tailored.json").write_text(json.dumps({"key": A}))
    return tmp_path


def card(ref, stage="Applied"):
    return {"title": f"Acme {ref[0]}", "stage": stage, "content": {"body": f"<!-- job-radar:ref={ref} -->"}}


APPLIED = [(A, "Applied", "claude", "2026-11-01T10:00:00")]


def refs(result, bucket):
    return [r["ref"] for r in result[bucket]]


def test_due_only_after_the_limit_and_a_mail_search_since_the_deadline(tmp_path):
    root = make(tmp_path, log=APPLIED, checked={A: "2026-11-16"})
    assert refs(ar.assess(root, [card(A)], TODAY), "due") == [A]
    root = make(tmp_path, log=APPLIED, checked={A: "2026-11-15"})   # searched the day before the deadline
    assert refs(ar.assess(root, [card(A)], TODAY), "waiting") == [A]
    assert not any(ar.assess(root, [card(A)], date(2026, 11, 15)).values())


def test_off_by_default_and_only_applied_cards(tmp_path):
    root = make(tmp_path, days=0, log=APPLIED, checked={A: "2026-11-27"})
    assert not any(ar.assess(root, [card(A)], TODAY).values())
    root = make(tmp_path, log=APPLIED, checked={A: "2026-11-27"})
    assert not any(ar.assess(root, [card(A, "Interview")], TODAY).values())


def test_a_repeated_applied_entry_keeps_the_first_date_and_a_restart_resets_it(tmp_path):
    root = make(tmp_path, log=APPLIED + [(A, "Applied", "board", "2026-11-20T10:00:00")])
    assert ar.applied_since(root, A) == date(2026, 11, 1)
    root = make(tmp_path, log=APPLIED + [(A, "Rejected", "auto", "2026-11-17T10:00:00"), (A, "Applied", "board", "2026-11-20T10:00:00")])
    assert ar.applied_since(root, A) == date(2026, 11, 20)


def test_receipt_dates_a_card_with_no_log_and_no_date_is_left_alone(tmp_path):
    mail = [{"id": "1", "ref": A, "type": "receipt", "action": False, "at": "2026-11-02T09:00:00", "subject": "Thanks"}]
    root = make(tmp_path, mail=mail, checked={A: "2026-11-27", B: "2026-11-27"})
    result = ar.assess(root, [card(A), card(B)], TODAY)
    assert refs(result, "due") == [A] and refs(result, "undated") == [B]


def test_an_unhandled_reply_or_a_hold_keeps_the_card(tmp_path):
    reply = {"id": "9", "ref": A, "type": "unknown", "action": True, "at": "2026-11-10T09:00:00", "subject": "A question"}
    root = make(tmp_path, log=APPLIED, mail=[reply], checked={A: "2026-11-27"})
    assert refs(ar.assess(root, [card(A)], TODAY), "held") == [A]
    root = make(tmp_path, log=APPLIED, mail=[reply, {"ack": "9"}], checked={A: "2026-11-27"})
    assert refs(ar.assess(root, [card(A)], TODAY), "due") == [A]
    root = make(tmp_path, log=APPLIED, checked={A: "2026-11-27"}, holds={A: "recruiter phoned"})
    assert refs(ar.assess(root, [card(A)], TODAY), "held") == [A]


def test_run_moves_the_card_removes_its_folder_and_fixes_the_snapshot(tmp_path, monkeypatch):
    root = make(tmp_path, log=APPLIED, checked={A: "2026-11-27"})
    (root / "data" / "pipeline_snapshot.json").write_text(json.dumps({A: "Applied"}))
    calls = []
    monkeypatch.setattr(board_sync, "set_role_fields",
                        lambda gh, ref, values, note="", by="claude": calls.append((ref, values, by)) or f"{ref}: Stage=Rejected (closed)")
    items = [card(A)]
    result = ar.run(root, items, TODAY, gh=object())
    assert calls == [(A, {"Stage": "Rejected"}, "auto")]
    assert result["moved"][0]["folders"] == ["x"] and not (root / "profile" / "applications" / "x").exists()
    assert items[0]["stage"] == "Rejected"
    assert json.loads((root / "data" / "pipeline_snapshot.json").read_text()) == {A: "Rejected"}


def test_mail_scan_keeps_watching_an_auto_rejected_role_for_a_while(tmp_path):
    root = make(tmp_path, log=[(A, "Rejected", "auto", "2026-11-20T10:00:00"), (B, "Rejected", "claude", "2026-11-20T10:00:00"),
                               (A, "Rejected", "board", "2026-11-21T10:00:00")])
    (root / "data" / "matches.csv").write_text(f"ref,company,title\n{A},Acme,One\n{B},Beta,Two\n")
    assert [t["ref"] for t in am.targets(root, today=TODAY)] == [A]
    assert am.targets(root, today=date(2027, 3, 1)) == []
