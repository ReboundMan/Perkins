"""Lever job boards: api.lever.co/v0/postings/<slug>?mode=json."""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote

from . import http

API = "https://api.lever.co/v0/postings/{slug}?mode=json"
BOARD_URL = "https://jobs.lever.co/{slug}"


def _date(ms) -> str:
    """Lever's createdAt is milliseconds since 1970."""
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def list_jobs(slug: str) -> list[dict]:
    data = http.get_json(API.format(slug=quote(slug, safe="")))
    jobs = data if isinstance(data, list) else []
    out = []
    for j in jobs:
        if not isinstance(j, dict) or not j.get("text"):
            continue
        cats = j.get("categories") if isinstance(j.get("categories"), dict) else {}
        places = cats.get("allLocations") or [cats.get("location") or ""]
        out.append({
            "id": str(j.get("id", "")),
            "title": str(j["text"]).strip(),
            "location": "; ".join(str(p) for p in places if p),
            "url": str(j.get("hostedUrl") or j.get("applyUrl") or ""),
            "posted": _date(j.get("createdAt")),
        })
    return out
