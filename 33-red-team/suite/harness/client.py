"""Small MCP client for the v1 suite. Standard library only.

It reads the instance and token from the harness environment
(34-eval-harness/TASK_FORMAT.md, section 2). It never prints, logs or stores the token.
"""
import json
import urllib.error
import urllib.request

TIMEOUT = 30

# Error codes the platform returns in error.data.code (same as replay/).
DENIED = {"permission_denied"}          # JSON-RPC -32001
NOT_EXPOSED = {"tool_not_available"}    # JSON-RPC -32602, not in this login's tools/list
NOT_FOUND = {"not_found"}               # JSON-RPC -32004


class InfraError(Exception):
    """The check could not be made (missing setting, network error, bad token).
    The runner reports it as an infrastructure failure, never as a pass."""


def mcp_url(env):
    base = (env.get("AGENTSWITCH_BASE_URL") or "").rstrip("/")
    if not base:
        raise InfraError("AGENTSWITCH_BASE_URL is not set")
    return base if base.endswith("/api/mcp") else base + "/api/mcp"


def token(env):
    tok = env.get("AGENTSWITCH_TOKEN")
    if not tok:
        raise InfraError("AGENTSWITCH_TOKEN is not set")
    return tok


def rpc(env, method, params=None, tok=None):
    """One JSON-RPC call. tok=None sends no Authorization header.
    Returns (http_status, parsed_body)."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method,
                       "params": params or {}}).encode()
    headers = {"Content-Type": "application/json",
               "Accept": "application/json, text/event-stream"}
    if tok is not None:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(mcp_url(env), data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, _parse(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError) as e:
        raise InfraError(f"network error ({type(e).__name__})") from None


def tool(env, name, args=None):
    """tools/call with the seat token. Returns (http_status, data, is_error).
    On a JSON-RPC error, data is the error object and is_error is True."""
    st, resp = rpc(env, "tools/call", {"name": name, "arguments": args or {}}, tok=token(env))
    data, err = resp, False
    if isinstance(resp, dict):
        if "result" in resp:
            res = resp["result"]
            if isinstance(res, dict) and "content" in res:
                txt = "\n".join(c.get("text", "") for c in res.get("content", [])
                                if c.get("type") == "text")
                try:
                    data = json.loads(txt)
                except ValueError:
                    data = txt
                err = bool(res.get("isError", False))
            else:
                data = res
        elif "error" in resp:
            data, err = resp["error"], True
    return st, data, err


def error_code(data):
    """The platform's error code, e.g. 'permission_denied', or None."""
    if isinstance(data, dict) and isinstance(data.get("data"), dict):
        code = data["data"].get("code")
        return code if isinstance(code, str) else None
    return None


def refused(st, data, is_error):
    """True only for a real refusal: HTTP 403, permission_denied or tool_not_available.
    An empty 200, a bad-argument error or a server error is NOT a refusal."""
    code = error_code(data) if is_error else None
    return st == 403 or code in DENIED or code in NOT_EXPOSED


def _parse(raw):
    if raw.startswith("data:") or "\ndata:" in raw:
        out = []
        for line in raw.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    try:
                        out.append(json.loads(chunk))
                    except ValueError:
                        out.append(chunk)
        return out[-1] if len(out) == 1 else (out or raw)
    try:
        return json.loads(raw)
    except ValueError:
        return raw
