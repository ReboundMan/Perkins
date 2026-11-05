"""Where the data folder lives, what perkins.toml says, and the active state's rules.

The data folder is found in this order: an explicit --data path, the PERKINS_HOME
environment variable, the one-line pointer file ~/.perkins that setup writes, and
finally ~/job-search. Stdlib only.
"""
from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

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

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ConfigError(Exception):
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

    @property
    def claims(self) -> bool:
        return self.mode == CLAIMS

    @property
    def mode_name(self) -> str:
        return MODE_NAMES.get(self.mode, self.mode)

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
    claims = raw.get("claims", {}) or {}
    git = raw.get("git", {}) or {}
    cfg = Config(
        home=root,
        mode=str(raw.get("mode", SEARCH)),
        timezone=str(raw.get("timezone", "") or ""),
        weekly_target=int(raw.get("weekly_target", 0) or 0),
        hold_extras=bool(raw.get("hold_extras", False)),
        docs_mirror=bool(raw.get("docs_mirror", False)),
        docs_id=str(raw.get("docs_id", "") or ""),
        state=str(claims.get("state", "") or "").lower(),
        claim_start=_as_date(claims.get("claim_start"), "claims.claim_start"),
        claim_end=_as_date(claims.get("claim_end"), "claims.claim_end"),
        git_commit=bool(git.get("commit", False)),
        git_push=bool(git.get("push", False)),
        scan=dict(raw.get("scan", {}) or {}),
    )
    if cfg.mode not in MODES:
        raise ConfigError(f"mode must be one of {', '.join(MODES)}, not {cfg.mode!r}")
    if cfg.weekly_target < 0:
        raise ConfigError("weekly_target cannot be negative")
    if cfg.claims and not cfg.state:
        raise ConfigError("Claims tracking needs a state: set [claims] state in perkins.toml (for example \"wa\").")
    return cfg


def _toml_str(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


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

    @property
    def week_end(self) -> int:
        return (self.week_start + 6) % 7


def _weekday(value: str, key: str) -> int:
    v = str(value).strip().lower()
    if v not in WEEKDAYS:
        raise ConfigError(f"{key} must be a weekday name, not {value!r}")
    return WEEKDAYS.index(v)


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
            kinds=list(raw.get("kinds", [])),
            contact_rule=raw.get("contact_rule", ""),
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
            pass  # unknown zone or no tz database (pip install tzdata on Windows): fall back to local
    return date.today()


def weekday_name(d: date) -> str:
    return WEEKDAYS[d.weekday()].capitalize()
