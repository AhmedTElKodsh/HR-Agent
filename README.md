# HR-Agent

A portfolio replica of the HR policy assistant from the "AI Engineer Technical Interview Mock". It uses fictional data (Nilebyte Solutions) and exists to produce first-hand evidence for every interview stage.

This is the full version. An earlier, compact edition, planned as a ~16-hour build for a two-day interview scenario, lives in [`sprint-2day/`](sprint-2day/README.md). It uses its own fictional company and data, and its README explains how the two differ.

| Start here | What it is |
|---|---|
| `docs/PLAN.md` | Interview story map, milestones M0–M7 with exit criteria, and the decision log |
| `docs/agent_tools.md` | Tool contract for the agent: identity, the confirm flow, violations |
| `docs/results.md` | The only numbers you may quote |
| `docs/war_stories.md` | Failures you found, written from traces |
| `data/README.md` | The corpus, its formats and the test cases built into it |
| `eval/README.md` | Eval files, slices, matching rules and statistics |
| `sprint-2day/` | The earlier compact edition, scoped for a two-day interview sprint (frozen, reference only) |

```bash
pip install -r scripts/requirements-data.txt
python scripts/build_corpus.py          # render data/policies/ into data/corpus/ (PDF, DOCX, scan, HTML)
python scripts/make_counterfactuals.py  # regenerate the fairness suite
python scripts/validate_data.py         # check that everything is consistent
```

The ticket-routing dataset (milestone M5) is public and licensed CC BY-NC 4.0 (see `data/tickets/README.md`). Credit its author if you publish results.

A private, local-only copy of the interview mock this project replicates is kept at `docs/private/` (git-ignored, not published here) so its case brief and model answers stay out of a public repo. See the honesty rule in `docs/PLAN.md`.
