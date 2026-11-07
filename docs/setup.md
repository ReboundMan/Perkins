# Setup

Four steps, about ten minutes. The two sections after them are for reference.

## Step 1: What you need

- **Claude Code**, on your own Claude plan.
- **Python 3.11 or later.** Check with `python --version` (`python3 --version` on macOS or Linux).
- **The markdown package:** `pip install markdown`. On Windows, also `pip install tzdata`, so time zones work.
- **A Chromium browser** for PDFs: Microsoft Edge, Google Chrome, or Chromium. Perkins looks in the usual places on Windows, macOS, and Linux. If yours is somewhere else, set `PERKINS_BROWSER` to its path.

## Step 2: Install the plugin

Inside Claude Code:

```
/plugin marketplace add ReboundMan/Perkins
/plugin install perkins@perkins
```

While Perkins is in private preview, installing works for people who've been given access to the repository, using their own git credentials (`gh auth login` and then `gh auth setup-git`, or an SSH key).

### Updates

Perkins pins a version, so updates arrive as deliberate releases. Third-party plugins don't update on their own by default. To update, open `/plugin`, choose Installed, and update Perkins, or run `claude plugin update perkins@perkins`. Then run `/reload-plugins`. Updates never touch your data folder.

## Step 3: Check the computer

`python run.py doctor` checks for Python 3.11 or later, the markdown package, a browser for PDFs, and (on Windows) time zone data, and says how to fix anything missing. Setup runs it first.

## Step 4: Run setup

Say "set up Perkins" (or run `/perkins:setup`). It asks:

1. **Where to keep your data.** Default `~/job-search`. Pick a private folder. Never put it inside a public repository.
2. **"Are you also tracking work search for an unemployment claim?"** No means Search. Yes means Search with tracking for Unemployment Claims, and it then asks for your state and the first day of your claim. See [modes](modes.md).

Setup writes a one-line pointer file, `~/.perkins`, so every skill finds your folder. To use a different folder for one session, set `PERKINS_HOME`. Running `init` yourself repoints `~/.perkins` at whatever `--data` folder you give it; add `--no-pointer` when you're only trying something out.

### Let Claude Code read the folder

A plugin can't grant itself permissions, so setup shows you this snippet for your Claude Code user settings (`~/.claude/settings.json`) and offers to add it:

```json
{
  "permissions": {
    "additionalDirectories": ["/path/to/your/job-search"]
  }
}
```

Without it, Claude Code asks before reading or writing files there.

## Your data folder

| File | What it is |
|---|---|
| `perkins.toml` | Your settings: mode, state, claim dates, weekly target, options |
| `master.md` | Your master resume: the only source of facts |
| `tailoring-model.md` | The role types you target and how to angle the resume for each |
| `style.md` | Your resume rules |
| `fact-sheet.md` | Copy-paste answers for applicant forms |
| `tracker.md` | Every application, conversation, lead, pass, and employer you watch |
| `dashboard.html` | The whole search on one page, rebuilt after every change |
| `claim-log.html` | With claims tracking: the work-search log week by week, for a meeting with the state |
| `applications/` | One folder per tailored resume, with its PDF |
| `log/`, `log/evidence/`, `nudges.md` | With claims tracking: the weekly log, screenshots, and reminders |

## Try it without installing

From a clone of the repository: `claude --plugin-dir .` loads it as the plugin for one session. Under the skills, everything is `python run.py <command>`; run `python run.py -h` for the list.
