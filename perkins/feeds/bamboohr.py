"""BambooHR careers pages: <sub>.bamboohr.com/careers/list.

This is the JSON the public careers page itself loads. It is not a documented
API and its shape was not confirmed live when this adapter was written, so every
field is read defensively. It gives no posting date.
"""
from __future__ import annotations

from . import http

API = "https://{sub}.bamboohr.com/careers/list"
BOARD_URL = "https://{sub}.bamboohr.com/careers"
JOB_URL = "https://{sub}.bamboohr.com/careers/{id}"


def _place(j: dict) -> str:
    parts = []
    for key in ("location", "atsLocation"):
        loc = j.get(key)
        if isinstance(loc, dict):
            parts = [loc.get("city"), loc.get("state") or loc.get("province"), loc.get("country")]
            parts = [str(p) for p in parts if p]
            if parts:
                break
        elif isinstance(loc, str) and loc:
            parts = [loc]
            break
    text = ", ".join(parts)
    if j.get("isRemote") or str(j.get("locationType", "")) == "1":
        text = f"{text}; Remote" if text else "Remote"
    return text


def list_jobs(sub: str) -> list[dict]:
    data = http.get_json(API.format(sub=sub))
    if isinstance(data, dict):
        jobs = data.get("result") or data.get("jobs") or []
    else:
        jobs = data if isinstance(data, list) else []
    out = []
    for j in jobs:
        if not isinstance(j, dict):
            continue
        title = j.get("jobOpeningName") or j.get("title") or ""
        if not title or j.get("id") in (None, ""):
            continue
        out.append({
            "id": str(j["id"]),
            "title": str(title).strip(),
            "location": _place(j),
            "url": JOB_URL.format(sub=sub, id=j["id"]),
            "posted": str(j.get("datePosted") or "")[:10],
        })
    return out
