# Resources

Curated, and cited when the coach explains something. Prefer the official page over a blog post; prefer a blog post you have read over one you have not.

**Rule:** the coach cites from here or from official docs, not from memory. Anything version-sensitive gets checked against the current docs at the time of use, or is labelled unverified.

## Evaluation and statistics

- [ ] Cohen's kappa — definition and interpretation bands
- [ ] McNemar's test — when it applies, and why paired comparison beats two averages
- [ ] Confidence intervals for proportions (Wilson interval)
- [ ] A reference on building golden sets and avoiding holdout leakage

## Parsing

- [ ] The PDF library chosen (layout mode, table extraction)
- [ ] The OCR engine chosen (languages, confidence output)
- [ ] `python-docx` — styles, tables, RTL
- [ ] HTML parsing and boilerplate removal

## Chunking, embeddings and retrieval

- [ ] Tokenizer docs for the embedding model, for fixed token budgets
- [ ] The embedding models in the bake-off — context length, languages, licence
- [ ] pgvector — index types, distance operators, filtering behaviour
- [ ] BM25 implementation chosen
- [ ] Reciprocal Rank Fusion — the original description
- [ ] The cross-encoder reranker chosen
- [ ] Arabic text normalisation reference

## Generation

- [ ] Provider docs for structured output / JSON schema
- [ ] Server-Sent Events, and the framework's streaming support
- [ ] Prompt-injection guidance from a source you trust

## Agent

- [ ] Pydantic — validation, error shapes
- [ ] FastAPI — dependencies, background tasks, streaming responses
- [ ] The tracing tool chosen — spans, masking

## Classic ML (M5)

- [ ] scikit-learn — TF-IDF, linear models, `classification_report`
- [ ] SetFit
- [ ] The fine-tuning approach chosen
- [ ] Safe model loading (why not to `pickle.load` untrusted artifacts)

## Responsible AI (M4)

- [ ] The redaction library chosen (Presidio or similar) — recognisers and recall
- [ ] Counterfactual fairness — a definition you can quote

## Operations (M6)

- [ ] Docker and Compose
- [ ] Postgres row-level security
- [ ] Locust or k6
- [ ] The dashboard tool chosen

## In-repo documents (read these first)

- `docs/PLAN.md` — milestones, exit criteria, decision log
- `eval/README.md` — slices, matching rules, statistics
- `docs/agent_tools.md` — tool contract and the confirm flow
- `data/README.md` — corpus formats and the planted test cases
- `docs/results.md` — the only numbers quotable
- `docs/war_stories.md` — the template and the stories the data will produce
