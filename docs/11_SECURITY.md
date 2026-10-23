# 11 — MVP Security, Privacy and Responsible AI

- Demo uses **synthetic or properly licensed public** curriculum/workforce material; no real student CVs, grades, or personally identifying learning data.
- Upload allowlist PDF / DOCX only; sniff content/MIME, limit file size and count, sanitize filename, generate server-side storage keys, prevent `../` traversal. Never execute document macros or embedded scripts.
- Don't send files or private content to a remote LLM without permission and an appropriate privacy/data-processing assessment. Defaults should use synthetic fixtures and explicit opt-in API integration.
- PDF content may be out of reading order; scanned-only requires review/OCR later. Preserve document provenance.
- Treat extracted document content and online source text as **untrusted data**. It cannot alter system prompts, make network calls or issue instructions; ignore prompt injection inside documents.
- Never log API keys, upload full text to application logs, or commit `.env`. `.env.example` contains placeholder variable names only.
- Limit LLM output via typed schema and evidence ref validation; no unsupported claim accepted as factual.
- Keep role state generic until authentication is implemented. For demo, label approvals as simulation and do not falsely claim verified identity/role permissions.
- Document retention/deletion policy before deploying with real university uploads. MVP local dev storage is **not** production-ready security.
- Source licences, user consent and Malaysian data privacy obligations must be reviewed before real deployment; project ZIP is not legal assurance.
