import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, X } from "lucide-react";
import { ApiError } from "../api/client";
import { useSession } from "../app/session";
import { createPublicUploadWorkspace } from "../lib/public-upload-session";
import { Card } from "./ui";

export default function PublicUploadEntry() {
  const { publicUploadsEnabled, refreshAccess } = useSession();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [institution, setInstitution] = useState("");
  const [programme, setProgramme] = useState("");
  const [programmeUrl, setProgrammeUrl] = useState("");
  const [permitted, setPermitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  if (!publicUploadsEnabled || !refreshAccess) return null;
  return (
    <Card className="sample-programme-card">
      <button className="button secondary" onClick={() => setOpen(true)}>
        Try your own PDF <ArrowUpRight size={16} aria-hidden="true" />
      </button>
      {open && (
        <dialog
          className="form-dialog"
          aria-labelledby="public-upload-title"
          ref={(element) => {
            if (element && !element.open) element.showModal();
          }}
          onCancel={(event) => {
            if (busy) event.preventDefault();
            else setOpen(false);
          }}
        >
          <header className="dialog-header">
            <h2 id="public-upload-title">Try your own PDF</h2>
            <button
              className="icon-button"
              aria-label="Close upload workspace"
              disabled={busy}
              onClick={() => setOpen(false)}
            >
              <X />
            </button>
          </header>
          <p>
            Use a public brochure. Uploads are temporary, private to this
            session and do not trigger paid AI.
          </p>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              if (busy || !permitted) return;
              let url: URL;
              try {
                url = new URL(programmeUrl.trim());
                if (
                  url.protocol !== "https:" ||
                  url.username ||
                  url.password ||
                  (url.port && url.port !== "443")
                )
                  throw new Error();
              } catch {
                setError(
                  "Enter the official HTTPS programme page for this public brochure.",
                );
                return;
              }
              const request = new AbortController();
              controller.current = request;
              setBusy(true);
              setError("");
              try {
                const workspace = await createPublicUploadWorkspace(
                  {
                    institution_name: institution.trim(),
                    institution_url: url.origin,
                    programme_name: programme.trim(),
                    programme_url: url.href,
                    permitted_public_document: true,
                  },
                  request.signal,
                );
                const access = await refreshAccess(workspace.institution_id);
                if (
                  !access.permissions.includes("write") ||
                  !access.permissions.includes("read") ||
                  access.permissions.some(
                    (permission) => !["read", "write"].includes(permission),
                  ) ||
                  !access.institution_ids.includes(workspace.institution_id) ||
                  access.global_admin
                )
                  throw new ApiError("FORBIDDEN");
                if (!request.signal.aborted)
                  navigate(`/programmes/${workspace.programme_id}/upload`);
              } catch (failure) {
                if (request.signal.aborted) return;
                setError(
                  failure instanceof ApiError &&
                    failure.code === "PUBLIC_UPLOAD_LIMIT"
                    ? "The temporary upload limit has been reached. Please try again later."
                    : failure instanceof ApiError && failure.code === "TIMEOUT"
                      ? "Workspace creation timed out. Reload to check the session before trying again."
                      : "The temporary workspace could not be opened. Check the public programme details and try again.",
                );
              } finally {
                if (!request.signal.aborted) setBusy(false);
              }
            }}
          >
            <label>
              Programme name
              <input
                required
                maxLength={255}
                value={programme}
                onChange={(event) => setProgramme(event.target.value)}
              />
            </label>
            <label>
              Institution name
              <input
                required
                maxLength={255}
                value={institution}
                onChange={(event) => setInstitution(event.target.value)}
              />
            </label>
            <label>
              Official programme page
              <input
                type="url"
                required
                value={programmeUrl}
                onChange={(event) => setProgrammeUrl(event.target.value)}
                placeholder="https://university.example/programme"
                maxLength={2048}
              />
            </label>
            <label className="checkbox-label">
              <input
                type="checkbox"
                required
                checked={permitted}
                onChange={(event) => setPermitted(event.target.checked)}
              />
              I may upload this public brochure; it contains no private or
              personal data.
            </label>
            {error && (
              <p role="alert" className="form-error">
                {error}
              </p>
            )}
            <button
              className="button"
              disabled={
                busy ||
                !permitted ||
                !programme.trim() ||
                !institution.trim() ||
                !programmeUrl.trim()
              }
            >
              {busy ? "Opening workspace…" : "Continue to PDF upload"}
            </button>
          </form>
        </dialog>
      )}
    </Card>
  );
}
