#!/usr/bin/env python3
"""Learner-progress helper for the HR-Agent daily-practice-coach skill.

Standard library only. Reads and writes the learner state described in
references/progress-protocol.md:

    <workspace>/learning/progress.json
    <workspace>/learning/review.json
    <workspace>/learning/records/*.md

It records what the learner reports. It never runs their tests, and it never
proves anything passed.

Commands:
    init      scaffold learning/ and tasks/ into an existing HR-Agent checkout
    status    report recorded state and what to do next
    update    record task status, evidence, hint level, next action
    review    add | due | grade   (spaced retrieval prompts)
    record    new                 (write a records/ entry)
    validate  check recorded state against the catalog
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 1
SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_ROOT / "assets" / "project-template"

# A directory is an HR-Agent workspace when both of these are present.
WORKSPACE_MARKERS = (Path("docs") / "PLAN.md", Path("eval") / "gates.json")

TASK_STATUSES = ("not_started", "in_progress", "done", "waived")
UNDERSTANDING = ("unassessed", "assessed", "shaky")
EVIDENCE_KINDS = ("observed", "learner_reported")
PLACEMENT_STATUSES = ("none", "done", "declined")
GRADES = ("pass", "partial", "fail")
RECORD_KINDS = ("prior-knowledge", "decision", "war-story", "misconception", "milestone")

MAX_INTERVAL_DAYS = 60


class CoachError(Exception):
    """A problem the learner can act on."""


# --------------------------------------------------------------------------
# workspace discovery
# --------------------------------------------------------------------------

def is_workspace(path: Path) -> bool:
    return all((path / marker).is_file() for marker in WORKSPACE_MARKERS)


def find_workspace(start: Path | None = None) -> Path:
    """Walk upward looking for the markers.

    Deliberately a sentinel search, not a fixed number of levels up from this
    file: the skill's install depth varies and counting levels breaks silently.
    """
    current = (start or Path.cwd()).resolve()
    for candidate in [current, *current.parents]:
        if is_workspace(candidate):
            return candidate
    raise CoachError(
        "No HR-Agent workspace found (looked for docs/PLAN.md and eval/gates.json "
        f"in {current} and its parents). Pass --project PATH."
    )


def resolve_project(arg: str | None) -> Path:
    if arg:
        path = Path(arg).expanduser().resolve()
        if not path.is_dir():
            raise CoachError(f"Not a directory: {path}")
        if not is_workspace(path):
            raise CoachError(
                f"{path} is not an HR-Agent checkout "
                "(needs docs/PLAN.md and eval/gates.json)."
            )
        return path
    return find_workspace()


# --------------------------------------------------------------------------
# io
# --------------------------------------------------------------------------

def today() -> str:
    return _dt.date.today().isoformat()


def read_json(path: Path, default=None):
    if not path.is_file():
        if default is None:
            raise CoachError(f"Missing file: {path}")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CoachError(f"{path} is not valid JSON: {exc}") from exc


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def progress_path(project: Path) -> Path:
    return project / "learning" / "progress.json"


def review_path(project: Path) -> Path:
    return project / "learning" / "review.json"


def load_progress(project: Path) -> dict:
    data = read_json(progress_path(project))
    data.setdefault("tasks", {})
    data.setdefault("settings", {})
    data.setdefault("placement", {"status": "none", "date": None, "waived_tasks": []})
    return data


def load_review(project: Path) -> dict:
    # A missing review.json is an empty review set, not an error.
    return read_json(review_path(project), {"schema_version": SCHEMA_VERSION, "items": []})


def load_catalog(project: Path) -> dict:
    local = project / "tasks" / "catalog.json"
    if local.is_file():
        return read_json(local)
    bundled = TEMPLATE / "tasks" / "catalog.json"
    if bundled.is_file():
        return read_json(bundled)
    raise CoachError("No tasks/catalog.json in the workspace and none bundled.")


def catalog_index(catalog: dict) -> dict[str, dict]:
    return {task["id"]: task for task in catalog.get("tasks", [])}


# --------------------------------------------------------------------------
# spacing
# --------------------------------------------------------------------------

def _next_interval(grade: str, streak: int, previous_interval: int) -> int:
    """Days until this review item is due again.

    Contract (references/retrieval-and-spacing.md) - the rest of the system
    relies on all five holding:

      1. A 'fail' returns to 1 day.
      2. A 'pass' strictly increases the interval.
      3. A 'partial' neither grows nor resets - it holds roughly where it is.
      4. Returns an integer >= 1, capped at MAX_INTERVAL_DAYS.
      5. Pure and deterministic.

    `streak` is the count of consecutive passes BEFORE this grade.
    `previous_interval` is the interval that was just served (>= 1).

    The curve is deliberately cautious for the first two passes and steeper
    once an item has demonstrably stuck. The payoff here is recall weeks
    later under interview pressure, so forgetting between looks costs more
    than spending an extra minute on review.

    Constraint 2 yields to constraint 4 at the ceiling: at MAX_INTERVAL_DAYS
    an item is effectively retired from the queue and stops growing.
    """
    previous = max(1, int(previous_interval))

    if grade == "fail":
        nxt = 1
    elif grade == "partial":
        # Hold roughly where it is: a small pullback, never a reset to 1.
        nxt = max(2, math.ceil(previous * 0.8))
        if previous >= 2:
            nxt = min(nxt, previous)
    else:  # pass
        factor = 2.0 if streak == 0 else (2.2 if streak == 1 else 2.5)
        nxt = max(previous + 1, math.ceil(previous * factor))

    return max(1, min(int(nxt), MAX_INTERVAL_DAYS))


def grade_item(item: dict, grade: str, on: str | None = None) -> dict:
    if grade not in GRADES:
        raise CoachError(f"Grade must be one of {', '.join(GRADES)}")
    on = on or today()
    streak = int(item.get("streak", 0))
    previous = max(1, int(item.get("interval_days", 1)))

    interval = _next_interval(grade, streak, previous)
    interval = max(1, min(int(interval), MAX_INTERVAL_DAYS))

    item["streak"] = streak + 1 if grade == "pass" else 0
    item["interval_days"] = interval
    item["due"] = (_dt.date.fromisoformat(on) + _dt.timedelta(days=interval)).isoformat()
    item.setdefault("history", []).append({"date": on, "grade": grade})
    return item


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------

def cmd_init(args) -> int:
    target = Path(args.project).expanduser().resolve() if args.project else Path.cwd().resolve()
    if not target.is_dir():
        raise CoachError(f"Not a directory: {target}")
    if not is_workspace(target):
        raise CoachError(
            f"{target} does not look like an HR-Agent checkout "
            "(needs docs/PLAN.md and eval/gates.json). Refusing to scaffold."
        )
    if not TEMPLATE.is_dir():
        raise CoachError(
            "assets/project-template/ is missing from this skill copy; nothing to scaffold."
        )

    created, skipped = [], []
    for src in sorted(TEMPLATE.rglob("*")):
        if src.is_dir():
            continue
        dest = target / src.relative_to(TEMPLATE)
        if dest.exists():
            skipped.append(dest.relative_to(target))
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        created.append(dest.relative_to(target))

    for path in created:
        print(f"created  {path.as_posix()}")
    for path in skipped:
        print(f"kept     {path.as_posix()} (already present)")
    if not created:
        print("Nothing to create; the workspace was already scaffolded.")
    return 0


def _ready_tasks(progress: dict, index: dict) -> list[str]:
    tasks = progress.get("tasks", {})
    waived = set(progress.get("placement", {}).get("waived_tasks", []))

    def settled(task_id: str) -> bool:
        return tasks.get(task_id, {}).get("status") in ("done", "waived") or task_id in waived

    ready = []
    for task_id, task in index.items():
        if settled(task_id):
            continue
        if all(settled(dep) for dep in task.get("depends_on", [])):
            ready.append(task_id)
    return sorted(ready)


def cmd_status(args) -> int:
    project = resolve_project(args.project)
    progress = load_progress(project)
    review = load_review(project)
    index = catalog_index(load_catalog(project))
    now = today()

    print(f"workspace: {project}")
    print(f"catalog:   {len(index)} tasks")
    if progress.get("settings", {}).get("code_by_myself", True):
        print("mode:      code_by_myself ON - the coach directs and reviews; you write the code.")
    else:
        print("mode:      code_by_myself OFF - the coach may write project code on request.")
    print()

    # priority 1 - mission
    if not progress.get("mission"):
        print("GATE  Mission not set -> start M0-T01.")
        return 0

    # priority 2 - placement
    placement = progress.get("placement", {})
    if placement.get("status") == "none":
        print("GATE  No placement on record -> offer M0-T02 once.")

    # priority 3 - overdue reviews
    overdue = [i for i in review.get("items", []) if i.get("due", "9999-12-31") <= now]
    last_failed = False
    for item in review.get("items", []):
        history = item.get("history") or []
        if history and history[-1].get("grade") == "fail":
            last_failed = True
    if len(overdue) >= 2 or last_failed:
        print(f"OFFER Review before new material ({len(overdue)} due"
              f"{', last retrieval failed' if last_failed else ''}).")
    elif overdue:
        print(f"OFFER Warm-up available ({len(overdue)} review item due).")

    # priority 4 - unassessed understanding
    unassessed = [
        task_id for task_id, task in progress.get("tasks", {}).items()
        if task.get("status") == "done" and task.get("understanding") == "unassessed"
    ]
    if unassessed:
        print(f"OFFER Teach-back for {len(unassessed)} done-but-unassessed task(s): "
              f"{', '.join(sorted(unassessed)[:5])}")

    # The code-by-myself contract: anything the coach wrote owes a teach-back.
    coach_written = [
        task_id for task_id, task in progress.get("tasks", {}).items()
        if task.get("coach_wrote_code")
    ]
    if coach_written:
        print(f"DEBT  Coach wrote project code for {len(coach_written)} task(s): "
              f"{', '.join(sorted(coach_written))}")
        print("      These owe a teach-back or a variation before they count as yours.")

    print()
    in_progress = [
        task_id for task_id, task in progress.get("tasks", {}).items()
        if task.get("status") == "in_progress"
    ]
    if in_progress:
        print("in progress:")
        for task_id in sorted(in_progress):
            entry = progress["tasks"][task_id]
            title = index.get(task_id, {}).get("title", "?")
            print(f"  {task_id}  {title}")
            if entry.get("next_action"):
                print(f"            next: {entry['next_action']}")

    ready = _ready_tasks(progress, index)
    if ready:
        print("dependency-ready:")
        for task_id in ready[:8]:
            task = index[task_id]
            bridge = " [bridge]" if task.get("bridge") else ""
            print(f"  {task_id}  {task['title']}{bridge}")
        if len(ready) > 8:
            print(f"  ... and {len(ready) - 8} more")
    else:
        print("No dependency-ready tasks. Everything is done, waived, or blocked.")

    print()
    print("Note: this reads recorded state only. It does not prove any test passed.")
    return 0


def cmd_update(args) -> int:
    project = resolve_project(args.project)
    progress = load_progress(project)
    index = catalog_index(load_catalog(project))

    if args.task not in index:
        raise CoachError(f"Unknown task {args.task}. Not in the catalog.")

    entry = progress["tasks"].setdefault(args.task, {
        "status": "not_started",
        "understanding": "unassessed",
        "hint_level": 0,
        "struggles": 0,
        "coach_wrote_code": False,
        "evidence": [],
        "next_action": "",
    })

    if args.status:
        if args.status not in TASK_STATUSES:
            raise CoachError(f"--status must be one of {', '.join(TASK_STATUSES)}")
        entry["status"] = args.status

    if args.understanding:
        if args.understanding not in UNDERSTANDING:
            raise CoachError(f"--understanding must be one of {', '.join(UNDERSTANDING)}")
        entry["understanding"] = args.understanding

    if args.evidence:
        entry.setdefault("evidence", []).append({
            "kind": "observed" if args.observed else "learner_reported",
            "text": args.evidence,
            "date": today(),
        })

    if args.hint_level is not None:
        if not 0 <= args.hint_level <= 5:
            raise CoachError("--hint-level must be 0-5")
        # Record the highest rung reached, never a lower one.
        entry["hint_level"] = max(int(entry.get("hint_level", 0)), args.hint_level)

    if args.coach_wrote_code:
        # The code-by-myself contract: if the coach wrote project code for
        # this task, that is permanent state. Understanding cannot be
        # 'assessed' off the back of it, and rung 5 is recorded.
        entry["coach_wrote_code"] = True
        entry["hint_level"] = 5
        entry["understanding"] = "unassessed"

    if args.struggle:
        entry["struggles"] = int(entry.get("struggles", 0)) + 1

    if args.next:
        entry["next_action"] = args.next

    entry["updated"] = today()

    if entry.get("coach_wrote_code") and (
        args.understanding == "assessed" or entry.get("understanding") == "assessed"
    ):
        raise CoachError(
            f"{args.task}: the coach wrote project code for this task, so understanding "
            "cannot be 'assessed' off the back of it. Pass a teach-back or a variation "
            "first, then clear coach_wrote_code by hand."
        )

    if entry["status"] == "done" and not entry.get("evidence"):
        raise CoachError(
            f"{args.task} cannot be 'done' with no evidence. "
            "Record a command and its output first (--evidence, plus --observed if you ran it)."
        )

    write_json(progress_path(project), progress)
    print(f"{args.task}: status={entry['status']} understanding={entry['understanding']} "
          f"hint_level={entry['hint_level']} struggles={entry['struggles']}")
    return 0


def _next_review_id(review: dict) -> str:
    used = {i.get("id", "") for i in review.get("items", [])}
    n = 1
    while f"r{n:04d}" in used:
        n += 1
    return f"r{n:04d}"


def cmd_review(args) -> int:
    project = resolve_project(args.project)
    review = load_review(project)
    now = today()

    if args.review_cmd == "add":
        item = {
            "id": _next_review_id(review),
            "prompt": args.prompt,
            "answer": args.answer,
            "source_task": args.task,
            "created": now,
            "due": (_dt.date.fromisoformat(now) + _dt.timedelta(days=1)).isoformat(),
            "interval_days": 1,
            "streak": 0,
            "history": [],
        }
        review.setdefault("items", []).append(item)
        write_json(review_path(project), review)
        print(f"added {item['id']} (due {item['due']})")
        return 0

    if args.review_cmd == "due":
        due = [i for i in review.get("items", []) if i.get("due", "9999-12-31") <= now]
        if not due:
            print("Nothing due. Offer a kata instead.")
            return 0
        print(f"{len(due)} due; offer one or two, never the whole list:")
        for item in due:
            print(f"  {item['id']}  [{item.get('source_task', '-')}]  {item['prompt']}")
        return 0

    if args.review_cmd == "grade":
        for item in review.get("items", []):
            if item.get("id") == args.id:
                grade_item(item, args.grade)
                write_json(review_path(project), review)
                print(f"{args.id}: {args.grade} -> next due {item['due']} "
                      f"(interval {item['interval_days']}d, streak {item['streak']})")
                return 0
        raise CoachError(f"No review item with id {args.id}")

    raise CoachError("Unknown review subcommand")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "record"


def cmd_record(args) -> int:
    project = resolve_project(args.project)
    if args.kind not in RECORD_KINDS:
        raise CoachError(f"--kind must be one of {', '.join(RECORD_KINDS)}")

    records = project / "learning" / "records"
    records.mkdir(parents=True, exist_ok=True)
    path = records / f"{today()}-{slugify(args.title)}.md"
    if path.exists():
        raise CoachError(f"{path} already exists; edit it instead of overwriting.")

    tasks = f"[{', '.join(args.task)}]" if args.task else "[]"
    body = args.body or "<!-- Write this from the trace or the conversation, while it is fresh. -->"
    path.write_text(
        f"---\nkind: {args.kind}\ndate: {today()}\ntasks: {tasks}\n---\n\n"
        f"# {args.title}\n\n{body}\n",
        encoding="utf-8",
    )
    print(f"created {path.relative_to(project).as_posix()}")
    return 0


def cmd_validate(args) -> int:
    project = resolve_project(args.project)
    progress = load_progress(project)
    review = load_review(project)
    index = catalog_index(load_catalog(project))
    problems: list[str] = []

    placement = progress.get("placement", {})
    if placement.get("status") not in PLACEMENT_STATUSES:
        problems.append(f"placement.status {placement.get('status')!r} is not a legal value")

    waived = placement.get("waived_tasks", [])
    for task_id in waived:
        if task_id not in index:
            problems.append(f"waived task {task_id} is not in the catalog")
        elif not index[task_id].get("bridge"):
            problems.append(f"{task_id} is waived but is not a bridge task")

    settled = set(waived)
    for task_id, entry in progress.get("tasks", {}).items():
        if entry.get("status") in ("done", "waived"):
            settled.add(task_id)

    for task_id, entry in sorted(progress.get("tasks", {}).items()):
        if task_id not in index:
            problems.append(f"{task_id} is in progress.json but not in the catalog")
            continue
        if entry.get("status") not in TASK_STATUSES:
            problems.append(f"{task_id}: status {entry.get('status')!r} is not legal")
        if entry.get("understanding") not in UNDERSTANDING:
            problems.append(f"{task_id}: understanding {entry.get('understanding')!r} is not legal")
        hint = entry.get("hint_level", 0)
        if not isinstance(hint, int) or not 0 <= hint <= 5:
            problems.append(f"{task_id}: hint_level {hint!r} is out of range 0-5")
        if entry.get("coach_wrote_code") and entry.get("understanding") == "assessed":
            problems.append(
                f"{task_id}: coach_wrote_code is set but understanding is 'assessed'; "
                "generated code is not evidence of understanding"
            )
        for ev in entry.get("evidence", []):
            if ev.get("kind") not in EVIDENCE_KINDS:
                problems.append(f"{task_id}: evidence kind {ev.get('kind')!r} is not legal")
        if entry.get("status") == "done":
            if not entry.get("evidence"):
                problems.append(f"{task_id} is done with no evidence")
            for dep in index[task_id].get("depends_on", []):
                if dep not in settled:
                    problems.append(f"{task_id} is done but prerequisite {dep} is not")

    for item in review.get("items", []):
        for field in ("id", "prompt", "answer", "due"):
            if not item.get(field):
                problems.append(f"review item {item.get('id', '?')} is missing {field}")
        try:
            _dt.date.fromisoformat(item.get("due", ""))
        except ValueError:
            problems.append(f"review item {item.get('id', '?')}: due {item.get('due')!r} is not a date")
        interval = item.get("interval_days", 1)
        if not isinstance(interval, int) or interval < 1:
            problems.append(f"review item {item.get('id', '?')}: interval_days must be >= 1")
        for entry in item.get("history", []):
            if entry.get("grade") not in GRADES:
                problems.append(f"review item {item.get('id', '?')}: grade {entry.get('grade')!r} is not legal")

    if problems:
        for problem in problems:
            print(f"FAIL {problem}")
        print(f"\n{len(problems)} problem(s).")
        return 1

    print(f"OK  {len(progress.get('tasks', {}))} task entries, "
          f"{len(review.get('items', []))} review items, no problems.")
    return 0


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="coach.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    # --project has to live on every *leaf* parser: once a nested subcommand
    # takes over (e.g. `review grade`), the parent's options are no longer
    # accepted after it on the command line.
    proj = argparse.ArgumentParser(add_help=False)
    proj.add_argument("--project", help="workspace path (default: search upward from cwd)")

    def with_project(p):
        return p

    sub.add_parser("init", parents=[proj], help="scaffold learning/ and tasks/").set_defaults(func=cmd_init)
    sub.add_parser("status", parents=[proj], help="recorded state and what to do next").set_defaults(func=cmd_status)

    p_update = with_project(sub.add_parser("update", parents=[proj], help="record task progress"))
    p_update.add_argument("--task", required=True)
    p_update.add_argument("--status", choices=TASK_STATUSES)
    p_update.add_argument("--understanding", choices=UNDERSTANDING)
    p_update.add_argument("--evidence", help="a command and its output, or a test name")
    p_update.add_argument("--observed", action="store_true",
                          help="you ran it yourself; otherwise it is learner_reported")
    p_update.add_argument("--hint-level", type=int, dest="hint_level",
                          help="0-5; the highest rung reached is kept")
    p_update.add_argument("--coach-wrote-code", action="store_true", dest="coach_wrote_code",
                          help="the coach wrote project code for this task "
                               "(records rung 5; understanding stays unassessed)")
    p_update.add_argument("--struggle", action="store_true")
    p_update.add_argument("--next", help="the next action")
    p_update.set_defaults(func=cmd_update)

    p_review = sub.add_parser("review", help="spaced retrieval prompts")
    rsub = p_review.add_subparsers(dest="review_cmd", required=True)
    p_add = rsub.add_parser("add", parents=[proj])
    p_add.add_argument("--prompt", required=True)
    p_add.add_argument("--answer", required=True)
    p_add.add_argument("--task", default=None)
    rsub.add_parser("due", parents=[proj])
    p_grade = rsub.add_parser("grade", parents=[proj])
    p_grade.add_argument("--id", required=True)
    p_grade.add_argument("--grade", required=True, choices=GRADES)
    p_review.set_defaults(func=cmd_review)

    p_record = sub.add_parser("record", help="write a records/ entry")
    rec = p_record.add_subparsers(dest="record_cmd", required=True)
    p_new = rec.add_parser("new", parents=[proj])
    p_new.add_argument("--kind", required=True, choices=RECORD_KINDS)
    p_new.add_argument("--title", required=True)
    p_new.add_argument("--task", action="append", default=[])
    p_new.add_argument("--body", default=None)
    p_record.set_defaults(func=cmd_record)

    sub.add_parser("validate", parents=[proj], help="check recorded state").set_defaults(func=cmd_validate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CoachError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except NotImplementedError as exc:
        print(f"error: {exc}", file=sys.stderr)
        print("hint: see references/retrieval-and-spacing.md for the schedule contract.",
              file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
