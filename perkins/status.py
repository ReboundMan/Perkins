"""Where the whole search stands, for /perkins:job-status and "where does my search stand?".

CLI: status [--json]
"""
from __future__ import annotations

import json
from datetime import date, timedelta

from . import config as C
from . import due as D
from . import tracker as T


def report(cfg: C.Config, today: date) -> dict:
    out = {"today": today.isoformat(), "mode": cfg.mode, "mode_name": cfg.mode_name, "home": str(cfg.home)}
    tr = T.Tracker.load(cfg.tracker)

    def rows(name):
        t = tr.maybe_table(name)
        return (t, [t.normalized(r) for r in t.rows]) if t else (None, [])

    t_sub, sub = rows(T.SUBMITTED)
    t_con, con = rows(T.CONSIDERING)
    out["counts"] = {
        "submitted": len(sub),
        "conversations": len(rows(T.CONVERSATIONS)[1]),
        "considering": len(con),
        "passed": len(rows(T.PASSED)[1]),
        "watching": len(rows(T.WATCH)[1]),
    }
    out["resumes_ready"] = [T.plain(t_con.get(r, "Company")) + ", " + T.plain(t_con.get(r, "Role"))
                            for r in con if T.plain(t_con.get(r, "Resume")).lower().startswith("ready")]
    out["leads"] = [T.plain(t_con.get(r, "Company")) + ", " + T.plain(t_con.get(r, "Role"))
                    for r in con if T.plain(t_con.get(r, "Status")).lower() == "lead"]
    out["held"] = [T.plain(t_con.get(r, "Company")) + ", " + T.plain(t_con.get(r, "Role")) + " (" + T.plain(t_con.get(r, "Next step")) + ")"
                   for r in con if "held" in T.plain(t_con.get(r, "Status")).lower()]
    out["due"] = D.collect(cfg, today, 7)

    target = cfg.weekly_target
    if cfg.claims:
        from . import clerk
        state = C.load_state(cfg.state)
        rep = clerk.run(cfg, today, status_only=True)
        out["claims"] = {"state": state.name, "agency": state.agency, "required": state.required,
                         "this_week": rep["this_week"], "last_week": rep["last_week"],
                         "guidance": C.guidance_line(state.agency)}
        target = max(target, state.required)
    start, end = D.week_window(cfg, today)
    out["week"] = {"start": start.isoformat(), "end": end.isoformat(),
                   "applied": D.applied_this_week(cfg, tr, today), "target": target}

    if not cfg.claims and cfg.log_dir.exists() and any(cfg.log_dir.glob("week-ending-*.md")):
        retention = ""
        if cfg.state:
            try:
                retention = C.load_state(cfg.state).retention
            except C.ConfigError:
                pass
        out["log_kept"] = {"path": str(cfg.log_dir), "retention": retention or "Keep it as long as your state asks."}
    return out


def text(r: dict) -> str:
    c = r["counts"]
    lines = [f"Perkins · {r['mode_name']} · {r['today']}",
             f"Submitted {c['submitted']} · Conversations {c['conversations']} · Considering {c['considering']} · "
             f"Watching {c['watching']} · Passed {c['passed']}"]
    w = r["week"]
    lines.append(f"This week ({w['start']} to {w['end']}): {w['applied']} applied"
                 + (f" of a target of {w['target']}" if w["target"] else ""))
    if "claims" in r:
        cl = r["claims"]
        tw, lw = cl["this_week"], cl["last_week"]
        from .clerk import counts_phrase
        if tw:
            req = tw.get("required", cl["required"])
            line = f"Claim week: {counts_phrase(tw, req)}"
            if tw.get("required_reason") and req:
                line += f" ({cl['agency']} minimum {req}, adjusted: {tw['required_reason']})"
            lines.append(line)
        else:
            lines.append("Claim week: no log yet")
        if lw:
            filed = lw.get("claim_filed") or "no"
            lines.append(f"Last week's claim: {'filed ' + filed if C.DATE_RE.match(filed) else 'not filed yet'}"
                         f" (closed at {counts_phrase(lw, lw.get('required', cl['required']))})")
        lines.append(cl["guidance"])
    if r["resumes_ready"]:
        lines.append("Resumes ready to submit: " + "; ".join(r["resumes_ready"]))
    if r["held"]:
        lines.append("Held for a later week: " + "; ".join(r["held"]))
    if r["leads"]:
        lines.append(f"Leads to read: {len(r['leads'])}")
    if r["due"]:
        lines.append("Needs you:")
        today = date.fromisoformat(r["today"])
        for i in r["due"]:
            lines.append(f"  {i['date'] or '(no date)'} {D.label(i, today).upper()}: {i['what']}"
                         + (f" ({i['detail']})" if i["detail"] else ""))
    else:
        lines.append("Nothing due in the next 7 days.")
    if "log_kept" in r:
        lines.append(f"Your work-search log is kept in {r['log_kept']['path']}. {r['log_kept']['retention']}")
    return "\n".join(lines)


def add_arguments(p) -> None:
    p.add_argument("--json", action="store_true")


def cli(args, cfg: C.Config, today: date) -> int:
    r = report(cfg, today)
    print(json.dumps(r, indent=2, ensure_ascii=False) if args.json else text(r))
    return 0
