# Reminders

## Built in

- **The dashboard's due-soon list:** every follow-up and employer check due within a week or overdue, highlighted, with an unfiled claim on top.
- **With claims tracking, `nudges.md`:** a midweek work search check with the week's count (raised late in the week if you're short) and a claim-day reminder to file last week's claim. It works with any Markdown task list, including Obsidian's.
- **"What's due?"** or `/perkins:job-status` any time.

## Add your own

The `reminders/` folder has two recipes, both off until you copy them into place:

- **A scheduled Claude Code task:** a prompt that lists what's due and sends a push notification if it can. Reminder only: it never applies, signs in, fills in forms, or logs anything.
- **A weekly GitHub issue:** a workflow for your own **private** data repository that opens or updates one "Due this week" issue, so GitHub notifies you. It uses only the built-in token.

Both read the same list as the dashboard: `python run.py due`. See [reminders/README.md](../reminders/README.md) for the steps.
