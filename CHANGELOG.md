# Changelog

All notable changes to Perkins are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Perkins adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Virginia, the second state for claims tracking (`states/va.toml`), researched from the Virginia Employment Commission's own pages, the Code of Virginia, and the Virginia Administrative Code: two work search activities a week, Sunday-to-Saturday weeks, the claim reminder on Sunday, and VEC's log fields in the order of the sample log in its Claimant Handbook. Workforce center activities are always potentially counts, because VEC's handbook counts them and its web pages ask for two different employers. The tailor and log-activity skills use each state's own field names.

- A yellow grade, **potentially counts**, for a complete log entry the state's rules don't clearly count (in Washington, say, a networking conversation that isn't clearly an approved activity). It's shown on the claim log page, the dashboard, `status`, and the reminders, and never counts toward the week's minimum. `clerk add --fit maybe` writes one with a reason, and a state file can mark a whole activity kind as potentially counts (`counts = "maybe"` with a `maybe_reason`).
- A guidance-only headline wherever Perkins shows a state's rules: the state's rules can change at any time, take precedence over anything Perkins says, shows, or counts, and are yours to know and meet. The full headline opens the state rules guide and `states/README.md`, sits in every state file's header, and is said once at setup; a one-line version is on the claim log page (prep notes), the dashboard's claim panel, and `status`.

### Changed

- The check grade is red-orange instead of amber, so yellow means only "potentially counts".

## [0.2.0] - 2026-11-05

Private preview, ready for beta testers.

### Added

- The claim log page (claims tracking): `claim-log.html`, rebuilt with the dashboard and linked from it, walks a state reviewer through the work-search log. One collapsed row per claim week, newest first, with its count against the minimum and its filing status; each activity with the state's fields, its posting, the resume and cover letter PDFs that were sent, the Claude Docs copy when configured, and embedded confirmation screenshots. It opens in a meeting view every time; "Show prep notes" adds fit grades, sources, week counts, and the full text of blank fields. Expand all, print, phone, and dark mode. New `claim-log` command.
- A browser tab icon on the dashboard and the claim log page: your initials from the master resume, white on the dashboard's green.
- A tip line at the bottom of the dashboard, linking to a page where you can buy Perkins's maker a frosty beverage. It isn't printed, and it never appears on the claim log page. The README, the getting-started page, and the repository's Sponsor button link the same tip jar.

### Changed

- The tailor skill records the application's folder in a log entry's Source, and says when a cover letter went, so the claim log page links exactly what was sent.
- The version and build date sit at the bottom right of the dashboard and the claim log page.
- The GitHub reminder recipe runs 0.2.0.

### Fixed

- Turning on claims tracking for a tracker that already had rows gave every row in Submitted and in Conversations and referrals a stray empty cell, which showed up as a `\|` at the end of the row. The Claim log cell now goes in cleanly.

## [0.1.0] - 2026-11-04

Private preview.

### Added

- Claude Code plugin with five skills: setup, tailor, log-activity, job-status, and watch. Each works from plain words, or as `/perkins:<skill>`.
- Two modes: Search, and Search with tracking for Unemployment Claims. Washington is the first supported state.
- Tailoring that builds every resume only from facts in your master resume, names the gaps, and grows the master as you review.
- Posting fetch for Workday, Greenhouse, Ashby, iCIMS, and any page with embedded JobPosting data.
- Tracker and dashboard: count cards, a due-soon list, every table, and, with claims tracking, the claim week.
- The claims clerk: weekly log files with the state's fields, a midweek check, a claim-day reminder, and filing stamps.
- Job board scanning for employers you watch: Greenhouse, Ashby, Lever, Workable, BambooHR, Rippling, and Workday.
- PDF rendering through Edge, Chrome, or Chromium on Windows, macOS, and Linux.
- Optional Claude Docs copy, checked against the Markdown files.
- Reminder recipes for Claude Code and GitHub, off until you set them up.
- A privacy check to run before sharing any folder.
- A `doctor` command; setup checks the computer first. Each skill pre-approves only the commands it uses.

### Fixed

Found by a six-persona review panel (security, performance, fresh eyes, edge cases, UX, and accessibility) before the preview:

- Settings are read strictly: a file that doesn't parse is never replaced, `"false"` is an error rather than true, a regex whose backslashes TOML ate is caught by name, and claim dates and time zones are checked.
- Claims: setup partway through a claim opens the earlier weeks; the last claim reminder survives the claim's end until it's filed; a new claim clears an old end date; entries are checked against the claim's exact dates.
- The tracker keeps every cell of a ragged row, survives Unicode line separators, refuses duplicate tables, keeps CRLF files CRLF, and prefers exact matches.
- Posting HTML is parsed in one linear pass, so hostile pages can't stall it.
- The dashboard labels overdue and soon dates in text, has keyboard-scrollable named tables, explains the claim panel, and lists ready resumes and unreadable dates under "Needs you".

### Security

- The log and the tracker refuse Social Security-shaped numbers, claimant IDs, and passwords, and a line break can't forge a heading in a log.
- Fetches go only to public addresses, even through redirects. PDFs print raw HTML as text on a page that can load nothing.
- The privacy check fails closed, reads UTF-16, masks what it prints, looks for keys and tokens, and checks history line by line under each file's own rules.

[Unreleased]: https://github.com/ReboundMan/Perkins/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ReboundMan/Perkins/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ReboundMan/Perkins/releases/tag/v0.1.0
