# How it works

## Tailoring

You give Perkins a posting: a link, pasted text, or a referrer's notes when there's no posting yet.

1. **It gets the full posting.** For a link it reads the posting's public data (Workday, Greenhouse, Ashby, iCIMS, or any page with embedded JobPosting data). If that fails and your Claude Code session has a browser tool, Claude reads the page there; if that fails too, it asks you to paste. It never signs in, and it only fetches public addresses.
2. **It picks a variant** from your tailoring model: the role type that fits the title and the top three requirements, and the gap that role type usually has to answer.
3. **It drafts from your master resume only.** Same facts, new emphasis: the variant's headline and summary opening, the sections reordered, the posting's own phrases mirrored where they're true, and one new bullet aimed at the top requirement.
4. **It checks every fact.** Each number, date, and title in the draft must be in your master. Anything that isn't comes out.
5. **It saves and renders** the resume as Markdown and a PDF in `applications/`, checks the page count, and adds the posting to Considering in your tracker.
6. **It tells you the gaps:** requirements you can't fully back, each with the honest answer your master supports.

### Review, and the master grows

You review the draft and ask for changes in plain words. Wording and emphasis change only that resume. A new or corrected fact ("the team was 40 people, not 35", "add the vendor consolidation") goes into your master resume first, once you confirm it's true in general and not just framing for this job. So the next resume starts from a better record, and the fact check still holds.

## Recording an application

When you say you submitted it, Perkins confirms the date and how you applied, moves the row from Considering to Submitted, and sets a suggested follow-up date two weeks out. With claims tracking on, it also writes the activity into that week's log with every field your state requires, and notes where it went.

It never records an application you haven't confirmed, and never applies for you.

## Logging other activities

"Log my interview with Kestrel today", "a recruiter called about a role", "I went to a job center workshop": Perkins adds a row to Conversations and referrals, and with claims tracking writes the log entry for the day it happened. If a required field is missing, it asks. It never fills one in with a guess.

## The dashboard

`dashboard.html` is rebuilt from `tracker.md` (and, with claims tracking, the week files) after every change:

- with claims tracking, the claim panel: this week's solid entries against your state's minimum, and whether last week's claim is filed
- count cards: submitted, conversations, considering, resumes ready, employers watched
- a "needs you" list: an unfiled claim first, then resumes ready to submit, then follow-ups and employer checks due within a week or overdue, then any date Perkins couldn't read
- every tracker table, overdue dates in red and upcoming ones in amber

## The claims clerk

With claims tracking on, a small script keeps the weekly rhythm. It runs whenever a skill does, so there's nothing to schedule:

- It opens each claim week's log file with open slots for the required activities. Set up partway through a claim, it opens the earlier claim weeks too, so past activities have somewhere to go (mark those weeks' claims filed with "I filed my claim for the week ending ...").
- It recounts every week: solid, check, and blank fields.
- Midweek, it adds a "work search check" line to `nudges.md` with the count, and raises it late in the week if you're short. Once the week reaches the minimum, it ticks that line itself.
- On claim day, it adds "file the weekly claim" for the week that just ended. Tick it, or say "I filed my claim", and it stamps the date on that week's log.

Each entry is graded **solid** only when the activity is on your state's list, every required field is filled, and it rests on your own words. Otherwise it's **check**, with a reason. Only you write **no**.
