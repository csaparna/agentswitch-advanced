# Attempt 22 — Mailbox.get (synthetic id)

1. **Attempt:** Fetch a mailbox by a fabricated mailbox id (`Mailbox.get`).
2. **Boundary:** (Permission) A synthetic or foreign mailbox id must not disclose another user's mailbox.
3. **Steps:**
   1. `tools/call` `Mailbox.get` `{id:"00000000-0000-4000-8000-000000000022"}`.
4. **Expected:** `not_found`, empty, or refused. Never another user's mailbox metadata beyond a refusal.
5. **Actual:** Suryodaya (replay D5): HTTP 200, isError, JSON-RPC `-32004`, `data.code=not_found` ("Mailbox not found."). No mailbox record returned. Keystone not re-checked in this fill.
6. **Result:** Held
