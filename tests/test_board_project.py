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

    def __init__(self, fields=None, items=None, projects=None):
        self.calls = []
        self.projects = projects or []
        self.fields = fields if fields is not None else []
        self.items = items or []

    def __call__(self, *args):
        self.calls.append(args)
        if args[:2] == ("api", "user"):
            return "me"
        if args[:2] == ("project", "list"):
            return json.dumps({"projects": self.projects})
        if args[:2] == ("project", "copy"):
            return json.dumps({"number": 9, "id": "PVT_9", "url": "https://github.com/users/me/projects/9"})
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
    assert ("project", "link", "3", "--owner", "me", "--repo", "my-job-radar") in gh.calls  # @me resolved
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


def test_skip_recommendation_moves_untouched_cards_to_skipped_but_not_users_cards(board_file):
    gh, _ = setup(board_file)
    for stage, moved in ((None, True), ("New", True), ("Shortlisted", False), ("Applied", False)):
        gh.items, gh.calls, gh._items_cache = [item(stage=stage)], [], None   # a fresh process: nothing cached
        msg = bs.set_role_fields(gh, REF, {"Fit": "20", "Recommendation": "Skip"})
        opts = [c[-1] for c in gh.calls if c[:2] == ("project", "item-edit") and c[-2] == "--single-select-option-id"]
        assert ("O_Stage_Skipped" in opts) is moved, stage
        assert (("issue", "close", "https://github.com/me/r/issues/7") in gh.calls) is moved
        assert ("(closed)" in msg) is moved
    gh.items, gh.calls, gh._items_cache = [item(stage="New")], [], None
    bs.set_role_fields(gh, REF, {"Recommendation": "Apply"})                      # only Skip moves a card
    assert not any(c[:3] == ("issue", "close", "https://github.com/me/r/issues/7") for c in gh.calls)


def test_board_is_read_once_per_session_and_cache_stays_in_step(board_file):
    gh, _ = setup(board_file)
    REF2 = "b" * 16
    second = item()
    second["id"], second["content"] = "PVTI_2", {"type": "Issue", "url": "https://github.com/me/r/issues/8",
                                                   "body": f"... <!-- job-radar:ref={REF2} -->"}
    gh.items, gh.calls = [item(), second], []
    for ref in (REF, REF2, REF):                      # three updates, two cards
        bs.set_role_fields(gh, ref, {"Sponsor": "Likely"})
    assert sum(1 for c in gh.calls if c[:2] == ("project", "item-list")) == 1
    # a Skip recommendation moves card 1 to Skipped; the cache knows, so archive (same session) sees it, no re-read
    bs.set_role_fields(gh, REF, {"Recommendation": "Skip"})
    assert bs.archive_skipped(gh, sleep=lambda s: None) == "archived 1 Skipped card(s)"
    assert [c[-1] for c in gh.calls if c[:2] == ("project", "item-archive")] == ["PVTI_9"]
    assert sum(1 for c in gh.calls if c[:2] == ("project", "item-list")) == 1
    bs._items(gh, bs.load_board(), refresh=True)      # an explicit refresh does re-read
    assert sum(1 for c in gh.calls if c[:2] == ("project", "item-list")) == 2


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
    assert bs.fill_new(gh).startswith("filled 1 new cards")
    opts = [c[-1] for c in gh.calls if c[:2] == ("project", "item-edit") and "--date" not in c]
    assert opts == ["O_Stage_New", "O_Tier_T1", "O_Sponsor_Licensed"]  # register match = Licensed, not "Yes"


def test_fill_reads_tier_and_sponsor_from_matches_csv_not_labels(board_file, tmp_path, monkeypatch):
    gh, _ = setup(board_file)
    csv_path = tmp_path / "matches.csv"
    csv_path.write_text(f"ref,countries,tier,uk_sponsor,nl_sponsor\n{REF},NL,2,,no (not on register)\n", encoding="utf-8")
    monkeypatch.setattr(bs, "MATCHES", csv_path)
    gh.items = [item(labels=("role",))]   # the Action now attaches only `role`
    assert bs.fill_new(gh).startswith("filled 1 new cards")
    opts = [c[-1] for c in gh.calls if c[:2] == ("project", "item-edit") and "--date" not in c]
    assert opts == ["O_Stage_New", "O_Tier_T2", "O_Sponsor_Unlikely"]


def test_archive_archives_only_skipped_and_respects_cap(board_file):
    gh, _ = setup(board_file)
    def skipped(n):
        i = item(stage="Skipped")
        i["id"] = f"PVTI_{n}"
        return i
    gh.items = [item(), item(stage="Applied"), skipped(1), skipped(2), skipped(3)]
    msg = bs.archive_skipped(gh, max_n=2, sleep=lambda s: None)
    archived = [c for c in gh.calls if c[:2] == ("project", "item-archive")]
    assert [c[-1] for c in archived] == ["PVTI_1", "PVTI_2"]          # not New/Applied cards, capped at 2
    assert archived[0][:5] == ("project", "item-archive", "3", "--owner", "me")
    assert msg == "archived 2 Skipped card(s), 1 left for the next run"


def test_archive_with_nothing_skipped_or_no_board(board_file):
    gh, _ = setup(board_file)
    gh.items = [item(), item(stage="Interview")]
    assert bs.archive_skipped(gh, sleep=lambda s: None) == "archived 0 Skipped card(s)"
    assert not any(c[:2] == ("project", "item-archive") for c in gh.calls)
    board_file.unlink()
    assert "not set up" in bs.archive_skipped(FakeProjectGh())


def test_existing_project_is_adopted_not_duplicated(board_file):
    gh = FakeProjectGh(projects=[{"number": 2, "id": "PVT_2", "title": "Job search", "closed": False,
                                  "url": "https://github.com/users/me/projects/2"}])
    bs.setup_project(gh, "me/my-job-radar")
    assert not any(c[:2] == ("project", "create") for c in gh.calls)
    assert json.loads(board_file.read_text())["number"] == "2"


def test_board_saved_even_if_link_fails(board_file):
    class LinkFails(FakeProjectGh):
        def __call__(self, *args):
            if args[:2] == ("project", "link"):
                raise RuntimeError("link failed")
            return super().__call__(*args)
    with pytest.raises(RuntimeError):
        bs.setup_project(LinkFails(), "me/my-job-radar")
    assert json.loads(board_file.read_text())["number"] == "3"   # re-run won't create a second project


def test_repo_of_another_owner_rejected(board_file):
    with pytest.raises(ValueError, match="isn't owned"):
        bs.setup_project(FakeProjectGh(), "someoneelse/repo")


def test_posted_date_from_body_else_first_seen():
    assert bs.posted_date("x\n- Posted: 2026-09-20\ny", {}) == "2026-09-20"
    body = f"no date\n<!-- job-radar:ref={REF} -->"
    assert bs.posted_date(body, {REF: "2026-09-25"}) == "2026-09-25"
    assert bs.posted_date(body, {}) is None


def test_fill_dates_every_undated_role_card(board_file):
    gh, _ = setup(board_file)
    dated = item(stage="Applied")
    dated["content"]["body"] = "- Posted: 2026-09-21\n" + dated["content"]["body"]
    gh.items = [dated, {**item(stage="New"), "posted": "2026-09-01"}]
    assert bs.fill_new(gh).endswith("dated 1")
    dates = [c for c in gh.calls if c[:2] == ("project", "item-edit") and "--date" in c]
    assert len(dates) == 1 and dates[0][-1] == "2026-09-21"


def test_note_is_logged_and_commented_on_the_issue(board_file):
    gh, _ = setup(board_file)
    gh.items = [item()]
    msg = bs.set_role_fields(gh, REF, {"Stage": "Skipped"}, note="No live way to apply.")
    comments = [c for c in gh.calls if c[:2] == ("issue", "comment")]
    assert len(comments) == 1 and comments[0][2] == "https://github.com/me/r/issues/7"
    assert ("issue", "close", "https://github.com/me/r/issues/7") in gh.calls and "(closed)" in msg
    logged = [json.loads(l) for l in bs.PIPELINE_LOG.read_text(encoding="utf-8").splitlines()]
    assert logged[-1]["note"] == "No live way to apply." and logged[-1]["value"] == "Skipped"


SCORE = {"key": REF, "fit_score": 78, "recommendation": "apply", "summary": "Strong [match](http://x).",
         "must_haves": [{"requirement": "Web testing", "met": "yes", "evidence": ["B01"]},
                        {"requirement": "Vendor management", "met": "partial", "evidence": ["B07"]},
                        {"requirement": "Network testing", "met": "no", "evidence": []}],
         "blockers": [{"type": "language", "quote": "Fluent German required"}], "injection_suspected": False}


def test_fit_section_groups_requirements_and_escapes_text():
    s = bs.fit_section({**SCORE, "must_haves": SCORE["must_haves"] + [
        {"requirement": "Use [a link](http://x)", "met": "yes", "evidence": ["B02"]}]}, "2026-09-28")
    assert "**Matches**\n- Web testing" in s and "**Partly**\n- Vendor management" in s
    assert "**Doesn't match**\n- Language: \"Fluent German required\"\n- Network testing" in s
    assert r"\[a link\]" in s and "### Fit" not in s and "percentage" not in s and "Strong" not in s


def test_with_fit_inserts_once_replaces_later_and_drops_tier_line():
    body = "**Acme**\n\n- **Tier 1** (score 8: title+4 country+2)\n- Found on: ats\n\nRole ID: `x`\n<!-- m -->"
    once = bs.with_fit(body, bs.fit_section(SCORE))
    assert "Tier 1" not in once and once.index("**Matches**") < once.index("Role ID:")
    twice = bs.with_fit(once, bs.fit_section({**SCORE, "must_haves": SCORE["must_haves"][:1]}))
    assert twice.count(bs.FIT_START) == 1 and "Network testing" not in twice


def test_gh_reads_utf8_not_the_windows_default(monkeypatch):
    seen = {}

    class R:
        stdout = "Amazon — GBR"

    def fake_run(cmd, **kw):
        seen.update(kw)
        return R()
    monkeypatch.setattr(bs.subprocess, "run", fake_run)
    assert bs.Gh()("issue", "view", "1") == "Amazon — GBR" and seen["encoding"] == "utf-8"
