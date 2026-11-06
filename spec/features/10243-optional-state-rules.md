---
spec: 10243
feature: optional-state-rules
status: ready
drafted: 2026-11-06
revised: 2026-11-06 (the maintainer answered both open questions)
source: spec/punchlist.md (Ideas / Backlog, the second-state line); split from spec 10241 on 2026-11-06 at the maintainer's direction, so each part fits the 800-line limit on one automated build
depends: 10242 (the yellow grade), 10241 (states/va.toml and the Virginia test helpers); both merged first
size: M
priority: M (proposed; the maintainer's call)
---

# Three optional state rules: same employer, one-time reminders, a file-by date

**Perkins** · spec **10243** · `optional-state-rules`

> **Guidance only.** Perkins summarizes each state's published work-search rules to help you keep your log. It is not legal advice, and it is not the state. The state's own rules:
>
> 1. **can change at any time**, without Perkins knowing;
> 2. **take precedence** over anything Perkins says, shows, or counts;
> 3. **are your responsibility** to know and meet, not Perkins's.

Part 3 of the four specs split from the Virginia work. Order: 10242 (headline and yellow grade), 10241 (Virginia), **10243** (this one), 10244 (claim adjustments). Mark it ready only after 10241 has merged.

Three optional state-file keys, each small and independent of the others. Virginia sets all three. Washington sets none, so it's unchanged.

## The ask

The maintainer, 2026-11-06, answering 10241's open questions:

- **Question 5:** a second opening at the same employer in one week is yellow (potentially counts).
- **Question 6:** add one-time reminders (Virginia's registration deadline).
- **Question 10:** yes, show VEC's filing deadline.

And later the same day, answering this spec's own two questions as proposed: a likely repeat (same employer, same opening) is check, and Washington's late-filing rule gets researched as its own backlog item.

## Sources

The facts below come from these VEC and Virginia Administrative Code pages, checked 2026-11-06. Spec 10241 holds the full research and the rest of the sources.

| Tag | Source |
|---|---|
| [R&R] | VEC, [Your Unemployment Benefit Rights and Responsibilities](https://www.vec.virginia.gov/your-unemployment-benefit-rights-and-responsibilities) |
| [Roadmap] | VEC, [Benefits Roadmap](https://www.vec.virginia.gov/unemployed/benefits-roadmap) |
| [Certify] | VEC, [Certify for Weekly Benefits](https://www.vec.virginia.gov/certify-weekly-benefits) |
| [Elig] | VEC, [Benefits Eligibility](https://www.vec.virginia.gov/benefits-eligibility) |
| [Handbook] | VEC, [Claimant Handbook](https://www.vec.virginia.gov/sites/default/files/documents/VEC%20Claimant%20Handbook%20updated%2012.11.23.pdf) (PDF; page numbers are the handbook's own) |
| [60-10] | Virginia Administrative Code, [16VAC5-60-10](https://law.lis.virginia.gov/admincode/title16/agency5/chapter60/section10/) |

## Problem

- **Same employer.** Perkins counts solid entries and nothing else. Two solid applications at one employer show "2 of 2 solid", while VEC's roadmap asks for "a minimum of two different employers each week" [Roadmap], and the rights page says not to repeat a contact with the same employer unless it's for a different job opening [R&R].
- **One-time tasks.** The schema only knows weekly rhythms. Virginia asks claimants to register with the Virginia Workforce Connection within 10 days of filing, and not registering can delay or deny benefits. [Roadmap] [Handbook, p. 14]
- **No deadline on the claim reminder.** The weekly claim reminder appears on the claim day but never says when it's too late. VEC treats a weekly claim filed 21 or more days after the week ends as untimely, and in most cases it isn't paid. [R&R] [60-10, F]

## Charter

Add three optional state keys, `distinct_employers`, `[[once]]`, and `claim_late_days`, each validated by the loader and each doing nothing for a state that doesn't set it. Add all three to `states/va.toml`.

## Model: what the code has today

- `perkins/config.py:275-337`: `load_state`. Unknown keys are ignored, so none of these keys does anything today.
- `perkins/clerk.py:26-27`: `CLAIM_RE` and `CHECK_RE`, which find the claim and check lines in `nudges.md`.
- `perkins/clerk.py:222-241`: `claim_line` and `check_line`. `perkins/clerk.py:255-359`: `tend_nudges`, which writes and finds those lines.
- `perkins/clerk.py:415-474`: `add_entry`, which grades each entry (after 10242: solid, maybe, check). It counts solid entries with no regard to employer.
- `perkins/due.py:81-104`: the claim due item.
- `states/va.toml` (from 10241): `required = 2`, Sunday-to-Saturday weeks, the claim reminder on Sunday; employer field `Employer or business name`, position field `Type of work or position`.

## Behavior

### 1. A second contact with the same employer in a week (yellow, or check)

An optional state key names which fields hold the employer and the opening:

```toml
distinct_employers = { employer = "Employer or business name", opening = "Type of work or position" }
```

`load_state` checks both names appear in some kind's fields and refuses otherwise, naming the missing one. In `add_entry`, when the key is set and the new entry would be solid, compare its employer (case and spacing ignored) with the week's existing solid and maybe entries:

- **Same employer, different opening** → maybe, with the reason "A second contact with this employer this week, for a different opening. VEC asks for two different employers, so this one potentially counts." (maintainer, question 5)
- **Same employer, same opening** → check, with the reason "Looks like a repeat of activity N (same employer and opening). VEC doesn't count a repeated contact." Check rather than yellow, because a person should look and VEC says repeats don't count. (Maintainer, 2026-11-06: as proposed.)

The reasons use the state's agency name, not a hardcoded "VEC". Entries without the employer field (Virginia's workforce center activities) never match.

Tests:
- Virginia: same employer, different positions, same week: the second is maybe with that reason; the week reads 1 solid, 1 potentially counts.
- Virginia: same employer, same position, same week: the second is check, naming activity 1.
- Virginia: "Kestrel Energy" and "kestrel  energy" match.
- Virginia: the same employer in two different weeks: both solid.
- Virginia: two workforce center activities in one week: both maybe (from their kind), neither matched here.
- Washington: two entries at one employer stay solid.
- `distinct_employers` naming a field no kind has refuses to load, naming it.

### 2. One-time reminders

An optional `[[once]]` table in the state file, each entry with `task` and `within_days`. `load_state` reads `once` as a list of tables, each needing a non-empty `task` and a whole-number `within_days`.

When claims tracking is on and `claim_start` is set, the clerk writes one nudge line per task, once:

```
- [ ] (H) <today> One-time: <task>. Due <claim_start + within_days>; tick this once it's done. 📅 <due>
```

It finds the line again by the text after "One-time: " (a new `ONCE_RE` beside `CLAIM_RE` and `CHECK_RE`), so it never adds a second copy and never unticks one. A claim set up late still gets the line, already overdue; the person ticks it if it's done. The due list shows an unticked one-time line from its due date, like the claim item (`perkins/due.py:81-104`).

Tests:
- Virginia claims home: the first clerk run adds exactly one "One-time:" line, due `claim_start + 10`; a second run adds nothing; ticking it survives a rerun.
- The due list shows it from its due date until it's ticked.
- Search mode: no line. Washington: no line.
- A `[[once]]` entry missing `task`, or with `within_days = "ten"`, refuses to load.

### 3. A file-by date on the claim reminder

An optional state key, `claim_late_days` (Virginia: 21), meaning, in the rights page's words, a weekly claim filed this many days or more after the week ends is late. [R&R] `load_state` requires a whole number above zero.

- The file-by date is the week's last day plus `claim_late_days - 1`. For the claim's first week it's the earlier of that and `claim_start + claim_late_days - 1`, because the first weekly claim is due within 21 days of applying. [60-10, F] [Certify] (If someone enters their last day of work as `claim_start`, the date only gets earlier, which is the safe direction.)
- `claim_line` adds "File by <date>." before the week link. Once that date passes with the line unticked, it reads "Past {agency}'s file-by date (<date>): the claim may have gone inactive, and {agency} may need you to reactivate it." [Handbook, p. 12] `CLAIM_RE` matches the line's opening words, which don't change.
- The due item's detail adds the file-by date.

The 21-day rule has a small conflict in VEC's own sources. The regulation, the eligibility page, the rights page, the certification page, and the handbook say 21 days; one FAQ line says 20. The regulation, the eligibility page's example, and the handbook ("more than 21 days") allow day 21 itself; the rights page calls 21 or more days late. This uses the rights page's stricter reading. [60-10, F] [Elig] [R&R] [Certify] [Handbook, p. 12]

Washington doesn't set the key, so its claim line is unchanged. ESD's late-filing rule hasn't been researched; that's its own backlog item ("Washington's late-filing rule"), and Washington sets `claim_late_days` only once it's sourced from ESD's own pages.

Tests:
- Virginia, week ending 2027-03-06, claim started earlier: "File by 2027-03-26."
- Virginia, first week, `claim_start` 2027-03-01: "File by 2027-03-21."
- Virginia, today past the date, unticked: the past-date wording; ticked: unchanged.
- Washington: the claim line is byte-for-byte what it was before this spec.
- `claim_late_days = 0` or a non-integer refuses to load.

### 4. `states/va.toml` gains the three keys

After `raise_day`:

```toml
# VEC: a weekly claim filed 21 or more days after the week ends is late.
claim_late_days = 21
```

After `contact_rule`:

```toml
# A second contact with one employer in a week potentially counts (a different opening)
# or is likely a repeat (the same opening). VEC's roadmap asks for two different employers.
distinct_employers = { employer = "Employer or business name", opening = "Type of work or position" }
```

At the end:

```toml
# One-time reminders, counted from the claim's first day.
[[once]]
task = "Fully register with the Virginia Workforce Connection (vawc.virginia.gov) and add your resume. If you live outside Virginia, register with your own state's workforce agency and send VEC proof"
within_days = 10
```

`test_va_rules` (from 10241) gains: `claim_late_days == 21`, the `distinct_employers` pair, and one `[[once]]` entry with `within_days == 10`.

### 5. Docs

- `states/README.md`'s key table gains `claim_late_days`, `distinct_employers`, and `[[once]]`; `states/_template.toml` gains them as comments.
- `docs/state-rules.md`, Virginia section (added by 10241): the repeat-contact line ends "Perkins marks a second opening at the same employer in one week as potentially counts."; the registration line ends "Perkins reminds you once."; the filing line ends "Perkins shows the file-by date."
- `CHANGELOG.md`: `[Unreleased]` lines. No `VERSION` change.

## Size

Estimated diff: about 450 to 550 lines across about 10 files, most of it tests. Under the 800-line / 30-file limit on one automated build.

## Relationships

- **Depends on** 10242 (the same-employer rule writes maybe) and 10241 (`states/va.toml`, `claims_home(state="va")`, and `VA_EMPLOYER_FIELDS` in `tests/helpers.py`).
- **Before** 10244, for shared files only (the clerk, the due list, the docs, the changelog): building one at a time keeps the pull requests free of conflicts. 10244 doesn't use anything from this spec.
- **Connects to** the backlog item "Close out an item on the due list": the one-time line is a natural first non-tracker item for done and won't do.
- **Connects to** "A dated tick on a claim line could carry the tick's own date": the one-time line would use the same tick handling.
- **Follow-up:** the backlog item "Washington's late-filing rule", so Washington can set `claim_late_days` too. Not part of this spec.
- **Contradicts** nothing found.

## Permissions

N/A for the product: user-invoked, runs in the user's own session. No new command. Building it needs no credentials.

## Acceptance

- A second same-week contact with one Virginia employer is yellow for a different opening, check for the same one. Washington is unchanged.
- The Virginia registration reminder appears once, due 10 days after the claim's first day, and shows on the due list until it's ticked.
- Virginia's claim reminder shows its file-by date, and says so plainly once that date has passed. Washington's claim line is unchanged.
- A bad value for any of the three keys refuses to load, naming the key.
- `python -m pytest tests -q` and `python run.py pii-check . --history` pass.

## Open questions

Carried from 10241 (questions 12 and 13 there). Answered 2026-11-06, kept for the record:

1. ~~**Same employer, same opening.**~~ *Maintainer: as proposed.* Behavior 1 grades a likely repeat as check, not yellow.
2. ~~**Washington's file-by date.**~~ *Maintainer: as proposed.* Researching ESD's late-filing rule is its own backlog item; Washington shows no file-by date until then.

None open.
