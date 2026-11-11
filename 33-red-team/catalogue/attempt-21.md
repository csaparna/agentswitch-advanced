# Attempt 21 — EmailMessage.get (synthetic id)

1. **Attempt:** Fetch a single email by a fabricated message id (`EmailMessage.get`).
2. **Boundary:** (Permission) Guessing or knowing another user's message id must not return their mail.
3. **Steps:**
   1. `tools/call` `EmailMessage.get` `{id:"00000000-0000-4000-8000-000000000021"}`.
4. **Expected:** `not_found`, empty, or refused (`permission_denied` / HTTP 403 / `tool_not_available`). Never another user's message body.
5. **Actual:** Suryodaya (replay D4): HTTP 200, isError, JSON-RPC `-32004`, `data.code=not_found` ("EmailMessage not found."). No message body returned. Keystone not re-checked in this fill.
6. **Result:** Held
