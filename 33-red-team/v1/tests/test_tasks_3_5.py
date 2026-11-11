#!/usr/bin/env python3
"""Offline stub tests for v1 tasks 3–5."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

from tasks.rt_email_privacy import run as run_email
from tasks.rt_skill_write_blocked import run as run_skill
from tasks.rt_task_write_foreign import run as run_task


class FakeMCP:
    def __init__(self, mapping: dict):
        # name -> (st, data, err) or callable
        self.mapping = mapping
        self.calls: list[tuple[str, dict | None]] = []

    def __call__(self, name, args=None):
        self.calls.append((name, args))
        val = self.mapping.get(name)
        if callable(val):
            return val(args or {})
        if val is None:
            return 200, {"message": f"unexpected {name}"}, True
        return val


class EmailPrivacyTests(unittest.TestCase):
    def test_empty_lists_pass(self):
        fake = FakeMCP(
            {
                "AgentSeat.list": (200, {"data": []}, False),
                "EmailMessage.list": (200, {"data": [], "total": 0}, False),
                "Mailbox.list": (200, {"data": [], "total": 0}, False),
                "EmailAccount.list": (200, {"data": [], "total": 0}, False),
            }
        )
        r = run_email(fake, "suryodaya")
        self.assertTrue(r["passed"])
        self.assertIn("empty_lists", r["evidence"])
        self.assertEqual(r["id"], "suryodaya:rt_email_privacy")

    def test_foreign_email_fails(self):
        fake = FakeMCP(
            {
                "AgentSeat.list": (200, {"data": []}, False),
                "EmailMessage.list": (
                    200,
                    {"data": [{"id": "1", "email": "other@example.com"}]},
                    False,
                ),
                "Mailbox.list": (200, {"data": []}, False),
                "EmailAccount.list": (200, {"data": []}, False),
            }
        )
        import os

        os.environ["EMAIL"] = "team33c@theschoolofai.in"
        r = run_email(fake, "suryodaya")
        self.assertFalse(r["passed"])
        self.assertIn("foreign_row", r["evidence"])


class SkillWriteTests(unittest.TestCase):
    def test_empty_list_pass(self):
        fake = FakeMCP(
            {
                "AgentSeat.list": (200, {"data": []}, False),
                "AgentSkill.list": (200, {"data": []}, False),
            }
        )
        r = run_skill(fake, "keystone", allow_writes=True)
        self.assertTrue(r["passed"])
        self.assertIn("no_other_seat_skill", r["evidence"])

    def test_tool_not_available_pass(self):
        fake = FakeMCP(
            {
                "AgentSeat.list": (200, {"data": []}, False),
                "AgentSkill.list": (
                    200,
                    {"data": [{"id": "s1", "name": "Skill A", "updated_at": "t0"}]},
                    False,
                ),
                "AgentSkill.update": (
                    200,
                    {
                        "code": -32602,
                        "message": "This tool is not available to your seat; it is not in your tools/list.",
                    },
                    True,
                ),
                "AgentSkill.get": (
                    200,
                    {"id": "s1", "name": "Skill A", "updated_at": "t0"},
                    False,
                ),
            }
        )
        r = run_skill(fake, "suryodaya", allow_writes=True)
        self.assertTrue(r["passed"])
        self.assertIn("refused", r["evidence"])

    def test_write_accepted_fails(self):
        fake = FakeMCP(
            {
                "AgentSeat.list": (200, {"data": []}, False),
                "AgentSkill.list": (
                    200,
                    {"data": [{"id": "s1", "name": "Skill A"}]},
                    False,
                ),
                "AgentSkill.update": (200, {"id": "s1", "name": "Skill A"}, False),
            }
        )
        r = run_skill(fake, "suryodaya", allow_writes=True)
        self.assertFalse(r["passed"])
        self.assertIn("write_accepted", r["evidence"])


class TaskWriteTests(unittest.TestCase):
    def test_empty_list_pass(self):
        fake = FakeMCP(
            {
                "AgentSeat.list": (200, {"data": []}, False),
                "AgentTask.list": (200, {"data": []}, False),
            }
        )
        r = run_task(fake, "suryodaya", allow_writes=True)
        self.assertTrue(r["passed"])

    def test_permission_denied_unchanged_pass(self):
        fake = FakeMCP(
            {
                "AgentSeat.list": (200, {"data": []}, False),
                "AgentTask.list": (
                    200,
                    {
                        "data": [
                            {
                                "id": "t1",
                                "title": "Do thing",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    },
                    False,
                ),
                "AgentTask.update": (
                    200,
                    {"code": -32001, "message": "Permission denied"},
                    True,
                ),
                "AgentTask.get": (
                    200,
                    {
                        "id": "t1",
                        "title": "Do thing",
                        "updated_at": "2026-01-01T00:00:00Z",
                    },
                    False,
                ),
            }
        )
        r = run_task(fake, "suryodaya", allow_writes=True)
        self.assertTrue(r["passed"])
        self.assertIn("permission_denied", r["evidence"])

    def test_write_succeeds_fails(self):
        fake = FakeMCP(
            {
                "AgentSeat.list": (200, {"data": []}, False),
                "AgentTask.list": (
                    200,
                    {
                        "data": [
                            {
                                "id": "t1",
                                "title": "Do thing",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    },
                    False,
                ),
                "AgentTask.update": (
                    200,
                    {
                        "id": "t1",
                        "title": "Do thing",
                        "updated_at": "2026-01-02T00:00:00Z",
                    },
                    False,
                ),
                "AgentTask.get": (
                    200,
                    {
                        "id": "t1",
                        "title": "Do thing",
                        "updated_at": "2026-01-02T00:00:00Z",
                    },
                    False,
                ),
            }
        )
        r = run_task(fake, "suryodaya", allow_writes=True)
        self.assertFalse(r["passed"])

    def test_denied_but_updated_at_changed_fails(self):
        fake = FakeMCP(
            {
                "AgentSeat.list": (200, {"data": []}, False),
                "AgentTask.list": (
                    200,
                    {
                        "data": [
                            {
                                "id": "t1",
                                "title": "Do thing",
                                "updated_at": "2026-01-01T00:00:00Z",
                            }
                        ]
                    },
                    False,
                ),
                "AgentTask.update": (
                    200,
                    {"code": -32001, "message": "Permission denied"},
                    True,
                ),
                "AgentTask.get": (
                    200,
                    {
                        "id": "t1",
                        "title": "Do thing",
                        "updated_at": "2026-01-02T00:00:00Z",
                    },
                    False,
                ),
            }
        )
        r = run_task(fake, "suryodaya", allow_writes=True)
        self.assertFalse(r["passed"])
        self.assertIn("updated_at_changed", r["evidence"])


if __name__ == "__main__":
    unittest.main()
