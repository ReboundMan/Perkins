# Scanning the watch list

Perkins can check the employers you watch for new senior postings and put them in front of you as leads. It reads each employer's public job board, keeps the titles that fit your filters, skips anything it has already shown you, and adds the rest to the top of Considering.

Run it from the plugin:

```
python run.py scan              # scan and add leads
python run.py scan --dry-run    # show what would be added; write nothing
python run.py scan --baseline-only
python run.py scan --json
```

## The watch list

The scan reads the **Employers to watch** table in `tracker.md`. Two columns drive it.

**Board** names the applicant tracking system the employer uses. The scan understands Greenhouse, Ashby, Lever, Workable, BambooHR, Rippling, and Workday. Anything else (for example "Careers site" or "No public board") is a check by hand.

**Where to look** is the board's URL. It can be bare or a Markdown link like `[jobs](https://jobs.lever.co/kestrelenergy)`. The scan takes the board name (the slug) from it:

| Board | URL shape | Slug taken |
|---|---|---|
| Greenhouse | `job-boards.greenhouse.io/<slug>` or `boards.greenhouse.io/<slug>` | `<slug>` |
| Ashby | `jobs.ashbyhq.com/<slug>` | `<slug>` |
| Lever | `jobs.lever.co/<slug>` | `<slug>` |
| Workable | `apply.workable.com/<slug>` | `<slug>` |
| BambooHR | `<sub>.bamboohr.com/careers` | `<sub>` |
| Rippling | `ats.rippling.com/<slug>/jobs` | `<slug>` |
| Workday | `<tenant>.wd<N>.myworkdayjobs.com/[en-US/]<site>` | `<tenant>.wd<N>/<site>` |

If the URL is the employer's own careers page, name the slug in the Board cell instead: `Greenhouse (larkspuranalytics)` or `Workday (pinecresthealth.wd1/External)`. A named slug always wins over the URL.

Every row with a feed is scanned on every run, whatever its Next check date says. After a successful scan the row's **Last checked** becomes today and **Next check** moves out by the interval (14 days unless you change it).

## Filters

Titles have to pass three filters, set under `[scan]` in `perkins.toml`. Each is a list of regular expressions, matched without regard to case.

- `seniority`: a title must match at least one. The default matches VP, SVP, EVP, Vice President, Head of, Chief, C-suite titles (CEO, CFO, CTO, COO, CIO, CMO, CPO, CRO, CISO, CHRO and similar), President, General Manager, Director, and Principal.
- `functions`: if set, a title must also match at least one. Empty (the default) means any function.
- `exclude`: a title that matches any of these is dropped.

An empty list means "no limit" for that filter. Use single-quoted strings in TOML so backslashes survive. In double quotes TOML reads `\b` as a backspace character; Perkins refuses a setting that holds one and says which key, so double every backslash there (`"\\bVP\\b"`) or switch to single quotes:

```toml
[scan]
interval_days = 14
seniority = ['\bVP\b', 'Vice President', 'Head of', '\bDirector\b']
functions = ['operations', '\bdata\b']
exclude = ['\bIntern', 'Assistant']
```

A pattern that is not a valid regular expression stops the scan with a message naming it.

## Baselines and the first scan

`baseline.json` in your data folder remembers, per company, every posting the scan has seen (by the board's job id, or the posting URL when there is no id). Only postings not in the baseline can become leads. Every posting is remembered, not just the ones that passed the filters, so loosening a filter later will not flood you with old postings.

The first time an employer is scanned it has no baseline. The scan records one and still adds that employer's current matches as leads, so you see what is open today. If you would rather start quiet, run `scan --baseline-only` once: it records what each board lists now and adds no leads.

To start an employer over, delete its entry from `baseline.json`. You can also add a posting URL to an employer's list by hand to keep it from ever showing up.

## What a lead looks like

Before adding a lead, the scan looks for its URL anywhere in Considering, Submitted, and Passed (ignoring a trailing slash and tracking parameters), so a posting you already have, applied to, or passed on is skipped.

Each new lead goes to the top of Considering:

| Found | Company | Role | Where | Base pay | Resume | Status | Next step |
|---|---|---|---|---|---|---|---|
| 2027-03-11 | Larkspur Analytics | [VP, Data Platform](https://jobs.example.com/larkspur/vp-data-platform) | Remote, United States | not checked | Not built | Lead | Found in the 2027-03-11 watch-list scan; read the posting |

## What "check by hand" means

The report ends with a list of employers the scan could not check for you. There are three reasons.

- **No feed.** The Board column is not one of the seven supported boards. These are listed only when the row's Next check is today, past, or empty. Open the careers page yourself, then update Last checked and Next check.
- **No slug.** The board is supported but the slug could not be found in Where to look. Fix the URL, or write the Board cell as `Greenhouse (slug)`.
- **The feed failed.** The board did not answer, answered with an error, or sent something unreadable. The scan never retries, never signs in, and never tries to get past a bot check. Open the board in your browser. If it keeps failing, the employer may have moved boards.

Rows that failed keep their old Last checked and Next check dates, so the next scan tries them again.

## Finding boards for a list of companies

`scan --discover FILE` reads company names, one per line (blank lines and lines starting with `#` are skipped). For each name it guesses slugs (lowercase, joined and hyphenated, then with endings like Inc, Labs, and AI trimmed) and tries them on Greenhouse, Ashby, and Lever. It reports the board each name resolved to and the senior titles listed there.

A guess can land on a different company with the same name, so check the result before you trust it. A board that exists but lists nothing is reported with a note. Add `--add` to append every company it found to the watch table (companies already there are skipped). Each added row gets today as its Next check.

## Reading one posting

`python run.py posting URL` prints a posting's title line and full text. `--json` prints every field: title, company, location, req_id, description, source, url, and notes (base pay and posting date, when the page gives them).

It picks a route by the URL:

- **Workday** job pages are read through the site's own JSON (`/wday/cxs/<tenant>/...`).
- **Greenhouse** job pages are read through the public job API. A company careers URL carrying `gh_jid=<id>` works too, when the page names its Greenhouse board.
- **Ashby** job pages are read from the page's JSON-LD (the whole-board API is far too large for one posting).
- **iCIMS** job pages are read from the page's iframe view, falling back to its JSON-LD when the text is thin.
- **Anything else** is read from the page's JSON-LD `JobPosting`, which most career sites include.

When none of that yields a description, the command says so. Open the page in your browser and copy the text, or paste the posting into the conversation.

## How the requests behave

Every request (scans and posting fetches alike) is a plain HTTPS call with the User-Agent `Perkins (+https://github.com/ReboundMan/Perkins)`, a 15-second timeout, and a 25 MB cap on the reply. No cookies, no browser impersonation, no retries. Requests go only to public addresses: a link that points at this computer or the local network, directly or through a redirect, is refused. Up to six boards are read at once. With `--json`, each employer's `skipped_by_filters` counts the postings your filters passed over.

## What is confirmed and what is not

The board list responses for Greenhouse, Ashby, Lever, Workable, Rippling (first page), and Workday (first page) were checked against live public boards in November 2026. The rest is read defensively, and may need adjusting when a provider changes things:

- **BambooHR** `careers/list` is the JSON the careers page loads, not a documented API. Its shape was not confirmed live. The adapter expects `result` entries with `id`, `jobOpeningName`, and `location` or `atsLocation`, and it gives no posting date.
- **Rippling** pages its replies. Later pages are requested with `?page=N`, which was not confirmed live; the adapter stops as soon as a page brings nothing new, and reads at most 10 pages.
- **Workday** reads at most 200 postings per employer (10 pages of 20), and turns "Posted 3 Days Ago" into a date. "Posted 30+ Days Ago" has no date. Workday sites on a custom domain are not scanned; list them as a check by hand.
- **Single-posting endpoints** (the Workday job JSON, the Greenhouse single-job API, the iCIMS iframe page) follow their known public shapes but were not called live while this was written. If one fails, `posting` falls back to the page's JSON-LD.
- European Greenhouse and Lever hosts are not scanned yet.
