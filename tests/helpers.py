"""Shared helpers for tests: fictional data folders in either mode."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from perkins import config as C
from perkins import init as I


def make_home(tmp: Path, mode: str = C.SEARCH, today: date = date(2027, 3, 10), **kw) -> C.Config:
    I.init(tmp, mode, today, pointer=False, **kw)
    return C.load(tmp)


def claims_home(tmp: Path, today: date = date(2027, 3, 10), claim_start: date = date(2027, 2, 28), **kw) -> C.Config:
    return make_home(tmp, C.CLAIMS, today, state="wa", claim_start=claim_start, **kw)


EMPLOYER_FIELDS = {
    "Job title or reference number": "Director of Operations (LA-1)",
    "Employer or business name": "Larkspur Analytics",
    "How": "Online (careers site)",
    "Type": "Application/resume",
    "Employer contact info": "Portland, OR · https://jobs.example.com/la · phone not listed",
    "Person": "none named in the posting",
    "Result and next step": "Applied; awaiting a response",
    "Source": "https://jobs.example.com/la",
}
