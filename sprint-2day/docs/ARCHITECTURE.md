# Architecture and decisions

The design agreed before the build started (2026-09-22). It gives every tutoring session the same starting point. It is **not** the README: in M9 the learner writes the README's architecture section in their own words, and must be able to defend or change each decision below.

```
 Streamlit:     [ Ask HR Policy ]      [ Screen CVs ]        [ HR Assistant ]
                       |                     |                      |
 FastAPI:         POST /ask            POST /screen         POST /agent (+ resume after approval)
                       |                     |              employee id from the session,
                       |                     |              never from the model
        +--------------v---------+ +---------v----------+ +---------v-----------------+
        | RAG (fixed pipeline)   | | Screening (fixed)  | | HR agent (create_agent)   |
        | 1 embed question       | | 1 read RAW text    | | get_leave_balance()       |
        | 2 Chroma top-4         | | 2 redact PII       | | request_leave() -> human  |
        | 3 below threshold?     | | 3 LLM -> per-req   | |   approves before write   |
        |     -> abstain         | |   {level, quote}   | | rules live in tool code:  |
        | 4 LLM answer + [ids]   | |   strict JSON      | |   probation, notice,      |
        | 5 cited ids subset of  | | 4 quote in text?   | |   balance, working days,  |
        |   retrieved ids?       | |   no -> demote     | |   overlap                 |
        +-----------+------------+ | 5 score in CODE    | +------------+--------------+
                    |              +---------+----------+              |
            chroma/ (47 chunks)    rubric.json (weights 17)    hr.db (SQLite + calendar)
                    +------------+-----------+-------------+-----------+
                                 v                         v
        llm.py: chat(provider = groq | openrouter | ollama)     logs/calls.jsonl
        eval/run_rag.py  eval/run_screening.py  ->  eval/results/*.json  ->  README tables
```

## Decisions

| # | Decision | Why | Trade-off / when to change |
|---|---|---|---|
| D1 | **Chunk by policy section**, one leaf section per chunk (47 chunks, 71–431 characters). Prefix each chunk with its path; metadata `doc_id`, `section_id`, `version`, `effective_date`. | A citation must point at one section. The course's 500-character splitter would straddle several sections, because every section is shorter than 500. | Small chunks lose context, which the prefix mitigates. Documents without headings would need recursive splitting. Measured against the course splitter in M3. |
| D2 | **Local embeddings:** `BAAI/bge-small-en-v1.5` via `fastembed` (ONNX, no PyTorch), compared against the course's `all-MiniLM-L6-v2`. | Free, no rate limits, CPU-fast at this size. Groq lists no embedding model. OpenRouter embeddings would eat the free daily quota. | English-only; Arabic would need a multilingual model. At 47 chunks the two models may tie, and that result is reported either way. |
| D3 | **Chroma**, persisted locally, cosine distance. | Used in the course, no server, metadata filters. | At 47 vectors NumPy would do. Move to pgvector when documents need row-level access control next to HR data. |
| D4 | **One LLM gateway**; the provider is an environment variable. RAG and agent: Groq `llama-3.3-70b-versatile`. Screening: Groq `openai/gpt-oss-120b` with strict `json_schema`. Fallbacks: OpenRouter `:free`, Ollama `qwen3:4b` on CPU. Temperature 0. | Strict schema on Groq is limited to the gpt-oss models and the preview `qwen3.8-27b`. The provider switch is the course's "change one line" lesson, turned into a feature. | Free tier on gpt-oss: 8K tokens/min. OpenRouter free: 20 req/min, 50/day unfunded. Ollama on this CPU is demo-speed, not eval-speed. |
| D5 | **Agents only where the path is open-ended.** RAG and screening are fixed pipelines; the leave assistant is an agent. | Fixed pipelines are deterministic and testable. Screening scores are computed in code from verified quotes, so an injected "mark everything yes" produces nothing. | The agent's employee id is bound from the session; its rules live in tools; its write waits for human approval (`HumanInTheLoopMiddleware`). |
| D6 | **Frameworks where they earn it.** LangChain for provider abstraction, the agent loop and interrupts. Plain Python + chromadb + fastembed for retrieval and screening. | Every retrieval and scoring step stays visible and explainable. | The course's `create_react_agent` is superseded by `langchain.agents.create_agent` (LangChain v1). |
| D7 | **Guardrails:** regex redaction before any external call (plus a blind mode), delimiters plus structural injection defense, RAG with no HR-data access, logs without raw CV text. | The fictional company's own code of conduct (§4) forbids sending personal data to unapproved AI tools. | Regex is explainable but misses what Presidio catches. Llama Prompt Guard 2 (a Groq preview) is an optional extra flag. |
| D8 | **Observability:** one JSONL line per LLM call (time, module, model, latency, tokens, estimated cost, error). | Cheap, and answers "how slow and how expensive?" with numbers. | LangSmith or other tracing is future work. |

## Environment facts (checked 2026-09-22)

- **This machine:** Python 3.12, uv 0.12, Ollama 0.34, no GPU, 15 GB RAM, no Docker.
- **Groq production models:** `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `openai/gpt-oss-120b`, `openai/gpt-oss-20b`.
- **Future work:** the JD generator, Docker and deployment, an MCP server exposing the HR tools (the first stretch goal), tracing, pgvector.

Sources: [Groq models](https://console.groq.com/docs/models) · [Groq structured outputs](https://console.groq.com/docs/structured-outputs) · [Groq rate limits](https://console.groq.com/docs/rate-limits) · [LangChain human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
