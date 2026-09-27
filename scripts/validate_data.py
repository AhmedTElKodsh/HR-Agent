"""Check that the dataset and eval files are consistent with each other.

Run after any edit to data/ or eval/:  python scripts/validate_data.py
It checks structure and cross-references only. It does not run your system.
The normalise() and matches() helpers implement the matching rules in
eval/README.md; reuse them in your evaluation harness.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRORS = []

SLICES = {"typical", "table", "follow_up", "security", "out_of_scope", "abac", "multi_hop",
          "tool_route", "version", "code_lookup", "conflict"}
BEHAVIOURS = {"answer", "refuse", "conflict", "route_to_tool"}
TOOLS = {"get_employee_profile", "get_leave_balance", "get_my_leave_requests", "get_team_leave_summary",
         "get_public_holidays", "search_policy", "preview_leave_request", "prepare_leave_request"}
ACTIONS = {"confirm", "confirm_retry", "cancel"}
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")


def err(msg):
    ERRORS.append(msg)


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


# ------------------------------------------------------------ matching rules ---
def normalise(text):
    text = text.translate(ARABIC_DIGITS).lower()
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)          # 1,000 -> 1000
    return re.sub(r"\s+", " ", text).strip()


def matches(answer, item):
    """True if the answer contains the item. A list item means any-of.
    A purely numeric item matches only as a whole number."""
    if isinstance(item, list):
        return any(matches(answer, i) for i in item)
    a, i = normalise(answer), normalise(item)
    if re.fullmatch(r"[\d.]+%?", i):
        return re.search(r"(?<![\d.])" + re.escape(i) + r"(?![\d])", a) is not None
    return i in a


# ------------------------------------------------------------------- corpus ---
def section_exists(src_text, section, fmt):
    if fmt == "html":
        return re.search(r"<h3>\s*" + re.escape(section) + r"\s", src_text) is not None
    return re.search(r"^" + re.escape(section) + r" ", src_text, re.M) is not None


def check_manifest():
    m = json.loads((ROOT / "data/corpus_manifest.json").read_text(encoding="utf-8"))
    roles, regions = set(m["_meta"]["roles"]), set(m["_meta"]["regions"]) | {"all"}
    docs = {}
    for d in m["documents"]:
        k = d["doc_key"]
        if k in docs:
            err(f"manifest: duplicate doc_key {k}")
        docs[k] = d
        for p in ("source", "file"):
            if not (ROOT / d[p]).exists():
                err(f"manifest: {k}: missing {p} {d[p]} (run scripts/build_corpus.py?)")
        if not set(d["allowed_roles"]) <= roles:
            err(f"manifest: {k}: unknown role")
        if not set(d["regions"]) <= regions:
            err(f"manifest: {k}: unknown region")
        if d["status"] == "superseded" and not d["effective_to"]:
            err(f"manifest: {k}: superseded without effective_to")
        if d.get("supersedes") and d["supersedes"] not in [x["doc_key"] for x in m["documents"]]:
            err(f"manifest: {k}: supersedes unknown doc")
    texts = {k: (ROOT / d["source"]).read_text(encoding="utf-8") for k, d in docs.items()}
    return docs, texts


def visible(doc, user):
    return user["role"] in doc["allowed_roles"] and ("all" in doc["regions"] or user.get("region") in doc["regions"])


# ------------------------------------------------------------------- golden ---
def check_golden(docs, texts):
    items = load_jsonl(ROOT / "eval/golden_rag.jsonl")
    ids = [x["id"] for x in items]
    if len(ids) != len(set(ids)):
        err("golden: duplicate ids")
    for x in items:
        i = x["id"]
        if x["slice"] not in SLICES:
            err(f"golden {i}: unknown slice {x['slice']}")
        if x["expected_behavior"] not in BEHAVIOURS:
            err(f"golden {i}: unknown behaviour")
        if x["lang"] not in ("en", "ar"):
            err(f"golden {i}: unknown lang")
        for key in ("expected_sources", "alt_sources"):
            for doc_key, section in x.get(key, []):
                if doc_key not in docs:
                    err(f"golden {i}: unknown doc {doc_key}")
                    continue
                if not section_exists(texts[doc_key], section, docs[doc_key]["format"]):
                    err(f"golden {i}: section {doc_key} {section} not found")
                if key == "expected_sources" and not visible(docs[doc_key], x["user"]):
                    err(f"golden {i}: expects {doc_key}, which this user can't see")
        for item in x["must_include"]:
            if not matches(x["reference_answer"], item):
                err(f"golden {i}: must_include {item!r} not in its own reference answer")
        for item in x.get("must_not_include", []):
            if matches(x["reference_answer"], item) and x["expected_behavior"] != "refuse":
                err(f"golden {i}: must_not_include {item!r} appears in the reference answer")
        if x["slice"] == "follow_up" and not (x.get("turns") and x.get("standalone_query")):
            err(f"golden {i}: follow_up needs turns and standalone_query")
        if x["expected_behavior"] == "route_to_tool":
            if not x.get("expected_tools") or not set(x["expected_tools"]) <= TOOLS:
                err(f"golden {i}: route_to_tool needs valid expected_tools")
            if "session_employee_id" not in x["user"]:
                err(f"golden {i}: route_to_tool needs user.session_employee_id")
        if x["expected_behavior"] == "answer" and not x["expected_sources"]:
            err(f"golden {i}: answer without expected_sources")
    gates = json.loads((ROOT / "eval/gates.json").read_text(encoding="utf-8"))
    for name in ("smoke_set", "holdout_set"):
        for gid in gates[name]["ids"]:
            if gid not in ids:
                err(f"gates: {name} has unknown id {gid}")
    return items


# -------------------------------------------------------------------- agent ---
def check_agent():
    seed = json.loads((ROOT / "data/hris_seed.json").read_text(encoding="utf-8"))
    emp = {e["employee_id"] for e in seed["employees"]}
    for e in seed["employees"]:
        if e["manager_id"] and e["manager_id"] not in emp:
            err(f"hris: {e['employee_id']} has unknown manager")
    for b in seed["leave_balances"]:
        if b["employee_id"] not in emp:
            err(f"hris: balance for unknown {b['employee_id']}")
    for s in load_jsonl(ROOT / "eval/agent_scenarios.jsonl"):
        if s["session_employee_id"] not in emp:
            err(f"agent {s['id']}: unknown employee")
        for t in s.get("expected_tools", []) + s.get("must_not_call", []):
            if t not in TOOLS:
                err(f"agent {s['id']}: unknown tool {t}")
        for a in s.get("user_actions", []):
            if a not in ACTIONS:
                err(f"agent {s['id']}: unknown user action {a}")
    rules = json.loads((ROOT / "data/leave_rules.json").read_text(encoding="utf-8"))
    leave = (ROOT / "data/policies/leave_policy.md").read_text(encoding="utf-8")
    for key, val in rules.items():
        if isinstance(val, dict) and "source" in val:
            for sec in re.findall(r"leave_policy §(\d+\.\d+)", val["source"]):
                if not section_exists(leave, sec, "md"):
                    err(f"leave_rules {key}: cites missing leave_policy §{sec}")


# ---------------------------------------------------------------- screening ---
def check_screening():
    exp = json.loads((ROOT / "eval/screening_expectations.json").read_text(encoding="utf-8"))
    resumes = {p.stem for p in (ROOT / "data/resumes").glob("cand_*.txt")}
    if set(exp["candidates"]) != resumes:
        err("screening: expectations and resumes differ")
    rubric = json.loads((ROOT / "data/jobs/junior_data_analyst_rubric.json").read_text(encoding="utf-8"))
    ids = {c["id"] for c in rubric["criteria"]}
    if sum(c["weight"] for c in rubric["criteria"]) != rubric["max_score"]:
        err("rubric: weights don't add up to max_score")
    for cand, e in exp["candidates"].items():
        for f in e.get("must_flag", []):
            if f.startswith("missing_required:") and f.split(":", 1)[1] not in ids:
                err(f"screening {cand}: unknown criterion in {f}")
    cf = json.loads((ROOT / "eval/counterfactuals/manifest.json").read_text(encoding="utf-8"))
    for v in cf["variants"]:
        if not (ROOT / "eval/counterfactuals" / v["variant"]).exists():
            err(f"counterfactuals: missing {v['variant']}")


def main():
    docs, texts = check_manifest()
    items = check_golden(docs, texts)
    check_agent()
    check_screening()
    if ERRORS:
        print(f"{len(ERRORS)} problem(s):")
        for e in ERRORS:
            print(" -", e)
        sys.exit(1)
    print(f"OK: {len(docs)} documents, {len(items)} golden items, agent scenarios, screening and counterfactuals are consistent.")


if __name__ == "__main__":
    main()
