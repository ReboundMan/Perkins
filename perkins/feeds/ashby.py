"""Ashby job boards: api.ashbyhq.com/posting-api/job-board/<slug>.

The reply carries every posting's full description, so a large board can run to
several megabytes. Only the list fields are kept.
"""
from __future__ import annotations

from urllib.parse import quote

from . import http

API = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
BOARD_URL = "https://jobs.ashbyhq.com/{slug}"


def list_jobs(slug: str) -> list[dict]:
    data = http.get_json(API.format(slug=quote(slug, safe="")))
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    out = []
    for j in jobs:
        if not isinstance(j, dict) or not j.get("title"):
            continue
        if j.get("isListed") is False:
            continue
        places = [j.get("location") or ""]
        for extra in j.get("secondaryLocations") or []:
            name = extra.get("location") if isinstance(extra, dict) else extra
            if name:
                places.append(str(name))
        out.append({
            "id": str(j.get("id", "")),
            "title": str(j["title"]).strip(),
            "location": "; ".join(p for p in places if p),
            "url": str(j.get("jobUrl") or j.get("applyUrl") or ""),
            "posted": str(j.get("publishedAt") or "")[:10],
        })
    return out
