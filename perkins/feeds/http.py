"""Plain HTTP for postings and the feeds: one request, a timeout, a size cap, and no retries.

No cookies, no browser impersonation, nothing that tries to get past a bot check. A board
that refuses a plain request is one to check by hand.

Every request, and every redirect it follows, must go to a public http or https address.
A posting link (or text inside a posting) can't steer a fetch to this computer, the local
network, or a cloud metadata address.
"""
from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from ..errors import PerkinsError

USER_AGENT = "Perkins (+https://github.com/ReboundMan/Perkins)"
TIMEOUT = 15
MAX_BYTES = 25 * 1024 * 1024


class FeedError(PerkinsError):
    """A request failed, was refused, or returned something unreadable; the message says which URL and why."""


def check_url(url: str) -> None:
    """Refuse anything but http(s) to a public address."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FeedError(f"{url} isn't an http or https link")
    try:
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80),
                                   type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise FeedError(f"{url} could not be reached: {e}") from e
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%", 1)[0])
        if not ip.is_global or ip.is_multicast:
            raise FeedError(f"{url} points at a private or local address ({ip}); Perkins only fetches public sites")


class _CheckedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_CheckedRedirects())


def _request(url: str, data: bytes | None = None, headers: dict | None = None) -> str:
    check_url(url)
    hdrs = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdrs, method="POST" if data is not None else "GET")
    try:
        with _OPENER.open(req, timeout=TIMEOUT) as resp:
            body = resp.read(MAX_BYTES + 1)
            charset = resp.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as e:
        raise FeedError(f"{url} answered HTTP {e.code}") from e
    except FeedError:
        raise
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise FeedError(f"{url} could not be reached: {reason}") from e
    if len(body) > MAX_BYTES:
        raise FeedError(f"{url} returned more than {MAX_BYTES // (1024 * 1024)} MB; stopped reading")
    try:
        return body.decode(charset, errors="replace")
    except LookupError:  # a made-up charset name in the response header
        return body.decode("utf-8", errors="replace")


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
