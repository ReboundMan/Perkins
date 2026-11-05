# Perkins reminder (a prompt for a scheduled Claude Code task)

Copy everything below the line into a scheduled task. Replace `<path to run.py>` with the plugin's `run.py` (find it with `/plugin`, or use your clone), and choose the day and time in the scheduler.

---

Remind me what's due in my job search. This is a reminder only: do not apply to anything, sign in anywhere, fill in any form, or log any activity on my behalf.

1. Run `python "<path to run.py>" due --days 7`. If it fails, tell me the error in one line and stop.
2. If nothing is due, reply "Nothing due in the next 7 days." and stop.
3. Otherwise reply with a short list: overdue items first, then the rest by date. One line each: the date, the company and role, and what to do.
4. If an unfiled claim is on the list, put it first and say which week it's for.
5. Send the same list as a push notification if a notification tool is available.

Keep it plain and short. Never write a Social Security number, claimant ID, or benefits login anywhere.
