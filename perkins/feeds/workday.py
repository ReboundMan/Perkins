"""Workday career sites: POST <tenant>.wd<N>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs.

A site is named "<tenant>.wd<N>/<site>" (for example "kestrel.wd5/External"), or
given as its careers URL. Pages hold 20 postings; at most MAX_JOBS are read.
Workday gives the posting date as text ("Posted 3 Days Ago"), turned into a date
here when it can be.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from . import http

SITE_RE = re.compile(r"^([\w-]+)\.(wd\d+)/([^/?#\s]+)$")
URL_RE = re.compile(r"([\w-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([^/?#\s]+)", re.I)
PAGE = 20
MAX_JOBS = 200
AGO_RE = re.compile(r"(\d+)\+?\s+days?\s+ago", re.I)


def parse_site(site: str) -> tuple[str, str, str]:
    """(tenant, wdN, site) from "tenant.wdN/site" or a myworkdayjobs.com URL."""
    s = (site or "").strip()
    m = SITE_RE.match(s) or URL_RE.search(s)
    if not m:
        raise ValueError(f"Not a Workday site: {site!r} (expected tenant.wd5/Site or a myworkdayjobs.com URL)")
    return m.group(1), m.group(2).lower(), m.group(3)


def posted_date(text: str, today: date | None = None) -> str:
    """'Posted Today', 'Posted Yesterday', 'Posted 3 Days Ago' as an ISO date; '' for '30+ Days Ago' or unknown."""
    t = (text or "").lower()
    today = today or date.today()
    if "today" in t:
        return today.isoformat()
    if "yesterday" in t:
        return (today - timedelta(days=1)).isoformat()
    m = AGO_RE.search(t)
    if m and "+" not in t:
        return (today - timedelta(days=int(m.group(1)))).isoformat()
    return ""


def list_jobs(site: str) -> list[dict]:
    tenant, wd, name = parse_site(site)
    host = f"https://{tenant}.{wd}.myworkdayjobs.com"
    api = f"{host}/wday/cxs/{tenant}/{name}/jobs"
    out, offset, total = [], 0, None
    while offset < MAX_JOBS:
        body = {"appliedFacets": {}, "limit": PAGE, "offset": offset, "searchText": ""}
        data = http.post_json(api, body)
        posts = data.get("jobPostings", []) if isinstance(data, dict) else []
        if total is None and isinstance(data, dict):
            total = int(data.get("total") or 0)  # later pages may report 0, so keep the first
        for j in posts:
            if not isinstance(j, dict) or not j.get("title"):
                continue
            path = str(j.get("externalPath") or "")
            bullets = j.get("bulletFields") or []
            out.append({
                "id": path or (str(bullets[0]) if bullets else ""),
                "title": str(j["title"]).strip(),
                "location": str(j.get("locationsText") or ""),
                "url": f"{host}/{name}{path}" if path else "",
                "posted": posted_date(str(j.get("postedOn") or "")),
            })
        offset += PAGE
        if len(posts) < PAGE or (total and offset >= total):
            break
    return out[:MAX_JOBS]
