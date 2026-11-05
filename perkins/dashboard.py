"""Render tracker.md (and, with claims tracking, the claim week) into dashboard.html.

The Markdown is the source of truth; this page is rebuilt from it after every change.
The page has, top to bottom: the claim panel (claims tracking only), count cards, the
due-soon list, and every tracker table with overdue dates in red and upcoming ones in amber.
CLI: dashboard [--open]
"""
from __future__ import annotations

import html
import re
from datetime import date, timedelta

from . import __version__
from . import config as C
from . import due as D
from . import tracker as T

SOON_DAYS = 7


def inline(text: str) -> str:
    """Escape, then render [links](url), **bold**, *italic*, and `code`."""
    out = html.escape(text.replace("\\|", "|"), quote=False)
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                 lambda m: f'<a href="{html.escape(m.group(2))}" target="_blank" rel="noopener">{m.group(1)}</a>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    return out


def _sections(tr: T.Tracker) -> tuple[list[str], list[tuple[str, list[str], T.Table]]]:
    """(intro paragraphs, [(section, note paragraphs, table)])."""
    intro, sections, current, para = [], [], None, []

    def flush():
        if para:
            (current[1] if current else intro).append(" ".join(para))
            para.clear()

    for b in tr.blocks:
        if b[0] == "table":
            flush()
            if current is not None and current[2] is None:
                current[2] = b[2]
            continue
        line = b[1].rstrip()
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            flush()
            current = [line[3:].strip(), [], None]
            sections.append(current)
        elif line.strip():
            para.append(line.strip())
        else:
            flush()
    flush()
    return intro, [(s[0], s[1], s[2]) for s in sections]


def claim_panel(cfg: C.Config, today: date) -> str:
    if not cfg.claims:
        return ""
    from . import clerk
    state = C.load_state(cfg.state)
    start, end = clerk.week_bounds(today, state)
    prev_end = start - timedelta(days=1)
    weeks = clerk.load_weeks(cfg)
    w, lw = weeks.get(end), weeks.get(prev_end)
    raise_off = (state.raise_day - state.week_start) % 7
    days_in = (today - start).days

    if w is None:
        tw_cls, tw_big, tw_sub = "neutral", "No log yet", "The clerk opens this week's log on its next run."
    else:
        tw_big = f"{w['solid']} of {state.required} solid"
        bits = [f"{w['check']} to check"]
        if w["missing"]:
            bits.append(f"{w['missing']} blank{'s' if w['missing'] != 1 else ''}")
        bits.append(f"{C.weekday_name(start)} {start.isoformat()} to {C.weekday_name(end)} {end.isoformat()}")
        tw_sub = " · ".join(bits)
        tw_cls = "good" if w["solid"] >= state.required else ("warn" if days_in >= raise_off else "neutral")

    if lw is None:
        lw_cls, lw_big, lw_sub = "neutral", "No claim week yet", f"Week ending {prev_end.isoformat()}"
    else:
        filed = lw["fm"].get("claim_filed", "")
        closed = f"Closed at {clerk.counts_phrase(lw, state.required)}"
        if C.DATE_RE.match(filed):
            lw_cls, lw_big, lw_sub = "good", f"Filed {filed}", closed
        else:
            lw_cls, lw_big, lw_sub = "warn", "Not filed yet", f"Week ending {prev_end.isoformat()} · {closed}"

    def card(cls, label, big, sub):
        return (f"<div class='claim {cls}'><span class='k'>{html.escape(label)}</span>"
                f"<span class='big'>{html.escape(big)}</span><span class='s'>{html.escape(sub)}</span></div>")

    return ("<section class='claim-panel' aria-label='Claim week'>"
            + card(tw_cls, f"This week · {state.agency} minimum {state.required}", tw_big, tw_sub)
            + card(lw_cls, "Last week's claim", lw_big, lw_sub)
            + "</section>")


def build(cfg: C.Config, today: date) -> str:
    tr = T.Tracker.load(cfg.tracker)
    intro, sections = _sections(tr)
    by_name = {s[0].lower(): s for s in sections}
    due_items = D.collect(cfg, today, SOON_DAYS)

    def count(name, pred=lambda t, r: True):
        s = by_name.get(name.lower())
        if not s or not s[2]:
            return 0
        return sum(1 for r in s[2].rows if pred(s[2], s[2].normalized(r)))

    ready = count(T.CONSIDERING, lambda t, r: T.plain(t.get(r, "Resume")).lower().startswith("ready"))
    cards = [
        ("Submitted", count(T.SUBMITTED)),
        ("Conversations", count(T.CONVERSATIONS)),
        ("Considering", count(T.CONSIDERING)),
        ("Resumes ready", ready),
        ("Employers watched", count(T.WATCH)),
        ("Due in 7 days", len(due_items)),
    ]
    if not cfg.claims and cfg.weekly_target > 0:
        start = today - timedelta(days=today.weekday())
        applied = count(T.SUBMITTED, lambda t, r: (d := D.first_date(t.get(r, "Submitted"))) is not None and start <= d <= today)
        cards.append((f"Applied this week (target {cfg.weekly_target})", applied))

    parts = ["<header class='top'><div>",
             "<p class='eyebrow'>Perkins · " + html.escape(cfg.mode_name) + "</p>",
             "<h1>Job search dashboard</h1>"]
    parts += [f"<p class='lead'>{inline(p)}</p>" for p in intro]
    parts.append(f"</div><p class='asof'>Built {today.isoformat()}</p></header>")
    parts.append(claim_panel(cfg, today))
    parts.append("<section class='cards'>" + "".join(
        f"<div class='card'><div class='n'>{n}</div><div class='l'>{html.escape(label)}</div></div>"
        for label, n in cards) + "</section>")

    parts.append("<section><h2>Due soon</h2>")
    if due_items:
        parts.append("<ul class='due'>")
        for i in due_items:
            d = date.fromisoformat(i["date"])
            cls = "over" if i["overdue"] else "soon"
            when = "Overdue" if i["overdue"] else ("Today" if d == today else f"In {(d - today).days} days")
            parts.append(f"<li class='{cls}'><span class='date'>{d.isoformat()}</span>"
                         f"<span class='pill {cls}'>{html.escape(when)}</span>"
                         f"<span class='what'><strong>{html.escape(i['what'])}</strong> "
                         f"<span class='src'>{html.escape(i['section'])}</span>"
                         + (f"<span class='detail'>{html.escape(i['detail'])}</span>" if i["detail"] else "")
                         + "</span></li>")
        parts.append("</ul>")
    else:
        parts.append(f"<p class='muted'>Nothing due in the next {SOON_DAYS} days.</p>")
    parts.append("</section>")

    for heading, paras, table in sections:
        rows = table.rows if table else []
        parts.append(f"<section><h2>{html.escape(heading)} <span class='count'>{len(rows)}</span></h2>")
        parts += [f"<p class='note'>{inline(p)}</p>" for p in paras]
        if table:
            cols = [h.strip().lower() for h in table.header]
            parts.append("<div class='scroll'><table><thead><tr>"
                         + "".join(f"<th scope='col'>{inline(h)}</th>" for h in table.header)
                         + "</tr></thead><tbody>")
            for row in rows:
                tds = []
                for ci, cell in enumerate(table.normalized(row)):
                    cls = ""
                    if cols[ci] in D.DATE_COLS:
                        d = D.first_date(cell)
                        if d and d < today:
                            cls = " class='over'"
                        elif d and d <= today + timedelta(days=SOON_DAYS):
                            cls = " class='soon'"
                    if not cls and re.fullmatch(r"\d{4}-\d{2}-\d{2}", cell.strip()):
                        cls = " class='d'"
                    tds.append(f"<td{cls}>{inline(cell)}</td>")
                parts.append("<tr>" + "".join(tds) + "</tr>")
            parts.append("</tbody></table></div>")
            if not rows:
                parts.append("<p class='muted'>Nothing here yet.</p>")
        parts.append("</section>")
    parts.append(f"<footer>Built {today.isoformat()} by Perkins {__version__}. The tracker file is the source; "
                 "this page is rebuilt after every change.</footer>")

    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Job search dashboard</title><style>" + CSS + "</style></head><body><main>"
            + "".join(parts) + "</main></body></html>")


def write(cfg: C.Config, today: date) -> str:
    cfg.dashboard.write_text(build(cfg, today), encoding="utf-8", newline="\n")
    return str(cfg.dashboard)


CSS = """
:root{--bg:#f3f5f2;--panel:#fff;--ink:#16202e;--muted:#566272;--line:#d6dcd5;--accent:#1d6a56;--accent-soft:#e0eee8;
--soon-bg:#fbeed0;--soon-ink:#8f5c00;--over-bg:#fbe2de;--over-ink:#b02a20;--good-bg:#dff1e5;--good-ink:#1f7a49;--head:#eaeee9}
@media (prefers-color-scheme:dark){:root{--bg:#0f151d;--panel:#17202b;--ink:#e6ebf0;--muted:#9ba7b5;--line:#2a3542;
--accent:#63c7a7;--accent-soft:#15302a;--soon-bg:#3a2e12;--soon-ink:#f2c766;--over-bg:#3d1c19;--over-ink:#ff8b7c;
--good-bg:#163022;--good-ink:#7cd49b;--head:#1d2834;color-scheme:dark}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Public Sans","Segoe UI",system-ui,Arial,sans-serif}
main{max-width:1280px;margin:0 auto;padding:24px max(16px,env(safe-area-inset-left)) 48px max(16px,env(safe-area-inset-right))}
a{color:var(--accent)}a:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.top{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:14px}
.eyebrow{margin:0;font:500 12px/1.4 ui-monospace,Consolas,monospace;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
h1{margin:4px 0 6px;font-size:30px;letter-spacing:-.01em}h2{font-size:18px;margin:28px 0 10px}
.count{font-size:13px;color:var(--muted);font-weight:400;margin-left:6px}
.lead,.note{color:var(--muted);margin:4px 0;max-width:900px}.asof{color:var(--muted);font-size:13px;margin:0}
.claim-panel{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:20px}
.claim{border-radius:10px;padding:14px 16px;display:grid;gap:2px;border:1px solid var(--line);background:var(--panel)}
.claim.warn{background:var(--soon-bg);border-color:transparent}.claim.good{background:var(--good-bg);border-color:transparent}
.claim .k{font:500 11px/1.4 ui-monospace,Consolas,monospace;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.claim.warn .k,.claim.warn .big{color:var(--soon-ink)}.claim.good .k,.claim.good .big{color:var(--good-ink)}
.claim .big{font-size:26px;font-weight:700;line-height:1.15}.claim .s{font-size:13px;color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:14px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px 14px}
.card .n{font-size:26px;font-weight:700;font-variant-numeric:tabular-nums}.card .l{color:var(--muted);font-size:13px}
ul.due{list-style:none;padding:0;margin:0;display:grid;gap:8px}
ul.due li{display:grid;grid-template-columns:7rem auto minmax(0,1fr);gap:10px;align-items:center;background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--soon-ink);border-radius:6px;padding:8px 12px}
ul.due li.over{border-left-color:var(--over-ink)}
.date{font-variant-numeric:tabular-nums;font-weight:600}
.pill{font:500 11px/1.6 ui-monospace,Consolas,monospace;text-transform:uppercase;letter-spacing:.05em;padding:1px 8px;border-radius:999px;white-space:nowrap}
.pill.soon{background:var(--soon-bg);color:var(--soon-ink)}.pill.over{background:var(--over-bg);color:var(--over-ink)}
.what{min-width:0}.src{color:var(--muted);font-size:13px;margin-left:6px}.detail{display:block;color:var(--muted);font-size:13px}
.scroll{overflow-x:auto;background:var(--panel);border:1px solid var(--line);border-radius:8px}
table{border-collapse:collapse;width:100%;min-width:820px}th,td{text-align:left;vertical-align:top;padding:8px 10px;border-bottom:1px solid var(--line)}
th{background:var(--head);font-size:13px}tr:last-child td{border-bottom:0}
td.d,td.soon,td.over{white-space:nowrap}td.soon{background:var(--soon-bg);color:var(--soon-ink);font-weight:600}
td.over{background:var(--over-bg);color:var(--over-ink);font-weight:600}
code{font-size:13px}.muted{color:var(--muted)}footer{margin-top:36px;color:var(--muted);font-size:13px}
@media (max-width:640px){.claim-panel{grid-template-columns:1fr}ul.due li{grid-template-columns:auto 1fr}ul.due li .what{grid-column:1/-1}}
@media print{body{background:#fff}.scroll{overflow:visible;border:0}table{min-width:0}}
"""


def add_arguments(p) -> None:
    p.add_argument("--open", action="store_true", help="open the page in your browser after building it")


def cli(args, cfg: C.Config, today: date) -> int:
    path = write(cfg, today)
    print(f"wrote {path}")
    if getattr(args, "open", False):
        import webbrowser
        webbrowser.open(cfg.dashboard.as_uri())
    return 0
