import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, LoaderCircle } from "lucide-react";
import { ApiError } from "../api/client";
import type { Model } from "../api/types";
import { useWorkspace } from "../app/workspace";
import { prepareReview } from "../lib/prepare-review";
import { Card } from "./ui";

/** One visible entry into the existing, non-billable assessment jobs. */
export default function GenerateReview({
  revisionId: selectedRevision,
  courseCount,
  careerId,
}: {
  revisionId?: string | null;
  courseCount?: number;
  careerId?: string;
}) {
  const { api, access, programme, revisionId } = useWorkspace();
  const selected = selectedRevision || revisionId;
  const scope = `${programme.id}:${selected}:${careerId || ""}`;
  const navigate = useNavigate();
  const controller = useRef<AbortController | null>(null);
  const attempt = useRef({ scope, key: `ui-review-${crypto.randomUUID()}` });
  const current = useRef(scope);
  current.current = scope;
  const [state, setState] = useState({
    scope,
    busy: false,
    progress: "",
    error: "",
  });
  useEffect(() => {
    const stop = () => {
      if (document.hidden) controller.current?.abort();
    };
    document.addEventListener("visibilitychange", stop);
    return () => {
      controller.current?.abort();
      document.removeEventListener("visibilitychange", stop);
    };
  }, [scope]);
  if (!selected || courseCount === 0 || !access.permissions.includes("write"))
    return null;
  const visible = state.scope === scope ? state : null;
  const busy = Boolean(visible?.busy);
  return (
    <Card title="Get results from your courses" className="generation-panel">
      <p>
        Uploading extracts the course list. Generate a preliminary review for
        course findings and suggested next steps. An action plan is prepared
        where the evidence allows.
      </p>
      <p className="muted">
        Uses saved evidence, with no paid AI or search calls. Missing evidence
        is shown explicitly; course titles do not prove taught content.
      </p>
      <button
        className="button"
        disabled={busy}
        onClick={async () => {
          if (controller.current && !controller.current.signal.aborted && busy)
            return;
          if (attempt.current.scope !== scope)
            attempt.current = {
              scope,
              key: `ui-review-${crypto.randomUUID()}`,
            };
          const request = new AbortController();
          controller.current = request;
          setState({
            scope,
            busy: true,
            progress: "Checking saved courses…",
            error: "",
          });
          try {
            const coverage = await api.get<Model<"CoverageRead">>(
              `/api/v1/programmes/${programme.id}/coverage?revision_id=${selected}`,
              "CoverageRead",
              request.signal,
            );
            if (
              coverage.programme_id !== programme.id ||
              coverage.programme_revision_id !== selected
            )
              throw new ApiError("INVALID_RESPONSE");
            if (!coverage.course_count) {
              setState({
                scope,
                busy: false,
                progress: "",
                error:
                  "This revision has no extracted courses. Upload a course list first.",
              });
              return;
            }
            const result = await prepareReview(api, programme.id, selected, {
              key: attempt.current.key,
              signal: request.signal,
              careerId,
              onProgress: (progress) => {
                if (current.current === scope && !request.signal.aborted)
                  setState({ scope, busy: true, progress, error: "" });
              },
            });
            if (current.current !== scope || request.signal.aborted) return;
            const params = new URLSearchParams({
              revision: selected,
              analysis: result.analysisId,
              career: result.careerId,
            });
            if (result.planId) params.set("plan", result.planId);
            navigate(`/programmes/${programme.id}/recommendations?${params}`);
          } catch (failure) {
            if (current.current !== scope) return;
            setState({
              scope,
              busy: false,
              progress: "",
              error: request.signal.aborted
                ? "Review paused. Choose Check progress to continue from saved jobs."
                : failure instanceof ApiError
                  ? failure.message
                  : "Review could not finish. Check progress before submitting again.",
            });
          }
        }}
      >
        {busy ? (
          <LoaderCircle size={16} className="spin" />
        ) : (
          <ArrowRight size={16} />
        )}
        {busy
          ? "Generating results…"
          : visible?.error
            ? "Check progress"
            : "Generate results"}
      </button>
      {busy && <p role="status">{visible?.progress}</p>}
      {visible?.error && (
        <p className="form-error" role="alert">
          {visible.error}
        </p>
      )}
    </Card>
  );
}
