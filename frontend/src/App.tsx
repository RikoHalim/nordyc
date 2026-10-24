import {
  Component,
  Suspense,
  lazy,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  BrowserRouter,
  Link,
  NavLink,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import {
  ArrowLeft,
  BookOpen,
  BriefcaseBusiness,
  ChartNoAxesCombined,
  ChevronRight,
  CircleHelp,
  ClipboardCheck,
  FileCheck2,
  FlaskConical,
  Layers,
  Menu,
  Network,
  Settings2,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import { ApiClient, ApiError } from "./api/client";
import {
  revisionLabel,
  type AccessContext,
  type Institution,
  type Programme,
  type Revision,
} from "./api/types";
import { useResource } from "./lib/resource";
import { SessionContext, useSession } from "./app/session";
import { Workspace, useWorkspace } from "./app/workspace";
import { Brand, BRAND } from "./components/Brand";
import { EvidenceProvider } from "./components/EvidenceDrawer";
import {
  Card,
  Empty,
  ErrorState,
  Loading,
  Notice,
  PageHeading,
} from "./components/ui";

const Library = lazy(() => import("./pages/Library"));
const Overview = lazy(() => import("./pages/Overview"));
const Courses = lazy(() => import("./pages/Courses"));
const UploadPage = lazy(() => import("./pages/Upload"));
const Intelligence = lazy(() => import("./pages/Intelligence"));
const SECTIONS = [
  ["overview", "Programme overview", Layers],
  ["courses", "Course intelligence", BookOpen],
  ["industry", "Industry outlook", ChartNoAxesCombined],
  ["careers", "Career alignment", BriefcaseBusiness],
  ["competencies", "Competency analysis", Network],
  ["recommendations", "Academic recommendations", FileCheck2],
  ["pathways", "Academic pathways", Network],
  ["scenarios", "Future scenarios", Layers],
  ["sdg", "SDG alignment", FlaskConical],
  ["plan", "Academic Action Plan", ClipboardCheck],
] as const;
const validId = (id?: string | null) =>
  Boolean(
    id && /^[a-f\d]{8}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{4}-[a-f\d]{12}$/i.test(id),
  );

class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main className="access-screen">
        <h1>Workspace view unavailable</h1>
        <p>No academic result is displayed. Reload the page to reconnect.</p>
        <button className="button" onClick={() => window.location.reload()}>
          Reload workspace
        </button>
      </main>
    ) : (
      this.props.children
    );
  }
}

function Connect({
  onConnect,
}: {
  onConnect: (api: ApiClient, access: AccessContext) => void;
}) {
  const [credential, setCredential] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  return (
    <main className="access-screen">
      <Brand />
      <p className="eyebrow">Evidence-led academic review</p>
      <h1>
        Curriculum, with direction<span className="accent">.</span>
      </h1>
      <p>
        Connect to your authorised institutional workspace. Academic decisions
        stay with your team.
      </p>
      <form
        className="card access-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setLoading(true);
          setError(null);
          try {
            const api = new ApiClient(credential.trim(), () =>
              window.dispatchEvent(new Event("workspace-auth-expired")),
            );
            const access = await api.get<AccessContext>(
              "/api/v1/access-context",
              "AccessContext",
            );
            if (!access.authenticated || access.access_mode !== "scoped")
              throw new ApiError("SCOPED_ACCESS_REQUIRED");
            setCredential("");
            onConnect(api, access);
          } catch (error) {
            setError(
              error instanceof ApiError ? error : new ApiError("NETWORK"),
            );
          } finally {
            setLoading(false);
          }
        }}
      >
        <h2>Open your workspace</h2>
        <label>
          Scoped operator credential
          <input
            type="password"
            name="workspace-credential"
            value={credential}
            onChange={(e) => setCredential(e.target.value)}
            autoComplete="off"
            spellCheck={false}
            required
            minLength={32}
            maxLength={4096}
          />
        </label>
        <small>
          Ask the development administrator for your scoped credential. It stays
          in this tab’s memory and is cleared when you disconnect or reload.
        </small>
        {error && (
          <p role="alert" className="form-error">
            {error.message} ({error.code})
          </p>
        )}
        <button
          className="button"
          disabled={loading || credential.trim().length < 32}
        >
          {loading ? "Connecting…" : "Connect workspace"}
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      </form>
      <p className="notice">
        <ShieldCheck size={16} aria-hidden="true" />
        Controlled preview · operator grants are not named academic identities.
      </p>
    </main>
  );
}

function AccessPage() {
  const { access, disconnect } = useSession();
  return (
    <>
      <PageHeading eyebrow="Workspace access" title="Your operator grant">
        Your capabilities are enforced by the backend on every request.
      </PageHeading>
      <Card title="Access context">
        <dl className="detail-list">
          <dt>Operator alias</dt>
          <dd>{access.operator_alias || "Not configured"}</dd>
          <dt>Identity</dt>
          <dd>Scoped operator grant; not a named academic reviewer</dd>
          <dt>Permissions</dt>
          <dd>{access.permissions.join(", ") || "None"}</dd>
          <dt>Institution scope</dt>
          <dd>
            {access.global_admin
              ? "Explicit global administrator grant"
              : `${access.institution_ids.length} institution(s)`}
          </dd>
          <dt>External processing</dt>
          <dd>
            {access.execution.external_processing_allowed
              ? "Configured; this is not per-request billing approval"
              : "Disabled"}
          </dd>
          <dt>External research</dt>
          <dd>
            {access.execution.research_enabled
              ? "Configured; separate approval still required"
              : "Disabled"}
          </dd>
        </dl>
        <button className="button secondary" onClick={disconnect}>
          Disconnect workspace
        </button>
      </Card>
      <Notice>
        The preview contains no built-in provider secrets. New analysis actions
        use the offline workflow; no live model or research action is offered
        here.
      </Notice>
    </>
  );
}
function Help() {
  return (
    <>
      <PageHeading title="A little guidance">
        A considered review begins with what you can verify.
      </PageHeading>
      <div className="card-grid">
        <Card title="Start with your curriculum">
          <p>
            A brochure or title inventory is enough for preliminary review.
            Upload a supported PDF, inspect the extraction and retain its source
            references. Missing syllabi remain unknown.
          </p>
        </Card>
        <Card title="Read evidence before acting">
          <p>
            Occupation requirements are benchmarks. AI exposure is not job
            replacement, and evidence coverage is not a curriculum quality
            score.
          </p>
        </Card>
        <Card title="Keep human review explicit">
          <p>
            Recommendations, pathways and SDG contributions are proposals.
            Review decisions require an authorised grant and the exact current
            result version.
          </p>
        </Card>
        <Card title="Understand the preview">
          <p>
            Fictional programmes and mocked model output are labelled. Brave
            original-source admission remains partial. Public deployment and
            expert academic validation are not accepted.
          </p>
        </Card>
      </div>
    </>
  );
}
function GlobalLayout() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="global-header">
        <Link to="/" aria-label={`${BRAND.name} curriculum library`}>
          <Brand />
        </Link>
        <span className="brand-descriptor">{BRAND.descriptor}</span>
        <div className="header-actions">
          <Link
            to="/help"
            className="icon-button"
            aria-label="Help and guidance"
          >
            <CircleHelp size={19} />
          </Link>
          <Link to="/access" className="avatar" aria-label="Workspace access">
            OP
          </Link>
        </div>
      </header>
      <div className="mode-banner">
        <span className="dot" />
        Protected backend workspace · evidence-led review · human decisions
      </div>
      <main id="main" tabIndex={-1} className="library-main">
        <Suspense fallback={<Loading />}>
          <Outlet />
        </Suspense>
      </main>
      <footer className="global-footer">
        <span>{BRAND.name.toLowerCase()} · Curriculum, with direction.</span>
        <span>Scoped access · no browser data storage</span>
      </footer>
    </>
  );
}

function ProgrammeShell() {
  const { api, access } = useSession();
  const { programmeId } = useParams();
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const [menu, setMenu] = useState(false);
  const lastFocus = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!menu) return;
    lastFocus.current = document.activeElement as HTMLElement | null;
    const nav = document.getElementById("programme-navigation");
    const targets = () =>
      nav?.querySelectorAll<HTMLElement>("a[href],button:not(:disabled)") || [];
    targets()[0]?.focus();
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMenu(false);
      }
      if (event.key === "Tab") {
        const nodes = targets();
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      lastFocus.current?.focus();
    };
  }, [menu]);
  const context = useResource(
    validId(programmeId)
      ? `${programmeId}:${params.get("revision") || "active"}`
      : null,
    async (signal) => {
      const programme = await api.get<Programme>(
        `/api/v1/programmes/${programmeId}`,
        "ProgrammeRead",
        signal,
      );
      const [institution, revisions] = await Promise.all([
        api.get<Institution>(
          `/api/v1/institutions/${programme.institution_id}`,
          "InstitutionRead",
          signal,
        ),
        api.all<Revision>(
          `/api/v1/programmes/${programme.id}/revisions`,
          "Page_ProgrammeRevisionRead_",
          signal,
        ),
      ]);
      return { programme, institution, revisions };
    },
    0,
  );
  useEffect(() => {
    setMenu(false);
    document.getElementById("main")?.focus();
  }, [location.pathname]);
  const section = location.pathname.split("/").pop() || "overview";
  const label =
    SECTIONS.find((item) => item[0] === section)?.[1] ||
    (
      {
        upload: "Curriculum upload",
        evidence: "Evidence & sources",
        reviews: "Review history",
        settings: "Curriculum settings",
      } as Record<string, string>
    )[section] ||
    "Programme overview";
  if (!validId(programmeId))
    return (
      <main className="library-main">
        <Empty title="Invalid programme reference">
          <Link to="/">Return to the library</Link>
        </Empty>
      </main>
    );
  if (context.loading)
    return (
      <main className="library-main">
        <Loading />
      </main>
    );
  if (context.error)
    return (
      <main className="library-main">
        <ErrorState error={context.error} retry={context.reload} />
        <Link to="/">Return to the library</Link>
      </main>
    );
  if (!context.data) return null;
  const { programme, institution, revisions } = context.data;
  const revisionId = params.get("revision") || programme.active_revision_id;
  if (revisionId && !revisions.some((row) => row.id === revisionId))
    return (
      <main className="library-main">
        <Empty title="Revision unavailable">
          <button className="button" onClick={() => setParams({})}>
            Use the active revision
          </button>
        </Empty>
      </main>
    );
  const setRevision = (id: string) => {
    const next = new URLSearchParams();
    next.set("revision", id);
    setParams(next);
  };
  const base = `/programmes/${programme.id}`;
  const suffix = params.size
    ? `?${params.toString()}`
    : revisionId
      ? `?revision=${revisionId}`
      : "";
  return (
    <Workspace.Provider
      value={{
        api,
        access,
        programme,
        institution,
        revisionId,
        revisions,
        setRevision,
      }}
    >
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {menu && (
        <button
          className="menu-backdrop"
          aria-label="Close programme menu"
          onClick={() => setMenu(false)}
        />
      )}
      <aside
        id="programme-navigation"
        className={`sidebar ${menu ? "is-open" : ""}`}
        role={menu ? "dialog" : undefined}
        aria-modal={menu ? true : undefined}
        aria-label="Programme navigation"
      >
        <button
          className="icon-button mobile-menu-close"
          onClick={() => setMenu(false)}
          aria-label="Close navigation"
        >
          <X size={20} />
        </button>
        <Link to="/" className="back-link">
          <ArrowLeft size={16} />
          All curricula
        </Link>
        <div className={`programme-tile ${category(programme.discipline_key)}`}>
          <span className="programme-symbol">
            <BookOpen size={24} />
          </span>
          <h2>{programme.name}</h2>
          <p>{institution.name}</p>
          <small>
            {programme.is_synthetic
              ? "Synthetic demonstration"
              : "Stored programme records"}
          </small>
        </div>
        <p className="eyebrow nav-label">Explore &amp; improve</p>
        <nav>
          {SECTIONS.filter(([key]) => !["scenarios", "sdg"].includes(key)).map(
            ([key, text, Icon]) => (
              <NavLink key={key} to={`${base}/${key}${suffix}`}>
                <Icon size={17} aria-hidden="true" />
                <span>{text}</span>
              </NavLink>
            ),
          )}
        </nav>
        <nav className="support-nav">
          <NavLink to={`${base}/evidence${suffix}`}>
            <ShieldCheck size={17} />
            Evidence &amp; sources
          </NavLink>
          <NavLink to={`${base}/reviews${suffix}`}>
            <ClipboardCheck size={17} />
            Review history
          </NavLink>
          {access.permissions.includes("write") && (
            <NavLink to={`${base}/upload${suffix}`}>
              <Upload size={17} />
              Upload &amp; extraction
            </NavLink>
          )}
          <NavLink to={`${base}/settings${suffix}`}>
            <Settings2 size={17} />
            Curriculum settings
          </NavLink>
          <Link to="/help">
            <CircleHelp size={17} />A little guidance
          </Link>
        </nav>
        <div className="sidebar-brand">
          <Link to="/">
            <Brand compact />
          </Link>
          <small>Curriculum, with direction.</small>
        </div>
      </aside>
      <div className="workspace-canvas" inert={menu ? true : undefined}>
        <header className="workspace-topbar">
          <button
            className="icon-button mobile-menu"
            aria-label="Open programme menu"
            aria-expanded={menu}
            aria-controls="programme-navigation"
            onClick={() => setMenu(!menu)}
          >
            <Menu size={22} />
          </button>
          <div className="breadcrumbs">
            <Link to={`${base}/overview${suffix}`}>{programme.name}</Link>
            <ChevronRight size={12} />
            <span>{label}</span>
          </div>
          <div className="header-actions">
            <span className="snapshot-label">
              <span className="dot" />
              Versioned evidence
            </span>
            <Link to="/access" className="avatar" aria-label="Workspace access">
              OP
            </Link>
          </div>
        </header>
        <div className="workspace-banner">
          <span>
            {programme.is_synthetic
              ? "Synthetic demonstration — not real university findings."
              : "Stored curriculum · title-only records need syllabus confirmation"}
          </span>
          <Link to={`${base}/evidence${suffix}`}>Evidence &amp; limits ↗</Link>
        </div>
        <div className="context-strip">
          <span>{institution.name}</span>
          <label className="revision-picker">
            Revision
            <select
              aria-label="Curriculum revision"
              value={revisionId || ""}
              onChange={(e) => setRevision(e.target.value)}
            >
              {revisions.map((row) => (
                <option key={row.id} value={row.id}>
                  {revisionLabel(row)}
                  {row.id === programme.active_revision_id
                    ? " · active"
                    : " · historical"}
                </option>
              ))}
            </select>
          </label>
        </div>
        <main id="main" tabIndex={-1} className="workspace-main">
          {["pathways", "scenarios", "sdg", "plan", "reviews"].includes(
            section,
          ) && (
            <nav
              className="workspace-tabs tabs"
              aria-label="Action plan sections"
            >
              {[
                ["pathways", "Academic pathways"],
                ["scenarios", "Future scenarios"],
                ["sdg", "SDG alignment"],
                ["plan", "Action Plan"],
                ["reviews", "Review history"],
              ].map(([key, text]) => (
                <NavLink key={key} to={`${base}/${key}${suffix}`}>
                  {text}
                </NavLink>
              ))}
            </nav>
          )}
          <Suspense fallback={<Loading />}>
            <Outlet />
          </Suspense>
        </main>
        <footer className="workspace-footer">
          <span>
            <ShieldCheck size={13} />
            Academic decisions stay with your team.
          </span>
          <button className="text-link" onClick={() => navigate("/access")}>
            Workspace access
          </button>
        </footer>
      </div>
    </Workspace.Provider>
  );
}
export function category(discipline?: string | null) {
  if (/comput|tech|digital/.test(discipline || "")) return "technology";
  if (/account|business|econom/.test(discipline || "")) return "business";
  if (/engineer/.test(discipline || "")) return "engineering";
  if (/bio|science|marine/.test(discipline || "")) return "science";
  return "other";
}
function SettingsPage() {
  const { programme, revisions } = useWorkspace();
  return (
    <>
      <PageHeading title="Curriculum settings">
        Catalogue identities and immutable revision history.
      </PageHeading>
      <Card title={programme.name}>
        <dl className="detail-list">
          <dt>Programme ID</dt>
          <dd>{programme.id}</dd>
          <dt>Discipline</dt>
          <dd>{programme.discipline_key || "Not documented"}</dd>
          <dt>Official programme URL</dt>
          <dd>
            {programme.canonical_url ||
              "Not supplied; required for an attributed PDF workflow"}
          </dd>
        </dl>
        <Notice>
          Changing a curriculum uses a reviewed import and creates a new
          revision. This interface does not silently edit protected historical
          records.
        </Notice>
        <Link className="button secondary" to="../upload">
          Upload or import a revision
        </Link>
      </Card>
      <Card title="Revision history">
        <ul className="text-list">
          {revisions.map((row) => (
            <li key={row.id}>
              {row.version_label} · {row.id}
            </li>
          ))}
        </ul>
      </Card>
    </>
  );
}

export default function App() {
  const [session, setSession] = useState<{
    api: ApiClient;
    access: AccessContext;
  } | null>(null);
  const disconnect = () => setSession(null);
  useEffect(() => {
    window.addEventListener("workspace-auth-expired", disconnect);
    return () =>
      window.removeEventListener("workspace-auth-expired", disconnect);
  }, []);
  useEffect(() => {
    if (!session) return;
    const refresh = () => {
      session.api
        .get<AccessContext>("/api/v1/access-context", "AccessContext")
        .then((access) =>
          setSession((current) =>
            current?.api === session.api ? { ...current, access } : current,
          ),
        )
        .catch(() => disconnect());
    };
    const timer = setInterval(refresh, 30_000);
    window.addEventListener("focus", refresh);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", refresh);
    };
  }, [session?.api]);
  const value = useMemo(
    () => (session ? { ...session, disconnect } : null),
    [session],
  );
  return (
    <Boundary>
      {!value ? (
        <Connect onConnect={(api, access) => setSession({ api, access })} />
      ) : (
        <SessionContext.Provider value={value}>
          <BrowserRouter>
            <EvidenceProvider api={value.api}>
              <Routes>
                <Route element={<GlobalLayout />}>
                  <Route
                    path="/"
                    element={
                      value.access.permissions.includes("read") ? (
                        <Library />
                      ) : (
                        <Empty title="Read access is not granted">
                          <Link to="/access">Inspect your operator grant</Link>
                        </Empty>
                      )
                    }
                  />
                  <Route path="/access" element={<AccessPage />} />
                  <Route path="/help" element={<Help />} />
                  <Route
                    path="*"
                    element={
                      <Empty title="Page not found">
                        <Link to="/">Return to curricula</Link>
                      </Empty>
                    }
                  />
                </Route>
                <Route
                  path="/programmes/:programmeId"
                  element={<ProgrammeShell />}
                >
                  <Route index element={<Navigate to="overview" replace />} />
                  <Route path="overview" element={<Overview />} />
                  <Route path="courses" element={<Courses />} />
                  <Route path="upload" element={<UploadPage />} />
                  <Route path="settings" element={<SettingsPage />} />
                  {[
                    "industry",
                    "careers",
                    "competencies",
                    "recommendations",
                    "pathways",
                    "scenarios",
                    "sdg",
                    "plan",
                    "reviews",
                    "evidence",
                  ].map((section) => (
                    <Route
                      key={section}
                      path={section}
                      element={<Intelligence section={section} />}
                    />
                  ))}
                </Route>
              </Routes>
            </EvidenceProvider>
          </BrowserRouter>
        </SessionContext.Provider>
      )}
    </Boundary>
  );
}
