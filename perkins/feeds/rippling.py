"""Rippling job boards: ats.rippling.com/api/v2/board/<slug>/jobs.

The reply is paged (items, page, pageSize, totalPages). Later pages are asked
for with ?page=N, which was not confirmed live; if a page brings nothing new the
adapter stops. At most MAX_PAGES pages are read.
"""
from __future__ import annotations

from urllib.parse import quote

from . import http

API = "https://ats.rippling.com/api/v2/board/{slug}/jobs"
BOARD_URL = "https://ats.rippling.com/{slug}/jobs"
JOB_URL = "https://ats.rippling.com/{slug}/jobs/{id}"
MAX_PAGES = 10


def _place(loc) -> str:
    if isinstance(loc, str):
        return loc
    if not isinstance(loc, dict):
        return ""
    if loc.get("name"):
        return str(loc["name"])
    parts = [loc.get("city"), loc.get("state") or loc.get("stateCode"), loc.get("country") or loc.get("countryCode")]
    return ", ".join(str(p) for p in parts if p)


def _items(data) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items") or data.get("jobs") or data.get("results") or []
    return []


def list_jobs(slug: str) -> list[dict]:
    base = API.format(slug=quote(slug, safe=""))
    data = http.get_json(base)
    pages = data.get("totalPages", 1) if isinstance(data, dict) else 1
    raw = list(_items(data))
    seen = {str(j.get("id")) for j in raw if isinstance(j, dict)}
    page = 1
    while isinstance(pages, int) and page < min(pages, MAX_PAGES):
        more = [j for j in _items(http.get_json(f"{base}?page={page}")) if isinstance(j, dict)]
        fresh = [j for j in more if str(j.get("id")) not in seen]
        if not fresh:
            break
        raw.extend(fresh)
        seen.update(str(j.get("id")) for j in fresh)
        page += 1
    out = []
    for j in raw:
        if not isinstance(j, dict):
            continue
        title = j.get("name") or j.get("title") or ""
        if not title:
            continue
        jid = str(j.get("id", ""))
        places = [_place(x) for x in j.get("locations") or []]
        out.append({
            "id": jid,
            "title": str(title).strip(),
            "location": "; ".join(p for p in places if p),
            "url": str(j.get("url") or (JOB_URL.format(slug=slug, id=jid) if jid else "")),
            "posted": str(j.get("createdAt") or j.get("publishedAt") or "")[:10],
        })
    return out
