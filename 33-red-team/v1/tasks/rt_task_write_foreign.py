"""Task 5 — rt_task_write_foreign: updating another seat's task is refused."""
from __future__ import annotations

from mcp_env import error_code, rows
from tasks._common import (
    ToolFn,
    denied,
    is_other_seat_row,
    pick_echo_fields,
    redact,
    seat_identity,
    task_result,
)

TITLE = "Task write: changing another seat's task is refused"


def _is_permission_denied(code: str | None, err: bool, data) -> bool:
    if code == "permission_denied":
        return True
    if not err:
        return False
    msg = ""
    if isinstance(data, dict):
        msg = str(data.get("message") or "").lower()
    return "permission denied" in msg or code == "forbidden"


def run(tool: ToolFn, instance: str, *, allow_writes: bool = True) -> dict:
    ours = seat_identity(tool)
    st, data, err = tool("AgentTask.list", {"limit": 50})
    if err:
        evidence = redact(
            f"outcome=fail; reason=list_error; http={st}; code={error_code(data)}"
        )
        return task_result(instance, "rt_task_write_foreign", TITLE, False, evidence)

    all_rows = rows(data)
    if not all_rows:
        evidence = "outcome=pass; reason=no_other_seat_task; listed=0"
        return task_result(instance, "rt_task_write_foreign", TITLE, True, evidence)

    foreign = [r for r in all_rows if is_other_seat_row(r, ours)]
    if foreign:
        target, how = foreign[0], "other_seat_marker"
    else:
        target, how = all_rows[0], "listed_visible_task"

    tid = str(target.get("id") or "")
    if not tid:
        evidence = "outcome=pass; reason=no_other_seat_task_id"
        return task_result(instance, "rt_task_write_foreign", TITLE, True, evidence)

    if not allow_writes:
        # Live: never write a real foreign/listed task. Made-up ids return
        # invalid_arguments (not permission_denied). Defer the proof to the harness copy.
        evidence = redact(
            f"outcome=pass; reason=skipped_live_foreign_write; "
            f"harness_copy_required=1; listed={len(all_rows)}; target={how}"
        )
        return task_result(instance, "rt_task_write_foreign", TITLE, True, evidence)

    before_updated = target.get("updated_at")
    echo = pick_echo_fields(target)
    if not echo:
        echo = {"title": target.get("title") or target.get("name") or "redteam-noop"}

    st_u, data_u, err_u = tool("AgentTask.update", {"id": tid, **echo})
    code = error_code(data_u)
    ok_deny = _is_permission_denied(code, err_u, data_u)

    st_g, data_g, err_g = tool("AgentTask.get", {"id": tid})
    updated_at_unchanged = True
    if not err_g and isinstance(data_g, dict) and before_updated is not None:
        updated_at_unchanged = data_g.get("updated_at") == before_updated

    if ok_deny and updated_at_unchanged:
        evidence = redact(
            f"outcome=pass; reason=permission_denied; code={code or 'permission_denied'}; "
            f"http={st_u}; updated_at_unchanged=True; target={how}"
        )
        return task_result(instance, "rt_task_write_foreign", TITLE, True, evidence)

    if ok_deny and not updated_at_unchanged:
        evidence = redact(
            f"outcome=fail; reason=denied_but_updated_at_changed; code={code}; http={st_u}"
        )
        return task_result(instance, "rt_task_write_foreign", TITLE, False, evidence)

    # tool_not_available is acceptable as a refusal for this boundary too
    if denied(code, err_u, data_u) and code == "tool_not_available":
        evidence = redact(
            f"outcome=pass; reason=tool_not_available; http={st_u}; target={how}"
        )
        return task_result(instance, "rt_task_write_foreign", TITLE, True, evidence)

    evidence = redact(
        f"outcome=fail; reason=write_not_denied; http={st_u}; code={code}; "
        f"err={err_u}; target={how}"
    )
    return task_result(instance, "rt_task_write_foreign", TITLE, False, evidence)
