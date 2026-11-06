"""What needs you: every follow-up and employer check dated within N days or already past,
resumes ready to submit, dates Perkins can't read, and, while there's a claim to keep up
with, last week's claim when it isn't filed yet.

Shared by the dashboard's due-soon list, status, and the reminder recipes, so all three agree.
CLI: due [--days N] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta

from . import config as C
from . import tracker as T

DATE_COLS = ("next follow-up", "next check")
DETAIL_COLS = ("follow-up notes", "why watch", "next step", "about")
FIRST_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
MAX_DAYS = 3650


def first_date(text: str) -> date | None:
    m = FIRST_DATE.search(text or "")
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(0))
    except ValueError:
        return None


def _what(t: T.Table, row: list[str]) -> str:
    what = T.plain(t.get(row, "Company")) or T.plain(row[0])
    role = T.plain(t.get(row, "Role"))
    return f"{what}, {role}" if role else what


def from_tracker(tr: T.Tracker, today: date, days: int = 7) -> list[dict]:
    items = []
    for b in tr.blocks:
        if b[0] != "table" or not b[1]:
            continue
        section, t = b[1], b[2]
        cols = [h.strip().lower() for h in t.header]
        detail_col = next((c for c in DETAIL_COLS if c in cols), None)
        for row in t.rows:
            row = t.normalized(row)
            for ci, col in enumerate(cols):
                if col not in DATE_COLS or not row[ci].strip():
                    continue
                d = first_date(row[ci])
                base = {"section": section, "what": _what(t, row),
                        "detail": T.plain(row[cols.index(detail_col)]) if detail_col else ""}
                if d is None:
                    # Never drop a follow-up silently because its date is written another way.
                    items.append({**base, "date": "", "overdue": False, "kind": "unreadable date",
                                  "detail": f"{t.header[ci]} says \"{T.plain(row[ci])}\"; write it as YYYY-MM-DD"})
                    continue
                if d > today + timedelta(days=days):
                    continue
                items.append({**base, "date": d.isoformat(), "overdue": d < today,
                              "kind": "check" if col == "next check" else "follow-up"})
    return items


def ready_items(tr: T.Tracker, today: date) -> list[dict]:
    t = tr.maybe_table(T.CONSIDERING)
    if not t:
        return []
    out = []
    for row in t.rows:
        row = t.normalized(row)
        if T.plain(t.get(row, "Resume")).lower().startswith("ready") and "held" not in T.plain(t.get(row, "Status")).lower():
            out.append({"date": today.isoformat(), "overdue": False, "section": T.CONSIDERING, "kind": "ready",
                        "what": _what(t, row), "detail": "Resume ready to submit"})
    return out


def claim_items(cfg: C.Config, today: date) -> list[dict]:
    """Last week's claim, while there are claim records to keep and it isn't marked filed."""
    if not cfg.claim_records:
        return []
    from . import clerk
    state = C.load_state(cfg.state)
    start, _ = clerk.week_bounds(today, state)
    prev_end = start - timedelta(days=1)
    w = clerk.load_weeks(cfg).get(prev_end)
    if w is None or not clerk.in_claim(cfg, prev_end - timedelta(days=6), prev_end):
        return []
    if C.DATE_RE.match(w["fm"].get("claim_filed", "")):
        return []
    due_on = prev_end + timedelta(days=clerk.claim_offset(state))
    if today < due_on:
        return []
    by = clerk.file_by(state, prev_end, cfg.claim_start)
    return [{
        "date": due_on.isoformat(),
        "overdue": today > due_on,
        "section": "Claim",
        "kind": "claim",
        "what": f"File the {state.agency} weekly claim for the week ending {prev_end.isoformat()}",
        "detail": f"Closed at {clerk.counts_phrase(w, state.required)}"
                  + (f"; file by {by.isoformat()}" if by else ""),
    }]


def once_items(cfg: C.Config, today: date, days: int) -> list[dict]:
    """Unticked one-time lines in nudges.md, from the state file's [[once]] tasks, within the window."""
    if not cfg.claims or not cfg.nudges.exists():
        return []
    from . import clerk
    out = []
    for line in clerk.read_text(cfg.nudges).splitlines():
        m = clerk.TODO_RE.match(line)
        c = clerk.ONCE_RE.search(m.group(4)) if m and m.group(1) == " " else None
        if not c:
            continue
        due_on = date.fromisoformat(c.group(2))
        if (due_on - today).days > days:
            continue
        out.append({"date": due_on.isoformat(), "overdue": today > due_on, "section": "Claim", "kind": "once",
                    "what": c.group(1), "detail": "One-time; tick it in nudges.md once it's done"})
    return out


def collect(cfg: C.Config, today: date, days: int = 7) -> list[dict]:
    """The claim first, then resumes ready to submit, then dated items by date, then unreadable dates."""
    items = claim_items(cfg, today) + once_items(cfg, today, days)
    if not cfg.tracker.exists():
        return items
    tr = T.Tracker.load(cfg.tracker)
    tracked = from_tracker(tr, today, days)
    dated = sorted((i for i in tracked if i["date"]), key=lambda i: (i["date"], i["what"].lower()))
    unreadable = [i for i in tracked if not i["date"]]
    return items + ready_items(tr, today) + dated + unreadable


def week_window(cfg: C.Config, today: date) -> tuple[date, date]:
    """This week's first and last day: the claim week with claims tracking, else Monday to Sunday."""
    if cfg.claims:
        from . import clerk
        return clerk.week_bounds(today, C.load_state(cfg.state))
    start = today - timedelta(days=today.weekday())
    return start, start + timedelta(days=6)


def applied_this_week(cfg: C.Config, tr: T.Tracker, today: date) -> int:
    """Applications in Submitted dated this week, up to today."""
    t = tr.maybe_table(T.SUBMITTED)
    if not t:
        return 0
    start, _ = week_window(cfg, today)
    return sum(1 for r in t.rows if (d := first_date(t.get(t.normalized(r), "Submitted"))) and start <= d <= today)


def _days(value: str) -> int:
    n = int(value)
    if not 0 <= n <= MAX_DAYS:
        raise argparse.ArgumentTypeError(f"--days must be between 0 and {MAX_DAYS}")
    return n


def add_arguments(p) -> None:
    p.add_argument("--days", type=_days, default=7, help="look this many days ahead (default 7)")
    p.add_argument("--json", action="store_true")


def label(i: dict, today: date) -> str:
    if i["kind"] == "unreadable date":
        return "fix date"
    if i["kind"] == "ready":
        return "ready"
    if i["overdue"]:
        return "overdue"
    d = date.fromisoformat(i["date"])
    n = (d - today).days
    return "today" if n == 0 else ("tomorrow" if n == 1 else f"in {n} days")


def cli(args, cfg: C.Config, today: date) -> int:
    items = collect(cfg, today, args.days)
    if args.json:
        print(json.dumps({"today": today.isoformat(), "days": args.days, "items": items}, indent=2, ensure_ascii=False))
        return 0
    if not items:
        print(f"Nothing due in the next {args.days} days.")
        return 0
    for i in items:
        line = f"{i['date'] or '----------'}  {label(i, today):<10} {i['what']}"
        if i["detail"]:
            line += f"  ({i['detail']})"
        print(line)
    return 0
