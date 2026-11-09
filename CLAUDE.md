# Working on Perkins

Perkins is a Claude Code plugin: `skills/` holds the five skills, `perkins/` the Python they run (through `run.py`), `states/` each state's work-search rules, and `templates/` what setup copies into a user's data folder. `spec/SPEC.md` is the design; `spec/punchlist.md` is the to-do list.

## Rules for every change

- **Stdlib only** in `perkins/`, except the `markdown` package for PDFs (and `tzdata` on Windows). Python 3.11 or later.
- **Fictional data only.** Tests, fixtures, examples, and docs use made-up people and employers (Larkspur Analytics, Kestrel Energy, Alder Robotics, Bluewater Grid, Pinecrest Health) and `example.com` links. Never a real person, a real application, or a real posting.
- **Never store** a Social Security number, claimant ID, benefits login, date of birth, or bank details, in code, tests, or examples.
- **No em dashes** in any prose: use commas, colons, periods, or parentheses.
- **State rules come from the agency's own pages**, with sources and a last-checked date. Never guess a state's rules.
- **Run before every push:** `python -m pytest tests -q` and `python run.py pii-check . --history`.
- **Try a change without installing:** `claude --plugin-dir .` loads this checkout as the plugin for one session.
- **Versioning (house standards 10, 11, and 24).** `VERSION` is the one place the version is set, in plain semver. To release: change `VERSION`; match it in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, the `**Version:**` line of `spec/SPEC.md`, and `PERKINS_REF` in `reminders/github-actions-reminder.yml`; rename `## [Unreleased]` in `CHANGELOG.md` to `## [x.y.z] - YYYY-MM-DD` under a fresh empty `[Unreleased]`, and update the compare links at the bottom; then tag the commit `vX.Y.Z`. After the tag is pushed, publish it as a GitHub Release (`gh release create vX.Y.Z --title "Perkins X.Y.Z" --notes-file <that version's CHANGELOG section>`; GitHub attaches the source zip and tarball itself), and last, rebuild the website from the new tag. `tests/test_package.py` fails if any copy disagrees. Installed copies update only when the version changes, so a fix nobody gets until the next bump is not yet shipped.
- **Never point your real setup at test data:** `run.py init` repoints `~/.perkins` unless you pass `--no-pointer`. Tests already isolate it (`tests/conftest.py`).
