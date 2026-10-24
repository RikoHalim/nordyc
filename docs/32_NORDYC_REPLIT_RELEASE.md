# NORDYC — Replit release preparation

## Current acceptance and scope

**Public deployment acceptance is PENDING.** The first read-only deployment built successfully but **FAILED promotion at the health check after approximately 14 minutes**. Its public URL returned **404** and was not live. Application runtime logs were unavailable, so the exact cause remains unconfirmed. A corrective adapter now prepares a runtime SHA/hash receipt instead of depending on Git at startup and explicitly binds/maps **8080**. Judge-upload republication is being started; success has not been established. NORDYC retains FastAPI/PostgreSQL, React and Replit hosting. These paths make no live AI/research requests; Gemini and fallback remain disabled.

Final current verification passes **1,173 backend tests including 21 PostgreSQL cases in 309.87 seconds**, **204 frontend tests**, TypeScript/production build and formatting. Focused checks also passed **46 backend plus 9 worker cases**. Real PostgreSQL acceptance persists two extracted courses, two offline findings, one review recommendation, a pathway and two scenarios, then confirms them independently. Actual browser verification against the production entrypoint on **8086** selected a PDF, observed HTTP **202**, retrieved both courses, ran **Generate results** and opened a saved recommendation with no observed browser errors. These are local production-entry observations, not public hosting acceptance or academic accuracy. **0 live AI/research requests.** Earlier results retain their original scope in [STATUS](../STATUS.md).

Implementation **ba3ab4f67e93fb6a06a950a1ab3396f0b800cc04** was followed by the owner's explicit request to push main. A source-identical history merge produced **c307860a39c0ef932a57c73e72ee083e4b17d52f**, pushed and remote-verified on both **main** and **feature/phase8-judge-demo**, without force-push. This later authorisation supersedes the earlier feature-only publication boundary; it does not rewrite historical no-main-change receipts.

The proposed public dataset is exactly one fictional Applied Data Science course in its own Data Science workspace. Its persisted offline outputs include five recommendations, five pathways, two hypothetical scenarios, two possible SDG contributions and an eight-section Action Plan. Fictional source provenance and backend flags remain explicit; authentic UN references remain attributed standards. Neither the example nor the software checks establish real university findings, academic approval, student competence or achieved SDG impact.

## Rename, recovery and access cleanup

The product display name and 19 documentation files now use NORDYC. Repository remotes in both local checkouts use the canonical `https://github.com/RikoHalim/nordyc.git`. Existing technical package/import names (`shiftos`), `SHIFTOS_*` variables, schema/ownership identifiers and local paths remain compatible. Archived Replit URLs and historical results are preserved.

All 15 remote refs were mirrored and a complete private recovery bundle was verified before cleanup. Five remote branches fully contained in retained history were removed: the Phase 2, Phase 5, Phase 6, Phase 7 and earlier Phase 8 React branches. Unique Gemini, Claude, `celilinss`, revert and main histories remain. No local branch deletion or force-push occurred. Cleanup itself performed no merge; the later explicitly authorised source-identical history merge is recorded above. Recovery material remains private and outside published source.

The running local preview's operator and reader policy now scopes only the new fictional Data Science institution. Other programme records remain in the old PostgreSQL schema and the prior access policy is backed up. Removing their active access does not erase their data. Recovery or broader access requires an explicit administrator decision; do not add them to the public reader's scope.

## One web origin and explicit read-only public access

[The web launcher](../scripts/run_web.py) runs [the same-origin application](../src/shiftos/web.py), serving `frontend/dist` and the existing protected FastAPI routes. It binds to the host-provided `PORT` (otherwise 8080). It does not migrate, seed, import data or install model mocks at startup. The ordinary API factory remains available separately.

Both public opt-ins are required: build the frontend with `VITE_PUBLIC_DEMO=true`, and set `NORDYC_PUBLIC_DEMO_ENABLED=true` only for the admitted isolated example. The runtime `/__public_demo` marker revalidates the target before reporting it available. Without that combination, normal manual scoped authentication remains. No token or policy is compiled into the frontend or returned by the marker.

The saved example requires an existing reader principal with exactly `read` permission and exactly the selected fictional institution. That institution must contain exactly one fictional programme and course, a current revision and schema-valid committed results with matching lineage/fingerprints and current source permissions. Its public reader cannot mutate the example. Optional judge upload sessions receive only the separate own-programme scope described below; ordinary uploads, reviews and source administration retain their existing authenticated boundaries. Foreign-institution/global administration access remains denied. Invalid or withdrawn evidence fails closed.

The new deployment CSP keeps script sources on the current origin and disallows inline scripts. It permits `unsafe-eval` because the existing AJV client compiles only the bundled OpenAPI schemas using `Function`; it does not compile request-supplied or external schemas. A real browser check caught and corrected an initially blank page when this compilation was blocked. This is an explicit compatibility tradeoff, not a claim of strict eval-free CSP. API permissions, source checks and the ban on anonymous mutations remain independent server controls.

Set `NORDYC_WORKER_ENABLED=false` for the frozen read-only example. It needs no new job execution. The optional judge-upload mode starts a restricted worker for its active session institutions and approved PDF/offline job kinds; it does not make a general worker or paid provider available. An ordinary authenticated institutional upload service still needs durable private storage, supervised operations, identity and separate release checks.

## Optional judge PDF sessions

`NORDYC_PUBLIC_UPLOADS_ENABLED` defaults **false**. Enabling it additionally requires the admitted public example, disabled paid-provider gates and a server-only session signing secret. The Library's **Try your own PDF** asks for programme/institution names and an official HTTPS programme URL; the institution origin is taken from that user-provided URL. Those details are unverified metadata, not discovered or certified university facts. One checkbox confirms permission to upload a public brochure containing no personal/private data.

The bootstrap issues a signed **HttpOnly, SameSite Strict** cookie. Its **one-hour expiry limits access; it does not delete uploaded files or database records**. No credential is returned in JSON, a frontend bundle or public URL. A session can read its own records and the saved example, but can write only its own programme through the restricted PDF and offline-analysis workflow. The example remains read-only. Other sessions, source administration, review/approval, advanced mapping and live AI/research requests remain denied. The ordinary authenticated operator flow remains separate.

Limits include **3 PDF submissions per session**, each at most **20 MB**, and **12 bounded submissions per session**. Current global caps are **100 sessions, 30 uploads and 500 submissions**. These are enforced server-side; a new page/tab is not an entitlement to unlimited requests. Extraction produces course candidates, and titles alone do not establish taught content. Offline outputs preserve missing-evidence states; they do not substitute the saved example's recommendations for an uploaded real programme.

Original PDF files currently remain private on **temporary instance-local storage**. Keep the release to **one Autoscale instance** while using that storage; it is not safe shared storage for multiple independent instances. A restart can lose an original needed by a queued extraction job even though PostgreSQL metadata survives. Shared durable private storage, retention/deletion tooling and operational restore acceptance remain pending. Do not promise browser-only storage, automatic deletion after one hour or durable recovery of originals.

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
| `NORDYC_PUBLIC_UPLOADS_ENABLED` | Defaults `false`; explicitly enables bounded judge sessions and their restricted worker only |
| `NORDYC_UPLOAD_SESSION_SECRET` | Server-only persistent signing value of at least 32 characters; otherwise the existing Replit `SESSION_SECRET` is used, subject to the same minimum |
| `VITE_PUBLIC_DEMO` | Public build-time boolean only; `.replit` derives it from the explicit runtime opt-in setting |
| `ANALYSIS_EXTERNAL_PROCESSING_ALLOWED`, `RESEARCH_ENABLED`, `GEMINI_ENABLED`, `ANALYSIS_GEMINI_FALLBACK_ENABLED` | All `false` |
| `NORDYC_DIST_DIR` | Optional built-frontend location; defaults to the repository's `frontend/dist` |

No Claude/Brave key is needed to read saved outputs. If retained managed credentials exist, keep them in Replit Secrets; their presence does not authorise a live call. Do not copy the localhost auto-entry setting or its private operator file into a public build.

## Managed PostgreSQL and permitted snapshot import

A local rehearsal exported/transferred **102 rows across 24 tables** into a new owned PostgreSQL schema, then verified current source permissions, canonical analysis outputs and exact fingerprints. Only the permitted authored fictional example and its necessary attributed UN standard references were selected. The bounded snapshot omits private PDF bytes/original-file storage, credentials and private runtime paths. It is not a backup of the real university upload or the complete old development database.

The selected managed Replit PostgreSQL database was initially inspected as empty, then the reviewed **102-row / 24-table** snapshot was explicitly imported into a fresh owned schema and verified. The isolated **e9c5516** release checkout passed HTTPS development checks against that imported data. This is a completed managed import, not a production backup or public-deployment acceptance. Local Windows records did not transfer automatically. The architecture remains PostgreSQL; no SQLite switch or assumption that the disposable local test cluster is a release database was used.

Before importing, independently confirm the intended managed database and authorisation, preserve the original workspace and inspect the snapshot. [The transfer helper](../scripts/transfer_programme.py) reads the connection from a named server environment variable, refuses an existing destination schema and creates a new random owner-marked schema. A non-loopback managed destination requires the explicit flag:

```sh
.venv/bin/python scripts/transfer_programme.py import \
  --database-url-env DATABASE_URL \
  --allow-managed-database \
  --file data/local/permitted-programme-snapshot.json
```

This is an administrator operation, not an HTTP/public endpoint. The path is illustrative and must point to the separately reviewed permitted snapshot. The helper applies the existing Alembic migrations through **0007_academic_action_plans** only in the newly created schema, restores bounded rows and verifies them before commit. Keep the import receipt private, configure its actual schema/target identities, and confirm results through an independent connection. It never modifies the source database or starts model/worker calls. Missing original files must not be represented as present uploads.

## Replit build, startup and preservation

The original Replit workspace's **215 tracked/nonignored files**, including its uncommitted work, were backed up before a separate release checkout was installed. **214 original files remain unchanged**; only the approved `.replit` deployment/port adapter changed, including **8080 → 80** forwarding. No original source checkout was reset or switched, and no unreviewed original source was copied into the release. The managed database was explicitly selected and reviewed rather than inferred from an ambient variable.

The added [`.replit` deployment section](../.replit) uses `deploymentTarget = "cloudrun"`, builds a Python virtual environment from pinned `requirements.lock`, installs the package with `--no-deps`, installs the locked frontend dependencies and builds the frontend with the explicit public boolean. The release run command is `.venv/bin/python scripts/run_web.py`. The repository's development launcher remains separate; the original Replit workspace received only the approved deployment/8080 forwarding adapter described above. Replit documents these deployment keys in [its application configuration reference](https://docs.replit.com/features/project-setup/configuration).

Selecting/building this configuration is not publishing. Before any release, verify the exact isolated checkout/commit, private Secrets, imported managed schema and source admission, migration head, same-origin assets/API health, anonymous read-only target and denied mutation/admin/foreign routes. Confirm restart behavior, logging without secrets, backup/restore and provider gates. Record actual observed results and cost rather than assuming development forwarding establishes deployment readiness. Build/runtime/deployment billing is separate from the zero live AI/research requests in this preparation.

The current public-release result remains **PENDING**. Do not present an old forwarded development URL, a prepared build or a local import rehearsal as a newly deployed NORDYC service.
