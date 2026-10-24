import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";
import { useSession } from "../app/session";
import type {
  CareerRun,
  Institution,
  Model,
  PlanRun,
  Programme,
} from "../api/types";
import { byCreatedAt, safeCareerResult, safePlanResult } from "../lib/results";
import { useResource } from "../lib/resource";
import { Card, ErrorState, Loading } from "./ui";

type Coverage = Model<"CoverageRead">;

/** A sample is an existing, permission-checked result, never a client-side fixture. */
export default function SampleProgrammeEntry({
  programmes,
  institutions,
  coverage,
}: {
  programmes: Programme[];
  institutions: Institution[];
  coverage: Map<string, Coverage | null>;
}) {
  const { api } = useSession();
  const candidates = programmes.filter((programme) => {
    const institution = institutions.find(
      (row) => row.id === programme.institution_id,
    );
    const inventory = coverage.get(programme.id);
    return (
      programme.is_synthetic &&
      institution?.is_synthetic &&
      programme.active_revision_id &&
      programme.active_revision?.is_synthetic &&
      programme.active_revision.programme_id === programme.id &&
      programme.active_revision.id === programme.active_revision_id &&
      inventory?.is_synthetic &&
      inventory.programme_id === programme.id &&
      inventory.programme_revision_id === programme.active_revision_id &&
      inventory.course_count > 0
    );
  });
  const key = `sample-programme:${candidates
    .map(
      (row) =>
        `${row.id}:${row.active_revision_id}:${coverage.get(row.id)?.course_count}`,
    )
    .join(",")}`;
  const sample = useResource(key, async (signal) => {
    for (const programme of candidates) {
      const revision = programme.active_revision_id!;
      const careers = byCreatedAt(
        await api.all<CareerRun>(
          `/api/v1/programmes/${programme.id}/career-analyses`,
          "Page_CareerRead_",
          signal,
        ),
      );
      for (const career of careers) {
        if (
          !career.is_synthetic ||
          career.institution_id !== programme.institution_id ||
          career.programme_id !== programme.id ||
          career.programme_revision_id !== revision
        )
          continue;
        const careerResult = safeCareerResult(career, programme.id, revision);
        if (
          !career.completed_at ||
          !careerResult ||
          careerResult.course_ids.length !==
            coverage.get(programme.id)?.course_count ||
          new Set(careerResult.course_ids).size !==
            coverage.get(programme.id)?.course_count
        )
          continue;
        const plans = byCreatedAt(
          await api.all<PlanRun>(
            `/api/v1/career-analyses/${career.id}/action-plans`,
            "Page_PlanRead_",
            signal,
          ),
        );
        for (const plan of plans) {
          if (
            !plan.is_synthetic ||
            plan.institution_id !== programme.institution_id
          )
            continue;
          const result = safePlanResult(plan, career, programme.id, revision);
          if (
            !plan.completed_at ||
            !result ||
            result.overview.institution_id !== programme.institution_id ||
            result.overview.programme_id !== programme.id ||
            result.overview.programme_revision_id !== revision ||
            result.overview.course_ids.length !==
              careerResult.course_ids.length ||
            new Set(result.overview.course_ids).size !==
              careerResult.course_ids.length ||
            !result.overview.course_ids.every((id) =>
              careerResult.course_ids.includes(id),
            )
          )
            continue;
          const params = new URLSearchParams({
            revision,
            career: career.id,
            plan: plan.id,
          });
          return {
            name: programme.name,
            to: `/programmes/${programme.id}/overview?${params}`,
          };
        }
      }
    }
    return null;
  });
  return (
    <Card title="Explore before you upload" className="sample-programme-card">
      <p className="eyebrow">Demo data — fictional example.</p>
      <p>
        Explore a fictional programme, its stored analysis and Academic Action
        Plan. No PDF or new AI generation is needed. Evidence limitations remain
        visible throughout the workspace.
      </p>
      {sample.loading ? (
        <Loading label="Checking the prepared sample programme" />
      ) : sample.error ? (
        <ErrorState error={sample.error} retry={sample.reload} />
      ) : sample.data ? (
        <>
          <p className="muted">Prepared sample: {sample.data.name}</p>
          <Link className="button" to={sample.data.to}>
            Explore Sample Programme
            <ArrowUpRight size={16} aria-hidden="true" />
          </Link>
        </>
      ) : (
        <p role="status">
          No prepared sample programme is available in your authorised
          workspace. Ask the development administrator to load the demo through
          the supported backend workflow. No sample has been invented.
        </p>
      )}
    </Card>
  );
}
