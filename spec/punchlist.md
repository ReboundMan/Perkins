# Perkins: Punchlist

> Quick capture of features, ideas, and fixes. Newest items go at the top of each section.

## 🔥 Now (In Progress)

<!-- items currently being worked on -->

## 📋 Next (Up Soon)

- Confirm plain-language requests load the right skill with the plugin installed ("tailor my resume for <link>", "I submitted the <company> application", "where does my search stand?", "set up Perkins").
- Confirm a skill's `allowed-tools` pre-approves `python "${CLAUDE_PLUGIN_ROOT}/run.py" ...` on each platform.
- Confirm the marketplace and plugin manifests can share `.claude-plugin/` for installs from this repository.

## 💡 Ideas / Backlog

- (M) Close out an item on the due list (`due`, the dashboard's due panel, and the skills behind them) in plain words. Three actions: **done**, with an optional note on what happened; **won't do**, with an optional reason; and **new date**, to move it. Done and won't do clear the item's Next follow-up or Next check date and add a dated line to its notes (for example "2026-11-05 done: careers site still says Applied"); a new date changes only the date. Examples: "Larkspur follow-up done, still says Applied", "not going to chase the Kestrel nudge", "move Alder Robotics to 11-12". Open: whether done should offer a next follow-up date, and whether finishing a watch-list check sets Last checked and rolls Next check forward. (Maintainer ask, 2026-11-05; don't build yet.)
- (S) Dashboard on a phone: show Company, Role, and Next follow-up first, or stack rows as cards (Lens, 0.1.0 review).
- (S) Dashboard sizes in rem rather than px, and row headers on the Company column (Beacon, 0.1.0 review).
- (S) Parse each week file once per command instead of several times (Bolt, 0.1.0 review; about 0.3 s at a year of weeks).
- (S) Prune baseline.json of postings that have left a board; give each fetch a total deadline, not just a per-read timeout (Bolt).
- (S) A dated tick on a claim line could carry the tick's own date when the editor adds one (Chaos).

- A second state's rules file, researched from that agency's own pages with sources.
- Cover letter variants in the tailoring model.

## 🐛 Bugs

<!-- known issues -->

## ✅ Done

- 0.1.0: first version (see CHANGELOG.md).
- Turning on claims tracking no longer damages a tracker that already has rows: the Claim log cell is inserted at each row's old width (2026-11-05).
