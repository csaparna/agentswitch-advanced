"""Offline tests: a local stub server stands in for the platform. No network, no login.

    cd 33-red-team/suite && python -m unittest discover -s tests -t .
"""
import importlib
import json
import os
import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from harness import bugs, client, runner
from harness.tasks import t01_auth_no_token as t01, t02_auth_tampered_token as t02

GOOD = "good-token-" + "x" * 32
JSON, SSE = "application/json", "text/event-stream"


def jr(result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": 1}
    msg.update({"error": error} if error else {"result": result})
    return json.dumps(msg)


def tool_text(obj, is_error=False):
    return jr({"content": [{"type": "text", "text": json.dumps(obj)}], "isError": is_error})


def strict(method, auth):
    """Like the platform: only the real token works."""
    if auth != f"Bearer {GOOD}":
        return 401, '{"error": "unauthorized"}', JSON
    if method == "tools/call":
        return 200, tool_text({"data": []}), JSON
    return 200, jr({"tools": []}), JSON


def open_server(method, auth):
    """Broken auth: every call works, with or without a token."""
    return strict(method, f"Bearer {GOOD}")


class Stub(BaseHTTPRequestHandler):
    handler = staticmethod(strict)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        code, body, ctype = Stub.handler(req["method"], self.headers.get("Authorization"))
        raw = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


class Base(unittest.TestCase):
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
        Stub.handler = staticmethod(strict)

    def serve(self, fn):
        Stub.handler = staticmethod(fn)

    def run_task(self, task, **env):
        return runner.run_one(task, {**self.env, **env})

    def assertInfra(self, r, text=""):
        self.assertFalse(r["passed"])
        self.assertTrue(r["evidence"].startswith("infrastructure:"), r["evidence"])
        self.assertIn(text, r["evidence"])


class AuthTasks(Base):
    def test_t01_passes_on_401(self):
        r = self.run_task(t01.TASK)
        self.assertTrue(r["passed"], r["evidence"])
        self.assertEqual(r["id"], "suryodaya:rt_auth_no_token")

    def test_t01_fails_when_open(self):
        self.serve(open_server)
        r = self.run_task(t01.TASK)
        self.assertFalse(r["passed"])
        self.assertIn("call accepted", r["evidence"])

    def test_t01_wrong_url_is_infrastructure(self):
        self.serve(lambda m, a: (404, "<html>not found</html>", "text/html"))
        self.assertInfra(self.run_task(t01.TASK), "control call")

    def test_t01_proxy_401_is_infrastructure(self):
        self.serve(lambda m, a: (401, "denied by proxy", "text/plain"))   # real token fails too
        self.assertInfra(self.run_task(t01.TASK), "control call")

    def test_t01_odd_status_is_infrastructure(self):
        self.serve(lambda m, a: strict(m, a) if a else (500, "oops", "text/plain"))
        self.assertInfra(self.run_task(t01.TASK), "neither refused with 401 nor accepted")

    def test_t02_passes_on_401(self):
        self.assertTrue(self.run_task(t02.TASK)["passed"])

    def test_t02_fails_when_changed_token_accepted(self):
        self.serve(open_server)
        r = self.run_task(t02.TASK)
        self.assertFalse(r["passed"])
        self.assertNotIn("infrastructure", r["evidence"])

    def test_t02_bad_real_token_is_infrastructure(self):
        self.serve(lambda m, a: (401, "{}", JSON))
        self.assertInfra(self.run_task(t02.TASK), "control call")

    def test_tamper(self):
        changed = t02.tamper(GOOD)
        self.assertEqual(len(changed), len(GOOD))
        self.assertNotEqual(changed, GOOD)
        self.assertNotEqual(t02.tamper("A" * 43), "A" * 43)


class Runner(Base):
    def test_missing_token_is_infrastructure(self):
        self.assertInfra(self.run_task(t02.TASK, AGENTSWITCH_TOKEN=None),
                         "AGENTSWITCH_TOKEN is not set")

    def test_network_error_is_infrastructure(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        self.assertInfra(self.run_task(t01.TASK, AGENTSWITCH_BASE_URL=f"http://127.0.0.1:{port}"),
                         "network error")

    def test_write_task_skipped_outside_harness(self):
        called = []
        task = {"id": "w", "title": "w", "writes": True,
                "run": lambda env: called.append(1) or {"passed": True}}
        self.assertIsNone(self.run_task(task))
        self.assertEqual(called, [])
        self.assertTrue(self.run_task(task, AGENTSWITCH_RUN_ID="run-1")["passed"])
        self.assertEqual(called, [1])

    def test_task_bug_is_infrastructure_and_hides_message(self):
        def boom(env):
            raise ValueError("secret-looking text")
        r = self.run_task({"id": "b", "title": "b", "run": boom})
        self.assertEqual(r["evidence"], "infrastructure: ValueError in task")

    def test_bad_result_shapes_are_infrastructure(self):
        for bad in [(True, 1.0), None, {"passed": "yes"}, {"passed": True, "score": "n/a"},
                    {"passed": True, "score": 2}, {"passed": True, "score": True},
                    {"passed": True, "score": 0.0}, {"passed": False, "score": 1.0}]:
            with self.subTest(bad=bad):
                self.assertInfra(self.run_task({"id": "s", "title": "s", "run": lambda env: bad}))

    def test_score_follows_passed_when_missing(self):
        for ret, score in [({"passed": True}, 1.0), ({"passed": False}, 0.0),
                           ({"passed": True, "score": None}, 1.0),
                           ({"passed": True, "score": 0.5}, 0.5)]:
            with self.subTest(ret=ret):
                r = self.run_task({"id": "s", "title": "s", "run": lambda env: ret})
                self.assertEqual(r["score"], score)

    def test_broken_task_file_does_not_stop_the_run(self):
        root = tempfile.mkdtemp()
        pkg = os.path.join(root, "fake_tasks_pkg")
        os.mkdir(pkg)
        files = {"__init__.py": "",
                 "t01_ok.py": "TASK = {'id': 'ok', 'title': 'ok', 'run': lambda env: {'passed': True}}\n",
                 "t02_syntax.py": "def broken(:\n",
                 "t03_import.py": "import no_such_module_xyz\n",
                 "t04_no_task.py": "x = 1\n"}
        for name, text in files.items():
            with open(os.path.join(pkg, name), "w", encoding="utf-8") as f:
                f.write(text)
        sys.path.insert(0, root)
        try:
            found = runner.discover(importlib.import_module("fake_tasks_pkg"))
        finally:
            sys.path.remove(root)
        results = [self.run_task(t) for t in found]
        self.assertEqual([r["id"].split(":")[1] for r in results],
                         ["ok", "t02_syntax", "t03_import", "t04_no_task"])
        self.assertTrue(results[0]["passed"])
        self.assertInfra(results[1], "could not be loaded (SyntaxError)")
        self.assertInfra(results[2], "could not be loaded (ModuleNotFoundError)")
        self.assertInfra(results[3], "has no valid TASK")

    def _main(self, extra_env=None):
        out = os.path.join(tempfile.mkdtemp(), "results.json")
        env = {k: v for k, v in {**self.env, **(extra_env or {})}.items() if v}
        # clear=True: nothing from the developer's shell (e.g. AGENTSWITCH_RUN_ID) leaks in
        with mock.patch.dict(os.environ, env, clear=True):
            runner.main(["--out", out])
        with open(out, encoding="utf-8") as f:
            return json.load(f)

    def test_results_file_shape(self):
        rep = self._main()
        expected = [t for t in runner.discover() if not t.get("writes")]
        self.assertEqual(len(rep["tasks"]), len(expected))
        self.assertRegex(rep["summary"], rf"^suryodaya: \d+/{len(expected)} tasks passed")
        for t in rep["tasks"]:
            self.assertEqual(set(t), {"id", "title", "passed", "score", "evidence"})
            self.assertTrue(t["id"].startswith("suryodaya:"))
            self.assertNotIn(GOOD, json.dumps(t))

    def test_skipped_write_tasks_not_counted(self):
        w = {"id": "w", "title": "w", "writes": True, "run": lambda env: {"passed": True}}
        with mock.patch.object(runner, "discover", return_value=[t01.TASK, w]):
            rep = self._main()
            self.assertEqual(rep["summary"], "suryodaya: 1/1 tasks passed; "
                                             "1 write task(s) not run (local run, not a harness copy)")
            self.assertEqual(rep["not_run"], ["suryodaya:w"])
            rep = self._main({"AGENTSWITCH_RUN_ID": "run-1"})   # harness run: nothing skipped
            self.assertEqual(rep["summary"], "suryodaya: 2/2 tasks passed")
            self.assertNotIn("not_run", rep)


class Client(Base):
    def test_refusal_codes(self):
        cases = [(jr(error={"code": -32602, "message": "x", "data": {"code": "tool_not_available"}}), True),
                 (jr(error={"code": -32001, "message": "x", "data": {"code": "permission_denied"}}), True),
                 (jr(error={"code": -32602, "message": "x", "data": {"code": "invalid_arguments"}}), False),
                 (tool_text({"code": "permission_denied"}, is_error=True), True),            # tool-level
                 (tool_text({"error": {"code": "tool_not_available"}}, is_error=True), True),
                 (tool_text({"code": "permission_denied"}, is_error=False), False),          # not an error
                 (tool_text({"data": []}), False)]                                           # empty 200
        for body, want in cases:
            with self.subTest(body=body):
                self.serve(lambda m, a, body=body: (200, body, JSON))
                self.assertEqual(client.refused(*client.tool(self.env, "Contract.list")), want)

    def test_sse_refusal_after_progress_event(self):
        stream = ('event: message\ndata: {"jsonrpc": "2.0", "method": "notifications/progress", '
                  '"params": {"progress": 1}}\n\n'
                  'event: message\ndata: ' + jr(error={"code": -32001, "message": "x",
                                                         "data": {"code": "permission_denied"}}) + '\n\n')
        self.serve(lambda m, a: (200, stream, SSE))
        self.assertTrue(client.refused(*client.tool(self.env, "Contract.list")))

    def test_sse_multiline_event_is_joined(self):
        msg = json.dumps(json.loads(jr({"tools": []})), indent=2)
        stream = "".join(f"data: {line}\n" for line in msg.splitlines()) + "\ndata: [DONE]\n\n"
        self.assertEqual(client._parse(stream), {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}})

    def test_odd_content_does_not_crash(self):
        for res in [{"content": None, "isError": False}, {"content": ["text"]},
                    {"content": [{"type": "text", "text": None}]}]:
            with self.subTest(res=res):
                self.serve(lambda m, a, res=res: (200, jr(res), JSON))
                st, data, err = client.tool(self.env, "Contract.list")
                self.assertEqual(st, 200)
                self.assertEqual(data, res)

    def test_bug_status_file(self):
        self.assertEqual(bugs.status("BUG-33-001"), "new")
        self.assertEqual(bugs.status("BUG-33-002"), "new")


if __name__ == "__main__":
    unittest.main()
