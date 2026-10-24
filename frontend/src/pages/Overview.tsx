import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  BookOpen,
  FileCheck2,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { useWorkspace } from "../app/workspace";
import { useResource } from "../lib/resource";
import type { Model, Page, CareerRun } from "../api/types";
import {
  Badge,
  Card,
  ErrorState,
  Loading,
  Notice,
  PageHeading,
  Status,
} from "../components/ui";

export default function Overview() {
  const { api, programme, institution, revisionId, access } = useWorkspace();
  const data = useResource(
    `overview:${programme.id}:${revisionId}`,
    async (signal) => {
      const [coverage, analyses, careers] = await Promise.all([
        api.get<Model<"CoverageRead">>(
          `/api/v1/programmes/${programme.id}/coverage${revisionId ? `?revision_id=${revisionId}` : ""}`,
          "CoverageRead",
          signal,
        ),
        api.get<Page<Model<"AnalysisRead">>>(
          `/api/v1/programmes/${programme.id}/analyses?limit=10`,
          "Page_AnalysisRead_",
          signal,
        ),
        api.get<Page<CareerRun>>(
          `/api/v1/programmes/${programme.id}/career-analyses?limit=10`,
          "Page_CareerRead_",
          signal,
        ),
      ]);
      return {
        coverage,
        analyses: analyses.items.filter(
          (row) => row.programme_revision_id === revisionId,
        ),
        careers: careers.items.filter(
          (row) => row.programme_revision_id === revisionId,
        ),
      };
    },
  );
  if (data.loading) return <Loading />;
  if (data.error) return <ErrorState error={data.error} retry={data.reload} />;
  if (!data.data) return null;
  const { coverage, analyses, careers } = data.data;
  const suffix = revisionId ? `?revision=${revisionId}` : "";
  return (
    <>
      <PageHeading
        eyebrow={institution.name}
        title="A clearer view of your curriculum"
        actions={
          access.permissions.includes("write") && (
            <Link className="button secondary" to={`../upload${suffix}`}>
              <Upload size={16} />
              Upload curriculum
            </Link>
          )
        }
      >
        Begin with your recorded courses, understand the evidence, and review
        what needs attention.
      </PageHeading>
      <section className="context-hero">
        <div>
          <p className="eyebrow">Programme intelligence</p>
          <h2>{programme.name}</h2>
          <p>
            {programme.is_synthetic
              ? "A fictional programme used to demonstrate the complete academic review workflow."
              : "A versioned programme workspace. Findings remain bounded by the documents and evidence actually admitted."}
          </p>
          <Link className="text-link" to={`../courses${suffix}`}>
            Explore the learning journey
            <ArrowUpRight size={16} />
          </Link>
        </div>
        <div className="hero-glyph" aria-hidden="true">
          <BookOpen size={40} />
          <span>Evidence</span>
          <span>Review</span>
        </div>
      </section>
      <div className="overview-counts">
        <div>
          <strong>{coverage.course_count}</strong>
          <span>Recorded courses</span>
        </div>
        <div>
          <strong>{coverage.title_only_count}</strong>
          <span>Title-only records</span>
        </div>
        <div>
          <strong>{coverage.needs_review_count}</strong>
          <span>Extraction records needing review</span>
        </div>
      </div>
      <Notice>
        These counts describe available records and evidence. They do not
        measure programme quality or certify a complete graduation curriculum.
      </Notice>
      <div className="card-grid">
        <Card eyebrow="Evidence first" title="Know what is documented">
          <p>
            {coverage.verified_title_count} verified catalogue title(s). A
            verified title does not establish learning outcomes, assessment or
            actual teaching content.
          </p>
          <Link className="section-link" to={`../evidence${suffix}`}>
            Inspect admitted sources
            <ShieldCheck size={16} />
          </Link>
        </Card>
        <Card
          eyebrow="Your next review"
          title="From findings to considered action"
        >
          <p>
            Inspect related occupations, distinguish supported competencies from
            unknowns, then compare academic interventions with the no-change
            option.
          </p>
          <Link className="section-link" to={`../careers${suffix}`}>
            Explore career alignment
            <ArrowUpRight size={16} />
          </Link>
        </Card>
      </div>
      <Card title="Recent analysis for this revision">
        <div className="analysis-list">
          <div>
            <FileCheck2 size={20} />
            <div>
              <h3>Course intelligence</h3>
              <p>
                {analyses.length
                  ? "Recent stored screening runs for the selected revision."
                  : "No screening result is recorded for this revision in the recent history."}
              </p>
            </div>
            {analyses[0] ? (
              <>
                <Status value={analyses[0].status} />
                {analyses[0].needs_evidence_revalidation &&
                  !["QUEUED", "RUNNING"].includes(analyses[0].status) && (
                    <Badge tone="caution">Needs revalidation</Badge>
                  )}
              </>
            ) : (
              <Badge>Not run</Badge>
            )}
            <Link className="text-link" to={`../courses${suffix}`}>
              Open
            </Link>
          </div>
          <div>
            <ShieldCheck size={20} />
            <div>
              <h3>Career alignment &amp; action planning</h3>
              <p>
                {careers.length
                  ? "Review the evidence, proposals and version-bound operator decisions."
                  : "Reviewed mappings and curriculum evidence are needed for supported alignment."}
              </p>
            </div>
            {careers[0] ? (
              <Status value={careers[0].status} />
            ) : (
              <Badge>Not run</Badge>
            )}
            <Link className="text-link" to={`../plan${suffix}`}>
              Open plan
            </Link>
          </div>
        </div>
      </Card>
      {programme.is_synthetic && (
        <Notice>
          Synthetic inputs and mocked model output demonstrate software
          behaviour. They are not findings about XMUM or another real
          university.
        </Notice>
      )}
    </>
  );
}
