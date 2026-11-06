"""Spec 10242: the yellow "potentially counts" grade and the guidance-only headline."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

import run as R
from perkins import claim_log as L
from perkins import clerk as K
from perkins import config as C
from perkins import dashboard as Dash
from perkins import status as S
from helpers import EMPLOYER_FIELDS, claims_home, make_home

ROOT = Path(__file__).resolve().parents[1]
OTHER = {"What activity": "Networking call with a former colleague about open roles",
         "What documentation": "Calendar invite and my notes",
         "Person": "Riley Moss, operations lead", "Result and next step": "Sent my resume; follow up 2027-03-17",
         "Source": "my own account"}
WORKSHOP = {"What activity": "Resume workshop", "What documentation": "Attendance sheet",
            "Office name and city": "WorkSource Tacoma", "Person": "leader not named",
            "Result and next step": "Attended", "Source": "my own account"}


def test_state(tmp_path: Path, monkeypatch, extra: str = "", required: int = 2) -> None:
    """A fictional state "zz" (Washington's file, two a week) in a temporary states folder,
    with its WorkSource kind marked potentially counts unless extra says otherwise."""
    text = (C.STATES_DIR / "wa.toml").read_text(encoding="utf-8")
    text = text.replace('code = "wa"', 'code = "zz"').replace("required = 3", f"required = {required}")
    text = text.replace('name = "WorkSource activity"\nfields = ["Contact date", "Kind", "What activity", "What documentation", "Office name and city"]',
                        'name = "WorkSource activity"\nfields = ["Contact date", "Kind", "What activity", "What documentation", "Office name and city"]\n'
                        + (extra or 'counts = "maybe"\nmaybe_reason = "The test agency\'s pages don\'t say whether workshops count."'))
    states = tmp_path / "states"
    states.mkdir(exist_ok=True)
    (states / "zz.toml").write_text(text, encoding="utf-8")
    monkeypatch.setattr(C, "STATES_DIR", states)


def zz_home(tmp_path: Path, monkeypatch, today=date(2027, 3, 1)) -> C.Config:
    test_state(tmp_path, monkeypatch)
    return make_home(tmp_path / "home", C.CLAIMS, today, state="zz", claim_start=date(2027, 2, 28))


test_state.__test__ = False  # a helper, not a test


# --- the grade ---------------------------------------------------------------

def test_fit_of_reads_maybe_and_still_treats_unknown_words_as_check():
    assert K.fit_of({"Fit": "maybe. The agency's pages don't say."}) == "maybe"
    assert K.fit_of({"Fit": "Maybe."}) == "maybe"
    assert K.fit_of({"Fit": "probably"}) == "check"


def test_agent_writes_maybe_with_a_reason(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    st = C.load_state("wa")
    out = K.add_entry(cfg, st, date(2027, 3, 10), "Other approved activity", OTHER, "maybe",
                      reason="A networking call isn't clearly on ESD's approved list.")
    assert out["fit"] == "maybe"
    w = K.parse_week(K.week_path(cfg, date(2027, 3, 13)))
    assert (w["solid"], w["maybe"], w["check"]) == (0, 1, 0)
    assert "- **Fit:** maybe. A networking call" in K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")


def test_maybe_needs_a_reason_and_a_blank_field_makes_it_check(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    st = C.load_state("wa")
    with pytest.raises(K.ClerkError, match="maybe entry needs one sentence"):
        K.add_entry(cfg, st, date(2027, 3, 10), "Other approved activity", OTHER, "maybe")
    out = K.add_entry(cfg, st, date(2027, 3, 10), "Other approved activity",
                      {k: v for k, v in OTHER.items() if k != "What documentation"}, "maybe",
                      reason="Not clearly approved.", allow_missing=True)
    assert out["fit"] == "check"
    text = K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")
    assert "- **Fit:** check. A required field is blank. Not clearly approved." in text


def test_agents_still_never_write_no(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    with pytest.raises(K.ClerkError, match="solid, maybe, or check"):
        K.add_entry(cfg, C.load_state("wa"), date(2027, 3, 10), "Employer contact", EMPLOYER_FIELDS, "no")


def test_a_maybe_kind_turns_solid_into_maybe_with_its_reason(tmp_path, monkeypatch):
    cfg = zz_home(tmp_path, monkeypatch)
    st = C.load_state("zz")
    out = K.add_entry(cfg, st, date(2027, 3, 10), "WorkSource activity", WORKSHOP, "solid")
    assert out["fit"] == "maybe"
    text = K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")
    assert "- **Fit:** maybe. The test agency's pages don't say whether workshops count." in text
    # The agent's own reason wins on a maybe it marked itself.
    K.add_entry(cfg, st, date(2027, 3, 11), "WorkSource activity", WORKSHOP, "maybe", reason="My own words.")
    assert "- **Fit:** maybe. My own words." in K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")


def test_a_maybe_never_counts_toward_the_minimum(tmp_path, monkeypatch):
    cfg = zz_home(tmp_path, monkeypatch)
    st = C.load_state("zz")
    K.add_entry(cfg, st, date(2027, 3, 8), "Employer contact", EMPLOYER_FIELDS, "solid")
    K.add_entry(cfg, st, date(2027, 3, 9), "WorkSource activity", WORKSHOP, "solid")
    rep = K.run(cfg, date(2027, 3, 11))
    w = K.parse_week(K.week_path(cfg, date(2027, 3, 13)))
    assert (w["solid"], w["maybe"]) == (1, 1)
    assert rep["this_week"]["maybe"] == 1
    phrase = K.counts_phrase(w, 2)
    assert phrase.startswith("1 of 2 solid, 1 potentially counts")
    (check,) = [l for l in cfg.nudges.read_text(encoding="utf-8").splitlines() if K.CHECK_RE.search(l)]
    assert check.startswith("- [ ]") and "1 potentially counts" in check
    html = Dash.build(cfg, date(2027, 3, 12))
    assert "claim good" not in html and "1 potentially counts: get another solid" in html
    page = L.build(cfg, date(2027, 3, 12))
    assert "solid 1 · potentially counts 1 · check 0" in page


def test_recount_adds_maybe_to_an_older_week_file_and_nothing_else(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    p = K.week_path(cfg, date(2027, 3, 13))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\ntype: work-search-log\nweek_ending: 2027-03-13\nsolid: 0\ncheck: 0\nmissing: 0\n"
                 "claim_filed: \"no\"\n---\n\n# Log\n\n## Activity 1: Co\n\n- **Kind:** Employer contact\n"
                 "- **Fit:** solid\n", encoding="utf-8")
    K.recount(p)
    text = p.read_text(encoding="utf-8")
    assert "\nmaybe: 0\n" in text and "\nsolid: 1\n" in text
    assert text.endswith("- **Kind:** Employer contact\n- **Fit:** solid\n")


def test_claim_log_badges(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    st = C.load_state("wa")
    K.add_entry(cfg, st, date(2027, 3, 10), "Other approved activity", OTHER, "maybe", reason="Unclear.")
    K.add_entry(cfg, st, date(2027, 3, 11), "Employer contact", EMPLOYER_FIELDS, "check", reason="Confirm the date.")
    page = L.build(cfg, date(2027, 3, 12))
    assert "<span class='prep badge maybe'>potentially counts</span>" in page
    assert "<span class='prep badge check'>check</span>" in page
    assert ".badge.maybe{background:var(--chk-bg);color:var(--chk-ink)}" in page
    assert ".badge.check,.badge.ungraded{background:var(--warn-bg);color:var(--warn-ink)}" in page


@pytest.mark.parametrize("extra, message", [
    ('counts = "sometimes"', "must be \"yes\" or \"maybe\""),
    ('counts = "maybe"', "no maybe_reason"),
])
def test_a_bad_counts_value_refuses_to_load(tmp_path, monkeypatch, extra, message):
    test_state(tmp_path, monkeypatch, extra=extra)
    with pytest.raises(C.ConfigError, match=message):
        C.load_state("zz")


def test_clerk_add_cli_takes_fit_maybe(tmp_path, capsys):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    args = ["--data", str(cfg.home), "clerk", "add", "--date", "2027-03-10", "--kind", "Other approved activity",
            "--fit", "maybe", "--reason", "Not clearly on the list."]
    for k, v in OTHER.items():
        args += ["--field", f"{k}={v}"]
    assert R.main(args) == 0
    assert '"fit": "maybe"' in capsys.readouterr().out


# --- the guidance-only headline ----------------------------------------------

def test_screens_carry_the_one_line_guidance(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    line = C.guidance_line("ESD")
    assert line == ("Guidance only: ESD's rules can change at any time, take precedence over Perkins, "
                    "and are yours to know and meet.")
    page = L.build(cfg, date(2027, 3, 12))
    assert f"<p class='prep guidance'>{line.replace(chr(39), '&#x27;')}</p>" in page
    assert "Guidance only: ESD&#x27;s rules" in Dash.build(cfg, date(2027, 3, 12))
    text = S.text(S.report(cfg, date(2027, 3, 12)))
    assert line in text.splitlines()


def test_search_mode_screens_have_no_claim_guidance(tmp_path):
    cfg = make_home(tmp_path)
    assert "Guidance only" not in Dash.build(cfg, date(2027, 3, 12))


def test_docs_and_state_files_carry_the_headline():
    for doc in ("docs/state-rules.md", "states/README.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        for phrase in ("can change at any time", "take precedence", "your responsibility"):
            assert phrase in text, (doc, phrase)
    for p in sorted((ROOT / "states").glob("*.toml")):
        header = "".join(re.findall(r"^#.*\n", p.read_text(encoding="utf-8").split("\n\n")[0] + "\n", re.M))
        assert "Guidance only" in header, p.name
