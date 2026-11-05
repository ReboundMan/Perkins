"""Workable job boards: apply.workable.com/api/v1/widget/accounts/<slug>."""
from __future__ import annotations

from urllib.parse import quote

from . import http

API = "https://apply.workable.com/api/v1/widget/accounts/{slug}"
BOARD_URL = "https://apply.workable.com/{slug}"


def _place(d: dict) -> str:
    parts = [d.get("city"), d.get("region") or d.get("state"), d.get("country")]
    return ", ".join(str(p) for p in parts if p)


def list_jobs(slug: str) -> list[dict]:
    data = http.get_json(API.format(slug=quote(slug, safe="")))
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    out = []
    for j in jobs:
        if not isinstance(j, dict) or not j.get("title"):
            continue
        places = [_place(x) for x in j.get("locations") or [] if isinstance(x, dict) and not x.get("hidden")]
        places = [p for p in places if p] or [_place(j)]
        if j.get("telecommuting"):
            places.append("Remote")
        code = j.get("shortcode") or j.get("code") or ""
        out.append({
            "id": str(code or j.get("url", "")),
            "title": str(j["title"]).strip(),
            "location": "; ".join(p for p in places if p),
            "url": str(j.get("url") or j.get("shortlink") or (f"https://apply.workable.com/j/{code}" if code else "")),
            "posted": str(j.get("published_on") or j.get("created_at") or "")[:10],
        })
    return out
