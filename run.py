"""Perkins command line. The skills run everything through this one file.

  python run.py [--data DIR] [--today YYYY-MM-DD] <command> [options]

Commands: init, status, due, dashboard, tracker, clerk, pdf, posting, scan, sync-check, pii-check, version.
Run any command with -h for its options. Changes to the tracker or the log rebuild dashboard.html.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from perkins import __version__  # noqa: E402
from perkins import config as C  # noqa: E402

# command: (module, needs a data folder, changes data so the dashboard is rebuilt after)
COMMANDS = {
    "status": ("status", True, False),
    "due": ("due", True, False),
    "dashboard": ("dashboard", True, False),
    "tracker": ("tracker", True, True),
    "clerk": ("clerk", True, True),
    "pdf": ("render_pdf", False, False),
    "posting": ("posting", False, False),
    "scan": ("scan_watchlist", True, True),
    "sync-check": ("sync_check", True, False),
    "pii-check": ("pii_check", False, False),
}
HELP = {
    "init": "create or extend a data folder (setup)",
    "status": "where the whole search stands",
    "due": "follow-ups and checks that are due",
    "dashboard": "rebuild dashboard.html",
    "tracker": "show or edit tracker.md tables",
    "clerk": "claims tracking: open, recount, nudge, log an activity",
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
    p.add_argument("--match", action="append", metavar="COL=VALUE")
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
            continue
        try:
            importlib.import_module(f"perkins.{module}").add_arguments(p)
        except ModuleNotFoundError:
            p.set_defaults(unavailable=True)
    return ap


def refresh(cfg: C.Config, today: date) -> None:
    """Run the clerk (claims tracking) and rebuild the dashboard."""
    if cfg.claims:
        from perkins import clerk
        clerk.run(cfg, today)
    if cfg.tracker.exists():
        from perkins import dashboard
        dashboard.write(cfg, today)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    if args.command == "version":
        print(f"Perkins {__version__}")
        return 0
    if args.command == "states":
        for code in C.available_states():
            st = C.load_state(code)
            print(f"{code}  {st.name} ({st.agency}): {st.required} activities a week, rules checked {st.last_checked}")
        return 0
    try:
        pinned = date.fromisoformat(args.today) if args.today else None
        if args.command == "init":
            from perkins import init as init_mod
            return init_mod.cli(args, C.find_home(args.data), pinned or date.today())
        if getattr(args, "unavailable", False):
            print(f"The {args.command} command isn't available in this install.", file=sys.stderr)
            return 2
        module, needs_cfg, changes = COMMANDS[args.command]
        cfg = C.load(args.data) if needs_cfg else (C.load(args.data) if _has_config(args.data) else None)
        today = pinned or C.today(cfg)
        mod = importlib.import_module(f"perkins.{module}")
        if args.command == "status" and cfg:
            refresh(cfg, today)
        takes_today = len(inspect.signature(mod.cli).parameters) >= 3
        code = mod.cli(args, cfg, today) if takes_today else mod.cli(args, cfg)
        mutated = changes and not getattr(args, "dry_run", False) and not (
            args.command == "tracker" and args.action == "show")
        if mutated and cfg:
            refresh(cfg, today)
        return code
    except Exception as e:  # every module raises errors with a message meant for the user
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            raise
        name = type(e).__name__
        if name in ("ConfigError", "TrackerError", "ClerkError", "PdfError", "SyncError", "PostingError", "ScanError",
                    "FileNotFoundError", "ValueError"):
            print(f"Error: {e}", file=sys.stderr)
            return 2
        raise


def _has_config(explicit) -> bool:
    return (C.find_home(explicit) / C.CONFIG_NAME).is_file()


if __name__ == "__main__":
    sys.exit(main())
