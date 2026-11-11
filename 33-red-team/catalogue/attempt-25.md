# Attempt 25 — AgentTask.update (foreign owner, copy only)

1. **Attempt:** Update another seat's task (`AgentTask.update`), echoing one current scalar (`title` / `name` / `description`), after selecting a row whose `user_id` is not ours.
2. **Boundary:** (Permission) Foreign task writes must be refused; `updated_at` must not change.
3. **Steps:**
   1. **Run only on the Eval-Harness throwaway copy.** Do not send this write on live data (`CONTRIBUTING.md` Tier 2b; same rule as suite tasks 4–8).
   2. `GET /api/auth/me` → our `id`.
   3. `AgentTask.list` (page if needed); pick the first row with `user_id` ≠ our `id`.
   4. If none: stop; boundary held at read (no write).
   5. Note `updated_at`, then `AgentTask.update` with the echoed scalar only.
   6. Re-`get` and confirm `updated_at` unchanged after a refusal.
4. **Expected:** Refused (`permission_denied` preferred; `tool_not_available` also holds the write); `updated_at` unchanged. Or no foreign row → pass without writing.
5. **Actual:** Not exercised on live (Tier 2b). Deferred to the harness copy / `RUN_WRITE_PROBES=1` on a copy only.
6. **Result:** Unclear — awaiting copy run
