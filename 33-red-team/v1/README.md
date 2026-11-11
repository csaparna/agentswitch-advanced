# Seat 33 v1 — tasks 3–5 (Padmanabh)

Eval-Harness-shaped checks for:

| # | id | Check |
|---|---|---|
| 3 | `rt_email_privacy` | Mail / mailbox / email-account lists show no other user's rows (empty passes) |
| 4 | `rt_skill_write_blocked` | `AgentSkill.update` on another seat's skill is refused |
| 5 | `rt_task_write_foreign` | `AgentTask.update` on another seat's task is `permission_denied`; `updated_at` unchanged |

`passed` is judged on HTTP / JSON-RPC / record state only ([`34-eval-harness/TASK_FORMAT.md`](../../34-eval-harness/TASK_FORMAT.md)).

## Harness env

```bash
export AGENTSWITCH_TOKEN=...
export AGENTSWITCH_BASE_URL=https://<copy-host>
export AGENTSWITCH_INSTANCE=suryodaya   # or keystone
python run_tasks_3_5.py
```

Optional: `EMAIL` / `AGENTSWITCH_EMAIL` to mark "our" mailbox address for task 3.

## Safety

- Tasks **4–5** touch records we did not create → **throwaway copy only** (`CONTRIBUTING.md` tier 2b).
- Against the public live hosts, `run_tasks_3_5.py` sets `writes_allowed=false` unless you force `ALLOW_FOREIGN_WRITES=1` (do not do that on live).
- Task 3 is read-only and may be smoke-tested on live.

## Offline tests

```bash
python -m unittest discover -s tests -v
```

## Output

`results.json` (git-ignored) with instance-prefixed ids, e.g. `suryodaya:rt_email_privacy`.
