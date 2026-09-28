"""Referral tracking: contacts lookup order, the ask/result log, board updates via a fake gh, reminders."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import board_sync as bs  # noqa: E402
import referrals as rf  # noqa: E402


def write_network(rows):
    rf.NETWORK.write_text("name,relation,company,role,how_to_reach,notes,added\n" + "\n".join(rows) + "\n",
                          encoding="utf-8")


def test_contacts_match_company_loosely_and_follow_the_users_order():
    write_network(["Ravi,recruiter,Amazon UK Services Ltd,Tech recruiter,,,",
                   "Priya,friend_family,Amazon,SDE,WhatsApp,,",
                   "Tom,connection,amazon,AppSec,,,",
                   "Ana,friend_family,Monzo,,,,"])
    assert [c["name"] for c in rf.contacts("Amazon")] == ["Priya", "Tom", "Ravi"]


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
    rf.ask("a" * 16, "Priya", "friend_family", channel="WhatsApp")
    rf.result("a" * 16, "Priya", "referred", note="Submitted via internal portal.")
    assert seen[0] == ({"Referral": "Asked"}, "Referral: asked Priya (friend/family) via WhatsApp.")
    assert seen[1][0] == {"Referral": "Referred"} and "Priya referred you. Submitted" in seen[1][1]
    rf.ask("a" * 16, "Tom", "connection")  # already referred: the Referral field is left as Referred
    assert len(seen) == 2
    log = [json.loads(line) for line in rf.LOG.read_text(encoding="utf-8").splitlines()]
    assert [r["status"] for r in log] == ["asked", "referred", "asked"]


def test_pending_lists_unanswered_asks_after_wait():
    now = datetime(2026, 10, 5, tzinfo=timezone.utc)
    old = (now - timedelta(days=5)).isoformat()
    rf.LOG.write_text("\n".join(json.dumps(r) for r in [
        {"ref": "r1", "person": "Priya", "relation": "friend_family", "status": "asked", "at": old},
        {"ref": "r1", "person": "Tom", "relation": "connection", "status": "asked", "at": old},
        {"ref": "r1", "person": "Tom", "status": "declined", "at": now.isoformat()},
        {"ref": "r2", "person": "Ravi", "relation": "recruiter", "status": "asked", "at": now.isoformat()}]) + "\n",
        encoding="utf-8")
    assert [(r["ref"], r["person"], r["days"]) for r in rf.pending(4, now)] == [("r1", "Priya", 5)]
