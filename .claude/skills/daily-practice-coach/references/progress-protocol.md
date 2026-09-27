# Progress protocol

State schemas, record triggers, and the exact helper commands. **This file is the fallback**: if `scripts/coach.py` cannot run, read and write these files by hand using the schemas below, then say validation was not executed.

All learner state lives under `<workspace>/learning/`. Nothing is ever written into this skill's folder.

```
learning/
  LEARNER_PROFILE.md     prose, learner-owned
  GLOSSARY.md            prose, grows during sessions
  RESOURCES.md           curated links, cited in explanations
  progress.json          task state + settings
  review.json            spaced-repetition items
  records/               one markdown file per record, YYYY-MM-DD-slug.md
```

## `progress.json`

```json
{
  "schema_version": 1,
  "project": "HR-Agent",
  "mission": "Defend every stage of the HR Policy Assistant case two levels deep, with my own evidence.",
  "placement": {
    "status": "done",
    "date": "2026-09-27",
    "waived_tasks": ["B-T02"]
  },
  "settings": {
    "code_by_myself": true,
    "strict_mode": false,
    "session_minutes": 60
  },
  "tasks": {
    "M1-T01": {
      "status": "done",
      "understanding": "assessed",
      "hint_level": 1,
      "struggles": 0,
      "coach_wrote_code": false,
      "evidence": [
        {
          "kind": "observed",
          "text": "pytest tests/test_harness.py -q -> 14 passed",
          "date": "2026-09-27"
        }
      ],
      "next_action": "Add per-slice reporting (M1-T02)",
      "updated": "2026-09-27"
    }
  }
}
```

**Field rules**

| Field | Values | Notes |
|---|---|---|
| `status` | `not_started`, `in_progress`, `done`, `waived` | `done` requires at least one evidence entry |
| `understanding` | `unassessed`, `assessed`, `shaky` | Independent of `status`. Generated code never sets this to `assessed` |
| `hint_level` | 0-5 | The **highest** rung reached. A `strict_mode` bypass records 3; an analogue records 4; coach-written project code records 5 |
| `coach_wrote_code` | bool | Set by `update --coach-wrote-code`. Permanent until cleared by hand. Forces `understanding` to stay `unassessed` and shows as DEBT in `status` |
| `struggles` | integer | Incremented by `update --struggle` |
| `evidence[].kind` | `observed`, `learner_reported` | `observed` only for output you saw yourself |
| `placement.status` | `none`, `done`, `declined` | `declined` means never re-offer |
| `waived_tasks` | task IDs | Only tasks with `"bridge": true` may appear |

**Settings**

| Setting | Default | Effect |
|---|---|---|
| `code_by_myself` | `true` | The coach directs and reviews but does not write project code. See SKILL.md, *The code-by-myself contract*. Set `false` to lift it |
| `strict_mode` | `false` | Ask once for a commitment before revealing an answer; the bypass is granted and recorded as rung 3 |
| `session_minutes` | `60` | Used to size the session goal, not enforced |

## `review.json`

```json
{
  "schema_version": 1,
  "items": [
    {
      "id": "r0007",
      "prompt": "Why does the access filter live in the SQL query instead of the system prompt?",
      "answer": "Security must hold even if the model is fully manipulated (PLAN.md D9). A prompt filter is advisory; a query filter is enforced.",
      "source_task": "M2-T05",
      "created": "2026-09-27",
      "due": "2026-09-28",
      "interval_days": 1,
      "streak": 0,
      "history": [{ "date": "2026-09-27", "grade": "partial" }]
    }
  ]
}
```

A missing `review.json` is treated as `{"schema_version": 1, "items": []}`.

## Records

One file per record, `learning/records/YYYY-MM-DD-slug.md`, with front matter:

```markdown
---
kind: war-story
date: 2026-09-27
tasks: [M2-T02]
---

Body.
```

`kind` is one of:

| Kind | Written when |
|---|---|
| `prior-knowledge` | A placement result, with the evidence that demonstrated it |
| `decision` | The learner chose between real alternatives and the reason should survive |
| `war-story` | A non-trivial bug, in the `docs/war_stories.md` template. Also append it to that file |
| `misconception` | A belief that turned out wrong. The most valuable kind; write what they believed, not just the correction |
| `milestone` | A milestone's exit criterion was met, with the evidence |

### Record triggers

Write a record when, and only when, one of these fires. Otherwise the folder fills with noise and stops being read.

1. A bug took more than one hypothesis to find → `war-story`.
2. The learner chose between two real options and can state why → `decision`.
3. Something they believed confidently turned out to be false → `misconception`.
4. A placement item was assessed → `prior-knowledge`.
5. A milestone exit criterion was met → `milestone`.

A finished task on its own is **not** a trigger; that is what `progress.json` is for.

## Helper commands

All take `--project PATH` (defaults to the discovered workspace).

```bash
python scripts/coach.py init      --project PATH
python scripts/coach.py status    --project PATH
python scripts/coach.py update    --project PATH --task M2-T04 \
                                  --status in_progress \
                                  --evidence "pytest -k rrf -> 3 passed" --observed \
                                  --hint-level 2 \
                                  --next "Tune the relevance gate on out_of_scope"
python scripts/coach.py update    --project PATH --task M2-T04 --struggle
python scripts/coach.py update    --project PATH --task M2-T04 --coach-wrote-code
python scripts/coach.py review add   --project PATH --task M2-T05 \
                                     --prompt "..." --answer "..."
python scripts/coach.py review due   --project PATH
python scripts/coach.py review grade --project PATH --id r0007 --grade pass
python scripts/coach.py record new   --project PATH --kind war-story \
                                     --title "2025 policy outranks 2026" --task M2-T06
python scripts/coach.py validate  --project PATH
```

**Checkpoint order** (SKILL.md step 8): `update` → `review add` → `record new` (only on a trigger) → `validate` last.

### What `status` does and does not tell you

It reports recorded state: mission, placement, overdue reviews, unassessed understanding, and which tasks are dependency-ready. **It never proves a test passed** — it reads the `evidence` you wrote, and it cannot tell `observed` from wishful thinking. Treat its suggestions as a priority list, not a verdict.

### What `validate` checks

- Every task ID in `progress.json` exists in `tasks/catalog.json`.
- No task is `done` without at least one evidence entry.
- No non-bridge task appears in `placement.waived_tasks`.
- No task is `done` while any `depends_on` is neither `done` nor `waived`.
- No task has `coach_wrote_code` set while `understanding` is `assessed`.
- `review.json` items have valid dates, grades and intervals.
- Enum fields hold legal values.

It exits non-zero on any violation and prints one line per problem.

## Writing by hand

If the helper is unavailable, edit the JSON directly and keep these invariants:

- Bump nothing; `schema_version` stays 1.
- Never delete a task entry — set its status instead.
- Never rewrite `evidence` history; append.
- Keep `updated` as an ISO date.
- Preserve any keys you do not understand. They may come from a newer helper.

Then tell the learner: *"I edited the JSON directly; `validate` was not run."*
