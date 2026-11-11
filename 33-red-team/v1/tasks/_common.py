"""Shared helpers for v1 tasks 3–5."""
from __future__ import annotations

import os
import re
from typing import Any, Callable

ToolFn = Callable[..., tuple[int | str, Any, bool]]


def task_result(
    instance: str,
    task_id: str,
    title: str,
    passed: bool,
    evidence: str,
    score: float | None = None,
) -> dict:
    if score is None:
        score = 1.0 if passed else 0.0
    return {
        "id": f"{instance}:{task_id}",
        "title": title,
        "passed": passed,
        "score": score,
        "evidence": evidence[:500],
    }


def our_email() -> str:
    return (os.environ.get("EMAIL") or os.environ.get("AGENTSWITCH_EMAIL") or "").strip().lower()


def redact(s: str) -> str:
    s = re.sub(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        "<uuid>",
        s,
        flags=re.I,
    )
    s = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+", "<email>", s)
    return s


def seat_identity(tool: ToolFn) -> dict[str, Any]:
    """Best-effort 'us' markers from AgentSeat.list + EMAIL env."""
    email = our_email()
    st, data, err = tool("AgentSeat.list", {"limit": 50})
    ours: dict[str, Any] = {"email": email, "seat_numbers": set(), "user_ids": set(), "seat_ids": set()}
    if err or not isinstance(data, dict):
        return ours
    rows = data.get("data") or []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # Prefer seats whose contact/email matches ours when available
        row_email = str(row.get("email") or row.get("user_email") or "").lower()
        if email and row_email and row_email != email:
            continue
        if email and row_email == email:
            _absorb_seat(ours, row)
            continue
        # If no email filter, keep all listed as candidate "visible" seats;
        # foreign detection still compares against our email when set.
        if not email:
            _absorb_seat(ours, row)
    return ours


def _absorb_seat(ours: dict[str, Any], row: dict) -> None:
    if row.get("seat_number") is not None:
        ours["seat_numbers"].add(row["seat_number"])
        try:
            ours["seat_numbers"].add(int(row["seat_number"]))
        except (TypeError, ValueError):
            pass
    if row.get("id"):
        ours["seat_ids"].add(str(row["id"]))
    for k in ("assigned_user_id", "user_id", "owner_user_id"):
        if row.get(k):
            ours["user_ids"].add(str(row[k]))


def is_foreign_email_row(row: dict, ours: dict[str, Any]) -> bool:
    email = ours.get("email") or ""
    for key in ("email", "owner_email", "user_email", "mailbox_email", "address"):
        val = str(row.get(key) or "").strip().lower()
        if val and email and val != email and "@" in val:
            return True
    for key in ("user_id", "owner_user_id", "assigned_user_id", "owner_id"):
        val = str(row.get(key) or "")
        if val and ours["user_ids"] and val not in ours["user_ids"]:
            return True
    return False


def is_other_seat_row(row: dict, ours: dict[str, Any]) -> bool:
    """True if the row clearly belongs to a different seat/user than ours."""
    sn = row.get("seat_number")
    if sn is not None and ours["seat_numbers"]:
        try:
            if int(sn) not in {int(x) for x in ours["seat_numbers"]}:
                return True
        except (TypeError, ValueError):
            if sn not in ours["seat_numbers"]:
                return True
    for key in ("assigned_user_id", "user_id", "owner_user_id"):
        val = str(row.get(key) or "")
        if val and ours["user_ids"] and val not in ours["user_ids"]:
            return True
    seat_id = str(row.get("agent_seat_id") or row.get("seat_id") or "")
    if seat_id and ours["seat_ids"] and seat_id not in ours["seat_ids"]:
        return True
    return False


def pick_echo_fields(row: dict) -> dict:
    for k in ("name", "title", "description"):
        if row.get(k) is not None:
            return {k: row[k]}
    return {}


def denied(code: str | None, err: bool, data: Any) -> bool:
    if code in ("tool_not_available", "permission_denied", "forbidden"):
        return True
    if not err:
        return False
    msg = ""
    if isinstance(data, dict):
        msg = str(data.get("message") or "")
    low = msg.lower()
    return any(
        x in low
        for x in (
            "not available",
            "permission denied",
            "forbidden",
            "not in your tools/list",
        )
    )
