import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, FileCheck2, FileText, UploadCloud } from "lucide-react";
import { useWorkspace } from "../app/workspace";
import { ApiError, validateResponse } from "../api/client";
import { humanise, isPending, type Course, type Model } from "../api/types";
import { useResource } from "../lib/resource";
import {
  Badge,
  Card,
  Empty,
  ErrorState,
  Loading,
  Notice,
  PageHeading,
  Status,
} from "../components/ui";

export function validatePdf(file: File) {
  if (
    !file.name.toLowerCase().endsWith(".pdf") ||
    (file.type && file.type !== "application/pdf")
  )
    return "Choose a PDF curriculum or brochure.";
  if (file.size === 0 || file.size > 20_000_000)
    return "The PDF must contain data and be no larger than 20 MB.";
  return null;
}

export default function UploadPage() {
  const { api, access, programme, institution } = useWorkspace();
  const [params, setParams] = useSearchParams();
  const [file, setFile] = useState<File | null>(null);
  const [sourceUrl, setSourceUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [manifestText, setManifestText] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [tab, setTab] = useState<"pdf" | "json">("pdf");
  const jobId = params.get("job");
  const job = useResource(
    jobId ? `upload:${programme.id}:${jobId}` : null,
    (signal) =>
      api.get<Model<"JobRead">>(
        `/api/v1/catalogue/jobs/${jobId}`,
        "JobRead",
        signal,
      ),
    2000,
  );
  const entries =
    (job.data?.result?.entries as
      { programme_id?: string; revision_id?: string | null }[] | undefined) ||
    [];
  const revisionId = entries.find(
    (entry) => entry.programme_id === programme.id,
  )?.revision_id;
  const extracted = useResource(
    revisionId && !isPending(job.data?.status)
      ? `extracted:${programme.id}:${revisionId}`
      : null,
    (signal) =>
      api.all<Course>(
        `/api/v1/programmes/${programme.id}/revisions/${revisionId}/courses`,
        "CoursePage",
        signal,
      ),
  );
  const showJob = (id: string) => {
    const next = new URLSearchParams(params);
    next.set("job", id);
    setParams(next);
  };
  if (!access.permissions.includes("write"))
    return (
      <>
        <PageHeading title="Curriculum upload" />
        <Empty title="Write permission is required">
          Your current operator grant can inspect records but cannot submit
          imports.
        </Empty>
      </>
    );
  return (
    <>
      <PageHeading
        eyebrow="Upload, inspect, review"
        title="Bring your curriculum into focus"
      >
        Add a supported PDF or reviewed input. The worker will create a
        versioned inventory with traceable origins.
      </PageHeading>
      <Notice>
        Private originals remain in backend storage. Uploading does not send a
        document to an external AI service or certify extracted courses.
      </Notice>
      <div className="tabs" role="group" aria-label="Curriculum input type">
        <button
          className={tab === "pdf" ? "active" : ""}
          aria-pressed={tab === "pdf"}
          onClick={() => setTab("pdf")}
        >
          <FileText size={16} />
          PDF brochure
        </button>
        <button
          className={tab === "json" ? "active" : ""}
          aria-pressed={tab === "json"}
          onClick={() => setTab("json")}
        >
          <FileCheck2 size={16} />
          Reviewed input
        </button>
      </div>
      {tab === "pdf" ? (
        <Card title="Upload your curriculum PDF">
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (!file || busy) return;
              const invalid = validatePdf(file);
              if (invalid) {
                setError(invalid);
                return;
              }
              if (!programme.canonical_url || !institution.website_url) {
                setError(
                  "The institution website and official programme URL must be configured before an attributed PDF upload. Use reviewed input or ask your administrator to confirm the catalogue origins.",
                );
                return;
              }
              setBusy(true);
              setError("");
              try {
                if ((await file.slice(0, 5).text()) !== "%PDF-") {
                  setError(
                    "This file does not have a supported PDF signature.",
                  );
                  return;
                }
                const query = sourceUrl.trim()
                  ? `?source_url=${encodeURIComponent(sourceUrl.trim())}`
                  : "";
                const result = await api.upload<Model<"JobRead">>(
                  `/api/v1/programmes/${programme.id}/curriculum-pdf${query}`,
                  "JobRead",
                  file,
                );
                showJob(result.id);
              } catch (error) {
                setError(
                  error instanceof ApiError
                    ? error.message
                    : "The file could not be submitted. No successful upload is assumed.",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            <label className="upload-zone">
              <UploadCloud size={34} strokeWidth={1.3} aria-hidden="true" />
              <strong>Choose a curriculum or brochure</strong>
              <span>PDF · up to 20 MB · selectable text recommended</span>
              <input
                type="file"
                accept="application/pdf,.pdf"
                aria-label="Curriculum PDF"
                onChange={(e) => {
                  const value = e.target.files?.[0] || null;
                  setFile(value);
                  setError(value ? validatePdf(value) || "" : "");
                }}
              />
              {file && (
                <Badge>
                  {file.name} · {(file.size / 1_000_000).toFixed(2)} MB
                </Badge>
              )}
            </label>
            <label>
              Original document URL{" "}
              <span className="muted">
                (optional; official institution host only)
              </span>
              <input
                type="url"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                placeholder={programme.canonical_url || "Official source URL"}
              />
            </label>
            <p className="muted">
              Supported year-column PDFs can be extracted automatically. Scanned
              or ambiguous layouts may require reviewed JSON transcription.
              Unknown fields remain unknown.
            </p>
            <button
              className="button"
              disabled={busy || !file || Boolean(file && validatePdf(file))}
            >
              {busy ? "Submitting file…" : "Upload and queue extraction"}
              <ArrowRight size={16} />
            </button>
          </form>
        </Card>
      ) : (
        <Card title="Import a reviewed course inventory">
          <p>
            Load a programme import JSON with the original title excerpts and
            locators. Correct it against your own source document before
            confirming review. This creates an immutable revision; it does not
            silently approve existing records.
          </p>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (!reviewed || busy) return;
              setBusy(true);
              setError("");
              try {
                const value = JSON.parse(manifestText);
                if (
                  typeof value !== "object" ||
                  value === null ||
                  Array.isArray(value)
                )
                  throw new Error("FORMAT");
                if (
                  value.name !== programme.name ||
                  value.canonical_url !== programme.canonical_url
                ) {
                  setError(
                    "The reviewed input must use this programme’s exact name and official canonical URL.",
                  );
                  return;
                }
                const manifest = {
                  ...value,
                  reviewed: true,
                  is_synthetic: programme.is_synthetic,
                  idempotency_key: `ui-import-${crypto.randomUUID()}`,
                };
                validateResponse(manifest, "ProgrammeImport");
                const result = await api.post<Model<"JobRead">>(
                  `/api/v1/programmes/${programme.id}/imports`,
                  "JobRead",
                  manifest,
                );
                showJob(result.id);
              } catch (error) {
                setError(
                  error instanceof ApiError
                    ? error.message
                    : "The JSON format is invalid. Include the documented programme fields, courses, source locators and exact title excerpts.",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            <label>
              Load reviewed JSON file
              <input
                type="file"
                accept="application/json,.json"
                onChange={async (e) => {
                  const value = e.target.files?.[0];
                  if (!value) return;
                  if (value.size > 1_048_576) {
                    setError("Reviewed JSON must be no larger than 1 MiB.");
                    return;
                  }
                  setManifestText(await value.text());
                  setReviewed(false);
                  setError("");
                }}
              />
            </label>
            <label>
              Programme import JSON
              <textarea
                rows={14}
                value={manifestText}
                onChange={(e) => {
                  setManifestText(e.target.value);
                  setReviewed(false);
                }}
                spellCheck={false}
                maxLength={1_048_576}
                aria-describedby="manifest-help"
              />
            </label>
            <p id="manifest-help" className="muted">
              Required: name, canonical_url, source_url, source_locator,
              retrieved_at and courses. Each course needs course_name,
              source_locator and a matching source_excerpt. Year and semester
              may remain absent.
            </p>
            <label className="checkbox-label">
              <input
                type="checkbox"
                required
                checked={reviewed}
                onChange={(e) => setReviewed(e.target.checked)}
              />
              I reviewed these course titles and source excerpts against the
              original document.
            </label>
            <button
              className="button"
              disabled={busy || !reviewed || !manifestText.trim()}
            >
              {busy ? "Submitting…" : "Queue reviewed curriculum import"}
              <ArrowRight size={16} />
            </button>
          </form>
        </Card>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {job.loading && <Loading label="Checking extraction job" />}
      {job.error && <ErrorState error={job.error} retry={job.reload} />}
      {job.data && (
        <Card title="Extraction &amp; import status">
          <div className="result-strip">
            <Status value={job.data.status} />
            <small>Job {job.data.id}</small>
          </div>
          {isPending(job.data.status) ? (
            <Notice>
              The job is {job.data.status.toLowerCase()}. A running worker is
              required. Queue status does not prove worker availability; no
              extraction success is assumed.
            </Notice>
          ) : job.data.status === "FAILED" ? (
            <Notice tone="caution">
              The worker reported a failure:{" "}
              {job.data.error || "No additional safe diagnostic available"}.
              Review the file/layout or use reviewed input. This button does not
              automatically retry a failed job.
            </Notice>
          ) : (
            <Notice>
              The worker has finished. Inspect the actual extracted records and
              their unresolved fields before analysis.
            </Notice>
          )}
          {job.data.is_synthetic && <Badge>Synthetic input</Badge>}
          {revisionId && (
            <Link
              className="button secondary"
              to={`../courses?revision=${revisionId}`}
            >
              Inspect this extracted revision
              <ArrowRight size={16} />
            </Link>
          )}
        </Card>
      )}
      {extracted.loading && (
        <Loading label="Retrieving committed course records" />
      )}
      {extracted.error && (
        <ErrorState error={extracted.error} retry={extracted.reload} />
      )}
      {extracted.data && (
        <Card title="Review extracted courses">
          <Notice>
            Extraction flags are not academic verification. Supported
            corrections use reviewed input and create a new revision; there is
            no blanket “approve extraction” action.
          </Notice>
          <div className="table-scroll">
            <table className="data-table">
              <caption>Committed courses from this import</caption>
              <thead>
                <tr>
                  <th scope="col">Course</th>
                  <th scope="col">Year / semester</th>
                  <th scope="col">Classification</th>
                  <th scope="col">Review required</th>
                  <th scope="col">Origin</th>
                </tr>
              </thead>
              <tbody>
                {extracted.data.map((row) => (
                  <tr key={row.id}>
                    <td>{row.course_name}</td>
                    <td>
                      {row.year ?? "Unknown"} / {row.semester ?? "Unknown"}
                    </td>
                    <td>{humanise(row.course_type)}</td>
                    <td>
                      {humanise(row.extraction_status)}
                      <ul>
                        {row.missing_fields.map((value) => (
                          <li key={value}>{humanise(value)} missing</li>
                        ))}
                      </ul>
                    </td>
                    <td>{row.source_locator || "Not supplied"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="button secondary" onClick={() => setTab("json")}>
            Review corrections through structured input
          </button>
        </Card>
      )}
    </>
  );
}
