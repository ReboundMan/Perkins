---
name: job-status
description: Report where the user's job search stands and what's due. Use when the user asks "where does my search stand?", "what's due?", "how many applications this week?", "did I file my claim?", "show my dashboard", "I filed my claim", or /perkins:job-status.
allowed-tools: Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" status), Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" status *), Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" due), Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" due *), Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" dashboard), Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" dashboard *), Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" clerk), Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" clerk *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" status), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" status *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" due), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" due *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" dashboard), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" dashboard *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" clerk), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" clerk *)
---

# Job status

Every command is `python "${CLAUDE_PLUGIN_ROOT}/run.py" ...` (`python3` on macOS or Linux if `python` isn't found).

1. Run `run.py status`. It runs the claims clerk first when claims tracking is on, rebuilds the dashboard, and prints the summary.
2. Give the user the short version. Lead with what needs them: anything overdue, an unfiled claim, a week short of the minimum late in the week. Then the counts. Skip sections that are empty.
3. Offer the next useful step, one at a time: submit a resume that's ready, follow up on something overdue, read new leads, or log a stray activity.

## Common requests

- **"Show my dashboard":** `run.py dashboard --open` opens `dashboard.html` in their browser.
- **"I filed my claim"** (claims tracking): ask which week if it's unclear (usually the week that just ended), then `run.py clerk filed --week <week's last day> [--on <date filed>]`. Confirm in one line.
- **"What's due?":** `run.py due` (add `--days 14` to look further ahead).
- **A week that's short, late in the week:** say the count plainly and what kinds of activity count in their state (from the state file). Never suggest logging anything that didn't happen. If the week will close short, the honest move is to tell the state agency, not to stretch the log.

Never store a Social Security number, claimant ID, state benefits login, date of birth, or bank details.
