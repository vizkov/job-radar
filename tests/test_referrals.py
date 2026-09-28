"""Referral tracking: contacts lookup order, the ask/result log, board updates via a fake gh, reminders."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import board_sync as bs  # noqa: E402
import referrals as rf  # noqa: E402


def write_network(rows):
    rf.NETWORK.write_text("name,company,added\n" + "\n".join(rows) + "\n", encoding="utf-8")


def test_contacts_match_company_loosely_in_the_order_given():
    write_network(["Priya,Amazon UK Services Ltd,2026-09-28", "Tom,amazon,2026-09-28", "Ana,Monzo,2026-09-28"])
    assert [c["name"] for c in rf.contacts("Amazon")] == ["Priya", "Tom"]


class FakeGh:
    dry_run = False

    def __init__(self):
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        return ""


def test_ask_and_result_update_board_and_log(monkeypatch):
    seen = []
    monkeypatch.setattr(bs, "set_role_fields", lambda gh, ref, values, note="": seen.append((values, note)) or "ok")
    rf.ask("a" * 16, "Priya", channel="WhatsApp")                      # someone the user knows
    rf.ask("b" * 16, "Ravi", relation="recruiter")                     # a stranger
    rf.result("a" * 16, "Priya", "referred", note="Submitted via internal portal.")
    assert seen[0] == ({"Referral": "Asked"}, "Referral: asked Priya via WhatsApp.")
    assert seen[1] == ({"Referral": "Asked"}, "Referral: asked Ravi (recruiter).")
    assert seen[2][0] == {"Referral": "Referred"} and "Priya referred you. Submitted" in seen[2][1]
    rf.ask("a" * 16, "Tom")  # already referred: the Referral field is left as Referred
    assert len(seen) == 3
    log = [json.loads(line) for line in rf.LOG.read_text(encoding="utf-8").splitlines()]
    assert [r["status"] for r in log] == ["asked", "asked", "referred", "asked"]


def test_pending_lists_unanswered_asks_after_wait():
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    old = (now - timedelta(days=5)).isoformat()
    rf.LOG.write_text("\n".join(json.dumps(r) for r in [
        {"ref": "r1", "person": "Priya", "status": "asked", "at": old},
        {"ref": "r1", "person": "Tom", "status": "asked", "at": old},
        {"ref": "r1", "person": "Tom", "status": "declined", "at": now.isoformat()},
        {"ref": "r2", "person": "Ravi", "status": "asked", "at": now.isoformat()}]) + "\n",
        encoding="utf-8")
    assert [(r["ref"], r["person"], r["days"]) for r in rf.pending(4, now)] == [("r1", "Priya", 5)]
