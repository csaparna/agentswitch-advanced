# Attempt 24 — AgentSkill.update (foreign owner, copy only)

1. **Attempt:** Update another seat's skill (`AgentSkill.update`), echoing the current `name`, after selecting a row whose `user_id` is not ours.
2. **Boundary:** (Permission) Only the owning seat may change that skill; the write must be refused and the record left unchanged.
3. **Steps:**
   1. **Run only on the Eval-Harness throwaway copy.** Do not send this write on live data (`CONTRIBUTING.md` Tier 2b; same rule as suite tasks 4–8).
   2. `GET /api/auth/me` → our `id`.
   3. `AgentSkill.list` (page if needed); pick the first row with `user_id` ≠ our `id`.
   4. If none: stop; boundary held at read (no write).
   5. Note `updated_at`, then `AgentSkill.update` `{id:<foreign>, name:<current name>}`.
   6. Re-`get` and confirm `updated_at` unchanged if the platform returned a refusal.
4. **Expected:** Refused (`tool_not_available` or `permission_denied` / HTTP 403); `updated_at` unchanged. Or no foreign row → pass without writing.
5. **Actual:** Not exercised on live (Tier 2b). Deferred to the harness copy / `RUN_WRITE_PROBES=1` on a copy only.
6. **Result:** Unclear — awaiting copy run
