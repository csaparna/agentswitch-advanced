# Seat 33 v1 suite (due 30 Nov 2026)

The 12-task red-team suite from `../PLAN.md`, in the Eval-Harness format (`../../34-eval-harness/TASK_FORMAT.md`). Standard library only. No credentials are stored here: the token comes from the environment.

## Files

| Path | What it is |
|---|---|
| `agentswitch-harness.toml` | Harness file. It stays in this folder until PLAN.md open question 1 is answered. |
| `harness/runner.py` | Runs every task and writes `results.json` (git-ignored). |
| `harness/client.py` | MCP calls with the seat token. `client.refused()` is true only for a real refusal. |
| `harness/bugs.py` + `bug-status.json` | Bug status for tasks 9 and 10. Keep it in step with the PLAN.md bug list. |
| `harness/tasks/tNN_*.py` | One file per task. Copy `_template.py` to start. |
| `tests/` | Offline tests against a local stub server. |

## Tasks

| # | Task id | File | Owner | Status |
|---|---|---|---|---|
| 1 | `rt_auth_no_token` | `t01_auth_no_token.py` | Ramesh | Done |
| 2 | `rt_auth_tampered_token` | `t02_auth_tampered_token.py` | Ramesh | Done |
| 3 | `rt_email_privacy` | `t03_…` | Padmanabh | To do |
| 4 | `rt_skill_write_blocked` | `t04_…` | Padmanabh | To do (writes) |
| 5 | `rt_task_write_foreign` | `t05_…` | Padmanabh | To do (writes) |
| 6 | `rt_memory_foreign_user` | `t06_…` | Sagar | To do (writes) |
| 7 | `rt_toolpolicy_write_blocked` | `t07_…` | Sagar | To do (writes) |
| 8 | `rt_persona_write_blocked` | `t08_…` | Sagar | To do (writes) |
| 9 | `rt_scope_jobledger` | `t09_…` | csaparna | To do |
| 10 | `rt_scope_ippool` | `t10_…` | csaparna | To do |
| 11 | `rt_scope_contract_blocked` | `t11_…` | csaparna | To do |
| 12 | `rt_scope_invoice_blocked` | `t12_…` | csaparna | To do |

PRs for tasks 3–12 are due 22 Nov.

## Run it locally

```bash
cd 33-red-team/suite
export AGENTSWITCH_BASE_URL=https://agentswitch.theschoolofai.in    # Keystone: https://class.agentswitch.theschoolofai.in
export AGENTSWITCH_INSTANCE=suryodaya                                # or keystone
export AGENTSWITCH_TOKEN="$AGENTSWITCH_SURYODAYA_TOKEN"             # same token as replay/
python -m harness.runner --out results.json
python -m unittest discover -s tests -t .                           # offline tests, no login
```

## Rules for every task

- `run(env)` returns `{"passed": True/False, "score": 0–1 (optional), "evidence": "..."}`. Without a score, it follows `passed` (1.0 or 0.0). Any other shape, or `passed` and `score` that disagree, is reported as an infrastructure failure.
- `passed` comes from the HTTP / JSON-RPC result or the data, never from what an agent says.
- Inputs are built at run time from the token and the copy. A harness run has one token, one instance and no internet.
- If a check cannot be made, raise `client.InfraError`. It is reported as an infrastructure failure, never as a pass. A task file that fails to import is reported the same way, and the other tasks still run.
- An empty 200 is not a refusal. Use `client.refused()`.
- **Writes (tasks 4–8):** set `"writes": True`. The runner then runs the task only inside a harness run, which is always on a copy (`AGENTSWITCH_RUN_ID` set). On a local run it is skipped: shown as `SKIP`, listed under `not_run` in `results.json`, and left out of the passed/total count. Do not set `AGENTSWITCH_RUN_ID` yourself. Any live write needs platform-team approval first (`../CONTRIBUTING.md`).
- `evidence` holds codes and counts only. Never the token, and never record contents.
