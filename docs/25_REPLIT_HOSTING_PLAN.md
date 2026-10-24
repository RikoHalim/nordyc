# Replit hosting plan — direct Google AI, no deployment in this phase

Replit remains the official future hosting platform. Gemini 4 Argon is primary AI,
accessed directly through Google; Brave Search is external research. Replit AI
Integrations/managed Claude are discontinued for this MVP; retained legacy code is
not used in this plan. Development stays local in Codex/VS Code and GitHub.
This is planning only: no provisioning, deployment files or data transfer occurred.

## Environment and secrets

Use the existing environment settings. Replit documents environment-based
[Secrets](https://docs.replit.com/core-concepts/project-editor/app-setup/secrets)
and database [connection details](https://docs.replit.com/features/data-and-storage/connection-details).
Verify development/production values separately. Never print environment dumps
or commit local .env files.

| Setting | Later Replit requirement |
|---|---|
| APP_ENV | production for production, distinct from development/test |
| DATABASE_URL | Actual intended PostgreSQL connection with postgresql+psycopg driver and real TLS/query options retained |
| GEMINI_API_KEY | Private Google AI Studio credential in Replit Secrets for the intended paid API project |
| GEMINI_MODEL / ANALYSIS_MODEL_PROVIDER | gemini-4-argon / gemini |
| GEMINI_ENABLED / ANALYSIS_EXTERNAL_PROCESSING_ALLOWED | Explicit true only after access/billing/source/privacy checks |
| GEMINI_THINKING_LEVEL | medium; low/high configurable for later evaluation |
| GEMINI_MAX_OUTPUT_TOKENS / GEMINI_TIMEOUT_SECONDS | Initially 32768 / 180; hard bounds 65536 / 300 and remaining worker deadline |
| ANALYSIS_PROVIDER_MAX_ATTEMPTS | 1 for initial paid verification; maximum 3 for separately reviewed operation |
| ANALYSIS_WRITE_TOKEN / CATALOGUE_WRITE_TOKEN | Private nonempty secrets; these MVP guards are not complete user/tenant authorization |
| BRAVE_SEARCH_API_KEY / RESEARCH_ENABLED | Separate private Brave key and explicit permission; otherwise research remains disabled |
| ANALYSIS_PERMISSIONS_PATH / ANALYSIS_RESEARCH_POLICY | Reviewed source/research policies relative to the application working directory |
| CLAUDE_ENABLED / ANALYSIS_GEMINI_FALLBACK_ENABLED | false; do not provision managed Anthropic credentials |
| CURRICULUM_UPLOAD_DIR | Future durable private storage/mount, with reviewed retention; no local Windows path |

Use GEMINI_API_KEY, not SDK GOOGLE_API_KEY discovery or a Replit-managed alias.
A consumer Google AI subscription does not prove API credits. Google model access/
billing/quota and Brave rights are separate from Replit hosting billing.

If Replit supplies a postgresql:// or postgres:// URL, privately translate only the
driver prefix to postgresql+psycopg://, retaining credentials, host, port, database,
percent-encoding and TLS parameters. Do not log it. Existing settings deliberately
reject other drivers. Do not use a local developer database or disposable test schema.

## Runtime and migration lifecycle

Use Python 3.12+, existing requirements.lock and package installation. Preserve
SQLAlchemy/Alembic instead of replacing them with a platform ORM. Keep the project
root as working directory for existing relative policy paths.

Plan separate supervised processes sharing the intended database/policies/secrets:

```bash
# Web process: verify PORT against the actual Replit runtime/port mapping.
uvicorn shiftos.main:app --host 0.0.0.0 --port "$PORT"

# Separate durable worker; do not spawn it in a request or web startup.
python -m shiftos.cli worker
```

Set/verify PORT in that environment; no mapping is installed here. Reload is for
development only. Replit's [deployment types](https://docs.replit.com/features/publishing/deployment-types)
describe Reserved VM support for always-on/background workloads. Choose appropriate
worker hosting/process supervision later; an autoscaled request-only web process
must not be assumed to keep a worker alive. Do not work around this with unsupervised
shell backgrounding. Restart/health/capacity setup belongs to later deployment work.

Back up/select the intended database before a later explicit release migration:

```bash
python -m alembic current
python -m alembic heads
python -m alembic upgrade head
```

Current head is 0005_programme_analysis. Migrations are administrative release work,
not concurrent web startup. Inspect schema match and /health/ready; readiness proves
connectivity, not completed migrations. Local rows, snapshots, raw/private files and
reports do not transfer through Git. Import only permitted packs/synthetic fixtures
using existing provenance-aware services. Never silently copy restricted research.

## Network, limits and observability

Later verify HTTPS/DNS/TLS access to generativelanguage.googleapis.com and, only
when enabled, the separate Brave endpoint. Existing transport uses verified TLS,
fixed provider origins, no redirects, trust_env=false and bounded streaming reads.
Do not weaken TLS/source SSRF/robots/permission rules. If a hosting network requires
a proxy, assess it explicitly; environment proxies are not silently trusted.

Gemini uses stateless synchronous Interactions: store=false, no provider background
execution/polling/tools/agents. Provider timeout/retries and one validation repair
are bounded by the 600-second worker budget. Request/response caps are 1,000,000
bytes. Slow HTTP submissions enqueue jobs and return existing IDs. Failed processing
retains explicit partial/insufficient course results; polling must not replay paid work.

Retain request/job IDs, status, safe errors, returned model, observed tokens,
thinking/budgets and latency. Never log keys/headers, raw rejected responses or private
source text. Cost requires actual account evidence; list-price estimates are separate.
Keep source permissions, citation validation and offline synthetic mode intact.

## Compatibility assessment and later gates

The backend uses portable Python/environment variables, platform-independent HTTP,
PostgreSQL and separate durable workers. **It is architecturally compatible with
future Replit hosting, but no Replit runtime/deployment has been verified.**
Remote TLS/database/migrations, process supervision, durable private storage,
retention, Google/Brave access, production identity/tenant controls, backups and
monitoring remain later acceptance work. Current tokens are not complete production
security.

First close [Phase 4 local live gates](24_PHASE4_GEMINI.md), then complete separately
authorized integration/security/deployment phases. Do not deploy or start Phase 5/6
from this planning document.
