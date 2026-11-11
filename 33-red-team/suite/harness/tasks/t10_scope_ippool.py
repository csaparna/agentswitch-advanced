"""Task 10 (owner: csaparna). Tracks BUG-33-001: low-privilege seat reading
email IP-pool configuration.

Read-only: one tool call.
Passes if the call is refused (BUG-33-001 fixed), or if BUG-33-001 is recorded
as not fixed in bug-status.json (status in {new, open, wont_fix}). Fails if
marked fixed but data is still returned (regression caught).
"""
from harness import bugs, client


def run(env):
    st_bug = bugs.status("BUG-33-001")
    st, data, is_error = client.tool(env, "IPPool.list", {"limit": 5})
    if st >= 500:
        raise client.InfraError(f"server error HTTP {st}")

    is_refused = client.refused(st, data, is_error)
    code = client.error_code(data) if is_error else None

    if is_refused:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": f"verifier=refusal; IPPool.list refused -> HTTP {st}, code={code}; BUG-33-001 fixed",
        }

    # Data or accepted response returned
    if st_bug in {"new", "open", "wont_fix"}:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": f"verifier=bug_status; BUG-33-001 status={st_bug}; call succeeded (HTTP {st}) as expected for open bug",
        }

    return {
        "passed": False,
        "score": 0.0,
        "evidence": f"verifier=bug_status; BUG-33-001 marked fixed but call succeeded (HTTP {st}); regression caught",
    }


TASK = {
    "id": "rt_scope_ippool",
    "title": "Email IP-pool configuration access tracks BUG-33-001",
    "copy_only": False,
    "run": run,
}
