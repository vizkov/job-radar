"""Project field commands against a fake `gh` returning gh's JSON shapes.
Not verified against live GitHub here: needs the user's login with the project scope."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import board_sync as bs  # noqa: E402

REF = "e3a8ef9df1405cdf"


class FakeProjectGh:
    dry_run = False

    def __init__(self, fields=None, items=None):
        self.calls = []
        self.fields = fields if fields is not None else []
        self.items = items or []

    def __call__(self, *args):
        self.calls.append(args)
        if args[:2] == ("project", "create"):
            return json.dumps({"number": 3, "id": "PVT_1", "url": "https://github.com/users/me/projects/3"})
        if args[:2] == ("project", "field-create"):
            name = args[args.index("--name") + 1]
            opts = args[args.index("--single-select-options") + 1].split(",") if "--single-select-options" in args else []
            self.fields.append({"id": f"F_{name}", "name": name,
                                "options": [{"id": f"O_{name}_{o}", "name": o} for o in opts]})
            return ""
        if args[:2] == ("project", "field-list"):
            return json.dumps({"fields": self.fields})
        if args[:2] == ("project", "item-list"):
            return json.dumps({"items": self.items})
        return ""


@pytest.fixture
def board_file(tmp_path, monkeypatch):
    monkeypatch.setattr(bs, "BOARD_FILE", tmp_path / "board.json")
    return tmp_path / "board.json"


def setup(board_file):
    gh = FakeProjectGh(fields=[{"id": "F_Status", "name": "Status", "options": [{"id": "o1", "name": "Todo"}]}])
    msg = bs.setup_project(gh, "me/my-job-radar")
    return gh, msg


def test_setup_creates_fields_links_repo_and_saves(board_file):
    gh, msg = setup(board_file)
    created = [c[c.index("--name") + 1] for c in gh.calls if c[:2] == ("project", "field-create")]
    assert created == list(bs.FIELDS)
    assert ("project", "link", "3", "--owner", "@me", "--repo", "me/my-job-radar") in gh.calls
    saved = json.loads(board_file.read_text())
    assert saved["number"] == "3" and saved["fields"]["Stage"]["options"]["applied"] == "O_Stage_Applied"
    assert "Auto-add to project" in msg and "label:role" in msg


def test_setup_is_idempotent(board_file):
    gh, _ = setup(board_file)
    gh2 = FakeProjectGh(fields=gh.fields)
    bs.setup_project(gh2, "me/my-job-radar")
    assert not any(c[:2] in (("project", "create"), ("project", "field-create")) for c in gh2.calls)


def item(stage=None, labels=("role", "tier-1", "sponsor-yes")):
    return {"id": "PVTI_9", "labels": list(labels), "stage": stage,
            "content": {"type": "Issue", "url": "https://github.com/me/r/issues/7",
                        "body": f"... <!-- job-radar:ref={REF} -->"}}


def test_set_fields_and_close_on_final_stage(board_file):
    gh, _ = setup(board_file)
    gh.items = [item()]
    msg = bs.set_role_fields(gh, REF, {"Stage": "Rejected", "Fit": "72"})
    edits = [c for c in gh.calls if c[:2] == ("project", "item-edit")]
    assert ("--single-select-option-id", "O_Stage_Rejected") == edits[0][-2:]
    assert edits[1][-2:] == ("--number", "72.0")
    assert ("issue", "close", "https://github.com/me/r/issues/7") in gh.calls and "Stage=Rejected" in msg


def test_bad_option_and_missing_card(board_file):
    gh, _ = setup(board_file)
    gh.items = [item()]
    with pytest.raises(ValueError, match="Stage must be one of"):
        bs.set_role_fields(gh, REF, {"Stage": "Ghosted"})
    assert "no board card" in bs.set_role_fields(gh, "0" * 16, {"Stage": "Applied"})


def test_not_set_up(board_file):
    assert "not set up" in bs.set_role_fields(FakeProjectGh(), REF, {"Stage": "Applied"})


def test_fill_sets_new_cards_only(board_file):
    gh, _ = setup(board_file)
    gh.items = [item(), item(stage="Applied"), {"id": "X", "labels": ["radar-status"], "content": {}}]
    assert bs.fill_new(gh) == "filled 1 new cards"
    opts = [c[-1] for c in gh.calls if c[:2] == ("project", "item-edit")]
    assert opts == ["O_Stage_New", "O_Tier_T1", "O_Sponsor_Yes"]
