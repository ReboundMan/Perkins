"""Perkins command line. The skills run everything through this one file.

  python run.py [--data DIR] [--today YYYY-MM-DD] <command> [options]

Commands: init, doctor, states, status, due, dashboard, tracker, clerk, pdf, posting, scan,
sync-check, pii-check, version. Run any command with -h for its options.

Commands that change the tracker or the log rebuild dashboard.html afterwards, and status runs
the claims clerk and rebuilds the dashboard before it reports, so what it shows is current.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from perkins import __version__  # noqa: E402
from perkins import config as C  # noqa: E402
from perkins.errors import PerkinsError  # noqa: E402

# command: (module, data folder: "required" / "optional" / "none", refresh: "before" / "after" / "")
#   refresh "before": run the clerk and rebuild the dashboard, then the command (status, dashboard)
#   refresh "after": the command changes data, so run the clerk and rebuild afterwards
COMMANDS = {
    "doctor": ("doctor", "none", ""),
    "status": ("status", "required", "before"),
    "due": ("due", "required", ""),
    "dashboard": ("dashboard", "required", "before"),
    "tracker": ("tracker", "required", "after"),
    "clerk": ("clerk", "required", "after"),
    "pdf": ("render_pdf", "none", ""),
    "posting": ("posting", "none", ""),
    "scan": ("scan_watchlist", "required", "after"),
    "sync-check": ("sync_check", "optional", ""),
    "pii-check": ("pii_check", "none", ""),
}
HELP = {
    "init": "create or extend a data folder (setup)",
    "doctor": "check this computer has what Perkins needs",
    "status": "where the whole search stands (runs the clerk and rebuilds the dashboard first)",
    "due": "what needs you: follow-ups, checks, ready resumes, an unfiled claim",
    "dashboard": "rebuild dashboard.html",
    "tracker": "show or edit tracker.md tables",
    "clerk": "claims tracking: open, recount, nudge, log an activity, mark a claim filed",
    "pdf": "render Markdown resumes to PDF",
    "posting": "fetch a job posting's full text",
    "scan": "scan the employers you watch for new postings",
    "sync-check": "check Claude Docs tabs against their Markdown files",
    "pii-check": "look for personal information before sharing a folder",
}


def tracker_arguments(p) -> None:
    p.add_argument("action", choices=["show", "add", "update", "move", "remove"])
    p.add_argument("section", nargs="?", help="table name, such as Considering")
    p.add_argument("to", nargs="?", help="for move: the table to move the row to")
    p.add_argument("--set", action="append", metavar="COL=VALUE")
    p.add_argument("--match", action="append", metavar="COL=VALUE",
                   help="pick the row: an exact cell value wins; otherwise a cell containing it")
    p.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="run.py", description="Perkins: tailored resumes, a tracker, and a work-search log.")
    ap.add_argument("--data", help="the data folder (default: PERKINS_HOME, then ~/.perkins, then ~/job-search)")
    ap.add_argument("--today", help="pin today's date, YYYY-MM-DD (for testing)")
    sub = ap.add_subparsers(dest="command", required=True)
    from perkins import init as init_mod
    init_mod.add_arguments(sub.add_parser("init", help=HELP["init"]))
    sub.add_parser("version", help="print the version")
    sub.add_parser("states", help="list the states claims tracking supports")
    for name, (module, _, _) in COMMANDS.items():
        p = sub.add_parser(name, help=HELP[name])
        if name == "tracker":
            tracker_arguments(p)
        else:
            importlib.import_module(f"perkins.{module}").add_arguments(p)
    return ap


def refresh(cfg: C.Config, today: date, clerk: bool = True) -> None:
    """Run the clerk (while there are claim records) and rebuild the dashboard. A failure here
    is reported but never undoes or hides the command that already succeeded."""
    try:
        if clerk and cfg.claim_records:
            from perkins import clerk as clerk_mod
            clerk_mod.run(cfg, today)
        if cfg.tracker.exists():
            from perkins import dashboard
            dashboard.write(cfg, today)
    except (PerkinsError, OSError, UnicodeDecodeError) as e:
        print(f"Warning: the dashboard wasn't rebuilt: {e}", file=sys.stderr)


def run(args) -> int:
    if args.command == "version":
        print(f"Perkins {__version__}")
        return 0
    if args.command == "states":
        for code in C.available_states():
            st = C.load_state(code)
            print(f"{code}  {st.name} ({st.agency}): {st.required} activities a week, rules checked {st.last_checked}")
        return 0
    pinned = date.fromisoformat(args.today) if args.today else None
    if args.command == "init":
        from perkins import init as init_mod
        return init_mod.cli(args, C.find_home(args.data), pinned or date.today())

    module, folder, when = COMMANDS[args.command]
    if folder == "optional" and getattr(args, "compare", None):
        folder = "none"
    cfg = C.load(args.data) if folder in ("required", "optional") else None
    today = pinned or C.today(cfg)
    if cfg and when == "before":
        refresh(cfg, today)
    mod = importlib.import_module(f"perkins.{module}")
    code = mod.cli(args, cfg, today)
    read_only = getattr(args, "dry_run", False) or getattr(args, "action", None) == "show"
    if cfg and when == "after" and not read_only:
        refresh(cfg, today, clerk=args.command != "clerk")  # the clerk command just ran the clerk
    return code


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (PerkinsError, OSError, UnicodeDecodeError, ValueError) as e:
        # Every Perkins error, a file problem, or a bad date: one plain line, exit 2.
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
