// Self-check for src/analysis.ts. Run: npm run check
import assert from 'node:assert/strict'
import { analyseProgramme, programmes } from '../src/analysis.ts'

const swe = programmes.find((p) => p.id === 'syn-prg-swe')!
const sqe = (snap: string, sc: 'moderate' | 'accelerated') =>
  analyseProgramme(swe, snap, sc).find((r) => r.course.id === 'syn-c-03')!

// Snapshot change must traceably change the outcome (demo step 8).
assert.equal(sqe('syn-snap-A', 'moderate').primary, 'no_change')
assert.equal(sqe('syn-snap-B', 'moderate').primary, 'revise_syllabus')
// Scenario lowers thresholds: signal 22 crosses accelerated engage threshold (20).
assert.equal(sqe('syn-snap-A', 'accelerated').primary, 'workshops_and_industry_engagement')

for (const p of programmes) {
  for (const r of analyseProgramme(p, 'syn-snap-B', 'moderate')) {
    assert.equal(r.isFinalCurriculumVerdict, false)
    assert.ok(r.alternatives.includes('no_change') || r.primary === 'no_change', 'no_change always comparable')
    // Every recommendation cites evidence or reports insufficient_evidence.
    assert.ok(r.sourceId !== null || r.confidence === 'insufficient_evidence')
  }
}
console.log('analysis checks passed')
