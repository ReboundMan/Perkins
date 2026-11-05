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


def _need_dir(path: Path) -> None:
    if path.exists() and not path.is_dir():
        raise C.ConfigError(f"{path} is a file, but Perkins needs a folder there. Move or rename the file.")


def settings_snippet(home: Path) -> str:
    return json.dumps({"permissions": {"additionalDirectories": [str(home)]}}, indent=2)


def init(home: Path, mode: str, today: date, state: str | None = None, claim_start: date | None = None,
         claim_end: date | None = None, timezone: str | None = None, pointer: bool = True) -> dict:
    if mode not in C.MODES:
        raise C.ConfigError(f"mode must be one of {', '.join(C.MODES)}")
    home = Path(home).expanduser().resolve()
    _need_dir(home)
    home.mkdir(parents=True, exist_ok=True)
    created, notes = [], []

    if (home / C.CONFIG_NAME).exists():
        cfg = C.load(home)  # a file that doesn't read is an error to fix, never something to replace
        notes.append(f"Kept your existing {C.CONFIG_NAME} and changed only what you asked.")
    else:
        cfg = C.Config(home=home)
    cfg.mode = mode
    if timezone is not None:
        C.check_timezone(timezone)
        cfg.timezone = timezone
    if mode == C.CLAIMS:
        code = (state or cfg.state or "").lower()
        st = C.load_state(code)  # refuses an unknown state with the list of known ones
        cfg.state = st.code
        if claim_start and cfg.claim_end and claim_start > cfg.claim_end:
            notes.append(f"Started a new claim on {claim_start}; cleared the old claim_end ({cfg.claim_end}).")
            cfg.claim_end = None
        cfg.claim_start = claim_start or cfg.claim_start or today
        if cfg.weekly_target < st.required:
            if cfg.weekly_target:
                notes.append(f"Raised weekly_target to {st.required}, the {st.name} minimum.")
            cfg.weekly_target = st.required
    if claim_end is not None:
        cfg.claim_end = claim_end
    if cfg.claim_start and cfg.claim_end and cfg.claim_end < cfg.claim_start:
        raise C.ConfigError(f"The claim end ({cfg.claim_end}) is before the claim start ({cfg.claim_start}).")
    for d in (cfg.applications, cfg.log_dir, cfg.evidence_dir):
        _need_dir(d)
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
        if cfg.claim_records:
            from . import clerk
            clerk.run(cfg, today)  # keeps the last week's claim reminder until it's filed
            notes.append("Your last claim week's reminder stays until you mark that claim filed.")

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
    p.add_argument("--no-pointer", action="store_true",
                   help="don't point ~/.perkins at this folder (by default init makes it the folder every skill uses)")


def cli(args, home: Path, today: date) -> int:
    out = init(
        home, args.mode, today, state=args.state,
        claim_start=date.fromisoformat(args.claim_start) if args.claim_start else None,
        claim_end=date.fromisoformat(args.claim_end) if args.claim_end else None,
        timezone=args.timezone, pointer=not args.no_pointer,
    )
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0
