---
name: setup
description: Set up Perkins, or change how it's set up. Use when the user says "set up Perkins", "get started with Perkins", runs /perkins:setup, wants to turn unemployment claims tracking on or off ("I filed for unemployment", "my claim ended", "I got a job"), wants to move their data folder, or wants to turn the Claude Docs copy on or off.
allowed-tools: Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" *)
---

# Perkins setup

Perkins keeps everything in one data folder the user owns, outside the plugin, so plugin updates never touch it. Setup creates that folder, or extends it. It only ever adds: it never overwrites a file the user has, and never edits a row already in their tracker.

Every command below is `python "${CLAUDE_PLUGIN_ROOT}/run.py" ...`. On macOS or Linux, use `python3` if `python` isn't found. If Python is missing or older than 3.11, stop and say so: Perkins needs Python 3.11 or later, plus `pip install markdown` (and `pip install tzdata` on Windows).

## First-time setup

Ask these one at a time, in plain words. Offer the default each time.

1. **Where to keep your data.** Default: `~/job-search`. It should be a private folder. Never suggest a folder inside a public repository.
2. **"Are you also tracking work search for an unemployment claim?"** Default: no.
   - **No:** the mode is **Search** (`--mode search`).
   - **Yes:** the mode is **Search with tracking for Unemployment Claims** (`--mode search-claims`). Run `run.py states` and ask which state. If theirs isn't listed, say plainly that claims tracking supports only the listed states today, and offer Search instead. Never guess another state's rules. Then ask the first day of the claim (`--claim-start`, default today).
3. **Time zone.** Default: this computer's local time. Only ask if they mention travel or a different zone.

Then run:

```
python "${CLAUDE_PLUGIN_ROOT}/run.py" --data "<folder>" init --mode <search|search-claims> [--state wa --claim-start YYYY-MM-DD] [--timezone Area/City]
```

It prints JSON listing what it created and a `settings_snippet`. Then:

- **Let Claude Code read the folder without asking each time.** Show the user the snippet and explain that it goes under `permissions.additionalDirectories` in their Claude Code user settings (`~/.claude/settings.json`). A plugin can't grant this itself. Offer to add it for them, and only edit their settings file if they say yes. Merge the entry into any existing `permissions` block; never replace the file.
- **Start the master resume.** Ask whether they have a current resume (a file path, or pasted text). If they do, write it into `master.md` in the data folder, keeping every fact exactly as they gave it. Say it doesn't need to be complete: it grows as they review tailored versions.
- **The tailoring model.** `tailoring-model.md` starts with five example role types. Offer to rename the columns to the roles they target and draft the cells from their master. Use only facts from the master, and have them review it.
- **Optional: Claude Docs copy.** Mention it only if they use Claude Docs. If they want it, set `docs_mirror = true` and `docs_id` in `perkins.toml` (see the plugin's `docs/claude-docs.md`).

Finish with how to use it, in two lines: "Ask me to tailor your resume for a posting link. When you've applied, tell me and I'll record it." If claims tracking is on, add: "I'll keep your weekly work-search log and remind you to file your claim."

## Changing modes

- **Claims tracking on** ("I filed for unemployment"): run init again on the same folder with `--mode search-claims --state <code> --claim-start <date>`. It adds the log folder, the reminders file, and an empty Claim log column. Then run `run.py status` to see the first claim week. Offer to look back over Submitted and Conversations rows dated inside claim weeks as possible log entries. Write each one only on the user's yes, field by field, through the log-activity rules. Nothing dated before the first claim week goes into a log.
- **Claim ended** ("I got a job", "my benefits ended"): run init with `--mode search --claim-end <date>`. The last week's claim reminder stays until they tick it. The log is never deleted, moved, or edited. Tell them how long their state asks them to keep it (`run.py status` prints it).

## Rules

- Never store a Social Security number, claimant ID, state benefits login, date of birth, or bank details anywhere, even if the user offers one.
- Never sign in to anything on the user's behalf.
- Don't commit or push the data folder unless the user turned `[git] commit` on in `perkins.toml`.
