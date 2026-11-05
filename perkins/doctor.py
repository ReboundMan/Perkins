"""Check this computer has what Perkins needs, and say how to fix anything missing, in plain words.

CLI: doctor [--json]
Exit 0 when everything required is present, 1 when something required is missing.
"""
from __future__ import annotations

import json
import platform
import sys

from . import config as C


def checks(home=None) -> list[dict]:
    out = []

    def add(name, ok, required, fix=""):
        out.append({"check": name, "ok": ok, "required": required, "fix": "" if ok else fix})

    v = sys.version_info
    add(f"Python 3.11 or later (found {v.major}.{v.minor})", v >= (3, 11), True,
        "Install the latest Python from python.org, then open a new terminal and run setup again.")
    try:
        import markdown  # noqa: F401
        has_md = True
    except ImportError:
        has_md = False
    add("The markdown package (for PDFs)", has_md, True, "Run: pip install markdown")
    if platform.system() == "Windows":
        try:
            import tzdata  # noqa: F401
            has_tz = True
        except ImportError:
            has_tz = False
        add("Time zone data (Windows)", has_tz, False, "Run: pip install tzdata")
    from . import render_pdf
    try:
        browser = render_pdf.find_browser()
        add(f"A browser for printing PDFs ({browser})", True, True)
    except render_pdf.PdfError:
        add("A browser for printing PDFs (Edge, Chrome, or Chromium)", False, True,
            "Install Microsoft Edge or Google Chrome. If one is installed somewhere unusual, set "
            "PERKINS_BROWSER to its full path.")
    found = C.find_home(home)
    if (found / C.CONFIG_NAME).is_file():
        try:
            cfg = C.load(found)
            add(f"Your data folder ({found}, {cfg.mode_name})", True, False)
        except C.ConfigError as e:
            add(f"Your data folder ({found})", False, True, f"perkins.toml has a problem: {e}")
    else:
        add("Your data folder", False, False, "Not set up yet: run setup (say \"set up Perkins\").")
    return out


def add_arguments(p) -> None:
    p.add_argument("--json", action="store_true")


def cli(args, cfg=None, today=None) -> int:
    results = checks(getattr(args, "data", None))
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            mark = "ok  " if r["ok"] else ("MISSING" if r["required"] else "note")
            print(f"{mark:<8}{r['check']}" + (f"\n        {r['fix']}" if r["fix"] else ""))
    return 0 if all(r["ok"] or not r["required"] for r in results) else 1
