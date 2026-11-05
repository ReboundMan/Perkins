"""What is due: every follow-up and employer check dated within N days or already past,
plus, with claims tracking, last week's claim when it isn't filed yet.

Shared by the dashboard's due-soon list and the reminder recipes, so both always agree.
CLI: due [--days N] [--json]
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta

from . import config as C
from . import tracker as T

DATE_COLS = ("next follow-up", "next check")
DETAIL_COLS = ("follow-up notes", "why watch", "next step", "about")
FIRST_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def first_date(text: str) -> date | None:
    m = FIRST_DATE.search(text or "")
    if not m:
        return None
    try:
        return date.fromisoformat(m.group(0))
    except ValueError:
        return None


def from_tracker(tr: T.Tracker, today: date, days: int = 7) -> list[dict]:
    items = []
    for b in tr.blocks:
        if b[0] != "table" or not b[1]:
            continue
        section, t = b[1], b[2]
        cols = [h.strip().lower() for h in t.header]
        for row in t.rows:
            row = t.normalized(row)
            for ci, col in enumerate(cols):
                if col not in DATE_COLS:
                    continue
                d = first_date(row[ci])
                if not d or d > today + timedelta(days=days):
                    continue
                what = T.plain(row[cols.index("company")]) if "company" in cols else T.plain(row[0])
                if "role" in cols and T.plain(row[cols.index("role")]):
                    what += ", " + T.plain(row[cols.index("role")])
                detail_col = next((c for c in DETAIL_COLS if c in cols), None)
                items.append({
                    "date": d.isoformat(),
                    "overdue": d < today,
                    "section": section,
                    "kind": "check" if col == "next check" else "follow-up",
                    "what": what,
                    "detail": T.plain(row[cols.index(detail_col)]) if detail_col else "",
                })
    return items


def claim_items(cfg: C.Config, today: date) -> list[dict]:
    """Last week's claim, when claims tracking is on and it isn't marked filed."""
    if not cfg.claims:
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
    claim_off = (state.claim_day - state.week_end) % 7 or 7
    due_on = prev_end + timedelta(days=claim_off)
    if today < due_on:
        return []
    return [{
        "date": due_on.isoformat(),
        "overdue": today > due_on,
        "section": "Claim",
        "kind": "claim",
        "what": f"File the {state.agency} weekly claim for the week ending {prev_end.isoformat()}",
        "detail": f"Closed at {clerk.counts_phrase(w, state.required)}",
    }]


def collect(cfg: C.Config, today: date, days: int = 7) -> list[dict]:
    items = claim_items(cfg, today)  # an unfiled claim always tops the list
    tracked = []
    if cfg.tracker.exists():
        tracked = from_tracker(T.Tracker.load(cfg.tracker), today, days)
    tracked.sort(key=lambda i: (i["date"], i["what"].lower()))
    return items + tracked


def add_arguments(p) -> None:
    p.add_argument("--days", type=int, default=7, help="look this many days ahead (default 7)")
    p.add_argument("--json", action="store_true")


def cli(args, cfg: C.Config, today: date) -> int:
    items = collect(cfg, today, args.days)
    if args.json:
        print(json.dumps({"today": today.isoformat(), "days": args.days, "items": items}, indent=2, ensure_ascii=False))
        return 0
    if not items:
        print(f"Nothing due in the next {args.days} days.")
        return 0
    for i in items:
        when = "overdue" if i["overdue"] else ("today" if i["date"] == today.isoformat() else "due")
        line = f"{i['date']}  {when:<8} {i['what']}"
        if i["detail"]:
            line += f"  ({i['detail']})"
        print(line)
    return 0
