"""Plain HTTP for the feeds: one request, a timeout, a size cap, and no retries.

No cookies, no browser impersonation, nothing that tries to get past a bot
check. A board that refuses a plain request is one to check by hand.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

USER_AGENT = "Perkins job-board scan (+https://github.com/ReboundMan/Perkins)"
TIMEOUT = 15
MAX_BYTES = 25 * 1024 * 1024


class FeedError(Exception):
    """A request failed or returned something unreadable; the message says which URL and why."""


def _request(url: str, data: bytes | None = None, headers: dict | None = None) -> str:
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            body = resp.read(MAX_BYTES + 1)
            charset = resp.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as e:
        raise FeedError(f"{url} answered HTTP {e.code}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise FeedError(f"{url} could not be reached: {reason}") from e
    if len(body) > MAX_BYTES:
        raise FeedError(f"{url} returned more than {MAX_BYTES // (1024 * 1024)} MB; stopped reading")
    return body.decode(charset, errors="replace")


def _parse(url: str, text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise FeedError(f"{url} did not return JSON ({e.msg})") from e


def get_text(url: str) -> str:
    """The body of a GET request as text."""
    return _request(url, headers={"Accept": "text/html,application/xhtml+xml,*/*"})


def get_json(url: str):
    """The body of a GET request, parsed as JSON."""
    return _parse(url, _request(url, headers={"Accept": "application/json"}))


def post_json(url: str, body: dict):
    """POST a JSON body and parse the JSON reply."""
    data = json.dumps(body).encode("utf-8")
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    return _parse(url, _request(url, data=data, headers=headers))
