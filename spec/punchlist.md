# Perkins: Punchlist

> Quick capture of features, ideas, and fixes. Newest items go at the top of each section.

## 🔥 Now (In Progress)

<!-- items currently being worked on -->

## 📋 Next (Up Soon)

- Confirm plain-language requests load the right skill with the plugin installed ("tailor my resume for <link>", "I submitted the <company> application", "where does my search stand?", "set up Perkins").
- Confirm a skill's `allowed-tools` pre-approves `python "${CLAUDE_PLUGIN_ROOT}/run.py" ...` on each platform.
- Confirm the marketplace and plugin manifests can share `.claude-plugin/` for installs from this repository.

## 💡 Ideas / Backlog

- (S) Washington's late-filing rule: research ESD's deadline for filing a weekly claim from ESD's own pages, with sources, so `states/wa.toml` can set `claim_late_days` and Washington's claim reminder shows a file-by date the way Virginia's does (spec 10243). Leave it out if ESD doesn't publish one. (Maintainer, 2026-11-06; don't build until 10243 has merged.)
- (M) Close out an item on the due list (`due`, the dashboard's due panel, and the skills behind them) in plain words. Three actions: **done**, with an optional note on what happened; **won't do**, with an optional reason; and **new date**, to move it. Done and won't do clear the item's Next follow-up or Next check date and add a dated line to its notes (for example "2026-11-05 done: careers site still says Applied"); a new date changes only the date. Examples: "Larkspur follow-up done, still says Applied", "not going to chase the Kestrel nudge", "move Alder Robotics to 11-12". Open: whether done should offer a next follow-up date, and whether finishing a watch-list check sets Last checked and rolls Next check forward. (Maintainer ask, 2026-11-05; don't build yet.)
- (S) Dashboard on a phone: show Company, Role, and Next follow-up first, or stack rows as cards (Lens, 0.1.0 review).
- (S) Dashboard sizes in rem rather than px, and row headers on the Company column (Beacon, 0.1.0 review).
- (S) Parse each week file once per command instead of several times (Bolt, 0.1.0 review; about 0.3 s at a year of weeks).
- (S) Prune baseline.json of postings that have left a board; give each fetch a total deadline, not just a per-read timeout (Bolt).
- (S) A dated tick on a claim line could carry the tick's own date when the editor adds one (Chaos).

- Cover letter variants in the tailoring model.

## 🐛 Bugs

<!-- known issues -->

## ✅ Done

- 1.0.0: the public release: no private-preview wording, an install step that links updating, the latest release, and the source, a README website line, GitHub Releases, and `spec/card.json` (2026-11-09; see CHANGELOG.md).
- 0.3.3: an activity from earlier in the week the claim was filed is logged in the first claim week, instead of refused; a claim week is the whole week at both ends (2026-11-06; see CHANGELOG.md).
- 0.3.2: one header and footer across the website, with a Setup guide link and a Guides menu, and the setup guide in numbered steps (2026-11-06; see CHANGELOG.md).
- 0.3.1: bugs, ideas, state requests, and security reports go to the website's Feedback button instead of GitHub; the manifest's homepage is the site (2026-11-06; see CHANGELOG.md).
- 0.3.0: Virginia, the potentially counts grade, and the guidance-only headline (2026-11-06; see CHANGELOG.md).
- Virginia as the second state, with the guidance-only headline, a yellow "potentially counts" grade, same-employer grading, one-time reminders, a file-by date, and per-claim requirement adjustments (specs 10242, 10241, 10243, 10244; PRs #1 to #4, merged 2026-11-06; released in 0.3.0).
- 0.1.0: first version (see CHANGELOG.md).
- Turning on claims tracking no longer damages a tracker that already has rows: the Claim log cell is inserted at each row's old width (2026-11-05).
- 0.2.0: the claim log page, the tab icon, the tip line, and that fix, ready for beta testers (2026-11-05; see CHANGELOG.md).
