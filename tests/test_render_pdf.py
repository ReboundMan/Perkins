from pathlib import Path

import pytest

from perkins import render_pdf as R

ROOT = Path(__file__).resolve().parents[1]


def test_count_pages_ignores_the_pages_tree(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4\n<< /Type /Pages /Count 2 >>\n<< /Type /Page >>\n<< /Type/Page >>\n")
    assert R.count_pages(p) == 2


def test_browser_override_must_exist(monkeypatch):
    monkeypatch.setenv("PERKINS_BROWSER", "/no/such/browser")
    with pytest.raises(R.PdfError, match="PERKINS_BROWSER"):
        R.find_browser()


def test_no_browser_says_where_it_looked(monkeypatch):
    monkeypatch.delenv("PERKINS_BROWSER", raising=False)
    monkeypatch.setattr(R, "candidates", lambda: ["/nowhere/chrome"])
    with pytest.raises(R.PdfError, match="/nowhere/chrome"):
        R.find_browser()


def test_raw_html_in_a_resume_is_shown_not_run():
    html = R.to_html("Text <script>alert(1)</script> <iframe src=x></iframe>", "t")
    assert "<script>" not in html and "<iframe" not in html and "&lt;script&gt;" in html


def test_html_has_the_resume_and_no_remote_assets():
    html = R.to_html("# Jordan Avery\n\n- A bullet", "Jordan")
    head = html.split("<body>")[0]
    assert "<h1>Jordan Avery</h1>" in html and "https://" not in head and "Content-Security-Policy" in head


def test_real_render_fits_two_pages(tmp_path):
    try:
        R.find_browser()
    except R.PdfError:
        pytest.skip("no Chromium browser on this machine")
    md = tmp_path / "resume.md"
    md.write_text((ROOT / "examples" / "sample-tailored-resume.md").read_text(encoding="utf-8"), encoding="utf-8")
    pdf = R.render(md)
    assert pdf.exists() and 1 <= R.count_pages(pdf) <= 2
