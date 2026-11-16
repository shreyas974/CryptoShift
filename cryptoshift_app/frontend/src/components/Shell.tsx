import * as React from "react";
import { NavLink, Outlet, useLocation, useNavigate, Link } from "react-router-dom";
import { useApi, mutate } from "../api/client";
import type { AuditList, Health, Repository, FindingsResponse } from "../api/types";
import { useAuth, ROLE_LABEL } from "../auth/Auth";

interface AppContextValue {
  repoId: string | null;
  setRepoId: (id: string) => void;
  repos: Repository[];
  openSearch: () => void;
}

const AppContext = React.createContext<AppContextValue>({
  repoId: null,
  setRepoId: () => {},
  repos: [],
  openSearch: () => {},
});
export const useApp = () => React.useContext(AppContext);

const read = (key: string) => {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};
const write = (key: string, value: string) => {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage unavailable */
  }
};

const NAV: { to: string; label: string; icon: string }[] = [
  { to: "/", label: "Overview", icon: "M3 3h4v4H3zM9 3h4v4H9zM3 9h4v4H3zM9 9h4v4H9z" },
  { to: "/repositories", label: "Repositories", icon: "M3 2.5h8l2 2v9H3zM6 6h4M6 9h4" },
  { to: "/inventory", label: "Crypto Inventory", icon: "M5 7V5a3 3 0 0 1 6 0v2M3.5 7h9v6.5h-9zM8 9.5v2" },
  { to: "/risk", label: "Risk Assessment", icon: "M8 2 14 13H2zM8 6.5v3M8 11.2v.1" },
  { to: "/planner", label: "Migration Planner", icon: "M3 4h4M3 8h7M3 12h10M9 2.5l2 1.5-2 1.5" },
  { to: "/patches", label: "AI Patch Studio", icon: "M4 3v10M4 3a1.5 1.5 0 1 0 0 .1M12 13a1.5 1.5 0 1 0 0-.1M4 6c0 3 8 2 8 5.5" },
  { to: "/verification", label: "Verification Center", icon: "M8 2 13 4v4c0 3-2.2 5-5 6-2.8-1-5-3-5-6V4zM5.8 8l1.6 1.6L10.5 6.5" },
  { to: "/traces", label: "Protocol Traces", icon: "M2 8h3l1.5-4 3 8L11 8h3" },
  { to: "/rollback", label: "Rollback & Recovery", icon: "M4 6.5H10a3 3 0 0 1 0 6H6M4 6.5 6.5 4M4 6.5 6.5 9" },
  { to: "/anatomy", label: "Anatomy Lab", icon: "M2.5 5.5 8 2.5l5.5 3v5L8 13.5l-5.5-3zM2.5 5.5 8 8.5l5.5-3M8 8.5v5" },
  { to: "/reports", label: "Reports & Audit", icon: "M4 2.5h6l2 2v9H4zM6 7h4M6 9.5h4M6 12h2" },
  { to: "/settings", label: "Settings", icon: "M8 5.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5M8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4" },
];

const CRUMBS: Record<string, string> = Object.fromEntries(NAV.map((n) => [n.to, n.label]));
const SUB: Record<string, string> = {
  "/anatomy/quantum-computer": "Quantum Computer",
  "/anatomy/cryptographic-asset": "Cryptographic Asset",
  "/anatomy/banking-dependencies": "Banking Dependencies",
  "/anatomy/verified-migration": "Verified Migration",
};

function Icon({ d }: { d: string }) {
  return (
    <svg className="nav-icon" viewBox="0 0 16 16" aria-hidden="true">
      <path d={d} />
    </svg>
  );
}

export function Shell() {
  const repos = useApi<Repository[]>("/api/repositories");
  const health = useApi<Health>("/api/health", 10000);
  const [repoId, setRepo] = React.useState<string | null>(() => read("cs.repo"));
  const { user, signOut } = useAuth();
  const [navOpen, setNavOpen] = React.useState(false);
  const [searchOpen, setSearchOpen] = React.useState(false);
  const [notificationsOpen, setNotificationsOpen] = React.useState(false);
  const location = useLocation();

  React.useEffect(() => {
    if (repos.data?.length && (!repoId || !repos.data.some((r) => r.id === repoId))) {
      setRepo(repos.data[0].id);
    }
  }, [repos.data, repoId]);

  React.useEffect(() => setNavOpen(false), [location.pathname]);

  // Global Ctrl+K / Cmd+K listener
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const value: AppContextValue = {
    repoId,
    setRepoId: (id) => {
      setRepo(id);
      write("cs.repo", id);
    },
    repos: repos.data ?? [],
    openSearch: () => setSearchOpen(true),
  };

  const online = Boolean(health.data) && !health.error;
  const base = "/" + (location.pathname.split("/")[1] ?? "");
  const crumbs = [{ to: base, label: CRUMBS[base] ?? "Overview" }, ...(SUB[location.pathname] ? [{ to: location.pathname, label: SUB[location.pathname] }] : [])];

  return (
    <AppContext.Provider value={value}>
      <a className="skip" href="#main">
        Skip to content
      </a>
      <div className="app" data-nav-open={navOpen ? "" : undefined}>
        <nav className="sidebar" aria-label="Primary">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                <path d="M12 2.5 20.5 7.4v9.2L12 21.5 3.5 16.6V7.4z" />
                <path d="M8.5 12.6 11 15l4.5-5" />
              </svg>
            </span>
            <span>
              CryptoShift
              <small>PQC-01 · Banking Cryptography</small>
            </span>
          </Link>
          <ul>
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink to={item.to} end={item.to === "/"} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                  <Icon d={item.icon} />
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <div className="sidebar-motto">
            <p>
              <strong>AI proposes.</strong>
              <br />
              <strong>Verification validates.</strong>
              <br />
              <strong>Humans approve.</strong>
            </p>
            {user ? (
              <div className="sidebar-user">
                <span className="sidebar-user-name">{user.displayName}</span>
                <span className="sidebar-user-role">{ROLE_LABEL[user.role]} · @{user.username}</span>
                <button className="btn btn-small btn-ghost sidebar-signout" onClick={() => void signOut()}>
                  Sign out
                </button>
              </div>
            ) : null}
          </div>
        </nav>
        <div className="main-col">
          <TopBar
            crumbs={crumbs}
            online={online}
            health={health.data}
            healthError={health.error?.message}
            onMenu={() => setNavOpen((o) => !o)}
            onOpenSearch={() => setSearchOpen(true)}
            onToggleNotifications={() => setNotificationsOpen((o) => !o)}
          />
          <main id="main" className="content" tabIndex={-1}>
            {repos.error && !repos.data ? (
              <div className="banner banner-error" role="alert">
                Backend unavailable: {repos.error.message.replace(/\.?$/, ".")} Data on every page is unavailable until it reconnects; nothing shown is cached or simulated.
              </div>
            ) : null}
            <Outlet />
          </main>
        </div>
      </div>

      {searchOpen ? <GlobalSearchModal repoId={repoId} onClose={() => setSearchOpen(false)} /> : null}
      {notificationsOpen ? <NotificationsDrawer onClose={() => setNotificationsOpen(false)} /> : null}
    </AppContext.Provider>
  );
}

function TopBar({
  crumbs,
  online,
  health,
  healthError,
  onMenu,
  onOpenSearch,
  onToggleNotifications,
}: {
  crumbs: { to: string; label: string }[];
  online: boolean;
  health: Health | null;
  healthError?: string;
  onMenu: () => void;
  onOpenSearch: () => void;
  onToggleNotifications: () => void;
}) {
  const { repoId, setRepoId, repos } = useApp();
  const { user, can, signOut } = useAuth();
  const [busy, setBusy] = React.useState(false);
  const [profileOpen, setProfileOpen] = React.useState(false);
  const audit = useApi<AuditList>("/api/audit?limit=1", 10000);
  const recentCount = audit.data?.total ?? 0;

  return (
    <header className="topbar">
      <button className="btn btn-ghost menu-btn" onClick={onMenu} aria-label="Toggle navigation">
        ☰
      </button>
      <label className="repo-select">
        <span className="sr-only">Repository</span>
        <svg viewBox="0 0 16 16" aria-hidden="true">
          <path d="M3 2.5h8l2 2v9H3z" />
        </svg>
        <select value={repoId ?? ""} onChange={(e) => setRepoId(e.target.value)} disabled={!repos.length}>
          {repos.length ? repos.map((r) => <option key={r.id} value={r.id}>{r.name}</option>) : <option value="">No repository</option>}
        </select>
      </label>
      <nav aria-label="Breadcrumb" className="crumbs">
        <ol>
          {crumbs.map((c, i) => (
            <li key={c.to}>{i === crumbs.length - 1 ? <span aria-current="page">{c.label}</span> : <Link to={c.to}>{c.label}</Link>}</li>
          ))}
        </ol>
      </nav>

      {/* Global search trigger */}
      <div className="top-search">
        <button
          className="search"
          type="button"
          onClick={onOpenSearch}
          aria-label="Search algorithms, files, services"
          style={{ width: "100%", cursor: "pointer", justifyContent: "space-between" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <circle cx="7" cy="7" r="4.5" />
              <path d="M10.5 10.5 14 14" />
            </svg>
            <span style={{ fontSize: 13, color: "var(--cs-muted)" }}>Search (Ctrl+K)</span>
          </div>
          <span className="mono" style={{ fontSize: 10, padding: "2px 5px" }}>⌘K</span>
        </button>
      </div>

      {can("engineer") ? (
      <button
        className="btn"
        disabled={!online || !repoId || busy}
        onClick={async () => {
          setBusy(true);
          try {
            await mutate(`/api/repositories/${repoId}/scan`);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Scanning…" : "Rescan"}
      </button>
      ) : null}

      {/* Activity / Notification Bell */}
      <button
        className="btn btn-ghost"
        onClick={onToggleNotifications}
        title="Activity stream & audit notifications"
        aria-label="Activity stream"
        style={{ position: "relative", padding: "6px 9px" }}
      >
        <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M8 1.5a4 4 0 0 0-4 4v3.5l-1.5 2h11L12 9V5.5a4 4 0 0 0-4-4z" />
          <path d="M6.5 13.5a1.5 1.5 0 0 0 3 0" />
        </svg>
        {recentCount > 0 ? (
          <span
            style={{
              position: "absolute",
              top: 3,
              right: 3,
              width: 7,
              height: 7,
              borderRadius: "50%",
              background: "var(--cs-accent)",
            }}
          />
        ) : null}
      </button>

      <span className={online ? "conn conn-on" : "conn conn-off"} title={online ? `Server connected · version ${health?.version ?? "?"}` : `Server offline${healthError ? ": " + healthError : ""}`} role="status">
        <span className="conn-dot" aria-hidden="true" />
        {online ? "Connected" : "Offline"}
      </span>

      <div className="profile">
        <button className="avatar" aria-haspopup="true" aria-expanded={profileOpen} onClick={() => setProfileOpen((o) => !o)} aria-label="Account menu">
          {(user?.displayName || user?.username || "?").slice(0, 1).toUpperCase()}
        </button>
        {profileOpen && user ? (
          <div className="profile-menu" role="menu">
            <p>
              <strong>{user.displayName}</strong>
              <br />
              <span className="small muted">
                @{user.username} · {ROLE_LABEL[user.role]}
              </span>
            </p>
            <Link role="menuitem" to="/settings" onClick={() => setProfileOpen(false)} className="btn btn-small">
              Account &amp; security
            </Link>
            <button role="menuitem" className="btn btn-small btn-ghost" onClick={() => void signOut()}>
              Sign out
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}

// ---------------- Global Search Modal (Ctrl+K) ----------------
function GlobalSearchModal({ repoId, onClose }: { repoId: string | null; onClose: () => void }) {
  const [query, setQuery] = React.useState("");
  const findings = useApi<FindingsResponse>(repoId ? `/api/repositories/${repoId}/findings` : null);
  const inputRef = React.useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  React.useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const needle = query.trim().toLowerCase();
  const hits = React.useMemo(() => {
    if (!needle || !findings.data) return [];
    return findings.data.findings.filter(
      (f) =>
        f.algorithm.toLowerCase().includes(needle) ||
        f.file.toLowerCase().includes(needle) ||
        f.service?.name?.toLowerCase().includes(needle) ||
        f.role.value?.toLowerCase().includes(needle) ||
        f.risk.band.toLowerCase().includes(needle)
    ).slice(0, 8);
  }, [needle, findings.data]);

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Quick Search">
      <div className="modal-box" onClick={(e) => e.stopPropagation()} style={{ padding: 0 }}>
        <div style={{ display: "flex", alignItems: "center", padding: "14px 18px", borderBottom: "1px solid var(--cs-border)" }}>
          <svg viewBox="0 0 16 16" width="16" height="16" fill="none" stroke="var(--cs-muted)" strokeWidth="1.5" style={{ marginRight: 10 }}>
            <circle cx="7" cy="7" r="4.5" />
            <path d="M10.5 10.5 14 14" />
          </svg>
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search cryptographic algorithms, services, files or risk bands…"
            style={{ border: 0, outline: "none", width: "100%", fontSize: 15, background: "transparent", color: "var(--cs-text)" }}
          />
          <button className="btn btn-ghost btn-small" onClick={onClose}>ESC</button>
        </div>
        <div style={{ maxHeight: 380, overflowY: "auto", padding: "12px 16px" }}>
          {!needle ? (
            <div style={{ color: "var(--cs-muted)", fontSize: 13, padding: "12px 6px" }}>
              <p style={{ fontWeight: 600, marginBottom: 8, color: "var(--cs-text)" }}>Quick Navigation:</p>
              <div className="kv">
                <button className="btn btn-small" onClick={() => { navigate("/inventory"); onClose(); }}>Crypto Inventory</button>
                <button className="btn btn-small" onClick={() => { navigate("/planner"); onClose(); }}>Migration Planner</button>
                <button className="btn btn-small" onClick={() => { navigate("/verification"); onClose(); }}>Verification Center</button>
                <button className="btn btn-small" onClick={() => { navigate("/patches"); onClose(); }}>AI Patch Studio</button>
              </div>
            </div>
          ) : hits.length === 0 ? (
            <p className="muted" style={{ padding: 16 }}>No cryptographic findings match "{query}".</p>
          ) : (
            <ul className="list">
              {hits.map((h) => (
                <li
                  key={h.id}
                  style={{
                    padding: "8px 12px",
                    borderRadius: 8,
                    background: "rgba(254, 243, 199, 0.3)",
                    border: "1px solid var(--cs-border)",
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                  onClick={() => {
                    navigate(`/inventory?finding=${h.id}`);
                    onClose();
                  }}
                >
                  <div>
                    <strong>{h.algorithm}</strong> <span className="mono" style={{ fontSize: 11.5 }}>{h.file}:{h.line}</span>
                    <div style={{ fontSize: 12, color: "var(--cs-muted)" }}>{h.service?.name ?? "Service"} · {h.role.value ?? "Role"}</div>
                  </div>
                  <span className="badge badge-amber">{h.risk.band}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------- Notifications / Activity Stream Drawer ----------------
function NotificationsDrawer({ onClose }: { onClose: () => void }) {
  const audit = useApi<AuditList>("/api/audit?limit=15", 5000);
  const events = audit.data?.entries ?? [];

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} />
      <div className="drawer" role="dialog" aria-modal="true" aria-label="Activity Stream">
        <div className="drawer-head">
          <div>
            <strong>Recent Activity Stream</strong>
            <div style={{ fontSize: 12, color: "var(--cs-muted)" }}>Live backend audit ledger</div>
          </div>
          <button className="btn" onClick={onClose}>Close</button>
        </div>
        <div className="drawer-body">
          {events.length === 0 ? (
            <p className="muted">No activity events recorded yet.</p>
          ) : (
            <ul className="list">
              {events.slice(0, 15).map((e) => (
                <li
                  key={e.id}
                  style={{
                    padding: "10px 14px",
                    borderRadius: 9,
                    background: "var(--cs-surface-glass-card)",
                    border: "1px solid var(--cs-border)",
                    display: "grid",
                    gap: 4,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span className="mono" style={{ fontSize: 12, fontWeight: 700, color: "var(--cs-accent-strong)" }}>{e.action}</span>
                    <span style={{ fontSize: 11.5, color: "var(--cs-muted)" }}>{new Date(e.at).toLocaleTimeString()}</span>
                  </div>
                  <div style={{ fontSize: 13, color: "var(--cs-text)" }}>{e.detail}</div>
                  <div style={{ fontSize: 11.5, color: "var(--cs-muted)" }}>Actor: <strong>{e.actor}</strong></div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  );
}
