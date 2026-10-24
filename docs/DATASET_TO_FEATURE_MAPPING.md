# Dataset-to-feature evidence map

Baseline: 24 October 2026. IDs resolve to [dataset_registry.csv](../data/dataset_registry.csv). “Direct” means what the source itself establishes; the resulting academic judgement may still be an inference.

| Function | Minimum source dependencies | Direct evidence | NORDYC inference / missing evidence / permitted result |
|---|---|---|---|
| University programme discovery | `A-XMUM-DIRECTORY`, brochure index | Official observed programme labels/URLs | Current directory is not a complete historical census; report every discovered entry and blocked source |
| Course catalogue extraction | `A-XMUM-01..25`, `A-XMUM-MPU`, brochures | Published titles, explicit study-year and elective groups; EEE programme PLOs separately | Main Courses ≠ certified graduation curriculum; unknown semesters/types null; no made-up description |
| Academic competency benchmarking | `B-MQF-2024`, applicable B-MQA field, circulars; EAC when applicable | Normative graduate/core-area requirements within edition/level | Which standard applies and how it maps to a programme/course requires review; benchmark is not delivery evidence |
| Occupation and skill mapping | `C-ESCO`, `C-MASCO`; P1 MyNSR/ISCO | Taxonomy IDs, definitions, occupation-skill relations; selected Malaysian code context | Programme→occupation/course→skill and cross-taxonomy links remain uncertain, many-to-many and reviewable |
| Workforce demand analysis | Both `D-JMI-*`; P1 MyCOL/sector survey | Dated occupation-group advertising counts; separate survey shares and shortage classification | No individual skill demand, placements, graduate prospects or causal AI effect; restrict conclusions to published unit/coverage |
| AI occupational impact analysis | `E-ILO-2025`, observed studies; P1 local sector reports | Exposure estimates, bounded experiments, professional guidance and forecasts **as separate subtypes** | Local applicability and future adoption uncertain; exposure is not replacement probability |
| Course relevance screening | Curriculum + applicable standards + reviewed occupational/task evidence | Verified title/document level and independent external requirements | With titles only: `investigate` / `needs_syllabus_confirmation`; unsupported or uncited: `insufficient_evidence`; never “obsolete” |
| Programme-wide gap identification | All course appearances + elective structure + relevant benchmarks | Publicly documented offering and external benchmark | “Verify whether competency X is covered across courses”; absence of a matching title does not prove content absent; incomplete catalogue weakens gap claims |
| Academic intervention recommendations | A supported finding + admissible source pointer + review state | Sources supporting the concern/possible objective | Propose review, workshop or conditional revision; compare retain/no change. Major redesign/consolidation needs much stronger evidence and human decision |
| Scenario comparison/reassessment | Frozen curriculum, two D snapshots, fixed mapping/AI versions; explicit assumptions | What changed in dated observations or corrected evidence | Moderate/accelerated adoption are assumptions, not predicted unemployment. A changed timestamp alone must not change outcomes; no required artificial action flip |
| SDG mapping | `F-UN-SDG`; relevant task/skill/standard evidence; P1 UNESCO ESD | Official goal/target semantics | Role/skill→target is an explained inference; not UN endorsement or measured progress |
| Reskilling resources / supporting pathways | `F-OPENLEARN`; selected resource records; optional MIT/e-LATiH | Provider-stated subject/outcomes/hours/cost/prerequisites when present | Resource alignment and ordering require review; no guaranteed completion or proficiency; individual pathway also needs a skills profile and organiser clarification |

## Seven evidence classes and permitted use

| Required class | Example | Guardrail |
|---|---|---|
| `verified_university_fact` | Official XMUM published course title/year | Retain exact page/heading/PDF locator; published facts do not prove current classroom content |
| `published_standard` | MQA outcome, UN target, professional guideline | Normative benchmark; applicability and edition required; provider learning metadata separately typed |
| `occupation_requirement` | ESCO essential/optional skill link | Taxonomy requirement, not Malaysian hiring frequency or proof taught |
| `dated_workforce_signal` | DOSM occupation-group job offerings | Period, unit, geography, method and scope retained; no skill-level extrapolation |
| `dated_ai_capability` | ILO exposure, bounded study, sector foresight | Required subtype distinguishes observed experiment, exposure model, forecast and correction; normative guidance remains `published_standard` |
| `inference` | Course-title match, possible gap, SDG rationale, future adoption assumption | Input evidence links, explanation and uncertainty; human review required |
| `synthetic_demo` | Invented offline curriculum, learner, feasibility constraint or signal | Clearly fictional at all levels; never presented as actual XMUM taught detail or actual Malaysian evidence |

Resource metadata is a separately typed supporting reference under the current broad `published_standard` class; this does not imply a provider course is an accreditation standard. Refine subtype/validation in a future schema phase, without changing the required class vocabulary in this research task.

## Concrete traceable review examples

**Accounting:** the university title source can confirm a published course label. ESCO may identify accountant skill relations; MQA provides a programme benchmark; ILO characterises finance/clerical task exposure. Linking those to a review question about evaluating AI-assisted accounting outputs is inference. DOSM “Professionals” advertising counts cannot establish demand for that specific accounting skill. The output must ask whether relevant competencies/assessments are covered, without asserting they are absent.

**Communication:** an official brochure can resolve a truncated HTML title. MQA Media and Communication Studies and professional journalism guidance can motivate a source-verification/media-literacy review. Normative guidance does not measure AI automation, and a course title does not reveal its assessments. A proposed SDG16.10 link needs a specific public-information mechanism and a reviewer.

**Science/engineering:** retain the actual programme's physical/laboratory/foundational purpose. The corrected A-Lab study can support a bounded question about data validation in materials workflows; it does not establish that a marine, physics, chemical-engineering or TCM course should be replaced. Missing field-specific benchmark or task evidence returns an explicit data-limited finding.

These are reasoning templates, **not completed assessments of XMUM**. No occupation mapping, curriculum gap, recommendation or proficiency score was validated by this research.

## Data-limited execution contract

Every programme and every identified course appears in the coverage inventory. Missing evidence does not exclude the course. Minimum response includes evidence level, verified facts, supporting pointers, inference text, disagreements/unknowns and next confirmation needed. A course title alone permits a preliminary review prompt. Descriptions allow comparison only of published stated content. Detailed official syllabus/assessment evidence, when later available voluntarily, permits more specific review but never an automatic academic decision.

Changing a broad workforce group can update contextual text without changing the academic action. Adding a correction must reconsider dependent claims. Unrelated programme findings should remain unchanged. A working demonstration can show a legitimate abstention/no-change outcome; it should not manufacture sensitivity or a numerical relevance score.

Institutional analysis does not itself satisfy person-to-role matching, an explainable individual score or an ordered personalised pathway. The CV-upload exemption remains narrower than these unconfirmed waivers. Supporting SDG and resource datasets preserve options while the core institution-facing workflow stays intact.
