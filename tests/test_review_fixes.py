"""Regression tests for findings from the 0.1.0 review panel (Rookie, Chaos, Hawk, Lens, Beacon, Bolt)."""
from datetime import date

import pytest

import run as R
from perkins import clerk as K
from perkins import config as C
from perkins import dashboard as Dash
from perkins import due as D
from perkins import init as I
from perkins import tracker as T
from perkins.errors import PerkinsError
from helpers import EMPLOYER_FIELDS, claims_home, make_home

WA = C.load_state("wa")


# --- settings ----------------------------------------------------------------

def test_init_never_replaces_an_unreadable_config(tmp_path):
    make_home(tmp_path)
    p = tmp_path / "perkins.toml"
    p.write_text('mode = "search"\ndocs_id = "keep-me"\n[git\n', encoding="utf-8")
    with pytest.raises(C.ConfigError):
        I.init(tmp_path, C.SEARCH, date(2027, 3, 10), pointer=False)
    assert "keep-me" in p.read_text(encoding="utf-8")


def test_string_booleans_are_refused_not_flipped(tmp_path):
    make_home(tmp_path)
    p = tmp_path / "perkins.toml"
    p.write_text(p.read_text(encoding="utf-8").replace("commit = false", 'commit = "false"'), encoding="utf-8")
    with pytest.raises(C.ConfigError, match="git.commit"):
        C.load(tmp_path)


def test_control_characters_are_refused_with_a_fix(tmp_path):
    make_home(tmp_path)
    p = tmp_path / "perkins.toml"
    p.write_text(p.read_text(encoding="utf-8") + 'seniority = ["\\bVP\\b"]\n', encoding="utf-8")
    with pytest.raises(C.ConfigError, match="single quotes"):
        C.load(tmp_path)


def test_render_escapes_control_characters():
    assert "\\u0008" in C._toml_str("a\bb")


def test_claim_end_before_start_is_refused(tmp_path):
    with pytest.raises(C.ConfigError, match="before"):
        claims_home(tmp_path, claim_start=date(2027, 3, 10), claim_end=date(2027, 3, 1))


def test_unknown_time_zone_is_refused(tmp_path):
    with pytest.raises(C.ConfigError, match="time zone"):
        make_home(tmp_path, timezone="America/Los_Angelos")


def test_claims_target_starts_at_the_state_minimum(tmp_path):
    assert claims_home(tmp_path).weekly_target == WA.required


def test_a_file_in_the_way_is_a_clear_error(tmp_path):
    (tmp_path / "blocker").write_text("x", encoding="utf-8")
    with pytest.raises(C.ConfigError, match="is a file"):
        make_home(tmp_path / "blocker")


# --- the claim lifecycle -----------------------------------------------------

def test_mid_claim_setup_opens_the_earlier_weeks(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 24), claim_start=date(2027, 3, 1))
    ends = sorted(p.stem for p in cfg.log_dir.glob("week-ending-*.md"))
    assert ends == ["week-ending-2027-03-06", "week-ending-2027-03-13",
                    "week-ending-2027-03-20", "week-ending-2027-03-27"]


def test_claim_end_keeps_the_last_reminder_until_filed(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 1))
    for _ in range(3):
        K.add_entry(cfg, WA, date(2027, 3, 3), "Employer contact", EMPLOYER_FIELDS, "solid")
    I.init(tmp_path, C.SEARCH, date(2027, 3, 8), claim_end=date(2027, 3, 6), pointer=False)
    cfg = C.load(tmp_path)
    assert not cfg.claims and cfg.claim_records
    items = D.collect(cfg, date(2027, 3, 9), 7)
    assert items[0]["kind"] == "claim" and "2027-03-06" in items[0]["what"]
    K.stamp_filed(cfg, date(2027, 3, 6), date(2027, 3, 9))
    assert not [i for i in D.collect(cfg, date(2027, 3, 9), 7) if i["kind"] == "claim"]


def test_clerk_filed_refuses_loudly_with_no_claim_records(tmp_path, capsys):
    make_home(tmp_path)
    code = R.main(["--data", str(tmp_path), "clerk", "filed", "--week", "2027-03-06"])
    assert code == 2 and "nothing was recorded" in capsys.readouterr().err


def test_a_new_claim_clears_a_stale_claim_end(tmp_path):
    claims_home(tmp_path, today=date(2027, 3, 1))
    I.init(tmp_path, C.SEARCH, date(2027, 3, 20), claim_end=date(2027, 3, 13), pointer=False)
    I.init(tmp_path, C.CLAIMS, date(2027, 5, 3), state="wa", claim_start=date(2027, 5, 2), pointer=False)
    cfg = C.load(tmp_path)
    assert cfg.claim_end is None and (cfg.log_dir / "week-ending-2027-05-08.md").exists()


def test_entry_earlier_in_the_first_claim_week_is_logged(tmp_path):
    # Filed on a Wednesday: the Monday before is in the same claim week, which Perkins asks to fill.
    cfg = claims_home(tmp_path, today=date(2027, 3, 3), claim_start=date(2027, 3, 3))
    K.add_entry(cfg, WA, date(2027, 3, 1), "Employer contact", EMPLOYER_FIELDS, "solid")
    assert K.parse_week(K.week_path(cfg, date(2027, 3, 6)))["solid"] == 1


def test_entry_in_the_week_before_the_claim_is_refused(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 3), claim_start=date(2027, 3, 3))
    with pytest.raises(K.ClerkError, match="outside the claim period"):
        K.add_entry(cfg, WA, date(2027, 2, 27), "Employer contact", EMPLOYER_FIELDS, "solid")
    assert not K.week_path(cfg, date(2027, 2, 27)).exists()


def test_the_last_claim_week_is_a_whole_week_too(tmp_path):
    cfg = claims_home(tmp_path, today=date(2027, 3, 12))
    cfg.claim_end = date(2027, 3, 10)  # a Wednesday
    K.add_entry(cfg, WA, date(2027, 3, 12), "Employer contact", EMPLOYER_FIELDS, "solid")
    assert K.parse_week(K.week_path(cfg, date(2027, 3, 13)))["solid"] == 1
    with pytest.raises(K.ClerkError, match="outside the claim period"):
        K.add_entry(cfg, WA, date(2027, 3, 14), "Employer contact", EMPLOYER_FIELDS, "solid")


def test_a_line_break_cannot_forge_a_heading_in_the_log(tmp_path):
    cfg = claims_home(tmp_path)
    fields = dict(EMPLOYER_FIELDS, Person="Sam\n## Activity 9: fake")
    K.add_entry(cfg, WA, date(2027, 3, 10), "Employer contact", fields, "solid")
    text = K.week_path(cfg, date(2027, 3, 13)).read_text(encoding="utf-8")
    assert "\n## Activity 9" not in text
    assert K.parse_week(K.week_path(cfg, date(2027, 3, 13)))["solid"] == 1


@pytest.mark.parametrize("value", ["SSN 123456789", "social security: 123 45 6789", "claimant ID 4455667", "password: hunter2"])
def test_sensitive_values_are_refused_in_the_log_and_the_tracker(tmp_path, value):
    cfg = claims_home(tmp_path)
    with pytest.raises(PerkinsError):
        K.add_entry(cfg, WA, date(2027, 3, 10), "Employer contact", dict(EMPLOYER_FIELDS, Person=value), "solid")
    code = R.main(["--data", str(tmp_path), "--today", "2027-03-10", "tracker", "add", "Considering",
                   "--set", "Company=Larkspur", "--set", f"Next step={value}"])
    assert code == 2


def test_requisition_numbers_are_not_mistaken_for_ssns(tmp_path):
    cfg = claims_home(tmp_path)
    fields = dict(EMPLOYER_FIELDS, **{"Job title or reference number": "Director (job 260084976)"})
    assert K.add_entry(cfg, WA, date(2027, 3, 10), "Employer contact", fields, "solid")["solid"] == 1


# --- the tracker -------------------------------------------------------------

def tracker_file(tmp_path, body, newline="\n"):
    p = tmp_path / "tracker.md"
    p.write_bytes(body.replace("\n", newline).encode("utf-8"))
    return p


def test_extra_cells_are_kept_not_dropped(tmp_path):
    p = tracker_file(tmp_path, "## Passed\n\n| Date | Company | Why |\n|---|---|---|\n| 2027-03-01 | Acme | too far | really |\n| 2027-03-02 | Beta | pay |\n")
    tr = T.Tracker.load(p)
    tr.update("Passed", 1, {"Why": "pay too low"})
    tr.save()
    assert "too far \\| really" in p.read_text(encoding="utf-8")


def test_a_line_separator_in_a_cell_hides_nothing(tmp_path):
    p = tracker_file(tmp_path, "## Passed\n\n| Date | Company | Why |\n|---|---|---|\n| 2027-03-01 | Acme Labs | x |\n| 2027-03-02 | Beta | y |\n")
    assert len(T.Tracker.load(p).table("Passed").rows) == 2


def test_duplicate_sections_are_refused(tmp_path):
    p = tracker_file(tmp_path, "## Passed\n\n| Date |\n|---|\n| a |\n\n## Passed\n\n| Date |\n|---|\n| b |\n")
    with pytest.raises(T.TrackerError, match="two tables"):
        T.Tracker.load(p)


def test_crlf_trackers_stay_crlf(tmp_path):
    p = tracker_file(tmp_path, "## Passed\n\n| Date | Company |\n|---|---|\n", newline="\r\n")
    tr = T.Tracker.load(p)
    tr.add("Passed", {"Company": "Acme"})
    tr.save()
    raw = p.read_bytes()
    assert b"\r\n" in raw and b"\n" not in raw.replace(b"\r\n", b"")


def test_exact_match_beats_a_partial_one(tmp_path):
    p = tracker_file(tmp_path, "## Passed\n\n| Company |\n|---|\n| Acme Robotics |\n| Acme |\n")
    assert T.Tracker.load(p).find_one("Passed", {"Company": "acme"}) == 1


def test_add_without_a_table_or_values_is_a_clear_error(tmp_path, capsys):
    make_home(tmp_path)
    assert R.main(["--data", str(tmp_path), "tracker", "add", "--set", "Company=Acme"]) == 2
    assert R.main(["--data", str(tmp_path), "tracker", "add", "Submitted"]) == 2
    err = capsys.readouterr().err
    assert "needs a table name" in err and "Nothing to add" in err


def test_a_non_utf8_tracker_is_a_clear_error(tmp_path):
    p = tmp_path / "tracker.md"
    p.write_bytes(b"## Passed\n\n| Company |\n|---|\n| Caf\xe9 |\n")
    with pytest.raises(T.TrackerError, match="UTF-8"):
        T.Tracker.load(p)


# --- due, status, and the dashboard ------------------------------------------

def test_unreadable_dates_are_flagged_not_dropped(tmp_path):
    cfg = make_home(tmp_path)
    tr = T.Tracker.load(cfg.tracker)
    tr.add(T.SUBMITTED, {"Company": "Kestrel Energy", "Next follow-up": "Nov 12"})
    tr.save()
    (item,) = D.collect(cfg, date(2027, 3, 10), 7)
    assert item["kind"] == "unreadable date" and "Nov 12" in item["detail"]


def test_due_days_are_bounded(tmp_path, capsys):
    make_home(tmp_path)
    with pytest.raises(SystemExit):
        R.main(["--data", str(tmp_path), "due", "--days", "1000000000"])


def test_due_labels_read_naturally():
    today = date(2027, 3, 10)
    item = {"kind": "follow-up", "overdue": False}
    assert D.label({**item, "date": "2027-03-11"}, today) == "tomorrow"
    assert D.label({**item, "date": "2027-03-13"}, today) == "in 3 days"


def test_dashboard_links_keep_query_strings_and_cells_say_overdue(tmp_path):
    cfg = make_home(tmp_path)
    tr = T.Tracker.load(cfg.tracker)
    tr.add(T.SUBMITTED, {"Company": "Larkspur Analytics", "Role": "[Director](https://jobs.example.com/x?a=1&b=2)",
                         "Next follow-up": "2027-03-01"})
    tr.save()
    html = Dash.build(cfg, date(2027, 3, 10))
    assert 'href="https://jobs.example.com/x?a=1&amp;b=2"' in html
    assert "<span class='tag'>overdue</span>" in html
    assert "tabindex='0' role='region'" in html


def test_claim_panel_says_what_is_left(tmp_path):
    cfg = claims_home(tmp_path)
    K.add_entry(cfg, WA, date(2027, 3, 10), "Employer contact", EMPLOYER_FIELDS, "solid")
    html = Dash.build(cfg, date(2027, 3, 12))
    assert "2 more solid activities needed by Saturday 2027-03-13" in html
    assert "<strong>Solid</strong> means" in html


def test_compare_needs_no_data_folder(tmp_path, capsys):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_text("x\n", encoding="utf-8")
    b.write_text("x\r\n", encoding="utf-8")
    assert R.main(["--data", str(tmp_path / "none"), "sync-check", "--compare", str(a), str(b)]) == 0


# --- the privacy check and the network guard ----------------------------------

from perkins import pii_check as P  # noqa: E402
from perkins.feeds import http as H  # noqa: E402


def test_pii_reads_utf16_and_fails_closed(tmp_path):
    (tmp_path / "a.txt").write_bytes("mail jane.doe@mailhost.co\n".encode("utf-16"))
    assert any("email" in h for h in P.scan_tree(tmp_path, [], []))
    with pytest.raises(P.PiiError):
        P.load_list(tmp_path / "no-such-blocklist.txt", required=True)


def test_pii_short_allow_entries_hide_nothing(tmp_path):
    (tmp_path / "a.txt").write_text("Jane Doe at jane.doe@mailhost.co\n", encoding="utf-8")
    hits = P.scan_tree(tmp_path, ["jane doe"], ["Jane", "org"])
    assert any("blocklisted" in h for h in hits) and any("email" in h for h in hits)


def test_pii_masks_ssn_output_and_finds_tokens(tmp_path):
    (tmp_path / "a.txt").write_text("123-45-6789 and ghp_" + "a" * 36 + "\n", encoding="utf-8")
    hits = "\n".join(P.scan_tree(tmp_path, [], []))
    assert "123-**-****" in hits and "6789" not in hits and "key or token" in hits


@pytest.mark.parametrize("url", ["http://127.0.0.1/x", "http://localhost/x", "http://169.254.169.254/latest",
                                 "http://10.0.0.5/", "file:///c:/secret.txt", "ftp://example.com/x"])
def test_fetches_refuse_local_and_odd_addresses(url):
    with pytest.raises(H.FeedError):
        H.check_url(url)
