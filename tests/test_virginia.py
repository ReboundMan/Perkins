"""Spec 10241: Virginia as the second state."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from perkins import claim_log as L
from perkins import clerk as K
from perkins import config as C
from perkins import dashboard as Dash
from perkins import status as S
from helpers import VA_EMPLOYER_FIELDS, claims_home

ROOT = Path(__file__).resolve().parents[1]
EMPLOYER = ["Contact date", "Kind", "Employer or business name", "Employer address", "Employer email or website",
            "Type of work or position", "Person", "Employer phone or fax", "Type of contact", "Result and next step"]
WORKFORCE = ["Contact date", "Kind", "What activity", "Office name and city", "Person"]
WORKSHOP = {"What activity": "Resume workshop", "Office name and city": "Example Workforce Center, Richmond",
            "Person": "leader not named", "Result and next step": "Attended", "Source": "my own account"}


def va_home(tmp_path, today=date(2027, 3, 1)):
    return claims_home(tmp_path, today=today, state="va")


def nudge_lines(cfg, rx):
    return [l for l in cfg.nudges.read_text(encoding="utf-8").splitlines() if rx.search(l)]


def test_va_rules():
    va = C.load_state("va")
    assert (va.name, va.agency, va.required) == ("Virginia", "VEC", 2)
    assert C.WEEKDAYS[va.week_start] == "sunday" and C.WEEKDAYS[va.week_end] == "saturday"
    assert K.claim_offset(va) == 1
    assert [k["name"] for k in va.kinds] == ["Employer contact", "Workforce center activity"]
    assert va.kinds[0]["fields"] == EMPLOYER and va.kinds[1]["fields"] == WORKFORCE
    assert va.kinds[1]["counts"] == "maybe" and va.kinds[1]["maybe_reason"]
    assert all(s.startswith(("https://www.vec.virginia.gov/", "https://law.lis.virginia.gov/")) for s in va.sources)


def test_setup_raises_the_weekly_target_to_two(tmp_path):
    cfg = va_home(tmp_path)
    assert cfg.state == "va" and cfg.weekly_target == 2


def test_virginia_rhythm(tmp_path):
    cfg = va_home(tmp_path)
    K.run(cfg, date(2027, 3, 6))  # Saturday, the first week's last day
    assert not nudge_lines(cfg, K.CLAIM_RE)
    assert K.week_path(cfg, date(2027, 3, 6)).exists()
    K.run(cfg, date(2027, 3, 7))  # Sunday: the claim line for the week that just ended
    (claim,) = nudge_lines(cfg, K.CLAIM_RE)
    assert claim.startswith("- [ ] (H) 2027-03-07 File the VEC weekly claim for the week ending 2027-03-06: 0 of 2 solid")
    assert not [l for l in nudge_lines(cfg, K.CHECK_RE) if "2027-03-13" in l]
    K.run(cfg, date(2027, 3, 10))  # Wednesday: the midweek check, medium
    (check,) = [l for l in nudge_lines(cfg, K.CHECK_RE) if "2027-03-13" in l]
    assert check.startswith("- [ ] (M) 2027-03-10 Work search check, week ending 2027-03-13: 0 of 2 solid")
    K.run(cfg, date(2027, 3, 12))  # Friday: raised to high
    (check,) = [l for l in nudge_lines(cfg, K.CHECK_RE) if "2027-03-13" in l]
    assert check.startswith("- [ ] (H) 2027-03-10")
    assert sorted(p.name for p in cfg.log_dir.glob("week-ending-*.md")) == [
        "week-ending-2027-03-06.md", "week-ending-2027-03-13.md"]
    assert "required: 2" in K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")


def test_employer_contact_follows_the_handbook_log_order(tmp_path):
    cfg = va_home(tmp_path)
    va = C.load_state("va")
    out = K.add_entry(cfg, va, date(2027, 3, 10), "Employer contact", VA_EMPLOYER_FIELDS, "solid")
    assert out["fit"] == "solid" and out["required"] == 2
    text = K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")
    names = re.findall(r"^- \*\*(.+?):\*\*", text, re.M)
    assert names == EMPLOYER + ["Source", "Fit"]
    assert "## Activity 1: Kestrel Energy · Operations Manager (KE-7)" in text


def test_a_missing_virginia_field_refuses(tmp_path):
    cfg = va_home(tmp_path)
    fields = {k: v for k, v in VA_EMPLOYER_FIELDS.items() if k != "Type of contact"}
    with pytest.raises(K.ClerkError, match="Missing fields: Type of contact"):
        K.add_entry(cfg, C.load_state("va"), date(2027, 3, 10), "Employer contact", fields, "solid")


def test_workforce_center_activity_is_always_potentially_counts(tmp_path):
    cfg = va_home(tmp_path)
    out = K.add_entry(cfg, C.load_state("va"), date(2027, 3, 10), "Workforce center activity", WORKSHOP, "solid")
    assert out["fit"] == "maybe"
    text = K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")
    assert "## Activity 1: Resume workshop" in text
    assert "- **Fit:** maybe. VEC's handbook counts reemployment services at a workforce center" in text
    w = K.parse_week(K.week_path(cfg, date(2027, 3, 13)))
    assert (w["solid"], w["maybe"]) == (0, 1)


def test_washington_kinds_are_refused_in_virginia(tmp_path):
    cfg = va_home(tmp_path)
    with pytest.raises(K.ClerkError, match="Employer contact, Workforce center activity"):
        K.add_entry(cfg, C.load_state("va"), date(2027, 3, 10), "Other approved activity", WORKSHOP, "solid")


def test_virginia_screens_carry_the_guidance_with_vec(tmp_path):
    cfg = va_home(tmp_path)
    K.add_entry(cfg, C.load_state("va"), date(2027, 3, 10), "Employer contact", VA_EMPLOYER_FIELDS, "solid")
    day = date(2027, 3, 12)
    assert "Guidance only: VEC&#x27;s rules can change at any time" in L.build(cfg, day)
    assert "Guidance only: VEC&#x27;s rules can change at any time" in Dash.build(cfg, day)
    assert C.guidance_line("VEC") in S.text(S.report(cfg, day)).splitlines()
    assert "VEC minimum 2" in Dash.build(cfg, day)


@pytest.mark.parametrize("code, heading", [("wa", "Washington (`states/wa.toml`):"),
                                           ("va", "Virginia (`states/va.toml`):")])
def test_each_tailor_example_uses_exactly_its_states_fields(code, heading):
    text = (ROOT / "skills/tailor/SKILL.md").read_text(encoding="utf-8")
    block = text.split(heading, 1)[1].split("```", 2)[1]
    used = set(re.findall(r'--field "([^="]+)=', block))
    (kind,) = [k for k in C.load_state(code).kinds if k["name"] == "Employer contact"]
    expected = (set(kind["fields"]) - {"Contact date", "Kind"}) | set(K.EXTRA_FIELDS)
    assert used == expected, (sorted(used - expected), sorted(expected - used))


def test_claim_log_counts_and_links_a_virginia_application(tmp_path):
    cfg = va_home(tmp_path)
    folder = cfg.applications / "2027-03-09-kestrel-energy-operations-manager"
    folder.mkdir(parents=True)
    (folder / "resume.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    va = C.load_state("va")
    K.add_entry(cfg, va, date(2027, 3, 10), "Employer contact", VA_EMPLOYER_FIELDS, "solid")  # no folder in Source
    K.add_entry(cfg, va, date(2027, 3, 11), "Workforce center activity", WORKSHOP, "solid")
    page = L.build(cfg, date(2027, 3, 12))
    assert "<div class='n'>1</div><div class='l'>Applications</div>" in page
    assert "applications/2027-03-09-kestrel-energy-operations-manager/resume.pdf" in page
