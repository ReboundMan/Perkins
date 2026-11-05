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


class TrackerError(Exception):
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
        return (row + [""] * len(self.header))[: len(self.header)]


@dataclass
class Tracker:
    path: Path
    # blocks: ("text", line) or ("table", section, Table)
    blocks: list = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "Tracker":
        path = Path(path)
        if not path.is_file():
            raise TrackerError(f"No tracker at {path}. Run setup first.")
        lines = path.read_text(encoding="utf-8").splitlines()
        blocks, section, i = [], None, 0
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
                blocks.append(("table", section, Table(header, rows)))
                continue
            blocks.append(("text", line))
            i += 1
        return cls(path, blocks)

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
        self.path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")

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
        """Rows whose cells contain each match value (case-insensitive, links ignored)."""
        t = self.table(name)
        cols = {k: t.col(k) for k in match}
        out = []
        for idx, row in enumerate(t.rows):
            row = t.normalized(row)
            if all(str(v).strip().lower() in plain(row[cols[k]]).lower() for k, v in match.items()):
                out.append(idx)
        return out

    def find_one(self, name: str, match: dict) -> int:
        hits = self.find(name, match)
        if not hits:
            raise TrackerError(f"No row in {name} matches {match}")
        if len(hits) > 1:
            raise TrackerError(f"{len(hits)} rows in {name} match {match}; add another --match to pick one")
        return hits[0]

    # --- edits ----------------------------------------------------------------

    def add(self, name: str, values: dict, top: bool = True) -> None:
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
        t.header.insert(pos, col)
        t.rows = [t.normalized(r)[:pos] + [""] + t.normalized(r)[pos:] for r in t.rows]
        return True


def parse_pairs(pairs: list[str] | None, flag: str) -> dict:
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise TrackerError(f"{flag} takes Column=Value, not {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def cli(args, cfg) -> int:
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
    sets = parse_pairs(args.set, "--set")
    match = parse_pairs(args.match, "--match")
    if args.action == "add":
        tr.add(args.section, sets)
    elif args.action == "update":
        if not match:
            raise TrackerError("update needs at least one --match")
        tr.update(args.section, tr.find_one(args.section, match), sets)
    elif args.action == "move":
        if not match:
            raise TrackerError("move needs at least one --match")
        tr.move(args.section, args.to, tr.find_one(args.section, match), sets)
    elif args.action == "remove":
        if not match:
            raise TrackerError("remove needs at least one --match")
        del tr.table(args.section).rows[tr.find_one(args.section, match)]
    tr.save()
    print(f"{args.action}: done ({tr.path.name})")
    return 0
