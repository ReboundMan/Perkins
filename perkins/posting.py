"""Fetch one job posting's full text from its URL.

Routes by URL shape: Workday and Greenhouse through their public JSON, Ashby
and most other sites through the page's JSON-LD, iCIMS through its iframe page.
A posting that cannot be read raises PostingError, whose message says to open
the page in the browser or paste the text.

CLI (through run.py):
  posting URL [--json]
"""
from __future__ import annotations

import html
import json
import re
from datetime import date
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

from .feeds import http, jsonld

WORKDAY_HOST = re.compile(r"^([\w-]+)\.wd\d+\.myworkdayjobs\.com$", re.I)
LANG_SEGMENT = re.compile(r"^[a-z]{2}-[A-Z]{2}$")
GREENHOUSE_HOSTS = ("job-boards.greenhouse.io", "boards.greenhouse.io",
                    "job-boards.eu.greenhouse.io", "boards.eu.greenhouse.io")
GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{id}"
BOARD_FOR = re.compile(r"[?&;]for=([\w-]+)")
ICIMS_PATH = re.compile(r"^/jobs/(\d+)(?:/[^/]*)?/job/?$", re.I)
TITLE_TAG = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
THIN_WORDS = 120


class PostingError(Exception):
    """A posting could not be read; the message says what to do instead."""


def _blank(url: str, source: str) -> dict:
    return {"title": "", "company": "", "location": "", "req_id": "", "description": "",
            "source": source, "url": url, "notes": ""}


def _from_ld(out: dict, ld: dict) -> dict:
    """Fill empty fields from a parsed JSON-LD posting, and note the pay and date it gives."""
    for key, ld_key in (("title", "title"), ("company", "company"), ("location", "location"),
                        ("req_id", "identifier"), ("description", "description")):
        if not out[key] and ld.get(ld_key):
            out[key] = ld[ld_key]
    notes = [out["notes"]] if out["notes"] else []
    if ld.get("baseSalary"):
        notes.append(f"Base pay listed: {ld['baseSalary']}.")
    if ld.get("datePosted"):
        notes.append(f"Posted {ld['datePosted'][:10]}.")
    out["notes"] = " ".join(notes)
    return out


# --- routes ---------------------------------------------------------------------

def workday_api_url(url: str) -> str | None:
    """The cxs JSON URL for a Workday job page, or None if the URL is not one."""
    parts = urlsplit(url)
    m = WORKDAY_HOST.match(parts.hostname or "")
    if not m or "/job/" not in parts.path:
        return None
    segments = [s for s in parts.path.split("/") if s]
    if segments and LANG_SEGMENT.match(segments[0]):
        segments = segments[1:]
    path = "/".join(["wday", "cxs", m.group(1)] + segments)
    return urlunsplit(("https", parts.netloc, "/" + path, "", ""))


def from_workday(url: str, api: str) -> dict:
    data = http.get_json(api)
    info = data.get("jobPostingInfo", {}) if isinstance(data, dict) else {}
    out = _blank(url, "workday")
    out["title"] = str(info.get("title") or "").strip()
    org = data.get("hiringOrganization") if isinstance(data, dict) else None
    out["company"] = str(org.get("name") or "").strip() if isinstance(org, dict) else ""
    places = [info.get("location")] + list(info.get("additionalLocations") or [])
    out["location"] = "; ".join(str(p) for p in places if p)
    out["req_id"] = str(info.get("jobReqId") or "").strip()
    out["description"] = jsonld.to_text(info.get("jobDescription") or "")
    if info.get("postedOn"):
        out["notes"] = f"{info['postedOn']}."
    return out


def greenhouse_target(url: str) -> tuple[str, str] | None:
    """(board, job id) from a hosted Greenhouse job URL, or None."""
    parts = urlsplit(url)
    if (parts.hostname or "").lower() not in GREENHOUSE_HOSTS:
        return None
    query = parse_qs(parts.query)
    if query.get("for") and query.get("token"):
        return query["for"][0], query["token"][0]
    m = re.match(r"^/([\w-]+)/jobs/(\d+)", parts.path)
    return (m.group(1), m.group(2)) if m else None


def gh_jid(url: str) -> str | None:
    """The gh_jid on a company careers URL that embeds a Greenhouse board."""
    ids = parse_qs(urlsplit(url).query).get("gh_jid")
    return ids[0] if ids and ids[0].isdigit() else None


def from_greenhouse(url: str, board: str, job_id: str) -> dict:
    data = http.get_json(GREENHOUSE_API.format(board=quote(board, safe=""), id=quote(job_id, safe="")))
    if not isinstance(data, dict):
        data = {}
    out = _blank(url, "greenhouse")
    out["title"] = str(data.get("title") or "").strip()
    out["company"] = str(data.get("company_name") or "").strip()
    loc = data.get("location")
    out["location"] = str(loc.get("name", "") if isinstance(loc, dict) else loc or "").strip()
    out["req_id"] = str(data.get("requisition_id") or data.get("id") or "").strip()
    out["description"] = jsonld.to_text(html.unescape(str(data.get("content") or "")))
    if data.get("absolute_url"):
        out["url"] = str(data["absolute_url"])
    if not out["company"]:
        out["notes"] = f"The board did not name the company; its Greenhouse board is {board!r}."
    return out


def from_page_ld(url: str, page: str, source: str) -> dict:
    ld = jsonld.job_posting(page)
    if not ld:
        return _blank(url, source)
    return _from_ld(_blank(url, source), ld)


def icims_target(url: str) -> str | None:
    """The iframe URL for an iCIMS job page, or None if the URL is not one."""
    parts = urlsplit(url)
    if not (parts.hostname or "").lower().endswith(".icims.com"):
        return None
    if not ICIMS_PATH.match(parts.path):
        return None
    return urlunsplit((parts.scheme or "https", parts.netloc, parts.path, "in_iframe=1", ""))


def from_icims(url: str, frame_url: str) -> dict:
    page = http.get_text(frame_url)
    out = _blank(url, "icims")
    text = jsonld.html_to_text(page)
    if len(text.split()) >= THIN_WORDS:
        out["description"] = text
    ld = jsonld.job_posting(page)
    if ld:
        _from_ld(out, ld)
    if not out["title"]:
        m = TITLE_TAG.search(page)
        out["title"] = html.unescape(m.group(1)).strip() if m else ""
    if not out["req_id"]:
        m = ICIMS_PATH.match(urlsplit(url).path)
        out["req_id"] = m.group(1) if m else ""
    return out


def fetch_posting(url: str) -> dict:
    """title, company, location, req_id, description, source, url, notes for one posting URL."""
    url = (url or "").strip()
    if not re.match(r"^https?://", url, re.I):
        raise PostingError(f"Not a web address: {url!r}. Paste the posting's full URL, or paste its text.")
    tried: list[str] = []
    out = None
    api, gh, frame = workday_api_url(url), greenhouse_target(url), icims_target(url)
    try:
        if api:
            out = from_workday(url, api)
        elif gh:
            out = from_greenhouse(url, *gh)
        elif frame:
            out = from_icims(url, frame)
    except http.FeedError as e:
        tried.append(str(e))
    if not frame and (not out or not out["description"]):
        # Everything else, and the fallback when a JSON route fails: the page itself.
        try:
            page = http.get_text(url)
        except http.FeedError as e:
            tried.append(str(e))
            page = ""
        jid = gh_jid(url) if page and not gh else None
        board = BOARD_FOR.search(page) if jid else None
        if board:
            try:
                out = from_greenhouse(url, board.group(1), jid)
                out["url"] = url
            except http.FeedError as e:
                tried.append(str(e))
        if page and (not out or not out["description"]):
            host = (urlsplit(url).hostname or "").lower()
            out = from_page_ld(url, page, "ashby" if host == "jobs.ashbyhq.com" else "jsonld")
    if not out or not out["description"]:
        why = f" ({'; '.join(tried)})" if tried else ""
        raise PostingError(f"Could not read a job description from {url}{why}. "
                           "Open the page in the browser and copy the text, or paste the posting text here.")
    return out


# --- CLI --------------------------------------------------------------------------

def add_arguments(p) -> None:
    p.add_argument("url", help="the job posting's URL")
    p.add_argument("--json", action="store_true", help="print every field as JSON")


def cli(args, cfg=None, today: date | None = None) -> int:
    post = fetch_posting(args.url)
    if args.json:
        print(json.dumps(post, indent=2, ensure_ascii=False))
        return 0
    head = post["title"] or "Untitled posting"
    if post["company"]:
        head += f" at {post['company']}"
    if post["location"]:
        head += f" ({post['location']})"
    print(head)
    print()
    print(post["description"])
    return 0
