import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ExternalLink, X } from "lucide-react";
import { ApiClient, ApiError, validateResponse } from "../api/client";
import type { Evidence, Model } from "../api/types";
import { dateLabel, humanise } from "../api/types";
import { useResource } from "../lib/resource";

const EvidenceContext = createContext<{
  openEvidence: (path: string, referenceId?: string) => void;
}>({ openEvidence: () => {} });
export const useEvidence = () => useContext(EvidenceContext);
export function safeUrl(url?: string | null) {
  if (!url) return null;
  try {
    const value = new URL(url);
    return ["https:", "http:"].includes(value.protocol) &&
      !value.username &&
      !value.password
      ? value.href
      : null;
  } catch {
    return null;
  }
}

function EvidenceContent({
  api,
  path,
  referenceId,
}: {
  api: ApiClient;
  path: string;
  referenceId?: string;
}) {
  const result = useResource(
    `${path}:${referenceId || "all"}`,
    async (signal) => {
      if (/^\/api\/v1\/analyses\/[a-f\d-]+$/.test(path)) {
        const run = await api.get<Model<"AnalysisRead">>(
          path,
          "AnalysisRead",
          signal,
        );
        if (run.needs_evidence_revalidation)
          throw new ApiError("EVIDENCE_WITHHELD");
        const packet = run.manifest_json?.packet as
          { references?: unknown[] } | undefined;
        return (packet?.references || []).map((item) =>
          validateResponse<Evidence>(item, "EvidenceItem"),
        );
      }
      return api.all<Evidence>(
        path,
        path.includes("/action-plans/")
          ? "PlanSection_EvidenceItem_"
          : "EvidencePage",
        signal,
      );
    },
  );
  if (result.loading) return <p role="status">Revalidating source access…</p>;
  if (result.error)
    return (
      <div role="alert">
        <h3>Evidence unavailable or withheld</h3>
        <p>
          No cached excerpt is displayed. Source access must be revalidated
          before use.
        </p>
        <button className="button secondary" onClick={result.reload}>
          Revalidate evidence
        </button>
      </div>
    );
  const rows = referenceId
    ? result.data?.filter((row) => row.id === referenceId)
    : result.data;
  if (!rows?.length)
    return (
      <p>
        No currently eligible source matches this citation. Treat it as
        unavailable.
      </p>
    );
  return (
    <div className="evidence-list">
      {rows.map((row) => (
        <article key={row.id} className="evidence-record">
          <p className="eyebrow">
            {row.is_synthetic
              ? "Synthetic demonstration source"
              : row.evidence_class.replaceAll("_", " ")}
          </p>
          <h3>{row.title}</h3>
          <p>{row.publisher}</p>
          <dl className="detail-list">
            <dt>Reference</dt>
            <dd>{row.id}</dd>
            <dt>Version</dt>
            <dd>{row.version_id || "Not supplied"}</dd>
            <dt>Evidence class</dt>
            <dd>{humanise(row.evidence_class)}</dd>
            <dt>Applicable scope</dt>
            <dd>{humanise(row.scope)}</dd>
            {typeof row.facts?.geography === "string" &&
              row.facts.geography && (
                <>
                  <dt>Geography</dt>
                  <dd>{row.facts.geography}</dd>
                </>
              )}
            {row.language && (
              <>
                <dt>Language</dt>
                <dd>{row.language}</dd>
              </>
            )}
            <dt>Publication date</dt>
            <dd>
              {row.publication_date || "Not recorded"} ({row.date_precision})
            </dd>
            <dt>Observation period</dt>
            <dd>
              {[row.observation_start, row.observation_end]
                .filter(Boolean)
                .join(" to ") || "Not recorded"}
            </dd>
            {row.study_period && (
              <>
                <dt>Study period</dt>
                <dd>{row.study_period}</dd>
              </>
            )}
            {row.model_version && (
              <>
                <dt>Study model/version</dt>
                <dd>{row.model_version}</dd>
              </>
            )}
            {row.retrieved_at && (
              <>
                <dt>Retrieved</dt>
                <dd>{dateLabel(row.retrieved_at)}</dd>
              </>
            )}
            <dt>Locator</dt>
            <dd>{row.locator}</dd>
            <dt>Review state</dt>
            <dd>{row.review_status}</dd>
          </dl>
          {safeUrl(row.source_url) && (
            <a
              className="text-link"
              href={safeUrl(row.source_url)!}
              target="_blank"
              rel="noopener noreferrer"
            >
              Open original source
              <ExternalLink size={14} aria-hidden="true" />
            </a>
          )}
          {row.rights.excerpt_output_allowed === true &&
          row.internal_eligible &&
          row.excerpt ? (
            <blockquote>{row.excerpt}</blockquote>
          ) : (
            <p className="notice">
              Excerpt withheld or unavailable under the current source
              permissions.
            </p>
          )}
          {(row.limitations || []).length > 0 && (
            <ul className="text-list">
              {row.limitations?.map((value, index) => (
                <li key={index}>{value}</li>
              ))}
            </ul>
          )}
        </article>
      ))}
    </div>
  );
}

export function EvidenceProvider({
  api,
  children,
}: {
  api: ApiClient;
  children: ReactNode;
}) {
  const [target, setTarget] = useState<{
    path: string;
    referenceId?: string;
  } | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const close = () => setTarget(null);
  useEffect(() => {
    if (target && !dialog.current?.open) dialog.current?.showModal();
    if (!target && dialog.current?.open) dialog.current.close();
  }, [target]);
  return (
    <EvidenceContext.Provider
      value={{
        openEvidence: (path, referenceId) => setTarget({ path, referenceId }),
      }}
    >
      {children}
      <dialog
        ref={dialog}
        className="evidence-dialog"
        aria-labelledby="evidence-title"
        onCancel={close}
        onClose={close}
      >
        <header className="dialog-header">
          <div>
            <p className="eyebrow">Source provenance</p>
            <h2 id="evidence-title">Evidence &amp; limitations</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close evidence"
            onClick={close}
          >
            <X />
          </button>
        </header>
        <p className="notice">
          Permissions are checked again when you open this viewer. Benchmarks do
          not establish what a university teaches.
        </p>
        {target && (
          <EvidenceContent
            key={`${target.path}:${target.referenceId}`}
            api={api}
            {...target}
          />
        )}
      </dialog>
    </EvidenceContext.Provider>
  );
}
