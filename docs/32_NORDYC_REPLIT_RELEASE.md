# NORDYC — Replit release preparation

## Current acceptance and scope

**Public deployment is PENDING.** This runbook describes the prepared release path, not a published service. NORDYC remains FastAPI, PostgreSQL, SQLAlchemy/Alembic and React/TypeScript. Replit is the intended hosting platform. Replit-managed Claude remains the retained AI integration, but the proposed public example makes no live AI/research requests. Gemini and fallback stay disabled.

Current frontend verification passes **190 tests**, TypeScript/production build and formatting. The initial complete backend regression passed **1,133 tests including the available PostgreSQL cases in 244.93 seconds**. Final hosting compatibility changes receive targeted verification and a fresh full rerun. Earlier Phase 8/8.1 test and live-integration receipts retain their original scope in [STATUS](../STATUS.md) and [the upload/example runbook](31_PHASE81_UPLOAD_JUDGE_DEMO.md); they do not certify a public deployment.

The proposed public dataset is exactly one fictional Applied Data Science course in its own Data Science workspace. Its persisted offline outputs include five recommendations, five pathways, two hypothetical scenarios, two possible SDG contributions and an eight-section Action Plan. Fictional source provenance and backend flags remain explicit; authentic UN references remain attributed standards. Neither the example nor the software checks establish real university findings, academic approval, student competence or achieved SDG impact.

## Rename, recovery and access cleanup

The product display name and 19 documentation files now use NORDYC. Repository remotes in both local checkouts use the canonical `https://github.com/RikoHalim/nordyc.git`. Existing technical package/import names (`shiftos`), `SHIFTOS_*` variables, schema/ownership identifiers and local paths remain compatible. Archived Replit URLs and historical results are preserved.

All 15 remote refs were mirrored and a complete private recovery bundle was verified before cleanup. Five remote branches fully contained in the retained history were removed: the Phase 2, Phase 5, Phase 6, Phase 7 and earlier Phase 8 React branches. Unique Gemini, Claude, `celilinss`, revert and main histories remain. No local branch deletion, branch merge or force-push is implied. Recovery material remains private and outside published source.

The running local preview's operator and reader policy now scopes only the new fictional Data Science institution. Other programme records remain in the old PostgreSQL schema and the prior access policy is backed up. Removing their active access does not erase their data. Recovery or broader access requires an explicit administrator decision; do not add them to the public reader's scope.

## One web origin and explicit read-only public access

[The web launcher](../scripts/run_web.py) runs [the same-origin application](../src/shiftos/web.py), serving `frontend/dist` and the existing protected FastAPI routes. It binds to the host-provided `PORT` (otherwise 8080). It does not migrate, seed, import data or install model mocks at startup. The ordinary API factory remains available separately.

Both public opt-ins are required: build the frontend with `VITE_PUBLIC_DEMO=true`, and set `NORDYC_PUBLIC_DEMO_ENABLED=true` only for the admitted isolated example. The runtime `/__public_demo` marker revalidates the target before reporting it available. Without that combination, normal manual scoped authentication remains. No token or policy is compiled into the frontend or returned by the marker.

The server requires an existing reader principal with exactly `read` permission and exactly the selected fictional institution. That institution must contain exactly one fictional programme and course, a current revision and schema-valid committed results with matching lineage/fingerprints and current source permissions. Anonymous access is limited to read requests through this scope. Uploads, reviews, analysis submissions, source administration and other mutations still require the existing explicit authenticated grants; a public reader cannot perform them. Foreign-institution/global administration access remains denied. Invalid or withdrawn evidence fails closed.

The new deployment CSP keeps script sources on the current origin and disallows inline scripts. It permits `unsafe-eval` because the existing AJV client compiles only the bundled OpenAPI schemas using `Function`; it does not compile request-supplied or external schemas. A real browser check caught and corrected an initially blank page when this compilation was blocked. This is an explicit compatibility tradeoff, not a claim of strict eval-free CSP. API permissions, source checks and the ban on anonymous mutations remain independent server controls.

Set `NORDYC_WORKER_ENABLED=false` for the frozen read-only example. It needs no new job execution. Enabling an ordinary authenticated upload service would additionally require durable private storage, supervised worker operations, operational identity and separate release checks. The prepared optional worker is not acceptance of those operations.

## Configuration and secrets

[`.env.example`](../.env.example) documents safe defaults and commented placeholders. Configure the actual release environment privately:

| Setting | Required release value or purpose |
|---|---|
| `APP_ENV`, `API_ACCESS_MODE` | `production`, `scoped` |
| `DATABASE_URL` | Explicitly selected managed PostgreSQL connection, using `postgresql+psycopg`; retain actual SSL options and credentials in Secrets |
| `NORDYC_DATABASE_SCHEMA` | Exact newly imported owner-marked schema, not a guessed/default or old local schema |
| `NORDYC_ACCESS_POLICY_JSON` | Server-only bounded scoped policy JSON containing token hashes; never the raw token or frontend configuration |
| `NORDYC_PUBLIC_DEMO_ENABLED` | Defaults `false`; explicitly opt in only after the one-course admission checks |
| `NORDYC_PUBLIC_INSTITUTION_ID`, `NORDYC_PUBLIC_PROGRAMME_ID` | Exact imported fictional target identities |
| `NORDYC_PUBLIC_PRINCIPAL_ID` | Existing policy principal with exact read-only institution scope |
| `NORDYC_WORKER_ENABLED` | Defaults `false`; leave off for the frozen public example |
| `VITE_PUBLIC_DEMO` | Public build-time boolean only; `.replit` derives it from the explicit runtime opt-in setting |
| `ANALYSIS_EXTERNAL_PROCESSING_ALLOWED`, `RESEARCH_ENABLED`, `GEMINI_ENABLED`, `ANALYSIS_GEMINI_FALLBACK_ENABLED` | All `false` |
| `NORDYC_DIST_DIR` | Optional built-frontend location; defaults to the repository's `frontend/dist` |

No Claude/Brave key is needed to read saved outputs. If retained managed credentials exist, keep them in Replit Secrets; their presence does not authorise a live call. Do not copy the localhost auto-entry setting or its private operator file into a public build.

## Managed PostgreSQL and permitted snapshot import

A local rehearsal exported/transferred **102 rows across 24 tables** into a new owned PostgreSQL schema, then verified current source permissions, canonical analysis outputs and exact fingerprints. Only the permitted authored fictional example and its necessary attributed UN standard references were selected. The bounded snapshot omits private PDF bytes/original-file storage, credentials and private runtime paths. It is not a backup of the real university upload or the complete old development database.

Replit's managed database was reachable and empty during inspection. That observation does not establish a completed import or production backup. Local Windows PostgreSQL records do not appear in Replit automatically. Do not switch to SQLite or assume the disposable local test database is a release database.

Before importing, independently confirm the intended managed database and authorisation, preserve the original workspace and inspect the snapshot. [The transfer helper](../scripts/transfer_programme.py) reads the connection from a named server environment variable, refuses an existing destination schema and creates a new random owner-marked schema. A non-loopback managed destination requires the explicit flag:

```sh
.venv/bin/python scripts/transfer_programme.py import \
  --database-url-env DATABASE_URL \
  --allow-managed-database \
  --file data/local/permitted-programme-snapshot.json
```

This is an administrator operation, not an HTTP/public endpoint. The path is illustrative and must point to the separately reviewed permitted snapshot. The helper applies the existing Alembic migrations through **0007_academic_action_plans** only in the newly created schema, restores bounded rows and verifies them before commit. Keep the import receipt private, configure its actual schema/target identities, and confirm results through an independent connection. It never modifies the source database or starts model/worker calls. Missing original files must not be represented as present uploads.

## Replit build, startup and preservation

The original Replit workspace has **25 uncommitted files**. Preserve a verified backup and create an isolated release checkout before applying release configuration; do not replace that workspace, reset its work or copy unreviewed files into the release. Its currently provisioned database must be explicitly selected and reviewed, rather than inferred from an ambient variable.

The added [`.replit` deployment section](../.replit) uses `deploymentTarget = "cloudrun"`, builds a Python virtual environment from pinned `requirements.lock`, installs the package with `--no-deps`, installs the locked frontend dependencies and builds the frontend with the explicit public boolean. The release run command is `.venv/bin/python scripts/run_web.py`. Existing development Run and port settings are unchanged. Replit documents these deployment keys in [its application configuration reference](https://docs.replit.com/features/project-setup/configuration).

Selecting/building this configuration is not publishing. Before any release, verify the exact isolated checkout/commit, private Secrets, imported managed schema and source admission, migration head, same-origin assets/API health, anonymous read-only target and denied mutation/admin/foreign routes. Confirm restart behavior, logging without secrets, backup/restore and provider gates. Record actual observed results and cost rather than assuming development forwarding establishes deployment readiness. Build/runtime/deployment billing is separate from the zero live AI/research requests in this preparation.

The current public-release result remains **PENDING**. Do not present an old forwarded development URL, a prepared build or a local import rehearsal as a newly deployed NORDYC service.
