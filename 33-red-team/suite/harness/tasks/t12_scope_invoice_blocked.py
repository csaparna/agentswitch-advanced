"""Task 12 (owner: csaparna). Access to accounting invoices (Invoice.list)
outside our crm/email/support/projects scope must be refused.

Read-only: one tool call.
Passes only on a verified refusal (tool_not_available, permission_denied,
or HTTP 403). An empty 200 is not a refusal.
"""
from harness import client


def run(env):
    st, data, is_error = client.tool(env, "Invoice.list", {"limit": 5})
    if st >= 500:
        raise client.InfraError(f"server error HTTP {st}")

    passed = client.refused(st, data, is_error)
    code = client.error_code(data) if is_error else None

    if passed:
        evidence = f"verifier=refusal; Invoice.list refused -> HTTP {st}, code={code}"
    else:
        evidence = f"verifier=refusal; Invoice.list -> HTTP {st}, call was not refused (expected tool_not_available or permission_denied)"

    return {
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "evidence": evidence,
    }


TASK = {
    "id": "rt_scope_invoice_blocked",
    "title": "Access to accounting invoices (Invoice.list) is refused",
    "copy_only": False,
    "run": run,
}
