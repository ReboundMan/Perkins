---
name: watch
description: Manage the employers the user watches and scan their public job boards for new postings. Use when the user says "watch <company>", "add <company> to my watch list", "stop watching <company>", "check my watch list", "any new jobs at the companies I watch?", "scan for new postings", "find which job board <company> uses", or /perkins:watch.
allowed-tools: Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" *)
---

# Employers to watch

Every command is `python "${CLAUDE_PLUGIN_ROOT}/run.py" ...` (`python3` on macOS or Linux if `python` isn't found). The watch list is the Employers to watch table in `tracker.md`. The plugin's `docs/scanning.md` has the details.

## Add an employer

Ask why they want to watch it, if they haven't said. Find where its jobs are posted: the careers page link, and which board it uses (Greenhouse, Ashby, Lever, Workable, BambooHR, Rippling, Workday, or something else). `run.py scan --discover <file>` can guess the board for a list of company names (one per line, in a temporary file). Then:

`run.py tracker add "Employers to watch" --set "Company=<company>" --set "Why watch=<their reason>" --set "Where to look=[<host/path>](<url>)" --set "Board=<board>" --set "Application limit=<if the employer states one, such as 3/12mo>" --set "Next check=<today>"`

## Scan

`run.py scan` reads each watched employer's public job board, adds senior postings that are new since the last scan to Considering as leads, and sets each employer's next check two weeks out. Add `--dry-run` to preview without changing anything. Report what it found: new leads by company, and any employer marked "check by hand" because its board can't be read automatically (say which, so the user can look themselves).

The scan reads only public, unauthenticated feeds. Never sign in to a careers site, and never retry a site that refused.

## Remove an employer

`run.py tracker remove "Employers to watch" --match "Company=<company>"`. Leads it already found stay in Considering.
