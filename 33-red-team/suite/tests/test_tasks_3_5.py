"""Offline tests for tasks 3–5 (Padmanabh). Uses the same stub server as test_suite.

    cd 33-red-team/suite && python -m unittest discover -s tests -t .
"""
import json
import unittest

from harness.tasks import t03_email_privacy as t03
from harness.tasks import t04_skill_write_blocked as t04
from harness.tasks import t05_task_write_foreign as t05
from tests.test_suite import JSON, Base, GOOD, jr, tool_text


def _parse_call(raw):
    req = json.loads(raw)
    args = (req.get("params") or {}).get("arguments") or {}
    name = (req.get("params") or {}).get("name")
    return name, args


class Tasks35(Base):
    def test_flags(self):
        self.assertFalse(t03.TASK["copy_only"])
        self.assertTrue(t04.TASK["copy_only"])
        self.assertTrue(t05.TASK["copy_only"])

    def test_t03_empty_lists_pass(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method == "tools/call":
                return 200, tool_text({"data": [], "total": 0}), JSON
            return 200, jr({"tools": []}), JSON

        self.serve(h)
        r = self.run_task(t03.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertEqual(r["id"], "suryodaya:rt_email_privacy")
        self.assertIn("empty_lists", r["evidence"])

    def test_t03_foreign_email_fails(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            # EmailMessage.list returns a foreign address; others empty
            return 200, tool_text(
                {"data": [{"id": "1", "email": "other@example.com"}]}
            ), JSON

        self.serve(h)
        r = self.run_task(t03.TASK, EMAIL="team33c@theschoolofai.in")
        self.assertFalse(r["passed"], r["evidence"])
        self.assertIn("foreign_row", r["evidence"])

    def test_t04_empty_list_pass(self):
        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method == "tools/call":
                return 200, tool_text({"data": []}), JSON
            return 200, jr({"tools": []}), JSON

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("no_other_seat_skill", r["evidence"])

    def test_t04_tool_not_available_pass(self):
        state = {"phase": "list"}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            # Read body via side channel: Stub only passes method/auth.
            # Alternate responses by call count.
            n = state.get("n", 0)
            state["n"] = n + 1
            if n == 0:  # list
                return 200, tool_text(
                    {"data": [{"id": "s1", "name": "Skill A", "updated_at": "t0"}]}
                ), JSON
            if n == 1:  # update
                return 200, jr(
                    error={
                        "code": -32602,
                        "message": "not in your tools/list",
                        "data": {"code": "tool_not_available"},
                    }
                ), JSON
            return 200, tool_text(
                {"id": "s1", "name": "Skill A", "updated_at": "t0"}
            ), JSON  # get

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("refused", r["evidence"])

    def test_t04_write_accepted_fails(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text({"data": [{"id": "s1", "name": "Skill A"}]}), JSON
            return 200, tool_text({"id": "s1", "name": "Skill A"}), JSON

        self.serve(h)
        r = self.run_task(t04.TASK)
        self.assertFalse(r["passed"], r["evidence"])
        self.assertIn("write_accepted", r["evidence"])

    def test_t05_permission_denied_unchanged_pass(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "t1",
                                "title": "Do",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                ), JSON
            if n == 1:
                return 200, jr(
                    error={
                        "code": -32001,
                        "message": "Permission denied",
                        "data": {"code": "permission_denied"},
                    }
                ), JSON
            return 200, tool_text(
                {
                    "id": "t1",
                    "title": "Do",
                    "updated_at": "2026-01-01T00:00:00Z",
                }
            ), JSON

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertIn("permission_denied", r["evidence"])

    def test_t05_write_succeeds_fails(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "t1",
                                "title": "Do",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                ), JSON
            return 200, tool_text(
                {
                    "id": "t1",
                    "title": "Do",
                    "updated_at": "2026-01-02T00:00:00Z",
                }
            ), JSON

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertFalse(r["passed"], r["evidence"])
        self.assertIn("write_not_denied", r["evidence"])

    def test_t05_denied_but_updated_at_changed_fails(self):
        state = {"n": 0}

        def h(method, auth):
            if auth != f"Bearer {GOOD}":
                return 401, "{}", JSON
            if method != "tools/call":
                return 200, jr({"tools": []}), JSON
            n = state["n"]
            state["n"] = n + 1
            if n == 0:
                return 200, tool_text(
                    {
                        "data": [
                            {
                                "id": "t1",
                                "title": "Do",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    }
                ), JSON
            if n == 1:
                return 200, jr(
                    error={
                        "code": -32001,
                        "message": "Permission denied",
                        "data": {"code": "permission_denied"},
                    }
                ), JSON
            return 200, tool_text(
                {
                    "id": "t1",
                    "title": "Do",
                    "updated_at": "2026-01-02T00:00:00Z",
                }
            ), JSON

        self.serve(h)
        r = self.run_task(t05.TASK)
        self.assertFalse(r["passed"], r["evidence"])
        self.assertIn("updated_at_changed", r["evidence"])

    def test_copy_only_tasks_skipped_locally(self):
        from tests.test_suite import Runner

        rep = Runner._main(self, {"AGENTSWITCH_RUN_ID": None})
        self.assertIn("suryodaya:rt_skill_write_blocked", rep["not_run"])
        self.assertIn("suryodaya:rt_task_write_foreign", rep["not_run"])
        # email privacy is read-only and should run
        ids = [t["id"] for t in rep["tasks"]]
        self.assertIn("suryodaya:rt_email_privacy", ids)


if __name__ == "__main__":
    unittest.main()
