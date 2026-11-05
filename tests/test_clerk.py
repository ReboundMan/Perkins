from datetime import date

import pytest

from perkins import clerk as K
from perkins import config as C
from perkins.errors import PerkinsError
from helpers import EMPLOYER_FIELDS, claims_home

WA = None


def state():
    global WA
    WA = WA or C.load_state("wa")
    return WA


def write_week(cfg, end: str, fits: list[tuple[str, str]], claim_filed='"no"'):
    """fits: (fit, contact info) per activity."""
    body = "".join(
        f"## Activity {i + 1}: Co {i}\n\n- **Contact date:** {end}\n- **Kind:** Employer contact\n"
        f"- **Employer or business name:** Co {i}\n- **Employer contact info:** {info}\n- **Fit:** {fit}\n\n"
        for i, (fit, info) in enumerate(fits))
    p = K.week_path(cfg, date.fromisoformat(end))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\ntype: work-search-log\nweek_ending: {end}\nsolid: 0\ncheck: 0\n"
                 f"claim_filed: {claim_filed}\n---\n\n# Log\n\n{body}", encoding="utf-8")
    return p


def nudges(cfg, kind):
    rx = K.CLAIM_RE if kind == "claim" else K.CHECK_RE
    return [l for l in cfg.nudges.read_text(encoding="utf-8").splitlines() if rx.search(l)]


def run(cfg, d):
    return K.run(cfg, date.fromisoformat(d))


@pytest.fixture()
def cfg(tmp_path):
    return claims_home(tmp_path, today=date(2027, 3, 1))


# --- weeks -------------------------------------------------------------------

@pytest.mark.parametrize("d", ["2027-03-07", "2027-03-10", "2027-03-13"])
def test_week_runs_sunday_to_saturday(d):
    assert K.week_bounds(date.fromisoformat(d), state()) == (date(2027, 3, 7), date(2027, 3, 13))


def test_counts_solid_check_no_and_missing(cfg):
    p = write_week(cfg, "2027-03-13", [("solid", "x"), ("check. why", "MISSING: city"), ("no", "x")])
    w = K.parse_week(p)
    assert (w["solid"], w["check"], w["no"], w["missing"]) == (1, 1, 1, 1)


def test_unreadable_fit_counts_as_check_never_solid(cfg):
    p = write_week(cfg, "2027-03-13", [("Solid-ish", "x"), ("", "x")])
    w = K.parse_week(p)
    assert w["solid"] == 0 and w["check"] == 2


def test_legacy_contact_heading_and_fit_field_still_count(cfg):
    p = K.week_path(cfg, date(2027, 3, 13))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\nsolid: 0\n---\n\n## Contact 1: X\n\n- **Kind:** Employer contact\n- **ESD fit:** solid\n", encoding="utf-8")
    assert K.parse_week(p)["solid"] == 1


def test_open_slots_are_not_entries(cfg):
    K.ensure_week(cfg, state(), date(2027, 3, 13), date(2027, 3, 7))
    w = K.parse_week(K.week_path(cfg, date(2027, 3, 13)))
    assert (w["solid"], w["check"], len(w["entries"])) == (0, 0, 3)


def test_recount_writes_frontmatter(cfg):
    p = write_week(cfg, "2027-03-13", [("solid", "x"), ("solid", "x")])
    K.recount(p)
    assert "solid: 2" in p.read_text(encoding="utf-8")


def test_ensure_week_opens_once_and_never_overwrites(cfg):
    end = date(2027, 3, 13)
    assert K.ensure_week(cfg, state(), end, date(2027, 3, 8)) is True
    K.week_path(cfg, end).write_text("mine", encoding="utf-8")
    assert K.ensure_week(cfg, state(), end, date(2027, 3, 9)) is False
    assert K.week_path(cfg, end).read_text(encoding="utf-8") == "mine"


# --- nudges ------------------------------------------------------------------

def test_tuesday_adds_no_check_line(cfg):
    run(cfg, "2027-03-09")
    assert nudges(cfg, "check") == []


def test_wednesday_adds_an_m_check_line_at_the_top(cfg):
    run(cfg, "2027-03-10")
    lines = [l for l in cfg.nudges.read_text(encoding="utf-8").splitlines() if l.startswith("- [")]
    assert lines[0].startswith("- [ ] (M) 2027-03-10 Work search check, week ending 2027-03-13: 0 of 3 solid")


def test_runs_are_idempotent(cfg):
    run(cfg, "2027-03-10")
    first = cfg.nudges.read_text(encoding="utf-8")
    run(cfg, "2027-03-10")
    assert cfg.nudges.read_text(encoding="utf-8") == first


def test_friday_raises_and_refreshes_the_check_line(cfg):
    run(cfg, "2027-03-10")
    write_week(cfg, "2027-03-13", [("solid", "x")])
    run(cfg, "2027-03-12")
    (line,) = nudges(cfg, "check")
    assert "(H)" in line and "1 of 3 solid" in line


def test_three_solid_ticks_the_check_line(cfg):
    run(cfg, "2027-03-10")
    write_week(cfg, "2027-03-13", [("solid", "x")] * 3)
    run(cfg, "2027-03-11")
    (line,) = nudges(cfg, "check")
    assert line.startswith("- [x]") and "(auto: 3 solid entries logged)" in line


def test_no_check_line_once_the_week_already_has_three(cfg):
    write_week(cfg, "2027-03-13", [("solid", "x")] * 3)
    run(cfg, "2027-03-10")
    assert nudges(cfg, "check") == []


def test_monday_adds_the_claim_line_and_rolls_up_last_weeks_check(cfg):
    run(cfg, "2027-03-03")
    write_week(cfg, "2027-03-06", [("solid", "x"), ("check. c", "x")])
    run(cfg, "2027-03-08")
    (claim,) = nudges(cfg, "claim")
    assert claim.startswith("- [ ] (H) 2027-03-08 File the ESD weekly claim for the week ending 2027-03-06: 1 of 3 solid, 1 to check")
    (check,) = [l for l in nudges(cfg, "check") if "2027-03-06" in l]
    assert check.startswith("- [x]") and "week closed at" in check


def test_claim_line_catches_up_after_a_missed_monday(cfg):
    write_week(cfg, "2027-03-06", [("solid", "x")])
    run(cfg, "2027-03-10")
    assert len(nudges(cfg, "claim")) == 1


def test_no_claim_line_before_the_claim_has_a_past_week(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 7), claim_start=date(2027, 3, 7))
    run(cfg, "2027-03-08")
    assert nudges(cfg, "claim") == []


def test_no_claim_line_on_sunday(cfg):
    write_week(cfg, "2027-03-06", [("solid", "x")])
    run(cfg, "2027-03-07")
    assert nudges(cfg, "claim") == []


def test_no_claim_line_when_the_claim_is_already_stamped(cfg):
    write_week(cfg, "2027-03-06", [("solid", "x")], claim_filed="2027-03-08")
    run(cfg, "2027-03-09")
    assert nudges(cfg, "claim") == []


def test_ticking_the_claim_line_stamps_claim_filed(cfg):
    p = write_week(cfg, "2027-03-06", [("solid", "x")] * 3)
    run(cfg, "2027-03-08")
    text = cfg.nudges.read_text(encoding="utf-8").replace("- [ ] (H) 2027-03-08 File", "- [x] (H) 2027-03-08 File")
    cfg.nudges.write_text(text.rstrip("\n") + " ✅ 2027-03-09\n", encoding="utf-8")
    run(cfg, "2027-03-09")
    assert "claim_filed: 2027-03-09" in p.read_text(encoding="utf-8")


def test_status_changes_nothing(cfg):
    K.run(cfg, date(2027, 3, 10), status_only=True)
    assert not cfg.nudges.read_text(encoding="utf-8").count("Work search check")
    assert not K.week_path(cfg, date(2027, 3, 13)).exists()


def test_crlf_nudges_stay_crlf(cfg):
    cfg.nudges.write_bytes(K.NUDGES_HEAD.replace("\n", "\r\n").encode("utf-8"))
    run(cfg, "2027-03-10")
    raw = cfg.nudges.read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")


def test_duplicate_lines_collapse_and_a_ticked_copy_wins(cfg):
    run(cfg, "2027-03-10")
    (line,) = nudges(cfg, "check")
    ticked = line.replace("- [ ]", "- [x]", 1)
    cfg.nudges.write_text(cfg.nudges.read_text(encoding="utf-8") + line + "\n" + ticked + "\n", encoding="utf-8")
    run(cfg, "2027-03-10")
    (only,) = nudges(cfg, "check")
    assert only.startswith("- [x]")


# --- the claim period --------------------------------------------------------

def test_no_week_before_the_claim_starts(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1), claim_start=date(2027, 3, 14))
    run(cfg, "2027-03-10")
    assert not K.week_path(cfg, date(2027, 3, 13)).exists()
    assert nudges(cfg, "check") == []


def test_after_the_claim_ends_no_new_weeks_but_the_last_claim_line_stays(cfg):
    cfg.claim_end = date(2027, 3, 13)
    write_week(cfg, "2027-03-13", [("solid", "x")] * 3)
    run(cfg, "2027-03-15")
    assert len(nudges(cfg, "claim")) == 1
    run(cfg, "2027-03-24")
    assert not K.week_path(cfg, date(2027, 3, 20)).exists()
    assert not any("2027-03-27" in l for l in nudges(cfg, "check"))


# --- entries -----------------------------------------------------------------

def test_add_entry_fills_the_first_open_slot(cfg):
    out = K.add_entry(cfg, state(), date(2027, 3, 10), "Employer contact", EMPLOYER_FIELDS, "solid")
    assert out["activity"] == 1 and out["solid"] == 1
    text = K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")
    assert "## Activity 1: Larkspur Analytics · Director of Operations (LA-1)" in text
    assert text.index("**Job title or reference number:**") < text.index("**Employer contact info:**") < text.index("**Fit:** solid")
    assert text.count("(open)") == 2


def test_add_entry_appends_after_the_slots_fill(cfg):
    for _ in range(4):
        out = K.add_entry(cfg, state(), date(2027, 3, 10), "Employer contact", EMPLOYER_FIELDS, "solid")
    assert out["activity"] == 4 and out["solid"] == 4


def test_add_entry_refuses_missing_fields(cfg):
    fields = dict(EMPLOYER_FIELDS)
    del fields["Employer contact info"]
    with pytest.raises(K.ClerkError, match="Employer contact info"):
        K.add_entry(cfg, state(), date(2027, 3, 10), "Employer contact", fields, "solid")


def test_allow_missing_writes_a_blank_and_downgrades_to_check(cfg):
    fields = dict(EMPLOYER_FIELDS)
    del fields["How"]
    out = K.add_entry(cfg, state(), date(2027, 3, 10), "Employer contact", fields, "solid", allow_missing=True)
    assert out["fit"] == "check"
    w = K.parse_week(K.week_path(cfg, date(2027, 3, 13)))
    assert w["missing"] == 1 and w["solid"] == 0


def test_add_entry_refuses_ssn_shaped_numbers(cfg):
    fields = dict(EMPLOYER_FIELDS, Person="ID 123-45-6789")
    with pytest.raises(PerkinsError, match="Social Security"):
        K.add_entry(cfg, state(), date(2027, 3, 10), "Employer contact", fields, "solid")


def test_agents_never_write_no_and_check_needs_a_reason(cfg):
    with pytest.raises(K.ClerkError):
        K.add_entry(cfg, state(), date(2027, 3, 10), "Employer contact", EMPLOYER_FIELDS, "no")
    with pytest.raises(K.ClerkError, match="why"):
        K.add_entry(cfg, state(), date(2027, 3, 10), "Employer contact", EMPLOYER_FIELDS, "check")


def test_add_entry_refuses_dates_outside_the_claim(cfg):
    with pytest.raises(K.ClerkError, match="outside the claim period"):
        K.add_entry(cfg, state(), date(2027, 2, 20), "Employer contact", EMPLOYER_FIELDS, "solid")


def test_unknown_kind_lists_the_real_ones(cfg):
    with pytest.raises(K.ClerkError, match="WorkSource activity"):
        K.add_entry(cfg, state(), date(2027, 3, 10), "Coffee chat", {}, "solid")


def test_entry_in_a_filed_week_warns(cfg):
    write_week(cfg, "2027-03-06", [("solid", "x")], claim_filed="2027-03-08")
    out = K.add_entry(cfg, state(), date(2027, 3, 5), "Employer contact", EMPLOYER_FIELDS, "solid")
    assert "already filed" in out["warning"]


def test_stamp_filed_marks_the_week_and_ticks_the_line(cfg):
    p = write_week(cfg, "2027-03-06", [("solid", "x")] * 3)
    run(cfg, "2027-03-08")
    K.stamp_filed(cfg, date(2027, 3, 6), date(2027, 3, 8))
    assert "claim_filed: 2027-03-08" in p.read_text(encoding="utf-8")
    (line,) = nudges(cfg, "claim")
    assert line.startswith("- [x]") and "✅ 2027-03-08" in line
