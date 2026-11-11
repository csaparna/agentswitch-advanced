# Attempt 23 — EmailMessage.list (synthetic mailbox_id filter)

1. **Attempt:** List email messages filtered by a fabricated `mailbox_id`.
2. **Boundary:** (Permission) A foreign-looking mailbox filter must not return another user's mail (empty is fine).
3. **Steps:**
   1. `tools/call` `EmailMessage.list` `{mailbox_id:"00000000-0000-4000-8000-000000000023", limit:20}`.
4. **Expected:** Empty list, `not_found`, or refused. No rows belonging to another user.
5. **Actual:** Not filled in this PR (no live token in the authoring environment). Replay probe `D6` is wired; run locally and record `total` / row count only.
6. **Result:** Unclear — awaiting local Tier-1 replay
