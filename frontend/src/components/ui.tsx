import { useState, type ReactNode } from "react";
import {
  AlertCircle,
  ArrowUpRight,
  BookOpen,
  Check,
  FileText,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";
import type { ApiError } from "../api/client";
import { humanise, type Citation } from "../api/types";
import { useEvidence } from "./EvidenceDrawer";

export function PageHeading({
  eyebrow,
  title,
  children,
  actions,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        <p className="eyebrow">{eyebrow || "Your academic workspace"}</p>
        <h1>
          {title}
          <span className="accent">.</span>
        </h1>
        {children && <div className="subtitle">{children}</div>}
      </div>
      {actions && <div className="heading-actions">{actions}</div>}
    </header>
  );
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "blue" | "caution" | "success";
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
export function Status({ value }: { value: string }) {
  return (
    <Badge
      tone={
        [
          "unknown",
          "insufficient_evidence",
          "needs_evidence",
          "FAILED",
          "documented_gap",
        ].includes(value)
          ? "caution"
          : ["supported", "SUCCEEDED", "approved"].includes(value)
            ? "success"
            : "blue"
      }
    >
      {humanise(value)}
    </Badge>
  );
}
export function Notice({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "caution";
}) {
  return (
    <div className={`notice ${tone}`}>
      <ShieldCheck size={16} aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}
export function Card({
  title,
  eyebrow,
  children,
  className = "",
}: {
  title?: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      {title && <h2>{title}</h2>}
      {children}
    </section>
  );
}
export function Loading({
  label = "Loading workspace records",
}: {
  label?: string;
}) {
  return (
    <div className="state" role="status">
      <LoaderCircle className="spin" size={22} aria-hidden="true" />
      <p>{label}…</p>
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: ApiError;
  retry?: () => void;
}) {
  return (
    <div className="state state-error" role="alert">
      <AlertCircle size={22} aria-hidden="true" />
      <h2>Unable to load this view</h2>
      <p>{error.message}</p>
      <small>
        {error.code}
        {error.requestId ? ` · Request ${error.requestId}` : ""}
      </small>
      {retry && (
        <button className="button secondary" onClick={retry}>
          Reload records
        </button>
      )}
    </div>
  );
}
export function Empty({
  title = "No records yet",
  children,
}: {
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div className="state">
      <BookOpen size={24} aria-hidden="true" />
      <h2>{title}</h2>
      <div>{children || "This workspace has no result to display yet."}</div>
    </div>
  );
}
export function TextList({
  items,
  empty = "None recorded.",
}: {
  items?: string[];
  empty?: string;
}) {
  return items?.length ? (
    <ul className="text-list">
      {items.map((item, i) => (
        <li key={i}>
          {/^[a-z][a-z0-9_]+$/i.test(item) ? humanise(item) : item}
        </li>
      ))}
    </ul>
  ) : (
    <p className="muted">{empty}</p>
  );
}
export function Citations({
  citations,
  evidencePath,
}: {
  citations?: Citation[];
  evidencePath?: string;
}) {
  const { openEvidence } = useEvidence();
  if (!citations?.length)
    return <small className="muted">No supporting citation supplied.</small>;
  return (
    <div className="citations">
      {citations.map((citation, i) => (
        <button
          key={`${citation.reference_id}-${i}`}
          className="citation"
          disabled={!evidencePath}
          onClick={() =>
            evidencePath && openEvidence(evidencePath, citation.reference_id)
          }
        >
          <FileText size={13} aria-hidden="true" />
          Source {i + 1}
          <ArrowUpRight size={12} aria-hidden="true" />
          <span className="sr-only"> {citation.reference_id}</span>
        </button>
      ))}
    </div>
  );
}
export function SectionLink({
  to,
  children,
}: {
  to: string;
  children: ReactNode;
}) {
  return (
    <Link className="section-link" to={to}>
      {children}
      <ArrowUpRight size={16} aria-hidden="true" />
    </Link>
  );
}
export function ReviewForm({
  permitted,
  disabled,
  submit,
}: {
  permitted: boolean;
  disabled?: boolean;
  submit: (decision: string, reason: string) => Promise<void>;
}) {
  const [decision, setDecision] = useState("under_review");
  const [reason, setReason] = useState("");
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState("");
  if (!permitted)
    return (
      <Notice>
        Your operator grant has no review permission. Academic review is
        read-only.
      </Notice>
    );
  return (
    <form
      className="review-form"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!reason.trim() || disabled || state === "saving") return;
        setState("saving");
        setError("");
        try {
          await submit(decision, reason.trim());
          setState("saved");
          setReason("");
        } catch (error) {
          setState("idle");
          setError(
            error instanceof Error
              ? error.message
              : "The review was not saved. Reload the record.",
          );
        }
      }}
    >
      <Notice>
        This records an operator decision. It does not identify a named academic
        reviewer or automatically change a curriculum.
      </Notice>
      <label>
        Review decision
        <select
          value={decision}
          onChange={(e) => {
            setDecision(e.target.value);
            setState("idle");
          }}
          disabled={disabled || state === "saving"}
        >
          <option value="under_review">Under review</option>
          <option value="needs_evidence">Needs evidence</option>
          <option value="approved">Approve for consideration</option>
          <option value="rejected">Reject</option>
          <option value="no_change_required">No change required</option>
        </select>
      </label>
      <label>
        Reason
        <textarea
          required
          maxLength={2000}
          rows={3}
          value={reason}
          onChange={(e) => {
            setReason(e.target.value);
            setState("idle");
          }}
          disabled={disabled || state === "saving"}
        />
      </label>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      <button
        className="button"
        disabled={disabled || !reason.trim() || state === "saving"}
        type="submit"
      >
        {state === "saving" ? "Saving decision…" : "Record review decision"}
      </button>
      {state === "saved" && (
        <p role="status" className="saved">
          <Check size={16} />
          Review recorded by the backend.
        </p>
      )}
    </form>
  );
}
