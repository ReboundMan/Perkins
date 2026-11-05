# Perkins

**Tailored resumes. Every application, tracked. A work-search log that holds up.**

Perkins is a Claude Code plugin for people looking for work. It tailors your resume to each posting using only facts you can back, keeps every application and follow-up on one dashboard, and, if you're on an unemployment claim, keeps the weekly work-search log your state asks for.

> Private preview. The getting-started page is [docs/index.html](docs/index.html).

## Install

You need Python 3.11 or later, Claude Code, and Edge, Chrome, or Chromium for PDFs. On macOS and Linux the Python command is usually `python3`. Not sure? Setup runs a check (`python run.py doctor`) and says what's missing.

```
pip install markdown
pip install tzdata        # Windows only
```

Then, inside Claude Code:

```
/plugin marketplace add ReboundMan/Perkins
/plugin install perkins@perkins
```

## Get started

1. **Set up:** say "set up Perkins" (or run `/perkins:setup`). It asks where to keep your data (default `~/job-search`) and one question: are you also tracking work search for an unemployment claim?
2. **Start your master resume** from the resume you already have. It doesn't need to be complete: it grows as you review tailored versions and add facts.
3. **Tailor:** "Tailor my resume for https://..." Review the draft and the gaps it names, and ask for edits. New facts go into your master too.
4. **Apply yourself,** then say "I submitted the Larkspur application" so Perkins records it.
5. **Day to day:** "Where does my search stand?" Open `dashboard.html` in your data folder to see everything on one page.

The [setup guide](docs/setup.md) has the details.

## What it does

| | |
|---|---|
| **Tailor** | Reorders and rewords your master resume around what a posting asks for first. Every number, date, and title traces to your master; anything you can't back is named as a gap. Two-page PDFs on Windows, macOS, or Linux. |
| **Get the posting** | Reads Workday, Greenhouse, Ashby, and iCIMS postings through their public data, and any page with embedded JobPosting data. Never signs in. |
| **Track** | One Markdown tracker (Submitted, Conversations and referrals, Considering, Passed, Employers to watch) and a dashboard rebuilt after every change, with follow-ups due in amber and overdue in red. |
| **Employers to watch** | A short list of employers to check every two weeks, with application limits noted. A scan of their public boards (Greenhouse, Ashby, Lever, Workable, BambooHR, Rippling, Workday) adds new senior postings as leads. |
| **Claims tracking** (optional) | One log file per claim week with your state's required fields, each entry graded solid or check; a midweek check, a claim-day reminder, and the claim week on the dashboard. Washington today. |
| **Claim log page** (with claims tracking) | Your work-search log week by week, ready for a meeting with the state: each week collapsed with its count and filing date, each activity with its posting, the resume and cover letter you sent, and your confirmation screenshots. Opens in a clean meeting view; your own prep notes are one click away. |
| **Your files** | Plain Markdown in a folder you choose. An optional Claude Docs copy is checked against the Markdown and stops if they ever differ. |

## The two modes

- **Search** (default): tailoring, the tracker, the dashboard, the watch list, and scanning.
- **Search with tracking for Unemployment Claims:** all of that, plus the weekly work-search log your state asks for. Turn it on when a claim starts and off when it ends; the log is kept either way. See [modes](docs/modes.md) and [state rules](docs/state-rules.md).

## What Perkins never does

It never applies for you, never signs in to anything, never stores your Social Security number, claimant ID, or benefits login, never logs an application you haven't confirmed sending, and never guesses a field. See [SECURITY.md](SECURITY.md).

## Commands

You rarely need these: plain requests work. Each skill also runs as a command.

| Command | Plain words |
|---|---|
| `/perkins:setup` | "set up Perkins", "I filed for unemployment", "my claim ended" |
| `/perkins:tailor <link>` | "tailor my resume for <link>", "I submitted the <company> application" |
| `/perkins:log-activity` | "log my interview with <company> today" |
| `/perkins:job-status` | "where does my search stand?", "I filed my claim", "show my claim log" |
| `/perkins:watch` | "watch <company>", "check my watch list for new jobs" |

Under the skills, everything runs through `python run.py <command>` (`init`, `doctor`, `states`, `status`, `due`, `dashboard`, `claim-log`, `tracker`, `clerk`, `pdf`, `posting`, `scan`, `sync-check`, `pii-check`). Run `python run.py -h` for the list.

## More

[Setup](docs/setup.md) · [How it works](docs/how-it-works.md) · [Modes](docs/modes.md) · [State rules](docs/state-rules.md) · [Scanning job boards](docs/scanning.md) · [Reminders](docs/reminders.md) · [Claude Docs copy](docs/claude-docs.md) · [Security](SECURITY.md) · [Changelog](CHANGELOG.md)

## Thanks

If you like it, or it helps you, let me know! If you want to buy me a frosty beverage as a thank you, that's great.

## Why "Perkins"

Named for Frances Perkins, US Secretary of Labor from 1933 to 1945 and the first woman in a US cabinet. The US Employment Service was built on her watch, and she led the committee behind the Social Security Act of 1935, which created state unemployment insurance. Finding work, and the support that bridges the gap: the same two jobs this plugin does.

## License

MIT. Not legal advice: your state agency's site is the authority on its rules.
