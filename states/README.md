# State rules files

Each `<code>.toml` here holds one state's work-search rules for claims tracking. `_template.toml` is the starting point for a new one.

## The rules for these files

- **Only the agency's own pages.** The state's unemployment agency site and the state's own regulations. Not blog posts, forums, or another tool's summary.
- **Every source listed** in `sources`, and the date you checked them in `last_checked`.
- **Leave out what you can't source.** A missing value is better than a guessed one. Perkins refuses a state file that's missing a required key, which is the point.
- **Plain language** in `rules` and `retention`: the way you'd explain it to a friend filing their first claim.
- **Not legal advice.** The files summarize; the agency decides.

## The keys

| Key | Meaning |
|---|---|
| `code`, `name`, `agency`, `agency_full` | Two-letter code, state name, short and full agency name |
| `last_checked`, `sources` | When you checked, and the pages you checked |
| `required` | Approved activities needed in each week a claim is filed |
| `week_start` | The first day of a claim week (log files are named for its last day) |
| `claim_day` | The weekday the "file the weekly claim" reminder appears, after the week ends |
| `check_day`, `raise_day` | When the midweek check appears, and when it's raised to high priority |
| `retention` | How long to keep the log |
| `rules` | The rules in plain language |
| `contact_rule` | When employer contact info counts as filled |
| `[[kinds]]` | Each approved activity kind and the fields its log entry needs, in the form's order |

Test a new file with `python run.py states`, which loads every file and fails loudly on a bad one.
