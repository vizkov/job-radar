"""Board design drift and publish-board against a fake `gh` (GraphQL shapes as returned live)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import board_sync as bs  # noqa: E402


def view(name, fields, sort=()):
    return {"name": name, "layout": "TABLE_LAYOUT", "filter": None,
            "fields": {"nodes": [{"name": f} for f in fields]},
            "verticalGroupByFields": {"nodes": []},
            "sortByFields": {"nodes": [{"direction": d, "field": {"name": f}} for f, d in sort]}}


def project(views):
    return {"data": {"user": {"projectV2": {"views": {"nodes": views}, "fields": {"nodes": [
        {"name": "Stage", "dataType": "SINGLE_SELECT", "options": [{"name": "New"}, {"name": "Applied"}]},
        {"name": "Title", "dataType": "TITLE"}]}}}}}


class DesignGh:
    dry_run = False

    def __init__(self, designs):
        self.designs, self.calls = designs, []

    def __call__(self, *args):
        self.calls.append(args)
        if args[:2] == ("api", "graphql"):
            login = next(a for a in args if a.startswith("login=")).split("=", 1)[1]
            n = next(a for a in args if a.startswith("n=")).split("=", 1)[1]
            return json.dumps(self.designs[f"{login}/{n}"])
        if args[:2] == ("project", "copy"):
            return json.dumps({"number": 7})
        return ""


def setup(tmp_path, monkeypatch, template="me/3"):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"board": {"template": template}}, indent=2), encoding="utf-8")
    monkeypatch.setattr(bs, "profile_path", lambda name: tmp_path / name)
    bs.BOARD_FILE.write_text(json.dumps({"owner": "me", "number": "2"}), encoding="utf-8")
    return cfg


def test_same_design_no_diff(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    d = project([view("All Roles", ["Title", "Stage"])])
    assert bs.design_diff(DesignGh({"me/2": d, "me/3": d})) == []


def test_changed_view_and_new_view_reported(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    mine = project([view("All Roles", ["Title", "Stage", "Labels"], [("Fit", "DESC")]), view("Tier 2", ["Title"])])
    tmpl = project([view("All Roles", ["Title", "Stage"])])
    diffs = bs.design_diff(DesignGh({"me/2": mine, "me/3": tmpl}))
    assert "view 'All Roles' differs (fields, sort)" in diffs
    assert "view 'Tier 2' is only on your board" in diffs


def test_no_template_configured_is_silent(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch, template="")
    assert bs.design_diff(DesignGh({})) == []


def test_publish_board_copies_publishes_closes_and_rewrites_config(tmp_path, monkeypatch):
    cfg = setup(tmp_path, monkeypatch)
    examples = tmp_path / "examples_config.json"
    examples.write_text(cfg.read_text(encoding="utf-8"), encoding="utf-8")
    gh = DesignGh({})
    out = bs.publish_board(gh, examples)
    assert "me/7" in out
    for f in (cfg, examples):
        assert json.loads(f.read_text(encoding="utf-8"))["board"]["template"] == "me/7"
    assert any(c[:2] == ("project", "edit") and "PUBLIC" in c for c in gh.calls)
    assert ("project", "close", "3", "--owner", "me") in gh.calls
