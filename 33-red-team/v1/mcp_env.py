#!/usr/bin/env python3
"""Harness-aware MCP client for Seat 33 v1 tasks.

Preferred (Eval-Harness copy):
    AGENTSWITCH_TOKEN
    AGENTSWITCH_BASE_URL
    AGENTSWITCH_INSTANCE   # suryodaya | keystone

Local smoke remap (read-only email checks only):
    If harness vars are unset, fall back to AGENTSWITCH_SURYODAYA_TOKEN /
    AGENTSWITCH_KEYSTONE_TOKEN and default public bases — never for foreign writes.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE = {
    "suryodaya": "https://agentswitch.theschoolofai.in",
    "keystone": "https://class.agentswitch.theschoolofai.in",
}

_id = [0]


def instance_name() -> str:
    return (os.environ.get("AGENTSWITCH_INSTANCE") or "suryodaya").strip().lower()


def resolve_connection() -> tuple[str, str, str]:
    """Return (instance, base_url, token). Raises SystemExit if incomplete."""
    inst = instance_name()
    base = (os.environ.get("AGENTSWITCH_BASE_URL") or "").rstrip("/")
    token = os.environ.get("AGENTSWITCH_TOKEN") or ""
    if base and token:
        return inst, base, token
    # Local remap for smoke (catalogue-style env names)
    key = inst.upper()
    base = (os.environ.get(f"AGENTSWITCH_{key}_BASE") or DEFAULT_BASE.get(inst) or "").rstrip("/")
    token = os.environ.get(f"AGENTSWITCH_{key}_TOKEN") or ""
    if not base or not token:
        raise SystemExit(
            "missing AGENTSWITCH_TOKEN + AGENTSWITCH_BASE_URL "
            f"(or AGENTSWITCH_{key}_TOKEN for local remap)"
        )
    return inst, base, token


def _parse(raw: str, ctype: str) -> Any:
    if "text/event-stream" in ctype or raw.startswith("data:") or "\ndata:" in raw:
        out = []
        for line in raw.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    try:
                        out.append(json.loads(chunk))
                    except json.JSONDecodeError:
                        out.append(chunk)
        return out[-1] if len(out) == 1 else (out or raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def call(
    method: str,
    params: dict | None = None,
    *,
    base: str | None = None,
    token: str | None = None,
    token_override: str | None = None,
) -> tuple[int | str, Any]:
    if base is None or token is None:
        _, base, token = resolve_connection()
    if token_override is not None:
        token = token_override
    url = base.rstrip("/") + "/api/mcp"
    _id[0] += 1
    body = json.dumps(
        {"jsonrpc": "2.0", "id": _id[0], "method": method, "params": params or {}}
    ).encode()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, _parse(r.read().decode(), r.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read().decode(), e.headers.get("Content-Type", ""))
    except Exception as e:  # noqa: BLE001
        return "ERR", {"error": repr(e)}


def tool(
    name: str,
    args: dict | None = None,
    *,
    base: str | None = None,
    token: str | None = None,
) -> tuple[int | str, Any, bool]:
    """tools/call → (http_status, data, is_error)."""
    st, resp = call(
        "tools/call",
        {"name": name, "arguments": args or {}},
        base=base,
        token=token,
    )
    data, err = resp, False
    if isinstance(resp, dict):
        if "result" in resp:
            res = resp["result"]
            if isinstance(res, dict) and "content" in res:
                txt = "\n".join(
                    c.get("text", "")
                    for c in res.get("content", [])
                    if c.get("type") == "text"
                )
                try:
                    data = json.loads(txt)
                except Exception:  # noqa: BLE001
                    data = txt
                err = bool(res.get("isError", False))
            else:
                data = res
        elif "error" in resp:
            data, err = resp["error"], True
    return st, data, err


def error_code(data: Any) -> str | None:
    """Best-effort extract of platform / JSON-RPC error code."""
    if not isinstance(data, dict):
        return None
    if "data" in data and isinstance(data["data"], dict) and "code" in data["data"]:
        return str(data["data"]["code"])
    if "code" in data and not isinstance(data["code"], int):
        return str(data["code"])
    # JSON-RPC numeric codes often pair with message text
    msg = str(data.get("message") or "").lower()
    if "not available" in msg or "not in your tools/list" in msg:
        return "tool_not_available"
    if "permission denied" in msg:
        return "permission_denied"
    if data.get("code") == -32602:
        return "tool_not_available"
    if data.get("code") == -32001:
        return "permission_denied"
    return None


def rows(data: Any) -> list[dict]:
    if isinstance(data, dict) and isinstance(data.get("data"), list):
        return [r for r in data["data"] if isinstance(r, dict)]
    return []
