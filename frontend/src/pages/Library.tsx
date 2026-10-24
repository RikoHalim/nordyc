import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowUpRight,
  BookOpen,
  BriefcaseBusiness,
  Clock3,
  Code2,
  FlaskConical,
  Plus,
  Search,
  ShieldCheck,
  X,
  Zap,
} from "lucide-react";
import { category } from "../App";
import { useSession } from "../app/session";
import { ApiError } from "../api/client";
import {
  dateLabel,
  revisionLabel,
  type Institution,
  type Model,
  type Programme,
} from "../api/types";
import { useResource } from "../lib/resource";
import SampleProgrammeEntry from "../components/SampleProgrammeEntry";
import {
  Badge,
  Empty,
  ErrorState,
  Loading,
  Notice,
  PageHeading,
} from "../components/ui";

const categories = [
  ["all", "All curricula"],
  ["technology", "Technology"],
  ["business", "Business"],
  ["engineering", "Engineering"],
  ["science", "Science"],
  ["other", "Uncategorised"],
] as const;
const icons = {
  technology: Code2,
  business: BriefcaseBusiness,
  engineering: Zap,
  science: FlaskConical,
  other: BookOpen,
};

function CreateCurriculum({
  institutions,
  close,
}: {
  institutions: Institution[];
  close: () => void;
}) {
  const { api, access } = useSession();
  const navigate = useNavigate();
  const [institutionId, setInstitutionId] = useState(institutions[0]?.id || "");
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [localInstitutions, setLocalInstitutions] = useState(institutions);
  const [institutionName, setInstitutionName] = useState("");
  const [institutionUrl, setInstitutionUrl] = useState("");
  const [synthetic, setSynthetic] = useState(false);
  const institution = localInstitutions.find(
    (item) => item.id === institutionId,
  );
  const dialog = useRef<HTMLDialogElement>(null);
  return (
    <dialog
      ref={(element) => {
        dialog.current = element;
        if (element && !element.open) element.showModal();
      }}
      className="form-dialog"
      aria-labelledby="create-title"
      onCancel={close}
      onClose={close}
    >
      <header className="dialog-header">
        <div>
          <p className="eyebrow">Begin with what you know</p>
          <h2 id="create-title">New curriculum</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Close new curriculum"
          onClick={close}
        >
          <X />
        </button>
      </header>
      <p>
        Create a real stored programme record, then add its curriculum. A title
        inventory is sufficient for preliminary review.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (!institution || busy) return;
          setBusy(true);
          setError(null);
          try {
            const row = await api.post<Programme>(
              `/api/v1/institutions/${institution.id}/programmes`,
              "ProgrammeRead",
              {
                name: name.trim(),
                canonical_url: url.trim() || null,
                discipline_key: discipline.trim() || null,
                is_synthetic: institution.is_synthetic,
              },
            );
            close();
            navigate(`/programmes/${row.id}/upload`);
          } catch (error) {
            setError(error as ApiError);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Institution
          <select
            required
            value={institutionId}
            onChange={(e) => setInstitutionId(e.target.value)}
          >
            <option value="" disabled>
              Select an authorised institution
            </option>
            {localInstitutions.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
                {item.is_synthetic ? " · synthetic" : ""}
              </option>
            ))}
          </select>
        </label>
        <label>
          Programme name
          <input
            required
            maxLength={255}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label>
          Official programme URL{" "}
          <span className="muted">(needed for attributed uploads)</span>
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://your-university.example/programme"
          />
        </label>
        <label>
          Discipline <span className="muted">(optional)</span>
          <input
            maxLength={100}
            value={discipline}
            onChange={(e) => setDiscipline(e.target.value)}
            placeholder="Use the programme’s documented discipline"
          />
        </label>
        {institution?.is_synthetic && (
          <Notice>
            This institution is fictional. Its programme and imported records
            will remain synthetic.
          </Notice>
        )}
        {error && (
          <p role="alert" className="form-error">
            {error.message}
          </p>
        )}
        <button
          className="button"
          type="submit"
          disabled={busy || !institution || !name.trim()}
        >
          {busy ? "Creating record…" : "Create curriculum workspace"}
          <ArrowUpRight size={16} />
        </button>
      </form>
      {access.permissions.includes("admin") &&
        access.permissions.includes("write") && (
          <details className="admin-details">
            <summary>Create an authorised institution record</summary>
            <form
              onSubmit={async (e) => {
                e.preventDefault();
                setBusy(true);
                setError(null);
                try {
                  const row = await api.post<Institution>(
                    "/api/v1/institutions",
                    "InstitutionRead",
                    {
                      name: institutionName.trim(),
                      website_url: institutionUrl.trim() || null,
                      is_synthetic: synthetic,
                    },
                  );
                  setLocalInstitutions([...localInstitutions, row]);
                  setInstitutionId(row.id);
                  setInstitutionName("");
                  setInstitutionUrl("");
                } catch (error) {
                  setError(error as ApiError);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <label>
                Institution name
                <input
                  required
                  maxLength={255}
                  value={institutionName}
                  onChange={(e) => setInstitutionName(e.target.value)}
                />
              </label>
              <label>
                Official institution website
                <input
                  type="url"
                  value={institutionUrl}
                  onChange={(e) => setInstitutionUrl(e.target.value)}
                />
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={synthetic}
                  onChange={(e) => setSynthetic(e.target.checked)}
                />
                This is a fictional demonstration institution
              </label>
              <button
                className="button secondary"
                disabled={busy || !institutionName.trim()}
              >
                Create institution record
              </button>
            </form>
          </details>
        )}
    </dialog>
  );
}

export default function Library() {
  const { api, access } = useSession();
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [create, setCreate] = useState(false);
  const records = useResource(
    "library",
    async (signal) => {
      const [programmes, institutions] = await Promise.all([
        api.all<Programme>("/api/v1/programmes", "Page_ProgrammeRead_", signal),
        api.all<Institution>(
          "/api/v1/institutions",
          "Page_InstitutionRead_",
          signal,
        ),
      ]);
      const coverage = await Promise.all(
        programmes.map(async (programme) => {
          try {
            return [
              programme.id,
              await api.get<Model<"CoverageRead">>(
                `/api/v1/programmes/${programme.id}/coverage`,
                "CoverageRead",
                signal,
              ),
            ] as const;
          } catch (error) {
            if (signal.aborted) throw error;
            return [programme.id, null] as const;
          }
        }),
      );
      return { programmes, institutions, coverage: new Map(coverage) };
    },
    30_000,
    true,
  );
  if (records.loading) return <Loading label="Loading accessible curricula" />;
  if (records.error)
    return <ErrorState error={records.error} retry={records.reload} />;
  if (!records.data) return null;
  const { programmes, institutions, coverage } = records.data;
  const matches = programmes.filter(
    (row) =>
      (filter === "all" || category(row.discipline_key) === filter) &&
      `${row.name} ${institutions.find((item) => item.id === row.institution_id)?.name || ""}`
        .toLowerCase()
        .includes(search.toLowerCase()),
  );
  return (
    <>
      <PageHeading title="Your curricula">
        Choose a programme. See what’s changing. Shape what comes next.
      </PageHeading>
      <SampleProgrammeEntry
        programmes={programmes}
        institutions={institutions}
        coverage={coverage}
      />
      <div
        className="category-tabs"
        role="group"
        aria-label="Filter curricula by discipline"
      >
        {categories
          .filter(
            ([key]) =>
              key === "all" ||
              programmes.some((row) => category(row.discipline_key) === key),
          )
          .map(([key, label]) => (
            <button
              key={key}
              className={`${filter === key ? "selected" : ""} category-${key}`}
              aria-pressed={filter === key}
              onClick={() => setFilter(key)}
            >
              {key !== "all" && <span className="dot" />}
              {label}
            </button>
          ))}
      </div>
      <div className="library-tools">
        <p>
          Your programmes <Badge>{programmes.length}</Badge>
        </p>
        <label className="search-field">
          <Search size={17} aria-hidden="true" />
          <span className="sr-only">Find a curriculum</span>
          <input
            type="search"
            placeholder="Find a curriculum…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
      </div>
      <div className="programme-grid">
        <button
          className="new-curriculum-card"
          disabled={!access.permissions.includes("write")}
          onClick={() => setCreate(true)}
        >
          <span className="new-document">
            <Plus size={28} aria-hidden="true" />
          </span>
          <strong>New curriculum</strong>
          <span>Start with your programme</span>
          <small>
            {access.permissions.includes("write") ? (
              <>
                Create a workspace <ArrowUpRight size={14} />
              </>
            ) : (
              "Write permission required"
            )}
          </small>
        </button>
        {matches.map((programme) => {
          const key = category(programme.discipline_key),
            Icon = icons[key],
            cov = coverage.get(programme.id);
          return (
            <Link
              className={`programme-card ${key} ${key === "other" ? `palette-${programmes.findIndex((row) => row.id === programme.id) % 3}` : ""}`}
              key={programme.id}
              to={`/programmes/${programme.id}/overview`}
            >
              <div className="programme-cover">
                <div className="cover-top">
                  <span>
                    {categories.find((row) => row[0] === key)?.[1] ||
                      "Programme"}
                  </span>
                  <ArrowUpRight size={16} />
                </div>
                <span className="cover-icon">
                  <Icon size={32} strokeWidth={1.5} aria-hidden="true" />
                </span>
                <span className="cover-lines" />
                <small>Curriculum workspace</small>
              </div>
              <div className="programme-card-body">
                <h2>{programme.name}</h2>
                <p>
                  {institutions.find(
                    (row) => row.id === programme.institution_id,
                  )?.name || "Institution unavailable"}
                </p>
                <div className="programme-card-meta">
                  <span>
                    <span className="dot" />
                    {programme.active_revision
                      ? revisionLabel(programme.active_revision)
                      : "No revision"}
                  </span>
                  <span>
                    {cov
                      ? `${cov.course_count} courses`
                      : "Coverage unavailable"}
                  </span>
                </div>
                <p>
                  {cov
                    ? `${cov.verified_title_count} verified titles · ${cov.title_only_count} title-only records · ${cov.needs_review_count} needing extraction review`
                    : "Curriculum evidence unavailable"}
                </p>
                <div className="programme-card-footer">
                  <span>
                    <Clock3 size={12} />
                    {dateLabel(programme.updated_at)}
                  </span>
                  <Badge>
                    {programme.is_synthetic ? "Synthetic" : "Stored"}
                  </Badge>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
      {!matches.length && (
        <Empty
          title={
            programmes.length
              ? "No curricula match your filters"
              : "Your library is ready"
          }
        >
          <p>
            {programmes.length
              ? "Try another programme name or discipline."
              : "Create an authorised programme and import its curriculum to begin."}
          </p>
          {search || filter !== "all" ? (
            <button
              className="button secondary"
              onClick={() => {
                setSearch("");
                setFilter("all");
              }}
            >
              Clear filters
            </button>
          ) : null}
        </Empty>
      )}
      <p className="library-note">
        <ShieldCheck size={16} aria-hidden="true" />
        Synthetic programmes are fictional. Your own curriculum starts with
        attributed documents you provide.
      </p>
      {create && (
        <CreateCurriculum
          institutions={institutions}
          close={() => setCreate(false)}
        />
      )}
    </>
  );
}
