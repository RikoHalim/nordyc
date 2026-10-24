# Security, safety and operational requirements

- Demo uses only open/public/authorised and explicitly synthetic information. Avoid real personal data or CVs.
- Domain-allowlist and defend against SSRF: deny private/internal/link-local IPs and redirects to unsupported hosts; enforce response-size, timeout, extension and content-type limits.
- Respect official site terms/robots and access controls. No authentication bypass, no captcha solving, no bulk abusive traffic.
- Sanitise displayed excerpts against prompt injection in fetched pages. External content is **data, not instructions**; LLM cannot call tools because a webpage says to.
- Store provider keys only in environment variables; never in repo or logs. Lock down import/admin endpoints before public demo. No secrets in GitHub.
- Document provenance retention and data licences; where redistribution rights unclear store references/excerpts within lawful limits rather than re-hosting datasets.
- Output audit logs: who started analysis, source versions, LLM model name when used, rule-version and input hash; avoid logging uploaded raw documents unnecessarily.
- Background jobs must have retry limits, explicit failed status and idempotency; don't masquerade status as completed.
- Human-in-the-loop: academic plans are drafts and cannot enact curricular changes.

## Phase 7 implemented hardening and remaining operations

[Phase 7](29_PHASE7_INTEGRATION_EVALUATION_SECURITY.md) defines the current threat model and runbook. Shared tokens remain local compatibility only; production uses explicit hashed bearer policies, institution filters and read/write/review/admin separation. This is application-scoped operator access, not named users, SSO, database RLS or permission to deploy publicly. The all-interface launcher refuses missing/legacy policies; production readiness checks policy, DB and migration head. API source-derived responses are no-store; request logs retain safe routes/status/request IDs/operator aliases without headers, query values or raw documents.

Scoped private uploads use institution namespaces, SHA256 names, regular-file/nofollow/hardlink checks and private POSIX modes. Extraction occurs before DB mutation in a secret-free bounded child (30 wall seconds; POSIX 20 CPU seconds/512 MiB). New request bodies have a 30-second total receive deadline and existing byte limits. Windows ACLs, full process sandboxing, persistent shared storage, retention/reconciliation, edge limits, vulnerability operations, supervision, backups and restore testing remain deployment gates. Do not infer automatic artifact cleanup or durable storage from local test success.

Run `runtime-preflight` in API/worker environments and compare opaque receipts; `--check-database` reads the explicitly selected DB without migrations/model calls. It is not a worker heartbeat. Apply reviewed migrations separately only to the approved environment. Replit Run starts API only; worker supervision is explicit. Recover stale jobs with existing administrative commands, preserve historical versions/paid receipts and never automatically transfer approvals or repeat a paid request. No Replit DB/provisioning/deployment was performed in Phase 7.
