# Changelog

All notable changes to Perkins are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and Perkins adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.3] - 2026-11-06

An activity from earlier in the week you filed your claim is logged in your first claim week.

### Fixed

- An activity earlier in the week you filed your claim is logged in your first claim week. It used to be refused when the claim start was set to the filing day, even though Perkins opens that whole week and asks for its activities. A claim week is the whole week at both ends: an activity later in the week the claim ended is logged too, and one in a week outside the claim is still refused.
- The GitHub reminder recipe runs 0.3.3.

## [0.3.2] - 2026-11-06

One header and one footer across the website, and a setup guide in numbered steps.

### Changed

- The getting-started page's header has a Setup guide link and a Guides menu listing every guide. Its header and footer styles are marked `site:chrome`, so the website puts the same header and footer on every guide page instead of a separate guide bar.
- The setup guide's four steps are numbered in their headings (Step 1: What you need, through Step 4: Run setup). On the website they also get a list of the page's sections, beside the guide on wide screens.
- The GitHub reminder recipe runs 0.3.2.

## [0.3.1] - 2026-11-06

Bugs, ideas, and state requests go to the website's Feedback button instead of GitHub.

### Changed

- Bugs, ideas, state requests, and security problems go through the Feedback button on perkins.reboundman.com, which reaches Perkins's maker privately, instead of GitHub issues and pull requests. SECURITY.md, the state rules guide, the README, and the scanner's "please report it" message all say so. For a security problem, SECURITY.md asks for the form's optional email box, so the maker can reply privately.
- The plugin's homepage is perkins.reboundman.com. The repository link is unchanged.
- The GitHub reminder recipe runs 0.3.1.

## [0.3.0] - 2026-11-06

Virginia joins Washington for claims tracking, with a yellow "potentially counts" grade and a guidance-only headline for every state.

### Added

- Virginia, the second state for claims tracking (`states/va.toml`), researched from the Virginia Employment Commission's own pages, the Code of Virginia, and the Virginia Administrative Code: two work search activities a week, Sunday-to-Saturday weeks, the claim reminder on Sunday, and VEC's log fields in the order of the sample log in its Claimant Handbook. Workforce center activities are always potentially counts, because VEC's handbook counts them and its benefits roadmap asks for two different employers. The tailor and log-activity skills use each state's own field names.
- A yellow grade, **potentially counts**, for a complete log entry the state's rules don't clearly count (in Washington, say, a networking conversation that isn't clearly an approved activity). It's shown on the claim log page, the dashboard, `status`, and the reminders, and never counts toward the week's minimum. `clerk add --fit maybe` writes one with a reason, and a state file can mark a whole activity kind as potentially counts (`counts = "maybe"` with a `maybe_reason`).
- A guidance-only headline wherever Perkins shows a state's rules: the state's rules can change at any time, take precedence over anything Perkins says, shows, or counts, and are yours to know and meet. The full headline opens the state rules guide and `states/README.md`, sits in every state file's header, and is said once at setup; a one-line version is on the claim log page (prep notes), the dashboard's claim panel, and `status`.
- Three optional state-file rules, all set for Virginia and none for Washington. `distinct_employers`: a second contact with one employer in a week is potentially counts for a different opening, and check for the same one. `[[once]]`: a one-time reminder counted from the claim's first day (Virginia: register with the Virginia Workforce Connection within 10 days), shown on the due list until it's ticked. `claim_late_days`: the claim reminder shows a file-by date, and says plainly once it has passed.
- Per-claim requirement adjustments: when your agency changes your weekly requirement (approved training, a union hiring hall, a waiver), `clerk adjust` records it in `perkins.toml` with your dates and your reason. Those weeks count against the new number everywhere (the reminders, the dashboard, `status`, the due list, the claim log page), with the reason shown. A week with nothing required has no open slots and no midweek check, and still reminds you to file the weekly claim. Perkins records an adjustment only from what you say the agency told you.

### Changed

- The check grade is red-orange instead of amber, so yellow means only "potentially counts".
- The GitHub reminder recipe runs 0.3.0.

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

[Unreleased]: https://github.com/ReboundMan/Perkins/compare/v0.3.3...HEAD
[0.3.3]: https://github.com/ReboundMan/Perkins/compare/v0.3.2...v0.3.3
[0.3.2]: https://github.com/ReboundMan/Perkins/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/ReboundMan/Perkins/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/ReboundMan/Perkins/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/ReboundMan/Perkins/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ReboundMan/Perkins/releases/tag/v0.1.0
