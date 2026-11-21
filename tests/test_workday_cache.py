from datetime import datetime, timedelta, timezone

from ats_scrapers.models import Job

from jobradar import workday_cache as wc


def job():
    return Job(url="https://x.wd3.myworkdayjobs.com/s/job/L/Security-Engineer_R1", title="Security Engineer", company="X", ats_type="workday")


def test_roundtrip_and_age(tmp_path):
    e = wc.entry([job()])
    p = tmp_path / "w.json"
    p.write_text(wc.dumps({"u": e}), encoding="utf-8")
    got = wc.load(p)["u"]
    assert wc.jobs_of(got)[0].title == "Security Engineer"
    assert wc.age_days(got) < 0.01
    old = datetime.now(timezone.utc) + timedelta(days=4)
    assert 3.9 < wc.age_days(got, now=old) < 4.1


def test_missing_or_broken_file_is_empty(tmp_path):
    assert wc.load(tmp_path / "none.json") == {}
    (tmp_path / "bad.json").write_text("{nope", encoding="utf-8")
    assert wc.load(tmp_path / "bad.json") == {}
    assert wc.age_days({"fetched_at": "garbage"}) is None
    assert wc.jobs_of({"jobs": [{"title": "no url"}]}) == []
