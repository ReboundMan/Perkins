"""Read and edit tracker.md: a Markdown file of sections, each holding one table.

Everything outside the tables (headings, notes, blank lines) is kept exactly as
written. Rows are newest first, so new rows go to the top of their table.

CLI (through run.py):
  tracker show [SECTION] [--json]
  tracker add SECTION --set "Col=Value" ...
  tracker update SECTION --match "Col=Value" ... --set "Col=Value" ...
  tracker move FROM TO --match "Col=Value" ... [--set "Col=Value" ...]
  tracker remove SECTION --match "Col=Value" ...
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .errors import PerkinsError
from .guard import refuse_sensitive

SUBMITTED = "Submitted"
CONVERSATIONS = "Conversations and referrals"
CONSIDERING = "Considering"
PASSED = "Passed"
WATCH = "Employers to watch"
SECTIONS = (SUBMITTED, CONVERSATIONS, CONSIDERING, PASSED, WATCH)
CLAIM_COL = "Claim log"
CLAIM_TABLES = (SUBMITTED, CONVERSATIONS)

COLUMNS = {
    SUBMITTED: ["Submitted", "Company", "Role", "Req or ID", "Channel", "Resume used", "Status",
                "Next follow-up", "Follow-up notes"],
    CONVERSATIONS: ["Date", "Company", "Person", "About", "Status", "Next follow-up", "Follow-up notes"],
    CONSIDERING: ["Found", "Company", "Role", "Where", "Base pay", "Resume", "Status", "Next step"],
    PASSED: ["Date", "Company", "Role", "Why"],
    WATCH: ["Company", "Why watch", "Where to look", "Board", "Application limit", "Last checked", "Next check"],
}
# With claims tracking the Claim log column sits just before Next follow-up.
CLAIM_COL_BEFORE = "Next follow-up"

LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")


class TrackerError(PerkinsError):
    """The tracker could not be read or changed as asked; the message says why."""


def plain(cell: str) -> str:
    """A cell's text without Markdown links or emphasis."""
    return LINK_RE.sub(r"\1", cell).replace("**", "").replace("*", "").replace("`", "").strip()


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|") and not s.endswith("\\|"):
        s = s[:-1]
    cells, cur, i = [], [], 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s) and s[i + 1] == "|":
            cur.append("\\|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    cells.append("".join(cur).strip())
    return cells


def clean_cell(value: str) -> str:
    """Make a value safe for one table cell: one line, pipes escaped."""
    v = " ".join(str(value).replace("\r", " ").replace("\n", " ").split())
    return re.sub(r"(?<!\\)\|", r"\\|", v)


def join_row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def is_separator(cells: list[str]) -> bool:
    return bool(cells) and all(c and set(c) <= set("-: ") for c in cells)


@dataclass
class Table:
    header: list[str]
    rows: list[list[str]] = field(default_factory=list)

    def col(self, name: str) -> int:
        want = name.strip().lower()
        for i, h in enumerate(self.header):
            if h.strip().lower() == want:
                return i
        raise TrackerError(f"No column {name!r}; columns are: {', '.join(self.header)}")

    def has(self, name: str) -> bool:
        return any(h.strip().lower() == name.strip().lower() for h in self.header)

    def get(self, row: list[str], name: str, default: str = "") -> str:
        if not self.has(name):
            return default
        i = self.col(name)
        return row[i] if i < len(row) else default

    def dicts(self) -> list[dict]:
        return [{h: (r[i] if i < len(r) else "") for i, h in enumerate(self.header)} for r in self.rows]

    def normalized(self, row: list[str]) -> list[str]:
        """The row padded to the header's width. A row with extra cells (usually an unescaped
        | typed by hand) keeps them, joined into its last cell, so no text is ever dropped."""
        n = len(self.header)
        if len(row) > n:
            row = row[: n - 1] + [" \\| ".join(c for c in row[n - 1:])]
        return row + [""] * (n - len(row))


@dataclass
class Tracker:
    path: Path
    # blocks: ("text", line) or ("table", section, Table)
    blocks: list = field(default_factory=list)
    newline: str = "\n"  # the file's own line ending, kept on save

    @classmethod
    def load(cls, path: Path) -> "Tracker":
        path = Path(path)
        if not path.is_file():
            raise TrackerError(f"No tracker at {path}. Run setup first.")
        try:
            text = path.read_bytes().decode("utf-8")
        except UnicodeDecodeError as e:
            raise TrackerError(f"{path} isn't UTF-8 text (byte {e.start}). Fix or remove that character.") from e
        newline = "\r\n" if "\r\n" in text else "\n"
        # Split on real line breaks only; str.splitlines would also split on U+2028 and friends
        # pasted into a cell, and the rest of that table would silently vanish.
        lines = text.replace("\r\n", "\n").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        blocks, section, i, seen = [], None, 0, set()
        while i < len(lines):
            line = lines[i]
            if line.startswith("## "):
                section = line[3:].strip()
            if line.strip().startswith("|"):
                raw = []
                while i < len(lines) and lines[i].strip().startswith("|"):
                    raw.append(split_row(lines[i]))
                    i += 1
                header = raw[0]
                rows = [r for r in raw[1:] if not is_separator(r)]
                if section and section.lower() in seen:
                    raise TrackerError(f"{path.name} has two tables under '## {section}'. Merge them into one, "
                                       "then run the command again.")
                if section:
                    seen.add(section.lower())
                blocks.append(("table", section, Table(header, rows)))
                continue
            blocks.append(("text", line))
            i += 1
        return cls(path, blocks, newline)

    def save(self) -> None:
        out = []
        for b in self.blocks:
            if b[0] == "text":
                out.append(b[1])
            else:
                t = b[2]
                out.append(join_row(t.header))
                out.append("|" + "|".join("---" for _ in t.header) + "|")
                out.extend(join_row(t.normalized(r)) for r in t.rows)
        self.path.write_text(self.newline.join(out) + self.newline, encoding="utf-8", newline="")

    # --- lookup ---------------------------------------------------------------

    def section_name(self, name: str) -> str:
        want = name.strip().lower()
        names = [b[1] for b in self.blocks if b[0] == "table" and b[1]]
        for n in names:
            if n.lower() == want:
                return n
        hits = [n for n in names if n.lower().startswith(want)]
        if len(hits) == 1:
            return hits[0]
        raise TrackerError(f"No table named {name!r}; tables are: {', '.join(names)}")

    def table(self, name: str) -> Table:
        real = self.section_name(name)
        for b in self.blocks:
            if b[0] == "table" and b[1] == real:
                return b[2]
        raise TrackerError(f"No table named {name!r}")

    def maybe_table(self, name: str) -> Table | None:
        try:
            return self.table(name)
        except TrackerError:
            return None

    def find(self, name: str, match: dict) -> list[int]:
        """Rows matching every value (case-insensitive, links ignored). Exact matches win; only
        when no row matches exactly does a value match as part of a cell ("Larkspur" finds
        "Larkspur Analytics")."""
        t = self.table(name)
        cols = {k: t.col(k) for k in match}
        want = {k: str(v).strip().lower() for k, v in match.items()}
        rows = [(i, t.normalized(r)) for i, r in enumerate(t.rows)]
        exact = [i for i, r in rows if all(plain(r[cols[k]]).lower() == v for k, v in want.items())]
        if exact:
            return exact
        return [i for i, r in rows if all(v and v in plain(r[cols[k]]).lower() for k, v in want.items())]

    def find_one(self, name: str, match: dict) -> int:
        hits = self.find(name, match)
        if not hits:
            raise TrackerError(f"No row in {name} matches {match}")
        if len(hits) > 1:
            raise TrackerError(f"{len(hits)} rows in {name} match {match}; add another --match to pick one")
        return hits[0]

    # --- edits ----------------------------------------------------------------

    def add(self, name: str, values: dict, top: bool = True) -> None:
        if not any(str(v).strip() for v in values.values()):
            raise TrackerError("Nothing to add: give at least one --set Column=Value.")
        t = self.table(name)
        row = [""] * len(t.header)
        for k, v in values.items():
            row[t.col(k)] = clean_cell(v)
        if top:
            t.rows.insert(0, row)
        else:
            t.rows.append(row)

    def update(self, name: str, idx: int, values: dict) -> None:
        t = self.table(name)
        row = t.normalized(t.rows[idx])
        for k, v in values.items():
            row[t.col(k)] = clean_cell(v)
        t.rows[idx] = row

    def move(self, src: str, dst: str, idx: int, values: dict) -> None:
        """Move a row to the top of another table, carrying every column the two share."""
        s, d = self.table(src), self.table(dst)
        old = dict(zip(s.header, s.normalized(s.rows[idx])))
        new = [""] * len(d.header)
        for i, h in enumerate(d.header):
            for k, v in old.items():
                if k.lower() == h.lower():
                    new[i] = v
        for k, v in values.items():
            new[d.col(k)] = clean_cell(v)
        del s.rows[idx]
        d.rows.insert(0, new)

    def ensure_column(self, name: str, col: str, before: str | None = None) -> bool:
        """Add an empty column if it is missing. Never touches an existing cell. Returns True if added."""
        t = self.maybe_table(name)
        if t is None or t.has(col):
            return False
        pos = t.col(before) if before and t.has(before) else len(t.header)
        # Square each row at the old width first: padded to the new width, it would gain a
        # stray empty cell on top of the inserted one.
        rows = [t.normalized(r) for r in t.rows]
        t.header.insert(pos, col)
        t.rows = [r[:pos] + [""] + r[pos:] for r in rows]
        return True


def parse_pairs(pairs: list[str] | None, flag: str) -> dict:
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise TrackerError(f"{flag} takes Column=Value, not {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _row_text(tr: Tracker, section: str, idx: int) -> str:
    t = tr.table(section)
    return " | ".join(plain(c) for c in t.normalized(t.rows[idx]) if plain(c))[:160]


def cli(args, cfg, today=None) -> int:
    tr = Tracker.load(cfg.tracker)
    if args.action == "show":
        names = [args.section] if args.section else [b[1] for b in tr.blocks if b[0] == "table" and b[1]]
        data = {tr.section_name(n): tr.table(n).dicts() for n in names}
        if args.json:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            for n, rows in data.items():
                print(f"{n}: {len(rows)} row{'s' if len(rows) != 1 else ''}")
                for r in rows:
                    print("  " + " | ".join(plain(v) for v in r.values() if v))
        return 0
    if not args.section:
        raise TrackerError(f"tracker {args.action} needs a table name, such as Considering.")
    if args.action == "move" and not args.to:
        raise TrackerError("tracker move needs the table to move the row to, such as: move Considering Submitted")
    sets = parse_pairs(args.set, "--set")
    match = parse_pairs(args.match, "--match")
    refuse_sensitive(sets)
    touched = ""
    if args.action == "add":
        tr.add(args.section, sets)
    elif args.action == "update":
        if not match:
            raise TrackerError("update needs at least one --match")
        idx = tr.find_one(args.section, match)
        touched = _row_text(tr, args.section, idx)
        tr.update(args.section, idx, sets)
    elif args.action == "move":
        if not match:
            raise TrackerError("move needs at least one --match")
        idx = tr.find_one(args.section, match)
        touched = _row_text(tr, args.section, idx)
        tr.move(args.section, args.to, idx, sets)
    elif args.action == "remove":
        if not match:
            raise TrackerError("remove needs at least one --match")
        idx = tr.find_one(args.section, match)
        touched = _row_text(tr, args.section, idx)
        del tr.table(args.section).rows[idx]
    tr.save()
    print(f"{args.action}: done ({tr.path.name})" + (f": {touched}" if touched else ""))
    return 0
