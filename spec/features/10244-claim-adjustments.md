---
spec: 10244
feature: claim-adjustments
status: ready
drafted: 2026-11-06
source: spec/punchlist.md (Ideas / Backlog, the second-state line); split from spec 10241 on 2026-11-06 at the maintainer's direction, so each part fits the 800-line limit on one automated build
depends: 10242 (the yellow grade's counts phrase), 10241 (the Virginia docs section); 10243 merged first for shared files only
size: M
priority: M (proposed; the maintainer's call)
---

# Per-claim requirement adjustments

**Perkins** · spec **10244** · `claim-adjustments`

> **Guidance only.** Perkins summarizes each state's published work-search rules to help you keep your log. It is not legal advice, and it is not the state. The state's own rules:
>
> 1. **can change at any time**, without Perkins knowing;
> 2. **take precedence** over anything Perkins says, shows, or counts;
> 3. **are your responsibility** to know and meet, not Perkins's.

Part 4 of the four specs split from the Virginia work, and the largest. Order: 10242 (headline and yellow grade), 10241 (Virginia), 10243 (optional state rules), **10244** (this one). Mark it ready only after 10243 has merged.

## The ask

The maintainer, 2026-11-06, answering 10241's question 9 (per-claim exemptions): fold it in.

## Problem

The state file says how many activities a week; the agency can tell one person otherwise. Perkins has no way to record that, in Washington or Virginia, so those weeks look short on every screen.

In Virginia, VEC's own pages name the cases (sources and detail in 10241, "Exemptions and reduced requirements"):

- **VEC's own instruction wins:** two contacts a week "unless VEC specifically advises otherwise." [R&R]
- **Union hiring hall:** contact the approved hall each week instead of two employers. [R&R] [FAQ]
- **Temporary layoff with a return date:** may be treated as attached to the regular employer, which meets the requirement while attached. [60-10, G]
- **High-unemployment areas:** one employer contact a week at a 10% to 14.9% area rate, waived at 15% or more. [60-10, H] [612, A 7 a]
- **Approved training:** VEC decides and tells the claimant the requirement while in it; Trade Act training removes the active-search requirement. [Elig] [613]

| Tag | Source (checked 2026-11-06) |
|---|---|
| [R&R] | VEC, [Your Unemployment Benefit Rights and Responsibilities](https://www.vec.virginia.gov/your-unemployment-benefit-rights-and-responsibilities) |
| [Elig] | VEC, [Benefits Eligibility](https://www.vec.virginia.gov/benefits-eligibility) |
| [FAQ] | VEC, [Unemployment FAQ](https://www.vec.virginia.gov/faqs?category=unemployment) |
| [612] | Code of Virginia, [§ 60.2-612](https://law.lis.virginia.gov/vacode/title60.2/chapter6/section60.2-612/) |
| [613] | Code of Virginia, [§ 60.2-613](https://law.lis.virginia.gov/vacode/title60.2/chapter6/section60.2-613/) |
| [60-10] | Virginia Administrative Code, [16VAC5-60-10](https://law.lis.virginia.gov/admincode/title16/agency5/chapter60/section10/) |

Washington's equivalents weren't researched. They don't need to be: this records only what the agency told the person.

## Charter

Let a person record, in their own words, that their agency changed their weekly requirement for a stretch of weeks, and make every screen count against that number for those weeks, with the reason shown. Perkins never decides on its own that someone is in a high-unemployment area or that their training is approved. With no adjustments, nothing changes.

## Model: what the code has today

- `perkins/config.py:222-266`: `render` writes `perkins.toml` whole each time; `[claims]` holds `state`, `claim_start`, `claim_end`. `load` reads it. `refuse_sensitive` refuses SSN-shaped numbers and the like in free text.
- `perkins/clerk.py:174-201`: `ensure_week` opens a week file with `state.required` open slots, writes `required:` to frontmatter, and the line "{required} approved activities a week".
- `perkins/clerk.py:204-207`: `recount` keeps the week file's counts in frontmatter.
- `perkins/clerk.py:222-241`: `counts_phrase`, `claim_line`, `check_line` (after 10242, `counts_phrase` also names maybe entries). `perkins/clerk.py:255-359`: `tend_nudges`, which compares solid with `state.required` to auto-tick the check line.
- `perkins/claim_log.py:291-293`: each week's requirement already comes from its own frontmatter, falling back to the state's.
- `perkins/dashboard.py:75-115`: the claim panel compares solid with `state.required`. `perkins/due.py:81-104`: the claim due item. `perkins/status.py:43-56`: the claim summary.
- `perkins/init.py:53-64`: claims setup raises `weekly_target` to the state's minimum.
- `skills/job-status/SKILL.md` and `skills/log-activity/SKILL.md` already allow `run.py clerk *`.

## Behavior

### 1. The record, in `perkins.toml`

Under `[claims]`:

```toml
[[claims.adjustment]]
from = "2027-03-07"        # the first day it applies
to = "2027-04-24"          # optional; leave it out for "until the agency says otherwise"
required = 1               # 0 means the agency waived the work search for these weeks
reason = "Agency letter dated 2027-03-04: approved training, one contact a week"
```

- `load` reads the list: `from` a date; `to` an optional date on or after `from`; `required` a whole number, 0 or more; `reason` non-empty and passed through `refuse_sensitive` (no claimant ID or the like). `render` writes them back after the `[claims]` keys.
- An adjustment applies to every claim week that overlaps it. Where two overlap one week, the one starting later wins.

### 2. The command

`run.py clerk adjust --from <date> [--to <date>] --required <n> --reason "<words>"` adds one; `clerk adjust --list` shows them; `clerk adjust --remove --from <date>` removes one. Each runs the clerk afterward.

### 3. Week files follow the adjustments

Each clerk run keeps each week file's `required:` and a new `required_reason:` in frontmatter in step with the adjustments, the way it keeps the counts. Removing an adjustment restores the state's number on the next run. `ensure_week` opens a new week with the adjusted number of open slots.

### 4. Every reader uses the week's own number

Everything that compares a week's solid count with a requirement reads that week's own `required` (frontmatter, falling back to the state's): the check line's auto-tick and `counts_phrase` in `tend_nudges`, `clerk.run`'s report, the dashboard, the due item, and `status`. The claim log page already does.

Where a week's requirement differs from the state's, the dashboard, the claim log page, and `status` say so: "{agency} minimum 1 (adjusted: <reason>)". With 0: "no work search required this week (<reason>)". The check line isn't added for a 0 week; the claim line still is, because the weekly claim still has to be filed.

`weekly_target` is a pace goal and stays as it is.

### 5. Skills and docs

- job-status and log-activity record an adjustment when the user says the agency changed their requirement, asking for the dates and the source in the user's words. Never from a rule, a guess, or an area's unemployment rate.
- `docs/state-rules.md`, under "How Perkins grades an entry" (added by 10242): "If your agency changed your weekly requirement (for example, approved training or a union hiring hall), tell Perkins what they told you and when. Perkins records it with your reason and counts against that number for those weeks. Perkins never decides that on its own."
- `docs/state-rules.md`, Virginia section (added by 10241): the paragraph on people with a different requirement ends "VEC tells you if one applies; tell Perkins and it counts against your number."
- `CHANGELOG.md`: `[Unreleased]` lines. No `VERSION` change.

Tests (Washington unless noted; reasons are fictional):
- `clerk adjust` writes the table to `perkins.toml`; `load` reads it back; `--list` and `--remove` work.
- A week inside the period gets `required: 1` and its `required_reason:`; weeks outside keep 2; removing the adjustment restores 2 on the next run.
- With required 1, one solid entry auto-ticks the check line and turns the dashboard green.
- With required 0: no open slots, no check line, the claim line still appears, `counts_phrase` reads "no work search required this week (<reason>)".
- Overlapping periods: the later `from` wins for the shared week.
- `to` before `from`, a negative `required`, an empty `reason`, or a reason holding an SSN-shaped number each refuse.
- The claim log page shows the adjusted minimum with its reason.
- Virginia: the adjusted wording names "VEC".
- With no adjustments: every existing test passes.

## Size

Estimated diff: about 500 to 650 lines across about 14 files. Under the 800-line / 30-file limit on one automated build, but the closest of the four. If the build runs over, split it here: (a) the `perkins.toml` table, `clerk adjust`, and the week-file sync (Behaviors 1 to 3); (b) the readers and displays (Behaviors 4 and 5).

## Relationships

- **Depends on** 10242 (`counts_phrase` with maybe) and 10241 (the Virginia docs section this spec adds a sentence to).
- **After** 10243 for shared files only (the clerk, the due list, the docs, the changelog). Nothing here uses 10243's keys.
- **Changes Washington** only for a person who records an adjustment.
- **Contradicts** nothing found.

## Permissions

N/A for the product: user-invoked, runs in the user's own session. The new command, `run.py clerk adjust`, is covered by the `run.py clerk *` allow rules the log-activity, tailor, and job-status skills already have. The reason field goes through `refuse_sensitive`, so a claimant ID or SSN-shaped number refuses. Building it needs no credentials.

## Acceptance

- An adjustment the user reports (for example one contact a week during approved training) changes those weeks' minimum, with the reason shown wherever the minimum is.
- A 0 week shows no check line and no open slots, and still reminds the person to file the weekly claim.
- Removing an adjustment restores the state's number on the next clerk run.
- Perkins never adds an adjustment the user didn't report.
- `python -m pytest tests -q` and `python run.py pii-check . --history` pass.

## Open questions

None open.
