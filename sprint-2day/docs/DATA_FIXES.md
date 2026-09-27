# Mock-data review: bugs found and fixed

The mock data in `data/` and `eval/` was reviewed on 2026-09-22 during an AI-assisted design review, before any code existed. This file records what was wrong, why it mattered, what changed, and how each fix was checked.

**Honesty note for the interview.** These bugs were found by the review, not by the learner's code. Don't present them as your own debugging stories. What you *can* claim is that your tools and evaluation reproduce the correct values below. Bugs your own code catches later belong in [the learning log](../learning/LOG.md).

| ID | File(s) | Problem | Fix | Status |
|---|---|---|---|---|
| D1 | `hris/leave_requests.csv` | `LR1002` stores 5 days for an Egypt employee over 5–9 Oct. Egypt's weekend is Friday–Saturday, and Armed Forces Day falls in that week. The data had no weekend model or holiday calendar, so no tool could compute working days correctly. | Added `hris/countries.csv` (weekend days per country) and `hris/holidays.csv` (2026 company calendar for Egypt and Germany). Set `LR1002.days` to 3. | fixed |
| D2 | `policies/leave_policy.md` §2.1, `hris/leave_balances.csv` | `E003` passed 5 years of service on 2026-09-01 but shows 21 days, not 25. The policy never says *when* the 25-day tier starts. | Clarified §2.1: the tier is based on service completed on 1 January of the leave year. `E003` = 21 in 2026 is then correct, rising to 25 in 2027. Policy version 3.1 → 3.2. | fixed |
| D3 | `hris/leave_balances.csv` | `E007` (joined 2026-07-01) shows 5.25. That is leave accrued *to a date*, while every other row holds a full-year entitlement, so the column mixed two meanings. | Set it to 10.5 (1.75 × 6 months of 2026). Accrual-to-date is computed by tools: 1.75 per completed month. | fixed |
| D4 | `hris/leave_balances.csv` | `carried_over` days expire on 31 March (§2.3), but the data couldn't say whether they had been used, so any "available" figure was ambiguous. | Added `carried_over_used`. Unused carry-over is forfeited after 31 March. `annual_used` counts only days drawn from the current year's entitlement. | fixed |
| D5 | `hris/employees.csv` | `E010` is part-time with 12.6 days (21 × 0.6), but no field recorded the 0.6, so pro-rating couldn't be reproduced. | Added an `fte` column: 1.0 for everyone except `E010` (0.6). | fixed |
| D6 | `eval/golden_policy_qa.jsonl` | `q05`'s must-contain `"2"` passes on any answer containing "12" or "2026", so it tests nothing. Numeral-only strings fail correct answers that spell numbers out ("four weeks"). `q15` required one exact phrase. | `must_contain` items may now be lists of acceptable alternatives (any one matches). Fixed q04–q10, q13–q15. Added `must_not_contain` to `a01`. | fixed |
| D7 | `data/README.md`, eval | Citations were written `leave_policy §2.3` in the README but `leave_policy#2.1` in the eval. | Standardised ids to `<doc_id>#<section_id>`. `§` is for display only. Documented how section ids derive from headings. | fixed |
| D8 | `resumes/`, `eval/screening_expectations.json` | The counterfactual pair `cand_06` / `cand_07` changes the name, the pronouns *and* the implied ethnicity at once, so a score gap can't be attributed to any one of them. | Added `cand_09`: `cand_07`'s name with `cand_06`'s pronouns. Now 06 vs 09 differ only by name, and 07 vs 09 only by pronouns (contact details differ, and are redacted before screening). Checks updated. | fixed |
| D9 | `resumes/cand_05.md`, eval | The injection sits in an HTML comment. A loader that renders markdown to text drops it, and the injection test then passes without testing anything. | Added a precondition to the check: the text sent to the extractor must contain the injected sentence. Documented raw-text loading. | fixed |
| D10 | `data/README.md` | Said 8 CVs and referenced `scripts/seed_db.py` without noting it doesn't exist yet. | Updated the counts, file list and milestone reference. | fixed |
| D11 | `jobs/junior_ai_engineer_jd.md`, `jobs/junior_ai_engineer_rubric.json` | R6 bundled Git, Docker and cloud into one scored item, so a CV with Git but no Docker had no clear level. No requirement had scoring anchors ("solid Python"). Nothing mapped a score to the tiers the eval tests. Nothing told the screener to ignore degree, years, gaps or family status. The JD had no responsibilities, hiring process or equal-opportunity statement. | Split R6 into R6 Git, R7 Docker and N2 cloud (total weight 17). Added `yes` / `partial` anchors that reward demonstrated depth, not employment context (so career breaks aren't penalised). Added tier thresholds (strong ≥ 70, medium ≥ 40), an evidence rule and an `excluded_from_scoring` list. Rewrote the JD with responsibilities, an AI-assisted and human-reviewed hiring process, and an equal-opportunity statement. It's a realistic composite, not a real posting. | fixed |

**Verification (2026-09-22).** All eleven fixes were checked by a read-only script kept outside the repo. Results:
- every entitlement follows the §2.1 rule, including `fte` and first-year pro-rating;
- both leave requests match the computed working days (4 and 3);
- every golden-set citation id resolves to a policy heading;
- every `must_contain` item can be satisfied from its expected sections;
- the counterfactual CVs differ in exactly the intended line;
- under the new rubric, a reviewer's hand scoring of all 9 CVs lands every one in its expected tier, even when borderline judgments go either way (tightest: `cand_02` at 44.1 against the 40 threshold).

The script is deliberately not committed: the working-day logic is the learner's to write in M7.

## D1 detail: the October holiday

Armed Forces Day is **Tuesday 6 October 2026**. Egypt moves mid-week holidays to Thursday for long weekends; in 2026 the pattern shows Jan 25 → Jan 29, May 1 → May 7 and June 30 → July 2. Published calendars disagree about October:
- one reports the day off as **Thursday 8 October**;
- another lists **Friday 9 October**, which is already a weekend day in Egypt and looks like an error.

The company calendar uses **Thursday 8 October**. With it, 5–9 October has three working days: Sunday–Thursday is the working week, 8 October is the holiday and 9 October is a Friday.

If you use real data, verify against the Cabinet decree. `holidays.csv` is the fictional company's published calendar, and the data's source of truth.

Islamic holiday dates depend on moon sighting and can move a day or two. Coptic Easter Sunday is left out: it is a Sunday, which is a working day in Egypt, and in practice it's observed by Christian employees rather than as a general day off. German entries are nationwide holidays only; state holidays (for example Corpus Christi) vary.

Sources: [Office Holidays: Egypt 2026](https://www.officeholidays.com/countries/egypt/2026) · [Office Holidays: Armed Forces Day](https://www.officeholidays.com/holidays/egypt/egypt-armed-forces-day) · [Wikipedia: Public holidays in Egypt](https://en.wikipedia.org/wiki/Public_holidays_in_Egypt)

## Rules the tools must implement

These aren't data bugs; they're rules the M7 tools compute from the data:

- **Available annual leave** = `annual_entitlement` (accrued-to-date in the first year) `− annual_used − pending days` (from `leave_requests.csv` with status `pending`). Expired carry-over is never available after 31 March.
- **First-year accrual**: 1.75 days per completed month of service.
- **Probation**: no annual leave in the first 3 months after `hire_date`. `E007`'s probation runs until 2026-09-30.
- **Notice**: at least 10 working days for requests of 3+ days, otherwise at least 2.
- **Working days**: exclude the country's weekend days and its holidays.
- **Overlap**: a new request must not overlap an existing pending or approved request.
- **Today is an input**: rules take the current date as a parameter, so tests are reproducible.
