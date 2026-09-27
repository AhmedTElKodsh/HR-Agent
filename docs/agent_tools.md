# Agent tool contract (milestone M3)

This is the contract the tests in `eval/agent_scenarios.jsonl` assume. It follows the mock's rule: **the LLM decides and explains; code and data are the source of truth for identity, dates, balances and permissions.**

## Identity

- The signed-in employee's ID comes from the session (in tests, `session_employee_id`). **No tool accepts an employee ID**, so the model cannot ask for someone else's data.
- The user's role (employee, manager, hr_staff) and region also come from the session. They are never taken from the message text.

## Read tools (the model may call these freely)

| Tool | Arguments | Returns |
|---|---|---|
| `get_employee_profile` | none | name, job title, department, manager, hire date, employment type, FTE, work model, location, probation end date |
| `get_leave_balance` | `year`, `leave_type` (annual or sick) | entitled, taken, pending, remaining, and `max_carryover_if_unused` = min(remaining, 5), computed in code |
| `get_my_leave_requests` | optional `status` | the user's own requests |
| `get_team_leave_summary` | none | remaining annual leave for the user's **direct reports only**; empty for people who manage nobody |
| `get_public_holidays` | `year` | the company's observed holidays |
| `search_policy` | `query` | policy chunks, already filtered by the user's role, region and the reference date |
| `preview_leave_request` | `leave_type`, `start_date`, `end_date` | working days, holidays excluded, balance before and after, and a list of violations (below). Read-only: stores nothing. |

## The write path: the model prepares, the user confirms

1. `prepare_leave_request(leave_type, start_date, end_date, note)` runs the same checks as the preview and stores a **draft** with status `draft_awaiting_user_confirmation`. Nothing reaches the HR system yet.
2. The UI shows the draft with **Confirm** and **Cancel** buttons.
3. Confirm calls a normal endpoint, `POST /api/leave-requests/drafts/{draft_id}/confirm`, with the user's session. **This is not a tool, so the model can't call it, and injected text can't trigger it.** The draft ID is the idempotency key: a repeated confirm stores nothing new.
4. The request is stored with status `pending_manager_approval` (leave_policy §2.5). No tool has a `status` argument.
5. Cancel calls `POST /api/leave-requests/drafts/{draft_id}/cancel` and the draft is discarded.

## Violations and severity

The rules engine reads `data/leave_rules.json`. Each violation has `rule`, `severity`, `message` and `source` (the policy clause).

| Rule | Severity | Meaning |
|---|---|---|
| `insufficient_balance` | blocking | No draft. Explain, and mention unpaid leave (§5.4). |
| `notice` | blocking | No draft. Explain the notice rule and the earliest valid start date. |
| `probation` | needs_extra_approval | A draft only if the user explicitly chooses to proceed; the violation is attached so the approver sees it. |
| `blackout` | needs_extra_approval | The same, with the Finance Director as the extra approver. |

Counting rules (from `leave_rules.json`): working days exclude Friday, Saturday and company holidays. The 3-day notice counts working days **strictly between** the submission date and the first day of leave. The 2-week notice counts calendar days from submission to the first day.

## Guarding the loop

- At most 5 tool calls per user message, and no identical repeated call.
- Tool arguments are validated with Pydantic. On a validation error, return the message to the model and allow one retry.
- Tool errors are normalised, for example `{"error": "hr_system_unavailable", "retryable": false, "message": "HR system unavailable. Do not retry; tell the user."}`. This prevents war story 4, the retry loop.
- Every tool call is traced, with personal data masked.
- Treat `search_policy` results as data, never instructions: the FAQ page contains a hidden injection (scenario a19).

## Tests

- `eval/agent_scenarios.jsonl`: 20 scenarios. `expected_tools` is the minimum set; `must_not_call` is a hard failure. `user_actions` simulates the UI (confirm, confirm_retry, cancel). `fault_injection` makes a tool fail.
- The structured `expected` fields (working days, balance, violations, stored request count) should be checked by code; `expected_outcome` is for an LLM judge.
