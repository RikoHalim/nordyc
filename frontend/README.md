# NORDYC academic workspace

React + TypeScript + Vite frontend for the existing SHIFT//OS FastAPI/PostgreSQL backend. The NORDYC concept is visually reconstructed from its seven revised screenshots; authored NORDYC source was not recovered. Branding is provisional and configurable. See [the complete Phase 8 design, API, privacy and Replit runbook](../docs/30_PHASE8_FRONTEND_REPLIT_MVP.md).

Install a compatible Node runtime, run `npm ci`, then `npm run dev`. Development requests use the same-origin API proxy; configure `BACKEND_ORIGIN` for your explicitly selected loopback backend. The server does not create a database or worker. Use the documented owned PostgreSQL synthetic preview for a reproducible demonstration, with provider HTTP blocked and actual stored results.

Enter a scoped operator credential privately on the access screen. It remains in memory only; reload/disconnect clears it. No provider secret belongs in a `VITE_*` variable, browser storage, example file or bundle. Scoped grants do not establish named academic identity.

Checks: `npm run typecheck`, `npm test`, `npm run build`, `npm run format:check`, `npm audit`. Regenerate contract types with the root `python scripts/export_frontend_contract.py` followed by `npm run contracts`. Browser acceptance requires the running controlled backend/worker and `SHIFTOS_PREVIEW_AUTH` pointing to its ignored private credential file; run `npm run test:browser`. Tests generate synthetic upload input, never real private curricula.

All working pages consume protected APIs. Missing data, source withdrawal, unknown competencies, stale versions and failed jobs remain explicit. The interface offers offline submissions only; no paid AI/search request is triggered by its controls. Print styling supports human review; no validated PDF export or production deployment is claimed.
