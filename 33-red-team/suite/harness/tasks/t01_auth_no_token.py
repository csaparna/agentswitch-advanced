"""Task 1 (owner: Ramesh). An MCP call with no token must be refused with HTTP 401.
Read-only: one tools/list call. No record is read or changed."""
from harness import client


def run(env):
    st, _ = client.rpc(env, "tools/list", tok=None)
    passed = st == 401
    return {"passed": passed, "score": 1.0 if passed else 0.0,
            "evidence": f"verifier=http_status; tools/list with no token -> HTTP {st}; expected 401"}


TASK = {"id": "rt_auth_no_token", "title": "MCP call with no token is refused (401)", "run": run}
