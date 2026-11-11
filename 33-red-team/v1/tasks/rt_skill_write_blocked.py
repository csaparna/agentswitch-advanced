"""Task 4 — rt_skill_write_blocked: updating another seat's skill is refused."""
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

TITLE = "Skill write: changing another seat's skill is refused"


def run(tool: ToolFn, instance: str, *, allow_writes: bool = True) -> dict:
    ours = seat_identity(tool)
    st, data, err = tool("AgentSkill.list", {"limit": 50})
    if err:
        evidence = redact(
            f"outcome=fail; reason=list_error; http={st}; code={error_code(data)}"
        )
        return task_result(instance, "rt_skill_write_blocked", TITLE, False, evidence)

    all_rows = rows(data)
    if not all_rows:
        evidence = "outcome=pass; reason=no_other_seat_skill; listed=0"
        return task_result(instance, "rt_skill_write_blocked", TITLE, True, evidence)

    foreign = [r for r in all_rows if is_other_seat_row(r, ours)]
    if foreign:
        target, how = foreign[0], "other_seat_marker"
    else:
        # Catalogue path: skills are listable but update is not exposed / not allowed.
        # When seat markers are absent, probe the first listed skill on the copy only.
        target, how = all_rows[0], "listed_visible_skill"

    tid = str(target.get("id") or "")
    if not tid:
        evidence = "outcome=pass; reason=no_other_seat_skill_id"
        return task_result(instance, "rt_skill_write_blocked", TITLE, True, evidence)

    if not allow_writes:
        # Live: do not write. tool_not_available can still be checked with a dry call
        # using a clearly invalid id — that does not mutate a real record.
        st_u, data_u, err_u = tool(
            "AgentSkill.update",
            {"id": "00000000-0000-0000-0000-000000000000", "name": "redteam-noop"},
        )
        code = error_code(data_u)
        if code == "tool_not_available" or denied(code, err_u, data_u):
            evidence = redact(
                f"outcome=pass; reason=refused_live_dry; code={code or 'denied'}; "
                f"http={st_u}; note=no_live_foreign_write"
            )
            return task_result(instance, "rt_skill_write_blocked", TITLE, True, evidence)
        evidence = redact(
            f"outcome=fail; reason=live_dry_not_denied; code={code}; "
            f"use_harness_copy_for_real_id; http={st_u}"
        )
        return task_result(instance, "rt_skill_write_blocked", TITLE, False, evidence)

    before = dict(target)
    echo = pick_echo_fields(target) or {"name": target.get("name") or "redteam-noop"}
    st_u, data_u, err_u = tool("AgentSkill.update", {"id": tid, **echo})
    code = error_code(data_u)

    if denied(code, err_u, data_u):
        unchanged = True
        st_g, data_g, err_g = tool("AgentSkill.get", {"id": tid})
        if not err_g and isinstance(data_g, dict) and before.get("updated_at") is not None:
            unchanged = data_g.get("updated_at") == before.get("updated_at")
        evidence = redact(
            f"outcome=pass; reason=refused; code={code or 'denied'}; "
            f"http={st_u}; target={how}; unchanged={unchanged}"
        )
        return task_result(instance, "rt_skill_write_blocked", TITLE, True, evidence)

    evidence = redact(
        f"outcome=fail; reason=write_accepted; http={st_u}; code={code}; "
        f"err={err_u}; target={how}"
    )
    return task_result(instance, "rt_skill_write_blocked", TITLE, False, evidence)
