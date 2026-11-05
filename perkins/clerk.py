"""The claims clerk: the work-search log's bookkeeping, for Search with tracking for
Unemployment Claims only. Stdlib, no tokens, idempotent; safe to run as often as you like.

One file per claim week in log/, named for the week's last day. The clerk:
1. Opens the current week's file if it doesn't exist yet (within the claim period).
2. Recounts every week file (solid, check, no, and MISSING blanks) into its frontmatter.
3. Keeps nudges.md on the state's rhythm: a midweek "work search check" for the current
   week (raised to high priority late in the week), and a "file the weekly claim" line
   for the week that just ended. A ticked claim line stamps claim_filed on its week.
It also writes entries (`clerk add`) so every entry has the state's fields in order.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from . import config as C
from .errors import PerkinsError
from .guard import refuse_sensitive

# These patterns are keys, not prose: the clerk writes the nudge lines in this exact wording
# and finds them again by it. Change the wording in claim_line/check_line and here together.
TODO_RE = re.compile(r"^- \[( |x|X)\] \((H|M|L)\) (\d{4}-\d{2}-\d{2}) (.*)$")
CLAIM_RE = re.compile(r"File the (?:.+? )?weekly claim for the week ending (\d{4}-\d{2}-\d{2})")
CHECK_RE = re.compile(r"Work search check, week ending (\d{4}-\d{2}-\d{2})")
DONE_RE = re.compile(r"✅\s*(\d{4}-\d{2}-\d{2})")
FIELD_RE = re.compile(r"^- \*\*(.+?):\*\*\s*(.*)$")
OPEN_SLOT = "(open)"  # the body of an activity slot nobody has filled; ensure_week writes it
MAX_BACKFILL_WEEKS = 60
FITS = ("solid", "check", "no")
EXTRA_FIELDS = ["Person", "Result and next step", "Source"]
NUDGES_HEAD = (
    "# Nudges\n\n"
    "Claim and work-search reminders, kept by the Perkins clerk. Tick a claim line once you've "
    "filed that week's claim; the clerk stamps the date on that week's log. Don't edit the "
    "counts by hand: the clerk refreshes them.\n\n"
)


class ClerkError(PerkinsError):
    """An entry or command the clerk refuses; the message says why."""


def read_text(path: Path) -> str:
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as e:
        raise ClerkError(f"{path} isn't UTF-8 text (byte {e.start}). Fix or remove that character, "
                         "then run the command again.") from e


def claim_offset(state: C.State) -> int:
    """Days from the end of a claim week to the day its claim reminder appears. When the
    claim day falls on the week's own last weekday, that's the following week's (7 days on)."""
    return (state.claim_day - state.week_end) % 7 or 7


# --- weeks -------------------------------------------------------------------

def week_bounds(d: date, state: C.State) -> tuple[date, date]:
    start = d - timedelta(days=(d.weekday() - state.week_start) % 7)
    return start, start + timedelta(days=6)


def week_path(cfg: C.Config, end: date) -> Path:
    return cfg.log_dir / f"week-ending-{end.isoformat()}.md"


def week_link(end: date) -> str:
    return f"[log](log/week-ending-{end.isoformat()}.md)"


def in_claim(cfg: C.Config, start: date, end: date) -> bool:
    if cfg.claim_start and end < cfg.claim_start:
        return False
    if cfg.claim_end and start > cfg.claim_end:
        return False
    return True


def claim_weeks(cfg: C.Config, state: C.State, today: date) -> list[date]:
    """The end dates of every claim week from the claim's first week through this week,
    within the claim period. Setup partway through a claim opens the earlier weeks too, so
    past activities have somewhere to go. Capped, so a mistyped start year can't run away."""
    _, end = week_bounds(today, state)
    first = week_bounds(cfg.claim_start, state)[1] if cfg.claim_start else end
    first = max(first, end - timedelta(weeks=MAX_BACKFILL_WEEKS))
    out, wk = [], first
    while wk <= end:
        if in_claim(cfg, wk - timedelta(days=6), wk):
            out.append(wk)
        wk += timedelta(days=7)
    return out


def split_frontmatter(text: str) -> tuple[list[str], list[str]]:
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[1:i], lines[i + 1:]
    return [], lines


def is_activity_heading(title: str) -> bool:
    t = title.strip().lower()
    return t.startswith("activity") or t.startswith("contact")


def fit_of(fields: dict) -> str:
    """The first word of the Fit field. Anything unreadable counts as check, never solid."""
    for k, v in fields.items():
        if k.strip().lower() == "fit" or k.strip().lower().endswith(" fit"):
            word = re.split(r"[\s.,;:]", v.strip().lower() or "check")[0]
            return word if word in FITS else "check"
    return "check"


def parse_week(path: Path) -> dict:
    fm_lines, body = split_frontmatter(read_text(path))
    fm = {}
    for line in fm_lines:
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"')
    entries, current = [], None
    for line in body:
        if line.startswith("## "):
            title = line[3:].strip()
            current = {"title": title, "fields": {}} if is_activity_heading(title) else None
            if current is not None:
                entries.append(current)
            continue
        if current is not None:
            m = FIELD_RE.match(line.strip())
            if m:
                current["fields"][m.group(1).strip()] = m.group(2).strip()
    counts = {"solid": 0, "check": 0, "no": 0, "missing": 0}
    for e in entries:
        if not e["fields"]:
            continue  # an open slot, not an entry
        counts["missing"] += sum(1 for v in e["fields"].values() if v.upper().startswith("MISSING"))
        counts[fit_of(e["fields"])] += 1
    return {"path": path, "fm": fm, "entries": entries, **counts}


def set_frontmatter(path: Path, updates: dict) -> bool:
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return False
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return False
    fm = lines[1:end]
    for key, value in updates.items():
        new = f"{key}: {value}"
        for i, line in enumerate(fm):
            if line.split(":", 1)[0].strip() == key:
                fm[i] = new
                break
        else:
            fm.append(new)
    out = nl.join(["---", *fm, *lines[end:]]) + nl
    if out == text:
        return False
    path.write_text(out, encoding="utf-8", newline="")
    return True


def ensure_week(cfg: C.Config, state: C.State, end: date, opened: date) -> bool:
    path = week_path(cfg, end)
    if path.exists():
        return False
    start = end - timedelta(days=6)
    slots = "\n".join(f"## Activity {n}\n\n{OPEN_SLOT}\n" for n in range(1, state.required + 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "type: work-search-log\n"
        f"state: {state.code}\n"
        f"week_start: {start.isoformat()}\n"
        f"week_ending: {end.isoformat()}\n"
        f"required: {state.required}\n"
        "solid: 0\n"
        "check: 0\n"
        "missing: 0\n"
        'claim_filed: "no"\n'
        "---\n\n"
        f"# Work-search log, week ending {C.weekday_name(end)} {end.isoformat()}\n\n"
        f"{C.weekday_name(start)} {start.isoformat()} through {C.weekday_name(end)} {end.isoformat()}. "
        f"Opened {opened.isoformat()}. {state.name} rules ({state.agency}): {state.required} approved "
        f"activities a week; see the plugin's states/{state.code}.toml for the fields and sources.\n\n"
        f"{slots}",
        encoding="utf-8",
        newline="\n",
    )
    return True


def recount(path: Path) -> tuple[dict, bool]:
    w = parse_week(path)
    changed = set_frontmatter(path, {"solid": w["solid"], "check": w["check"], "missing": w["missing"]})
    return w, changed


def load_weeks(cfg: C.Config) -> dict[date, dict]:
    weeks = {}
    for p in sorted(cfg.log_dir.glob("week-ending-*.md")):
        try:
            weeks[date.fromisoformat(p.stem.removeprefix("week-ending-"))] = parse_week(p)
        except ValueError:
            continue
    return weeks


# --- nudges ------------------------------------------------------------------

def counts_phrase(w: dict | None, required: int) -> str:
    if w is None:
        return "no log file yet"
    s = f"{w['solid']} of {required} solid, {w['check']} to check"
    if w["missing"]:
        s += f", {w['missing']} blank{'s' if w['missing'] != 1 else ''}"
    return s


def claim_line(state: C.State, added: date, end: date, w: dict | None) -> str:
    return (f"- [ ] (H) {added.isoformat()} File the {state.agency} weekly claim for the week ending "
            f"{end.isoformat()}: {counts_phrase(w, state.required)}. Log any stragglers and fill the "
            f"blanks first; tick this once it's filed. {week_link(end)} 📅 {added.isoformat()}")


def check_line(state: C.State, priority: str, added: date, end: date, w: dict | None) -> str:
    start = end - timedelta(days=6)
    return (f"- [ ] ({priority}) {added.isoformat()} Work search check, week ending {end.isoformat()}: "
            f"{counts_phrase(w, state.required)}. Log anything done since {C.weekday_name(start)}; "
            f"{C.weekday_name(end)} is the last day. {week_link(end)} 📅 {end.isoformat()}")


def insert_at_top(lines: list[str], new: str) -> None:
    for i, line in enumerate(lines):
        if line.startswith("- ["):
            lines.insert(i, new)
            return
    while lines and not lines[-1].strip():
        lines.pop()
    lines.append("")
    lines.append(new)


def tend_nudges(cfg: C.Config, state: C.State, today: date, weeks: dict) -> list[str]:
    path = cfg.nudges
    if not path.exists():
        path.write_text(NUDGES_HEAD, encoding="utf-8", newline="\n")
    text = read_text(path)
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines()
    actions = []
    start, end = week_bounds(today, state)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=6)

    # Keep one line per nudge (a merge or a sync tool can duplicate them): a ticked copy wins.
    found: dict[tuple[str, date], list[int]] = {}
    for i, line in enumerate(lines):
        m = TODO_RE.match(line)
        if not m:
            continue
        if (c := CLAIM_RE.search(m.group(4))):
            found.setdefault(("claim", date.fromisoformat(c.group(1))), []).append(i)
        elif (c := CHECK_RE.search(m.group(4))):
            found.setdefault(("check", date.fromisoformat(c.group(1))), []).append(i)
    drop = set()
    for (kind, wk), idx in found.items():
        if len(idx) > 1:
            keep = next((i for i in idx if TODO_RE.match(lines[i]).group(1) in "xX"), idx[0])
            drop.update(i for i in idx if i != keep)
            actions.append(f"removed {len(idx) - 1} duplicate {kind} line(s), week ending {wk}")
    if drop:
        lines = [l for i, l in enumerate(lines) if i not in drop]

    claims, checks = {}, {}
    for i, line in enumerate(lines):
        m = TODO_RE.match(line)
        if not m:
            continue
        if (c := CLAIM_RE.search(m.group(4))):
            claims[date.fromisoformat(c.group(1))] = i
        elif (c := CHECK_RE.search(m.group(4))):
            checks[date.fromisoformat(c.group(1))] = i

    # A ticked claim line stamps claim_filed on its week file.
    for wk, i in claims.items():
        m = TODO_RE.match(lines[i])
        w = weeks.get(wk)
        if m.group(1) in "xX" and w and not C.DATE_RE.match(w["fm"].get("claim_filed", "")):
            done = DONE_RE.search(lines[i])
            filed = done.group(1) if done else today.isoformat()
            set_frontmatter(w["path"], {"claim_filed": filed})
            w["fm"]["claim_filed"] = filed
            note = "" if done else " (the tick had no date, so today's was used; correct it with clerk filed --on)"
            actions.append(f"stamped claim_filed {filed} on week ending {wk}{note}")

    days_in = (today - start).days
    check_off = (state.check_day - state.week_start) % 7
    raise_off = (state.raise_day - state.week_start) % 7
    claim_off = claim_offset(state)

    for wk, i in claims.items():
        m = TODO_RE.match(lines[i])
        if m.group(1) == " ":
            fresh = claim_line(state, date.fromisoformat(m.group(3)), wk, weeks.get(wk))
            if fresh != lines[i]:
                lines[i] = fresh
                actions.append(f"refreshed claim line, week ending {wk}")
    for wk, i in checks.items():
        m = TODO_RE.match(lines[i])
        if m.group(1) != " ":
            continue
        w = weeks.get(wk)
        added = date.fromisoformat(m.group(3))
        if w and w["solid"] >= state.required:
            lines[i] = (check_line(state, m.group(2), added, wk, w).replace("- [ ]", "- [x]", 1)
                        + f" ✅ {today.isoformat()} (auto: {state.required} solid entries logged)")
            actions.append(f"ticked check line, week ending {wk}: {state.required} solid")
        elif wk < start:
            lines[i] = (lines[i].replace("- [ ]", "- [x]", 1)
                        + f" ✅ {today.isoformat()} (auto: week closed at {counts_phrase(w, state.required)}; the claim line carries it)")
            actions.append(f"rolled up check line, week ending {wk}")
        else:
            priority = "H" if days_in >= raise_off else m.group(2)
            fresh = check_line(state, priority, added, wk, w)
            if fresh != lines[i]:
                lines[i] = fresh
                actions.append(f"refreshed check line, week ending {wk}")

    # The claim line for the week that just ended, from the claim day on, unless already filed.
    lw = weeks.get(prev_end)
    if ((today - prev_end).days >= claim_off and prev_end not in claims and lw is not None
            and in_claim(cfg, prev_start, prev_end)
            and not C.DATE_RE.match(lw["fm"].get("claim_filed", ""))):
        insert_at_top(lines, claim_line(state, today, prev_end, lw))
        actions.append(f"added claim line, week ending {prev_end}")

    # The check line for the current week, from the check day on, unless it already has enough.
    cw = weeks.get(end)
    if (days_in >= check_off and end not in checks and in_claim(cfg, start, end)
            and not (cw and cw["solid"] >= state.required)):
        insert_at_top(lines, check_line(state, "H" if days_in >= raise_off else "M", today, end, cw))
        actions.append(f"added check line, week ending {end}")

    out = nl.join(lines) + nl
    if out != text:
        path.write_text(out, encoding="utf-8", newline="")
    return actions


# --- run ---------------------------------------------------------------------

def run(cfg: C.Config, today: date, status_only: bool = False) -> dict:
    state = C.load_state(cfg.state)
    start, end = week_bounds(today, state)
    report = {"today": today.isoformat(), "week_ending": end.isoformat(), "actions": []}
    if not status_only:
        for wk_end in claim_weeks(cfg, state, today):
            if ensure_week(cfg, state, wk_end, today):
                report["actions"].append(f"opened week ending {wk_end}")
        for p in sorted(cfg.log_dir.glob("week-ending-*.md")):
            _, changed = recount(p)
            if changed:
                report["actions"].append(f"recounted {p.name}")
        report["actions"] += tend_nudges(cfg, state, today, load_weeks(cfg))
    weeks = load_weeks(cfg)
    prev_end = start - timedelta(days=1)
    for label, wk in (("this_week", end), ("last_week", prev_end)):
        w = weeks.get(wk)
        report[label] = None if w is None else {
            "week_ending": wk.isoformat(), "required": state.required, "solid": w["solid"],
            "check": w["check"], "no": w["no"], "missing": w["missing"],
            "claim_filed": w["fm"].get("claim_filed"),
        }
    return report


def stamp_filed(cfg: C.Config, week_end: date, filed: date) -> str:
    """Record that a week's claim was filed, on the week file and its nudge line."""
    path = week_path(cfg, week_end)
    if not path.exists():
        raise ClerkError(f"No log for the week ending {week_end}.")
    set_frontmatter(path, {"claim_filed": filed.isoformat()})
    if cfg.nudges.exists():
        lines = read_text(cfg.nudges).splitlines()
        for i, line in enumerate(lines):
            m = TODO_RE.match(line)
            if m and m.group(1) == " " and (c := CLAIM_RE.search(m.group(4))) and c.group(1) == week_end.isoformat():
                lines[i] = line.replace("- [ ]", "- [x]", 1) + f" ✅ {filed.isoformat()}"
        cfg.nudges.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return f"claim for the week ending {week_end} marked filed on {filed}"


# --- entries -----------------------------------------------------------------

def kind_fields(state: C.State, kind: str) -> list[str]:
    for k in state.kinds:
        if k["name"].lower() == kind.strip().lower():
            return list(k["fields"])
    names = ", ".join(k["name"] for k in state.kinds)
    raise ClerkError(f"{state.name} has no activity kind {kind!r}; kinds are: {names}")


def add_entry(cfg: C.Config, state: C.State, when: date, kind: str, fields: dict, fit: str,
              reason: str = "", allow_missing: bool = False, today: date | None = None) -> dict:
    """Write one activity into the week it happened in. Refuses guesses and sensitive numbers."""
    fit = fit.strip().lower()
    if fit not in ("solid", "check"):
        raise ClerkError("An agent writes solid or check. Only the person whose log it is writes no.")
    start, end = week_bounds(when, state)
    if (cfg.claim_start and when < cfg.claim_start) or (cfg.claim_end and when > cfg.claim_end):
        raise ClerkError(f"{when} is outside the claim period set in perkins.toml; nothing written.")
    # One line per field: a line break in a value could forge a heading in a legal log.
    fields = {k: " ".join(str(v).split()).lstrip("#").strip() for k, v in fields.items()}
    reason = " ".join(reason.split()).lstrip("#").strip()
    refuse_sensitive({**fields, "Reason": reason})
    wanted = kind_fields(state, kind)
    kind_name = next(k["name"] for k in state.kinds if k["name"].lower() == kind.strip().lower())
    values = {"Contact date": when.isoformat(), "Kind": kind_name}
    values.update({k: str(v).strip() for k, v in fields.items() if str(v).strip()})
    missing = [f for f in wanted if not values.get(f)]
    if missing and not allow_missing:
        raise ClerkError("Missing fields: " + ", ".join(missing) + ". Ask for them; never guess.")
    for f in missing:
        values[f] = f"MISSING: {f.lower()} needed"
    if fit == "solid" and (missing or any(str(v).upper().startswith("MISSING") for v in values.values())):
        fit = "check"
        reason = reason or "A required field is blank."
    if fit == "check" and not reason:
        raise ClerkError("A check entry needs one sentence saying why.")
    ensure_week(cfg, state, end, today or when)
    path = week_path(cfg, end)
    order = wanted + [f for f in EXTRA_FIELDS if f not in wanted]
    order += [k for k in values if k not in order]
    bullets = [f"- **{k}:** {values[k]}" for k in order if values.get(k)]
    bullets.append(f"- **Fit:** {fit}." + (f" {reason.strip()}" if reason.strip() else ""))
    title = " · ".join(x for x in (values.get("Employer or business name"),
                                     values.get("Job title or reference number"),
                                     values.get("What activity")) if x) or kind
    text = read_text(path)
    lines = text.splitlines()
    heads = [i for i, l in enumerate(lines) if l.startswith("## ") and is_activity_heading(l[3:])]
    slot = None
    for n, i in enumerate(heads):
        nxt = heads[n + 1] if n + 1 < len(heads) else len(lines)
        if [l for l in lines[i + 1:nxt] if l.strip()] == [OPEN_SLOT]:
            slot = (i, nxt)
            break
    number = (heads.index(slot[0]) + 1) if slot else len(heads) + 1
    block = [f"## Activity {number}: {title}", "", *bullets, ""]
    if slot:
        lines[slot[0]:slot[1]] = block
    else:
        while lines and not lines[-1].strip():
            lines.pop()
        lines += ["", *block]
    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8", newline="\n")
    w, _ = recount(path)
    return {"week_ending": end.isoformat(), "activity": number, "fit": fit, "path": str(path),
            "solid": w["solid"], "required": state.required,
            "claim_filed": w["fm"].get("claim_filed"),
            "warning": ("This week's claim is already filed. A filed claim doesn't change on its own; "
                        "tell the agency if it matters.") if C.DATE_RE.match(w["fm"].get("claim_filed", "")) else ""}


# --- CLI ---------------------------------------------------------------------

def add_arguments(p) -> None:
    sub = p.add_subparsers(dest="clerk_action")
    r = sub.add_parser("run", help="open, recount, and tend nudges (the default)")
    r.add_argument("--status", action="store_true", help="report only, change nothing")
    f = sub.add_parser("filed", help="mark a week's claim filed")
    f.add_argument("--week", required=True, help="the week's last day, YYYY-MM-DD")
    f.add_argument("--on", help="the date you filed, YYYY-MM-DD (default today)")
    a = sub.add_parser("add", help="write one activity into its week's log")
    a.add_argument("--date", required=True, help="the day the activity happened, YYYY-MM-DD")
    a.add_argument("--kind", required=True, help="an activity kind from the state file")
    a.add_argument("--field", action="append", default=[], metavar="NAME=VALUE")
    a.add_argument("--fit", required=True, choices=["solid", "check"])
    a.add_argument("--reason", default="", help="why it's check (one sentence)")
    a.add_argument("--allow-missing", action="store_true", help="write MISSING blanks instead of refusing")


def cli(args, cfg: C.Config, today: date) -> int:
    action = getattr(args, "clerk_action", None) or "run"
    if not cfg.claim_records:
        if action == "run":
            print("Claims tracking is off (mode is Search), so the clerk has nothing to do.")
            return 0
        raise ClerkError("Claims tracking is off and there's no claim log here, so nothing was recorded. "
                         "Turn claims tracking on with setup first.")
    state = C.load_state(cfg.state)
    if action == "filed":
        on = date.fromisoformat(args.on) if args.on else today
        print(stamp_filed(cfg, date.fromisoformat(args.week), on))
        return 0
    if action == "add":
        fields = {}
        for pair in args.field:
            if "=" not in pair:
                raise ClerkError(f"--field takes NAME=VALUE, not {pair!r}")
            k, v = pair.split("=", 1)
            fields[k.strip()] = v.strip()
        out = add_entry(cfg, state, date.fromisoformat(args.date), args.kind, fields, args.fit,
                        args.reason, args.allow_missing, today)
        tend_nudges(cfg, state, today, load_weeks(cfg))
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    print(json.dumps(run(cfg, today, status_only=getattr(args, "status", False)), indent=2, ensure_ascii=False))
    return 0
