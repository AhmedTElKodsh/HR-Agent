# Glossary

Terms in the learner's own words. The coach adds a term when it introduces one, and reuses these phrasings when re-explaining. Keep definitions short and grounded in this project.

| Term | In my words | Where it shows up here |
|---|---|---|
| Hit@k | | `eval/README.md`, retrieval scoring |
| MRR | | Retrieval scoring |
| Recall@k | | `multi_hop` slice |
| Slice | | The 11 slices in `eval/README.md` |
| Hard gate | | `eval/gates.json` |
| Holdout set | | `eval/gates.json`, never tuned on |
| McNemar's test | | Comparing two versions on the same questions |
| Cohen's kappa | | Validating the LLM judge |
| ABAC | | `abac` slice; role and region filters |
| RLS | | Access control in Postgres |
| RRF | | Fusing BM25 and vector results |
| Cross-encoder | | Reranking |
| Relevance gate | | Refusing out-of-scope questions |
| Contextual chunk header | | Chunking experiments |
| Indirect prompt injection | | `employee_faq.html` |
| Canary token | | `CANARY-7f3a` |
| Counterfactual fairness | | `eval/counterfactuals/` |
| Idempotency key | | The draft ID in the confirm flow |
| Blue-green index | | Swapping embedding models |
| TTFT | | Time to first token, p95 target 2 s |
