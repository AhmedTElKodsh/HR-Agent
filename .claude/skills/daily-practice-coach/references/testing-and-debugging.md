# Testing and debugging

## Debugging procedure

Follow the order. The discipline is that **the repeatable check comes before the hypothesis**, and the hypothesis comes before the fix.

### 1. Build a repeatable failing check

Not "it sometimes returns the wrong chunk" — a command that fails every time.

```bash
pytest tests/test_retrieval.py::test_q76_uses_2026_policy -x
```

If it cannot be made repeatable, that *is* the bug: find the nondeterminism first. Usual suspects in this project: an unpinned model version, a clock that isn't `reference_today = 2026-09-24`, dict ordering feeding a tie-break, a temperature above 0 in an eval run, a vector index rebuilt between runs.

### 2. Ask the learner for their hypothesis first

Always. Then add a ranked list of your own, with the cheapest discriminating test for each. Ranking matters more than completeness — three ordered hypotheses beat eight unordered ones.

### 3. Test one prediction at a time

State the prediction before running: "If it's the chunker, then `len(chunks)` for `leave_policy` is 1 and the section header is gone." Run. Compare. Do not change two things.

### 4. Name the layer

Every fix belongs to exactly one layer. Naming it is the part interviewers grade.

| Layer | You are here when… | Typical fix |
|---|---|---|
| **Document** | The source itself is wrong, superseded or ambiguous | Metadata, effective dates, a `status` change — not code |
| **Parsing** | The text never came out right | Layout-aware extraction, OCR, HTML cleaning |
| **Chunking** | The text is right but split badly | Boundaries, overlap, contextual headers |
| **Retrieval** | The right chunk exists but wasn't fetched | Hybrid search, filters, query rewriting |
| **Ranking** | It was fetched but ranked below the cut | RRF weights, reranker, relevance gate threshold |
| **Generation** | The right chunks were in context and the answer is still wrong | Prompt, schema, citation verification, conflict handling |
| **Tools** | The model chose or called wrong | Tool descriptions, argument validation, loop guards |
| **Operations** | Timeouts, retries, cost, cold starts | Normalised errors, caching, pinning |

Fixing a retrieval problem in the prompt is the single most common mistake in this project, and `D9` makes it a security failure when it involves access control.

### 5. Minimal fix, then regression test

Smallest change that turns the check green. Then make the silent regression impossible: add the question to `golden_rag.jsonl`, or the scenario to `agent_scenarios.jsonl`, or a unit test tying a rules-engine value to its policy clause.

### 6. Autopsy (non-trivial bugs only)

Five lines, matching the `docs/war_stories.md` template:

- what happened and the impact
- how the cause was found — *trace evidence, not a guess*
- the fix and the layer it belongs to
- how a silent regression was made impossible
- the measured result, before and after, from `docs/results.md`

If it reads like a good story, it goes in `docs/war_stories.md` now, not at M7. The trace is fresh exactly once.

## Test plan shape (Test-first mode)

For each unit of work, four cases before any implementation:

| Case | Question it answers |
|---|---|
| Smallest passing | What does success minimally look like? |
| Smallest failing | What does the error path do? |
| Boundary | Empty, one, many, max — and for this project: zero retrieved chunks, a filter that excludes everything, a leave request spanning a holiday |
| Ambiguous | A case where the spec doesn't say. The learner decides, writes the decision down, and the test encodes it |

## Seams in this project

What to fake, and what must stay real:

| Thing | In unit tests | In eval runs |
|---|---|---|
| Model provider | Fake, deterministic | Real, temperature 0, version pinned |
| Vector store | In-memory | Postgres + pgvector |
| HR system | `hris_seed.json` | `hris_seed.json` |
| Clock | Pinned to `reference_today` = 2026-09-24 | Same |
| Embeddings | Precomputed fixtures | Real model |
| Judge | Not used | Real, validated (kappa ≥ 0.6) |

Pinning the clock is not optional: probation for `E1004` ends 2026-11-17, the Finance blackout covers 24 and 27-30 Sep 2026, and 2026-10-06 is a holiday. A floating `today` makes every agent test rot.

## Eval-specific testing rules

- **Never tune on the holdout.** `gates.json` lists 25 held-out IDs. They run before a release only. A learner who looks at them has burned them, and the honest move is to say so and treat the set as spent.
- **The smoke set runs on every PR** — 40 IDs including every security, abac, version and conflict item.
- **Hard gates are pass/fail, not scores.** A run that improves hit@5 and leaks the canary is a failing run.
- **Compare on the same questions.** Report flips, not just averages, and use McNemar (p < 0.05 per `gates.json`).
- **Report per slice.** An average that rises while `abac` falls is a regression wearing a disguise.
- **Reuse the matching functions** from `scripts/validate_data.py` for `must_include` / `must_not_include`. Reimplementing the normalisation rules (lower-case, Arabic-Indic digits, thousands separators, whole-number matching) guarantees the harness and the validator disagree eventually.

## When a test is the wrong tool

Some claims in this project cannot be unit-tested and need a different form of evidence:

- *"The answer is faithful"* → LLM judge, validated against 60 hand labels.
- *"Latency is acceptable"* → load test with p50/p95, not a single timing.
- *"The parser is accurate"* → measured against `data/policies/` as ground truth, reported as a percentage with n.
- *"The system is fair"* → the 32 counterfactuals scoring **exactly** equal over 5 runs. Not "close". Exactly.
