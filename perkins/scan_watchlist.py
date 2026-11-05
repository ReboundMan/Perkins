"""Scan the employers to watch for new senior postings and add them to Considering.

Each row in the "Employers to watch" table names a board (Greenhouse, Ashby, Lever,
Workable, BambooHR, Rippling, or Workday) and a Where to look URL. The scan reads
each board's public feed, keeps titles that pass the [scan] filters, skips postings
already seen (baseline.json) or already in the tracker, and adds the rest as leads.
Any other board is a check by hand. A feed that fails is reported, never retried.

CLI (through run.py):
  scan [--dry-run] [--baseline-only] [--json]
  scan --discover FILE [--add] [--json]
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit

from . import config as C
from . import tracker as T
from .feeds import BOARD_NAMES, adapter, workday

INTERVAL_DAYS = 14
DEFAULT_SENIORITY = [
    r"\b[se]?vp\b",
    r"\bvice[\s-]+president\b",
    r"\bhead\s+of\b",
    r"\bchief\b",
    r"\bc(?:eo|fo|to|oo|io|mo|po|ro|so|do|ao|co|iso|hro)\b",
    r"\bpresident\b",
    r"\bgeneral\s+manager\b",
    r"\bdirector\b",
    r"\bprincipal\b",
]

BOARD_CELL = re.compile(r"^\s*([A-Za-z]+)\s*(?:\(\s*([^)]*?)\s*\))?\s*$")
LINK_URL = re.compile(r"\]\((https?://[^)\s]+)\)")
ANY_URL = re.compile(r"https?://[^\s|)\]>]+")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
SLUG_PATTERNS = {
    "greenhouse": re.compile(r"(?:job-)?boards\.(?:eu\.)?greenhouse\.io/(?:embed/job_board\?for=)?([\w-]+)", re.I),
    "ashby": re.compile(r"jobs\.ashbyhq\.com/([^/?#\s]+)", re.I),
    "lever": re.compile(r"jobs\.lever\.co/([^/?#\s]+)", re.I),
    "workable": re.compile(r"apply\.workable\.com/([^/?#\s]+)", re.I),
    "bamboohr": re.compile(r"([\w-]+)\.bamboohr\.com", re.I),
    "rippling": re.compile(r"ats\.rippling\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#\s]+)"),
}
NOT_SLUGS = {"embed", "j", "api", "www", "app"}
DROP_PARAMS = ("utm_", "gh_src", "source", "ref", "lever-source")

DISCOVER_BOARDS = ("greenhouse", "ashby", "lever")
LEGAL_WORDS = {"inc", "incorporated", "llc", "ltd", "limited", "corp", "corporation", "co", "company",
               "plc", "gmbh", "sa", "ag", "lp", "llp"}
TRIM_WORDS = LEGAL_WORDS | {"labs", "lab", "ai", "technologies", "technology", "tech", "software",
                            "systems", "group", "holdings", "hq", "io"}


class ScanError(Exception):
    """The scan could not run as asked; the message says how to fix it."""


# --- filters ----------------------------------------------------------------------

def _patterns(settings: dict, key: str, default: list[str]) -> list[re.Pattern]:
    raw = settings.get(key, default)
    if isinstance(raw, str):
        raw = [raw]
    out = []
    for p in raw or []:
        if not str(p).strip():
            continue
        try:
            out.append(re.compile(str(p), re.I))
        except re.error as e:
            raise ScanError(f"[scan] {key} in perkins.toml has a pattern that is not a valid regular expression: "
                            f"{p!r} ({e})") from e
    return out


@dataclass
class Filters:
    seniority: list[re.Pattern]
    functions: list[re.Pattern]
    exclude: list[re.Pattern]

    @classmethod
    def from_settings(cls, settings: dict | None) -> "Filters":
        s = settings or {}
        return cls(_patterns(s, "seniority", DEFAULT_SENIORITY), _patterns(s, "functions", []),
                   _patterns(s, "exclude", []))

    def match(self, title: str) -> bool:
        """True when a title is senior enough, in a wanted function, and not excluded. Empty lists allow anything."""
        if self.seniority and not any(p.search(title) for p in self.seniority):
            return False
        if self.functions and not any(p.search(title) for p in self.functions):
            return False
        return not any(p.search(title) for p in self.exclude)


# --- reading the watch table ------------------------------------------------------

def parse_board(cell: str) -> tuple[str | None, str]:
    """(adapter key, explicit slug) from a Board cell such as "Greenhouse" or "Greenhouse (larkspur)".

    Returns (None, "") for anything without a feed, such as "Careers site".
    """
    m = BOARD_CELL.match(T.plain(cell or ""))
    if not m or m.group(1).lower() not in BOARD_NAMES:
        return None, ""
    return m.group(1).lower(), (m.group(2) or "").strip()


def where_url(cell: str) -> str:
    """The URL in a Where to look cell, whether a Markdown link or bare."""
    m = LINK_URL.search(cell or "")
    if m:
        return m.group(1)
    m = ANY_URL.search(cell or "")
    return m.group(0) if m else ""


def derive_slug(key: str, url: str) -> str | None:
    """The board's slug (Workday: "tenant.wdN/site") from a Where to look URL, or None."""
    if not url:
        return None
    if key == "workday":
        m = workday.URL_RE.search(url)
        return f"{m.group(1)}.{m.group(2).lower()}/{m.group(3)}" if m else None
    m = SLUG_PATTERNS[key].search(url)
    if not m or m.group(1).lower() in NOT_SLUGS:
        return None
    return unquote(m.group(1))


def norm_url(url: str) -> str:
    """A URL reduced for comparison: no scheme, lowercase host, no trailing slash, no tracking parameters."""
    parts = urlsplit((url or "").strip().rstrip(".,;"))
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith(DROP_PARAMS)]
    path = parts.path.rstrip("/")
    return f"{(parts.hostname or '').lower()}{path}" + (f"?{urlencode(query)}" if query else "")


def tracked_urls(tr: T.Tracker) -> set[str]:
    """Every URL anywhere in Considering, Submitted, and Passed."""
    urls = set()
    for name in (T.CONSIDERING, T.SUBMITTED, T.PASSED):
        table = tr.maybe_table(name)
        for row in table.rows if table else []:
            for cell in row:
                urls.update(norm_url(u) for u in ANY_URL.findall(cell))
    return urls


def _first_date(text: str) -> date | None:
    m = DATE_RE.search(text or "")
    try:
        return date.fromisoformat(m.group(0)) if m else None
    except ValueError:
        return None


# --- baseline ---------------------------------------------------------------------

def load_baseline(path: Path) -> dict[str, list[str]]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ScanError(f"{path} is not valid JSON ({e.msg}). Fix it, or delete it to start every baseline over.") from e
    if not isinstance(data, dict):
        raise ScanError(f"{path} should map each company to a list of job ids.")
    return {str(k): [str(x) for x in v] for k, v in data.items() if isinstance(v, list)}


def save_baseline(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps({k: sorted(set(v)) for k, v in data.items()}, indent=2, sort_keys=True, ensure_ascii=False)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


# --- the scan ---------------------------------------------------------------------

def _interval(cfg: C.Config) -> int:
    try:
        return int(cfg.scan.get("interval_days", INTERVAL_DAYS) or INTERVAL_DAYS)
    except (TypeError, ValueError) as e:
        raise ScanError("[scan] interval_days in perkins.toml must be a whole number of days.") from e


def _role_link(title: str, url: str) -> str:
    safe = title.replace("[", "(").replace("]", ")")
    return f"[{safe}]({url})" if url else safe


def scan(cfg: C.Config, today: date, dry_run: bool = False, baseline_only: bool = False) -> dict:
    """Scan every watched employer with a feed. Returns a report; writes nothing when dry_run."""
    tr = T.Tracker.load(cfg.tracker)
    watch = tr.table(T.WATCH)
    filters = Filters.from_settings(cfg.scan)
    next_check = (today + timedelta(days=_interval(cfg))).isoformat()
    baseline = load_baseline(cfg.baseline)
    known = tracked_urls(tr)
    report = {"date": today.isoformat(), "dry_run": dry_run, "baseline_only": baseline_only,
              "scanned": [], "leads": [], "check_by_hand": [], "already_tracked": 0}
    scanned_rows = []

    for idx, row in enumerate(watch.rows):
        company = T.plain(watch.get(row, "Company"))
        if not company:
            continue
        board_cell = watch.get(row, "Board")
        url = where_url(watch.get(row, "Where to look"))
        key, slug = parse_board(board_cell)
        hand = {"company": company, "board": T.plain(board_cell), "where": url or T.plain(watch.get(row, "Where to look"))}
        if key is None:
            due = _first_date(watch.get(row, "Next check"))
            if due is None or due <= today:
                report["check_by_hand"].append({**hand, "reason": "No feed for this board; check it by hand."})
            continue
        name = BOARD_NAMES[key]
        slug = slug or derive_slug(key, url)
        if not slug:
            report["check_by_hand"].append({**hand, "reason": (
                f"Could not find the {name} board name in Where to look; check by hand, "
                f"or write the Board cell as \"{name} (board-name)\".")})
            continue
        try:
            jobs = adapter(key).list_jobs(slug)
        except Exception as e:  # a failed feed is reported, never retried
            report["check_by_hand"].append({**hand, "reason": f"The {name} feed failed ({e}); check by hand or in the browser."})
            continue

        jobs = [j for j in jobs if j.get("id") or j.get("url")]
        first = company not in baseline
        seen = set(baseline.get(company, []))
        matches = [j for j in jobs if filters.match(j["title"])]
        new = []
        for j in matches:
            if not first and (j["id"] in seen or j["url"] in seen):
                continue
            if j["url"] and norm_url(j["url"]) in known:
                report["already_tracked"] += 1
                continue
            if baseline_only:
                continue
            new.append(j)
            if j["url"]:
                known.add(norm_url(j["url"]))
        baseline[company] = sorted(seen | {j["id"] or j["url"] for j in jobs})
        report["scanned"].append({"company": company, "board": name, "slug": slug, "jobs": len(jobs),
                                  "matches": len(matches), "new": len(new), "first_scan": first})
        report["leads"] += [{"company": company, "title": j["title"], "url": j["url"], "location": j["location"],
                             "posted": j.get("posted", ""), "board": name} for j in new]
        scanned_rows.append(idx)

    if dry_run:
        return report
    for lead in reversed(report["leads"]):  # added bottom-up so the first lead found ends up on top
        tr.add(T.CONSIDERING, {
            "Found": today.isoformat(),
            "Company": lead["company"],
            "Role": _role_link(lead["title"], lead["url"]),
            "Where": lead["location"],
            "Base pay": "not checked",
            "Resume": "Not built",
            "Status": "Lead",
            "Next step": f"Found in the {today.isoformat()} watch-list scan; read the posting",
        })
    dates = {k: v for k, v in (("Last checked", today.isoformat()), ("Next check", next_check)) if watch.has(k)}
    for idx in scanned_rows:
        tr.update(T.WATCH, idx, dates)
    tr.save()
    save_baseline(cfg.baseline, baseline)
    return report


# --- discover ---------------------------------------------------------------------

def slug_candidates(name: str) -> list[str]:
    """Likely board slugs for a company name: joined and hyphenated, then with suffixes like inc, labs, ai trimmed."""
    text = name.lower().replace("&", " and ").replace("'", "").replace("’", "")
    words = re.findall(r"[a-z0-9]+", text)
    out: list[str] = []
    while words:
        for form in ("".join(words), "-".join(words)):
            if form not in out:
                out.append(form)
        if len(words) > 1 and words[-1] in TRIM_WORDS:
            words = words[:-1]
        else:
            break
    return out


def company_key(name: str) -> str:
    """A company name for comparison: lowercase words, legal suffixes such as Inc. dropped."""
    words = re.findall(r"[a-z0-9]+", T.plain(name).lower().replace("&", " and ").replace("'", ""))
    while len(words) > 1 and words[-1] in LEGAL_WORDS:
        words.pop()
    return " ".join(words)


def discover_one(name: str, filters: Filters) -> dict:
    """Try each slug guess on Greenhouse, Ashby, and Lever. A board with postings wins over an empty one."""
    empty = None
    for slug in slug_candidates(name):
        for key in DISCOVER_BOARDS:
            mod = adapter(key)
            try:
                jobs = mod.list_jobs(slug)
            except Exception:
                continue  # most guesses miss; a miss is not an error
            found = {"company": name, "board": BOARD_NAMES[key], "slug": slug, "where": mod.BOARD_URL.format(slug=slug),
                     "jobs": len(jobs), "senior": [{"title": j["title"], "url": j["url"], "location": j["location"]}
                                                   for j in jobs if filters.match(j["title"])]}
            if jobs:
                return found
            empty = empty or found
    if empty:
        empty["note"] = "The board exists but lists no postings; confirm it belongs to this company."
        return empty
    return {"company": name, "board": "", "slug": "", "where": "", "jobs": 0, "senior": [],
            "note": f"No Greenhouse, Ashby, or Lever board under {', '.join(slug_candidates(name)) or 'any guess'}."}


def read_names(path: str | Path) -> list[str]:
    p = Path(path)
    if not p.is_file():
        raise ScanError(f"No file at {p}. --discover takes a text file of company names, one per line.")
    names = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and line not in names:
            names.append(line)
    return names


def discover(cfg: C.Config, today: date, path: str | Path, add: bool = False, dry_run: bool = False) -> dict:
    """Guess boards for each company in a file; with add, append the ones found to the watch table."""
    filters = Filters.from_settings(cfg.scan if cfg else {})
    results = [discover_one(n, filters) for n in read_names(path)]
    added = []
    if add and cfg:
        tr = T.Tracker.load(cfg.tracker)
        watch = tr.table(T.WATCH)
        have = {company_key(watch.get(r, "Company")) for r in watch.rows}
        for r in results:
            if not r["board"] or company_key(r["company"]) in have:
                continue
            tr.add(T.WATCH, {
                "Company": r["company"],
                "Why watch": f"Found by discover on {today.isoformat()}",
                "Where to look": r["where"],
                "Board": r["board"],
                "Next check": today.isoformat(),
            }, top=False)
            have.add(company_key(r["company"]))
            added.append(r["company"])
        if added and not dry_run:
            tr.save()
    return {"date": today.isoformat(), "dry_run": dry_run, "results": results, "added": added}


# --- CLI --------------------------------------------------------------------------

def add_arguments(p) -> None:
    p.add_argument("--dry-run", action="store_true", help="report what would change and write nothing")
    p.add_argument("--baseline-only", action="store_true",
                   help="record what each board lists now without adding any leads")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    p.add_argument("--discover", metavar="FILE", help="find boards for the company names in FILE, one per line")
    p.add_argument("--add", action="store_true", help="with --discover: add the companies found to the watch table")


def scan_text(r: dict) -> str:
    lines = [f"Watch-list scan, {r['date']}" + (" (dry run: nothing written)" if r["dry_run"] else "")
             + (" (baseline only: no leads added)" if r["baseline_only"] else "")]
    lines.append(f"Scanned {len(r['scanned'])} employer{'s' if len(r['scanned']) != 1 else ''}.")
    for s in r["scanned"]:
        extra = ", first scan" if s["first_scan"] else ""
        lines.append(f"  {s['company']} ({s['board']}): {s['jobs']} postings, {s['matches']} match, {s['new']} new{extra}")
    if r["leads"]:
        verb = "would be added" if r["dry_run"] else "added"
        lines.append(f"New leads ({len(r['leads'])}, {verb} to Considering):")
        for lead in r["leads"]:
            where = f" ({lead['location']})" if lead["location"] else ""
            lines.append(f"  {lead['company']}: {lead['title']}{where}")
            if lead["url"]:
                lines.append(f"    {lead['url']}")
    else:
        lines.append("No new leads.")
    if r["already_tracked"]:
        lines.append(f"Skipped {r['already_tracked']} already in the tracker.")
    if r["check_by_hand"]:
        lines.append(f"Check by hand ({len(r['check_by_hand'])}):")
        for h in r["check_by_hand"]:
            where = f" {h['where']}" if h["where"] else ""
            lines.append(f"  {h['company']}:{where}")
            lines.append(f"    {h['reason']}")
    return "\n".join(lines)


def discover_text(r: dict) -> str:
    lines = [f"Board discovery, {r['date']}"]
    for d in r["results"]:
        if d["board"]:
            lines.append(f"  {d['company']}: {d['board']} ({d['slug']}), {d['jobs']} postings, "
                         f"{len(d['senior'])} senior  {d['where']}")
            lines += [f"      {s['title']}" for s in d["senior"]]
        else:
            lines.append(f"  {d['company']}: not found")
        if d.get("note"):
            lines.append(f"    {d['note']}")
    if r["added"]:
        verb = "Would add" if r["dry_run"] else "Added"
        lines.append(f"{verb} to Employers to watch: {', '.join(r['added'])}")
    return "\n".join(lines)


def cli(args, cfg: C.Config, today: date | None = None) -> int:
    today = today or C.today(cfg)
    if args.add and not args.discover:
        raise ScanError("--add only works with --discover FILE.")
    if args.discover:
        r = discover(cfg, today, args.discover, add=args.add, dry_run=args.dry_run)
        print(json.dumps(r, indent=2, ensure_ascii=False) if args.json else discover_text(r))
        return 0
    r = scan(cfg, today, dry_run=args.dry_run, baseline_only=args.baseline_only)
    print(json.dumps(r, indent=2, ensure_ascii=False) if args.json else scan_text(r))
    return 0
