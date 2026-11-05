"""Refuse sensitive numbers before they reach any file Perkins writes.

Perkins never stores a Social Security number, a claimant ID, or a benefits login. The
skills refuse them in conversation; this is the backstop in code, used by the log writer
and the tracker editor. It looks for the shapes, not every possibility: a nine-digit job
requisition number is fine, a nine-digit number next to "SSN" is not.
"""
from __future__ import annotations

import re

from .errors import PerkinsError

CHECKS = [
    ("a Social Security number", re.compile(r"(?<![\d-])\d{3}[- ]\d{2}[- ]\d{4}(?![\d-])")),
    ("a Social Security number", re.compile(r"\b(?:ssn|social security|soc\.? ?sec\.?)\b\D{0,24}\d{3}\D?\d{2}\D?\d{4}\b", re.I)),
    ("a claimant ID", re.compile(r"\bclaimant\s*(?:id|number|no\.?|#)\D{0,12}\d{4,}", re.I)),
    ("a password or PIN", re.compile(r"\b(?:password|passcode|pin)\b\s*(?:is|[:=])\s*\S", re.I)),
]


class SensitiveError(PerkinsError):
    """A value looks like something Perkins never stores."""


def refuse_sensitive(values: dict[str, str]) -> None:
    for key, value in values.items():
        for what, rx in CHECKS:
            if rx.search(str(value)):
                raise SensitiveError(f"{key} looks like it holds {what}. Perkins never stores one; "
                                     "remove it and try again.")
