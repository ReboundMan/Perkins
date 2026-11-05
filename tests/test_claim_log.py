"""The claim log page: claims tracking only, weeks collapsed and newest first, the meeting view
by default, artifact links that resolve, embedded screenshots, and the initials favicon."""
from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import run as R
from perkins import claim_log as L
from perkins import clerk as K
from perkins import config as C
from perkins import dashboard as Dash
from perkins import favicon as F
from helpers import EMPLOYER_FIELDS, claims_home, make_home

FOLDER = "2027-03-02-larkspur-analytics-director-of-operations"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def logged(tmp: Path) -> C.Config:
    """A claim with two weeks: three solid applications, then one blank-field check entry."""
    cfg = claims_home(tmp, today=date(2027, 3, 1))
    (cfg.master).write_text("# Jordan Avery\n\nPortland, OR\n", encoding="utf-8")
    st = C.load_state("wa")
    app = cfg.applications / FOLDER
    app.mkdir(parents=True)
    (app / "resume.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    (app / "cover-letter.pdf").write_bytes(b"%PDF-1.4\n%%EOF\n")
    cfg.evidence_dir.mkdir(parents=True, exist_ok=True)
    (cfg.evidence_dir / "2027-03-03-larkspur-application.png").write_bytes(PNG)
    first = {**EMPLOYER_FIELDS,
             "Result and next step": "Applied with a tailored resume and cover letter. "
                                     "Screenshot: log/evidence/2027-03-03-larkspur-application.png"}
    K.add_entry(cfg, st, date(2027, 3, 3), "Employer contact", first, "solid")
    K.add_entry(cfg, st, date(2027, 3, 4), "Employer contact",
                {**EMPLOYER_FIELDS, "Employer or business name": "Kestrel Energy",
                 "Job title or reference number": "Head of Customer Success"}, "solid")
    K.add_entry(cfg, st, date(2027, 3, 5), "Employer contact",
                {**EMPLOYER_FIELDS, "Type": "Inquiry", "Source": "my own account"}, "solid")
    K.stamp_filed(cfg, date(2027, 3, 6), date(2027, 3, 8))
    K.add_entry(cfg, st, date(2027, 3, 9), "Employer contact",
                {k: v for k, v in EMPLOYER_FIELDS.items() if k != "Employer contact info"},
                "check", reason="The posting gave no location.", allow_missing=True)
    return cfg


class Views(HTMLParser):
    """Collects text by whether it sits inside an element with the 'prep' class (prep notes only)
    or a 'meet' one (meeting view only)."""

    VOID = {"br", "img", "meta", "link", "input", "hr"}

    def __init__(self):
        super().__init__()
        self.stack: list[set[str]] = []
        self.prep_text, self.shared_text = [], []

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            return
        self.stack.append(set((dict(attrs).get("class") or "").split()))

    def handle_endtag(self, tag):
        if tag not in self.VOID and self.stack:
            self.stack.pop()

    def handle_data(self, data):
        classes = set().union(*self.stack) if self.stack else set()
        (self.prep_text if "prep" in classes else self.shared_text).append(data)


def views(page: str) -> tuple[str, str]:
    body = page[page.index("<main>"):page.index("</main>")]
    v = Views()
    v.feed(body)
    return " ".join(v.shared_text), " ".join(v.prep_text)


# --- mode gating -------------------------------------------------------------

def test_search_mode_builds_no_claim_log(tmp_path, capsys):
    cfg = make_home(tmp_path)
    Dash.write(cfg, date(2027, 3, 10))
    assert not cfg.claim_log.exists()
    assert "claim-log.html" not in cfg.dashboard.read_text(encoding="utf-8")
    assert R.main(["--data", str(tmp_path), "--today", "2027-03-10", "claim-log"]) == 0
    assert "no claim log page" in capsys.readouterr().out
    assert not cfg.claim_log.exists()


def test_claims_mode_builds_it_with_the_dashboard_and_links_both_ways(tmp_path):
    cfg = logged(tmp_path)
    Dash.write(cfg, date(2027, 3, 12))
    assert cfg.claim_log.exists()
    assert "href='claim-log.html'" in cfg.dashboard.read_text(encoding="utf-8")
    assert "href='dashboard.html'" in cfg.claim_log.read_text(encoding="utf-8")


def test_an_ended_claims_log_keeps_its_page_after_switching_to_search(tmp_path):
    cfg = logged(tmp_path)
    cfg.mode, cfg.claim_end = C.SEARCH, date(2027, 3, 13)
    C.save(cfg)
    cfg = C.load(tmp_path)
    assert cfg.claim_records
    Dash.write(cfg, date(2027, 3, 20))
    page = cfg.claim_log.read_text(encoding="utf-8")
    assert "ended 2027-03-13" in page


def test_the_command_rebuilds_the_page(tmp_path, capsys):
    logged(tmp_path)
    assert R.main(["--data", str(tmp_path), "--today", "2027-03-12", "claim-log"]) == 0
    assert "claim-log.html" in capsys.readouterr().out


# --- weeks -------------------------------------------------------------------

def test_weeks_are_collapsed_and_newest_first(tmp_path):
    cfg = logged(tmp_path)
    page = L.build(cfg, date(2027, 3, 12))
    tags = re.findall(r"<details[^>]*>", page)
    assert len(tags) == 2 and not any(" open" in t for t in tags)
    assert page.index("id='w2027-03-13'") < page.index("id='w2027-03-06'")
    assert "Expand all" in page and "beforeprint" in page


def test_week_headers_show_counts_and_claim_status(tmp_path):
    cfg = logged(tmp_path)
    page = L.build(cfg, date(2027, 3, 12))
    assert "<span class='cnt'>3 of 3 activities</span>" in page
    assert "<span class='cnt short'>1 of 3 activities</span>" in page
    assert "Claim filed: 2027-03-08" in page
    assert "Claim filed: Not yet (file on or after Sunday 2027-03-14)" in page
    later = L.build(cfg, date(2027, 3, 16))
    assert "Claim filed: Not recorded" in later


def test_header_cards_and_name(tmp_path):
    cfg = logged(tmp_path)
    shared, _ = views(L.build(cfg, date(2027, 3, 12)))
    assert "Jordan Avery" in shared and "Employment Security Department" in shared
    assert "claim started Sunday 2027-02-28" in shared and "Built 2027-03-12" in shared
    cards = re.findall(r"<div class='n'>(\d+)</div><div class='l'>([^<]+)</div>", L.build(cfg, date(2027, 3, 12)))
    assert dict((label, int(n)) for n, label in cards) == {"Claim weeks": 2, "Activities logged": 4, "Applications": 3}


# --- the two views -----------------------------------------------------------

def test_prep_notes_are_hidden_by_default(tmp_path):
    cfg = logged(tmp_path)
    page = L.build(cfg, date(2027, 3, 12))
    assert "<body><main>" in page and "localStorage" not in page
    assert "aria-pressed='false'>Show prep notes" in page
    assert "body:not(.show-prep) .prep{display:none}" in page
    shared, prep = views(page)
    assert "Not recorded" in shared
    assert "MISSING" not in shared and "MISSING" in prep
    assert "The posting gave no location." in prep and "The posting gave no location." not in shared
    assert "my own account" in prep and "my own account" not in shared  # Source is a prep note
    assert "solid 3" in prep


def test_meeting_view_strips_working_notes_but_keeps_the_record():
    assert L.meeting_value("Reno, NV · https://x.example.com · MISSING: phone needed") == "Reno, NV · https://x.example.com"
    assert L.meeting_value("Applied (MISSING: req id needed); awaiting") == "Applied; awaiting"
    assert L.meeting_value("Applied. Screenshot: log/evidence/a.png") == "Applied."


# --- artifacts ---------------------------------------------------------------

def hrefs(page: str) -> list[str]:
    return [unquote(h) for h in re.findall(r"class='btn' href=\"([^\"]+)\"", page)]


def test_artifact_links_resolve(tmp_path):
    cfg = logged(tmp_path)
    page = L.build(cfg, date(2027, 3, 12))
    local = [h for h in hrefs(page) if not h.startswith("http")]
    assert f"applications/{FOLDER}/resume.pdf" in local
    assert f"applications/{FOLDER}/cover-letter.pdf" in local
    for h in local:
        assert (cfg.home / h).is_file(), h
    assert "https://jobs.example.com/la" in hrefs(page)
    # The Kestrel application has no folder, and the inquiry isn't an application: no resume link.
    assert local.count(f"applications/{FOLDER}/resume.pdf") == 2  # Larkspur in both weeks


def test_cover_letter_only_when_the_log_says_it_went(tmp_path):
    assert L.cover_letter_sent("Applied with a tailored resume and cover letter")
    assert not L.cover_letter_sent("Applied with a tailored resume")
    assert not L.cover_letter_sent("Applied without a cover letter")
    assert not L.cover_letter_sent("Applied; cover letter skipped")


def test_a_different_role_at_the_same_company_links_nothing(tmp_path):
    cfg = logged(tmp_path)
    folders = L.app_folders(cfg)
    fields = {**EMPLOYER_FIELDS, "Contact date": "2027-03-09", "Job title or reference number": "VP of Finance (LA-9)"}
    assert L.match_folder(cfg, fields, folders) is None
    assert L.match_folder(cfg, {**fields, "Contact date": "2027-03-01"}, folders) is None  # before the resume existed
    named = {**fields, "Source": f"https://jobs.example.com/la · applications/{FOLDER}"}
    assert L.match_folder(cfg, named, folders) == FOLDER  # a path in the entry wins


def test_docs_copy_link_only_when_configured(tmp_path):
    cfg = logged(tmp_path)
    assert "Resume in Claude Docs" not in L.build(cfg, date(2027, 3, 12))
    cfg.docs_mirror, cfg.docs_id = True, "sampledoc"
    page = L.build(cfg, date(2027, 3, 12))
    assert "Resume in Claude Docs" in page and "artifact/" + "sampledoc" in page
    cfg.docs_id = "bad id\"><script>"
    assert L.docs_url(cfg) == ""


# --- evidence ----------------------------------------------------------------

def test_evidence_is_embedded(tmp_path):
    cfg = logged(tmp_path)
    page = L.build(cfg, date(2027, 3, 12))
    assert page.count("data:image/png;base64,") == 1
    assert "aria-label='Enlarge 2027-03-03-larkspur-application.png'" in page
    assert "id='lb'" in page and "hidden" in page


def test_evidence_outside_the_evidence_folder_is_never_read(tmp_path):
    cfg = logged(tmp_path)
    assert "not found" in L.evidence_html(cfg, "log/evidence/../../perkins.toml")
    assert "not found" in L.evidence_html(cfg, "log/evidence/missing.png")
    assert "base64" not in L.evidence_html(cfg, "log/evidence/../../perkins.toml")


def test_field_text_is_escaped(tmp_path):
    cfg = logged(tmp_path)
    st = C.load_state("wa")
    K.add_entry(cfg, st, date(2027, 3, 10), "Employer contact",
                {**EMPLOYER_FIELDS, "Person": "<script>alert(1)</script>"}, "solid")
    page = L.build(cfg, date(2027, 3, 12))
    assert "<script>alert(1)" not in page and "&lt;script&gt;alert(1)" in page


# --- favicon -----------------------------------------------------------------

def test_initials_from_the_master_heading():
    assert F.initials("Jordan Avery") == "JA"
    assert F.initials("Mary-Jane O'Neil, PMP") == "MO"
    assert F.initials("Zoë Quinn Jr.") == "ZQ"
    assert F.initials("Cher") == "C"
    assert F.initials("") == "P" and F.initials("12345") == "P"


def test_both_pages_carry_the_favicon(tmp_path):
    cfg = logged(tmp_path)
    Dash.write(cfg, date(2027, 3, 12))
    for page in (cfg.dashboard, cfg.claim_log):
        text = page.read_text(encoding="utf-8")
        assert "<link rel='icon' type='image/svg+xml' href='data:image/svg+xml," in text
    svg = F.svg("JA")
    assert svg.count("<path") == 2 and F.ACCENT in svg and "<text" not in svg


def test_favicon_falls_back_to_p_without_a_name(tmp_path):
    cfg = make_home(tmp_path)
    cfg.master.write_text("No heading here\n", encoding="utf-8")
    assert F.initials(F.name_from_master(cfg.master)) == "P"
    assert F.svg("") == F.svg("P")
