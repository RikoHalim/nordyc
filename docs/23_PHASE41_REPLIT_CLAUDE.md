# Phase 4.1 — Replit-managed Claude

This extension preserves the Phase 4 evidence engine, academic Pydantic contract, citation validator, deterministic workforce calculations, background worker and protected APIs. It adds a configurable Replit-managed Anthropic Messages adapter and optional explicit Gemini fallback. The user has authorized GitHub publication and this Replit handover; the completion report must confirm the published commit before it is imported. No Phase 5/6 implementation or public deployment is included.

## Availability and model selection

On 24 October 2026 this task runs in a local Windows checkout, not an authenticated Replit runtime. Neither `AI_INTEGRATIONS_ANTHROPIC_API_KEY` nor `AI_INTEGRATIONS_ANTHROPIC_BASE_URL` is present in the process or ignored local environment file. No Replit connection/configuration was discovered. **Managed access and a real Claude request cannot be verified here.** The user explicitly selected local completion with this live-test blocker documented. Existing Gemini and Brave live verification also remains open.

[Replit's official catalogue](https://docs.replit.com/features/integrations/replit-ai-integrations), checked on this date and labelled last updated 2 October 2026, lists **`claude-opus-5`** and older Opus alternatives. These are catalogue entries, not successful requests here. Keep `claude-opus-5` preferred and confirm it in the actual workspace. Any alternative requires an explicit model setting and a recorded reason. Compatibility of older models, including Opus 4.1, with [structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) must be checked separately.

Replit documents paid-plan access, organization controls and an approval flow for adding **Anthropic (Replit managed)** to an existing app. Its public documentation confirms Messages API support, but not this adapter's bridge variable/path contract. Managed credentials and an endpoint must actually be provisioned; a paid account alone is insufficient. [Replit AI Integrations](https://docs.replit.com/features/integrations/replit-ai-integrations).

## Replit handover

Use a separate development workspace and database for this verification. Import [RikoHalim/shift-os](https://github.com/RikoHalim/shift-os) through **Import → GitHub**, selecting `main`, after the publication report confirms the new commit. Replit's [GitHub import instructions](https://docs.replit.com/build/import-from-providers) describe connecting the repository. For an already imported workspace, inspect local changes and use the [Git pane's Pull action](https://docs.replit.com/features/workspace-tools/git-interface). Do not overwrite divergent work. The Shell equivalent below stops if a fast-forward is impossible:

```bash
git status --short
git branch --show-current
git pull --ff-only origin main
git rev-parse HEAD
```

Confirm the branch is `main` and compare the full SHA with the publication report. Source import transfers neither the local Windows PostgreSQL contents nor ignored files. Replit needs its own configured database, secrets and explicit reference imports. Do not upload `data/private`, `data/raw`, restricted MQA/research documents, `.env`, local reports or database dumps through Git.

Open **Shell** in the project root. Select/provision Python 3.12 in the workspace configuration if it is missing, then install this project's locked dependencies into its own environment. Do not replace the lock with automatically guessed latest packages. Replit documents [Shell dependency installation](https://docs.replit.com/features/project-setup/dependency-management); these commands use this repository's pip/setuptools configuration:

```bash
python3.12 --version
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e '.[dev]'
python -m pip check
```

In Replit's Database tool, select the **development** PostgreSQL database intended for this isolated check, then inspect **Settings** for its actual connection details. Use the provisioned host, database, user, credential and SSL options, without substituting guessed values. Replit documents the supplied [`DATABASE_URL`](https://docs.replit.com/features/data-and-storage/connection-details). SHIFT//OS requires SQLAlchemy's `postgresql+psycopg` driver prefix. If the managed value starts with `postgres://` or `postgresql://`, the following Shell-only normalization preserves its actual connection details and prints no credential. Repeat it in each new Shell used for migrations, API or worker; do not change the provider-managed database configuration:

```bash
shiftos_db_url="$(python - <<'PY'
import os
from sqlalchemy.engine import make_url
try:
    url = make_url(os.environ['DATABASE_URL'])
    if url.drivername not in {'postgres', 'postgresql', 'postgresql+psycopg'}:
        raise ValueError
    print(url.set(drivername='postgresql+psycopg').render_as_string(hide_password=False))
except Exception:
    raise SystemExit('Configure the actual isolated PostgreSQL DATABASE_URL in Secrets') from None
PY
)" && export DATABASE_URL="$shiftos_db_url"
unset shiftos_db_url
python - <<'PY'
from shiftos.core.config import Settings
Settings()
print('Settings validated; connection credentials were not printed')
PY
```

If either step fails, correct the supplied configuration before continuing. Keep any manually supplied database URL, managed credential and separate random `ANALYSIS_WRITE_TOKEN` and `CATALOGUE_WRITE_TOKEN` values in **Secrets**. Use a password manager to generate the tokens. Replit makes Secrets available as environment variables; non-sensitive flags can use its Configurations section. Never paste secret values into code, prompts, reports or browser URLs. [Secrets documentation](https://docs.replit.com/core-concepts/project-editor/app-setup/secrets).

Apply existing migrations to this isolated database:

```bash
python -m alembic upgrade head
python -m alembic current
python -m alembic history
```

The expected head is `0005_programme_analysis`; the chain contains `0001_foundation`, `0002_catalogue_sources`, `0003_curriculum_ingestion`, `0004_reference_evidence` and `0005_programme_analysis`. A successful upgrade creates schema, not evidence records. An unrelated existing database requires its own backup/review before migrations.

For a workspace-local API preview, keep this process running in one Shell:

```bash
source .venv/bin/activate
# Repeat DATABASE_URL normalization above in this Shell if needed.
python -m uvicorn shiftos.main:app --host 127.0.0.1 --port 8000
```

From a second initialized Shell, `curl --fail http://127.0.0.1:8000/health/ready` checks the database connection; `http://127.0.0.1:8000/docs` serves API documentation inside the workspace. This runbook uses loopback requests, without publishing the service. Replit's browser Preview uses [port forwarding](https://docs.replit.com/core-concepts/project-editor/app-setup/ports); do not infer that a forwarded port is private or change the server to public binding for this check. The worker is a separate process, started explicitly below.

## Configuration and controls

| Setting | Default / purpose |
|---|---|
| `ANALYSIS_MODEL_PROVIDER` | `gemini` preserves Phase 4 behavior; set `replit_claude` to select managed Claude |
| `CLAUDE_ENABLED` | `false`; explicit enable gate |
| `CLAUDE_MODEL` | `claude-opus-5`; configurable bounded Claude model identifier |
| `CLAUDE_MAX_OUTPUT_TOKENS` | `16384`; bounded to 1–16384 |
| `AI_INTEGRATIONS_ANTHROPIC_API_KEY` | Managed server credential; absent by default, never returned/logged |
| `AI_INTEGRATIONS_ANTHROPIC_BASE_URL` | Exact provisioned bridge base; absent by default |
| `ANALYSIS_GEMINI_FALLBACK_ENABLED` | `false`; optional Claude-to-Gemini fallback for operational failures only |
| `ANALYSIS_EXTERNAL_PROCESSING_ALLOWED` | Existing global approval gate; remains `false` by default |

Existing `ANALYSIS_PROVIDER_TIMEOUT_SECONDS`, bounded attempts and byte limits apply. Endpoint validation rejects embedded credentials, query/fragment injection, malformed/traversal paths and unsafe HTTP destinations; redirects are forbidden. Safe operator-provisioned bridge prefixes are supported; there is no guessed endpoint or public endpoint override. The managed endpoint is administrator-controlled server configuration, never request/user input. Source-specific processing permissions and admitted evidence remain mandatory for both providers; approving an integration does not authorize private university documents. Brave discovery, cache rules, source allowlists and deterministic workforce services are unchanged.

Claude uses the Messages API with `output_config.format` and a copied provider-compatible JSON schema. Unsupported schema constraints remain enforced by the original application Pydantic schema and grounding validator. [Anthropic documents this schema transformation pattern](https://platform.claude.com/docs/en/build-with-claude/structured-outputs). Native Anthropic citations, tool use, web search and prompt caching are not enabled; SHIFT//OS retains its existing citation IDs, exact excerpts, course associations and rights validation. Thinking blocks are not persisted as findings. Incomplete/refused/malformed responses cannot become accepted course results.

Optional fallback occurs only after Claude unavailability, bounded deadline or rate-limit failure. It requires explicit opt-in and separately enabled/configured Gemini access. Authentication/privacy/configuration/protocol failures and invalid schema/citations do not trigger cross-provider fallback. A grounded-output repair stays on the same provider. Fallback is disclosed and the job remains PARTIAL; it never claims verified Claude output when Gemini supplied the findings. Remaining failures preserve all courses with deterministic insufficiency.

## Provision managed Claude before live verification

In the imported app, request **only** the existing Replit-managed Anthropic connection, without asking Agent to rewrite the backend or start another feature. Confirm the approval prompt and **Anthropic (Replit managed)** label. If the account/organization does not offer that connection or the preferred model, record the exact access limitation and stop live verification.

Inspect the connection's runtime configuration privately. Map its actual managed credential and actual provisioned bridge base to this application's `AI_INTEGRATIONS_ANTHROPIC_API_KEY` and `AI_INTEGRATIONS_ANTHROPIC_BASE_URL` settings through Secrets if necessary. These names are **our adapter contract**, not a guarantee that Replit automatically exports those exact variables. Do not guess a host, add a personal `ANTHROPIC_API_KEY`, point at the direct Anthropic endpoint or print all environment values. The adapter appends `/v1/messages` once; if the provisioned transport contract differs, retain a blocker rather than weakening endpoint validation.

Set these non-sensitive verification flags in the workspace configuration:

```text
ANALYSIS_MODEL_PROVIDER=replit_claude
CLAUDE_ENABLED=true
CLAUDE_MODEL=claude-opus-5
CLAUDE_MAX_OUTPUT_TOKENS=4096
ANALYSIS_EXTERNAL_PROCESSING_ALLOWED=true
ANALYSIS_GEMINI_FALLBACK_ENABLED=false
GEMINI_ENABLED=false
RESEARCH_ENABLED=false
DISCOVERY_ENABLED=false
DISCOVERY_TERMS_REVIEWED=false
ANALYSIS_PROVIDER_MAX_ATTEMPTS=1
ANALYSIS_PERMISSIONS_PATH=data/analysis_permissions.json
```

The global approval is for this fictional inventory and permitted ESCO excerpt only. Confirm the configured permission file grants all three processing/output flags with a basis for `C-ESCO-V103`. Do not broaden permission to private documents. Restart initialized API/worker Shells after Secrets or configuration changes so they use the intended values.

## Zero-call preflight and bounded one-course check

Configuration inspection makes **zero network requests** and needs no database connection:

```bash
python -m shiftos.cli verify-claude --report data/local/phase41-claude-preflight.json
```

Missing/disabled configuration returns a structured `blocked` report and exit code 1. `configuration_ready` means configuration passes preflight, not that connectivity, authentication, model availability or proxy schema support has been verified.

Only after Replit provisions access, the following explicitly opts into one synthetic course request:

```bash
python -m shiftos.cli verify-claude --live --report data/local/phase41-claude-live.json
```

This helper pairs one explicitly fictional course/institution with an attributed genuine ESCO v1.0.3 skill excerpt from the permitted frozen reference pack. It preserves the original identifier, locator, edition and date limitations, and labels the copied packet as a synthetic verification lane; the source itself is not invented. The explicit `C-ESCO-V103` processing policy must allow use before any request. No real university documents are included. It caps output at 4096 tokens, disables provider fallback and transport retries, validates the existing `ProgrammeResult` plus supporting citations, and returns secret-free actual model/usage information. It is an isolated provider smoke, **not a database/API persistence proof**. Reports remain under ignored `data/local`.

Require `status=live_verified`, `provider_requests=1`, `schema_validated=true`, `grounding_validated=true` and a positive `citation_count`. Compare `requested_model`, upstream `actual_model` and `preferred_model_used`; a different returned model is disclosed, not proof that Opus 5 ran. Missing model identity, missing citations, refusal, rate limit or validation failure fails this check without an automatic second request. `observed_cost=null` is expected. If report-file export fails, the CLI preserves the completed result on stdout with `report_write_failed=true` and exits 1: retain that stdout securely, inspect its actual request count, and do not repeat a potentially billable call merely to recreate the file.

## Separate worker → PostgreSQL → protected API proof

This is a **second, explicitly initiated live check** after the dedicated helper. It exercises persistence and can incur additional usage. Keep fallback/research disabled. The ordinary worker may repair invalid output once on the same provider; with one transport attempt per generation, a one-course run can still make two requests. Do not run either test repeatedly to obtain a preferred answer.

Git has not transferred the local evidence database. Import the genuine permitted legacy ESCO subset explicitly, without network acquisition:

```bash
python -m shiftos.cli ingest-evidence --dataset C-ESCO-V103 \
  --file data/reference_packs/esco-v1.0.3.subset.reviewed.json \
  --retrieved-at 2026-10-23T19:57:05.013428+00:00 \
  --report data/local/replit-esco-real-import.json
```

A fresh successful import reports 87 normalized source records (38 occupations, 10 skills, 39 relationships); replay reports `UNCHANGED`. These are genuine legacy source records, not a current taxonomy or Malaysian demand measurement. The separate synthetic analysis lane deliberately cannot use real-lane records. Prepare one **unmodified genuine skill** as a clearly labelled verification copy and create one fictional inventory, using existing models only:

```bash
python - <<'PY'
import copy, json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from shiftos.core.config import Settings
from shiftos.db.session import create_database
from shiftos.models import Course, Institution, Programme, ProgrammeRevision

directory = Path('data/local')
directory.mkdir(parents=True, exist_ok=True)
pack_path = Path('data/reference_packs/esco-v1.0.3.subset.reviewed.json')
pack = json.loads(pack_path.read_text(encoding='utf-8'))
uri = 'http://data.europa.eu/esco/skill/700ea222-8139-4c48-95cf-014855565530'
skill = next(row for row in pack['records'] if row['kind'] == 'skill' and row['key'] == uri)
copy_pack = copy.deepcopy(pack)
copy_pack['records'] = [copy.deepcopy(skill)]
copy_pack['metadata'].update({
    'verification_copy': True, 'original_source_is_synthetic': False,
    'original_source_pack': str(pack_path),
    'adaptation_notice': pack['metadata']['adaptation_notice'] +
        ' One unchanged skill copied into a synthetic verification lane. '
        'Only the university/course association is fictional.',
})
(directory / 'replit-esco-verification-copy.reviewed.json').write_text(
    json.dumps(copy_pack, ensure_ascii=False, indent=2), encoding='utf-8')

ids = {key: uuid5(NAMESPACE_URL, 'shiftos:replit-claude-one-course-v1:' + key)
       for key in ('institution', 'programme', 'revision', 'course')}
database = create_database(Settings().database_url.get_secret_value())
try:
    with database.session_factory() as session:
        def ensure(model, key, **values):
            row = session.get(model, ids[key])
            if row is None:
                row = model(id=ids[key], **values)
                session.add(row)
                session.flush()
            else:
                assert all(getattr(row, k) == v for k, v in values.items()), 'Fixture conflict'
            return row
        ensure(Institution, 'institution', name='SYNTHETIC Replit Verification University',
               country='MY', is_synthetic=True)
        programme = ensure(Programme, 'programme', institution_id=ids['institution'],
            name='SYNTHETIC Bachelor of Water Engineering', discipline_key='engineering',
            is_synthetic=True)
        ensure(ProgrammeRevision, 'revision', programme_id=ids['programme'],
               version_label='synthetic-claude-verification-v1', is_synthetic=True)
        assert programme.active_revision_id in (None, ids['revision']), 'Revision conflict'
        programme.active_revision_id = ids['revision']
        ensure(Course, 'course', programme_revision_id=ids['revision'],
               course_name='SYNTHETIC Irrigation Systems', year=1,
               detailed_syllabus_available=False, is_synthetic=True)
        session.commit()
finally:
    database.engine.dispose()
(directory / 'replit-claude-inventory.json').write_text(
    json.dumps({key: str(value) for key, value in ids.items()}, indent=2), encoding='utf-8')
print('Prepared one fictional course and one attributed, genuine-source verification copy')
PY
python -m shiftos.cli ingest-evidence --dataset C-ESCO-V103 --synthetic \
  --file data/local/replit-esco-verification-copy.reviewed.json \
  --retrieved-at 2026-10-23T19:57:05.013428+00:00 \
  --report data/local/replit-esco-copy-import.json
```

The copy import must report one skill or `UNCHANGED`. Its `is_synthetic=true` identifies the isolated verification copy; its actual ESCO text, concept URI, source locators, edition, attribution and partial-archive limitations remain genuine. No invented ESCO source or fictional academic standard is added. Do not clear existing real/synthetic records or change the lane filters.

Before spending on the worker, prove that the normal internal retrieval path admits the exact quote under the configured source policy. This makes no model/search request:

```bash
python - <<'PY'
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID
from shiftos.core.config import Settings
from shiftos.db.session import create_database
from shiftos.services.analysis.claude_verification import inspect_claude_configuration
from shiftos.services.analysis.retrieval import retrieve_evidence
settings = Settings()
assert inspect_claude_configuration(settings)['status'] == 'configuration_ready'
ids = json.loads(Path('data/local/replit-claude-inventory.json').read_text())
policy = json.loads(settings.analysis_permissions_path.read_text())['sources']
database = create_database(settings.database_url.get_secret_value())
try:
    with database.session_factory() as session:
        packet = retrieve_evidence(session, UUID(ids['revision']), datetime.now(UTC),
                                   permitted_sources=policy)
    assert packet.is_synthetic and len(packet.courses) == 1
    refs = [r for r in packet.references if r.kind == 'skill'
            and r.facts.get('external_id') ==
                'http://data.europa.eu/esco/skill/700ea222-8139-4c48-95cf-014855565530']
    assert len(refs) == 1 and refs[0].model_eligible
    assert refs[0].excerpt == 'irrigation systems: The methods and systems management in irrigation.'
    assert refs[0].id in packet.courses[0].reference_ids
    Path('data/local/replit-claude-admitted-packet.json').write_text(
        packet.model_dump_json(indent=2), encoding='utf-8')
    print('One genuine-source quote admitted; title/content, historical and date limits retained')
finally:
    database.engine.dispose()
PY
python -m shiftos.cli analyse-programme \
  --programme "$(python -c "import json; print(json.load(open('data/local/replit-claude-inventory.json'))['programme'])")" \
  --mode live --no-research --idempotency-key replit-claude-one-course-v1 \
  > data/local/replit-claude-queued.json
python -m shiftos.cli worker --once
```

Use an otherwise idle verification database: `worker --once` processes the next eligible queued job, not a requested job ID. Check that its printed ID matches `job_id` in the queue report. Keep the loopback API process running with the same database, policy and tokens. Read the persisted run and owned course through protected HTTP, with token values supplied from Settings rather than printed in a command:

```bash
python - <<'PY'
import json
from pathlib import Path
from uuid import UUID
import httpx
from sqlalchemy import select
from shiftos.core.config import Settings
from shiftos.db.session import create_database
from shiftos.models import AnalysisRun, CourseFinding, Job
settings = Settings()
queued = json.loads(Path('data/local/replit-claude-queued.json').read_text())
run_id = queued['analysis_id']
headers = {'X-Analysis-Token': settings.analysis_write_token.get_secret_value()}
with httpx.Client(base_url='http://127.0.0.1:8000', headers=headers, trust_env=False) as client:
    response = client.get(f'/api/v1/analyses/{run_id}')
    response.raise_for_status()
    run = response.json()
    response = client.get(f'/api/v1/analyses/{run_id}/courses')
    response.raise_for_status()
    page = response.json()
    assert run['is_synthetic'] and run['status'] == 'SUCCEEDED', 'Inspect failed/partial run'
    assert not run['needs_evidence_revalidation'], 'Recheck current rights/source status'
    assert run['summary_json']['result_mode'] == 'live_model'
    assert page['total'] == 1
    finding = page['items'][0]
    detail = client.get(f"/api/v1/analyses/{run_id}/courses/{finding['course_id']}")
    detail.raise_for_status()
    assert detail.json() == finding
    dimensions = ('foundational_relevance', 'ai_transformation', 'workforce_alignment',
                  'curriculum_currency', 'future_resilience')
    citations = [citation for name in dimensions
                 for citation in finding['result_json'][name]['citations']]
    references = {r['id']: r for r in run['manifest_json']['packet']['references']}
    assert citations, 'No citation returned; citation smoke remains unproven, do not auto-retry'
    assert all(c['reference_id'] in references and
               ' '.join(c['quote'].split()) in
               ' '.join(references[c['reference_id']]['excerpt'].split()) for c in citations)
    assert finding['result_json']['needs_syllabus_confirmation']
    assert finding['result_json']['is_final_curriculum_verdict'] is False
    model = run['manifest_json']['model_processing']
    assert model['status'] == 'verified_output' and model['request_count'] >= 1
    assert all(r['provider'] == 'replit_claude' and r['actual_model'] for r in model['responses'])
    database = create_database(settings.database_url.get_secret_value())
    try:
        with database.session_factory() as session:
            stored = session.get(AnalysisRun, UUID(run_id))
            assert stored is not None and stored.fingerprint == run['fingerprint']
            rows = session.scalars(select(CourseFinding).where(
                CourseFinding.run_id == stored.id)).all()
            assert len(rows) == 1 and str(rows[0].course_id) == finding['course_id']
            assert session.get(Job, stored.job_id).status.value == run['status']
    finally:
        database.engine.dispose()
    Path('data/local/replit-claude-persisted-api-proof.json').write_text(
        json.dumps({'run': run, 'courses': page}, indent=2), encoding='utf-8')
    print(json.dumps({'status': run['status'], 'model_name': run['model_name'],
                      'responses': model['responses'], 'course_count': page['total'],
                      'citation_count': len(citations), 'fingerprint': run['fingerprint']}))
PY
```

These HTTP reads are backed by the migrated PostgreSQL records. Check the same run ID in the Database tool's `analysis_runs` and the one owned row in `course_findings`; `job_id` links its terminal `jobs` record. Re-run the **same queue command** with the same idempotency key only to confirm it returns the identical analysis/job IDs; it must not create another queued model job. Inspect model metadata instead of treating an HTTP 200, `SUCCEEDED` or an offline insufficiency result as evidence Claude ran. If a provider call, quote, permission check or database/API assertion fails, retain the report and mark that step blocked/failed. Never manufacture a source, citation, syllabus or usage amount to complete the checklist.

## Persistence, usage and costs

No new tables, migrations, HTTP routes, dependencies or academic result fields are required. Existing `analysis_runs.manifest_json.model_processing.responses` stores whitelisted per-invocation provider/requested model/returned model/token usage/request count/status. Error codes and fallback transitions are explicit. Model-generation invocations are distinct from actual HTTP attempts. `analysis_runs.model_name` records returned model identifiers only; the selected provider/model remains separate in the manifest. Request/response bodies, headers, credentials and chain-of-thought are excluded from this audit metadata. Protected API retrieval uses the existing source-text redaction/revalidation path.

If policy/inventory changes prevent final publication after a response, a still-running job retains sanitized model usage on its failed run/job without publishing source text or findings. Already terminated jobs reject late writes. Abrupt process loss or cancellation before accounting persists can leave an audit gap; reconcile those requests with Replit's external usage page rather than treating the local manifest as a complete billing ledger.

`observed_cost` remains null when no actual billing amount is available. Token counts do not establish a billed amount. Reconcile actual request timestamps and the relevant app against Replit's external [usage page](https://docs.replit.com/features/integrations/replit-ai-integrations#viewing-your-usage), which documents credit billing by app. Keep any observed charge separately identified with its billing window; do not convert direct-provider price estimates into a claimed Replit invoice. No billing statement is accessible in the local Windows workspace, no actual model has run there, and no cost or model-quality claim is made from mocks.

## Measured results and stop boundary

The final local suite passed **756 tests**, including **13 PostgreSQL integration cases**, with zero failures/skips; see [STATUS](../STATUS.md) for the measured environment, remaining warning and exact live-test status. Automated provider/worker/database/API tests use explicitly synthetic fixtures and mocked responses; PostgreSQL persistence is verified separately from provider connectivity. All five embedded Python examples were syntax-checked. The fictional-course preparation, explicit 87-record genuine-pack import, one-skill synthetic-lane copy import and exact-quote internal retrieval were also executed successfully in a disposable local PostgreSQL schema, then cleaned up, with zero model/search requests. These checks do not verify Linux/Replit execution or the later live API proof. A blocked preflight is a correctly reported access limitation, not a successful Claude integration smoke.

**Phase 4.1 live verification remains incomplete** until managed access, actual `claude-opus-5` structured output, supporting citations and a genuine worker-to-PostgreSQL-to-API round trip are observed in Replit. Stop here; do not start academic actions or pathways.
