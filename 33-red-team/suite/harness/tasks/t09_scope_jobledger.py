"""Task 9 (owner: csaparna). Component: Agent job-ledger forensics.
Regression check tracking BUG-33-002 against bug-status.json.

Read-only: one endpoint call.
Passes if the call is refused, if 0 rows are returned, or if BUG-33-002
is recorded as not fixed (new, open, wont_fix). Fails only if marked fixed
and rows are returned (regression caught).
"""
from harness import bugs, client


def _count_rows(data):
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("rows", "data", "items", "records"):
            if key in data and isinstance(data[key], list):
                return len(data[key])
        if "result" in data and isinstance(data["result"], dict):
            return _count_rows(data["result"])
    return 0


def run(env):
    st_bug = bugs.status("BUG-33-002")
    st, data, is_error = client.tool(env, "endpoint.job_ledger.forensics", {})
    if st >= 500:
        raise client.InfraError(f"server error HTTP {st}")

    is_refused = client.refused(st, data, is_error)
    code = client.error_code(data) if is_error else None

    if is_refused:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": f"verifier=refusal; endpoint.job_ledger.forensics refused -> HTTP {st}, code={code}; no disclosure",
        }

    count = _count_rows(data)
    if count == 0:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": f"verifier=row_count; endpoint.job_ledger.forensics returned HTTP {st} with 0 rows; no disclosure",
        }

    # Rows returned (count > 0)
    if st_bug in {"new", "open", "wont_fix"}:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": f"verifier=bug_status; BUG-33-002 status={st_bug}; {count} row(s) returned as known issue",
        }

    return {
        "passed": False,
        "score": 0.0,
        "evidence": f"verifier=bug_status; BUG-33-002 marked fixed but {count} row(s) returned; regression caught",
    }


TASK = {
    "id": "rt_scope_jobledger",
    "title": "Agent job-ledger forensics tracks BUG-33-002",
    "copy_only": False,
    "run": run,
}

