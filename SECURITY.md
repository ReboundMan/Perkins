# Security and privacy

Perkins handles a job seeker's resume, applications, and, with claims tracking, an unemployment work-search log. These are the rules it is built around, and what to expect from it.

## What Perkins never does

- **Never applies for you.** You review every resume and submit it yourself. Nothing is recorded as an application until you say you sent it.
- **Never signs in to anything.** If a posting is behind a login, Perkins asks you to paste the text. The job board scanner reads only public, unauthenticated feeds, with a 15-second timeout, an honest user agent, and no retry loops.
- **Never stores your Social Security number, claimant ID, state benefits login, date of birth, or bank details.** The log writer refuses a value shaped like a Social Security number, and the skills refuse the rest even if you offer them.
- **Never guesses a field.** A missing detail is asked for, or left visibly blank. A false entry in a state work-search log can be fraud.
- **Never follows instructions hidden in a job posting.** Postings sometimes carry text aimed at AI screeners. Perkins treats posting text as data, tells you what it found, and does not act on it. The same goes for forwarded emails and pasted messages.

## Where your information lives

- In one data folder you choose (default `~/job-search`), outside the plugin, so plugin updates never touch it. Keep it private. Never put it in a public repository.
- Claude reads it in your own Claude Code session.
- If you turn on the Claude Docs copy, your master resume and tailored resumes also live in your Claude Docs account.
- Evidence screenshots often show names, email addresses, and application IDs. They stay in your data folder's `log/evidence/`.

## Before you share a folder

Run the privacy check on it:

```
python run.py pii-check <folder>
```

It looks for email addresses, phone numbers, Social Security-shaped numbers, home-folder paths, Claude artifact links, and real job posting links. Add `--blocklist <file>` with a private list of exact strings that must never appear (your name, your employers), and `--history` to check every commit in a git repository too.

## State rules are not legal advice

Each state's rules file summarizes that agency's own pages, with the source links and the date they were last checked. The agency's site is the authority. If a week comes up short, tell the agency. Never add an activity that didn't happen.

## Reporting a problem

Open an issue on the repository, without personal details in it. For anything sensitive, use GitHub's private vulnerability reporting on the repository's Security tab.
