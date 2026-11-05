"""Rebuild examples/sample-data: one fictional applicant, Jordan Avery, three weeks into a
Washington claim. Every person, employer, and link here is made up.

Usage: python examples/make_sample.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "examples" / "sample-data"
HERE = Path(__file__).resolve().parent


def run(today: str, *args: str) -> None:
    cmd = [sys.executable, str(ROOT / "run.py"), "--data", str(DATA), "--today", today, *args]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        sys.exit(f"failed: {' '.join(args)}\n{out.stdout}\n{out.stderr}")


def entry(today: str, kind: str, fit: str, *fields: str, reason: str = "") -> None:
    args = ["clerk", "add", "--date", today, "--kind", kind, "--fit", fit]
    for f in fields:
        args += ["--field", f]
    if reason:
        args += ["--reason", reason]
    run(today, *args)


def main() -> None:
    if DATA.exists():
        shutil.rmtree(DATA)
    run("2027-03-01", "init", "--no-pointer", "--mode", "search-claims", "--state", "wa",
        "--claim-start", "2027-02-28", "--timezone", "America/Los_Angeles")
    shutil.copyfile(HERE / "sample-master.md", DATA / "master.md")

    t = "tracker"
    run("2027-03-01", t, "add", "Employers to watch", "--set", "Company=Larkspur Analytics",
        "--set", "Why watch=Operations and analytics leadership; Portland office",
        "--set", "Where to look=[job-boards.greenhouse.io/larkspuranalytics](https://job-boards.greenhouse.io/larkspuranalytics)",
        "--set", "Board=Greenhouse", "--set", "Last checked=2027-03-01", "--set", "Next check=2027-03-15")
    run("2027-03-01", t, "add", "Employers to watch", "--set", "Company=Bluewater Grid",
        "--set", "Why watch=Grid software; growing its operations team",
        "--set", "Where to look=[jobs.ashbyhq.com/bluewatergrid](https://jobs.ashbyhq.com/bluewatergrid)",
        "--set", "Board=Ashby", "--set", "Application limit=2/6mo",
        "--set", "Last checked=2027-03-01", "--set", "Next check=2027-03-15")
    run("2027-03-01", t, "add", "Employers to watch", "--set", "Company=Alder Robotics",
        "--set", "Why watch=Program leadership for warehouse robotics",
        "--set", "Where to look=[jobs.lever.co/alderrobotics](https://jobs.lever.co/alderrobotics)",
        "--set", "Board=Lever", "--set", "Last checked=2027-02-26", "--set", "Next check=2027-03-12")

    # Week ending 2027-03-06: three solid activities, claim filed Monday 2027-03-08.
    run("2027-03-02", t, "add", "Submitted", "--set", "Submitted=2027-03-02", "--set", "Company=Larkspur Analytics",
        "--set", "Role=[Director of Operations](https://jobs.example.com/larkspur/director-of-operations)",
        "--set", "Req or ID=LA-2231", "--set", "Channel=Careers site", "--set", "Resume used=Larkspur resume",
        "--set", "Status=Under review", "--set", "Claim log=Week ending 2027-03-06, activity 1 (solid)",
        "--set", "Next follow-up=2027-03-16 *suggested*",
        "--set", "Follow-up notes=Hiring range listed; Portland hybrid.")
    entry("2027-03-02", "Employer contact", "solid",
          "Job title or reference number=Director of Operations (LA-2231)",
          "Employer or business name=Larkspur Analytics", "How=Online (Larkspur careers site)",
          "Type=Application/resume",
          "Employer contact info=Portland, OR · https://jobs.example.com/larkspur/director-of-operations · phone not listed",
          "Person=none named in the posting", "Result and next step=Applied with a tailored resume; awaiting a response",
          "Source=https://jobs.example.com/larkspur/director-of-operations")
    run("2027-03-03", t, "add", "Submitted", "--set", "Submitted=2027-03-03", "--set", "Company=Pinecrest Health",
        "--set", "Role=[Head of Customer Success](https://jobs.example.com/pinecrest/head-of-customer-success)",
        "--set", "Req or ID=PH-118", "--set", "Channel=Careers site", "--set", "Resume used=Pinecrest resume",
        "--set", "Status=Applied", "--set", "Claim log=Week ending 2027-03-06, activity 2 (solid)",
        "--set", "Next follow-up=2027-03-10 *suggested*")
    entry("2027-03-03", "Employer contact", "solid",
          "Job title or reference number=Head of Customer Success (PH-118)",
          "Employer or business name=Pinecrest Health", "How=Online (Pinecrest careers site)",
          "Type=Application/resume",
          "Employer contact info=Seattle, WA · https://jobs.example.com/pinecrest/head-of-customer-success · phone not listed",
          "Person=none named in the posting", "Result and next step=Applied with a tailored resume; awaiting a response",
          "Source=https://jobs.example.com/pinecrest/head-of-customer-success")
    run("2027-03-04", t, "add", "Conversations and referrals", "--set", "Date=2027-03-04", "--set", "Company=Kestrel Energy",
        "--set", "Person=Sam Ortiz, Recruiter", "--set", "About=Head of Customer Success opening",
        "--set", "Status=Interview scheduled", "--set", "Claim log=Week ending 2027-03-06, activity 3 (solid)",
        "--set", "Next follow-up=2027-03-10", "--set", "Follow-up notes=First interview on 2027-03-10.")
    entry("2027-03-04", "Employer contact", "solid",
          "Job title or reference number=Head of Customer Success",
          "Employer or business name=Kestrel Energy", "How=Phone", "Type=Inquiry",
          "Employer contact info=Boise, ID · https://jobs.example.com/kestrel · recruiter's email given",
          "Person=Sam Ortiz, Recruiter", "Result and next step=Recruiter call; first interview set for 2027-03-10",
          "Source=Jordan's own account, 2027-03-04")
    run("2027-03-08", "clerk", "filed", "--week", "2027-03-06", "--on", "2027-03-08")

    # Week ending 2027-03-13: two solid so far and one to check, as of Friday 2027-03-12.
    run("2027-03-08", t, "add", "Submitted", "--set", "Submitted=2027-03-08", "--set", "Company=Alder Robotics",
        "--set", "Role=[VP of Program Management](https://jobs.example.com/alder/vp-program-management)",
        "--set", "Req or ID=AR-77", "--set", "Channel=Careers site", "--set", "Resume used=Alder resume",
        "--set", "Status=Applied", "--set", "Claim log=Week ending 2027-03-13, activity 1 (solid)",
        "--set", "Next follow-up=2027-03-22 *suggested*")
    entry("2027-03-08", "Employer contact", "solid",
          "Job title or reference number=VP of Program Management (AR-77)",
          "Employer or business name=Alder Robotics", "How=Online (Alder careers site)",
          "Type=Application/resume",
          "Employer contact info=Reno, NV · https://jobs.example.com/alder/vp-program-management · phone not listed",
          "Person=none named in the posting", "Result and next step=Applied with a tailored resume; awaiting a response",
          "Source=https://jobs.example.com/alder/vp-program-management")
    run("2027-03-10", t, "update", "Conversations and referrals", "--match", "Company=Kestrel",
        "--set", "Status=Interviewed; second round pending", "--set", "Next follow-up=2027-03-13",
        "--set", "Follow-up notes=Send the thank-you note and the case study.")
    entry("2027-03-10", "Employer contact", "solid",
          "Job title or reference number=Head of Customer Success",
          "Employer or business name=Kestrel Energy", "How=Online (video interview)", "Type=Interview",
          "Employer contact info=Boise, ID · https://jobs.example.com/kestrel · recruiter's email given",
          "Person=Sam Ortiz, Recruiter, and the VP of Customer Experience",
          "Result and next step=First interview; second round expected next week",
          "Source=Jordan's own account, 2027-03-10")
    entry("2027-03-11", "WorkSource activity", "check",
          "What activity=Resume workshop", "What documentation=Attendance confirmation requested",
          "Office name and city=WorkSource Example Center, Tacoma",
          "Person=Workshop facilitator (name not given)",
          "Result and next step=Attended; confirmation email expected",
          "Source=Jordan's own account, 2027-03-11",
          reason="The attendance confirmation hasn't arrived yet.")

    run("2027-03-11", t, "add", "Considering", "--set", "Found=2027-03-11", "--set", "Company=Bluewater Grid",
        "--set", "Role=[Director, Grid Operations](https://jobs.example.com/bluewater/director-grid-operations)",
        "--set", "Where=Remote US", "--set", "Base pay=not listed", "--set", "Resume=Not built",
        "--set", "Status=Lead", "--set", "Next step=Found in the 2027-03-11 watch-list scan; read the posting")
    run("2027-03-12", t, "add", "Considering", "--set", "Found=2027-03-09", "--set", "Company=Larkspur Analytics",
        "--set", "Role=[Senior Manager, Analytics Enablement](https://jobs.example.com/larkspur/analytics-enablement)",
        "--set", "Where=Portland, OR", "--set", "Base pay=not listed", "--set", "Resume=Ready",
        "--set", "Status=Resume ready", "--set", "Next step=Submit")
    run("2027-03-12", t, "add", "Passed", "--set", "Date=2027-03-05", "--set", "Company=Pinecrest Health",
        "--set", "Role=Director of Member Experience", "--set", "Why=Relocation required.")

    app = DATA / "applications" / "2027-03-08-alder-robotics-vp-of-program-management"
    app.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(HERE / "sample-tailored-resume.md", app / "resume.md")
    run("2027-03-12", "dashboard")


if __name__ == "__main__":
    main()
    print(f"rebuilt {DATA}")
