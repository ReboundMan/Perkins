# Reminders you set up yourself

Perkins's built-in reminder is the dashboard's due-soon list, and, with claims tracking, the claim and check lines in `nudges.md`. If you want a nudge to come to you instead, copy one of these recipes into place. Nothing here runs until you do.

Both recipes use the same list: `python run.py due` prints every follow-up and employer check that is due within seven days or already past, plus last week's claim if it isn't filed yet.

## Recipe 1: a Claude Code scheduled task

`claude-code-reminder.md` is a prompt for a scheduled task in the Claude desktop app, or anything else that can start Claude Code on a schedule. Create the task, paste the prompt in, set the day and time, and fill in the path to the plugin's `run.py`.

It is a reminder only. It never applies anywhere, signs in, fills in a form, or logs an activity.

For a one-time reminder ("apply to Larkspur on Thursday"), use the same prompt, add the task you want to be reminded of, and schedule it once.

## Recipe 2: a weekly GitHub issue

`github-actions-reminder.yml` is a GitHub Actions workflow for people who keep their data folder in their own **private** GitHub repository. Copy it to `.github/workflows/perkins-reminder.yml` in that repository. Every Monday it opens, or adds to, one issue titled "Due this week", assigned to you, so GitHub's own notifications deliver it.

It needs no secrets. It uses the built-in `GITHUB_TOKEN` with permission to write issues, and nothing else.

Two cautions:

- **Only in a private repository.** The issue names employers and dates.
- **It downloads Perkins at a pinned version** to run `due`. While the Perkins repository is private, that download needs a token, so this recipe works once Perkins is public. Until then, copy Perkins's `run.py`, `perkins/` folder, and `states/` folder into your data repository and change the workflow's two paths to point at them.
