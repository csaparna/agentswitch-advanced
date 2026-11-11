"""Task 4 (owner: Padmanabh). Updating another seat's skill must be refused
(tool_not_available or permission_denied). If AgentSkill.list has no usable
target, pass without writing (PLAN.md). Copy-only: runs on the harness copy.
"""
from harness import client


def _rows(data):
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [r for r in data["data"] if isinstance(r, dict)]
    return []


def _refused_or_msg(st, data, err):
    if client.refused(st, data, err):
        return True
    msg = str(data.get("message") or "").lower() if isinstance(data, dict) else ""
    return "not available" in msg or "permission denied" in msg or "not in your tools/list" in msg


def run(env):
    st, data, err = client.tool(env, "AgentSkill.list", {"limit": 50})
    if err:
        raise client.InfraError(
            f"AgentSkill.list failed HTTP {st} code={client.error_code(data)}"
        )
    rows = _rows(data)
    if not rows:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": "verifier=skill_write; reason=no_other_seat_skill; listed=0",
        }
    target = rows[0]
    tid = target.get("id")
    if not tid:
        return {
            "passed": True,
            "score": 1.0,
            "evidence": "verifier=skill_write; reason=no_other_seat_skill_id",
        }
    before = target.get("updated_at")
    echo_key = next((k for k in ("name", "title", "description") if target.get(k) is not None), "name")
    echo_val = target.get(echo_key) if echo_key in target else "redteam-noop"
    st_u, data_u, err_u = client.tool(env, "AgentSkill.update", {"id": tid, echo_key: echo_val})
    code = client.error_code(data_u)
    if not _refused_or_msg(st_u, data_u, err_u):
        return {
            "passed": False,
            "score": 0.0,
            "evidence": f"verifier=skill_write; write_accepted HTTP {st_u} code={code}",
        }
    unchanged = True
    st_g, data_g, err_g = client.tool(env, "AgentSkill.get", {"id": tid})
    if not err_g and isinstance(data_g, dict) and before is not None:
        unchanged = data_g.get("updated_at") == before
    return {
        "passed": True,
        "score": 1.0,
        "evidence": (
            f"verifier=skill_write; refused HTTP {st_u} code={code or 'denied'}; "
            f"unchanged={unchanged}"
        ),
    }


TASK = {
    "id": "rt_skill_write_blocked",
    "title": "Skill write: changing another seat's skill is refused",
    "copy_only": True,
    "run": run,
}
