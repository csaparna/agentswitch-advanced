#!/usr/bin/env python3
"""Run Seat 33 v1 tasks 3–5 and write TASK_FORMAT results.json.

Harness:
    AGENTSWITCH_TOKEN, AGENTSWITCH_BASE_URL, AGENTSWITCH_INSTANCE

Writes (tasks 4–5) require the throwaway copy. Set ALLOW_FOREIGN_WRITES=1 to
enable them (default on when AGENTSWITCH_BASE_URL looks like a harness copy,
or when ALLOW_FOREIGN_WRITES=1 explicitly). On live public hosts, writes stay off.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from mcp_env import instance_name, resolve_connection, tool as live_tool
from tasks.rt_email_privacy import run as run_email
from tasks.rt_skill_write_blocked import run as run_skill
from tasks.rt_task_write_foreign import run as run_task

LIVE_HOSTS = (
    "agentswitch.theschoolofai.in",
    "class.agentswitch.theschoolofai.in",
)


def writes_allowed(base_url: str) -> bool:
    flag = os.environ.get("ALLOW_FOREIGN_WRITES", "").strip()
    if flag == "0":
        return False
    if flag == "1":
        return True
    host = base_url.replace("https://", "").replace("http://", "").split("/")[0]
    # Default: block foreign writes against known live training hosts
    return host not in LIVE_HOSTS


def main() -> int:
    inst, base, token = resolve_connection()
    allow = writes_allowed(base)

    def tool(name, args=None):
        return live_tool(name, args, base=base, token=token)

    results = [
        run_email(tool, inst),
        run_skill(tool, inst, allow_writes=allow),
        run_task(tool, inst, allow_writes=allow),
    ]
    passed = sum(1 for r in results if r["passed"])
    out = {
        "tasks": results,
        "summary": f"{inst}: {passed}/{len(results)} tasks passed",
        "writes_allowed": allow,
        "instance": inst,
    }
    out_path = Path(os.environ.get("RESULTS_PATH") or HERE / "results.json")
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    print(f"Wrote {out_path}", file=sys.stderr)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
