"""Greenhouse job boards: boards-api.greenhouse.io/v1/boards/<slug>/jobs."""
from __future__ import annotations

from urllib.parse import quote

from . import http

API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
BOARD_URL = "https://job-boards.greenhouse.io/{slug}"


def list_jobs(slug: str) -> list[dict]:
    data = http.get_json(API.format(slug=quote(slug, safe="")))
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    out = []
    for j in jobs:
        if not isinstance(j, dict) or not j.get("title"):
            continue
        loc = j.get("location")
        out.append({
            "id": str(j.get("id", "")),
            "title": str(j["title"]).strip(),
            "location": str(loc.get("name", "") if isinstance(loc, dict) else loc or "").strip(),
            "url": str(j.get("absolute_url", "") or ""),
            "posted": str(j.get("first_published") or j.get("updated_at") or "")[:10],
        })
    return out
