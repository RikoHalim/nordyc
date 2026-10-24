// Prototype analysis over the repo's synthetic fixtures. Mirrors the planned Phase 4-6
// API shapes (docs/10_API_CONTRACT.md, docs/07_ACADEMIC_ACTIONS.md) so screens can later
// swap to fetch('/api/v1/...') without layout changes.
// shortcut: rules run in the browser on fixtures, replace with the backend analysis endpoints once Phase 4 exists.
import catalogue from '../../fixtures/synthetic_university_catalogue.json' with { type: 'json' }
import evidence from '../../fixtures/synthetic_evidence_snapshots.json' with { type: 'json' }

export const institution = catalogue.institution
export const programmes = catalogue.programmes
export const snapshots = evidence.snapshots
export const sources = evidence.sources

export type Programme = (typeof programmes)[number]
export type Course = Programme['courses'][number]
export type Scenario = 'moderate' | 'accelerated'
export type ActionKey =
  | 'no_change'
  | 'revise_syllabus'
  | 'workshops_and_industry_engagement'
  | 'request_review'

export const ACTION_LABEL: Record<ActionKey, string> = {
  no_change: 'No change (monitor pending review)',
  revise_syllabus: 'Consider syllabus review',
  workshops_and_industry_engagement: 'Hands-on workshop / industry engagement',
  request_review: 'Request review (evidence missing)',
}

// Synthetic inference: which fixture topic a course title *might* relate to. Title-only, so never proof of content.
const COURSE_TOPIC: Record<string, string> = {
  'syn-c-03': 'AI-assisted software test production',
  'syn-c-06': 'AI-assisted market research',
  'syn-c-08': 'AI-assisted market research',
  'syn-c-10': 'AI-assisted content drafting',
  'syn-c-12': 'AI-assisted content drafting',
}

// Stated scenario assumptions: accelerated AI adoption lowers the signal level that triggers review.
export const SCENARIOS: Record<Scenario, { label: string; review: number; engage: number; assumption: string }> = {
  moderate: { label: 'Moderate AI adoption', review: 50, engage: 25, assumption: 'Signal >= 50 suggests syllabus review; >= 25 suggests workshops.' },
  accelerated: { label: 'Accelerated AI adoption', review: 40, engage: 20, assumption: 'Signal >= 40 suggests syllabus review; >= 20 suggests workshops.' },
}

export type CourseResult = {
  course: Course
  topic: string | null
  signal: number | null
  sourceId: string | null
  observationDate: string
  primary: ActionKey
  alternatives: ActionKey[]
  conditions: string[]
  missingEvidence: string[]
  confidence: 'low' | 'insufficient_evidence'
  needsSyllabusConfirmation: true
  isFinalCurriculumVerdict: false
  reviewerStatus: 'pending'
}

export function analyseCourse(course: Course, snapshotId: string, scenario: Scenario): CourseResult {
  const snap = snapshots.find((s) => s.id === snapshotId)
  if (!snap) throw new Error(`Unknown snapshot ${snapshotId}`)
  const topic = COURSE_TOPIC[course.id] ?? null
  const item = topic ? snap.items.find((i) => i.topic === topic) : undefined
  const missing = ['Detailed syllabus / learning outcomes']
  if (course.year == null) missing.push('Year of study')
  if (course.elective == null) missing.push('Compulsory vs elective status')

  const base = {
    course, topic, observationDate: snap.observation_date,
    needsSyllabusConfirmation: true as const, isFinalCurriculumVerdict: false as const, reviewerStatus: 'pending' as const,
  }
  if (!item) {
    return {
      ...base, signal: null, sourceId: null, primary: 'request_review', alternatives: ['no_change'],
      conditions: [], missingEvidence: [...missing, 'No admissible workforce/AI evidence linked'], confidence: 'insufficient_evidence',
    }
  }
  const t = SCENARIOS[scenario]
  const primary: ActionKey =
    item.signal_index >= t.review ? 'revise_syllabus' : item.signal_index >= t.engage ? 'workshops_and_industry_engagement' : 'no_change'
  const alternatives = (['no_change', 'workshops_and_industry_engagement', 'revise_syllabus', 'request_review'] as ActionKey[]).filter((a) => a !== primary)
  return {
    ...base, signal: item.signal_index, sourceId: item.source_id, primary, alternatives,
    conditions: ['pending_detailed_syllabus_review'], missingEvidence: missing, confidence: 'low',
  }
}

export function analyseProgramme(p: Programme, snapshotId: string, scenario: Scenario): CourseResult[] {
  return p.courses.map((c) => analyseCourse(c, snapshotId, scenario))
}

// Comparison dimensions from docs/07: prefer the least disruptive adequately justified option.
export const ACTION_TRADEOFFS: Record<ActionKey, { disruption: string; speed: string; verification: string }> = {
  no_change: { disruption: 'None', speed: 'Immediate', verification: 'Confirm existing coverage from syllabus' },
  workshops_and_industry_engagement: { disruption: 'Low', speed: 'Weeks', verification: 'Hands-on assessment; attendance alone proves no skill' },
  revise_syllabus: { disruption: 'Medium', speed: 'One academic cycle', verification: 'Needs verified current outcomes + committee approval' },
  request_review: { disruption: 'None', speed: 'Immediate', verification: 'Gather missing evidence first' },
}
