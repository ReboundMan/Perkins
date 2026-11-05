from datetime import date

from perkins import clerk as K
from perkins import config as C
from perkins import dashboard as Dash
from perkins import due as D
from perkins import status as S
from perkins import tracker as T
from helpers import EMPLOYER_FIELDS, claims_home, make_home


def add_rows(cfg):
    tr = T.Tracker.load(cfg.tracker)
    tr.add(T.SUBMITTED, {"Submitted": "2027-03-02", "Company": "Larkspur Analytics", "Role": "Director",
                         "Next follow-up": "2027-03-09 *suggested*", "Follow-up notes": "Check the portal"})
    tr.add(T.SUBMITTED, {"Submitted": "2027-03-08", "Company": "Alder Robotics", "Role": "VP",
                         "Next follow-up": "2027-03-30"})
    tr.add(T.WATCH, {"Company": "Bluewater Grid", "Why watch": "Grid software", "Next check": "2027-03-14"})
    tr.add(T.CONSIDERING, {"Company": "Kestrel <b>Energy</b>", "Role": "Head", "Resume": "Ready", "Status": "Resume ready"})
    tr.save()


def test_due_lists_overdue_and_soon_but_not_far(tmp_path):
    cfg = make_home(tmp_path)
    add_rows(cfg)
    items = D.collect(cfg, date(2027, 3, 10), 7)
    whats = [i["what"] for i in items]
    assert whats == ["Kestrel <b>Energy</b>, Head", "Larkspur Analytics, Director", "Bluewater Grid"]
    assert items[0]["kind"] == "ready"
    assert items[1]["overdue"] and not items[2]["overdue"]
    assert items[2]["kind"] == "check" and items[2]["detail"] == "Grid software"


def test_unfiled_claim_tops_the_due_list(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    st = C.load_state("wa")
    for _ in range(3):
        K.add_entry(cfg, st, date(2027, 3, 3), "Employer contact", EMPLOYER_FIELDS, "solid")
    add_rows(cfg)
    items = D.collect(cfg, date(2027, 3, 10), 7)
    assert items[0]["kind"] == "claim" and "2027-03-06" in items[0]["what"] and items[0]["overdue"]
    K.stamp_filed(cfg, date(2027, 3, 6), date(2027, 3, 8))
    assert D.collect(cfg, date(2027, 3, 10), 7)[0]["kind"] != "claim"


def test_dashboard_claim_panel_matches_the_week_files(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    st = C.load_state("wa")
    K.add_entry(cfg, st, date(2027, 3, 3), "Employer contact", EMPLOYER_FIELDS, "solid")
    K.stamp_filed(cfg, date(2027, 3, 6), date(2027, 3, 8))
    K.add_entry(cfg, st, date(2027, 3, 9), "Employer contact", EMPLOYER_FIELDS, "solid")
    K.add_entry(cfg, st, date(2027, 3, 10), "Employer contact", EMPLOYER_FIELDS, "check", reason="Waiting on a detail.")
    html = Dash.build(cfg, date(2027, 3, 12))
    w = K.parse_week(K.week_path(cfg, date(2027, 3, 13)))
    assert f"{w['solid']} of 3 solid" in html and "1 to check" in html
    assert "claim warn" in html  # Friday and short
    assert "Filed 2027-03-08" in html and "claim good" in html


def test_dashboard_escapes_cells_and_counts_ready(tmp_path):
    cfg = make_home(tmp_path)
    add_rows(cfg)
    html = Dash.build(cfg, date(2027, 3, 10))
    assert "<b>Energy</b>" not in html and "&lt;b&gt;Energy&lt;/b&gt;" in html
    assert "<div class='n'>1</div><div class='l'>Resumes ready</div>" in html
    assert "class='over'" in html and "class='claim-panel'" not in html


def test_search_weekly_target_card(tmp_path):
    cfg = make_home(tmp_path)
    cfg.weekly_target = 2
    C.save(cfg)
    add_rows(cfg)
    html = Dash.build(C.load(tmp_path), date(2027, 3, 10))
    assert "Applied this week (target 2)" in html


def test_status_report_in_both_modes(tmp_path):
    cfg = make_home(tmp_path / "s")
    add_rows(cfg)
    r = S.report(cfg, date(2027, 3, 10))
    assert r["counts"]["submitted"] == 2 and r["resumes_ready"] and "claims" not in r
    assert "Needs you" in S.text(r)
    c = claims_home(tmp_path / "c", today=date(2027, 3, 10))
    r = S.report(c, date(2027, 3, 10))
    assert r["claims"]["required"] == 3 and r["claims"]["this_week"]["solid"] == 0


def test_status_reminds_where_the_log_is_after_the_claim(tmp_path):
    from perkins import init as I
    claims_home(tmp_path, today=date(2027, 3, 10))
    I.init(tmp_path, C.SEARCH, date(2027, 3, 20), claim_end=date(2027, 3, 13), pointer=False)
    r = S.report(C.load(tmp_path), date(2027, 3, 20))
    assert "30 days" in r["log_kept"]["retention"]
