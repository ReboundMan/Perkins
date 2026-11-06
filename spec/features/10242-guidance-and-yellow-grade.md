---
spec: 10242
feature: guidance-and-yellow-grade
status: ready
drafted: 2026-11-06
source: spec/punchlist.md (Ideas / Backlog, the second-state line); split from spec 10241 on 2026-11-06 at the maintainer's direction, so each part fits the 800-line limit on one automated build
depends: none
size: M
priority: M (proposed; the maintainer's call)
---

# The guidance-only headline and a yellow grade

**Perkins** · spec **10242** · `guidance-and-yellow-grade`

> **Guidance only.** Perkins summarizes each state's published work-search rules to help you keep your log. It is not legal advice, and it is not the state. The state's own rules:
>
> 1. **can change at any time**, without Perkins knowing;
> 2. **take precedence** over anything Perkins says, shows, or counts;
> 3. **are your responsibility** to know and meet, not Perkins's.

Part 1 of the four specs split from the Virginia work. It builds first: it changes both states, and Virginia's workforce center activities (10241) depend on the yellow grade.

| Order | Spec | What it adds |
|---|---|---|
| 1 | **10242** (this one) | The guidance-only headline, and the yellow "potentially counts" grade, for every state |
| 2 | 10241 `state-virginia` | `states/va.toml` and the skill fixes Virginia needs |
| 3 | 10243 `optional-state-rules` | Same-employer grading, one-time reminders, a file-by date |
| 4 | 10244 `claim-adjustments` | Per-claim requirement changes the agency tells a person about |

Mark each one ready only after the one before it has merged, so each is built on the last.

## The ask

The maintainer, 2026-11-06, answering 10241's open questions:

- **Question 2:** add a yellow category. Solid is green; potentially counts is yellow. It's a good model in Washington too: a conversation that might count gets logged yellow, and the user makes sure to get another green that week.
- **Question 11:** check moves to red, so yellow means only "potentially counts".
- **The headline:** say plainly that this is guidance only, and that the state's definitions (1) may change at any time, (2) take precedence, and (3) are the user's responsibility, not Perkins's.

## Problem

Two gaps, both older than Virginia.

**`check` means two things.** Today it marks both "this record needs fixing" (a blank field, details not in the user's own words) and "this might not count". A person can't tell a typo from a judgment call, and Perkins has nowhere to put a complete, honest record of something the state's rules don't clearly count. So it gets left out, or stretched to solid.

**The screens people look at every week don't say whose rules these are.** The disclaimers today are a "not legal advice" line in `docs/state-rules.md:5`, `states/README.md:11`, the header of `states/wa.toml:2-4`, `README.md:84`, and the site FAQ (`docs/index.html:731-751`). The claim log page, the dashboard, and `status` carry none.

## Charter

Split "might not count" from "needs fixing" with a yellow grade that's shown but never counts toward the minimum, and put the guidance-only headline everywhere Perkins shows a state's rules. Washington's counting doesn't change. Its display does: check turns red-orange, and the headline appears.

## Model: what the code has today

- `perkins/clerk.py:32`: `FITS = ("solid", "check", "no")`. `perkins/clerk.py:112-118`: `fit_of` reads the Fit field's first word; anything unreadable is check.
- `perkins/clerk.py:121-146`: `parse_week` counts solid, check, no, and MISSING blanks. `perkins/clerk.py:204-207`: `recount` writes solid, check, and missing to frontmatter.
- `perkins/clerk.py:222-241`: `counts_phrase`, `claim_line`, `check_line`. `perkins/clerk.py:255-359`: `tend_nudges`, which compares solid with `state.required` to auto-tick the check line.
- `perkins/clerk.py:415-474`: `add_entry`. The agent may write solid or check, never no; a check needs a reason; a blank field turns solid into check.
- `perkins/clerk.py:490`: `clerk add --fit` choices are solid and check.
- `perkins/config.py:275-337`: the `State` dataclass and `load_state`. Each kind passes through as a plain dict; unknown keys are ignored.
- `perkins/claim_log.py:342-343`: "{agency} asks for at least {required} approved activities". `perkins/claim_log.py:446-447`: the check badge uses the amber `--chk` colors; solid uses green.
- `perkins/dashboard.py:75-115`: the claim panel compares solid with `state.required`. `perkins/due.py:81-104`: the claim due item. `perkins/status.py:43-56, 74`: the claim summary and retention line.
- `skills/setup/SKILL.md:44`: the "Claims tracking on" step. `skills/tailor/SKILL.md:124` and `skills/log-activity/SKILL.md:42`: the solid-or-check paragraphs.

## Behavior

### 1. The guidance-only headline

The full three-point headline (the blockquote at the top of this spec) goes at:

- the top of `docs/state-rules.md`, replacing line 5, keeping "If anything here disagrees with the agency, the agency wins: tell us so the file can be fixed";
- `states/README.md`, replacing the "Not legal advice" bullet;
- the header comment of `states/_template.toml` and `states/wa.toml` (comments only; no values change);
- the setup skill's "Claims tracking on" step (`skills/setup/SKILL.md:44`), said once to the user when claims tracking turns on.

A one-line version, built from the state file's agency name, goes on the screens:

> Guidance only: {agency}'s rules can change at any time, take precedence over Perkins, and are yours to know and meet.

- **Claim log page:** under the lead line, in the prep layer (hidden in the meeting view, like the fit grades).
- **Dashboard:** under the claim panel.
- **`status`:** the last line of the claims section, next to retention.
- **README.md:** the claims tracking row and the license line.

One constant holds the one-line wording (`perkins/config.py`, beside `MODE_NAMES`), so the screens can't drift apart. The week files don't carry it: they're the user's record, and they stay clean.

Tests:
- The claim log page, the dashboard in claims mode, and `status` text each contain the one-line wording with "ESD".
- The claim log page's line carries the prep class.
- A package test: `docs/state-rules.md` and `states/README.md` contain "can change at any time", "take precedence", and "your responsibility"; every `states/*.toml` header comment contains "Guidance only". (That last check covers `va.toml` automatically once 10241 adds it.)

### 2. A yellow grade: potentially counts (all states)

**Solid is green, potentially counts is yellow.** A yellow entry is shown but never counts toward the minimum; the user's move is to get another green that week. In Washington, a conversation that might count (say, a networking call that isn't clearly on ESD's approved list) is logged yellow instead of left out or stretched to solid.

| Grade | Stored word | Color | Means | Counts toward the minimum |
|---|---|---|---|---|
| Solid | `solid` | green | On the state's list, every field filled, in the user's own words | Yes |
| Potentially counts | `maybe` | yellow | A complete record in the user's own words, but the state's sources don't clearly count it | No |
| Check | `check` | red-orange (the existing warn colors) | The record needs fixing or confirming | No |
| No | `no` | grey | The person's own call that it doesn't count | No |

Precedence: check outranks maybe, which outranks solid. A blank field makes even a potentially-counting entry check.

Code:
- `FITS = ("solid", "maybe", "check", "no")` (`perkins/clerk.py:32`); `fit_of` reads `maybe` like the others.
- `add_entry` accepts `maybe` from the agent, with one sentence saying why (as check requires). It forces maybe for an entry of a kind with `counts = "maybe"`, written with the kind's `maybe_reason`. A blank field still forces check.
- `load_state` validates a kind's optional `counts` as `"yes"` (the default) or `"maybe"`, and requires a non-empty `maybe_reason` when it's `"maybe"`.
- `parse_week` counts maybe; `recount` writes `maybe:` to frontmatter (added to older week files on their next recount).
- `counts_phrase` adds "N potentially counts" when N is above zero: "1 of 2 solid, 1 potentially counts". The check line's auto-tick and the dashboard's green state stay solid-only. The claim log page's meeting-view count stays as it was (every logged activity, because that's the record the state reviews); its prep notes break out solid and potentially counts. (Corrected while building: the spec first said the page's short-week marker was solid-only, but it has always counted logged activities.)
- Displays: the claim log page's `.badge.maybe` takes the amber `--chk` colors and reads "potentially counts"; `.badge.check` moves to the warn colors; the per-week counts line adds maybe. The dashboard claim panel adds "N potentially counts: get one more solid" when the week is short. `status` and the due item use `counts_phrase`.
- `clerk add --fit` choices add `maybe` (`perkins/clerk.py:490`).
- Skills: the fit paragraphs in `skills/tailor/SKILL.md:124` and `skills/log-activity/SKILL.md:42` gain the yellow definition and a Washington example.
- `states/README.md`'s key table gains a kind's `counts` and `maybe_reason`; `states/_template.toml` gains them as comments.

Tests (Washington, plus a fictional test state in a temporary states folder, since no shipped state uses `counts = "maybe"` until 10241):
- `fit_of` reads "maybe" and "Maybe." as maybe; unknown words still read as check.
- `add_entry` with fit maybe and a reason writes maybe; without a reason refuses; with a blank field writes check.
- A Washington "Other approved activity" can be written maybe by the agent.
- In the test state, an entry of a `counts = "maybe"` kind submitted as solid is written maybe with the kind's reason.
- A week with 1 solid and 1 maybe against 2 required: the check line doesn't auto-tick; `counts_phrase` reads "1 of 2 solid, 1 potentially counts"; the dashboard isn't green; the claim log page's prep counts show the maybe.
- `recount` adds `maybe:` to an older week file without it, and changes nothing else.
- Claim log page: a maybe entry's badge has class `maybe` and reads "potentially counts"; the check badge uses the warn colors.
- A state file with `counts = "sometimes"`, or `counts = "maybe"` without `maybe_reason`, refuses to load.
- Every existing Washington test passes, apart from tests that assert check's old color.

### 3. `docs/state-rules.md`

Replace the top of the page (line 5) with:

```markdown
> **Guidance only.** Perkins summarizes each state's published work-search rules to help you keep your log. It is not legal advice, and it is not the state. The state's own rules:
>
> 1. **can change at any time**, without Perkins knowing;
> 2. **take precedence** over anything Perkins says, shows, or counts;
> 3. **are your responsibility** to know and meet, not Perkins's.
>
> If anything here disagrees with the agency, the agency wins: tell us so the file can be fixed.

## How Perkins grades an entry

| Grade | Means | Counts toward the week's minimum |
|---|---|---|
| Solid (green) | On the state's list, every field filled, in your own words | Yes |
| Potentially counts (yellow) | A complete record, but the state's rules don't clearly count it | No: get another solid that week |
| Check (red) | The record needs fixing or confirming, such as a blank field | No |
| No | Your own call that it doesn't count | No |
```

`CHANGELOG.md` gets `[Unreleased]` lines for the headline and the grade. No `VERSION` change: the maintainer cuts the release once the parts they want have merged.

## Size

Estimated diff: about 400 to 500 lines across about 15 files, most of it tests. Under the 800-line / 30-file limit on one automated build.

## Relationships

- **Blocks** 10241 (Virginia): its workforce center kind sets `counts = "maybe"`. Without this spec the loader ignores that key and grades those activities solid.
- **Blocks** 10243 and 10244, which both grade or count against the yellow grade.
- **Changes Washington's display**: the headline, and check moving from amber to red-orange. Washington's counting doesn't change.
- **Contradicts** nothing found.

## Permissions

N/A for the product: user-invoked, runs in the user's own session. No new command. Building it needs no credentials.

## Acceptance

- `docs/state-rules.md` opens with the three-point headline and has the grading table.
- The claim log page, the dashboard, and `status` carry the one-line guidance wording with the state's agency name; the claim log page's line hides in the meeting view.
- Setup tells the user the headline once, when claims tracking turns on.
- An entry can be written maybe with a reason; it shows yellow as "potentially counts" and never counts toward the minimum. Check shows red-orange.
- A state file's kind can force maybe with `counts = "maybe"` and a `maybe_reason`; a bad value refuses to load.
- `python -m pytest tests -q` and `python run.py pii-check . --history` pass.

## Open questions

None open. The three answers this spec carries out (questions 2 and 11, and the headline) are recorded in 10241.
