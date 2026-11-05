# State rules

Claims tracking follows one state's work-search rules, kept in a small file in the plugin's `states/` folder. Each file lists the agency's own source pages and the date they were last checked.

**This is not legal advice.** The state agency's site is the authority. If anything here disagrees with it, the agency wins: tell us so the file can be fixed.

## Washington (`states/wa.toml`)

From the Employment Security Department (ESD), last checked 2026-10-16:

- Three approved activities for every week you file a weekly claim, in any mix of employer contacts, WorkSource activities, and other approved activities.
- They have to happen inside that week, Sunday through Saturday. Nothing carries over.
- The exact same activity can't count twice. Similar ones can, such as applications to two different jobs at the same company.
- An employer contact means asking an employer about a job, applying, or interviewing. It doesn't count if you already know they aren't hiring.
- ESD can ask for your log at any time, even after the claim ends. Keep it at least 30 days past the end of your benefit year, or past your last extension payment, whichever is later.
- False information is fraud. A short week is a conversation with ESD, not a stretched log.

Sources: [ESD job search requirements](https://esd.wa.gov/job-search), the [ESD job search log](https://esd.wa.gov/job-search-log), and [WAC 192-180-010](https://app.leg.wa.gov/wac/default.aspx?cite=192-180-010).

### What each entry records

The fields ESD's log form asks for, in its order, plus three that make an entry hold up if ESD asks (Person, Result and next step, Source) and the fit grade.

| Activity kind | Fields |
|---|---|
| Employer contact | Contact date, Kind, Job title or reference number, Employer or business name, How, Type, Employer contact info |
| WorkSource activity | Contact date, Kind, What activity, What documentation, Office name and city |
| Other approved activity | Contact date, Kind, What activity, What documentation |

**Employer contact info** counts as filled when it has the city and state plus at least one way ESD could verify the contact: a website, an email, or a phone. Name what the posting didn't give ("phone not listed"). It's marked missing only when there's no way to verify the contact at all. This is Perkins's working rule, because postings rarely list a phone or street address.

Never write your Social Security number, claimant ID, or ESD login into the log. Fill in the form's ID box on paper if ESD asks for your log.

## Adding a state

Copy `states/_template.toml` to `states/<two-letter code>.toml` and fill it in from that agency's own pages only: the number of activities, the claim week's days, the claim filing day, the log form's fields in order, retention, every source link, and the date you checked. Leave out anything you can't source rather than guess. Then open a pull request with the sources. See `states/README.md`.
