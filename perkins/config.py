"""Where the data folder lives, what perkins.toml says, and the active state's rules.

The data folder is found in this order: an explicit --data path, the PERKINS_HOME
environment variable, the one-line pointer file ~/.perkins that setup writes, and
finally ~/job-search. Stdlib only.
"""
from __future__ import annotations

import os
import re
import sys
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from .errors import PerkinsError

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
STATES_DIR = PLUGIN_ROOT / "states"
TEMPLATES_DIR = PLUGIN_ROOT / "templates"
POINTER = Path.home() / ".perkins"
DEFAULT_HOME = Path.home() / "job-search"
CONFIG_NAME = "perkins.toml"

SEARCH = "search"
CLAIMS = "search-claims"
MODES = (SEARCH, CLAIMS)
MODE_NAMES = {SEARCH: "Search", CLAIMS: "Search with tracking for Unemployment Claims"}

# The one-line guidance wording every screen that shows a state's rules carries. One constant,
# so the claim log page, the dashboard, and status can't drift apart.
GUIDANCE_LINE = ("Guidance only: {agency}'s rules can change at any time, take precedence over Perkins, "
                 "and are yours to know and meet.")

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ConfigError(PerkinsError):
    """A setting is missing or wrong; the message says how to fix it."""


def find_home(explicit: str | Path | None = None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env = os.environ.get("PERKINS_HOME", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    try:
        text = POINTER.read_text(encoding="utf-8").strip()
    except OSError:
        text = ""
    if text:
        return Path(text).expanduser().resolve()
    return DEFAULT_HOME


def _as_date(value, key: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and DATE_RE.match(value.strip()):
        return date.fromisoformat(value.strip())
    raise ConfigError(f"{key} must be a date like 2026-10-04, not {value!r}")


def _as_bool(value, key: str, default: bool = False) -> bool:
    """Only a real TOML true or false counts. A string like "false" is an error, never True."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise ConfigError(f"{key} must be true or false (no quotes), not {value!r}")


def _as_int(value, key: str) -> int:
    if value in (None, ""):
        return 0
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{key} must be a whole number, not {value!r}")
    return value


CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _check_control(raw, path: str = "") -> None:
    r"""A control character in a value almost always means TOML ate a backslash: in double
    quotes, \b is a backspace. Refuse it, naming the key, before it spreads."""
    if isinstance(raw, dict):
        for k, v in raw.items():
            _check_control(v, f"{path}.{k}" if path else k)
    elif isinstance(raw, list):
        for v in raw:
            _check_control(v, path)
    elif isinstance(raw, str) and CONTROL.search(raw):
        raise ConfigError(f"{path} holds a control character, usually a backslash TOML read as an escape. "
                          "Write regular expressions in single quotes, like '\\bVP\\b', or double each backslash.")


def check_timezone(tz: str) -> None:
    if not tz:
        return
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError:  # pragma: no cover
        return
    try:
        ZoneInfo(tz)
    except ZoneInfoNotFoundError as e:
        raise ConfigError(f"Unknown time zone {tz!r}. Use a name like America/Los_Angeles "
                          "(on Windows, also run: pip install tzdata).") from e
    except ValueError as e:
        raise ConfigError(f"Unknown time zone {tz!r}. Use a name like America/Los_Angeles.") from e


@dataclass
class Config:
    home: Path
    mode: str = SEARCH
    timezone: str = ""
    weekly_target: int = 0
    hold_extras: bool = False
    docs_mirror: bool = False
    docs_id: str = ""
    state: str = ""
    claim_start: date | None = None
    claim_end: date | None = None
    git_commit: bool = False
    git_push: bool = False
    scan: dict = field(default_factory=dict)
    # [[claims.adjustment]]: the agency changed this person's weekly requirement for a stretch of
    # weeks. Only from the person's own words about what the agency told them; never inferred.
    adjustments: list[dict] = field(default_factory=list)

    @property
    def claims(self) -> bool:
        return self.mode == CLAIMS

    @property
    def mode_name(self) -> str:
        return MODE_NAMES.get(self.mode, self.mode)

    @property
    def claim_records(self) -> bool:
        """True while there is claim bookkeeping to keep: claims tracking is on, or it was turned
        off at a claim's end and that claim's log is still there (its last claim reminder stays
        until it is filed)."""
        return self.claims or bool(self.state and self.claim_end and self.log_dir.is_dir())

    # The folder layout is fixed on purpose: every skill and script finds the same files.
    @property
    def config_path(self) -> Path: return self.home / CONFIG_NAME
    @property
    def master(self) -> Path: return self.home / "master.md"
    @property
    def tailoring_model(self) -> Path: return self.home / "tailoring-model.md"
    @property
    def style(self) -> Path: return self.home / "style.md"
    @property
    def fact_sheet(self) -> Path: return self.home / "fact-sheet.md"
    @property
    def tracker(self) -> Path: return self.home / "tracker.md"
    @property
    def dashboard(self) -> Path: return self.home / "dashboard.html"
    @property
    def claim_log(self) -> Path: return self.home / "claim-log.html"
    @property
    def applications(self) -> Path: return self.home / "applications"
    @property
    def log_dir(self) -> Path: return self.home / "log"
    @property
    def evidence_dir(self) -> Path: return self.log_dir / "evidence"
    @property
    def nudges(self) -> Path: return self.home / "nudges.md"
    @property
    def baseline(self) -> Path: return self.home / "baseline.json"


def load(home: str | Path | None = None) -> Config:
    """Read perkins.toml from the data folder. A missing file is an error that says to run setup."""
    root = find_home(home)
    path = root / CONFIG_NAME
    if not path.is_file():
        raise ConfigError(f"No {CONFIG_NAME} in {root}. Run setup first (/perkins:setup, or: python run.py init --data <folder>).")
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path} is not valid TOML: {e}") from e
    _check_control(raw)
    claims = raw.get("claims", {}) or {}
    git = raw.get("git", {}) or {}
    cfg = Config(
        home=root,
        mode=str(raw.get("mode", SEARCH)),
        timezone=str(raw.get("timezone", "") or ""),
        weekly_target=_as_int(raw.get("weekly_target"), "weekly_target"),
        hold_extras=_as_bool(raw.get("hold_extras"), "hold_extras"),
        docs_mirror=_as_bool(raw.get("docs_mirror"), "docs_mirror"),
        docs_id=str(raw.get("docs_id", "") or ""),
        state=str(claims.get("state", "") or "").lower(),
        claim_start=_as_date(claims.get("claim_start"), "claims.claim_start"),
        claim_end=_as_date(claims.get("claim_end"), "claims.claim_end"),
        git_commit=_as_bool(git.get("commit"), "git.commit"),
        git_push=_as_bool(git.get("push"), "git.push"),
        scan=dict(raw.get("scan", {}) or {}),
        adjustments=check_adjustments(claims.get("adjustment", []) or []),
    )
    if cfg.mode not in MODES:
        raise ConfigError(f"mode must be one of {', '.join(MODES)}, not {cfg.mode!r}")
    if cfg.weekly_target < 0:
        raise ConfigError("weekly_target cannot be negative")
    if cfg.claim_start and cfg.claim_end and cfg.claim_end < cfg.claim_start:
        raise ConfigError(f"claim_end ({cfg.claim_end}) is before claim_start ({cfg.claim_start}).")
    check_timezone(cfg.timezone)
    if cfg.claims and not cfg.state:
        raise ConfigError("Claims tracking needs a state: set [claims] state in perkins.toml (for example \"wa\").")
    return cfg


def check_adjustments(items) -> list[dict]:
    """Each adjustment: from (a date), to (an optional date on or after from), required (a whole
    number, 0 or more; 0 means the agency waived the work search), and reason (the person's words,
    one line, never a claimant ID or the like)."""
    from .guard import refuse_sensitive
    if not isinstance(items, list):
        raise ConfigError("claims.adjustment must be a list of [[claims.adjustment]] tables.")
    out = []
    for a in items:
        if not isinstance(a, dict):
            raise ConfigError("Each [[claims.adjustment]] needs from, required, and reason.")
        start = _as_date(a.get("from"), "claims.adjustment from")
        if start is None:
            raise ConfigError("Each [[claims.adjustment]] needs from, the first day it applies.")
        end = _as_date(a.get("to"), "claims.adjustment to")
        if end and end < start:
            raise ConfigError(f"claims.adjustment to ({end}) is before from ({start}).")
        req = a.get("required")
        if isinstance(req, bool) or not isinstance(req, int) or req < 0:
            raise ConfigError(f"claims.adjustment required must be a whole number, 0 or more, not {req!r}.")
        reason = " ".join(CONTROL.sub(" ", str(a.get("reason", "") or "")).split()).lstrip("#").strip()
        if not reason:
            raise ConfigError("Each [[claims.adjustment]] needs a reason: what the agency told you, and when.")
        refuse_sensitive({"Adjustment reason": reason})
        out.append({"from": start, "to": end, "required": req, "reason": reason})
    return sorted(out, key=lambda a: a["from"])


def claim_adjustments(cfg: "Config", state: "State") -> list[dict]:
    """The adjustments that belong to the current claim: one dated before the claim's first week
    is left over from an earlier claim and never applies, even with no end date."""
    if not cfg.claim_start:
        return list(cfg.adjustments)
    first = cfg.claim_start - timedelta(days=(cfg.claim_start.weekday() - state.week_start) % 7)
    return [a for a in cfg.adjustments if a["from"] >= first]


def required_for(cfg: "Config", state: "State", start: date, end: date) -> tuple[int, str]:
    """A claim week's requirement: the state's, unless an adjustment of this claim overlaps the
    week. Where two overlap one week, the one starting later wins."""
    hits = [a for a in claim_adjustments(cfg, state)
            if a["from"] <= end and (a["to"] is None or a["to"] >= start)]
    if not hits:
        return state.required, ""
    a = max(hits, key=lambda a: a["from"])
    return a["required"], a["reason"]


def _toml_str(value: str) -> str:
    out = value.replace("\\", "\\\\").replace('"', '\\"')
    out = CONTROL.sub(lambda m: "\\u%04x" % ord(m.group(0)), out)
    return '"' + out + '"'


def render(cfg: Config) -> str:
    """perkins.toml as text, with comments. Written whole each time; the keys are all known."""
    scan_lines = []
    for key, value in sorted(cfg.scan.items()):
        if isinstance(value, bool):
            scan_lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, int):
            scan_lines.append(f"{key} = {value}")
        elif isinstance(value, list):
            scan_lines.append(f"{key} = [" + ", ".join(_toml_str(str(v)) for v in value) + "]")
        else:
            scan_lines.append(f"{key} = {_toml_str(str(value))}")
    return "\n".join([
        "# Perkins settings. Setup writes this file; edit it by hand or run setup again.",
        "",
        "# \"search\" (tailoring and tracking) or \"search-claims\" (adds the unemployment work-search log).",
        f"mode = {_toml_str(cfg.mode)}",
        "# An IANA time zone such as \"America/Los_Angeles\". Empty means this computer's local time.",
        f"timezone = {_toml_str(cfg.timezone)}",
        "# Applications per week to aim for; 0 means none. With claims tracking it never goes below the state minimum.",
        f"weekly_target = {cfg.weekly_target}",
        "# With claims tracking: suggest holding applications past the target for a later week.",
        f"hold_extras = {'true' if cfg.hold_extras else 'false'}",
        "# Keep a copy of the master and each resume in Claude Docs too, checked against the Markdown files.",
        f"docs_mirror = {'true' if cfg.docs_mirror else 'false'}",
        f"docs_id = {_toml_str(cfg.docs_id)}",
        "",
        "[claims]",
        "# Read only when mode = \"search-claims\". state is a file in the plugin's states/ folder.",
        f"state = {_toml_str(cfg.state)}",
        f"claim_start = {_toml_str(cfg.claim_start.isoformat() if cfg.claim_start else '')}",
        "# Set when the claim ends. Reminders stop after that week; the log is kept.",
        f"claim_end = {_toml_str(cfg.claim_end.isoformat() if cfg.claim_end else '')}",
        "",
        *[line for a in cfg.adjustments for line in (
            "# What the agency told you about your weekly requirement (run.py clerk adjust).",
            "[[claims.adjustment]]",
            f"from = {_toml_str(a['from'].isoformat())}",
            *([f"to = {_toml_str(a['to'].isoformat())}"] if a["to"] else []),
            f"required = {a['required']}",
            f"reason = {_toml_str(a['reason'])}",
            "")],
        "[git]",
        "# Commit the data folder after each logged activity, if it is a git repository. Off by default.",
        f"commit = {'true' if cfg.git_commit else 'false'}",
        f"push = {'true' if cfg.git_push else 'false'}",
        "",
        "[scan]",
        "# Job board scan settings: interval_days, seniority and functions (regular expressions), exclude.",
        *scan_lines,
        "",
    ])


def save(cfg: Config) -> None:
    cfg.home.mkdir(parents=True, exist_ok=True)
    cfg.config_path.write_text(render(cfg), encoding="utf-8", newline="\n")


# --- states ------------------------------------------------------------------

@dataclass
class State:
    code: str
    name: str
    agency: str
    agency_full: str
    last_checked: str
    sources: list[str]
    required: int
    week_start: int          # Monday = 0 ... Sunday = 6
    claim_day: int           # weekday the claim reminder appears, after the week ends
    check_day: int           # weekday the midweek check appears
    raise_day: int           # weekday the check is raised to high priority
    retention: str
    rules: list[str]
    kinds: list[dict]        # [{"name": ..., "fields": [...]}]
    contact_rule: str = ""
    # Optional. A weekly claim filed this many days or more after its week ends is late (0: not set).
    claim_late_days: int = 0
    # Optional. {"employer": <field>, "opening": <field>}: a second same-week contact with one
    # employer potentially counts (a different opening) or is a likely repeat (the same opening).
    distinct_employers: dict = field(default_factory=dict)
    # Optional. One-time tasks counted from the claim's first day: [{"task": ..., "within_days": N}].
    once: list[dict] = field(default_factory=list)

    @property
    def week_end(self) -> int:
        return (self.week_start + 6) % 7


def _weekday(value: str, key: str) -> int:
    v = str(value).strip().lower()
    if v not in WEEKDAYS:
        raise ConfigError(f"{key} must be a weekday name, not {value!r}")
    return WEEKDAYS.index(v)


def guidance_line(agency: str) -> str:
    return GUIDANCE_LINE.format(agency=agency)


KIND_COUNTS = ("yes", "maybe")


def _check_kinds(kinds: list, name: str) -> list[dict]:
    """Each kind needs a name and fields. An optional counts is "yes" (the default) or "maybe";
    a "maybe" kind needs a maybe_reason, which the clerk writes on every entry of that kind."""
    out = []
    for k in kinds:
        if not isinstance(k, dict) or not k.get("name") or not isinstance(k.get("fields"), list):
            raise ConfigError(f"{name}: every [[kinds]] entry needs a name and a list of fields.")
        counts = k.get("counts", "yes")
        if counts not in KIND_COUNTS:
            raise ConfigError(f"{name}: kind {k['name']!r} has counts = {counts!r}; "
                              "it must be \"yes\" or \"maybe\".")
        if counts == "maybe" and not str(k.get("maybe_reason", "")).strip():
            raise ConfigError(f"{name}: kind {k['name']!r} has counts = \"maybe\" but no maybe_reason "
                              "saying why it only potentially counts.")
        if counts == "maybe":
            k = {**k, "maybe_reason": " ".join(str(k["maybe_reason"]).split())}
        out.append(k)
    return out


def _whole(value, what: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"{what} must be a whole number{' above zero' if minimum else ''}, not {value!r}.")
    return value


def _check_optional(raw: dict, kinds: list[dict], name: str) -> dict:
    """The optional keys, validated: each does nothing for a state that doesn't set it."""
    out = {}
    if "claim_late_days" in raw:
        out["claim_late_days"] = _whole(raw["claim_late_days"], f"{name}: claim_late_days", 1)
    if "distinct_employers" in raw:
        de = raw["distinct_employers"]
        if not isinstance(de, dict) or set(de) != {"employer", "opening"}:
            raise ConfigError(f"{name}: distinct_employers needs exactly employer and opening, each a field name.")
        for role in ("employer", "opening"):
            if not isinstance(de[role], str):
                raise ConfigError(f"{name}: distinct_employers {role} must be one field name, not {de[role]!r}.")
            if not any(de[role] in k["fields"] for k in kinds):
                raise ConfigError(f"{name}: distinct_employers {role} names {de[role]!r}, which no kind has.")
        if not any(de["employer"] in k["fields"] and de["opening"] in k["fields"] for k in kinds):
            raise ConfigError(f"{name}: distinct_employers needs one kind with both {de['employer']!r} "
                              f"and {de['opening']!r}.")
        out["distinct_employers"] = dict(de)
    if "once" in raw:
        tasks = raw["once"]
        if not isinstance(tasks, list):
            raise ConfigError(f"{name}: once must be a list of [[once]] tables.")
        for t in tasks:
            if not isinstance(t, dict) or not " ".join(str(t.get("task", "")).split()).rstrip("."):
                raise ConfigError(f"{name}: every [[once]] entry needs a task.")
            _whole(t.get("within_days"), f"{name}: [[once]] within_days", 0)
        out["once"] = [dict(t) for t in tasks]
    return out


def available_states() -> list[str]:
    return sorted(p.stem for p in STATES_DIR.glob("*.toml") if not p.stem.startswith("_"))


def load_state(code: str) -> State:
    code = (code or "").strip().lower()
    if not re.fullmatch(r"[a-z]{2}", code):
        raise ConfigError(f"A state is a two-letter code such as \"wa\", not {code!r}.")
    path = STATES_DIR / f"{code}.toml"
    if not path.is_file():
        have = ", ".join(available_states()) or "none"
        raise ConfigError(f"No rules file for state {code!r} (available: {have}). See states/README.md to add one.")
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    try:
        kinds = _check_kinds(list(raw.get("kinds", [])), path.name)
        return State(
            code=code,
            name=raw["name"],
            agency=raw["agency"],
            agency_full=raw.get("agency_full", raw["agency"]),
            last_checked=str(raw["last_checked"]),
            sources=list(raw["sources"]),
            required=int(raw["required"]),
            week_start=_weekday(raw["week_start"], "week_start"),
            claim_day=_weekday(raw["claim_day"], "claim_day"),
            check_day=_weekday(raw["check_day"], "check_day"),
            raise_day=_weekday(raw["raise_day"], "raise_day"),
            retention=raw.get("retention", ""),
            rules=list(raw.get("rules", [])),
            kinds=kinds,
            contact_rule=raw.get("contact_rule", ""),
            **_check_optional(raw, kinds, path.name),
        )
    except KeyError as e:
        raise ConfigError(f"{path.name} is missing the key {e.args[0]!r}") from e


# --- dates -------------------------------------------------------------------

def today(cfg: Config | None = None) -> date:
    """Today's date in the configured time zone, else this computer's local date."""
    tz = (cfg.timezone if cfg else "") or ""
    if tz:
        try:
            from zoneinfo import ZoneInfo
            return datetime.now(ZoneInfo(tz)).date()
        except Exception:
            # load() already refuses an unknown zone, so this is a missing tz database.
            print(f"Warning: can't use time zone {tz!r} (on Windows: pip install tzdata); "
                  "using this computer's local date.", file=sys.stderr)
    return date.today()


def weekday_name(d: date) -> str:
    return WEEKDAYS[d.weekday()].capitalize()
