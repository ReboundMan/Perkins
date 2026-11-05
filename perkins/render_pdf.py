"""Render a resume's Markdown to a print-ready Letter PDF with a Chromium browser's
headless print (Edge, Chrome, or Chromium), on Windows, macOS, or Linux.

Set PERKINS_BROWSER to a browser executable to choose one. Needs the `markdown` package.
CLI: pdf FILE.md [FILE.md ...] [--max-pages 2]
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from .errors import PerkinsError

CSS = """
@page { size: Letter; margin: 0.5in 0.6in; }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", "Helvetica Neue", Helvetica, Arial, "Liberation Sans", sans-serif;
       font-size: 10.5pt; line-height: 1.3; color: #1b1f24; margin: 0; }
h1 { font-size: 22pt; margin: 0 0 2pt; letter-spacing: 0.5pt; color: #13283f; }
h1 + p { font-size: 9.5pt; color: #4a5560; margin: 0 0 5pt; }
h1 + p + p { font-size: 11pt; color: #1f4e79; margin: 0 0 6pt; }
h2 { font-size: 11pt; text-transform: uppercase; letter-spacing: 1.2pt; color: #1f4e79;
     border-bottom: 1px solid #c3cfdb; padding-bottom: 2pt; margin: 11pt 0 5pt; break-after: avoid; }
h3 { font-size: 10.5pt; color: #13283f; margin: 8pt 0 3pt; break-after: avoid; }
p { margin: 0 0 5pt; }
ul { margin: 0 0 5pt; padding-left: 14pt; }
li { margin: 0 0 2.5pt; break-inside: avoid; }
strong { color: #13283f; }
a { color: inherit; text-decoration: none; }
"""

PAGE_RE = re.compile(rb"/Type\s*/Page(?![a-zA-Z])")


class PdfError(PerkinsError):
    """No browser, no markdown package, or the browser produced no PDF."""


def candidates() -> list[str]:
    system = platform.system()
    if system == "Windows":
        roots = [os.environ.get(k, "") for k in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA")]
        rels = [r"Microsoft\Edge\Application\msedge.exe", r"Google\Chrome\Application\chrome.exe",
                r"Chromium\Application\chrome.exe"]
        return [str(Path(r) / rel) for r in roots if r for rel in rels]
    if system == "Darwin":
        return ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
                "/Applications/Chromium.app/Contents/MacOS/Chromium"]
    return [w for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                        "microsoft-edge", "microsoft-edge-stable") if (w := shutil.which(n))]


def find_browser() -> str:
    env = os.environ.get("PERKINS_BROWSER", "").strip()
    if env:
        if Path(env).exists() or shutil.which(env):
            return env
        raise PdfError(f"PERKINS_BROWSER is set to {env!r}, which doesn't exist.")
    tried = candidates()
    for c in tried:
        if Path(c).exists():
            return c
    raise PdfError("No Chromium browser found (Edge, Chrome, or Chromium). Install one, or set "
                   "PERKINS_BROWSER to its path. Looked in: " + ("; ".join(tried) or "PATH"))


def count_pages(pdf: Path) -> int:
    return len(PAGE_RE.findall(pdf.read_bytes()))


def to_html(md_text: str, title: str) -> str:
    try:
        import markdown
    except ImportError as e:
        raise PdfError("The markdown package is missing: run  pip install markdown") from e
    # A tailored resume is written from posting text, which is untrusted. Raw HTML in it is
    # shown as text, never run, and the page may load nothing: no scripts, frames, or images
    # from anywhere, and no local files.
    md = markdown.Markdown(extensions=["extra"])
    md.preprocessors.deregister("html_block")
    md.inlinePatterns.deregister("html")
    body = md.convert(md_text)
    from html import escape
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; img-src data:\">"
            f"<title>{escape(title)}</title><style>{CSS}</style></head><body>{body}</body></html>")


def render(md_path: Path, browser: str | None = None) -> Path:
    md_path = Path(md_path).resolve()
    html = to_html(md_path.read_text(encoding="utf-8"), md_path.stem)
    pdf_path = md_path.with_suffix(".pdf")
    work = Path(tempfile.mkdtemp(prefix="perkins-pdf-"))
    try:
        html_path = work / "resume.html"
        html_path.write_text(html, encoding="utf-8")
        if pdf_path.exists():
            pdf_path.unlink()
        exe = browser or find_browser()
        try:
            subprocess.run([exe, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                            f"--user-data-dir={work / 'profile'}", f"--print-to-pdf={pdf_path}",
                            html_path.as_uri()], check=True, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as e:
            raise PdfError(f"The browser took more than two minutes printing {md_path.name}; try again.") from e
        except (subprocess.CalledProcessError, OSError) as e:
            raise PdfError(f"The browser couldn't print {md_path.name}: {e}") from e
        # Some browsers hand the print to a child process and return before the file lands,
        # so wait until the file exists and its size stops changing.
        last = -1
        for _ in range(120):
            size = pdf_path.stat().st_size if pdf_path.exists() else 0
            if size > 0 and size == last and pdf_path.read_bytes().rstrip().endswith(b"%%EOF"):
                return pdf_path
            last = size
            time.sleep(0.25)
        raise PdfError(f"The browser produced no PDF for {md_path.name}.")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def add_arguments(p) -> None:
    p.add_argument("files", nargs="+", help="Markdown files to render")
    p.add_argument("--max-pages", type=int, default=2, help="exit 1 when a PDF runs over this many pages (default 2)")


def cli(args, cfg=None, today=None) -> int:
    worst = 0
    for f in args.files:
        pdf = render(Path(f))
        pages = count_pages(pdf)
        over = pages > args.max_pages
        worst = max(worst, 1 if over else 0)
        print(json.dumps({"pdf": str(pdf), "bytes": pdf.stat().st_size, "pages": pages,
                          "over_limit": over}, ensure_ascii=False))
    return worst
