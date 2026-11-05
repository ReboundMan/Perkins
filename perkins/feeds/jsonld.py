"""Read a JobPosting from a page's JSON-LD, and turn posting HTML into plain text.

Most career sites embed the posting as <script type="application/ld+json">, as a
single object, a list, or inside "@graph". Stdlib only (html.parser).
"""
from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser

BLOCK_TAGS = {
    "p", "div", "section", "article", "header", "footer", "main", "aside", "nav", "blockquote",
    "pre", "table", "tr", "ul", "ol", "dl", "dt", "dd", "figure", "form", "hr", "address",
    "h1", "h2", "h3", "h4", "h5", "h6",
}
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head", "iframe"}
TAG_RE = re.compile(r"<[a-zA-Z/!]")


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self.skip += 1
        elif self.skip:
            return
        elif tag == "br":
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n-\n")
        elif tag in ("td", "th"):
            self.parts.append(" ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n\n")

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in BLOCK_TAGS:
            self.parts.append("\n\n")
        elif not self.skip and tag == "li":
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(re.sub(r"\s+", " ", data.replace("\xa0", " ")))


def _tidy(lines: list[str]) -> str:
    """Strip each line, attach bullet markers to their text, and keep single blank lines between paragraphs."""
    out, bullet = [], False
    for line in lines:
        line = re.sub(r"[ \t]{2,}", " ", line.replace("\xa0", " ")).strip()
        if line == "-":
            if len(out) >= 2 and not out[-1] and out[-2].startswith("- "):
                out.pop()  # list items sit on consecutive lines
            bullet = True
            continue
        if bullet and not line:
            continue
        if bullet:
            line, bullet = "- " + line, False
        if not line and (not out or not out[-1]):
            continue
        out.append(line)
    return "\n".join(out).strip()


def html_to_text(fragment: str) -> str:
    """Readable plain text from HTML: every word kept, paragraphs separated by a blank line, list items as "- "."""
    p = _TextParser()
    p.feed(fragment or "")
    p.close()
    return _tidy("".join(p.parts).split("\n"))


def to_text(value: str) -> str:
    """Plain text from a description that may be HTML, escaped HTML (&lt;p&gt;), or already plain."""
    s = str(value or "")
    if not TAG_RE.search(s) and "&lt;" in s:
        s = html.unescape(s)
    if TAG_RE.search(s):
        return html_to_text(s)
    return _tidy(html.unescape(s).replace("\r\n", "\n").split("\n"))


class _ScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[str] = []
        self._buf: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            kind = (dict(attrs).get("type") or "").strip().lower()
            self._buf = [] if kind.startswith("application/ld+json") else None

    def handle_endtag(self, tag):
        if tag == "script" and self._buf is not None:
            self.blocks.append("".join(self._buf))
            self._buf = None

    def handle_data(self, data):
        if self._buf is not None:
            self._buf.append(data)


def blocks(page: str) -> list:
    """Every parseable JSON-LD block on a page."""
    p = _ScriptParser()
    try:
        p.feed(page or "")
        p.close()
    except Exception:
        pass  # a malformed page still yields whatever blocks came before the fault
    out = []
    for raw in p.blocks:
        text = raw.strip()
        for junk in ("<!--", "-->", "//<![CDATA[", "//]]>", "<![CDATA[", "]]>"):
            text = text.replace(junk, "")
        try:
            out.append(json.loads(text.strip(), strict=False))
        except json.JSONDecodeError:
            continue
    return out


def _is_posting(d: dict) -> bool:
    t = d.get("@type")
    types = t if isinstance(t, list) else [t]
    return any(str(x).lower() == "jobposting" for x in types)


def _walk(node, depth: int = 0):
    """Yield every JobPosting dict in a parsed block: a single object, a list, @graph, or nested."""
    if depth > 6:
        return
    if isinstance(node, list):
        for item in node:
            yield from _walk(item, depth + 1)
    elif isinstance(node, dict):
        if _is_posting(node):
            yield node
            return
        for value in node.values():
            if isinstance(value, (dict, list)):
                yield from _walk(value, depth + 1)


def _name(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, dict):
        return str(value.get("name") or "").strip()
    return str(value or "").strip()


def _place(loc) -> str:
    if isinstance(loc, str):
        return loc.strip()
    if not isinstance(loc, dict):
        return ""
    addr = loc.get("address")
    if isinstance(addr, str):
        return addr.strip()
    if isinstance(addr, dict):
        parts = [addr.get("addressLocality"), addr.get("addressRegion"), _name(addr.get("addressCountry"))]
        text = ", ".join(str(p).strip() for p in parts if p)
        if text:
            return text
    return _name(loc)


def _location(d: dict) -> str:
    locs = d.get("jobLocation")
    locs = locs if isinstance(locs, list) else [locs]
    places = [p for p in (_place(x) for x in locs) if p]
    if "telecommute" in str(d.get("jobLocationType", "")).lower():
        where = _name(d.get("applicantLocationRequirements"))
        places.append(f"Remote ({where})" if where else "Remote")
    seen = []
    for p in places:
        if p not in seen:
            seen.append(p)
    return "; ".join(seen)


def _number(v) -> str:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"
    return str(v).strip()


def salary_text(value) -> str:
    """baseSalary (a MonetaryAmount, a number, or text) as one readable line."""
    if value in (None, "", {}):
        return ""
    if not isinstance(value, dict):
        return _number(value)
    currency = str(value.get("currency") or "").strip()
    amount = value.get("value")
    unit = ""
    if isinstance(amount, dict):
        unit = str(amount.get("unitText") or "").strip()
        low, high, single = amount.get("minValue"), amount.get("maxValue"), amount.get("value")
        if low not in (None, "") and high not in (None, "") and low != high:
            text = f"{_number(low)} to {_number(high)}"
        else:
            given = [v for v in (single, low, high) if v not in (None, "")]
            text = _number(given[0]) if given else ""
    else:
        text = _number(amount) if amount not in (None, "") else ""
    if not text:
        return ""
    line = f"{currency} {text}".strip()
    return f"{line} per {unit.lower()}" if unit else line


def _identifier(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, dict):
        return str(value.get("value") or value.get("name") or "").strip()
    return str(value or "").strip()


def parse_posting(d: dict) -> dict:
    """The fields Perkins uses from one JobPosting object."""
    return {
        "title": str(d.get("title") or d.get("name") or "").strip(),
        "company": _name(d.get("hiringOrganization")),
        "location": _location(d),
        "identifier": _identifier(d.get("identifier")),
        "datePosted": str(d.get("datePosted") or "").strip(),
        "baseSalary": salary_text(d.get("baseSalary")),
        "description": to_text(d.get("description") or ""),
    }


def job_posting(page: str) -> dict | None:
    """The first JobPosting on a page, parsed, or None if the page has none."""
    for block in blocks(page):
        for d in _walk(block):
            return parse_posting(d)
    return None
