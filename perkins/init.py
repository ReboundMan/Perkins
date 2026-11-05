"""Create a data folder, or extend one, for either mode. It only ever adds: it never
overwrites a file you have, and it never edits a row that's already in your tracker.

CLI: init [--data DIR] [--mode search|search-claims] [--state wa] [--claim-start DATE]
          [--claim-end DATE] [--timezone ZONE] [--no-pointer]
"""
from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from . import config as C
from . import tracker as T

TEMPLATE_FILES = {
    "master-resume.md": "master.md",
    "tailoring-model.md": "tailoring-model.md",
    "style.md": "style.md",
    "fact-sheet.md": "fact-sheet.md",
    "tracker.md": "tracker.md",
}


def settings_snippet(home: Path) -> str:
    return json.dumps({"permissions": {"additionalDirectories": [str(home)]}}, indent=2)


def init(home: Path, mode: str, today: date, state: str | None = None, claim_start: date | None = None,
         claim_end: date | None = None, timezone: str | None = None, pointer: bool = True) -> dict:
    if mode not in C.MODES:
        raise C.ConfigError(f"mode must be one of {', '.join(C.MODES)}")
    home = Path(home).expanduser().resolve()
    home.mkdir(parents=True, exist_ok=True)
    created, notes = [], []

    try:
        cfg = C.load(home)
        notes.append(f"Kept your existing {C.CONFIG_NAME} and changed only what you asked.")
    except C.ConfigError:
        cfg = C.Config(home=home)
    cfg.mode = mode
    if timezone is not None:
        cfg.timezone = timezone
    if mode == C.CLAIMS:
        code = (state or cfg.state or "").lower()
        st = C.load_state(code)  # refuses an unknown state with the list of known ones
        cfg.state = st.code
        cfg.claim_start = claim_start or cfg.claim_start or today
        if cfg.weekly_target and cfg.weekly_target < st.required:
            notes.append(f"Raised weekly_target to {st.required}, the {st.name} minimum.")
            cfg.weekly_target = st.required
    if claim_end is not None:
        cfg.claim_end = claim_end
    C.save(cfg)

    for src, dst in TEMPLATE_FILES.items():
        target = home / dst
        if not target.exists():
            shutil.copyfile(C.TEMPLATES_DIR / src, target)
            created.append(dst)
    cfg.applications.mkdir(exist_ok=True)

    if cfg.claims:
        for d in (cfg.log_dir, cfg.evidence_dir):
            if not d.exists():
                d.mkdir(parents=True)
                created.append(str(d.relative_to(home)) + "/")
        tr = T.Tracker.load(cfg.tracker)
        added = [name for name in T.CLAIM_TABLES if tr.ensure_column(name, T.CLAIM_COL, before=T.CLAIM_COL_BEFORE)]
        if added:
            tr.save()
            notes.append(f"Added an empty {T.CLAIM_COL} column to: {', '.join(added)}.")
        from . import clerk
        if not cfg.nudges.exists():
            cfg.nudges.write_text(clerk.NUDGES_HEAD, encoding="utf-8", newline="\n")
            created.append("nudges.md")
        clerk.run(cfg, today)
    elif cfg.log_dir.exists():
        notes.append("Claims tracking is off. Your work-search log stays in log/ untouched.")

    from . import dashboard
    dashboard.write(cfg, today)

    if pointer:
        C.POINTER.write_text(str(home) + "\n", encoding="utf-8")

    return {
        "home": str(home),
        "mode": cfg.mode,
        "mode_name": cfg.mode_name,
        "state": cfg.state if cfg.claims else "",
        "claim_start": cfg.claim_start.isoformat() if cfg.claims and cfg.claim_start else "",
        "created": created,
        "notes": notes,
        "settings_snippet": settings_snippet(home),
    }


def add_arguments(p) -> None:
    p.add_argument("--mode", choices=C.MODES, default=C.SEARCH)
    p.add_argument("--state", help="two-letter state code for claims tracking, such as wa")
    p.add_argument("--claim-start", help="the first day of your claim, YYYY-MM-DD (default today)")
    p.add_argument("--claim-end", help="the day your claim ended, YYYY-MM-DD")
    p.add_argument("--timezone", help="an IANA zone such as America/Los_Angeles")
    p.add_argument("--no-pointer", action="store_true", help="don't write ~/.perkins")


def cli(args, home: Path, today: date) -> int:
    out = init(
        home, args.mode, today, state=args.state,
        claim_start=date.fromisoformat(args.claim_start) if args.claim_start else None,
        claim_end=date.fromisoformat(args.claim_end) if args.claim_end else None,
        timezone=args.timezone, pointer=not args.no_pointer,
    )
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0
