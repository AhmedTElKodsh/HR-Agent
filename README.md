# HR-Agent

A portfolio replica of the HR policy assistant from the "AI Engineer Technical Interview Mock". It uses fictional data (Nilebyte Solutions) and exists to produce first-hand evidence for every interview stage.

| Start here | What it is |
|---|---|
| `docs/PLAN.md` | Interview story map, milestones M0–M7 with exit criteria, and the decision log |
| `docs/agent_tools.md` | Tool contract for the agent: identity, the confirm flow, violations |
| `docs/results.md` | The only numbers you may quote |
| `docs/war_stories.md` | Failures you found, written from traces |
| `data/README.md` | The corpus, its formats and the test cases built into it |
| `eval/README.md` | Eval files, slices, matching rules and statistics |

```bash
pip install -r scripts/requirements-data.txt
python scripts/build_corpus.py          # render data/policies/ into data/corpus/ (PDF, DOCX, scan, HTML)
python scripts/make_counterfactuals.py  # regenerate the fairness suite
python scripts/validate_data.py         # check that everything is consistent
```

The ticket-routing dataset (milestone M5) is public and licensed CC BY-NC 4.0 (see `data/tickets/README.md`). Credit its author if you publish results.
