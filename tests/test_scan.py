"""scan_watchlist.py and the board adapters, with recorded fictional fixtures and no network."""
import argparse
import json
from datetime import date
from pathlib import Path

import pytest

from perkins import scan_watchlist as S
from perkins import tracker as T
from perkins.config import Config
from perkins.feeds import adapter, ashby, bamboohr, greenhouse, http, lever, rippling, workable, workday

FIX = Path(__file__).parent / "fixtures" / "feeds"
TODAY = date(2026, 11, 4)

GH_LIST = "https://boards-api.greenhouse.io/v1/boards/larkspuranalytics/jobs"
ASHBY_LIST = "https://api.ashbyhq.com/posting-api/job-board/alderrobotics"
LEVER_LIST = "https://api.lever.co/v0/postings/kestrelenergy?mode=json"
WORKABLE_LIST = "https://apply.workable.com/api/v1/widget/accounts/bluewatergrid"
BAMBOO_LIST = "https://pinecresthealth.bamboohr.com/careers/list"
RIPPLING_LIST = "https://ats.rippling.com/api/v2/board/bluewater-grid/jobs"
WD_LIST = "https://pinecresthealth.wd1.myworkdayjobs.com/wday/cxs/pinecresthealth/External/jobs"


def fixture(name: str):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def fake_http(monkeypatch, routes: dict, posts: dict | None = None) -> list:
    """GET routes by URL, Workday POST routes by (URL, offset); anything else is a 404."""
    calls = []
    posts = posts or {}

    def get_json(url):
        calls.append(("get", url))
        if url not in routes:
            raise http.FeedError(f"{url} answered HTTP 404")
        return json.loads(json.dumps(routes[url]))

    def post_json(url, body):
        calls.append(("post", url, body["offset"]))
        key = (url, body["offset"])
        if key not in posts:
            raise http.FeedError(f"{url} answered HTTP 404")
        assert body["limit"] == 20 and body["searchText"] == "" and body["appliedFacets"] == {}
        return json.loads(json.dumps(posts[key]))

    def get_text(url):
        raise AssertionError("the scan never reads pages")

    monkeypatch.setattr(http, "get_json", get_json)
    monkeypatch.setattr(http, "post_json", post_json)
    monkeypatch.setattr(http, "get_text", get_text)
    return calls


# --- adapters -------------------------------------------------------------------------

def test_greenhouse_adapter(monkeypatch):
    fake_http(monkeypatch, {GH_LIST: fixture("greenhouse_jobs.json")})
    jobs = greenhouse.list_jobs("larkspuranalytics")
    assert len(jobs) == 4
    assert jobs[0] == {"id": "4001001001", "title": "VP, Data Platform", "location": "Remote, United States",
                       "url": "https://job-boards.greenhouse.io/larkspuranalytics/jobs/4001001001",
                       "posted": "2026-10-20"}


def test_ashby_adapter_skips_unlisted(monkeypatch):
    fake_http(monkeypatch, {ASHBY_LIST: fixture("ashby_board.json")})
    jobs = ashby.list_jobs("alderrobotics")
    assert [j["title"] for j in jobs] == ["Head of Manufacturing Operations", "Robotics Technician"]
    assert jobs[0]["location"] == "Pittsburgh, PA; Remote, United States"
    assert jobs[0]["url"] == "https://jobs.ashbyhq.com/alderrobotics/a1b2c3d4-0000-4000-8000-000000000001"
    assert jobs[0]["posted"] == "2026-10-15"


def test_lever_adapter(monkeypatch):
    fake_http(monkeypatch, {LEVER_LIST: fixture("lever_postings.json")})
    jobs = lever.list_jobs("kestrelenergy")
    assert jobs[0]["title"] == "Senior Director, Grid Software"
    assert jobs[0]["location"] == "Houston, TX; Remote, US"
    assert jobs[0]["posted"] == "2026-10-29"
    assert jobs[0]["url"] == "https://jobs.lever.co/kestrelenergy/0f0e0d0c-1111-4222-8333-444455556666"
    assert jobs[1]["location"] == "Houston, TX"


def test_workable_adapter(monkeypatch):
    fake_http(monkeypatch, {WORKABLE_LIST: fixture("workable_account.json")})
    jobs = workable.list_jobs("bluewatergrid")
    assert jobs[0] == {"id": "BWG0000001", "title": "General Manager, Storage Projects",
                       "location": "Portland, Oregon, United States; Remote",
                       "url": "https://apply.workable.com/j/BWG0000001", "posted": "2026-10-25"}
    assert jobs[1]["location"] == "Portland, Oregon, United States"


def test_bamboohr_adapter(monkeypatch):
    fake_http(monkeypatch, {BAMBOO_LIST: fixture("bamboohr_list.json")})
    jobs = bamboohr.list_jobs("pinecresthealth")
    assert jobs[0] == {"id": "117", "title": "Chief Nursing Officer", "location": "Boise, Idaho",
                       "url": "https://pinecresthealth.bamboohr.com/careers/117", "posted": ""}
    assert jobs[1]["location"] == "Remote"


def test_rippling_adapter_pages(monkeypatch):
    calls = fake_http(monkeypatch, {RIPPLING_LIST: fixture("rippling_page0.json"),
                                    RIPPLING_LIST + "?page=1": fixture("rippling_page1.json")})
    jobs = rippling.list_jobs("bluewater-grid")
    assert [c[1] for c in calls] == [RIPPLING_LIST, RIPPLING_LIST + "?page=1"]
    assert [j["title"] for j in jobs] == ["Vice President, Customer Success", "Support Specialist",
                                          "Director of Field Operations"]
    assert jobs[0]["location"] == "Remote (United States)"
    assert jobs[1]["location"] == "Portland, OR, United States"
    assert jobs[2]["url"] == "https://ats.rippling.com/bluewater-grid/jobs/5e5e5e5e-0000-4000-9000-000000000003"


def test_rippling_stops_when_paging_is_ignored(monkeypatch):
    calls = fake_http(monkeypatch, {RIPPLING_LIST: fixture("rippling_page0.json"),
                                    RIPPLING_LIST + "?page=1": fixture("rippling_page0.json")})
    assert len(rippling.list_jobs("bluewater-grid")) == 2
    assert len(calls) == 2


def test_workday_adapter_pages(monkeypatch):
    calls = fake_http(monkeypatch, {}, {(WD_LIST, 0): fixture("workday_page0.json"),
                                        (WD_LIST, 20): fixture("workday_page1.json")})
    jobs = workday.list_jobs("pinecresthealth.wd1/External")
    assert calls == [("post", WD_LIST, 0), ("post", WD_LIST, 20)]
    assert len(jobs) == 23
    assert jobs[0]["id"] == "/job/Boise-ID/Vice-President--Clinical-Operations_R0001"
    assert jobs[0]["url"] == ("https://pinecresthealth.wd1.myworkdayjobs.com/External"
                              "/job/Boise-ID/Vice-President--Clinical-Operations_R0001")
    assert jobs[3]["posted"] == ""  # "Posted 30+ Days Ago"
    assert workday.list_jobs("https://pinecresthealth.wd1.myworkdayjobs.com/en-US/External")[0]["title"] \
        == "Vice President, Clinical Operations"


def test_workday_posted_dates_and_bad_site():
    assert workday.posted_date("Posted Today", TODAY) == "2026-11-04"
    assert workday.posted_date("Posted Yesterday", TODAY) == "2026-11-03"
    assert workday.posted_date("Posted 3 Days Ago", TODAY) == "2026-11-01"
    assert workday.posted_date("Posted 30+ Days Ago", TODAY) == ""
    with pytest.raises(ValueError):
        workday.parse_site("pinecresthealth")


def test_adapter_lookup():
    assert adapter("Greenhouse") is greenhouse
    assert adapter(" bamboohr ") is bamboohr
    assert adapter("Careers site") is None


# --- reading the watch table ----------------------------------------------------------

def test_parse_board():
    assert S.parse_board("Greenhouse") == ("greenhouse", "")
    assert S.parse_board("Greenhouse (larkspur-data)") == ("greenhouse", "larkspur-data")
    assert S.parse_board("**Workday**") == ("workday", "")
    assert S.parse_board("Careers site") == (None, "")
    assert S.parse_board("No public board") == (None, "")
    assert S.parse_board("") == (None, "")


def test_where_url():
    assert S.where_url("[Larkspur jobs](https://job-boards.greenhouse.io/larkspuranalytics)") \
        == "https://job-boards.greenhouse.io/larkspuranalytics"
    assert S.where_url("see https://jobs.lever.co/kestrelenergy for roles") == "https://jobs.lever.co/kestrelenergy"
    assert S.where_url("the careers page") == ""


@pytest.mark.parametrize("key,url,slug", [
    ("greenhouse", "https://job-boards.greenhouse.io/larkspuranalytics", "larkspuranalytics"),
    ("greenhouse", "https://boards.greenhouse.io/larkspuranalytics/jobs/4001001001", "larkspuranalytics"),
    ("greenhouse", "https://boards.greenhouse.io/embed/job_board?for=larkspuranalytics", "larkspuranalytics"),
    ("ashby", "https://jobs.ashbyhq.com/alderrobotics", "alderrobotics"),
    ("ashby", "https://jobs.ashbyhq.com/Alder%20Robotics/a1b2", "Alder Robotics"),
    ("lever", "https://jobs.lever.co/kestrelenergy/0f0e", "kestrelenergy"),
    ("workable", "https://apply.workable.com/bluewatergrid/", "bluewatergrid"),
    ("workable", "https://apply.workable.com/j/BWG0000001", None),
    ("bamboohr", "https://pinecresthealth.bamboohr.com/careers", "pinecresthealth"),
    ("rippling", "https://ats.rippling.com/bluewater-grid/jobs", "bluewater-grid"),
    ("rippling", "https://ats.rippling.com/en-GB/bluewater-grid/jobs", "bluewater-grid"),
    ("workday", "https://pinecresthealth.wd1.myworkdayjobs.com/en-US/External", "pinecresthealth.wd1/External"),
    ("workday", "https://pinecresthealth.wd12.myworkdayjobs.com/Careers/job/Boise/VP_R1", "pinecresthealth.wd12/Careers"),
    ("greenhouse", "https://careers.larkspur.example/jobs", None),
    ("lever", "", None),
])
def test_derive_slug(key, url, slug):
    assert S.derive_slug(key, url) == slug


# --- filters --------------------------------------------------------------------------

def test_default_seniority_filter():
    f = S.Filters.from_settings({})
    for title in ("VP, Data Platform", "SVP Sales", "Vice President of Finance", "Head of People", "Chief of Staff",
                  "CFO", "President, North America", "General Manager", "Senior Director, Grid Software",
                  "Principal Product Manager"):
        assert f.match(title), title
    for title in ("Senior Software Engineer", "Cargo Specialist", "Executive Assistant", "Directorate clerk"):
        assert not f.match(title), title


def test_functions_and_exclude_filters():
    f = S.Filters.from_settings({"functions": ["operations", r"\bdata\b"], "exclude": [r"\bintern"]})
    assert f.match("VP, Data Platform")
    assert f.match("Head of Manufacturing Operations")
    assert not f.match("Director of Finance")
    assert not f.match("Director, Intern Programs, Data")
    f = S.Filters.from_settings({"seniority": "Engineer"})
    assert f.match("Senior Software Engineer") and not f.match("VP, Data Platform")


def test_bad_pattern_is_a_scan_error():
    with pytest.raises(S.ScanError):
        S.Filters.from_settings({"exclude": ["(unclosed"]})


# --- the scan -------------------------------------------------------------------------

TRACKER = """# Job search tracker

## Submitted

| Submitted | Company | Role | Req or ID | Channel | Resume used | Status | Next follow-up | Follow-up notes |
|---|---|---|---|---|---|---|---|---|
| 2026-10-01 | Alder Robotics | [Robotics Program Director](https://jobs.ashbyhq.com/alderrobotics/old-1) | | Ashby | v1 | Applied | 2026-10-15 | |

## Conversations and referrals

| Date | Company | Person | About | Status | Next follow-up | Follow-up notes |
|---|---|---|---|---|---|---|

## Considering

| Found | Company | Role | Where | Base pay | Resume | Status | Next step |
|---|---|---|---|---|---|---|---|
| 2026-10-25 | Larkspur Analytics | [Director of Finance](https://job-boards.greenhouse.io/larkspuranalytics/jobs/4001001003/) | Denver, CO | not checked | Not built | Lead | read it |

## Passed

| Date | Company | Role | Why |
|---|---|---|---|
| 2026-10-20 | Pinecrest Health | [Director of Revenue Cycle](https://pinecresthealth.wd1.myworkdayjobs.com/External/job/Remote/Director-of-Revenue-Cycle_R0021?utm_source=feed) | Too far |

## Employers to watch

| Company | Why watch | Where to look | Board | Application limit | Last checked | Next check |
|---|---|---|---|---|---|---|
{watch}
"""

WATCH_ROWS = """\
| Larkspur Analytics | Data platform | [board](https://job-boards.greenhouse.io/larkspuranalytics) | Greenhouse | 3/12mo | | |
| Alder Robotics | Robots | https://careers.alder.example/jobs | Ashby (alderrobotics) | | | |
| Pinecrest Health | Health system | https://pinecresthealth.wd1.myworkdayjobs.com/en-US/External | Workday | | | |
| Kestrel Energy | Grid | https://careers.kestrel.example | Careers site | | 2026-10-20 | 2026-11-03 |
| Bluewater Grid | Storage | https://jobs.lever.co/bluewatergrid | Lever | | | |"""


def make_cfg(tmp_path, scan=None, watch=WATCH_ROWS) -> Config:
    (tmp_path / "tracker.md").write_text(TRACKER.replace("{watch}", watch), encoding="utf-8", newline="\n")
    return Config(home=tmp_path, scan=dict(scan or {}))


def feeds(monkeypatch, gh=None):
    return fake_http(monkeypatch, {GH_LIST: gh or fixture("greenhouse_jobs.json"),
                                   ASHBY_LIST: fixture("ashby_board.json")},
                     {(WD_LIST, 0): fixture("workday_page0.json"), (WD_LIST, 20): fixture("workday_page1.json")})


def watch_row(cfg, company):
    tr = T.Tracker.load(cfg.tracker)
    t = tr.table(T.WATCH)
    return t.dicts()[tr.find_one(T.WATCH, {"Company": company})]


def test_first_scan_adds_leads_and_records_baseline(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    calls = feeds(monkeypatch)
    r = S.scan(cfg, TODAY)

    titles = [(lead["company"], lead["title"]) for lead in r["leads"]]
    assert titles == [
        ("Larkspur Analytics", "VP, Data Platform"),
        ("Larkspur Analytics", "Director, Intern Programs"),
        ("Alder Robotics", "Head of Manufacturing Operations"),
        ("Pinecrest Health", "Vice President, Clinical Operations"),
    ]
    assert r["already_tracked"] == 2  # Director of Finance (Considering) and Director of Revenue Cycle (Passed)
    assert all(s["first_scan"] for s in r["scanned"])
    assert [s["company"] for s in r["scanned"]] == ["Larkspur Analytics", "Alder Robotics", "Pinecrest Health"]

    # Lever 404s: reported, never retried. Kestrel has no feed and its check is due.
    hand = {h["company"]: h["reason"] for h in r["check_by_hand"]}
    assert set(hand) == {"Kestrel Energy", "Bluewater Grid"}
    assert "feed failed" in hand["Bluewater Grid"] and "HTTP 404" in hand["Bluewater Grid"]
    assert "No feed" in hand["Kestrel Energy"]
    assert calls.count(("get", "https://api.lever.co/v0/postings/bluewatergrid?mode=json")) == 1

    tr = T.Tracker.load(cfg.tracker)
    rows = tr.table(T.CONSIDERING).dicts()
    assert len(rows) == 5
    assert rows[0] == {
        "Found": "2026-11-04",
        "Company": "Larkspur Analytics",
        "Role": "[VP, Data Platform](https://job-boards.greenhouse.io/larkspuranalytics/jobs/4001001001)",
        "Where": "Remote, United States",
        "Base pay": "not checked",
        "Resume": "Not built",
        "Status": "Lead",
        "Next step": "Found in the 2026-11-04 watch-list scan; read the posting",
    }
    assert rows[3]["Company"] == "Pinecrest Health"
    assert rows[4]["Role"].startswith("[Director of Finance]")

    for company in ("Larkspur Analytics", "Alder Robotics", "Pinecrest Health"):
        row = watch_row(cfg, company)
        assert (row["Last checked"], row["Next check"]) == ("2026-11-04", "2026-11-18")
    assert watch_row(cfg, "Bluewater Grid")["Last checked"] == ""
    assert watch_row(cfg, "Kestrel Energy")["Next check"] == "2026-11-03"
    assert watch_row(cfg, "Larkspur Analytics")["Application limit"] == "3/12mo"

    base = json.loads(cfg.baseline.read_text(encoding="utf-8"))
    assert set(base) == {"Larkspur Analytics", "Alder Robotics", "Pinecrest Health"}
    assert len(base["Larkspur Analytics"]) == 4
    assert len(base["Alder Robotics"]) == 2
    assert len(base["Pinecrest Health"]) == 23


def test_second_scan_only_adds_unseen(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    feeds(monkeypatch)
    S.scan(cfg, TODAY)
    again = S.scan(cfg, date(2026, 11, 5))
    assert again["leads"] == []
    assert not any(s["first_scan"] for s in again["scanned"])

    gh = fixture("greenhouse_jobs.json")
    gh["jobs"].append({"id": 4001001005, "title": "Head of Analytics Engineering", "location": {"name": "Remote"},
                       "absolute_url": "https://job-boards.greenhouse.io/larkspuranalytics/jobs/4001001005",
                       "first_published": "2026-11-05T09:00:00-04:00"})
    gh["jobs"].append({"id": 4001001006, "title": "Data Analyst", "location": {"name": "Remote"},
                       "absolute_url": "https://job-boards.greenhouse.io/larkspuranalytics/jobs/4001001006"})
    feeds(monkeypatch, gh=gh)
    third = S.scan(cfg, date(2026, 11, 6))
    assert [lead["title"] for lead in third["leads"]] == ["Head of Analytics Engineering"]
    base = json.loads(cfg.baseline.read_text(encoding="utf-8"))
    assert "4001001006" in base["Larkspur Analytics"]  # every posting is remembered, not just matches
    rows = T.Tracker.load(cfg.tracker).table(T.CONSIDERING).dicts()
    assert rows[0]["Role"].startswith("[Head of Analytics Engineering]")
    assert sum(1 for r in rows if "4001001001" in r["Role"]) == 1


def test_baseline_url_entries_count_as_seen(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.baseline.write_text(json.dumps({"Alder Robotics": [
        "https://jobs.ashbyhq.com/alderrobotics/a1b2c3d4-0000-4000-8000-000000000001"]}), encoding="utf-8")
    feeds(monkeypatch)
    r = S.scan(cfg, TODAY)
    assert "Alder Robotics" not in {lead["company"] for lead in r["leads"]}


def test_baseline_only_records_without_leads(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    feeds(monkeypatch)
    r = S.scan(cfg, TODAY, baseline_only=True)
    assert r["leads"] == []
    assert len(T.Tracker.load(cfg.tracker).table(T.CONSIDERING).rows) == 1
    assert len(json.loads(cfg.baseline.read_text(encoding="utf-8"))["Pinecrest Health"]) == 23
    assert watch_row(cfg, "Alder Robotics")["Last checked"] == "2026-11-04"
    assert S.scan(cfg, TODAY)["leads"] == []  # already baselined


def test_dry_run_writes_nothing(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    feeds(monkeypatch)
    r = S.scan(cfg, TODAY, dry_run=True)
    assert len(r["leads"]) == 4
    assert cfg.tracker.read_text(encoding="utf-8") == TRACKER.replace("{watch}", WATCH_ROWS)
    assert not cfg.baseline.exists()


def test_interval_and_filters_from_settings(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path, {"interval_days": 7, "exclude": [r"\bintern"], "functions": ["data", "operations"]})
    feeds(monkeypatch)
    r = S.scan(cfg, TODAY)
    assert [lead["title"] for lead in r["leads"]] == ["VP, Data Platform", "Head of Manufacturing Operations",
                                                      "Vice President, Clinical Operations"]
    assert watch_row(cfg, "Alder Robotics")["Next check"] == "2026-11-11"
    with pytest.raises(S.ScanError):
        S.scan(make_cfg(tmp_path, {"interval_days": "soon"}), TODAY)


def test_hand_checks_only_when_due_and_missing_slug(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path, watch="\n".join([
        "| Kestrel Energy | Grid | https://careers.kestrel.example | No public board | | 2026-11-01 | 2026-11-15 |",
        "| Bluewater Grid | Storage | https://careers.bluewater.example/jobs | Greenhouse | | | |",
    ]))
    calls = feeds(monkeypatch)
    r = S.scan(cfg, TODAY)
    assert calls == []
    assert [h["company"] for h in r["check_by_hand"]] == ["Bluewater Grid"]
    assert "Greenhouse (board-name)" in r["check_by_hand"][0]["reason"]
    assert watch_row(cfg, "Kestrel Energy")["Next check"] == "2026-11-15"


def test_bad_baseline_is_a_scan_error(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    cfg.baseline.write_text("{not json", encoding="utf-8")
    feeds(monkeypatch)
    with pytest.raises(S.ScanError):
        S.scan(cfg, TODAY)


# --- discover -------------------------------------------------------------------------

def test_slug_candidates():
    assert S.slug_candidates("Alder Robotics, Inc.") == ["alderroboticsinc", "alder-robotics-inc",
                                                         "alderrobotics", "alder-robotics"]
    assert S.slug_candidates("Bluewater Grid AI") == ["bluewatergridai", "bluewater-grid-ai",
                                                      "bluewatergrid", "bluewater-grid"]
    assert S.slug_candidates("Kestrel") == ["kestrel"]
    assert S.slug_candidates("Larkspur Analytics Labs") == ["larkspuranalyticslabs", "larkspur-analytics-labs",
                                                            "larkspuranalytics", "larkspur-analytics"]
    assert S.company_key("Alder Robotics, Inc.") == S.company_key("alder robotics")


def test_discover_and_add(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path, watch="| Pinecrest Health | Health system | https://pinecresthealth.wd1.myworkdayjobs.com/External | Workday | | | |")
    names = tmp_path / "companies.txt"
    names.write_text("# watch these\nAlder Robotics, Inc.\nKestrel Energy\n\nPinecrest Health, Inc.\nBluewater Grid AI\n",
                     encoding="utf-8")
    empty_board = {"jobs": [], "meta": {"total": 0}}
    fake_http(monkeypatch, {
        ASHBY_LIST: fixture("ashby_board.json"),
        "https://api.lever.co/v0/postings/kestrelenergy?mode=json": fixture("lever_postings.json"),
        "https://boards-api.greenhouse.io/v1/boards/pinecresthealth/jobs": empty_board,
    })
    r = S.discover(cfg, TODAY, names, add=True)
    found = {d["company"]: d for d in r["results"]}
    assert found["Alder Robotics, Inc."]["board"] == "Ashby"
    assert found["Alder Robotics, Inc."]["slug"] == "alderrobotics"
    assert [s["title"] for s in found["Alder Robotics, Inc."]["senior"]] == ["Head of Manufacturing Operations"]
    assert found["Kestrel Energy"]["board"] == "Lever"
    assert found["Kestrel Energy"]["where"] == "https://jobs.lever.co/kestrelenergy"
    assert found["Pinecrest Health, Inc."]["board"] == "Greenhouse"  # exists but empty, so flagged
    assert "no postings" in found["Pinecrest Health, Inc."]["note"]
    assert found["Bluewater Grid AI"]["board"] == ""
    assert r["added"] == ["Alder Robotics, Inc.", "Kestrel Energy"]  # Pinecrest Health is already watched

    rows = T.Tracker.load(cfg.tracker).table(T.WATCH).dicts()
    assert [row["Company"] for row in rows] == ["Pinecrest Health", "Alder Robotics, Inc.", "Kestrel Energy"]
    assert rows[1]["Where to look"] == "https://jobs.ashbyhq.com/alderrobotics"
    assert rows[2]["Board"] == "Lever" and rows[2]["Next check"] == "2026-11-04"


def test_discover_dry_run_writes_nothing(monkeypatch, tmp_path):
    cfg = make_cfg(tmp_path)
    before = cfg.tracker.read_text(encoding="utf-8")
    names = tmp_path / "companies.txt"
    names.write_text("Alder Robotics\n", encoding="utf-8")
    fake_http(monkeypatch, {"https://boards-api.greenhouse.io/v1/boards/alderrobotics/jobs": fixture("greenhouse_jobs.json")})
    r = S.discover(cfg, TODAY, names, add=True, dry_run=True)
    assert r["added"] == []  # Alder Robotics is already watched
    assert cfg.tracker.read_text(encoding="utf-8") == before


def test_discover_not_found_and_missing_file(monkeypatch, tmp_path):
    fake_http(monkeypatch, {})
    d = S.discover_one("Bluewater Grid", S.Filters.from_settings({}))
    assert d["board"] == "" and "bluewatergrid" in d["note"]
    with pytest.raises(S.ScanError):
        S.read_names(tmp_path / "missing.txt")


# --- CLI ------------------------------------------------------------------------------

def args(**kw):
    base = {"dry_run": False, "baseline_only": False, "json": False, "discover": None, "add": False}
    base.update(kw)
    return argparse.Namespace(**base)


def test_cli_text_and_json(monkeypatch, tmp_path, capsys):
    cfg = make_cfg(tmp_path)
    feeds(monkeypatch)
    assert S.cli(args(dry_run=True), cfg, TODAY) == 0
    out = capsys.readouterr().out
    assert "dry run" in out and "New leads (4, would be added to Considering)" in out
    assert "Check by hand (2):" in out
    assert S.cli(args(json=True), cfg, TODAY) == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["leads"]) == 4 and data["dry_run"] is False
    with pytest.raises(S.ScanError):
        S.cli(args(add=True), cfg, TODAY)


def test_add_arguments():
    p = argparse.ArgumentParser()
    S.add_arguments(p)
    a = p.parse_args(["--dry-run", "--discover", "names.txt", "--add", "--json"])
    assert a.dry_run and a.discover == "names.txt" and a.add and a.json and not a.baseline_only
