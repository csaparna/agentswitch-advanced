"""Task 2 (owner: Ramesh). Our token with a few characters changed must be refused with
HTTP 401. Tokens are opaque, not JWTs. Read-only: two tools/list calls.

A control call with the real token comes first. If the real token does not work,
a 401 for the changed one proves nothing, so that is reported as infrastructure."""
from harness import client


def tamper(tok):
    """Change 4 characters in the middle. Same length, never equal to the original."""
    if len(tok) < 8:
        raise client.InfraError("AGENTSWITCH_TOKEN is too short to change")
    i = len(tok) // 2 - 2
    mid = "".join("B" if c == "A" else "A" for c in tok[i:i + 4])
    return tok[:i] + mid + tok[i + 4:]


def run(env):
    tok = client.token(env)
    st, _ = client.rpc(env, "tools/list", tok=tok)
    if st != 200:
        raise client.InfraError(f"control call with the real token returned HTTP {st}; "
                                "token missing or expired?")
    st, _ = client.rpc(env, "tools/list", tok=tamper(tok))
    passed = st == 401
    return {"passed": passed, "score": 1.0 if passed else 0.0,
            "evidence": f"verifier=http_status; real token -> HTTP 200 (control); "
                        f"changed token -> HTTP {st}; expected 401"}


TASK = {"id": "rt_auth_tampered_token", "title": "MCP call with a changed token is refused (401)",
        "run": run}
