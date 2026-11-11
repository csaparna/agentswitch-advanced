#!/usr/bin/env python3
"""Minimal JSON-RPC 2.0 / MCP client for the AgentSwitch training systems.

Tokens are read from environment variables ONLY — never hard-code or commit them:
    AGENTSWITCH_SURYODAYA_TOKEN   AGENTSWITCH_SURYODAYA_BASE (optional)
    AGENTSWITCH_KEYSTONE_TOKEN    AGENTSWITCH_KEYSTONE_BASE  (optional)

Get a token (per system, lasts ~7 days):
    curl -s https://<host>/api/auth/login -H 'Content-Type: application/json' \\
         -d '{"email":"<you>","password":"<pw>"}'    # token is the "token" field

Stdlib only. Handles both application/json and text/event-stream replies.
"""
import json, os, sys, urllib.request, urllib.error

DEFAULT_BASE = {
    "suryodaya": "https://agentswitch.theschoolofai.in",
    "keystone":  "https://class.agentswitch.theschoolofai.in",
}

def _cfg(system):
    key = system.upper()
    base = os.environ.get(f"AGENTSWITCH_{key}_BASE") or DEFAULT_BASE.get(system)
    token = os.environ.get(f"AGENTSWITCH_{key}_TOKEN")
    return base, token

_id = [0]

def call(system, method, params=None, token_override=None, base_override=None):
    base, token = _cfg(system)
    base = base_override or base
    if token_override is not None:
        token = token_override
    if not base:
        raise SystemExit(f"Unknown system '{system}'")
    url = base.rstrip("/") + "/api/mcp"
    _id[0] += 1
    body = json.dumps({"jsonrpc": "2.0", "id": _id[0], "method": method,
                       "params": params or {}}).encode()
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, _parse(r.read().decode(), r.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read().decode(), e.headers.get("Content-Type", ""))
    except Exception as e:
        return "ERR", {"error": repr(e)}

def _parse(raw, ctype):
    if "text/event-stream" in ctype or raw.startswith("data:") or "\ndata:" in raw:
        out = []
        for line in raw.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    try: out.append(json.loads(chunk))
                    except json.JSONDecodeError: out.append(chunk)
        return out[-1] if len(out) == 1 else (out or raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw

def tool(system, name, args=None, **kw):
    """tools/call wrapper returning (http_status, data, is_error)."""
    st, resp = call(system, "tools/call", {"name": name, "arguments": args or {}}, **kw)
    data, err = resp, False
    if isinstance(resp, dict):
        if "result" in resp:
            res = resp["result"]
            if isinstance(res, dict) and "content" in res:
                txt = "\n".join(c.get("text", "") for c in res.get("content", [])
                                if c.get("type") == "text")
                try: data = json.loads(txt)
                except Exception: data = txt
                err = res.get("isError", False)
            else:
                data = res
        elif "error" in resp:
            data, err = resp["error"], True
    return st, data, err

if __name__ == "__main__":
    system, method = sys.argv[1], sys.argv[2]
    params = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    st, resp = call(system, method, params)
    print(f"HTTP {st}")
    print(json.dumps(resp, indent=2, ensure_ascii=False))
