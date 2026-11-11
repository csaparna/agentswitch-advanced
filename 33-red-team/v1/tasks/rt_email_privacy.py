"""Task 3 — rt_email_privacy: no other user's mail visible."""
from __future__ import annotations

from typing import Any

from mcp_env import error_code, rows
from tasks._common import ToolFn, is_foreign_email_row, redact, seat_identity, task_result

TITLE = "Email privacy: lists show no other user's mail"
TOOLS = ("EmailMessage.list", "Mailbox.list", "EmailAccount.list")


def run(tool: ToolFn, instance: str) -> dict:
    ours = seat_identity(tool)
    foreign_hits: list[str] = []
    totals: dict[str, int] = {}
    errors: list[str] = []

    for name in TOOLS:
        st, data, err = tool(name, {"limit": 1000})
        if err and st not in (200,):
            errors.append(f"{name}:http={st}:code={error_code(data)}")
            continue
        if err:
            # tool error with 200 envelope — treat as no rows disclosed
            totals[name] = 0
            continue
        rs = rows(data)
        totals[name] = len(rs)
        for row in rs:
            if is_foreign_email_row(row, ours):
                foreign_hits.append(name)
                break

    if foreign_hits:
        evidence = redact(
            f"outcome=fail; reason=foreign_row; tools={foreign_hits}; totals={totals}"
        )
        return task_result(instance, "rt_email_privacy", TITLE, False, evidence)

    empty_all = all(v == 0 for v in totals.values()) if totals else True
    reason = "empty_lists" if empty_all else "own_scope_only"
    evidence = redact(
        f"outcome=pass; reason={reason}; totals={totals}; errors={errors or 'none'}"
    )
    return task_result(instance, "rt_email_privacy", TITLE, True, evidence)
