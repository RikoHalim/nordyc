import { useState } from 'react'
import {
  ACTION_LABEL, ACTION_TRADEOFFS, SCENARIOS, analyseProgramme, institution, programmes, snapshots, sources,
  type CourseResult, type Programme, type Scenario,
} from './analysis'

type View = { name: 'explorer' } | { name: 'programme'; id: string } | { name: 'report'; id: string }

export default function App() {
  const [view, setView] = useState<View>({ name: 'explorer' })
  const [snapshotId, setSnapshotId] = useState(snapshots[snapshots.length - 1].id)
  const [scenario, setScenario] = useState<Scenario>('moderate')
  const programme = view.name !== 'explorer' ? programmes.find((p) => p.id === view.id)! : null

  return (
    <>
      <div className="synthetic-banner" role="status">
        SYNTHETIC DEMO DATA: fictional university, curriculum and evidence. Not XMUM and not live sources.
      </div>
      <header className="topbar">
        <button className="brand" onClick={() => setView({ name: 'explorer' })}>SHIFT//OS</button>
        <div className="controls">
          <label>
            Evidence snapshot
            <select value={snapshotId} onChange={(e) => setSnapshotId(e.target.value)}>
              {snapshots.map((s) => <option key={s.id} value={s.id}>{s.id} · observed {s.observation_date}</option>)}
            </select>
          </label>
          <label>
            Scenario
            <select value={scenario} onChange={(e) => setScenario(e.target.value as Scenario)}>
              {Object.entries(SCENARIOS).map(([k, s]) => <option key={k} value={k}>{s.label}</option>)}
            </select>
          </label>
        </div>
      </header>
      <main>
        {view.name === 'explorer' && <Explorer onOpen={(id) => setView({ name: 'programme', id })} />}
        {view.name === 'programme' && programme && (
          <ProgrammeView programme={programme} snapshotId={snapshotId} scenario={scenario}
            onBack={() => setView({ name: 'explorer' })} onReport={() => setView({ name: 'report', id: programme.id })} />
        )}
        {view.name === 'report' && programme && (
          <Report programme={programme} snapshotId={snapshotId} scenario={scenario}
            onBack={() => setView({ name: 'programme', id: programme.id })} />
        )}
      </main>
    </>
  )
}

function Explorer({ onOpen }: { onOpen: (id: string) => void }) {
  return (
    <section>
      <p className="eyebrow">Malaysia · {institution.source_kind}</p>
      <h1>{institution.name}</h1>
      <p className="muted">Programmes discovered from the catalogue. Course titles only; no syllabi imported.</p>
      <div className="grid">
        {programmes.map((p) => {
          const gaps = p.courses.filter((c) => c.year == null || c.elective == null).length
          return (
            <button key={p.id} className="card programme-card" onClick={() => onOpen(p.id)}>
              <span className="eyebrow">{p.discipline}</span>
              <strong>{p.name}</strong>
              <span>{p.courses.length} courses · 0 syllabi</span>
              {gaps > 0 && <span className="tag warn">{gaps} with missing year/type</span>}
              <span className="tag">Source: synthetic fixture (no URL)</span>
            </button>
          )
        })}
      </div>
      <p className="muted small">Catalogue coverage cannot certify full graduation requirements.</p>
    </section>
  )
}

function ProgrammeView({ programme, snapshotId, scenario, onBack, onReport }: {
  programme: Programme; snapshotId: string; scenario: Scenario; onBack: () => void; onReport: () => void
}) {
  const [ran, setRan] = useState(false)
  const [selected, setSelected] = useState<string | null>(null)
  const results = analyseProgramme(programme, snapshotId, scenario)
  const baseline = analyseProgramme(programme, snapshots[0].id, scenario)
  const current = results.find((r) => r.course.id === selected)

  return (
    <section>
      <button className="link" onClick={onBack}>← All programmes</button>
      <h1>{programme.name}</h1>
      <p className="muted">Whole-programme review against snapshot {snapshotId} under the {SCENARIOS[scenario].label} scenario.</p>
      {!ran ? (
        <button className="primary" onClick={() => setRan(true)}>Run programme analysis</button>
      ) : (
        <>
          <div className="toolbar">
            <span className="muted small">{SCENARIOS[scenario].assumption}</span>
            <button className="primary" onClick={onReport}>Draft report</button>
          </div>
          <div className="split">
            <div className="course-list">
              {results.map((r, i) => (
                <CourseCard key={r.course.id} r={r} changed={r.primary !== baseline[i].primary && snapshotId !== snapshots[0].id}
                  active={r.course.id === selected} onClick={() => setSelected(r.course.id)} />
              ))}
            </div>
            <aside className="inspector">
              {current ? <Inspector r={current} /> : <p className="muted">Select a course to inspect its evidence and options.</p>}
            </aside>
          </div>
        </>
      )}
    </section>
  )
}

function CourseCard({ r, changed, active, onClick }: { r: CourseResult; changed: boolean; active: boolean; onClick: () => void }) {
  return (
    <button className={`card course-card ${active ? 'active' : ''}`} onClick={onClick}>
      <div className="row">
        <strong>{r.course.title}</strong>
        <span className="tag">title only</span>
      </div>
      <span className="small muted">
        Year {r.course.year ?? 'unknown'} · {r.course.elective == null ? 'type unknown' : r.course.elective ? 'elective' : 'compulsory'}
      </span>
      <span className={`action action-${r.primary}`}>{ACTION_LABEL[r.primary]}</span>
      {r.topic && <span className="small">Review whether “{r.topic}” is covered.</span>}
      {changed && <span className="tag changed">Changed vs {snapshots[0].id}</span>}
    </button>
  )
}

function Inspector({ r }: { r: CourseResult }) {
  const src = sources.find((s) => s.id === r.sourceId)
  return (
    <div>
      <h2>{r.course.title}</h2>
      <p className="notice">Title-only record: content unknown. Needs syllabus confirmation; this is not a final curriculum verdict.</p>

      <h3>Evidence</h3>
      {src ? (
        <dl className="evidence">
          <dt>Signal</dt><dd>{r.topic}: index {r.signal}</dd>
          <dt>Observed</dt><dd>{r.observationDate}</dd>
          <dt>Publisher</dt><dd>{src.publisher}</dd>
          <dt>Class</dt><dd><span className="tag warn">{src.type}</span></dd>
          <dt>Link</dt><dd>{src.url ?? 'none (synthetic)'}</dd>
        </dl>
      ) : <p className="tag warn">insufficient_evidence</p>}

      <h3>Options compared</h3>
      <table>
        <thead><tr><th>Option</th><th>Disruption</th><th>Speed</th><th>Verification needed</th></tr></thead>
        <tbody>
          {[r.primary, ...r.alternatives].map((a, i) => (
            <tr key={a} className={i === 0 ? 'primary-row' : ''}>
              <td>{ACTION_LABEL[a]}{i === 0 && <span className="tag">AI primary</span>}</td>
              <td>{ACTION_TRADEOFFS[a].disruption}</td>
              <td>{ACTION_TRADEOFFS[a].speed}</td>
              <td>{ACTION_TRADEOFFS[a].verification}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Missing evidence</h3>
      <ul>{r.missingEvidence.map((m) => <li key={m}>{m}</li>)}</ul>
      <p className="small muted">
        Confidence: {r.confidence}{r.conditions.length > 0 && ` · condition: ${r.conditions.join(', ')}`} · reviewer status: {r.reviewerStatus}
      </p>
    </div>
  )
}

function Report({ programme, snapshotId, scenario, onBack }: { programme: Programme; snapshotId: string; scenario: Scenario; onBack: () => void }) {
  const results = analyseProgramme(programme, snapshotId, scenario)
  const flagged = results.filter((r) => r.primary !== 'no_change' && r.primary !== 'request_review')
  const unknown = results.filter((r) => r.confidence === 'insufficient_evidence')
  return (
    <section className="report">
      <button className="link" onClick={onBack}>← Back to analysis</button>
      <p className="eyebrow">Draft · reviewer status: pending</p>
      <h1>Programme review draft: {programme.name}</h1>
      <p>Evidence snapshot {snapshotId}; {SCENARIOS[scenario].label}. {SCENARIOS[scenario].assumption}</p>

      <h2>Review priorities</h2>
      {flagged.length === 0 ? <p>No course reached a review threshold in this snapshot.</p> : (
        <ol>{flagged.map((r) => (
          <li key={r.course.id}><strong>{r.course.title}</strong>: {ACTION_LABEL[r.primary]}. Review whether “{r.topic}” is covered
            (signal {r.signal}, {r.sourceId}, observed {r.observationDate}). Condition: pending detailed syllabus review.</li>
        ))}</ol>
      )}

      <h2>Insufficient evidence</h2>
      <p>{unknown.map((r) => r.course.title).join(', ') || 'None'}: no admissible evidence linked; no action proposed.</p>

      <h2>SDG rationale</h2>
      <p>SDG 4.4 (relevant skills for employment): the review targets whether graduates' skills keep pace with dated workforce/AI evidence. Link applies only once syllabus content is confirmed.</p>

      <h2>Limitations</h2>
      <ul>
        <li>All data is synthetic; no real university courses were audited.</li>
        <li>Course titles do not prove taught content.</li>
        <li>AI exposure signals are not replacement probabilities.</li>
        <li>Human committee decides; proposals are not approved actions.</li>
      </ul>
    </section>
  )
}
