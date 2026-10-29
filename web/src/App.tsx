import { useQuery, useQueryClient } from "@tanstack/react-query";
import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";
import { api, ApiError, setCsrf, type Me } from "./api/client";
import { Background } from "./components/Background";
import { CommandPalette, type Command } from "./components/CommandPalette";
import { EvidenceProvider } from "./components/evidence";
import { HeroSphere } from "./components/HeroSphere";
import { Footer, PageHead, TopBar } from "./components/Shell";
import { Loading } from "./components/ui";
import { PAGES, pageFromHash, type PageId } from "./lib/pages";
import { usePrefs } from "./lib/prefs";
import { plainText } from "./lib/status";
import {
  ApprovalPage,
  AuditPage,
  ClaimsPage,
  InventoryPage,
  OverviewPage,
  PlanPage,
  SettingsPage,
  VerificationPage,
} from "./pages/tier1";
import { ActivityPage, ReportsPage, RunsPage, UsersPage } from "./pages/tier3";
// Tier 2 pages (Cytoscape, Recharts) are code-split: they load only when opened.
const DependenciesPage = lazy(() => import("./pages/tier2").then((m) => ({ default: m.DependenciesPage })));
const EvaluationPage = lazy(() => import("./pages/tier2").then((m) => ({ default: m.EvaluationPage })));
const MlAiPage = lazy(() => import("./pages/tier2").then((m) => ({ default: m.MlAiPage })));
const SourcesPage = lazy(() => import("./pages/tier2").then((m) => ({ default: m.SourcesPage })));

export { PAGES };

const BANNER =
  "Hackathon prototype (PQC-01). Synthetic demo bank; TLS results are a loopback TEST SCENARIO with throw-away keys. Not production ready, not certified, no quantum-safety guarantee. Candidates are for human review; unknown purpose = HOLD.";

function navigate(p: string) {
  window.location.hash = `/${p}`;
}

function Login({
  onDone,
  theme,
  reduceMotion,
}: {
  onDone: (m: Me) => void;
  theme: "dark" | "light";
  reduceMotion: boolean;
}) {
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [err, setErr] = useState("");
  return (
    <main className="container relative z-10 grid min-h-full grid-cols-1 items-center gap-8 py-10 md:grid-cols-2">
      <div className="hidden md:block">
        <div className="eyebrow">PQC-01 · Post-quantum migration console</div>
        <h1 className="display">
          Move to <span className="grad-text">post-quantum</span> cryptography, one verified step at a time.
        </h1>
        <HeroSphere theme={theme} reduceMotion={reduceMotion} nodes={[]} />
      </div>
      <form
        className="glass glass-overlay w-full max-w-[420px] justify-self-center p-8"
        onSubmit={async (e) => {
          e.preventDefault();
          setErr("");
          try {
            const me = await api.login(u, p);
            setCsrf(me.csrf);
            onDone(me);
          } catch (ex) {
            setErr(ex instanceof Error ? ex.message : "login failed");
          }
        }}
      >
        <div className="brand mb-2">
          <span className="brand-mark" aria-hidden="true" />
          CryptoShift
        </div>
        <h2 className="mt-4 mb-1 text-2xl font-semibold">Sign in</h2>
        <p className="t-muted mt-0 text-sm">Local prototype console. Use your local account.</p>
        <label className="mt-4 block text-sm">
          Username
          <input
            className="input mt-1 block w-full"
            autoComplete="username"
            value={u}
            onChange={(e) => setU(e.target.value)}
          />
        </label>
        <label className="mt-3 block text-sm">
          Password
          <input
            className="input mt-1 block w-full"
            type="password"
            autoComplete="current-password"
            value={p}
            onChange={(e) => setP(e.target.value)}
          />
        </label>
        {err && (
          <p role="alert" className="t-bad text-sm">
            {plainText(err, 200)}
          </p>
        )}
        <button type="submit" className="btn btn-primary mt-6 w-full">
          Sign in
        </button>
        <p className="t-muted mb-0 text-xs">Runs on 127.0.0.1 only.</p>
      </form>
    </main>
  );
}

export function App() {
  const [prefs, setPrefs] = usePrefs();
  const qc = useQueryClient();
  const [page, setPage] = useState<PageId>(pageFromHash);
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, retry: false });
  const assistant = useQuery({
    queryKey: ["assistant-status"],
    queryFn: api.assistantStatus,
    enabled: me.isSuccess,
    staleTime: 30_000,
  });
  const settings = useQuery({ queryKey: ["settings"], queryFn: api.settings, enabled: me.isSuccess });
  useEffect(() => {
    const on = () => {
      setPage(pageFromHash());
      window.scrollTo({ top: 0 });
    };
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    if (me.data) setCsrf(me.data.csrf);
  }, [me.data]);
  const go = navigate;
  const bg = <Background theme={prefs.theme} reduceMotion={prefs.reduceMotion} />;

  if (me.isLoading) return bg;
  if (me.error || !me.data) {
    const unauth = me.error instanceof ApiError && me.error.status === 401;
    return (
      <>
        {bg}
        {unauth || !me.error ? (
          <Login onDone={() => void qc.invalidateQueries()} theme={prefs.theme} reduceMotion={prefs.reduceMotion} />
        ) : (
          <p role="alert" className="relative z-10 p-6">
            Backend not reachable: {plainText((me.error as Error).message, 200)}. Start it with
            scripts\run_full_demo.ps1.
          </p>
        )}
      </>
    );
  }
  const user = me.data;
  const commands: Command[] = [
    ...PAGES.map((p) => ({ id: `go-${p.id}`, label: `Go to ${p.label}`, run: () => go(p.id) })),
    {
      id: "theme",
      label: `Switch to ${prefs.theme === "dark" ? "light" : "dark"} theme`,
      run: () => setPrefs({ theme: prefs.theme === "dark" ? "light" : "dark" }),
    },
    {
      id: "rt",
      label: "Toggle reduced transparency",
      run: () => setPrefs({ reduceTransparency: !prefs.reduceTransparency }),
    },
    { id: "hc", label: "Toggle high contrast", run: () => setPrefs({ highContrast: !prefs.highContrast }) },
    { id: "rm", label: "Toggle reduced motion", run: () => setPrefs({ reduceMotion: !prefs.reduceMotion }) },
    { id: "print", label: "Open the printable report", hint: "PDF", run: () => go("reports") },
    {
      id: "exp-md",
      label: "Export plan as Markdown",
      hint: "download",
      run: () => window.open("/api/v1/export/md?page=plan", "_blank", "noopener"),
    },
    {
      id: "exp-json",
      label: "Export evaluation as JSON",
      hint: "download",
      run: () => window.open("/api/v1/export/json?page=evaluation", "_blank", "noopener"),
    },
  ];
  const pages: Record<PageId, ReactNode> = {
    overview: <OverviewPage me={user} go={go} prefs={prefs} />,
    sources: <SourcesPage />,
    activity: <ActivityPage />,
    inventory: <InventoryPage />,
    dependencies: <DependenciesPage theme={prefs.theme} />,
    evaluation: <EvaluationPage />,
    plan: <PlanPage />,
    verification: <VerificationPage />,
    approval: <ApprovalPage me={user} />,
    runs: <RunsPage me={user} />,
    reports: <ReportsPage />,
    claims: <ClaimsPage />,
    ml: <MlAiPage me={user} />,
    audit: <AuditPage />,
    users: <UsersPage me={user} />,
    settings: <SettingsPage me={user} />,
  };
  const signOut = async () => {
    await api.logout();
    // drop every cached report, then reset the session query so it refetches (401) and shows sign-in
    qc.removeQueries({ predicate: (q) => q.queryKey[0] !== "me" });
    await qc.resetQueries({ queryKey: ["me"] });
  };
  return (
    <EvidenceProvider>
      {bg}
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="relative z-10 flex min-h-full flex-col">
        <TopBar
          me={user}
          page={page}
          prefs={prefs}
          setPrefs={setPrefs}
          palette={<CommandPalette commands={commands} />}
          dataMode={settings.data?.data_mode ?? "LIVE"}
          cloudAi={assistant.data?.cloud_ai ?? "OFF"}
          onSignOut={() => void signOut()}
        />
        <div className="truth-strip" role="note">
          <div className="container py-2">{BANNER}</div>
        </div>
        <main id="main" tabIndex={-1} className="container min-w-0 flex-1 pb-8">
          {page !== "overview" && <PageHead id={page} />}
          <Suspense fallback={<Loading what="page" />}>{pages[page]}</Suspense>
        </main>
        <Footer me={user} />
      </div>
    </EvidenceProvider>
  );
}
