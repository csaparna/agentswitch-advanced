# Attempt 21 — EmailMessage.get (synthetic id)

1. **Attempt:** Fetch a single email by a fabricated message id (`EmailMessage.get`).
2. **Boundary:** (Permission) Guessing or knowing another user's message id must not return their mail.
3. **Steps:**
   1. `tools/call` `EmailMessage.get` `{id:"00000000-0000-4000-8000-000000000021"}`.
4. **Expected:** `not_found`, empty, or refused (`permission_denied` / HTTP 403 / `tool_not_available`). Never another user's message body.
5. **Actual:** Not filled in this PR (no live token in the authoring environment). Replay probe `D4` is wired; run `python run_boundary_probes.py` locally and record HTTP / error code / that no message body was returned.
6. **Result:** Unclear — awaiting local Tier-1 replay
