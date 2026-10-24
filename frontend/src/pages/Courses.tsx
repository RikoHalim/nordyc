import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  ArrowUpRight,
  BookOpen,
  FileCheck2,
  Layers,
  Search,
  Upload,
} from "lucide-react";
import { useWorkspace } from "../app/workspace";
import { useResource } from "../lib/resource";
import GenerateReview from "../components/GenerateReview";
import { ApiError, validateResponse } from "../api/client";
import {
  dateLabel,
  humanise,
  isPending,
  type Course,
  type Model,
  type Page,
} from "../api/types";
import { safeUrl } from "../components/EvidenceDrawer";
import {
  Badge,
  Card,
  Citations,
  Empty,
  ErrorState,
  Loading,
  Notice,
  PageHeading,
  Status,
  TextList,
} from "../components/ui";

type Analysis = Model<"AnalysisRead">;
type Finding = Model<"CourseFindingResult">;
const dimensions = [
  "foundational_relevance",
  "ai_transformation",
  "workforce_alignment",
  "curriculum_currency",
  "future_resilience",
] as const;

export default function Courses() {
  const { api, programme, revisionId, access } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const [year, setYear] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [busy, setBusy] = useState(false);
  const [mutationError, setMutationError] = useState<ApiError | null>(null);
  const [historyOffset, setHistoryOffset] = useState(0);
  const inventory = useResource(
    `courses:${programme.id}:${revisionId}`,
    (signal) =>
      revisionId
        ? api.all<Course>(
            `/api/v1/programmes/${programme.id}/revisions/${revisionId}/courses`,
            "CoursePage",
            signal,
          )
        : Promise.resolve([]),
    30_000,
    true,
  );
  const history = useResource(
    `course-history:${programme.id}:${revisionId}:${historyOffset}`,
    (signal) =>
      api.get<Page<Analysis>>(
        `/api/v1/programmes/${programme.id}/analyses?limit=10&offset=${historyOffset}`,
        "Page_AnalysisRead_",
        signal,
      ),
    3000,
    true,
  );
  const rows =
    history.data?.items
      .filter((row) => row.programme_revision_id === revisionId)
      .sort((a, b) => b.created_at.localeCompare(a.created_at)) || [];
  const requested = params.get("analysis");
  const runId = requested || rows[0]?.id;
  const result = useResource(
    runId ? `course-result:${programme.id}:${revisionId}:${runId}` : null,
    async (signal) => {
      const run = await api.get<Analysis>(
        `/api/v1/analyses/${runId}`,
        "AnalysisRead",
        signal,
      );
      if (
        run.programme_id !== programme.id ||
        run.programme_revision_id !== revisionId
      )
        throw new ApiError("NOT_FOUND", 404);
      if (
        isPending(run.status) ||
        run.status === "FAILED" ||
        run.needs_evidence_revalidation
      )
        return { run, findings: [] as Finding[] };
      const findings = await api.all<Model<"FindingRead">>(
        `/api/v1/analyses/${run.id}/courses`,
        "Page_FindingRead_",
        signal,
      );
      if (findings.some((row) => row.needs_evidence_revalidation))
        throw new ApiError("CONFLICT", 409);
      return {
        run,
        findings: findings.map((row) =>
          validateResponse<Finding>(row.result_json, "CourseFindingResult"),
        ),
      };
    },
    3000,
    true,
  );
  if (inventory.loading)
    return <Loading label="Loading the learning journey" />;
  if (inventory.error)
    return <ErrorState error={inventory.error} retry={inventory.reload} />;
  const courses = inventory.data || [];
  const years = [...new Set(courses.map((row) => row.year))].sort(
    (a, b) => (a ?? Number.MAX_SAFE_INTEGER) - (b ?? Number.MAX_SAFE_INTEGER),
  );
  const filtered = courses.filter(
    (row) =>
      (year === "all" || String(row.year) === year) &&
      `${row.course_name} ${row.course_code || ""}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  const run = result.data?.run;
  const selectRun = (id: string) => {
    const next = new URLSearchParams(params);
    next.set("analysis", id);
    setParams(next);
  };
  return (
    <>
      <PageHeading
        eyebrow="The documented learning journey"
        title="Learning journey"
        actions={
          access.permissions.includes("write") && (
            <Link
              className="button secondary"
              to={`../upload${revisionId ? `?revision=${revisionId}` : ""}`}
            >
              <Upload size={16} />
              Upload &amp; review
            </Link>
          )
        }
      >
        See how recorded courses connect. Unknown content stays unknown.
      </PageHeading>
      <div className="tabs">
        <span className="active">
          <BookOpen size={16} />
          Course inventory
        </span>
        <Link
          to={`../competencies${revisionId ? `?revision=${revisionId}` : ""}`}
        >
          <Layers size={16} />
          Competency evidence
        </Link>
      </div>
      <Notice>
        Start here: choose a course to see its finding and next step. Titles
        alone cannot confirm what is taught.
      </Notice>
      {result.data?.findings.length ? (
        <Card title="What this review means">
          <p>
            {result.data.findings.length} courses reviewed. Open a course for
            the main finding; supporting checks and sources are inside.
          </p>
          <p className="muted">
            Missing evidence means “check the syllabus”, not “remove the
            course”. Academic staff decide any changes.
          </p>
        </Card>
      ) : null}
      <div className="year-grid">
        <button
          className={`year-panel ${year === "all" ? "selected" : ""}`}
          onClick={() => setYear("all")}
          aria-pressed={year === "all"}
        >
          <span className="eyebrow">Complete inventory</span>
          <strong>All recorded courses</strong>
          <small>
            {courses.length} courses <ArrowUpRight size={15} />
          </small>
        </button>
        {years.map((value, i) => (
          <button
            key={String(value)}
            className={`year-panel year-${i % 3} ${year === String(value) ? "selected" : ""}`}
            aria-pressed={year === String(value)}
            onClick={() => setYear(String(value))}
          >
            <span className="eyebrow">
              {value === null ? "Year not recorded" : `Year ${value}`}
            </span>
            <span className="year-number" aria-hidden="true">
              {value === null ? "?" : String(value).padStart(2, "0")}
            </span>
            <strong>
              {value === null
                ? "Confirm the sequence"
                : "Explore documented courses"}
            </strong>
            <small>
              {courses.filter((row) => row.year === value).length} courses
              <ArrowUpRight size={15} />
            </small>
          </button>
        ))}
      </div>
      <GenerateReview key={revisionId} courseCount={courses.length} />
      <div className="analysis-toolbar">
        <div>
          <h2>Course intelligence</h2>
          <p className="muted">
            Actual background jobs; offline submissions make no paid model
            request.
          </p>
        </div>
        {access.permissions.includes("write") && (
          <button
            className="button secondary"
            disabled={busy || !revisionId}
            onClick={async () => {
              if (!revisionId) return;
              setBusy(true);
              setMutationError(null);
              try {
                const row = await api.post<Analysis>(
                  `/api/v1/programmes/${programme.id}/analyses`,
                  "AnalysisRead",
                  {
                    revision_id: revisionId,
                    mode: "offline",
                    research: false,
                    idempotency_key: `ui-screening-${crypto.randomUUID()}`,
                  },
                );
                selectRun(row.id);
                history.reload();
              } catch (error) {
                setMutationError(error as ApiError);
              } finally {
                setBusy(false);
              }
            }}
          >
            <FileCheck2 size={16} />
            {busy ? "Submitting…" : "Queue offline course screening"}
          </button>
        )}
      </div>
      {mutationError && (
        <p className="form-error" role="alert">
          {mutationError.message}
        </p>
      )}
      {history.error && (
        <ErrorState error={history.error} retry={history.reload} />
      )}
      {rows.length > 0 && (
        <label className="history-picker">
          Screening version
          <select
            aria-label="Course screening version"
            value={runId || ""}
            onChange={(e) => selectRun(e.target.value)}
          >
            {requested && !rows.some((row) => row.id === requested) && (
              <option value={requested}>Selected historical run</option>
            )}
            {rows.map((row) => (
              <option key={row.id} value={row.id}>
                {dateLabel(row.created_at)} · {row.status} ·{" "}
                {row.id.slice(0, 8)}
              </option>
            ))}
          </select>
        </label>
      )}
      {history.data && history.data.total > 10 && (
        <div className="pagination">
          <button
            className="button secondary"
            disabled={historyOffset === 0}
            onClick={() => setHistoryOffset(Math.max(0, historyOffset - 10))}
          >
            Newer screenings
          </button>
          <button
            className="button secondary"
            disabled={historyOffset + 10 >= history.data.total}
            onClick={() => setHistoryOffset(historyOffset + 10)}
          >
            Older screenings
          </button>
        </div>
      )}
      {result.error && (
        <ErrorState error={result.error} retry={result.reload} />
      )}
      {run && (
        <div className="result-strip">
          <Status value={run.status} />
          <span>{run.model_name || "Model not used / not recorded"}</span>
          <Badge>
            {run.mode === "offline"
              ? "Offline execution"
              : run.model_name?.includes("mock")
                ? "Mocked model"
                : "Stored model execution"}
          </Badge>
        </div>
      )}
      {run && isPending(run.status) && (
        <Notice>
          Job {run.status.toLowerCase()}. Awaiting the actual worker result;
          worker availability is not established by queue status. No completion
          is assumed.
        </Notice>
      )}
      {run?.status === "FAILED" && (
        <Notice tone="caution">
          Screening failed. No successful analysis is displayed. Safe status:{" "}
          {run.error || "Failure reason not available"}.
        </Notice>
      )}
      {run?.needs_evidence_revalidation &&
        !isPending(run.status) &&
        run.status !== "FAILED" && (
          <Notice tone="caution">
            Evidence needs revalidation. Source-derived findings are withheld.
          </Notice>
        )}
      {!runId && !history.loading && (
        <Notice>
          No course screening is recorded for this revision. The inventory
          remains available.
        </Notice>
      )}
      <div className="list-toolbar">
        <h2>
          {year === "all"
            ? "Your recorded courses"
            : year === "null"
              ? "Courses without a recorded year"
              : `Year ${year} in focus`}
        </h2>
        <label className="search-field">
          <Search size={16} />
          <span className="sr-only">Find a course</span>
          <input
            type="search"
            placeholder="Find a course…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>
      {!filtered.length && (
        <Empty
          title={
            courses.length
              ? "No courses match this view"
              : "No courses imported yet"
          }
        >
          <Link to="../upload">Upload or import a curriculum</Link>
        </Empty>
      )}
      <div className="course-timeline">
        <div className="course-grid">
          {filtered.map((course) => {
            const finding = result.data?.findings.find(
              (row) => row.course_id === course.id,
            );
            return (
              <details key={course.id} className="course-card">
                <summary>
                  <span className="course-top">
                    <span className="course-book">
                      <BookOpen size={18} />
                    </span>
                    <small>
                      {humanise(course.course_type)} ·{" "}
                      {course.credit_hours === null
                        ? "Credits unknown"
                        : `${course.credit_hours} credits`}
                    </small>
                    <ArrowUpRight size={16} />
                  </span>
                  <h3>{course.course_name}</h3>
                  <span className="course-labels">
                    <Badge>
                      {course.year === null
                        ? "Year unknown"
                        : `Year ${course.year}`}
                    </Badge>
                    <Badge>
                      {course.semester === null
                        ? "Semester unknown"
                        : `Semester ${course.semester}`}
                    </Badge>
                  </span>
                  <span className="course-confirm">
                    {course.detailed_syllabus_available
                      ? "Inspect documented competency evidence"
                      : "Needs syllabus confirmation"}
                  </span>
                </summary>
                <div className="course-detail">
                  <dl className="detail-list">
                    <dt>Course code</dt>
                    <dd>{course.course_code || "Not documented"}</dd>
                    <dt>Extraction state</dt>
                    <dd>{humanise(course.extraction_status)}</dd>
                    <dt>Source locator</dt>
                    <dd>{course.source_locator || "Not supplied"}</dd>
                    <dt>Elective group</dt>
                    <dd>{course.elective_group || "Not recorded"}</dd>
                  </dl>
                  {safeUrl(course.source_url) && (
                    <a
                      className="text-link"
                      href={safeUrl(course.source_url)!}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      View course origin
                      <ArrowUpRight size={14} />
                    </a>
                  )}
                  <Notice>
                    Learning outcomes cannot be inferred from this title.
                    Inspect admitted curriculum passages in competency evidence.
                  </Notice>
                  <TextList
                    items={course.review_notes}
                    empty="No additional extraction review notes recorded."
                  />
                  {finding ? (
                    <>
                      <h4>Preliminary course findings</h4>
                      <Status value={finding.review_flag} />
                      <p>
                        {finding.review_flag === "insufficient_evidence"
                          ? "Next step: add or review syllabus evidence before deciding on changes."
                          : "Next step: review the supporting evidence with academic staff."}
                      </p>
                      <details>
                        <summary>Supporting checks and sources</summary>
                        {dimensions.map((key) => (
                          <section key={key} className="dimension">
                            <h4>{humanise(key)}</h4>
                            <Status value={finding[key].status} />
                            <TextList
                              items={(finding[key].review_questions || []).map(
                                humanise,
                              )}
                              empty="No further question recorded in this dimension."
                            />
                            <Citations
                              citations={finding[key].citations}
                              evidencePath={`/api/v1/analyses/${run?.id}`}
                            />
                          </section>
                        ))}
                      </details>
                    </>
                  ) : (
                    <p className="muted">
                      No currently validated finding is displayed for this
                      course.
                    </p>
                  )}
                  <Link
                    className="section-link"
                    to={`../competencies${revisionId ? `?revision=${revisionId}` : ""}`}
                  >
                    Open competency evidence
                    <ArrowUpRight size={14} />
                  </Link>
                </div>
              </details>
            );
          })}
        </div>
      </div>
      <Card
        eyebrow="A considered next step"
        title="Review evidence before changing a course"
      >
        <p>
          Partial coverage calls for investigation. Related occupation signals
          do not make a course obsolete. Keep alternatives and the no-change
          option visible.
        </p>
        <Link
          className="button secondary"
          to={`../recommendations${revisionId ? `?revision=${revisionId}` : ""}`}
        >
          Explore academic recommendations
          <ArrowUpRight size={16} />
        </Link>
      </Card>
    </>
  );
}
