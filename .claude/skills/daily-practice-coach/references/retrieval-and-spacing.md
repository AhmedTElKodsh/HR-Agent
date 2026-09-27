# Retrieval and spacing

How review prompts are created, graded and rescheduled. The state lives in `learning/review.json`; the schema is in [progress-protocol](progress-protocol.md).

## Why this exists

Rereading and watching code get written both feel like learning and mostly are not. Effortful recall — producing the answer from memory, late enough that it is hard — is what makes a learner able to answer "why this over the alternative?" under interview pressure two months later.

The cost is that it feels worse than rereading at the time. Say that out loud once, early, so the learner doesn't read the difficulty as failure.

## Writing a good review prompt

At the end of a working session, create **one or two** prompts from what was actually built. Not from the curriculum — from the session.

A good prompt:

- **Asks for production, not recognition.** "What does RRF do?" is weak. "You have BM25 and vector results for `q102`. Write the RRF formula and say what `k` controls." is strong.
- **Is answerable in under two minutes.**
- **Has a checkable answer** recorded with it, so grading isn't a judgement call at 7am.
- **Is grounded in this project.** Reference a real question ID, a real candidate, a real policy clause. Generic prompts decay into trivia.
- **Targets a decision, not a fact, wherever possible.** "Why is the access filter in the query instead of the prompt?" outranks "what does D9 say?".

Good sources for prompts: a bug just fixed, a decision just made, a number just measured, a library just adopted (the seven questions make excellent prompts), a tradeoff the learner hesitated on.

## Grading

Three grades. Keep the scale coarse — a finer one invites deliberation that the learner should be spending on the next prompt.

| Grade | Meaning | Recorded as |
|---|---|---|
| **pass** | Produced the substance unaided, reasonably promptly | `pass` |
| **partial** | Got there with a nudge, or produced part of it, or took a long time | `partial` |
| **fail** | Could not produce it, or produced something wrong | `fail` |

Rules:

- Grade the **first** attempt. A correct answer after being told the answer is a `fail`, and recording it as anything else destroys the schedule's usefulness.
- A learner may decline a warm-up entirely. That is not a grade and changes nothing.
- **A failed retrieval is scheduled again for tomorrow** (SKILL.md, *Learning practices*). This overrides whatever the interval function would otherwise return.

## The schedule contract

`coach.py review grade` computes the next due date through `_next_interval(grade, streak, previous_interval)`. Whatever curve is used must satisfy these, because the rest of the system depends on them:

1. **A `fail` returns to 1 day**, and resets the streak to 0. (SKILL.md requires tomorrow; the function must not contradict it.)
2. **A `pass` strictly increases the interval.** An item that never gets further apart is a chore, not a schedule.
3. **A `partial` does not increase the interval**, and does not reset it to 1 either — it holds roughly where it is.
4. **Intervals are integer days ≥ 1**, and capped (a 400-day interval inside a project measured in weeks is the same as deleting the item).
5. **It is pure and deterministic** — same inputs, same output — so the tests can pin it and the learner can predict it.

The growth curve *between* those constraints is a real design decision: aggressive growth covers more material but risks forgetting before the next look; gentle growth retains better but spends more of each session on review. It is implemented in `scripts/coach.py`.

## Daily flow

1. `coach.py review due --project PATH` → items with `due <= today`.
2. Offer **one or two**, never the whole backlog. A 14-item warm-up is how spaced repetition dies.
3. Reveal the recorded answer only after the learner answers or passes.
4. `coach.py review grade --id <review_id> --grade pass|partial|fail`.
5. If two or more items are overdue, SKILL.md makes review an *offer before new material* — still an offer, and still declinable.

## Mixed practice

Where you have a choice, interleave. Two retrieval prompts back to back are easier and teach less than one retrieval prompt, one screening prompt and one agent prompt. Interleaving forces the learner to first work out *which* kind of problem this is — which is exactly the skill an interviewer tests when they jump between stages.

## Interaction with difficulty adaptation

The review record feeds the rules in SKILL.md, *Learning practices*:

- Three consecutive tasks at `hint_level ≤ 1` → offer a Stretch.
- Two `--struggle` entries on one task → offer a prerequisite mini-lesson or a kata.
- A `fail` → due tomorrow.

Note the coupling: a `strict_mode` bypass is recorded as hint level 3, so a learner who routinely says "just tell me" will not be offered Stretches. That is intentional and worth explaining if they ask why the work stopped getting harder.

## Katas

When nothing is due but a warm-up is wanted, a kata is a 5-minute reimplementation of something small and already understood. Good ones here:

- Normalise an Arabic string (Arabic-Indic digits → ASCII, strip tatweel, unify alef forms) and match `"٥ أيام"` against `must_include: ["5"]`.
- Compute working days between two dates, excluding Friday, Saturday and the 2026 holiday list.
- Write RRF over two ranked lists from memory.
- Given three chunks and a question, write the citation-verification check.
- Score one criterion from `junior_data_analyst_rubric.json` in code, given an evidence quote.
