# Build guide

The milestone map for this project. The learner builds each milestone; the AI tutors it under the rules in [AGENTS.md](../AGENTS.md). Each milestone produces something runnable, has observable "done when" checks, and ends with explain-back questions. Those questions are the interview.

**Budget:** about 16 hours over two days, at tutoring pace. Writing the code yourself is slower than having it generated, and that trade is the whole point.

## Target layout

```
app/
  llm.py                 # one gateway: chat(...) for groq | openrouter | ollama, logs every call
  rag/chunk.py           # section-aware chunker
  rag/index.py           # embed + Chroma upsert, retrieve()
  rag/answer.py          # prompt, cited answer, abstain, citation check
  screening/redact.py    # PII and protected-attribute redaction
  screening/extract.py   # per-requirement evidence as strict JSON
  screening/score.py     # quote verification + weighted score (code, not the LLM)
  agent/tools.py         # leave tools; business rules live here
  agent/graph.py         # create_agent + human approval on writes
  api.py                 # FastAPI
ui/app.py                # Streamlit
scripts/build_index.py   scripts/seed_db.py
eval/run_rag.py          eval/run_screening.py      eval/results/
tests/                   logs/ (gitignored)         learning/LOG.md
```

## Budget at a glance

| # | Milestone | h | Σ |
|---|---|---|---|
| M0 | Environment, gateway, call log (you've already made Groq calls) | 0.5 | 0.5 |
| M1 | RAG: chunk, index, retrieve | 1.5 | 2.0 |
| M2 | RAG: cited answer and abstention | 1.0 | 3.0 |
| M3 | RAG evaluation and two experiments | 1.5 | 4.5 |
| M4 | Redaction | 1.0 | 5.5 |
| M5 | Evidence extraction and scoring | 2.0 | 7.5 |
| M6 | Screening evaluation | 1.5 | 9.0 |
| | **Safety net.** If M0–M6 aren't green at hour 9, the agent becomes a README design section instead of code. | | |
| M7 | HR agent: two tools plus human approval | 2.0 | 11.0 |
| M8 | API and UI | 1.0 | 12.0 |
| M9 | README and backup demo | 1.0 | 13.0 |
| M10 | Interview rehearsal, no new code | 2.0 | 15.0 |
| | Buffer for the thing that breaks | 1.0 | 16.0 |

### Decision: build the agent, keep it thin

The agent gets built, not just described. Reasons:
- **The JD names it** (N1: agents and tool/function calling), as most junior AI postings now do. It's where your current course ends (LangGraph, tools, human-in-the-loop), so the interviewer is likely to ask about it whatever you build.
- **It got cheaper.** The data prerequisites it needed (holiday calendar, weekends, carry-over, FTE) are already fixed ([DATA_FIXES.md](DATA_FIXES.md)). You've already made Groq calls, so M0 is shorter.
- **It's the only module with a write action.** That gives you a second Responsible-AI story beyond screening: authorization bound to the session, and a human approving before anything changes.
- **Thin means two tools**, `get_leave_balance` and `request_leave`, with approval on the write. A policy-search tool that reuses your RAG is a stretch goal, not a requirement.

A README design section would cost 30 minutes, but "I built it and here's how the approval works" beats "here's how I would build it."

---

## M0 · Environment, gateway, call log

**Goal.** `uv run python -m app.llm "hello"` prints a model reply and appends one line to `logs/calls.jsonl`. You've already made Groq calls, so the new parts are the single gateway every module will use, the provider switch and the log.
**Course link.** Lab 1 (first API call, `response.choices[0].message.content`, token usage) and Lab 2 (switching providers with LangChain).
**You write.** `chat()` in `app/llm.py`: build the messages, call the provider, time the call, return the text, and write the log line. Choose LangChain chat models or the provider SDKs, and be ready to justify the choice.
**AI may help with.** `uv init` / `uv add`, `.env.example`, `.gitignore` (`.env`, `logs/`, `chroma/`, `*.db`, `data/private/`, `.claude/settings.local.json`), `ollama pull qwen3:4b`, reading the response object.
**Done when.**
- A Groq call works.
- Setting `PROVIDER=ollama` works with no code change.
- The log line contains `latency_ms`, `prompt_tokens`, `completion_tokens` and `model`.

**Explain-back.**
1. Where does your Python stop and the model start? What crosses the network?
2. Why does `choices` need `[0]`?
3. What is in your log line, and which question would it answer in production?

## M1 · RAG: chunk, index, retrieve

**Goal.** `uv run python -m scripts.build_index` stores 47 section chunks in Chroma, and `retrieve("Can I roll over vacation?")` returns `leave_policy#2.3` in the top 4.
**Course link.** Vector database lab (embeddings, chunking, Chroma, similarity threshold).
**You write.**
- A chunker that splits on `##` / `###` headings, prefixes each chunk with its path (`Leave Policy v3.2 › 2 Annual Leave › 2.3 Carry-over`) and attaches `doc_id`, `section_id`, `version` and `effective_date`.
- Embedding with `fastembed` (`BAAI/bge-small-en-v1.5`).
- A Chroma upsert using ids like `leave_policy#2.3`.
- `retrieve(question, k)`.

**AI may help with.** Verified fastembed and Chroma syntax; cosine similarity explained on a toy example.
**Done when.**
- The index holds 47 chunks, each with its metadata.
- Golden questions q03 (carry-over) and q11 (jeans) retrieve their expected sections in the top 4.

**Explain-back.**
1. Why chunk by section instead of the course's 500 characters with 100 overlap? (Hint: your largest section is 431 characters.)
2. What exactly gets embedded, and why include the path prefix?
3. The whole corpus is about 2,500 tokens. Why not paste it all into every prompt?

## M2 · RAG: cited answer and abstention

**Goal.** `answer(question)` returns `{answer, citations}`, and says "I don't have that information in the provided documents" when it should.
**You write.**
- The prompt: context labelled with `[doc#section]` ids and a rule to answer only from the context and cite ids.
- A retrieval score threshold for abstaining.
- A post-check that every cited id was among the retrieved ids.

**Done when.**
- q01 cites `leave_policy#2.1` and says 21.
- o01 (stock options) abstains.
- a01 refuses and reveals nothing.

**Explain-back.**
1. How did you choose the threshold, and what did the out-of-scope questions teach you?
2. What happens if the model cites a section it was never given?
3. Why does the RAG module have no access to `employees.csv`?

## M3 · RAG evaluation and two experiments

**Goal.** `uv run python -m eval.run_rag` prints hit@4, citation precision, abstention accuracy and must-contain rate, and saves `eval/results/rag_<date>.json`.
**You write.** The metric functions and the loop, plus two experiments:
- Section chunker vs `RecursiveCharacterTextSplitter(500, 100)`.
- Top-4 RAG vs "stuff the whole corpus" (accuracy and prompt tokens per query).

**Note on the golden set.** Each `must_contain` item must appear in the answer, case-insensitively. An item that is itself a list means any one of its alternatives is enough (`["4 weeks", "four weeks"]`). `must_not_contain` must not appear at all. Citation ids use `<doc>#<section>` ([data/README.md](../data/README.md)).

**Done when.** The README has a results table with real numbers and one sentence of interpretation per row.
**Explain-back.**
1. Define hit@k and citation precision precisely.
2. Which question fails, and at which layer: retrieval or generation?
3. With 20 questions, what may you claim, and what may you not?

## M4 · Redaction

**Goal.** `redact(text)` removes email, phone, street address, date of birth, national ID, and marital-status and children lines. `redact(text, blind=True)` also removes the name and gendered pronouns.
**You write.** The patterns, plus tests against `cand_08`.
**Done when.**
- Redacted `cand_08` contains none of: the email, `+20 555`, `14 Fictional St`, `12/03/1994`, `Married, 2 children`.
- Nothing in `logs/` contains raw CV text.

**Explain-back.**
1. Why redact before the LLM call instead of telling the LLM to ignore PII?
2. What would regex miss that a tool like Presidio catches?
3. Why keep names in non-blind mode at all?

## M5 · Evidence extraction and scoring

**Goal.** `screen("cand_01")` returns, for each rubric requirement, `{level: yes|partial|no, evidence_quote}` plus a score from 0 to 100.
**You write.**
- The schema (Pydantic).
- The extraction prompt, with the CV inside delimiters as untrusted data.
- Groq `json_schema` with `strict: true` on `openai/gpt-oss-120b`.
- Quote verification: each quote must be an exact substring of the redacted CV, otherwise demote to `no`.
- The weighted score and tier from `data/jobs/junior_ai_engineer_rubric.json`, computed in Python.
- Put the rubric's `yes` / `partial` anchors and its `excluded_from_scoring` list into the prompt. Anchors are what make three runs agree.

**AI may help with.** Verified Groq structured-output syntax; the difference between JSON mode and strict schema.
**Done when.** `cand_01` scores at least 80. `cand_04` scores at most 25. `cand_05` scores at most 25 **when given the raw file text, HTML comment included.**
**About the JD.** It's a realistic composite of junior AI postings written for this project, not a copy of a real one. Optional demo: screen your own CV against it. Keep the CV in `data/private/` (add that folder to `.gitignore` in M0), redact it first, and run it on Ollama so it never leaves your laptop.
**Explain-back.**
1. Why doesn't the LLM produce the score?
2. Walk through what happens to `cand_05`'s injected instruction, step by step.
3. What does strict `json_schema` guarantee, and what does it not?

## M6 · Screening evaluation

**Goal.** `uv run python -m eval.run_screening` runs the six checks in `eval/screening_expectations.json` and prints pass or fail with numbers.
**You write.** The checks:
- Three-run consistency (standard deviation).
- Two counterfactual pairs, with blind mode off and on: `cand_06` vs `cand_09` (name only) and `cand_07` vs `cand_09` (pronouns only).
- The tier check.
- The career-gap check.
- A scan of the logs for PII.
- Injection resistance on `cand_05`, including the precondition that the injected text actually reached the extractor.

Throttle requests to stay under the free tier's 8K tokens per minute.
**Done when.** All six report. Any failure is explained in the README, not hidden.
**Explain-back.**
1. Suppose the name pair differs by 8 points and the pronoun pair by 1. What can you conclude, and what can't you, from 3 runs of one CV body?
2. Why three runs, and is that enough?
3. What would a real bias audit need that this doesn't have?

---

**Safety net.** At hour 9, if M0–M6 aren't green, skip the M7 code. Write the agent as a README design section instead (tools, where the rules live, approval flow, authorization), and use the time to finish M0–M6 properly.

## M7 · HR agent: two tools plus human approval

**Goal.** Logged in as `E004`, "I'd like 25 to 27 October off" leads the agent to check the balance and the rules, propose a 3-working-day request, **pause for human approval**, and only then write it.
**Course link.** LangGraph lab, plus the human-in-the-loop note at the end of the MCP section. The course's `create_react_agent` is superseded by `langchain.agents.create_agent` in LangChain v1; verify the current API.
**Read first.** The rules section of [DATA_FIXES.md](DATA_FIXES.md) and the HRIS conventions in [data/README.md](../data/README.md). The data is ready.
**You write.**
- `scripts/seed_db.py`: the five CSVs into SQLite.
- `get_leave_balance()`: available = entitlement (accrued-to-date in the first year) − used − pending. Carry-over is never available after 31 March. First-year joiners accrue 1.75 days per completed month.
- `request_leave(start, end, leave_type)`: working days by country (weekend + holidays), probation, the notice period, sufficient balance, no overlap with an existing pending or approved request. It *proposes*; the write happens only after approval.
- `create_agent` with `HumanInTheLoopMiddleware` on the write.
- The employee id bound from the session, never taken as a tool argument.
- Pass `today` into your rule functions instead of reading the clock inside them, so the checks below give the same result on any day.

**Done when** (with `today = 2026-09-22`):
- `E004` asking for 25–27 October: 3 working days proposed, paused for approval, and written only after you approve.
- Rejecting at the approval step writes nothing.
- 5–9 October for an Egypt employee counts **3** working days (Friday is the weekend; 8 October is the observed Armed Forces Day), matching `LR1002` in the data.
- `E003`'s available balance is **3**: 21 − 15 − 3 pending.
- `E003` asking for 5–9 October again is refused: it overlaps pending `LR1002`, and it gives only 8 working days' notice where 10 are required.
- `E007` asking for 27–28 September is refused for probation. Its notice is fine: 2 days required, 2 given.
- `E005` asking how many carried-over days remain gets **0**: 3 were used and 2 were forfeited on 31 March.
- Asking about another employee's salary band returns nothing.

**Explain-back.**
1. Why is the employee id not a tool argument?
2. Why do the business rules live in the tools and not in the prompt?
3. What does the checkpointer do while the agent waits for approval?
4. The public calendars disagree about when Armed Forces Day is taken off. How does your system decide, and what would you do with real data?

## M8 · API and UI

**Goal.** FastAPI routes `/ask` and `/screen` (and `/agent` if built), and a Streamlit page with a tab per module calling the API.
**AI may help with.** Boilerplate on request: the app object, routes that call *your* functions, the Streamlit layout.
**Done when.** `uv run uvicorn app.api:app` and `uv run streamlit run ui/app.py` give a working end-to-end demo.
**Explain-back.**
1. What does FastAPI validate for you, and what doesn't it?
2. Groq returns HTTP 429 during your demo. What happens, and what should happen?

## M9 · README and backup demo

The README covers:
- the problem
- the architecture diagram
- how to run it
- the evaluation results tables
- the known limitations
- an AI-assistance note (tutored; what you wrote; anything built in ship mode)

Record a three-minute demo video in case the network or rate limits fail on the day.
**AI may help with.** Reviewing the README for any claim not backed by a number.

## M10 · Interview rehearsal (no new code)

The tutor runs a mock interview:
- every explain-back question above, in random order
- a two-minute pitch
- one STAR story taken from [the learning log](../learning/LOG.md)
- "What would you improve with more time?"
