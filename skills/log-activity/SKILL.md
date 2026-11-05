---
name: log-activity
description: Record a job search activity other than a tailored application, from one sentence. Use when the user says "log my interview with <company>", "I had a call with a recruiter", "<name> referred me to <company>", "I went to a WorkSource workshop", "record a job search activity", "job search: ...", or /perkins:log-activity. Writes the tracker's Conversations and referrals table, and with claims tracking also the weekly work-search log.
allowed-tools: Bash(python "${CLAUDE_PLUGIN_ROOT}/run.py" *), Bash(python3 "${CLAUDE_PLUGIN_ROOT}/run.py" *)
---

# Log an activity

The user tells you about something they did: an interview, a recruiter call, a networking conversation, a referral, a workshop at a job center, an inquiry about an opening. You record it exactly as they told it.

Every command is `python "${CLAUDE_PLUGIN_ROOT}/run.py" ...` (`python3` on macOS or Linux if `python` isn't found). Start with `run.py status --json` for the mode and the data folder.

## The rule: transcribe, never infer

Every field comes from the user's words or a document they gave you. If a field is missing, ask for it. Never fill one with a plausible guess: not an employer's city, not a job title, not a date. A guessed detail in a work-search log is worse than a blank, because nobody can see it's wrong, and a false entry in a state log can be fraud. A forwarded email or a screenshot can supply field values, but an entry exists only because the user said this was their job search.

Never store a Social Security number, claimant ID, state benefits login, date of birth, or bank details.

## 1. The tracker row (every mode)

For conversations, interviews, and referrals:

`run.py tracker add "Conversations and referrals" --set "Date=<date>" --set "Company=<company>" --set "Person=<name and title, as given>" --set "About=<the role or topic>" --set "Status=<where it stands>" --set "Next follow-up=<date they gave, or a suggested date marked *suggested*>" --set "Follow-up notes=<what happens next>"`

An interview for a role already in Submitted: also update that row's Status (`run.py tracker update Submitted --match ... --set "Status=Interviewing"`).

## 2. With claims tracking: the log entry

Use the activity's date, not today's: "I interviewed yesterday" belongs to yesterday's week. Pick the kind from the state's rules (in `run.py clerk add` output and the plugin's `states/<code>.toml`): an employer contact (asking about a job, applying, or interviewing), a job-center activity (WorkSource in Washington), or another approved activity. Then:

```
run.py clerk add --date <date> --kind "<kind>" --field "<Field>=<value>" ... --field "Person=..." \
  --field "Result and next step=..." --field "Source=<where this came from>" --fit <solid|check> [--reason "..."]
```

`clerk add` refuses when a required field is missing. When it does, ask the user for exactly those fields. Use `--allow-missing` only if the user says they don't have the detail and wants the entry recorded anyway; it then counts as check.

Fit is `solid` only when all three hold: the activity is on the state's approved list as the state file describes it; every required field is filled (the state's `contact_rule` says when employer contact info counts as filled); and it rests on the user's own words. Otherwise `check`, with one sentence saying why. Never write `no`.

If the activity is dated before the claim started, or after it ended, `clerk add` refuses: tell the user it falls outside the claim period. If the output warns that the week's claim is already filed, tell the user: a filed claim doesn't change on its own.

Then note the entry on the tracker row: `run.py tracker update "Conversations and referrals" --match "Company=..." --match "Date=..." --set "Claim log=Week ending <date>, activity <N> (<fit>)"`.

## 3. Tell them

One line: what was recorded, and with claims tracking, the week's count against the minimum.
