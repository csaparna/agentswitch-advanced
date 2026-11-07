"""Offline tests: a local stub server stands in for the platform. No network, no login.

    cd 33-red-team/suite && python -m unittest discover -s tests -t .
"""
import json
import os
import socket
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from harness import bugs, client, runner
from harness.tasks import t01_auth_no_token as t01, t02_auth_tampered_token as t02

GOOD = "good-token-" + "x" * 32


class Stub(BaseHTTPRequestHandler):
    mode = "strict"    # strict: only GOOD works; open: any request works; down: GOOD fails too
    refuse = None      # JSON-RPC error data code for tools/call, or None for an empty 200

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        auth = self.headers.get("Authorization")
        ok = {"strict": auth == f"Bearer {GOOD}", "open": True, "down": False}[self.mode]
        if not ok:
            return self._send(401, {"error": "unauthorized"})
        if req["method"] == "tools/call" and self.refuse:
            return self._send(200, {"jsonrpc": "2.0", "id": 1, "error": {
                "code": -32602, "message": "refused", "data": {"code": self.refuse}}})
        if req["method"] == "tools/call":
            text = json.dumps({"data": []})
            return self._send(200, {"jsonrpc": "2.0", "id": 1,
                                    "result": {"content": [{"type": "text", "text": text}]}})
        self._send(200, {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}})

    def _send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


class SuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.env = {"AGENTSWITCH_BASE_URL": f"http://127.0.0.1:{cls.srv.server_port}",
                   "AGENTSWITCH_TOKEN": GOOD, "AGENTSWITCH_INSTANCE": "suryodaya",
                   "AGENTSWITCH_RUN_ID": None}

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        Stub.mode, Stub.refuse = "strict", None

    def run_task(self, task, **env):
        return runner.run_one(task, {**self.env, **env})

    # Task 1
    def test_t01_passes_on_401(self):
        r = self.run_task(t01.TASK)
        self.assertTrue(r["passed"])
        self.assertEqual(r["id"], "suryodaya:rt_auth_no_token")

    def test_t01_fails_when_open(self):
        Stub.mode = "open"
        self.assertFalse(self.run_task(t01.TASK)["passed"])

    # Task 2
    def test_t02_passes_on_401(self):
        self.assertTrue(self.run_task(t02.TASK)["passed"])

    def test_t02_fails_when_changed_token_accepted(self):
        Stub.mode = "open"
        r = self.run_task(t02.TASK)
        self.assertFalse(r["passed"])
        self.assertNotIn("infrastructure", r["evidence"])

    def test_t02_bad_real_token_is_infrastructure(self):
        Stub.mode = "down"
        r = self.run_task(t02.TASK)
        self.assertFalse(r["passed"])
        self.assertTrue(r["evidence"].startswith("infrastructure:"))

    def test_tamper(self):
        changed = t02.tamper(GOOD)
        self.assertEqual(len(changed), len(GOOD))
        self.assertNotEqual(changed, GOOD)
        self.assertNotEqual(t02.tamper("A" * 43), "A" * 43)

    # Runner
    def test_missing_token_is_infrastructure(self):
        r = self.run_task(t02.TASK, AGENTSWITCH_TOKEN=None)
        self.assertFalse(r["passed"])
        self.assertIn("AGENTSWITCH_TOKEN is not set", r["evidence"])

    def test_network_error_is_infrastructure(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        r = self.run_task(t01.TASK, AGENTSWITCH_BASE_URL=f"http://127.0.0.1:{port}")
        self.assertTrue(r["evidence"].startswith("infrastructure: network error"))

    def test_write_task_not_run_outside_harness(self):
        called = []
        task = {"id": "w", "title": "w", "writes": True, "run": lambda env: called.append(1)}
        r = self.run_task(task)
        self.assertEqual(called, [])
        self.assertFalse(r["passed"])
        self.assertIn("not run: write task", r["evidence"])
        self.run_task(task, AGENTSWITCH_RUN_ID="run-1")
        self.assertEqual(called, [1])

    def test_task_bug_is_infrastructure_and_hides_message(self):
        def boom(env):
            raise ValueError("secret-looking text")
        r = self.run_task({"id": "b", "title": "b", "run": boom})
        self.assertEqual(r["evidence"], "infrastructure: ValueError in task")

    def test_results_file_shape(self):
        out = os.path.join(tempfile.mkdtemp(), "results.json")
        keep = dict(os.environ)
        try:
            os.environ.update({k: v for k, v in self.env.items() if v})
            runner.main(["--out", out])
        finally:
            os.environ.clear()
            os.environ.update(keep)
        with open(out, encoding="utf-8") as f:
            rep = json.load(f)
        self.assertEqual(rep["summary"], "suryodaya: 2/2 tasks passed")
        for t in rep["tasks"]:
            self.assertEqual(set(t), {"id", "title", "passed", "score", "evidence"})
            self.assertNotIn(GOOD, json.dumps(t))

    # Client helpers for later tasks
    def test_refused(self):
        Stub.refuse = "tool_not_available"
        self.assertTrue(client.refused(*client.tool(self.env, "Contract.list")))
        Stub.refuse = "permission_denied"
        self.assertTrue(client.refused(*client.tool(self.env, "Contract.list")))
        Stub.refuse = "invalid_arguments"
        self.assertFalse(client.refused(*client.tool(self.env, "Contract.list")))
        Stub.refuse = None   # an empty 200 is not a refusal
        self.assertFalse(client.refused(*client.tool(self.env, "Contract.list")))

    def test_bug_status_file(self):
        self.assertEqual(bugs.status("BUG-33-001"), "new")
        self.assertEqual(bugs.status("BUG-33-002"), "new")


if __name__ == "__main__":
    unittest.main()
