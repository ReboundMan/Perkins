"""Job board feeds: one small adapter per applicant tracking system.

Each adapter exposes list_jobs(slug_or_site) and returns a list of dicts with
the keys id, title, location, url, and posted (an ISO date, or "" if the board
does not say). Every adapter reads a public, unauthenticated endpoint.
"""
from __future__ import annotations

import importlib

# Adapter module name -> the name a tracker's Board column uses.
BOARD_NAMES = {
    "greenhouse": "Greenhouse",
    "ashby": "Ashby",
    "lever": "Lever",
    "workable": "Workable",
    "bamboohr": "BambooHR",
    "rippling": "Rippling",
    "workday": "Workday",
}


def adapter(board: str):
    """The adapter module for a board name such as "Greenhouse", or None if there is none."""
    key = (board or "").strip().lower()
    if key not in BOARD_NAMES:
        return None
    return importlib.import_module(f"perkins.feeds.{key}")
