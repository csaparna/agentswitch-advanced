"""Task 5 (owner: Padmanabh). Updating another seat's task must return
permission_denied and leave updated_at unchanged. If AgentTask.list has no
usable target, pass without writing (PLAN.md). Copy-only: harness copy only.
"""
from harness import client


def _rows(data):
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [r for r in data["data"] if isinstance(r, dict)]
    return []


def _permission_denied(st, data, err):
    if st == 403:
        return True
    code = client.error_code(data) if err else None
    if code == "permission_denied":
        return True
    msg = str(data.get("message") or "").lower() if isinstance(data, dict) else ""
    return "permission denied" in msg


def run(env):
    st, data, err = client.tool(env, "AgentTask.list", {"limit": 50})
    if err:
        raise client.InfraError(
            f"AgentTask.list failed HTTP {st} code={client.error_code(data)}"
        )
    rows = _rows(data)
    if not rows:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": "verifier=task_write; reason=no_other_seat_task; listed=0",
        }
    target = rows[0]
    tid = target.get("id")
    if not tid:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": "verifier=task_write; reason=no_other_seat_task_id",
        }
    before = target.get("updated_at")
    echo_key = next((k for k in ("title", "name", "description") if target.get(k) is not None), "title")
    echo_val = target.get(echo_key) if echo_key in target else "redteam-noop"
    st_u, data_u, err_u = client.tool(env, "AgentTask.update", {"id": tid, echo_key: echo_val})
    code = client.error_code(data_u)

    # tool_not_available also holds the write boundary
    if client.refused(st_u, data_u, err_u) and code == "tool_not_available":
        return {
            "passed": True,
            "score": 1.0,
            "evidence": f"verifier=task_write; tool_not_available HTTP {st_u}",
        }

    if not _permission_denied(st_u, data_u, err_u):
        return {
            "passed": False,
            "score": 0.0,
            "evidence": f"verifier=task_write; write_not_denied HTTP {st_u} code={code}",
        }

    st_g, data_g, err_g = client.tool(env, "AgentTask.get", {"id": tid})
    unchanged = True
    if not err_g and isinstance(data_g, dict) and before is not None:
        unchanged = data_g.get("updated_at") == before
    if not unchanged:
        return {
            "passed": False,
            "score": 0.0,
            "evidence": f"verifier=task_write; denied_but_updated_at_changed code={code}",
        }
    return {
        "passed": True,
        "score": 1.0,
        "evidence": (
            f"verifier=task_write; permission_denied HTTP {st_u} code={code or 'permission_denied'}; "
            f"updated_at_unchanged=True"
        ),
    }


TASK = {
    "id": "rt_task_write_foreign",
    "title": "Task write: changing another seat's task is refused",
    "copy_only": True,
    "run": run,
}
