"""Tests for the hr-agent tutor skill.

Run from the skill folder:

    python -m unittest discover -s tests -v

Covers three things:
  * every relative link in the skill's Markdown resolves  (TestLinks)
  * the task catalog is internally consistent             (TestCatalog)
  * the helper does what progress-protocol.md says        (TestHelper, TestSpacing)
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import coach  # noqa: E402

TEMPLATE = SKILL_ROOT / "assets" / "project-template"

# [text](target) - skip absolute URLs, anchors and mailto.
LINK_RE = re.compile(r"\[[^\]]*\]\((?!https?://|#|mailto:)([^)\s]+)\)")


def markdown_files() -> list[Path]:
    files = [SKILL_ROOT / "SKILL.md"]
    files += sorted((SKILL_ROOT / "references").glob("*.md"))
    notices = SKILL_ROOT / "THIRD_PARTY_NOTICES.md"
    if notices.is_file():
        files.append(notices)
    return files


class TestLinks(unittest.TestCase):
    """The failure that made the shipped skill unusable: links to files that
    were never bundled. This test is the reason it cannot happen silently."""

    def test_every_relative_link_resolves(self):
        missing = []
        for md in markdown_files():
            text = md.read_text(encoding="utf-8")
            for target in LINK_RE.findall(text):
                target = target.split("#", 1)[0]
                if not target:
                    continue
                resolved = (md.parent / target).resolve()
                if not resolved.exists():
                    missing.append(f"{md.name} -> {target}")
        self.assertEqual([], missing, f"unresolved links: {missing}")

    def test_skill_md_has_frontmatter_name_and_description(self):
        text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"), "SKILL.md must open with YAML front matter")
        front = text.split("---", 2)[1]
        self.assertIn("name:", front)
        self.assertIn("description:", front)

    def test_referenced_helper_paths_exist(self):
        """Commands named in SKILL.md must point at files that are here."""
        for rel in ("scripts/coach.py", "tests/behavioral_cases.json"):
            self.assertTrue((SKILL_ROOT / rel).exists(), f"missing {rel}")


class TestCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(
            (TEMPLATE / "tasks" / "catalog.json").read_text(encoding="utf-8")
        )
        cls.tasks = cls.catalog["tasks"]
        cls.ids = [t["id"] for t in cls.tasks]

    def test_task_ids_unique(self):
        self.assertEqual(len(self.ids), len(set(self.ids)))

    def test_required_fields_present(self):
        for task in self.tasks:
            for field in ("id", "milestone", "title", "depends_on", "requirements", "acceptance"):
                self.assertIn(field, task, f"{task.get('id')} is missing {field}")
            self.assertIsInstance(task["bridge"], bool, f"{task['id']}: bridge must be a bool")

    def test_dependencies_resolve(self):
        known = set(self.ids)
        for task in self.tasks:
            for dep in task["depends_on"]:
                self.assertIn(dep, known, f"{task['id']} depends on unknown {dep}")

    def test_no_dependency_cycles(self):
        graph = {t["id"]: list(t["depends_on"]) for t in self.tasks}
        state: dict[str, int] = {}

        def visit(node: str, trail: list[str]):
            if state.get(node) == 2:
                return
            self.assertNotEqual(1, state.get(node), f"cycle: {' -> '.join(trail + [node])}")
            state[node] = 1
            for dep in graph[node]:
                visit(dep, trail + [node])
            state[node] = 2

        for task_id in graph:
            visit(task_id, [])

    def test_requirement_ids_unique_and_prefixed(self):
        seen = set()
        for task in self.tasks:
            for req in task["requirements"]:
                self.assertNotIn(req["id"], seen, f"duplicate requirement {req['id']}")
                seen.add(req["id"])
                self.assertTrue(
                    req["id"].startswith(task["id"] + "-"),
                    f"{req['id']} should start with {task['id']}-",
                )
                self.assertTrue(req["text"].strip(), f"{req['id']} has empty text")

    def test_only_bridge_tasks_are_marked_bridge(self):
        for task in self.tasks:
            if task["bridge"]:
                self.assertEqual("bridge", task["milestone"], f"{task['id']}")

    def test_every_milestone_has_tasks(self):
        milestones = {t["milestone"] for t in self.tasks}
        for expected in ("M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7"):
            self.assertIn(expected, milestones)


class WorkspaceCase(unittest.TestCase):
    """Builds a throwaway directory that looks enough like an HR-Agent checkout."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "docs").mkdir()
        (self.tmp / "eval").mkdir()
        (self.tmp / "docs" / "PLAN.md").write_text("# plan\n", encoding="utf-8")
        (self.tmp / "eval" / "gates.json").write_text("{}\n", encoding="utf-8")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_coach(self, *argv: str) -> int:
        return coach.main([*argv, "--project", str(self.tmp)])


class TestHelper(WorkspaceCase):
    def test_refuses_a_directory_that_is_not_a_checkout(self):
        other = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, other, ignore_errors=True)
        self.assertEqual(2, coach.main(["init", "--project", str(other)]))

    def test_init_scaffolds_and_never_overwrites(self):
        self.assertEqual(0, self.run_coach("init"))
        progress = self.tmp / "learning" / "progress.json"
        self.assertTrue(progress.is_file())
        self.assertTrue((self.tmp / "tasks" / "catalog.json").is_file())

        progress.write_text('{"schema_version":1,"mission":"mine","tasks":{}}', encoding="utf-8")
        self.assertEqual(0, self.run_coach("init"))
        self.assertIn("mine", progress.read_text(encoding="utf-8"))

    def test_workspace_discovery_walks_upward(self):
        nested = self.tmp / "a" / "b" / "c"
        nested.mkdir(parents=True)
        self.assertEqual(self.tmp.resolve(), coach.find_workspace(nested).resolve())

    def test_unknown_task_is_rejected(self):
        self.run_coach("init")
        self.assertEqual(2, self.run_coach("update", "--task", "NOPE-T99", "--status", "done"))

    def test_done_requires_evidence(self):
        self.run_coach("init")
        self.assertEqual(2, self.run_coach("update", "--task", "M0-T01", "--status", "done"))
        self.assertEqual(0, self.run_coach(
            "update", "--task", "M0-T01", "--status", "done",
            "--evidence", "mission written", "--observed",
        ))

    def test_hint_level_keeps_the_highest_rung(self):
        self.run_coach("init")
        self.run_coach("update", "--task", "M0-T01", "--hint-level", "3")
        self.run_coach("update", "--task", "M0-T01", "--hint-level", "1")
        data = json.loads((self.tmp / "learning" / "progress.json").read_text(encoding="utf-8"))
        self.assertEqual(3, data["tasks"]["M0-T01"]["hint_level"])

    def test_evidence_kind_tracks_who_ran_it(self):
        self.run_coach("init")
        self.run_coach("update", "--task", "M0-T01", "--evidence", "they said so")
        self.run_coach("update", "--task", "M0-T01", "--evidence", "I ran it", "--observed")
        data = json.loads((self.tmp / "learning" / "progress.json").read_text(encoding="utf-8"))
        kinds = [e["kind"] for e in data["tasks"]["M0-T01"]["evidence"]]
        self.assertEqual(["learner_reported", "observed"], kinds)

    def test_validate_catches_done_before_prerequisite(self):
        self.run_coach("init")
        path = self.tmp / "learning" / "progress.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["tasks"]["M1-T01"] = {
            "status": "done", "understanding": "unassessed", "hint_level": 0,
            "struggles": 0, "evidence": [{"kind": "observed", "text": "x", "date": "2026-09-27"}],
        }
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(1, self.run_coach("validate"))

    def test_validate_rejects_waiving_a_non_bridge_task(self):
        self.run_coach("init")
        path = self.tmp / "learning" / "progress.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["placement"] = {"status": "done", "date": "2026-09-27", "waived_tasks": ["M1-T01"]}
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(1, self.run_coach("validate"))

    def test_validate_accepts_waiving_a_bridge_task(self):
        self.run_coach("init")
        path = self.tmp / "learning" / "progress.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["placement"] = {"status": "done", "date": "2026-09-27", "waived_tasks": ["B-T01"]}
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(0, self.run_coach("validate"))

    def test_missing_review_json_is_treated_as_empty(self):
        self.run_coach("init")
        (self.tmp / "learning" / "review.json").unlink()
        self.assertEqual(0, self.run_coach("validate"))
        self.assertEqual(0, self.run_coach("status"))

    def test_coach_wrote_code_pins_rung_five_and_blocks_assessed(self):
        self.run_coach("init")
        self.assertEqual(0, self.run_coach("update", "--task", "M0-T01", "--coach-wrote-code"))
        data = json.loads((self.tmp / "learning" / "progress.json").read_text(encoding="utf-8"))
        entry = data["tasks"]["M0-T01"]
        self.assertTrue(entry["coach_wrote_code"])
        self.assertEqual(5, entry["hint_level"])
        self.assertEqual("unassessed", entry["understanding"])

        # The debt cannot be cleared by simply declaring understanding.
        self.assertEqual(2, self.run_coach(
            "update", "--task", "M0-T01", "--understanding", "assessed"))

    def test_validate_flags_coach_written_code_marked_assessed(self):
        self.run_coach("init")
        path = self.tmp / "learning" / "progress.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["tasks"]["M0-T01"] = {
            "status": "done", "understanding": "assessed", "hint_level": 5,
            "struggles": 0, "coach_wrote_code": True,
            "evidence": [{"kind": "observed", "text": "x", "date": "2026-09-27"}],
        }
        path.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(1, self.run_coach("validate"))

    def test_hint_level_five_is_legal_and_six_is_not(self):
        self.run_coach("init")
        self.assertEqual(0, self.run_coach("update", "--task", "M0-T01", "--hint-level", "5"))
        self.assertEqual(2, self.run_coach("update", "--task", "M0-T01", "--hint-level", "6"))

    def test_template_defaults_to_code_by_myself(self):
        self.run_coach("init")
        data = json.loads((self.tmp / "learning" / "progress.json").read_text(encoding="utf-8"))
        self.assertTrue(data["settings"]["code_by_myself"])

    def test_record_new_writes_front_matter(self):
        self.run_coach("init")
        self.assertEqual(0, self.run_coach(
            "record", "new", "--kind", "war-story", "--title", "2025 policy outranks 2026",
            "--task", "M2-T06", "--body", "It did.",
        ))
        files = list((self.tmp / "learning" / "records").glob("*.md"))
        self.assertEqual(1, len(files))
        text = files[0].read_text(encoding="utf-8")
        self.assertIn("kind: war-story", text)
        self.assertIn("tasks: [M2-T06]", text)


class TestSpacing(WorkspaceCase):
    """The schedule contract from references/retrieval-and-spacing.md.

    These fail until _next_interval is implemented. That is intentional: the
    growth curve is a design decision, and these five constraints are what any
    curve must satisfy.
    """

    def test_fail_returns_to_one_day(self):
        self.assertEqual(1, coach._next_interval("fail", streak=5, previous_interval=21))

    def test_pass_strictly_increases(self):
        for previous in (1, 2, 5, 13):
            nxt = coach._next_interval("pass", streak=1, previous_interval=previous)
            self.assertGreater(nxt, previous, f"pass must grow from {previous}")

    def test_partial_neither_grows_nor_resets(self):
        nxt = coach._next_interval("partial", streak=2, previous_interval=8)
        self.assertLessEqual(nxt, 8)
        self.assertGreater(nxt, 1)

    def test_result_is_a_bounded_positive_integer(self):
        for grade in coach.GRADES:
            for streak in (0, 3, 40):
                for previous in (1, 7, 400):
                    nxt = coach._next_interval(grade, streak, previous)
                    self.assertIsInstance(nxt, int)
                    self.assertGreaterEqual(nxt, 1)
                    self.assertLessEqual(nxt, coach.MAX_INTERVAL_DAYS)

    def test_is_deterministic(self):
        first = coach._next_interval("pass", 2, 6)
        for _ in range(5):
            self.assertEqual(first, coach._next_interval("pass", 2, 6))

    def test_grade_item_records_history_and_resets_streak_on_fail(self):
        item = {"id": "r0001", "interval_days": 10, "streak": 3, "history": []}
        coach.grade_item(item, "fail", on="2026-09-27")
        self.assertEqual(0, item["streak"])
        self.assertEqual("2026-09-28", item["due"])
        self.assertEqual("fail", item["history"][-1]["grade"])


class TestBehavioralCases(unittest.TestCase):
    def test_cases_file_is_well_formed(self):
        data = json.loads(
            (SKILL_ROOT / "tests" / "behavioral_cases.json").read_text(encoding="utf-8")
        )
        self.assertGreaterEqual(len(data["cases"]), 8)
        ids = [c["id"] for c in data["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        for case in data["cases"]:
            for field in ("id", "situation", "expected", "failure_looks_like"):
                self.assertTrue(str(case.get(field, "")).strip(), f"{case.get('id')}: {field}")


if __name__ == "__main__":
    unittest.main()
