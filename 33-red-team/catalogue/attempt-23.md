# Attempt 23 — EmailMessage.list (synthetic mailbox_id filter)

1. **Attempt:** List email messages filtered by a fabricated `mailbox_id`.
2. **Boundary:** (Permission) A foreign-looking mailbox filter must not return another user's mail (empty is fine).
3. **Steps:**
   1. `tools/call` `EmailMessage.list` `{mailbox_id:"00000000-0000-4000-8000-000000000023", limit:20}`.
4. **Expected:** Empty list, `not_found`, or refused. No rows belonging to another user.
5. **Actual:** Suryodaya (replay D6): HTTP 200, `data=[]`, `total=0` (limit 20, offset 0). No foreign rows. Keystone not re-checked in this fill.
6. **Result:** Held
