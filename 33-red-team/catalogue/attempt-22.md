# Attempt 22 — Mailbox.get (synthetic id)

1. **Attempt:** Fetch a mailbox by a fabricated mailbox id (`Mailbox.get`).
2. **Boundary:** (Permission) A synthetic or foreign mailbox id must not disclose another user's mailbox.
3. **Steps:**
   1. `tools/call` `Mailbox.get` `{id:"00000000-0000-4000-8000-000000000022"}`.
4. **Expected:** `not_found`, empty, or refused. Never another user's mailbox metadata beyond a refusal.
5. **Actual:** Not filled in this PR (no live token in the authoring environment). Replay probe `D5` is wired; run locally and record codes/counts only.
6. **Result:** Unclear — awaiting local Tier-1 replay
