---
spec: 10241
feature: state-virginia
status: built
built: 2026-11-06 (https://github.com/ReboundMan/Perkins/pull/2)
pr: https://github.com/ReboundMan/Perkins/pull/2
drafted: 2026-11-06
revised: 2026-11-06 (VEC's Claimant Handbook and Sample Work Search Log read); 2026-11-06 (the maintainer answered open questions 1 to 11); 2026-11-06 (split into 10242, 10241, 10243, and 10244 at the maintainer's direction, so each fits the 800-line limit on one automated build; this spec keeps Virginia's research and state file)
source: spec/punchlist.md (Ideas / Backlog, "A second state's rules file, researched from that agency's own pages with sources")
depends: 10242 (the yellow grade and the guidance headline); merged first
size: M
priority: M (proposed; the maintainer's call)
---

# Virginia as the second state

**Perkins** · spec **10241** · `state-virginia`

> **Guidance only.** Perkins summarizes each state's published work-search rules to help you keep your log. It is not legal advice, and it is not the state. The state's own rules:
>
> 1. **can change at any time**, without Perkins knowing;
> 2. **take precedence** over anything Perkins says, shows, or counts;
> 3. **are your responsibility** to know and meet, not Perkins's.

Spec 10242 carries that headline into the product, for Washington as well as Virginia.

Research and spec only. Nothing here is built, and `states/va.toml` does not exist yet: `python run.py states` loads every file in `states/` and would fail on a half-filled one.

## The split

The Virginia work was one large spec. On 2026-11-06 the maintainer split it into four, so each fits the 800-line / 30-file limit on one automated build. This spec keeps the research and Virginia's state file.

| Order | Spec | What it adds |
|---|---|---|
| 1 | 10242 `guidance-and-yellow-grade` | The guidance-only headline, and the yellow "potentially counts" grade, for every state |
| 2 | **10241** (this one) | `states/va.toml` and the skill fixes Virginia needs |
| 3 | 10243 `optional-state-rules` | Same-employer grading, one-time reminders, a file-by date |
| 4 | 10244 `claim-adjustments` | Per-claim requirement changes the agency tells a person about |

Mark each one ready only after the one before it has merged, so each is built on the last. All four together make one minor release (0.3.0); none of them changes `VERSION`.

## The ask

> A second state's rules file, researched from that agency's own pages with sources.

The maintainer picked Virginia. Two choices were already made: the state file comes only from the agency's own pages (VEC's site, the Code of Virginia, and the Virginia Administrative Code), and Perkins keeps refusing a state file that's missing a required key.

### The maintainer's answers (2026-11-06), and where each landed

| # | Question | Answer | Lands in |
|---|---|---|---|
| 1 | Download the handbook and sample log? | Yes | Read and folded into the research below |
| 2 | Count workforce center activities? | Add a yellow grade: solid is green, potentially counts is yellow. Useful in Washington too, for conversations that might count | 10242 (all states); Virginia's workforce center kind is yellow (this spec) |
| 3 | Job fairs and the union hall? | Leave out for now | Not in `va.toml` |
| 4 | Working rules for blank fields? | Yes, as proposed | `contact_rule` in `va.toml` |
| 5 | Same employer, different opening? | Yellow | 10243 |
| 6 | One-time registration reminder? | Add one-time reminders | 10243 |
| 7 | Retention wording? | Add a conservative note | `retention` in `va.toml` |
| 8 | Spec number? | Allocate from the central registry | 10241, then 10242 to 10244 for the split |
| 9 | Per-claim exemptions? | Fold them into this work | 10244 |
| 10 | Show VEC's filing deadline? | Yes | 10243 |
| 11 | Check's color? | Red, so yellow means only "potentially counts" | 10242 |

Plus: a guidance-only headline (above, and 10242).

## Problem

Claims tracking supports Washington only (`README.md:43`, "Washington today"). A beta tester claiming in Virginia gets Search mode and nothing else (`skills/setup/SKILL.md:24`). Virginia's rules are close to Washington's in shape (a Sunday-to-Saturday week, a fixed weekly count, a record the agency can audit) but differ in ways the code and the skills assume away: a different count, a different claim day, a different set of fields, a "different employers" rule, a one-time registration deadline, and a filing deadline. VEC's own sources also disagree on what counts toward the weekly two.

This spec covers the count, the week, the fields, and the kinds. 10243 covers the different-employers rule, the registration deadline, and the filing deadline. Two gaps older than Virginia are their own specs: 10242 (a way to say "this might count" apart from "this record needs fixing") and 10244 (a way to record that the agency changed one person's weekly requirement).

## Charter

Add Virginia so a claimant there gets the same weekly log, reminders, and claim log page Washington claimants get, with every value traced to a VEC, Code of Virginia, or Virginia Administrative Code source, and with gaps and conflicts left visible. Washington doesn't change.

## What Virginia requires

Every fact below comes from one of these sources, all checked 2026-11-06. The tag after each fact names its source. 10243 and 10244 cite this section.

| Tag | Source |
|---|---|
| [R&R] | VEC, [Your Unemployment Benefit Rights and Responsibilities](https://www.vec.virginia.gov/your-unemployment-benefit-rights-and-responsibilities) |
| [Elig] | VEC, [Benefits Eligibility](https://www.vec.virginia.gov/benefits-eligibility) |
| [Roadmap] | VEC, [Benefits Roadmap](https://www.vec.virginia.gov/unemployed/benefits-roadmap) |
| [Certify] | VEC, [Certify for Weekly Benefits](https://www.vec.virginia.gov/certify-weekly-benefits) |
| [FAQ] | VEC, [Unemployment FAQ](https://www.vec.virginia.gov/faqs?category=unemployment), sections "Weekly Eligibility and Certification", "Partial Unemployment", and "Job Search and Work Requirements" |
| [Handbook] | VEC, [Claimant Handbook](https://www.vec.virginia.gov/sites/default/files/documents/VEC%20Claimant%20Handbook%20updated%2012.11.23.pdf) (PDF, 21 pages; the cover says "Revised March 2023", the file name says "updated 12.11.23"). The certification page links it as the claimant handbook. Page numbers are the handbook's own. |
| [Log] | VEC, [Sample Work Search Log](https://www.vec.virginia.gov/sites/default/files/Sample-Work-Search-Log.xlsx) (Excel, one sheet), linked from the FAQ |
| [612] | Code of Virginia, [§ 60.2-612, Benefit eligibility conditions](https://law.lis.virginia.gov/vacode/title60.2/chapter6/section60.2-612/) |
| [613] | Code of Virginia, [§ 60.2-613, Benefits not denied to individuals in training](https://law.lis.virginia.gov/vacode/title60.2/chapter6/section60.2-613/) |
| [60-10] | Virginia Administrative Code, [16VAC5-60-10, Total and part-total unemployment](https://law.lis.virginia.gov/admincode/title16/agency5/chapter60/section10/) |
| [Forms] | Virginia Administrative Code, [FORMS (16VAC5-60)](https://law.lis.virginia.gov/admincode/title16/agency5/chapter60/section9998/) |

### How many, and what kind

- **At least two a week**, unless VEC tells you otherwise. VEC words it four ways: "at least two job searches or contacts for work each week" [R&R]; "a minimum of two different employers each week" [Roadmap]; "a minimum of two job contacts" [FAQ]; "at least two work search activities" [Handbook, p. 11].
- **Two different employers.** The roadmap says so outright. [Roadmap] The rights page says the same for union members without an approved hiring hall. [R&R]
- **No repeats with the same employer** unless it's for a different job opening there. [R&R] Whether that second opening counts toward the two isn't settled, so Perkins grades it yellow (10243).
- **In-person and phone contacts should reach someone who can hire.** [R&R]
- **The work has to be real for you:** work you're willing and qualified to do, at pay you'd accept, in an area you'd work in. [R&R]
- **Inside the claim week.** Contacts must happen within the week being claimed. [R&R]
- The eligibility page phrases it as "contact several employers each week" when VEC has directed you to look for work, and says most claimants are directed to. [Elig]
- The statute: every totally unemployed claimant reports the names of employers contacted each week, and VEC may verify them with employers. [612, A 7 a]

### What counts

VEC's sources don't agree, so this section lays them side by side.

- **The handbook's list of qualifying activities** [Handbook, p. 11]:
  - apply for a job that fits your skills and qualifications
  - interview for a job
  - report to a union hiring hall if you're a registered member of that union
  - participate in reemployment services at your state workforce center
- **The handbook's list of activities that don't count** [Handbook, p. 11]:
  - applying for a job you're unqualified for or have no intention of accepting
  - viewing job leads without applying
  - failing to apply the way the employer directs (its example: not submitting an online application when the employer says to apply online)
- **The handbook's sample log** (Appendix C, an image) lists five "options for meeting your weekly work search requirements": contact an employer in person or by phone; apply on "our online job search website"; apply online on a job board; attend a job fair, hiring event, or networking activity; take part in a reemployment assessment (RESEA) workshop or career center activity. [Handbook, p. 20] The image is a template: its header still reads "<# OF REQUIRED WEEKLY ACTIVITIES>" where a number belongs, and its example row is dated 2020. Job fairs, hiring events, and networking appear only there.
- **The web pages** describe the search as contacts with employers, and the roadmap asks for two different employers. [R&R] [Roadmap] [FAQ]
- **Union hiring hall.** The rights page and FAQ treat the hall as the whole requirement for a member who gets work through an approved hall (contact it each week instead). [R&R] [FAQ] [612, A 7 a] The handbook lists reporting to the hall as one qualifying activity among four. [Handbook, p. 11]
- **Registration as a contact, sometimes.** VEC may decide that registering with the state job service counts as an employer contact in labor market areas where jobs are limited. [612, A 7 a] That's VEC's call per area, not something Perkins can know.

**How the draft reads it:** two kinds, both from the handbook's own qualifying list. **Employer contact** (applying or interviewing) counts. **Workforce center activity** (reemployment services at a workforce center) is always yellow, potentially counts, because the handbook counts it and the roadmap's "two different employers" doesn't. Job fairs, hiring events, networking, and the union hiring hall stay out for now (maintainer, question 3).

### The claim week and the weekly claim

- **The week runs Sunday 12:01 a.m. through Saturday midnight.** [R&R] [Certify] [Elig] [Handbook, glossary, "Benefit Week"]
- **The first week starts the Sunday before** you file the claim and register for work. [60-10, A] The handbook calls that Sunday the claim effective date. [Handbook, glossary] (Perkins already does this: the first log week is the week containing `claim_start`, `perkins/clerk.py:83-95`.)
- **File on Sunday for the week that just ended.** "You should file your weekly claim on Sunday for the previous week." [R&R] The handbook says Sunday "or as soon as possible", that the first weekly claim can be filed the Sunday after you apply, and that not filing "on Sunday or Monday for the previous week will result in delayed benefit payment." [Handbook, p. 12]
- **Deadline.** The first weekly claim is due within 21 days of applying; each later one within 21 days of the claimed week's Saturday. [60-10, F] [Elig] [Certify] A claim filed 21 or more days late "will be considered as untimely and in most cases will not be paid." [R&R] The handbook says waiting more than 21 days makes the claim inactive, and the weeks before reactivation may be denied. [Handbook, p. 12] One FAQ line says the claim closes after 20 days. [FAQ] The regulation says 21. 10243 uses the rights page's stricter reading.
- **How the search reaches VEC.** Online filers enter their job contacts as they file each weekly claim. Phone filers give basic information by phone, then send detailed written information every four weeks on VEC's Work Search Record form. [R&R] The weekly certification asks whether you looked for work, "along with details about your work search efforts." [Handbook, p. 11]
- **The waiting week.** The first week you meet the weekly requirements is an unpaid waiting week. [Elig] It has to be eligible "in all other respects," which includes the work search. [612, A 9]

### What the record holds

VEC gives four versions. They agree on the core (date, employer, the person, the position, the employer's contact details, the result) and differ on order and extras.

| Source | Items, in the source's order |
|---|---|
| Handbook sample log [Handbook, p. 20] | Date · Employer · Address · Email · Position Title · Contact Name · Phone/Fax · Type of Contact (Phone, Mail, Internet, In-Person) · Next Steps. Each row also names its week, Sunday through Saturday. |
| Eligibility page [Elig] | Month, day, year of contact · complete name of employer · complete address (street, P.O. box, city, state, ZIP) · first and last name of the person you talked with · employer's phone, fax, and email or web address · type of work or position applied for · result of contact |
| Excel sample log [Log] | Employer name · Date of contact · Contact person & info · Job title applied for · Employer phone · Outcome of contact (Pending, interviewed, hired, etc.) |
| Handbook text [Handbook, p. 11] | date of the application · type of contact · position applied for · employer contact information |

The FAQ lists the eligibility page's items in slightly different words. [FAQ] The handbook also says to "document the details of each action (what, when, where, and with whom)" and, if possible, to save a screenshot, email confirmation, or other evidence, kept in one folder. [Handbook, p. 20] The roadmap's tip adds interview dates and times. [Roadmap]

**The draft follows the handbook sample log's order.** It's the closest thing VEC publishes to a form, it holds every item the eligibility page asks for, and it carries the handbook text's "type of contact". The Excel log is a shorter version of the same idea: it has no address and no type of contact.

### How long to keep it

- "Retain your work search records for at least one year following your benefit year begin date." [R&R]
- "You must maintain complete and accurate records of your work search contacts for one year, for auditing purposes." [Elig]
- The handbook doesn't say. It defines the benefit year as the 52 weeks from the claim effective date (the Sunday of the week you filed). [Handbook, glossary]

The first wording ends about when the benefit year does, so a contact from the claim's last week would be kept only days. The draft states VEC's rule and adds Perkins's conservative note, labeled as Perkins's advice (maintainer, question 7).

### Everything else that touches the log

- **Register with the Virginia Workforce Connection within 10 days of filing the initial claim.** Not registering can delay or deny benefits. [Roadmap] The handbook says to "fully register" and add a resume (or update it, if you registered before), and that VEC will tell you if you're exempt, for example when attached to a union hiring hall. [Handbook, p. 14] The eligibility page says to register online at vawc.virginia.gov, at a Virginia Works office, or, if you live outside Virginia, with the workforce agency where you live. [Elig] Out-of-state claimants send VEC proof of that registration within 10 days of filing. [Handbook, p. 14] The rights page exempts out-of-state union members, and a temporary layoff with a return date within six weeks of the last day worked, from registering in their own state. [R&R]
- **Verification and audits.** All contacts are subject to verification, and a claim can be picked for an audit. [R&R] [FAQ] Claims are audited regularly. [Handbook, p. 15]
- **Short weeks.** Fewer than two contacts in a claim week can mean that week is denied. [FAQ] It can also mean an overpayment. [R&R]
- **False information.** Reporting that you looked for work when you didn't make valid work search efforts is one of the handbook's examples of fraud. Penalties can include repaying the benefits, a penalty on top, up to a year without benefits, and criminal charges. [Handbook, p. 15] The FAQ says a false job contact can disqualify you for one year, and after that until the benefits are repaid. [FAQ]
- **Reemployment services.** If VEC selects you, you must take part. [612, A 11] [R&R]
- **During an appeal**, keep searching and certifying; you're paid only for weeks that met the requirements. [Handbook, p. 16]

### Exemptions and reduced requirements

These are what 10244 lets a person record, once VEC has told them one applies:

- **VEC's own instruction wins:** "unless VEC specifically advises otherwise." [R&R]
- **Union hiring hall:** contact the approved hall each week instead of two employers. [R&R] [FAQ]
- **Temporary layoff with a return date:** a claimant with a verifiable return date within a reasonable period may be treated as attached to the regular employer, which meets the search requirement while attached. [60-10, G]
- **High-unemployment areas:** VEC can adjust the requirement quarterly by area. At a total unemployment rate of 10% through 14.9% it drops to one employer contact a week; at 15% or more it's waived. [60-10, H] [612, A 7 a]
- **Approved training:** VEC decides whether training is approved and tells you the work search requirement while you're in it. [Elig] [613, A] Trade Act training removes the active-search requirement. [613, B]
- **Partial claimants** (hours cut by a regular employer) don't have to search, but must work every hour offered. In a week with no work offered by Friday, they file a total claim, register with the Virginia Workforce Connection, and search on Friday and Saturday. [FAQ]
- **Part-time and earning less than the weekly benefit amount:** still have to search and report contacts. [FAQ]

## Model: what the code has today

What this spec touches, as of 0.2.0. 10242 lands first and adds the `maybe` grade and a kind's `counts` key.

- `perkins/config.py:275-337`: the `State` dataclass and `load_state`. Required keys: `name`, `agency`, `last_checked`, `sources`, `required`, and the four weekday keys; a missing one raises `ConfigError`. `retention`, `rules`, `kinds`, and `contact_rule` default to empty. Unknown keys are ignored, and each kind is passed through as a plain dict.
- `perkins/clerk.py:54-57`: `claim_offset`. With `week_start = "sunday"` and `claim_day = "sunday"`, the offset is 1: the claim line for the week ending Saturday appears on Sunday. No change needed.
- `perkins/clerk.py:174-201`: `ensure_week` opens a week file with `state.required` open slots and names it for the week's last day.
- `perkins/clerk.py:407-412`: `clerk add` refuses an unknown kind and lists the state's kinds.
- `perkins/clerk.py:415-474`: `add_entry`. Fields are ordered as the state's list, then `Person`, `Result and next step`, `Source` if not already listed (`EXTRA_FIELDS`, line 33). A blank field turns solid into check.
- `perkins/clerk.py:448-450`: the entry heading is built from three Washington field names: `Employer or business name`, `Job title or reference number`, `What activity`.
- `skills/tailor/SKILL.md:107-124`: step 9 hardcodes Washington's fields (`How`, `Type`, `Employer contact info`, `Job title or reference number`) in the `clerk add` example.
- `skills/log-activity/SKILL.md:33`: kind guidance names "a job-center activity (WorkSource in Washington)".
- `perkins/claim_log.py:228-232, 257`: required fields come from the state file; generic. `perkins/claim_log.py:342-343`: "{agency} asks for at least {required} approved activities".
- `perkins/init.py:53-64`: claims setup loads the state and raises `weekly_target` to its minimum.
- `tests/test_modes.py:113-116`: every state file loads with `required`, `sources`, `last_checked`, and `kinds`. `tests/helpers.py:20-29`: `EMPLOYER_FIELDS` is Washington's field set; `claims_home` pins `state="wa"`.

## Draft `states/va.toml`

Every value is sourced except the two reminder days, which are Perkins's own rhythm (as in Washington's file), and the two pieces labeled as Perkins's: `contact_rule` (approved by the maintainer) and the conservative half of `retention`. The workforce center kind's `counts = "maybe"` needs 10242, which is why this spec builds after it. 10243 adds three more keys to this file when it lands (`claim_late_days`, `distinct_employers`, and a one-time `[[once]]` reminder), so the file never promises a feature that isn't there.

```toml
# Virginia work-search rules for unemployment claims.
# Guidance only, not legal advice. VEC's rules can change at any time, take precedence over
# anything in this file, and are the claimant's responsibility to know and meet, not Perkins's.
# This file summarizes VEC's own pages for the kit's use. Recheck the sources and update
# last_checked whenever you change a value.

code = "va"
name = "Virginia"
agency = "VEC"
agency_full = "Virginia Employment Commission"
last_checked = "2026-11-06"
sources = [
  "https://www.vec.virginia.gov/your-unemployment-benefit-rights-and-responsibilities",
  "https://www.vec.virginia.gov/benefits-eligibility",
  "https://www.vec.virginia.gov/unemployed/benefits-roadmap",
  "https://www.vec.virginia.gov/certify-weekly-benefits",
  "https://www.vec.virginia.gov/faqs?category=unemployment",
  "https://www.vec.virginia.gov/sites/default/files/documents/VEC%20Claimant%20Handbook%20updated%2012.11.23.pdf",
  "https://www.vec.virginia.gov/sites/default/files/Sample-Work-Search-Log.xlsx",
  "https://law.lis.virginia.gov/vacode/title60.2/chapter6/section60.2-612/",
  "https://law.lis.virginia.gov/admincode/title16/agency5/chapter60/section10/",
]

# Work search activities required in each week you file a weekly claim, unless VEC tells you otherwise.
required = 2
# Claim weeks run Sunday through Saturday. Log files are named for the Saturday that ends the week.
week_start = "sunday"
# VEC: file the weekly claim on Sunday for the previous week.
claim_day = "sunday"
# Perkins's own reminder rhythm, not a VEC rule (the same as Washington's): the midweek
# check appears on check_day and is raised to high priority on raise_day.
check_day = "wednesday"
raise_day = "friday"

retention = "VEC's rule: keep your work-search records at least one year following your benefit year begin date. Perkins's advice, to be safe: keep the whole log at least one year past the last week you claim, and until any VEC review or appeal is finished."

rules = [
  "Two work search activities for every week you file a weekly claim, unless VEC tells you otherwise.",
  "They have to happen inside that week, Sunday through Saturday.",
  "VEC's handbook counts applying for a job that fits your skills, interviewing, and taking part in reemployment services at a workforce center. VEC's benefits roadmap asks for contacts with at least two different employers.",
  "Apply only for work you're qualified for and would take, at pay you'd accept, in an area you'd work in. Looking at job leads without applying doesn't count, and neither does skipping the way an employer asks you to apply (such as its online application).",
  "Don't repeat a contact with the same employer unless it's for a different job opening.",
  "In-person and phone contacts should be with someone at the company who can hire.",
  "For each activity, write down what, when, where, and with whom, and save a screenshot or confirmation email when you can.",
  "Fully register with the Virginia Workforce Connection, resume included, within 10 days of filing your claim. If you live outside Virginia, register with your own state's workforce agency and send VEC proof within 10 days. VEC tells you if you're exempt.",
  "Online filers enter their work search with each weekly claim. Phone filers give basic details by phone and send VEC's Work Search Record form every four weeks.",
  "File the weekly claim on Sunday, or as soon as you can, for the week that just ended. After Monday, payment is delayed. A weekly claim filed 21 or more days after the week ended (the first weekly claim: 21 or more days after you applied) is late and in most cases isn't paid.",
  "Your first eligible week is an unpaid waiting week, and it still needs its two activities.",
  "Every contact can be checked. Reporting a search you didn't make is fraud, and it can cost you the benefits, a penalty, up to a year of benefits, and criminal charges.",
]

# Perkins's working rule, approved by the maintainer 2026-11-06. VEC asks for a complete
# street address, a phone or fax, an email or web address, and the name of the person you
# dealt with; postings rarely give all of them.
contact_rule = "Employer address counts as filled with at least the city and state; name what the source didn't give (\"street address not listed\"). Between Employer email or website and Employer phone or fax, at least one must give VEC a way to verify the contact; the other names what the source didn't give (\"phone and fax not listed\"). Mark them MISSING only when there is no way to verify the contact at all. Person is the first and last name of the person you dealt with, or \"no one: applied online\" for an online application with nobody named; for a workforce center activity, the staff member or workshop leader, or \"leader not named\". Type of contact is one of VEC's four: phone, mail, internet, or in person. Mark any other field MISSING only when there is nothing true to write."

[[kinds]]
name = "Employer contact"
fields = ["Contact date", "Kind", "Employer or business name", "Employer address", "Employer email or website", "Type of work or position", "Person", "Employer phone or fax", "Type of contact", "Result and next step"]

[[kinds]]
name = "Workforce center activity"
fields = ["Contact date", "Kind", "What activity", "Office name and city", "Person"]
# Always yellow: potentially counts, never solid.
counts = "maybe"
maybe_reason = "VEC's handbook counts reemployment services at a workforce center; its benefits roadmap asks for contacts with two different employers."
```

**Employer contact fields.** The order is the handbook sample log's: Date, Employer, Address, Email, Position Title, Contact Name, Phone/Fax, Type of Contact, Next Steps, with Perkins's `Kind` after the date as in Washington's file.

| Field | VEC's item |
|---|---|
| Contact date | Date [Handbook]; month, day, year of contact [Elig] |
| Kind | Perkins's own (`perkins/clerk.py:430`) |
| Employer or business name | Employer [Handbook]; complete name of employer [Elig] |
| Employer address | Address [Handbook]; complete address [Elig] |
| Employer email or website | Email [Handbook]; email or web address [Elig] |
| Type of work or position | Position Title [Handbook]; type of work or position applied for [Elig] |
| Person | Contact Name [Handbook]; first and last name of the person you talked with [Elig] |
| Employer phone or fax | Phone/Fax [Handbook]; telephone and fax number [Elig] |
| Type of contact | Type of Contact: Phone, Mail, Internet, In-Person [Handbook] |
| Result and next step | Next Steps [Handbook]; result of contact [Elig]; outcome of contact [Log] |

Three names reuse Perkins names on purpose, because the meaning matches and the tailor skill already supplies them: `Employer or business name`, `Person`, and `Result and next step`. Because `Person` and `Result and next step` are in the state's list, `add_entry` treats them as required and doesn't append them a second time (`perkins/clerk.py:444`).

**Workforce center activity fields.** VEC publishes no fields for it. These follow the handbook's "what, when, where, and with whom" [Handbook, p. 20], reusing Washington's names where they fit: `What activity` (what), `Contact date` (when), `Office name and city` (where), `Person` (with whom). `What activity` is already in the clerk's heading tuple.

## The changes

Each change is the smallest one that makes its piece fit. Tests are listed with each.

### 1. Add `states/va.toml`

The draft above, with `last_checked` set to the build day after rechecking every source.

Tests:
- `tests/test_modes.py::test_every_state_file_loads` already covers loading.
- New `test_va_rules`: `required == 2`; `week_start` is Sunday and `week_end` Saturday; `claim_offset(va) == 1`; two kinds, `Employer contact` and `Workforce center activity`, with the fields above in order; the workforce center kind has `counts == "maybe"` and a `maybe_reason`.
- New clerk rhythm test with a Virginia claims home: on a Saturday no claim line exists for that week; on the following Sunday the claim line for the Saturday's week appears; the midweek check appears Wednesday at (M) and is raised to (H) on Friday. Week files are named for Saturdays.
- A Virginia workforce center activity submitted as solid is written maybe with the kind's reason (10242's grade).
- The claim log page, the dashboard in claims mode, and `status` carry the one-line guidance wording with "VEC" (10242's wording).
- `tests/helpers.py`: `claims_home` gains a `state` parameter (default `"wa"`), and a fictional `VA_EMPLOYER_FIELDS` sits beside `EMPLOYER_FIELDS` (for example Kestrel Energy, Richmond, VA, `https://jobs.example.com/ke`, "phone and fax not listed", "Internet", "no one: applied online"). 10243 reuses both.

### 2. The tailor skill stops hardcoding Washington's fields

Today `skills/tailor/SKILL.md:107-124` passes `How`, `Type`, `Employer contact info`, and `Job title or reference number`. For Virginia, `clerk add` would refuse (it fails safe, `perkins/clerk.py:432-434`) and the agent would have to work out the mapping from the refusal.

Text only: step 9 says to use the field names of the `Employer contact` kind in `states/<code>.toml`, then shows one example per state. The Virginia example:

```
run.py clerk add --date <date> --kind "Employer contact" \
  --field "Employer or business name=<company>" \
  --field "Employer address=<street address, city, ST; or city, ST · street address not listed>" \
  --field "Employer email or website=<careers link>" \
  --field "Type of work or position=<title> (<req id>)" \
  --field "Person=<recruiter named, or no one: applied online>" \
  --field "Employer phone or fax=<phone or fax, or phone and fax not listed>" \
  --field "Type of contact=Internet" \
  --field "Result and next step=Applied with a tailored resume; awaiting a response" \
  --field "Source=<posting link> · applications/<the application's folder>" --fit solid
```

Tests:
- New package test: every `--field "<Name>=` in the tailor skill's examples is a field of some state's `Employer contact` kind or one of `EXTRA_FIELDS`. This catches a skill example drifting from the state files.
- New clerk test: `add_entry` with `VA_EMPLOYER_FIELDS` writes a solid entry with the fields in the handbook log's order, then `Source`; dropping `Type of contact` refuses with "Missing fields: Type of contact".

### 3. The entry heading knows Virginia's position field (one line)

`perkins/clerk.py:448-450` builds the heading from `Employer or business name`, `Job title or reference number`, and `What activity`. A Virginia employer contact would read "Activity 1: Kestrel Energy" with no position. Add `Type of work or position` to that tuple.

Test: a Virginia employer contact's heading is "Activity 1: Kestrel Energy · Operations Manager (KE-7)"; a Virginia workforce center activity's heading is its `What activity`.

### 4. The log-activity skill names Virginia's kinds (text only)

`skills/log-activity/SKILL.md:33` offers "a job-center activity (WorkSource in Washington), or another approved activity". Change it to: pick a kind the state file lists (in Washington, WorkSource activities and other approved activities; in Virginia, workforce center activities); if the activity fits no listed kind (a Virginia job fair, for example), it goes in the tracker only, and say so. `clerk add` already refuses an unknown kind and lists the state's kinds (`perkins/clerk.py:407-412`).

Test: add a Virginia case to the existing unknown-kind refusal (`--kind "Other approved activity"` refuses and lists Virginia's two kinds).

### 5. Docs

`docs/state-rules.md`: insert after the Washington section, before "Adding a state":

```markdown
## Virginia (`states/va.toml`)

From the Virginia Employment Commission (VEC), the Code of Virginia, and the Virginia Administrative Code, last checked 2026-11-06. Guidance only: VEC's rules win, and they're yours to meet (see the top of this page).

- Two work search activities for every week you file a weekly claim, unless VEC tells you otherwise.
- They have to happen inside that week, Sunday through Saturday.
- VEC's handbook counts applying for a job that fits your skills, interviewing, and taking part in reemployment services at a workforce center. VEC's benefits roadmap asks for contacts with at least two different employers. Perkins marks a workforce center activity as potentially counts.
- Apply only for work you're qualified for and would take, at pay you'd accept, in an area you'd work in. Looking at job leads without applying doesn't count, and neither does skipping the way an employer asks you to apply.
- Don't repeat a contact with the same employer unless it's for a different job opening.
- In-person and phone contacts should be with someone at the company who can hire.
- For each activity, write down what, when, where, and with whom, and save a screenshot or confirmation email when you can.
- Fully register with the Virginia Workforce Connection, resume included, within 10 days of filing your claim. If you live outside Virginia, register with your own state's workforce agency and send VEC proof within 10 days.
- Online filers enter their work search with each weekly claim. Phone filers give basic details by phone and send VEC's Work Search Record form every four weeks.
- File the weekly claim on Sunday, or as soon as you can, for the week that just ended. After Monday, payment is delayed. A weekly claim filed 21 or more days after the week ended (the first weekly claim: 21 or more days after you applied) is late and in most cases isn't paid.
- Your first eligible week is an unpaid waiting week, and it still needs its two activities.
- VEC's rule: keep your work-search records at least one year following your benefit year begin date. Perkins's advice, to be safe: keep the whole log at least one year past the last week you claim, and until any VEC review or appeal is finished.
- Every contact can be checked, and reporting a search you didn't make is fraud.

Some people have a different requirement: union members who get work through an approved hiring hall, people in VEC-approved training, people on a temporary layoff with a set return date, and people in an area VEC has marked as high unemployment (one contact a week, or none). VEC tells you if one applies.

Sources: [VEC benefit rights and responsibilities](https://www.vec.virginia.gov/your-unemployment-benefit-rights-and-responsibilities), [VEC benefits eligibility](https://www.vec.virginia.gov/benefits-eligibility), the [VEC benefits roadmap](https://www.vec.virginia.gov/unemployed/benefits-roadmap), [VEC weekly certification](https://www.vec.virginia.gov/certify-weekly-benefits), the [VEC unemployment FAQ](https://www.vec.virginia.gov/faqs?category=unemployment), the [VEC Claimant Handbook](https://www.vec.virginia.gov/sites/default/files/documents/VEC%20Claimant%20Handbook%20updated%2012.11.23.pdf) (PDF), VEC's [Sample Work Search Log](https://www.vec.virginia.gov/sites/default/files/Sample-Work-Search-Log.xlsx) (Excel), [Code of Virginia § 60.2-612](https://law.lis.virginia.gov/vacode/title60.2/chapter6/section60.2-612/), and [16VAC5-60-10](https://law.lis.virginia.gov/admincode/title16/agency5/chapter60/section10/).

### What each entry records

The fields of the sample log in VEC's handbook, in its order, plus Source and the grade.

| Activity kind | Fields |
|---|---|
| Employer contact | Contact date, Kind, Employer or business name, Employer address, Employer email or website, Type of work or position, Person, Employer phone or fax, Type of contact, Result and next step |
| Workforce center activity (potentially counts) | Contact date, Kind, What activity, Office name and city, Person |

**Employer address** counts as filled with at least the city and state, naming what the posting didn't give ("street address not listed"). Between **Employer email or website** and **Employer phone or fax**, at least one gives VEC a way to verify the contact; the other names what wasn't given. **Person** is the first and last name of the person you dealt with, or "no one: applied online" for an online application with nobody named. **Type of contact** is phone, mail, internet, or in person. A field is marked missing only when there's nothing true to write. These are Perkins's working rules, because postings rarely give a street address or a name.

Never write your Social Security number, claimant ID, PIN, or VEC login into the log.
```

10243 and 10244 each add a sentence to this section when they land.

Also: `README.md:43` changes "Washington today" to "Washington and Virginia today"; `CHANGELOG.md` gets `[Unreleased]` lines.

### Not changing

- **The count's wording.** VEC's web pages say "job contacts" and its handbook "work search activities"; Perkins's "approved activities" (`perkins/clerk.py:195-196`, `perkins/claim_log.py:342-343`) is close enough to the handbook. No new key.
- **Phone filers' four-week form.** A rules line only. Perkins can't fill VEC's paper form, and the form's fields aren't published.
- **Evidence.** The handbook's "save a screenshot or confirmation email" is what `log/evidence/` already holds.

## Size

Estimated diff: about 350 to 450 lines across about 10 files: the state file, two skills, one clerk line, the docs, and tests. Under the 800-line / 30-file limit on one automated build.

## What I couldn't source

Left out of the draft, or flagged in it, rather than guessed:

- **The Work Search Record form phone filers send.** VEC provides it to claimants; it isn't on the public pages, it isn't in the handbook, and it isn't in the 16VAC5-60 forms list. The forms list does include "Verification of Work Search Revised, VEC-B-36", which is VEC's verification letter, not the claimant's record. [Forms]
- **What the online weekly claim asks per contact.** That's inside Customer Self Service, behind a sign-in. Never signed in. The handbook says only that it asks for "details about your work search efforts." [Handbook, p. 11]
- **Which version of "what counts" VEC applies.** The handbook counts workforce center reemployment services; the roadmap asks for two different employers. The draft grades those activities yellow rather than resolving it.
- **Whether job fairs, hiring events, and networking count.** Only the handbook's template image lists them. Left out (maintainer, question 3).
- **The handbook's date.** The cover says "Revised March 2023"; the link's file name says "updated 12.11.23". The web pages may be newer, and where they differ the spec shows both.
- **Whether a different opening at the same employer counts toward the two.** Graded yellow (10243).
- **Which areas, if any, currently have an adjusted requirement** under 16VAC5-60-10 H. Not published on the pages I read. 10244 records one only when VEC tells the person.
- **What a union hiring-hall entry needs.** VEC says "you will be advised what to submit." [FAQ] The handbook doesn't say either.
- **Fields for a workforce center activity.** None published. The draft's fields come from the handbook's "what, when, where, and with whom".
- **Blind ads.** A search result attributed a "blind ads don't count" rule to an older VEC PDF. Neither the handbook nor the web pages say it, and I didn't read that PDF, so it's not in the draft.
- **The 21-day versus 20-day conflict.** The regulation, the eligibility page, the rights page, the certification page, and the handbook say 21. One FAQ line says 20. The draft follows the regulation. Day 21 itself is ambiguous: the regulation, the eligibility page's example (a week ending February 1 is due by February 22), and the handbook ("more than 21 days") allow it, while the rights page calls 21 or more days late. The rules line and 10243 use the rights page's stricter wording.
- **Washington's late-filing rule.** Not researched, so Washington gets no file-by date yet. Its own backlog item now (maintainer, 2026-11-06).

## Relationships

- **Depends on** 10242: the workforce center kind's `counts = "maybe"`, and the guidance headline this spec's tests check for Virginia.
- **Followed by** 10243 (adds three keys to `states/va.toml` and reuses this spec's Virginia test helpers) and 10244 (cites this spec's exemptions research).
- **Builds on** the 0.1.0 state-file design (`states/README.md`): no new required keys, so Washington's file and the loader's refusal rule are untouched.
- **Changes Washington** not at all.
- **Contradicts** nothing found.

## Permissions

N/A for the product: user-invoked, runs in the user's own session. No new command. Building this needs no credentials. Rechecking the sources on build day is read-only; the handbook and the sample log are file downloads, which need the maintainer's OK again. The spec numbers were allocated through the house registry's own tool (`emily_guard.py specnum`), at the maintainer's direction.

## Acceptance

- `python run.py states` lists `va  Virginia (VEC): 2 activities a week, rules checked <date>`.
- Setup with `--state va` creates a claims folder, raises `weekly_target` to 2, opens Sunday-to-Saturday week files named for Saturdays, and tells the user the guidance-only headline once.
- The claim reminder for a week appears on the Sunday after it; the midweek check appears Wednesday and is raised Friday.
- A Virginia application recorded through the tailor skill writes a solid entry with VEC's fields in the handbook log's order, without the agent having to recover from a refusal.
- A Virginia workforce center activity is written yellow (potentially counts) with its reason; a job fair goes to the tracker only.
- The claim log page, the dashboard, and `status` carry the one-line guidance wording with "VEC".
- Every Washington test passes.
- Every value in `states/va.toml` traces to a source listed in it, rechecked on build day, with `last_checked` set to that day.
- `python -m pytest tests -q` and `python run.py pii-check . --history` pass.
- No `VERSION` change. Installed copies get Virginia only when `VERSION` changes (`CLAUDE.md`, versioning rule); the maintainer cuts 0.3.0 once the parts they want have merged.

## Open questions

Answered 2026-11-06 (kept for the record):

1. ~~**Downloads.**~~ *Maintainer: answered (yes).* Both read and folded in. The Excel log turned out to be the shortest of VEC's four field lists, so the draft follows the handbook's sample log.
2. ~~**Workforce center activities.**~~ *Maintainer: add a yellow category, solid green and potentially counts yellow; useful in Washington too, for conversations that might count, where the user then makes sure of another green that week.* 10242; Virginia's workforce center kind is always yellow.
3. ~~**Job fairs and the union hall.**~~ *Maintainer: leave out for now.*
4. ~~**Working rules for blank fields.**~~ *Maintainer: yes, as proposed.* In `contact_rule`.
5. ~~**Same employer, different opening.**~~ *Maintainer: yellow.* 10243.
6. ~~**Registration reminder.**~~ *Maintainer: add one-time reminders.* 10243.
7. ~~**Retention wording.**~~ *Maintainer: add a conservative note.* In `retention`, labeled as Perkins's advice.
8. ~~**Spec number.**~~ *Maintainer: allocate from the central spec definitions.* Allocated 10241, then 10242 to 10244 for the split.
9. ~~**Exemptions.**~~ *Maintainer: fold it in.* 10244.
10. ~~**Filing deadline.**~~ *Maintainer: yes.* 10243.
11. ~~**Check's color.**~~ *Maintainer: yes, red check.* 10242 moves check from amber to the red-orange warn colors, so yellow means only "potentially counts".

Questions 12 (same employer, same opening) and 13 (Washington's file-by date) moved to 10243 as its open questions 1 and 2; the maintainer answered both as proposed on 2026-11-06 (a likely repeat is check; ESD's late-filing rule is its own backlog item). None open here.
