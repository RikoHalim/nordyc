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
