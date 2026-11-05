# The two modes

One setting, `mode` in `perkins.toml`. Setup asks one question to choose it: "Are you also tracking work search for an unemployment claim?"

## Search (default)

`mode = "search"`. Tailoring, the tracker, the dashboard, the watch list, and job board scanning. Nothing about claims: no state file, no week files, no claim reminders, no Claim log column.

If you set a `weekly_target`, status and the dashboard show how many applications you've sent this week against it.

## Search with tracking for Unemployment Claims

`mode = "search-claims"`, with your state and claim dates under `[claims]`. Everything in Search, plus:

- a work-search log in `log/`, one file per claim week, with your state's required fields, each entry graded solid or check
- `log/evidence/` for confirmation screenshots
- a midweek check and a claim-day reminder in `nudges.md`
- the claim week on the dashboard: this week's count against the minimum, and whether last week's claim is filed
- a Claim log column on Submitted and Conversations and referrals, pointing at each entry
- `weekly_target` never below the state minimum, and `hold_extras` to suggest holding extra applications for a later week

Washington is the supported state today. See [state rules](state-rules.md).

## Switching

**When a claim starts:** say "I filed for unemployment" (or run setup again and answer yes). Perkins adds the log folder, the reminders file, and an empty Claim log column. It never edits a row you already have. It can then go through applications and conversations dated inside your claim weeks with you, and log each one only if you say yes.

**When a claim ends:** say "my claim ended" or "I got a job". Perkins sets the end date, keeps last week's claim reminder until you tick it, and then stops opening weeks and adding reminders. Your log is never deleted, moved, or edited. Status reminds you where it is and how long your state asks you to keep it.
