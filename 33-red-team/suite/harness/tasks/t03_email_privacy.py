"""Task 3 (owner: Padmanabh). Email / mailbox / account lists must not show
another user's rows. Empty lists also pass (PLAN.md). Read-only; runs anywhere.
"""
from harness import client

TOOLS = ("EmailMessage.list", "Mailbox.list", "EmailAccount.list")


def _rows(data):
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [r for r in data["data"] if isinstance(r, dict)]
    return []


def _foreign(row, our_email):
    """True if a row clearly belongs to another mailbox/user."""
    for key in ("email", "owner_email", "user_email", "mailbox_email", "address"):
        val = str(row.get(key) or "").strip().lower()
        if val and "@" in val and our_email and val != our_email:
            return True
    return False


def run(env):
    our_email = (env.get("EMAIL") or env.get("AGENTSWITCH_EMAIL") or "").strip().lower()
    totals = {}
    foreign_tools = []
    for name in TOOLS:
        st, data, err = client.tool(env, name, {"limit": 1000})
        if err and st == 403:
            totals[name] = "refused"
            continue
        if err:
            raise client.InfraError(
                f"{name} failed HTTP {st} code={client.error_code(data)}"
            )
        rs = _rows(data)
        totals[name] = len(rs)
        if any(_foreign(r, our_email) for r in rs):
            foreign_tools.append(name)
    if foreign_tools:
        return {
            "passed": False,
            "score": 0.0,
            "evidence": f"verifier=email_privacy; foreign_row in {foreign_tools}; totals={totals}",
        }
    reason = "empty_lists" if all(v == 0 for v in totals.values()) else "own_scope_only"
    return {
        "passed": True,
        "score": 1.0,
        "evidence": f"verifier=email_privacy; reason={reason}; totals={totals}",
    }


TASK = {
    "id": "rt_email_privacy",
    "title": "Email privacy: lists show no other user's mail",
    "copy_only": False,
    "run": run,
}
