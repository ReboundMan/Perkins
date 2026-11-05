"""Perkins: tailored resumes, an application tracker, and a work-search log, run through Claude Code."""

from pathlib import Path

# VERSION at the top of the repository is the one place the version is set (house standard 10).
# The plugin manifests repeat it because Claude Code reads them; tests/test_package.py holds them equal.
try:
    __version__ = (Path(__file__).resolve().parent.parent / "VERSION").read_text(encoding="utf-8").strip()
except OSError:
    __version__ = "unknown"
