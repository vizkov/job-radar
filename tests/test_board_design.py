"""Board views as code (VIEWS): drift check and apply, against a fake `gh` with live GraphQL shapes."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import board_sync as bs  # noqa: E402


def node(spec, **over):
    v = {**spec, **over}
    return {"id": f"V_{v['name']}", "name": v["name"], "layout": v["layout"], "filter": v["filter"] or None,
            "fields": {"nodes": [{"name": f} for f in v["fields"]]},
            "verticalGroupByFields": {"nodes": [{"name": g} for g in v["group"]]},
            "sortByFields": {"nodes": [{"direction": d, "field": {"name": f}} for f, d in v["sort"]]}}


class ViewsGh:
    dry_run = False

    def __init__(self, nodes):
        self.nodes, self.calls = nodes, []

    def __call__(self, *args):
        self.calls.append(args)
        if args[:2] == ("project", "field-list"):
            names = {f for v in bs.VIEWS for f in v["fields"]}
            return json.dumps({"fields": [{"id": f"F_{n}", "name": n} for n in names]})
        if args[:2] == ("api", "graphql"):
            q = args[3]
            if "createProjectV2View" in q:
                return json.dumps({"data": {"createProjectV2View": {"projectV2View": {"id": "V_new"}}}})
            if "mutation" in q:
                return "{}"
            return json.dumps({"data": {"user": {"projectV2": {"id": "P", "views": {"nodes": self.nodes}}}}})
        return ""


def board(bs_file):
    bs_file.write_text(json.dumps({"owner": "me", "number": "2", "id": "PVT_2"}), encoding="utf-8")


def test_matching_board_has_no_diff_and_nothing_to_apply():
    board(bs.BOARD_FILE)
    gh = ViewsGh([node(v) for v in bs.VIEWS])
    assert bs.design_diff(gh) == []
    assert bs.apply_views(gh) == "views already match"
    assert not any("mutation" in a for c in gh.calls for a in c)


def test_extra_user_views_are_fine_but_changed_columns_are_reported():
    board(bs.BOARD_FILE)
    all_roles = next(v for v in bs.VIEWS if v["name"] == "All Roles")
    gh = ViewsGh([node(v) for v in bs.VIEWS if v is not all_roles]
                 + [node(all_roles, fields=["Title", "Stage"]), node({**all_roles, "name": "Mine"})])
    assert bs.design_diff(gh) == ["view 'All Roles' differs (fields)"]


def test_apply_creates_missing_view_and_lists_clicks_for_sort_and_group():
    board(bs.BOARD_FILE)
    gh = ViewsGh([])
    out = bs.apply_views(gh)
    creates = [c for c in gh.calls if c[:2] == ("api", "graphql") and "createProjectV2View" in c[3]]
    assert len(creates) == len(bs.VIEWS)
    assert '"F_Fit"' in creates[0][3] and "TABLE_LAYOUT" in creates[0][3]
    assert "Sort by -> Fit (descending)" in out and "Column by -> Stage" in out
    filters = [c[3] for c in gh.calls if c[:2] == ("api", "graphql") and "updateProjectV2View" in c[3]]
    assert any("posted:<=@today-14d" in f for f in filters)


def test_column_order_is_not_drift():
    board(bs.BOARD_FILE)
    spec = bs.VIEWS[0]
    gh = ViewsGh([node(v) for v in bs.VIEWS[1:]] + [node(spec, fields=list(reversed(spec["fields"])))])
    assert bs.design_diff(gh) == []
