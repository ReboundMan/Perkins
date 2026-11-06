"""Spec 10244: per-claim requirement adjustments, recorded only from what the agency told the person."""
from __future__ import annotations

from datetime import date

import pytest

import run as R
from perkins import claim_log as L
from perkins import clerk as K
from perkins import config as C
from perkins import dashboard as Dash
from perkins import status as S
from perkins.errors import PerkinsError
from helpers import EMPLOYER_FIELDS, VA_EMPLOYER_FIELDS, claims_home

TRAINING = "ESD letter dated 2027-03-04: approved training, one contact a week"
WAIVED = "ESD waived the job search while my approved training runs"


def adjust(cfg, today, *args):
    return R.main(["--data", str(cfg.home), "--today", today, "clerk", "adjust", *args])


def fm(cfg, end):
    return K.parse_week(K.week_path(cfg, end))["fm"]


def lines(cfg, rx):
    return [l for l in cfg.nudges.read_text(encoding="utf-8").splitlines() if rx.search(l)]


def test_adjust_records_lists_and_removes(tmp_path, capsys):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    K.run(cfg, date(2027, 3, 10))
    assert adjust(cfg, "2027-03-10", "--from", "2027-03-07", "--to", "2027-03-20", "--required", "1",
                  "--reason", TRAINING) == 0
    cfg = C.load(cfg.home)
    assert cfg.adjustments == [{"from": date(2027, 3, 7), "to": date(2027, 3, 20), "required": 1, "reason": TRAINING}]
    assert "[[claims.adjustment]]" in cfg.config_path.read_text(encoding="utf-8")
    assert (fm(cfg, date(2027, 3, 13))["required"], fm(cfg, date(2027, 3, 13))["required_reason"]) == ("1", TRAINING)
    assert fm(cfg, date(2027, 3, 6))["required"] == "3" and "required_reason" not in fm(cfg, date(2027, 3, 6))
    capsys.readouterr()
    assert adjust(cfg, "2027-03-10", "--list") == 0
    assert f"2027-03-07 to 2027-03-20: 1 a week ({TRAINING})" in capsys.readouterr().out
    assert adjust(cfg, "2027-03-10", "--remove", "--from", "2027-03-07") == 0
    cfg = C.load(cfg.home)
    assert cfg.adjustments == []
    week = fm(cfg, date(2027, 3, 13))
    assert week["required"] == "3" and "required_reason" not in week


def test_render_and_load_round_trip(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    cfg.adjustments = C.check_adjustments([{"from": "2027-03-07", "required": 0, "reason": WAIVED}])
    C.save(cfg)
    again = C.load(cfg.home)
    assert again.adjustments == [{"from": date(2027, 3, 7), "to": None, "required": 0, "reason": WAIVED}]
    assert again.state == "wa" and again.claim_start == date(2027, 2, 28)


def test_one_solid_meets_an_adjusted_minimum_of_one(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    adjust(cfg, "2027-03-10", "--from", "2027-03-07", "--required", "1", "--reason", TRAINING)
    cfg = C.load(cfg.home)
    (check,) = [l for l in lines(cfg, K.CHECK_RE) if "2027-03-13" in l]
    assert "0 of 1 solid" in check
    K.add_entry(cfg, C.load_state("wa"), date(2027, 3, 10), "Employer contact", EMPLOYER_FIELDS, "solid")
    K.run(cfg, date(2027, 3, 11))
    (check,) = [l for l in lines(cfg, K.CHECK_RE) if "2027-03-13" in l]
    assert check.startswith("- [x]") and "(auto: 1 solid entries logged)" in check
    html = Dash.build(cfg, date(2027, 3, 11))
    assert "This week · ESD minimum 1" in html and "1 of 1 solid" in html
    assert f"ESD minimum 1 (adjusted: {TRAINING})" in html
    text = S.text(S.report(cfg, date(2027, 3, 11)))
    assert f"Claim week: 1 of 1 solid, 0 to check (ESD minimum 1, adjusted: {TRAINING})" in text
    assert f"ESD minimum 1 (adjusted: {TRAINING})" in L.build(cfg, date(2027, 3, 11))


def test_a_waived_week(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    K.run(cfg, date(2027, 3, 10))
    adjust(cfg, "2027-03-10", "--from", "2027-03-14", "--required", "0", "--reason", WAIVED)
    cfg = C.load(cfg.home)
    K.run(cfg, date(2027, 3, 17))  # Wednesday of the waived week
    w = K.parse_week(K.week_path(cfg, date(2027, 3, 20)))
    assert w["entries"] == [] and w["fm"]["required"] == "0"
    assert not [l for l in lines(cfg, K.CHECK_RE) if "2027-03-20" in l]
    assert K.counts_phrase(w, K.week_required(w, C.load_state("wa"))) == f"no work search required this week ({WAIVED})"
    K.run(cfg, date(2027, 3, 22))  # Washington's claim day for that week
    (claim,) = [l for l in lines(cfg, K.CLAIM_RE) if "2027-03-20" in l]
    assert f"week ending 2027-03-20: no work search required this week ({WAIVED})." in claim
    assert "No work search required" in Dash.build(cfg, date(2027, 3, 17))


def test_overlapping_adjustments_the_later_one_wins(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    cfg.adjustments = C.check_adjustments([
        {"from": "2027-03-01", "to": "2027-03-31", "required": 2, "reason": "ESD letter: two a week this month"},
        {"from": "2027-03-10", "required": 1, "reason": TRAINING}])
    st = C.load_state("wa")
    assert C.required_for(cfg, st, date(2027, 2, 28), date(2027, 3, 6)) == (2, "ESD letter: two a week this month")
    assert C.required_for(cfg, st, date(2027, 3, 7), date(2027, 3, 13)) == (1, TRAINING)
    assert C.required_for(cfg, st, date(2027, 2, 21), date(2027, 2, 27)) == (3, "")


@pytest.mark.parametrize("bad, message", [
    ({"from": "2027-03-10", "to": "2027-03-01", "required": 1, "reason": "x"}, "before from"),
    ({"from": "2027-03-10", "required": -1, "reason": "x"}, "0 or more"),
    ({"from": "2027-03-10", "required": 1, "reason": "  "}, "needs a reason"),
    ({"required": 1, "reason": "x"}, "needs from"),
    ({"from": "2027-03-10", "required": 1, "reason": "ESD letter for SSN 123-45-6789"}, "Social Security"),
])
def test_bad_adjustments_refuse(bad, message):
    with pytest.raises(PerkinsError, match=message):
        C.check_adjustments([bad])


def test_virginia_names_vec(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1), state="va")
    adjust(cfg, "2027-03-10", "--from", "2027-03-07", "--required", "1",
           "--reason", "VEC letter dated 2027-03-04: approved training, one contact a week")
    cfg = C.load(cfg.home)
    K.add_entry(cfg, C.load_state("va"), date(2027, 3, 10), "Employer contact", VA_EMPLOYER_FIELDS, "solid")
    assert "VEC minimum 1 (adjusted: VEC letter dated 2027-03-04" in Dash.build(cfg, date(2027, 3, 11))


def test_no_adjustments_changes_nothing(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    K.run(cfg, date(2027, 3, 10))
    assert cfg.adjustments == [] and "[[claims.adjustment]]" not in cfg.config_path.read_text(encoding="utf-8")
    assert fm(cfg, date(2027, 3, 13))["required"] == "3" and "required_reason" not in fm(cfg, date(2027, 3, 13))


def test_an_earlier_claims_adjustment_never_applies_to_a_new_claim(tmp_path, capsys):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    adjust(cfg, "2027-03-10", "--from", "2027-03-07", "--required", "0", "--reason", WAIVED)  # no end date
    cfg = C.load(cfg.home)
    cfg.claim_start, cfg.claim_end = date(2028, 5, 7), None  # a new claim, a year on
    C.save(cfg)
    cfg = C.load(cfg.home)
    st = C.load_state("wa")
    assert C.required_for(cfg, st, date(2028, 5, 7), date(2028, 5, 13)) == (3, "")
    K.run(cfg, date(2028, 5, 10))
    assert fm(cfg, date(2028, 5, 13))["required"] == "3"
    capsys.readouterr()
    adjust(cfg, "2028-05-10", "--list")
    assert "before this claim, so it doesn't apply" in capsys.readouterr().out


def test_removing_an_adjustment_reopens_a_check_line_the_clerk_ticked(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    K.run(cfg, date(2027, 3, 10))  # Wednesday: the check line opens at 0 of 3
    adjust(cfg, "2027-03-10", "--from", "2027-03-07", "--required", "0", "--reason", WAIVED)
    (line,) = [l for l in lines(C.load(cfg.home), K.CHECK_RE) if "2027-03-13" in l]
    assert line.startswith("- [x]") and "(auto: no work search required this week)" in line
    adjust(cfg, "2027-03-11", "--remove", "--from", "2027-03-07")
    (line,) = [l for l in lines(C.load(cfg.home), K.CHECK_RE) if "2027-03-13" in l]
    assert line.startswith("- [ ] (M) 2027-03-10 Work search check, week ending 2027-03-13: 0 of 3 solid")


def test_a_mid_week_waiver_takes_away_the_empty_slots_and_gives_them_back(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    K.run(cfg, date(2027, 3, 10))
    K.add_entry(cfg, C.load_state("wa"), date(2027, 3, 8), "Employer contact", EMPLOYER_FIELDS, "solid")
    path = K.week_path(cfg, date(2027, 3, 13))
    assert path.read_text(encoding="utf-8").count(K.OPEN_SLOT) == 2
    adjust(cfg, "2027-03-10", "--from", "2027-03-09", "--required", "0", "--reason", WAIVED)
    text = path.read_text(encoding="utf-8")
    assert K.OPEN_SLOT not in text and "## Activity 1: Larkspur Analytics" in text
    adjust(cfg, "2027-03-10", "--remove", "--from", "2027-03-09")
    text = path.read_text(encoding="utf-8")
    assert text.count(K.OPEN_SLOT) == 2 and "## Activity 3\n" in text
    assert "## Activity 1: Larkspur Analytics" in text


def test_a_reason_with_a_colon_and_quotes_is_a_quoted_frontmatter_value(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    reason = 'ESD letter dated 2027-03-04: "one contact a week" #training'
    adjust(cfg, "2027-03-10", "--from", "2027-03-07", "--required", "1", "--reason", reason)
    cfg = C.load(cfg.home)
    text = K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")
    assert 'required_reason: "ESD letter dated 2027-03-04: \\"one contact a week\\" #training"' in text
    assert fm(cfg, date(2027, 3, 13))["required_reason"] == reason
    assert f"ESD minimum 1 (adjusted: {reason})".replace('"', "&quot;") in Dash.build(cfg, date(2027, 3, 11))


def test_control_characters_never_reach_perkins_toml():
    bell = chr(7)
    (a,) = C.check_adjustments([{"from": "2027-03-10", "required": 1, "reason": f"ESD letter{bell} one a week"}])
    assert a["reason"] == "ESD letter one a week"
