"""Runs the Seat 33 v1 suite and writes results.json
(34-eval-harness/TASK_FORMAT.md, section 3).

    python -m harness.runner --out results.json
"""
import argparse
import importlib
import json
import os
import pkgutil

from harness.client import InfraError

ENV_KEYS = ("AGENTSWITCH_BASE_URL", "AGENTSWITCH_TOKEN",
            "AGENTSWITCH_INSTANCE", "AGENTSWITCH_RUN_ID")


def discover():
    """Every harness/tasks/tNN_*.py module with a TASK, in file-name order."""
    from harness import tasks as pkg
    found = []
    for m in sorted(pkgutil.iter_modules(pkg.__path__), key=lambda m: m.name):
        if m.name.startswith("_"):
            continue
        task = getattr(importlib.import_module(f"harness.tasks.{m.name}"), "TASK", None)
        if task:
            found.append(task)
    return found


def _fail(task_id, title, reason):
    return {"id": task_id, "title": title, "passed": False, "score": 0.0,
            "evidence": f"infrastructure: {reason}"}


def run_one(task, env):
    instance = env.get("AGENTSWITCH_INSTANCE") or "unknown"
    task_id, title = f"{instance}:{task['id']}", task["title"]
    # A write task runs only inside a harness run, which is always on a copy
    # (TASK_FORMAT.md section 2). Never on live data. See CONTRIBUTING.md.
    if task.get("writes") and not env.get("AGENTSWITCH_RUN_ID"):
        return _fail(task_id, title, "not run: write task, and AGENTSWITCH_RUN_ID is not set "
                                     "(not a harness run on a copy)")
    try:
        r = task["run"](env) or {}
    except InfraError as e:
        return _fail(task_id, title, str(e))
    except Exception as e:  # a bug in a task must show up, not be dropped
        return _fail(task_id, title, f"{type(e).__name__} in task")
    score = min(1.0, max(0.0, float(r.get("score", 0.0))))
    return {"id": task_id, "title": title, "passed": bool(r.get("passed", False)),
            "score": score, "evidence": str(r.get("evidence", ""))}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seat 33 v1 suite")
    ap.add_argument("--out", default="results.json")
    args = ap.parse_args(argv)
    env = {k: os.environ.get(k) for k in ENV_KEYS}
    results = [run_one(t, env) for t in discover()]
    passed = sum(1 for r in results if r["passed"])
    instance = env.get("AGENTSWITCH_INSTANCE") or "unknown"
    report = {"tasks": results,
              "summary": f"{instance}: {passed}/{len(results)} tasks passed"}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    for r in results:
        print(f"{'PASS' if r['passed'] else 'FAIL'}  {r['id']}  {r['evidence']}")
    print(report["summary"])


if __name__ == "__main__":
    main()
