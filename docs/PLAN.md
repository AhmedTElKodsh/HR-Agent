# HR-Agent plan

**Goal:** be able to defend every stage of the "AI Engineer Technical Interview Mock: HR Policy Assistant Case" two levels deep, with evidence you produced yourself: a number, a failure, a fix.

**Honesty rule:** this is a portfolio replica on fictional data. Never quote the mock's numbers (3,000 employees, a pilot, 45% resolved, $39 to $8). Quote only what is in `docs/results.md`, with its confidence interval and the date you measured it.

## Interview story map

Each row is something an interviewer will drill into, and what you will be able to show for it.

| Mock stage | What you build | Evidence you'll quote | Milestone |
|---|---|---|---|
| Pitch and whiteboard | The two diagrams, drawn from your real system | Your own measured result line | M7 |
| 1 Framing and metrics | Targets and must-nevers in `eval/gates.json` | "I set hard gates before writing features" | M0 (done) |
| 2 Parsing and cleaning | Parsers for digital, two-column and scanned PDFs, DOCX (incl. RTL) and HTML | Extraction accuracy against `data/policies/`; the table-question slice before and after the layout parser | M2 |
| 3 Chunking | 5 strategies compared at a fixed token budget | Hit@5 by strategy; the effect of contextual headers | M2 |
| 4 Embeddings and store | Bake-off of 3+ multilingual models; pgvector with filters | Hit@5 on the `en` and `ar` slices per model; the filtered-search trap test | M2 |
| 5 Retrieval | BM25 (with Arabic normalisation) + RRF + cross-encoder; relevance gate; query rewriting | code_lookup and follow_up slices before and after; refusal accuracy at the chosen threshold | M2 |
| 6 LLM choice | Same eval run on 3+ models | Quality, p95 latency and cost per query table | M2 |
| 7 Generation | Schema output, citation check, conflict handling, SSE streaming | Faithfulness score; conflict slice; citation-failure rate | M2 |
| 8 Tools and agents | Tools, rules engine and confirm endpoint per `docs/agent_tools.md` | 20/20 scenarios over 5 runs; tool-selection accuracy | M3 |
| 9 Security | Role and region filters in SQL (RLS), canary, injection handling, masked logs | Hard gates green: security, abac and must_not_include | M2, M3 |
| 10 Evaluation | Harness, LLM judge validated against your labels, CI smoke gate | Judge kappa; a McNemar comparison you ran | M1 |
| 11 Classic ML | Ticket routing: TF-IDF, SetFit, fine-tuned encoder, LLM | Macro-F1, latency and cost table; the English-to-German shift test | M5 |
| 12 Serving | FastAPI + SSE, Docker, Postgres, CI/CD | A running demo and the pipeline | M6 |
| 13 Observability and cost | Traces from day 1; dashboards; load test | Cost and TTFT before and after each optimisation | M1, M6 |
| 14 Lifecycle | Incremental re-index by hash; blue-green index swap; version filtering | Version slice results; a model or index swap done with evals | M2, M6 |
| War stories | `docs/war_stories.md`, written from real traces | At least 4, each with diagnosis, fix, prevention and result | Every milestone |
| Responsible AI (extra) | Screening with redaction, code-side scoring and a counterfactual suite | Exact equality across 32 variants; injection caught | M4 |

## Milestones and exit criteria

Order matters: the eval harness comes before features, and each feature must beat the baseline to stay.

**M0: Data and evaluation ready (done).**
Exit: `python scripts/validate_data.py` passes.

**M1: Eval harness and the simplest baseline.**
- Harness: runs `golden_rag.jsonl`; reports hit@k, MRR and recall per slice and per language, with confidence intervals; applies the matching rules; grades with an LLM judge.
- Label 60 answers yourself and report judge agreement and kappa.
- Baseline: the simplest parser per format, fixed-size chunks, one embedding model, top-5 vector search, one grounded prompt with citations.
- Tracing from the first request (for example Langfuse or Phoenix). CI runs the smoke set and blocks on the hard gates.
- Exit: baseline row in `docs/results.md`; CI gate working; judge validated.

**M2: RAG depth.** Change one thing per experiment and record each in `docs/results.md`:
1. Parsing: layout-aware extraction for tables and two columns, OCR for the scan, HTML cleaning. Decide what to do with hidden HTML elements, and defend it.
2. Chunking comparison at a fixed token budget, then contextual chunk headers.
3. Metadata filters: effective dates, roles and regions, enforced in SQL. Test that restrictive filters still return k results.
4. Embedding bake-off on the English and Arabic slices.
5. Hybrid search and RRF, then reranking, then the relevance gate threshold tuned on out_of_scope against answerable items.
6. Query rewriting, evaluated against `standalone_query`.
7. Generation: schema, citation verification, conflict answers, streaming.
8. LLM comparison.
9. Incremental re-indexing, then one blue-green index swap (for example a new embedding model).
- Exit: all hard gates green; targets met, or each gap explained; at least 2 war stories logged.

**M3: Agent.**
- Tools and the confirm endpoint per `docs/agent_tools.md`; rules engine reading `data/leave_rules.json`, with a unit test tying each value to the policy clause.
- Exit: all 20 scenarios pass 5 runs in a row; tool-selection accuracy reported.

**M4: Screening (responsible AI).**
- Redact personal data before the LLM (for example Presidio); the LLM extracts evidence quotes; code computes the score; injection detection; the PDF inputs.
- Exit: `screening_expectations.json` passes, and all 32 counterfactual variants score exactly like their base over 5 runs.

**M5: Ticket routing (Stage 11).** Follow `data/tickets/README.md`.
- Exit: comparison table and confusion matrix, plus a one-paragraph "when not to use an LLM" conclusion.

**M6: Serving and operations.**
- FastAPI with SSE streaming, Docker, Postgres + pgvector, CI/CD with the eval gate, dashboards.
- Load test with Locust or k6; measure cost and latency optimisations (fewer chunks, prompt caching, a small model for rewriting); pin model versions; write a runbook.
- Exit: a demo you can run live, and before/after numbers.

**M7: Interview pack.**
- The 60-second pitch rewritten with your numbers; the two diagrams; 4 war stories; one drill-down card per stage ("say it, understand it, why this over the alternative").
- Exit: two timed mock interviews, and the gaps they expose logged as tasks.

## Starting technology candidates

These are the mock's choices, used as the first candidates, **not decisions**. Each one stays only if it wins its comparison on your eval set: Postgres + pgvector, BM25 via `pg_search` or `rank_bm25`, BGE-M3, bge-reranker-v2-m3, FastAPI, Langfuse, pytest.

## Decision log

| # | Decision | Why |
|---|---|---|
| D1 | Keep screening (M4) **and** add ticket routing (M5) | Time isn't constrained. Screening shows responsible-AI testing; routing covers Stage 11, which the mock expects. |
| D2 | Evaluation before features | The mock's method: build the baseline first, and every addition must beat it |
| D3 | The LLM never computes dates, balances, eligibility or scores | These have money or legal effect: code computes them from `leave_rules.json` and the rubric |
| D4 | Writes go through a confirm endpoint, not a model tool | Injected text can't click a button; the draft ID is the idempotency key |
| D5 | A missing required skill caps the band at review | The JD's must-haves matter, but a human decides; no automatic rejection |
| D6 | Never raise overqualified, age, gap or family flags | Flagging a proxy hands the bias to the human reviewer |
| D7 | Ingest mixed formats; keep the Markdown sources as parser ground truth | Parsing quality caps answer quality (Stage 2), so it needs a measurable target |
| D8 | Arabic as the second language | Realistic for a Cairo company, and it exercises multilingual embeddings and Arabic keyword normalisation |
| D9 | Access control lives in the retrieval query (and RLS), never in the prompt | Security must hold even if the model is fully manipulated |
| D10 | A public synthetic ticket dataset for routing, with its limits stated | No real HR tickets exist; the limits (no timestamps, synthetic) are an interview talking point |
| D11 | Use BMAD lightly: a product brief and an architecture doc, then build | Solo portfolio project. BMAD workflows need setup first: the `_bmad/` folder is missing. |

## Working rhythm

- One experiment = one change + an eval run + a row in `docs/results.md`.
- Every failure you find: open the trace, name the layer, fix it there, and add the question to the eval set. If it would make a good story, log it in `docs/war_stories.md`.
- Before each milestone closes, explain its stage out loud in 60 seconds, then answer "why not X?" for your two biggest choices.
