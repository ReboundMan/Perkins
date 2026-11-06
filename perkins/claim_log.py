"""Render the work-search log into claim-log.html: a page for walking a state reviewer through
the log, week by week. Claims tracking only; nothing is built in Search mode unless an ended
claim's log is still in the data folder (the state can ask for it after the claim ends).

Every activity shows the fields the state asks for, in the order the log file has them, and
links to what backs it up: the posting, the resume PDF and cover letter PDF that were sent
(from its applications/ folder), the Claude Docs copy when one is configured, and any
confirmation screenshots from log/evidence, embedded so the page shows them on its own.

Two views. The meeting view, shown on every load, is the log as recorded: a blank field reads
"Not recorded" and the working notes about blanks are left out. "Show prep notes" adds what's
for you alone: each entry's fit grade and reasoning, its source, the week's counts, and the
full text of any blank field.

The week files are the record. This page only reads them and is rebuilt with the dashboard.
CLI: claim-log [--open]
"""
from __future__ import annotations

import base64
import html
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

from . import __version__
from . import clerk as K
from . import config as C
from . import favicon

MAX_EMBED = 8 * 1024 * 1024  # bigger screenshots are linked, not embedded
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
HEADING_RE = re.compile(r"^(?:Activity|Contact)\s+(\d+)\s*(?::\s*(.*))?$", re.I)
EVIDENCE = r"(?<![\w/])log/evidence/[^\s,;()\[\]<>\"']+"
EVIDENCE_RE = re.compile(EVIDENCE)
TOKEN_RE = re.compile(
    r"\[([^\]]+)\]\((https?://[^)\s]+)\)"            # 1, 2: a Markdown link
    r"|(https?://[^\s<>()\"']*[^\s<>().,;:\"'])"     # 3: a bare link
    r"|((?:Screenshot:\s*)?" + EVIDENCE + r")"       # 4: a screenshot reference
    r"|\*\*(.+?)\*\*"                                # 5: bold
    r"|`([^`]+)`"                                    # 6: code
)
APP_REF_RE = re.compile(r"(?<![\w/])applications/(\d{4}-\d{2}-\d{2}-[A-Za-z0-9._-]+)")
FOLDER_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
STOPWORDS = {"of", "the", "and", "a", "an", "for", "to", "at", "in"}
NOT_RECORDED = "<span class='missing'>Not recorded</span>"


# --- text --------------------------------------------------------------------

def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def _a(url: str, label: str) -> str:
    return (f"<a href=\"{esc(url)}\" target=\"_blank\" rel=\"noopener\">{label}"
            "<span class='sr-only'> (opens in a new tab)</span></a>")


def evidence_refs(text: str) -> list[str]:
    return [m.group(0).rstrip(".,;:") for m in EVIDENCE_RE.finditer(text)]


def inline(text: str, evidence: list[str] | None = None) -> str:
    """Escape, then render links, bold, and code. A screenshot reference becomes a pointer to
    the screenshot shown below the entry, and is collected into `evidence`."""
    out, pos = [], 0
    for m in TOKEN_RE.finditer(text):
        out.append(esc(text[pos:m.start()]))
        ltext, lurl, bare, shot, bold, code = m.groups()
        if ltext:
            out.append(_a(lurl, esc(ltext)))
        elif bare:
            out.append(_a(bare, esc(bare)))
        elif shot:
            if evidence is not None:
                evidence += [r for r in evidence_refs(shot) if r not in evidence]
            out.append("<span class='muted'>(screenshot below)</span>")
        elif bold:
            out.append(f"<strong>{esc(bold)}</strong>")
        elif code:
            out.append(f"<code>{esc(code)}</code>")
        pos = m.end()
    out.append(esc(text[pos:]))
    return "".join(out)


def is_blank(value: str) -> bool:
    return value.strip().upper().startswith("MISSING")


def meeting_value(value: str) -> str:
    """The recorded value with the working notes about blanks and screenshots taken out."""
    v = re.sub(r"\s*(?:Screenshot:\s*)?" + EVIDENCE, "", value)
    v = re.sub(r"\s*\([^()]*MISSING:[^()]*\)", "", v)
    v = re.sub(r"\s*MISSING:[^.;]*[.;]?", "", v)
    return v.strip(" ;,·")


def is_fit(name: str) -> bool:
    n = name.strip().lower()
    return n == "fit" or n.endswith(" fit")


# --- applications --------------------------------------------------------------

def slug(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def words(s: str) -> set[str]:
    return {w for w in slug(s).split("-") if w and w not in STOPWORDS}


def app_folders(cfg: C.Config) -> list[tuple[date, str, str]]:
    """(date, the rest of the name, folder name) for every applications/<date>-<...> folder."""
    out = []
    if cfg.applications.is_dir():
        for p in cfg.applications.iterdir():
            m = FOLDER_RE.match(p.name)
            if not (m and p.is_dir()):
                continue
            try:
                out.append((date.fromisoformat(m.group(1)), m.group(2), p.name))
            except ValueError:
                continue
    return sorted(out)


def is_application(fields: dict) -> bool:
    """Whether an entry records an application. A state whose form has a Type field (Washington)
    says so there. Otherwise (Virginia's form has no such field) an entry that points at its
    applications/ folder, or whose result starts with "Applied", is one."""
    low = {k.lower(): v for k, v in fields.items()}
    if "type" in low:
        return "application" in low["type"].lower()
    if any(APP_REF_RE.search(v) for v in fields.values()):
        return True
    return low.get("result and next step", "").strip().lower().startswith("applied")


def match_folder(cfg: C.Config, fields: dict, folders: list) -> str | None:
    """The applications/ folder behind an entry. A path in the entry wins. Otherwise only an
    application is matched, by employer and role, to a folder made on or before the contact
    date; when that leaves more than one role and none matches, nothing is linked, because a
    wrong resume in front of a reviewer is worse than none."""
    for v in fields.values():
        for m in APP_REF_RE.finditer(v):
            name = m.group(1).rstrip(".-")
            if (cfg.applications / name).is_dir():
                return name
    low = {k.lower(): v for k, v in fields.items()}
    if not is_application(fields):
        return None
    company = slug(low.get("employer or business name", ""))
    if not company:
        return None
    try:
        when = date.fromisoformat(low.get("contact date", "")[:10])
    except ValueError:
        when = None
    cands = [f for f in folders if (f[1] == company or f[1].startswith(company + "-"))
             and (when is None or f[0] <= when)]
    role = words(re.sub(r"\([^)]*\)\s*$", "", low.get("job title or reference number", "")
                        or low.get("type of work or position", "")))
    if not role:
        return cands[0][2] if len(cands) == 1 else None
    hits = [f for f in cands if (rest := words(f[1][len(company):])) and (role <= rest or rest <= role)]
    return hits[-1][2] if hits else None  # the latest folder for that role


def cover_letter_sent(result: str) -> bool:
    if not re.search(r"cover letter", result, re.I):
        return False
    return not re.search(r"\b(?:no|without|skipped|not sent|didn't send|did not send)\b[^.;]*cover letter"
                         r"|cover letter[^.;]*\b(?:skipped|not sent|not included)\b", result, re.I)


def docs_url(cfg: C.Config) -> str:
    if not (cfg.docs_mirror and cfg.docs_id.strip()):
        return ""
    d = cfg.docs_id.strip()
    if d.startswith("https://"):
        return d
    return "https://claude.ai/artifact/" + d if re.fullmatch(r"[A-Za-z0-9_-]+", d) else ""


def artifacts(cfg: C.Config, fields: dict, folders: list) -> list[tuple[str, str, bool]]:
    """(label, link, opens a new tab) for each thing that backs an entry up."""
    low = {k.lower(): v for k, v in fields.items()}
    links = []
    posting = next((u for u in re.findall(r"https?://[^\s,()\]<>\"']+", low.get("source", ""))
                    if "claude.ai" not in u), None)
    if posting:
        links.append(("Posting", posting.rstrip(".,;:"), True))
    folder = match_folder(cfg, fields, folders)
    if folder:
        base = cfg.applications / folder
        rel = "applications/" + quote(folder) + "/"
        if (base / "resume.pdf").is_file():
            links.append(("Resume sent (PDF)", rel + "resume.pdf", False))
        if (base / "cover-letter.pdf").is_file() and cover_letter_sent(low.get("result and next step", "")):
            links.append(("Cover letter sent (PDF)", rel + "cover-letter.pdf", False))
        if (url := docs_url(cfg)):
            links.append(("Resume in Claude Docs", url, True))
    return links


def evidence_html(cfg: C.Config, rel: str) -> str:
    name = esc(Path(rel).name)
    base = cfg.evidence_dir.resolve()
    p = (cfg.home / rel).resolve()
    if not (p.is_relative_to(base) and p.is_file()):
        return f"<p class='shot missingfile'>Screenshot not found: {name}</p>"
    mime = MIME.get(p.suffix.lower())
    if not mime or p.stat().st_size > MAX_EMBED:
        return f"<p class='shot'><a href=\"{esc(quote(rel))}\">{name}</a></p>"
    data = base64.b64encode(p.read_bytes()).decode("ascii")
    return (f"<figure class='shot'><button type='button' class='thumb' aria-label='Enlarge {name}'>"
            f"<img src='data:{mime};base64,{data}' alt='Confirmation screenshot, {name}'></button>"
            f"<figcaption>{name}</figcaption></figure>")


# --- weeks -------------------------------------------------------------------

def claim_status(fm: dict, end: date, today: date) -> tuple[str, str]:
    """(what the week's header says, a prep note when the filing date is missing)."""
    filed = fm.get("claim_filed", "")
    if C.DATE_RE.match(filed):
        return filed, ""
    if end >= today:
        first = end + timedelta(days=1)
        return f"Not yet (file on or after {C.weekday_name(first)} {first.isoformat()})", ""
    return "Not recorded", ("The log has no filing date for this week. If the claim was filed, tell "
                            "Perkins the date (\"I filed my claim for the week ending ...\") and the clerk records it.")


def required_fields(state: C.State, kind: str) -> list[str]:
    for k in state.kinds:
        if k["name"].lower() == kind.strip().lower():
            return list(k["fields"])
    return []


def activity_html(cfg: C.Config, state: C.State, entry: dict, end: date, folders: list) -> str:
    m = HEADING_RE.match(entry["title"])
    number, title = (m.group(1), m.group(2) or "") if m else ("", entry["title"])
    fields = entry["fields"]
    evidence: list[str] = []
    rows, fit = [], ""
    for name, value in fields.items():
        if is_fit(name):
            fit = value
            continue
        if name.strip().lower() == "source":
            rows.append(f"<div class='row prep'><dt>{esc(name)}</dt><dd>{inline(value, evidence)}</dd></div>")
            continue
        full = inline(value, evidence)
        if is_blank(value):
            meet = NOT_RECORDED
        else:
            mv = meeting_value(value)
            meet = inline(mv) if mv else NOT_RECORDED
        cell = full if meet == full else f"<span class='meet'>{meet}</span><span class='prep prep-inline'>{full}</span>"
        rows.append(f"<div class='row'><dt>{esc(name)}</dt><dd>{cell}</dd></div>")
    present = {k.strip().lower() for k in fields}
    for name in required_fields(state, fields.get("Kind", "")):
        if name.lower() not in present:
            rows.append(f"<div class='row'><dt>{esc(name)}</dt><dd><span class='meet'>{NOT_RECORDED}</span>"
                        "<span class='prep prep-inline'>Not in the log file.</span></dd></div>")

    grade = re.split(r"[\s.,;:]", fit.strip().lower())[0] if fit.strip() else ""
    grade = grade if grade in K.FITS else ("check" if grade else "ungraded")
    id_attr = f" id='w{end.isoformat()}-a{esc(number)}'" if number else ""
    parts = [f"<article class='act'{id_attr}>"
             f"<h3><span class='num'>Activity {esc(number)}</span> <span class='ttl'>{inline(title)}</span> "
             f"<span class='prep badge {grade}'>{K.FIT_LABELS.get(grade, grade)}</span></h3>"]
    arts = artifacts(cfg, fields, folders)
    if arts:
        parts.append("<p class='arts'>" + "".join(
            f"<a class='btn' href=\"{esc(u)}\"" + (" target='_blank' rel='noopener'" if new else "")
            + f">{esc(label)}" + ("<span class='sr-only'> (opens in a new tab)</span>" if new else "") + "</a>"
            for label, u, new in arts) + "</p>")
    parts.append("<dl>" + "".join(rows) + "</dl>")
    if evidence:
        parts.append("<div class='shots'><p class='shots-h'>Confirmation</p>"
                     + "".join(evidence_html(cfg, e) for e in evidence) + "</div>")
    if fit:
        parts.append(f"<div class='prep prepbox'><p><strong>Fit:</strong> {inline(fit)}</p></div>")
    parts.append("</article>")
    return "".join(parts)


def week_html(cfg: C.Config, state: C.State, end: date, w: dict, today: date, folders: list) -> str:
    fm = w["fm"]
    try:
        start = date.fromisoformat(fm.get("week_start", ""))
    except ValueError:
        start = end - timedelta(days=6)
    try:
        required = int(fm.get("required", "") or state.required)
    except ValueError:
        required = state.required
    filled = [e for e in w["entries"] if e["fields"]]
    adjusted = K.adjusted_note(w, state)
    claim, note = claim_status(fm, end, today)
    short = "" if len(filled) >= required else " short"
    counts = (f"solid {w['solid']}" + (f" · potentially counts {w['maybe']}" if w["maybe"] else "")
              + f" · check {w['check']}" + (f" · no {w['no']}" if w["no"] else "") + f" · blank {w['missing']}")
    parts = [f"<details class='week' id='w{end.isoformat()}'><summary><span class='chev' aria-hidden='true'></span>"
             f"<span class='wk'>Week ending {end.isoformat()}</span>"
             f"<span class='wd'>{C.weekday_name(start)} {start.isoformat()} to {C.weekday_name(end)} {end.isoformat()}</span>"
             f"<span class='cnt{short}'>{len(filled)} of {required} activities</span>"
             + (f"<span class='adj'>{esc(adjusted[0].upper() + adjusted[1:])}</span>" if adjusted else "") +
             f"<span class='claim'>Claim filed: {esc(claim)}</span>"
             f"<span class='prep pcount'>{counts}</span></summary><div class='wbody'>"]
    prep = [f"Solid {w['solid']}, " + (f"potentially counts {w['maybe']}, " if w["maybe"] else "")
            + f"to check {w['check']}, blank fields {w['missing']}. "
            f"<a href=\"log/{esc(quote(w['path'].name))}\">{esc(w['path'].name)}</a>"]
    if note:
        prep.append(esc(note))
    parts.append("<div class='prep prepbox'>" + "".join(f"<p>{p}</p>" for p in prep) + "</div>")
    if filled:
        parts += [activity_html(cfg, state, e, end, folders) for e in filled]
    else:
        parts.append("<p class='muted'>No activities logged this week.</p>")
    parts.append("</div></details>")
    return "".join(parts)


# --- page --------------------------------------------------------------------

def build(cfg: C.Config, today: date) -> str:
    state = C.load_state(cfg.state)
    weeks = sorted(K.load_weeks(cfg).items(), reverse=True)  # newest week first
    folders = app_folders(cfg)
    entries = [e for _, w in weeks for e in w["entries"] if e["fields"]]
    applications = sum(1 for e in entries if is_application(e["fields"]))
    name = favicon.name_from_master(cfg.master)
    if cfg.claim_start:
        since = f"claim started {C.weekday_name(cfg.claim_start)} {cfg.claim_start.isoformat()}"
    elif weeks:
        first = weeks[-1][0] - timedelta(days=6)
        since = f"claim weeks from {C.weekday_name(first)} {first.isoformat()}"
    else:
        since = "no claim weeks yet"
    ended = f" · ended {cfg.claim_end.isoformat()}" if cfg.claim_end else ""
    who = f"{esc(name)} · " if name else ""

    p = ["<p class='back'><a href='dashboard.html'>&larr; Job search dashboard</a></p>",
         "<header class='top'><div><p class='eyebrow'>Perkins · Claim log</p>",
         "<h1>Work-search log</h1>",
         f"<p class='lead'>{who}{esc(state.name)} unemployment claim with the {esc(state.agency_full)} "
         f"({esc(state.agency)}) · {esc(since)}{esc(ended)}</p>",
         f"<p class='prep guidance'>{esc(C.guidance_line(state.agency))}</p>",
         f"<p class='asof'>Built {today.isoformat()} from the week files in log/. {esc(state.agency)} asks for at "
         f"least {state.required} approved activities in each claim week.</p></div>",
         "<button type='button' id='prep' aria-pressed='false'>Show prep notes</button></header>",
         "<section class='cards'>"
         f"<div class='card'><div class='n'>{len(weeks)}</div><div class='l'>Claim weeks</div></div>"
         f"<div class='card'><div class='n'>{len(entries)}</div><div class='l'>Activities logged</div></div>"
         f"<div class='card'><div class='n'>{applications}</div><div class='l'>Applications</div></div></section>",
         "<div class='wkhead'><h2>Week by week</h2>"
         "<button type='button' id='expand' class='tool' aria-pressed='false'>Expand all</button></div>"]
    if weeks:
        p += [week_html(cfg, state, end, w, today, folders) for end, w in weeks]
    else:
        p.append("<p class='muted'>No claim weeks yet. The clerk opens the first one when the claim starts.</p>")
    # The version and build date, bottom right (house standard 24, RM_version_footer).
    p.append("<footer data-standard='RM_version_footer'><p>The week files in log/ are the record; "
             f"this page only reads them.</p><p class='ver'>Built {today.isoformat()} by Perkins {__version__}</p></footer>")

    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Work-search log</title>{favicon.link(cfg.master)}<style>{CSS}</style></head>"
            "<body><main>" + "".join(p) + "</main>" + LIGHTBOX + SCRIPT + "</body></html>")


def write(cfg: C.Config, today: date) -> str:
    cfg.claim_log.write_text(build(cfg, today), encoding="utf-8", newline="\n")
    return str(cfg.claim_log)


LIGHTBOX = ("<div id='lb' role='dialog' aria-modal='true' aria-label='Screenshot' hidden>"
            "<button type='button' id='lb-close'>Close</button><img alt=''></div>")

SCRIPT = """<script>
(function(){
  var b=document.getElementById('prep');
  b.addEventListener('click',function(){var on=document.body.classList.toggle('show-prep');
    b.setAttribute('aria-pressed',on?'true':'false');b.textContent=on?'Hide prep notes':'Show prep notes';});
  var lb=document.getElementById('lb'),li=lb.querySelector('img'),lc=document.getElementById('lb-close'),opener=null;
  function closeLb(){if(lb.hidden)return;lb.hidden=true;li.removeAttribute('src');if(opener)opener.focus();}
  document.querySelectorAll('.thumb').forEach(function(t){t.addEventListener('click',function(){
    var i=t.querySelector('img');li.src=i.src;li.alt=i.alt;opener=t;lb.hidden=false;lc.focus();});});
  lb.addEventListener('click',function(e){if(e.target!==li)closeLb();});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')closeLb();});
  var weeks=[].slice.call(document.querySelectorAll('details.week')),x=document.getElementById('expand');
  function sync(){var all=weeks.length&&weeks.every(function(d){return d.open;});
    x.textContent=all?'Collapse all':'Expand all';x.setAttribute('aria-pressed',all?'true':'false');}
  x.addEventListener('click',function(){var open=!weeks.every(function(d){return d.open;});
    weeks.forEach(function(d){d.open=open;});sync();});
  weeks.forEach(function(d){d.addEventListener('toggle',sync);});
  function openHash(){var id=location.hash.slice(1),el=id&&document.getElementById(id);if(!el)return;
    var d=el.tagName==='DETAILS'?el:el.closest('details.week');if(d){d.open=true;el.scrollIntoView();}}
  window.addEventListener('hashchange',openHash);openHash();
  var was=[];
  window.addEventListener('beforeprint',function(){was=weeks.map(function(d){return d.open;});
    weeks.forEach(function(d){d.open=true;});});
  window.addEventListener('afterprint',function(){weeks.forEach(function(d,i){d.open=was[i];});sync();});
})();
</script>"""

CSS = """
:root{--bg:#f3f5f2;--panel:#fff;--ink:#16202e;--muted:#566272;--line:#d6dcd5;--accent:#1d6a56;--accent-soft:#e0eee8;
--warn-ink:#b02a20;--warn-bg:#fbe1dc;--good-bg:#dff1e5;--good-ink:#1f7a49;--chk-bg:#fbeed0;--chk-ink:#8f5c00;--prep-bg:#fff7e0;--prep-line:#e2c36a}
@media (prefers-color-scheme:dark){:root{--bg:#0f151d;--panel:#17202b;--ink:#e6ebf0;--muted:#9ba7b5;--line:#2a3542;
--accent:#63c7a7;--accent-soft:#15302a;--warn-ink:#ff8b7c;--warn-bg:#3d1d19;--good-bg:#163022;--good-ink:#7cd49b;--chk-bg:#3a2e12;--chk-ink:#f2c766;
--prep-bg:#2b2716;--prep-line:#7a6528;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Public Sans","Segoe UI",system-ui,Arial,sans-serif}
main{max-width:1000px;margin:0 auto;padding:20px max(16px,env(safe-area-inset-left)) 48px max(16px,env(safe-area-inset-right))}
a{color:var(--accent)}a:focus-visible,button:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.back{margin:0 0 12px;font-size:14px}.back a{text-decoration:none;font-weight:600}.back a:hover{text-decoration:underline}
.top{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:14px}
.eyebrow{margin:0;font:500 12px/1.4 ui-monospace,Consolas,monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
h1{margin:4px 0 6px;font-size:30px;letter-spacing:-.01em}h2{font-size:18px;margin:0}
h3{font-size:16px;margin:0 0 10px;display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline}
.lead{color:var(--muted);margin:4px 0;overflow-wrap:anywhere}.asof{color:var(--muted);font-size:13px;margin:6px 0 0}
#prep,.tool{font:inherit;font-size:14px;padding:8px 14px;border:1px solid var(--line);border-radius:8px;background:var(--panel);color:var(--ink);cursor:pointer}
#prep[aria-pressed=true]{background:var(--prep-bg);border-color:var(--prep-line)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.card .n{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}.card .l{color:var(--muted);font-size:13px}
.wkhead{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:28px 0 8px}
details.week{background:var(--panel);border:1px solid var(--line);border-radius:10px;margin:10px 0}
details.week>summary{list-style:none;cursor:pointer;display:flex;flex-wrap:wrap;align-items:center;gap:4px 18px;padding:14px 16px;border-radius:10px}
details.week>summary::-webkit-details-marker{display:none}details.week>summary:hover{background:var(--accent-soft)}
details.week>summary:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.chev{width:9px;height:9px;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);transform:rotate(-45deg);transition:transform .15s;flex:none;margin:0 2px}
details[open]>summary .chev{transform:rotate(45deg)}
.wk{font-weight:700;font-size:16px;font-variant-numeric:tabular-nums}.wd,.claim{color:var(--muted);font-variant-numeric:tabular-nums}
.cnt{font-weight:600}.cnt.short{color:var(--warn-ink)}.adj{color:var(--muted);font-size:13px;overflow-wrap:anywhere}
.pcount{font-size:13px;background:var(--prep-bg);border-radius:4px;padding:0 6px}
.wbody{padding:4px 16px 8px;border-top:1px solid var(--line)}
.act{background:var(--bg);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.num{color:var(--muted);font:600 12px/1.4 ui-monospace,Consolas,monospace;text-transform:uppercase;letter-spacing:.06em}
.ttl{overflow-wrap:anywhere}
.arts{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 12px}
.btn{display:inline-block;padding:5px 12px;border-radius:999px;background:var(--accent-soft);text-decoration:none;font-size:14px;font-weight:600}
.btn:hover{text-decoration:underline}
dl{display:grid;grid-template-columns:minmax(140px,220px) 1fr;gap:6px 16px;margin:0}.row{display:contents}
dt{color:var(--muted);font-size:14px}dd{margin:0;overflow-wrap:anywhere}
.missing{color:var(--warn-ink);font-style:italic}.muted{color:var(--muted)}
.shots{margin-top:12px}.shots-h{margin:0 0 6px;color:var(--muted);font-size:14px}
.shot{margin:0 12px 8px 0;display:inline-block;vertical-align:top}
.thumb{padding:0;border:1px solid var(--line);border-radius:8px;background:none;cursor:zoom-in;display:block}
.thumb img{display:block;max-width:300px;max-height:180px;border-radius:7px}
.shot figcaption{font-size:12px;color:var(--muted);margin-top:4px;max-width:300px;overflow-wrap:anywhere}
.badge{font:600 11px/1.6 ui-monospace,Consolas,monospace;padding:1px 8px;border-radius:999px;text-transform:uppercase;letter-spacing:.05em}
.badge.solid{background:var(--good-bg);color:var(--good-ink)}.badge.maybe{background:var(--chk-bg);color:var(--chk-ink)}
.badge.check,.badge.ungraded{background:var(--warn-bg);color:var(--warn-ink)}
.guidance{color:var(--muted);font-size:13px;margin:6px 0 0;background:var(--prep-bg);border-radius:4px;padding:2px 6px;display:inline-block}
.badge.no{background:var(--line);color:var(--ink)}
.prepbox{background:var(--prep-bg);border-left:3px solid var(--prep-line);padding:8px 12px;margin:10px 0;border-radius:6px;font-size:14px}
.prepbox p{margin:4px 0}.prep-inline{background:var(--prep-bg);border-radius:4px;padding:0 4px}
body:not(.show-prep) .prep{display:none}body.show-prep .meet{display:none}
#lb{position:fixed;inset:0;background:rgba(0,0,0,.85);display:flex;align-items:center;justify-content:center;padding:48px 16px 16px;cursor:zoom-out;z-index:10}
#lb[hidden]{display:none}#lb img{max-width:100%;max-height:100%;border-radius:8px;background:#fff}
#lb-close{position:absolute;top:10px;right:16px;font:inherit;font-size:14px;padding:6px 12px;border-radius:8px;border:0;background:#fff;color:#16202e;cursor:pointer}
footer{margin-top:36px;color:var(--muted);font-size:13px;display:flex;flex-wrap:wrap;gap:4px 24px}footer p{margin:0}footer .ver{margin-left:auto}code{font-size:13px}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media (max-width:640px){dl{grid-template-columns:1fr;gap:2px}dt{margin-top:8px}.thumb img{max-width:100%}.shot{display:block}}
@media print{:root{--bg:#fff;--panel:#fff;--ink:#000;--muted:#444;--line:#bbb;--accent:#1d6a56;--accent-soft:#eee;--warn-ink:#a00;--warn-bg:#fbe1dc;
--good-bg:#dff1e5;--good-ink:#1f7a49;--chk-bg:#fbeed0;--chk-ink:#8f5c00;--prep-bg:#f6f0dc;--prep-line:#c9a640;color-scheme:light}
#prep,#expand,#lb,.back{display:none!important}body{background:#fff}.act{break-inside:avoid}
details.week{break-inside:auto}.thumb img{max-height:160px}a{text-decoration:none}}
"""


def add_arguments(p) -> None:
    p.add_argument("--open", action="store_true", help="open the page in your browser after building it")


def cli(args, cfg: C.Config, today: date) -> int:
    if not cfg.claim_records:
        print("Claims tracking is off (mode is Search), so there's no claim log page.")
        return 0
    path = write(cfg, today)
    print(f"wrote {path}")
    if getattr(args, "open", False):
        import webbrowser
        webbrowser.open(cfg.claim_log.as_uri())
    return 0
