# HR-Agent: 2-Day Sprint Edition

> **This is the compact first version of HR-Agent, scoped for a two-day interview scenario.** It was planned as a ~16-hour build for a Junior AI Engineer interview that was two days away. It is **frozen at "baseline before M0"**: the data, eval set, architecture and build guide exist, but no application code was written here.
>
> Active development lives in the [repository root](../README.md). This folder is kept as a reference for how the same case looks when the clock is the main constraint.

## Why it exists

The root project is the full version: every stage of the interview mock, measured, over eight milestones with no deadline. This edition answers a different question: *what is the smallest honest system you can build, understand and defend in two days?* The two plans make opposite trade-offs on purpose, and comparing them is itself a useful interview talking point ("what would you cut, and why?").

## How it differs from the main project

| | 2-Day Sprint Edition (this folder) | Main project (root) |
|---|---|---|
| Time budget | ~16 hours over two days, with a safety net at hour 9 | Open-ended, milestone by milestone |
| Milestones | M0–M10, each ~0.5–2 h ([BUILD_GUIDE](docs/BUILD_GUIDE.md)) | M0–M7 with exit criteria ([PLAN](../docs/PLAN.md)) |
| Fictional company | Nilecrest Technologies | Nilebyte Solutions |
| Policy corpus | 4 English Markdown policies (47 section chunks) | 21 documents in PDF, DOCX, HTML, Markdown and a scan; English and Arabic |
| RAG eval | 20 golden Q&A items | 125 items, with slices, gates and confidence intervals |
| Screening | 9 CVs for a Junior AI Engineer JD; counterfactual pairs 06/07/09 | 8 CVs for a Junior Data Analyst JD; a 32-variant counterfactual suite |
| Agent | Two tools, human approval via LangChain `HumanInTheLoopMiddleware` | Tools plus a confirm endpoint and a rules engine; 20 scenarios |
| Ticket routing | Not in scope | M5 |
| Stack | Chroma, `fastembed` (bge-small), Groq, SQLite, FastAPI + Streamlit | Candidates to be compared: Postgres + pgvector, BGE-M3, reranker, Langfuse |
| Tutoring | [AGENTS.md](AGENTS.md) tutor contract and hint ladder | The coaching skill in `.claude/skills/` |

The two datasets are **independent**: they use different companies, people and ids. Don't mix their eval numbers, and don't point one edition's code at the other's data. Both use the same citation-id format, `<doc_id>#<section_id>`.

## What's worth reading

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): the decision table (D1–D8), with a trade-off and a "when to change" for each choice, plus the environment facts checked on 2026-09-22 (no GPU, 15 GB RAM, no Docker at the time).
- [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md): the hour-by-hour budget, the hour-9 safety net, and the explain-back questions per milestone.
- [docs/DATA_FIXES.md](docs/DATA_FIXES.md): eleven mock-data bugs found in review, and the honesty rule about which ones you may tell as your own stories.
- [AGENTS.md](AGENTS.md): the "tutor, not author" contract and the seven-rung hint ladder.

## Layout

```
AGENTS.md, CLAUDE.md     tutor contract (applies to this folder only)
.claude/                 the "HR Tutor" output style used during the sprint
data/                    policies/, jobs/, resumes/, hris/ (CSV)
docs/                    ARCHITECTURE, BUILD_GUIDE, DATA_FIXES
eval/                    golden_policy_qa.jsonl, screening_expectations.json
learning/LOG.md          learning-log template (no entries)
```

Paths in these documents (`app/`, `scripts/seed_db.py`, `eval/run_rag.py`, ...) are relative to this folder and describe the planned layout. None of them exist yet.

The edition's original commit history is kept as the second parent of the merge commit that brought it in. Its files sat at the root back then, so `git log -- sprint-2day/` won't find it. Use `git log <merge-commit>^2` instead.
