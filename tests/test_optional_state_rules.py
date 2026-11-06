"""Spec 10243: three optional state rules (same employer, one-time reminders, a file-by date)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from perkins import clerk as K
from perkins import config as C
from perkins import due as D
from helpers import EMPLOYER_FIELDS, VA_EMPLOYER_FIELDS, claims_home, make_home

WORKSHOP = {"What activity": "Resume workshop", "Office name and city": "Example Workforce Center, Richmond",
            "Person": "leader not named", "Result and next step": "Attended", "Source": "my own account"}


def va_home(tmp_path, today=date(2027, 3, 1), claim_start=date(2027, 2, 28)):
    return claims_home(tmp_path, today=today, claim_start=claim_start, state="va")


def week_text(cfg, end=date(2027, 3, 13)):
    return K.week_path(cfg, end).read_text(encoding="utf-8")


def lines(cfg, rx):
    return [l for l in cfg.nudges.read_text(encoding="utf-8").splitlines() if rx.search(l)]


def broken_state(tmp_path, monkeypatch, old: str, new: str) -> None:
    text = (C.STATES_DIR / "va.toml").read_text(encoding="utf-8").replace('code = "va"', 'code = "zz"')
    assert old in text
    states = tmp_path / "states"
    states.mkdir(exist_ok=True)
    (states / "zz.toml").write_text(text.replace(old, new), encoding="utf-8")
    monkeypatch.setattr(C, "STATES_DIR", states)


def test_va_sets_all_three_keys():
    va = C.load_state("va")
    assert va.claim_late_days == 21
    assert va.distinct_employers == {"employer": "Employer or business name", "opening": "Type of work or position"}
    (task,) = va.once
    assert task["within_days"] == 10 and task["task"].startswith("Fully register with the Virginia Workforce Connection")
    wa = C.load_state("wa")
    assert (wa.claim_late_days, wa.distinct_employers, wa.once) == (0, {}, [])


# --- same employer -----------------------------------------------------------

def test_same_employer_different_opening_potentially_counts(tmp_path):
    cfg = va_home(tmp_path)
    va = C.load_state("va")
    K.add_entry(cfg, va, date(2027, 3, 8), "Employer contact", VA_EMPLOYER_FIELDS, "solid")
    out = K.add_entry(cfg, va, date(2027, 3, 9), "Employer contact",
                      {**VA_EMPLOYER_FIELDS, "Type of work or position": "Field Supervisor (KE-9)"}, "solid")
    assert out["fit"] == "maybe"
    assert ("- **Fit:** maybe. A second contact with this employer this week, for a different opening. "
            "VEC asks for two different employers, so this one potentially counts.") in week_text(cfg)
    w = K.parse_week(K.week_path(cfg, date(2027, 3, 13)))
    assert (w["solid"], w["maybe"]) == (1, 1)
    assert K.counts_phrase(w, 2).startswith("1 of 2 solid, 1 potentially counts")


def test_same_employer_same_opening_is_a_likely_repeat(tmp_path):
    cfg = va_home(tmp_path)
    va = C.load_state("va")
    K.add_entry(cfg, va, date(2027, 3, 8), "Employer contact", VA_EMPLOYER_FIELDS, "solid")
    out = K.add_entry(cfg, va, date(2027, 3, 9), "Employer contact",
                      {**VA_EMPLOYER_FIELDS, "Employer or business name": "kestrel  ENERGY"}, "solid")
    assert out["fit"] == "check"
    assert ("- **Fit:** check. Looks like a repeat of activity 1 (same employer and opening). "
            "VEC doesn't count a repeated contact.") in week_text(cfg)


def test_same_employer_in_different_weeks_is_fine(tmp_path):
    cfg = va_home(tmp_path)
    va = C.load_state("va")
    assert K.add_entry(cfg, va, date(2027, 3, 3), "Employer contact", VA_EMPLOYER_FIELDS, "solid")["fit"] == "solid"
    assert K.add_entry(cfg, va, date(2027, 3, 9), "Employer contact", VA_EMPLOYER_FIELDS, "solid")["fit"] == "solid"


def test_workforce_center_activities_never_match_an_employer(tmp_path):
    cfg = va_home(tmp_path)
    va = C.load_state("va")
    for d in (date(2027, 3, 8), date(2027, 3, 9)):
        assert K.add_entry(cfg, va, d, "Workforce center activity", WORKSHOP, "solid")["fit"] == "maybe"


def test_washington_doesnt_set_the_rule(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    wa = C.load_state("wa")
    for d in (date(2027, 3, 8), date(2027, 3, 9)):
        assert K.add_entry(cfg, wa, d, "Employer contact", EMPLOYER_FIELDS, "solid")["fit"] == "solid"


def test_distinct_employers_must_name_real_fields(tmp_path, monkeypatch):
    broken_state(tmp_path, monkeypatch, 'opening = "Type of work or position"', 'opening = "Position applied for"')
    with pytest.raises(C.ConfigError, match="Position applied for"):
        C.load_state("zz")


# --- one-time reminders ------------------------------------------------------

def test_one_time_line_is_written_once_and_never_unticked(tmp_path):
    cfg = va_home(tmp_path)
    K.run(cfg, date(2027, 3, 1))
    (line,) = lines(cfg, K.ONCE_RE)
    assert line.startswith("- [ ] (H) 2027-03-01 One-time: Fully register with the Virginia Workforce Connection")
    assert "Due 2027-03-10; tick this once it's done. 📅 2027-03-10" in line
    K.run(cfg, date(2027, 3, 2))
    assert len(lines(cfg, K.ONCE_RE)) == 1
    text = cfg.nudges.read_text(encoding="utf-8")
    cfg.nudges.write_text(text.replace(line, line.replace("- [ ]", "- [x]", 1) + " ✅ 2027-03-04"), encoding="utf-8")
    K.run(cfg, date(2027, 3, 5))
    (line,) = lines(cfg, K.ONCE_RE)
    assert line.startswith("- [x]")


def test_one_time_line_on_the_due_list_until_ticked(tmp_path):
    cfg = va_home(tmp_path)
    K.run(cfg, date(2027, 3, 1))
    assert not [i for i in D.collect(cfg, date(2027, 3, 1), 7) if i["kind"] == "once"]  # 9 days out
    (soon,) = [i for i in D.collect(cfg, date(2027, 3, 5), 7) if i["kind"] == "once"]
    assert soon["date"] == "2027-03-10" and not soon["overdue"]
    (late,) = [i for i in D.collect(cfg, date(2027, 3, 12), 7) if i["kind"] == "once"]
    assert late["overdue"]
    line = lines(cfg, K.ONCE_RE)[0]
    cfg.nudges.write_text(cfg.nudges.read_text(encoding="utf-8").replace(line, line.replace("- [ ]", "- [x]", 1)),
                          encoding="utf-8")
    assert not [i for i in D.collect(cfg, date(2027, 3, 12), 7) if i["kind"] == "once"]


def test_no_one_time_line_in_washington_or_search(tmp_path):
    wa = claims_home(tmp_path / "wa", today=date(2027, 3, 1))
    K.run(wa, date(2027, 3, 3))
    assert not lines(wa, K.ONCE_RE)
    search = make_home(tmp_path / "search")
    assert not search.nudges.exists() or not lines(search, K.ONCE_RE)
    assert not [i for i in D.collect(search, date(2027, 3, 5), 7) if i["kind"] == "once"]


@pytest.mark.parametrize("old, new, message", [
    ('task = "Fully register', 'job = "Fully register', "needs a task"),
    ("within_days = 10", 'within_days = "ten"', "within_days must be a whole number"),
])
def test_a_bad_once_entry_refuses_to_load(tmp_path, monkeypatch, old, new, message):
    broken_state(tmp_path, monkeypatch, old, new)
    with pytest.raises(C.ConfigError, match=message):
        C.load_state("zz")


# --- the file-by date --------------------------------------------------------

def test_file_by_dates():
    va = C.load_state("va")
    assert K.file_by(va, date(2027, 3, 6), date(2027, 2, 21)) == date(2027, 3, 26)
    assert K.file_by(va, date(2027, 3, 6), date(2027, 3, 1)) == date(2027, 3, 21)  # the first week
    assert K.file_by(C.load_state("wa"), date(2027, 3, 6), date(2027, 3, 1)) is None


def test_claim_line_shows_the_file_by_date_then_says_it_passed(tmp_path):
    cfg = va_home(tmp_path, claim_start=date(2027, 2, 21))
    K.run(cfg, date(2027, 3, 7))
    (line,) = [l for l in lines(cfg, K.CLAIM_RE) if "2027-03-06" in l]
    assert "tick this once it's filed. File by 2027-03-26. [log](log/week-ending-2027-03-06.md)" in line
    K.run(cfg, date(2027, 3, 27))
    (line,) = [l for l in lines(cfg, K.CLAIM_RE) if "2027-03-06" in l]
    assert ("Past VEC's file-by date (2027-03-26): the claim may have gone inactive, and VEC may need you "
            "to reactivate it.") in line


def test_ticked_claim_line_is_left_alone(tmp_path):
    cfg = va_home(tmp_path, claim_start=date(2027, 2, 21))
    K.run(cfg, date(2027, 3, 7))
    K.stamp_filed(cfg, date(2027, 3, 6), date(2027, 3, 7))
    (before,) = [l for l in lines(cfg, K.CLAIM_RE) if "2027-03-06" in l]
    K.run(cfg, date(2027, 3, 27))
    (after,) = [l for l in lines(cfg, K.CLAIM_RE) if "2027-03-06" in l]
    assert before == after and before.startswith("- [x]") and "File by 2027-03-26." in after


def test_due_item_names_the_file_by_date(tmp_path):
    cfg = va_home(tmp_path, claim_start=date(2027, 2, 21))
    K.run(cfg, date(2027, 3, 8))
    (item,) = D.claim_items(cfg, date(2027, 3, 8))
    assert item["detail"].endswith("; file by 2027-03-26")


def test_washington_claim_line_is_unchanged():
    wa = C.load_state("wa")
    w = {"solid": 1, "maybe": 0, "check": 1, "missing": 0}
    assert K.claim_line(wa, date(2027, 3, 8), date(2027, 3, 6), w, date(2027, 2, 28), date(2027, 3, 30)) == (
        "- [ ] (H) 2027-03-08 File the ESD weekly claim for the week ending 2027-03-06: 1 of 3 solid, 1 to check. "
        "Log any stragglers and fill the blanks first; tick this once it's filed. "
        "[log](log/week-ending-2027-03-06.md) 📅 2027-03-08")


@pytest.mark.parametrize("value", ["0", '"21"', "21.5"])
def test_a_bad_claim_late_days_refuses_to_load(tmp_path, monkeypatch, value):
    broken_state(tmp_path, monkeypatch, "claim_late_days = 21", f"claim_late_days = {value}")
    with pytest.raises(C.ConfigError, match="claim_late_days must be a whole number above zero"):
        C.load_state("zz")
