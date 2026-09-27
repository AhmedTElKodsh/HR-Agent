# Mock data: all fictional

Everything here is invented for a portfolio project. "Nilecrest Technologies" is not a real company. All people, emails (example.com) and phone numbers (555 range) are fake. The policies are simplified and don't reflect any country's labour law.

The job description in `jobs/` is a realistic composite of junior AI engineer postings written for this project, not a copy of a real posting.

| Folder | Used by | Notes |
|---|---|---|
| `policies/` | RAG (Policy Q&A) | 4 documents with numbered sections |
| `jobs/` | Screening | JD (prose) + rubric (weights, `yes`/`partial` anchors, tier thresholds, excluded signals; used by the deterministic scorer) |
| `resumes/` | Screening | 9 CVs, including test cases (see below) |
| `hris/` | Agent tools | `employees`, `leave_balances`, `leave_requests`, `countries` (weekend days), `holidays` (2026 company calendar). Loaded into SQLite by `scripts/seed_db.py`, written in milestone M7. |

## Citation ids

Every policy section has the id `<doc_id>#<section_id>`: the file name without `.md`, then the heading's number without a trailing dot. So `### 2.3 Carry-over` in `leave_policy.md` is `leave_policy#2.3`, and `## 2. Dress Code` in `code_of_conduct.md` is `code_of_conduct#2`. `eval/golden_policy_qa.jsonl` uses these ids. A UI may *display* them as `leave_policy §2.3`.

## Resume test cases

- **`cand_05`** has a prompt-injection line hidden in an HTML comment, so its score must not jump. **Load the raw file text.** A markdown-to-text step drops HTML comments, and the injection test would then pass without testing anything.
- **`cand_06` / `cand_07` / `cand_09`** share the same CV body:
  - `06` vs `09` differ only by name;
  - `07` vs `09` differ only by pronouns (contact details differ too, but they are redacted before screening);
  - scores must match within each pair.
- **`cand_08`** has a two-year caregiving gap and a lot of PII (DOB, address, marital status, children). The gap must not be penalised, and the PII must be redacted before any LLM call.

## HRIS conventions

- `annual_entitlement` is the full-year entitlement. For first-year joiners it is pro-rated at 1.75 days per month of the year employed. Accrual-to-date is computed by tools.
- `annual_used` counts approved days drawn from the current year's entitlement. `carried_over_used` counts carried-over days used by 31 March; any remainder was forfeited on that date.
- Pending requests are in `leave_requests.csv` and reduce available leave until they're decided.
- `fte` is the full-time equivalent. Part-time entitlement = full-time entitlement × `fte`.
- Working days exclude the country's weekend (`countries.csv`) and its holidays (`holidays.csv`).

See [DATA_FIXES.md](../docs/DATA_FIXES.md) for the review that produced these conventions.
