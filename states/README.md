# State rules files

Each `<code>.toml` here holds one state's work-search rules for claims tracking. `_template.toml` is the starting point for a new one.

## The rules for these files

- **Only the agency's own pages.** The state's unemployment agency site and the state's own regulations. Not blog posts, forums, or another tool's summary.
- **Every source listed** in `sources`, and the date you checked them in `last_checked`.
- **Leave out what you can't source.** A missing value is better than a guessed one. Perkins refuses a state file that's missing a required key, which is the point.
- **Plain language** in `rules` and `retention`: the way you'd explain it to a friend filing their first claim.
- **Guidance only, and it says so.** Every file's header comment opens with it, and Perkins shows it wherever it shows a state's rules:

  > **Guidance only.** Perkins summarizes each state's published work-search rules to help you keep your log. It is not legal advice, and it is not the state. The state's own rules:
  >
  > 1. **can change at any time**, without Perkins knowing;
  > 2. **take precedence** over anything Perkins says, shows, or counts;
  > 3. **are your responsibility** to know and meet, not Perkins's.

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
| a kind's `counts`, `maybe_reason` | Optional. `counts = "maybe"` grades every entry of that kind potentially counts (shown, never counted toward the minimum), with `maybe_reason` saying why in a sentence. Leave it out for a kind that counts (the default, `"yes"`). |

Test a new file with `python run.py states`, which loads every file and fails loudly on a bad one.
