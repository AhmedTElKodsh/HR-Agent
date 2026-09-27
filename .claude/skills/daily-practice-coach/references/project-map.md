# Project map - HR-Agent

Milestones, what each one proves, and how they hand off. The authority is `docs/PLAN.md` in the workspace; this file is the coach's index into it. When they disagree, the workspace wins (SKILL.md, **Precedence**).

## The shape of the project

A bilingual (English / Arabic) HR policy assistant for the fictional **Nilebyte Solutions**, built as interview evidence. Four systems share one eval discipline:

| System | Milestone | Eval file |
|---|---|---|
| Policy RAG (parse → chunk → embed → retrieve → generate) | M1, M2 | `eval/golden_rag.jsonl` (125 items) |
| Leave agent (tools, rules engine, confirm flow) | M3 | `eval/agent_scenarios.jsonl` (20 scenarios) |
| Resume screening (redact → extract → score in code) | M4 | `eval/screening_expectations.json` + `eval/counterfactuals/` (32) |
| Ticket routing (classic ML vs LLM) | M5 | see `data/tickets/README.md` |

Serving and operations (M6) wrap all four; the interview pack (M7) is the deliverable.

## Milestones and exit criteria

| Milestone | Theme | Exit criterion |
|---|---|---|
| **M0** | Data and evaluation ready *(done)* | `python scripts/validate_data.py` passes |
| **M1** | Eval harness + simplest baseline | Baseline row in `docs/results.md`; CI gate working; LLM judge validated against 60 hand labels (kappa ≥ 0.6) |
| **M2** | RAG depth - nine experiments, one change each | All hard gates green; targets met or each gap explained; ≥ 2 war stories logged |
| **M3** | Agent | All 20 scenarios pass 5 runs in a row; tool-selection accuracy reported |
| **M4** | Screening (responsible AI) | `screening_expectations.json` passes; all 32 counterfactuals score **exactly** like their base over 5 runs |
| **M5** | Ticket routing | Comparison table + confusion matrix + a "when not to use an LLM" paragraph |
| **M6** | Serving and operations | A demo runnable live, plus before/after numbers |
| **M7** | Interview pack | Two timed mock interviews; gaps logged as tasks |

## The ordering rule that matters most

> **Evaluation before features** (`docs/PLAN.md` D2).

M1 is not a warm-up. Until the harness runs `golden_rag.jsonl` and reports per-slice metrics with intervals, every later experiment is unmeasurable and every later claim is unquotable. If a learner wants to jump to M2 retrieval work, that is the one place to push back hard — and to say *why*: without a baseline there is nothing for the change to beat.

## Stage → milestone map

The interview has 14 stages. Learners will be drilled per stage, not per milestone, so tie coaching to both.

| Stage | Milestone | The evidence to be able to quote |
|---|---|---|
| 1 Framing and metrics | M0 | "I set hard gates before writing features" (`eval/gates.json`) |
| 2 Parsing and cleaning | M2 | Extraction accuracy vs `data/policies/`; the `table` slice before/after the layout parser |
| 3 Chunking | M2 | Hit@5 by strategy at a **fixed token budget**; effect of contextual headers |
| 4 Embeddings and store | M2 | Hit@5 on `en` and `ar` per model; the filtered-search trap test |
| 5 Retrieval | M2 | `code_lookup` and `follow_up` before/after; refusal accuracy at the chosen threshold |
| 6 LLM choice | M2 | Quality, p95 latency, cost-per-query table |
| 7 Generation | M2 | Faithfulness; the `conflict` slice; citation-failure rate |
| 8 Tools and agents | M3 | 20/20 over 5 runs; tool-selection accuracy |
| 9 Security | M2, M3 | Hard gates green: security, abac, must_not_include |
| 10 Evaluation | M1 | Judge kappa; a McNemar comparison actually run |
| 11 Classic ML | M5 | Macro-F1 / latency / cost table; the English→German shift test |
| 12 Serving | M6 | A running demo and the pipeline |
| 13 Observability and cost | M1, M6 | Cost and TTFT before/after each optimisation |
| 14 Lifecycle | M2, M6 | Version-slice results; a model or index swap done with evals |

## Hand-offs between milestones

Each arrow is a place learners commonly lose evidence. Check it explicitly at the boundary.

- **M1 → M2.** The baseline row must be *in* `docs/results.md` before the first M2 experiment, with the eval-set version. Otherwise M2's "before" number is a memory, not a record.
- **M2 → M3.** `search_policy` is an agent tool but it is the *M2 retrieval stack* behind it, already filtered by role, region and reference date. If M2's filters live in the prompt, M3 inherits a security failure (`D9`).
- **M2 → M4.** The parsing work (two-column PDF, OCR) is reused for `cand_05.pdf` and `cand_08.pdf`. A learner who hand-waved OCR in M2 will hit it again here.
- **M3 → M6.** The confirm endpoint is a real HTTP route, not a tool. It has to survive the move into FastAPI with the draft ID still acting as the idempotency key.
- **M4 → M7.** The counterfactual result (exact equality across 32 variants) is the single strongest responsible-AI claim in the pack. It needs 5 runs, not 1.
- **Every milestone → M7.** A war story is written *from a trace while it is fresh*. Learners who defer them write four vague ones at the end and cannot answer "how did you find it?".

## Slices of `golden_rag.jsonl` and who owns them

Use this to pick which slice a task is allowed to claim.

| Slice | n | Owned by | Common failure |
|---|---|---|---|
| typical | 46 | M1 baseline | — |
| table | 15 | M2 parsing | Column meaning lost; scanned schedule needs OCR |
| follow_up | 11 | M2 query rewriting | "And in Paris?" retrieves nothing standalone |
| security | 10 | M2/M3 | Indirect injection in `employee_faq.html` reaches the prompt |
| out_of_scope | 9 | M2 relevance gate | Threshold tuned on the wrong set |
| abac | 8 | M2 filters | Filter applied in prompt, not query |
| multi_hop | 7 | M2 retrieval | Recall, not hit@k, is the metric here |
| tool_route | 7 | M3 | Personal-data question answered from search |
| version | 6 | M2 metadata | 2025 PDF outranks 2026 on carry-over |
| code_lookup | 4 | M2 hybrid search | Pure vector search misses `HR-EX-03` |
| conflict | 2 | M2 generation | Answer picks a side instead of showing both |

## Bridge tasks

A bridge task teaches a prerequisite skill rather than advancing a milestone. They carry `"bridge": true` in `tasks/catalog.json` and are the only tasks a placement result may waive. Current bridges cover: pytest fixtures and parametrisation, Arabic text normalisation, SQL window functions for pgvector filtering, and reading a trace.
