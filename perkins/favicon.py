"""The browser-tab icon for Perkins pages: the person's initials, white on the dashboard's
accent color, in a rounded square. Letters are drawn as strokes, not text, so the icon looks
the same on every computer and still reads at 16 pixels. Stdlib only.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from urllib.parse import quote

ACCENT = "#1d6a56"  # the dashboard's light-mode accent
HEIGHT = 28         # every glyph is 28 units tall, drawn inside a 64-unit square
GAP = 8
STROKE = 6

# Stroke outlines for A to Z: (width, SVG path data), y running down from the cap line.
GLYPHS = {
    "A": (16, "M0 28L8 0L16 28M3.5 18H12.5"),
    "B": (16, "M0 28V0H8a6 7 0 0 1 0 14H0M0 14H9a7 7 0 0 1 0 14H0"),
    "C": (16, "M13.7 4.1A8 14 0 1 0 13.7 23.9"),
    "D": (16, "M0 0V28H6A10 14 0 0 0 6 0Z"),
    "E": (15, "M15 0H0V28H15M0 14H11"),
    "F": (15, "M15 0H0V28M0 14H11"),
    "G": (16, "M13.7 4.1A8 14 0 1 0 16 14H9"),
    "H": (16, "M0 0V28M16 0V28M0 14H16"),
    "I": (10, "M5 0V28M0 0H10M0 28H10"),
    "J": (14, "M14 0V20A7 7 0 0 1 0 20"),
    "K": (16, "M0 0V28M16 0L0 17M5 12L16 28"),
    "L": (15, "M0 0V28H15"),
    "M": (20, "M0 28V0L10 16L20 0V28"),
    "N": (16, "M0 28V0L16 28V0"),
    "O": (16, "M8 0A8 14 0 1 0 8 28A8 14 0 1 0 8 0Z"),
    "P": (16, "M0 28V0H9a7 7.5 0 0 1 0 15H0"),
    "Q": (17, "M8 0A8 14 0 1 0 8 28A8 14 0 1 0 8 0ZM10 20L17 29"),
    "R": (16, "M0 28V0H9a7 7 0 0 1 0 14H0M8 14L16 28"),
    "S": (16, "M14.5 3.5A7.5 7 0 1 0 8 14A7.5 7 0 1 1 1.5 24.5"),
    "T": (16, "M0 0H16M8 0V28"),
    "U": (16, "M0 0V19A8 9 0 0 0 16 19V0"),
    "V": (16, "M0 0L8 28L16 0"),
    "W": (20, "M0 0L4.5 28L10 10L15.5 28L20 0"),
    "X": (16, "M0 0L16 28M16 0L0 28"),
    "Y": (16, "M0 0L8 14L16 0M8 14V28"),
    "Z": (16, "M0 0H16L0 28H16"),
}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "phd", "md", "mba", "esq"}


def name_from_master(master: Path) -> str:
    """The name on the master resume: its first '# ' heading. Empty if there isn't one."""
    try:
        text = master.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _letter(word: str) -> str:
    """A word's first letter as plain A to Z (accents dropped), or empty."""
    base = unicodedata.normalize("NFKD", word[:1]).encode("ascii", "ignore").decode().upper()
    return base if base in GLYPHS else ""


def initials(name: str) -> str:
    """First and last initials ("Jordan Avery" is JA), skipping suffixes like Jr. or PhD.
    "P" (for Perkins) when there's no usable name."""
    name = re.sub(r"\([^)]*\)", " ", name.split(",")[0])
    words = [w for w in re.findall(r"[^\W\d_][\w'.-]*", name) if w.strip(".").lower() not in SUFFIXES]
    if not words:
        return "P"
    picks = [words[0]] if len(words) == 1 else [words[0], words[-1]]
    letters = "".join(_letter(w) for w in picks)
    return letters or "P"


def svg(letters: str, color: str = ACCENT) -> str:
    letters = "".join(c for c in letters.upper() if c in GLYPHS)[:2] or "P"
    total = sum(GLYPHS[c][0] for c in letters) + GAP * (len(letters) - 1)
    x, y = (64 - total) / 2, (64 - HEIGHT) / 2
    paths = []
    for c in letters:
        width, d = GLYPHS[c]
        paths.append(f'<path transform="translate({x:g} {y:g})" d="{d}"/>')
        x += width + GAP
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
            f'<rect width="64" height="64" rx="12" fill="{color}"/>'
            f'<g fill="none" stroke="#fff" stroke-width="{STROKE}" stroke-linecap="square" stroke-linejoin="round">'
            + "".join(paths) + "</g></svg>")


def link(master: Path, color: str = ACCENT) -> str:
    """The <link rel=icon> tag for a page, with the icon inline as a data URI."""
    return ("<link rel='icon' type='image/svg+xml' href='data:image/svg+xml,"
            + quote(svg(initials(name_from_master(master)), color)) + "'>")
