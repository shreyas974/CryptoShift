import * as React from "react";
import { api, ApiError, setCsrf } from "../api/client";
import type { Role, User } from "../api/types";

const RANK: Record<Role, number> = { viewer: 0, engineer: 1, reviewer: 2, admin: 3 };
export const ROLE_LABEL: Record<Role, string> = { viewer: "Viewer", engineer: "Engineer", reviewer: "Reviewer", admin: "Administrator" };
export const ROLE_CAN: Record<Role, string> = {
  viewer: "Read findings, plans, verification results and the audit log",
  engineer: "Viewer rights, plus scan, propose and run verification",
  reviewer: "Engineer rights, plus approve, release and roll back",
  admin: "Reviewer rights, plus manage accounts and reset demo state",
};

type Status = "loading" | "setup" | "signedOut" | "signedIn" | "offline";
interface AuthValue {
  status: Status;
  user: User | null;
  passwordMin: number;
  can: (role: Role) => boolean;
  signIn: (username: string, password: string) => Promise<void>;
  setup: (input: { token: string; username: string; displayName: string; password: string }) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = React.createContext<AuthValue | null>(null);
export function useAuth() {
  const value = React.useContext(AuthContext);
  if (!value) throw new Error("useAuth outside AuthProvider");
  return value;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<Status>("loading");
  const [user, setUser] = React.useState<User | null>(null);
  const [passwordMin, setPasswordMin] = React.useState(15);

  const refresh = React.useCallback(async () => {
    try {
      const s = await api<{ setupRequired: boolean; signedIn: boolean; passwordMin: number }>("/api/auth/status");
      setPasswordMin(s.passwordMin);
      if (s.setupRequired) return setStatus("setup");
      if (!s.signedIn) return setStatus("signedOut");
      const session = await api<{ user: User; csrf: string }>("/api/auth/session");
      setCsrf(session.csrf);
      setUser(session.user);
      setStatus("signedIn");
    } catch (e) {
      setStatus((e as ApiError).status === 0 ? "offline" : "signedOut");
    }
  }, []);

  React.useEffect(() => {
    void refresh();
    const expired = () => {
      setUser(null);
      setStatus("signedOut");
    };
    window.addEventListener("cryptoshift:unauthorized", expired);
    return () => window.removeEventListener("cryptoshift:unauthorized", expired);
  }, [refresh]);

  const accept = (r: { user: User; csrf: string }) => {
    setCsrf(r.csrf);
    setUser(r.user);
    setStatus("signedIn");
  };

  const value: AuthValue = {
    status,
    user,
    passwordMin,
    can: (role) => Boolean(user) && RANK[user!.role] >= RANK[role],
    signIn: async (username, password) => accept(await api("/api/auth/login", { method: "POST", body: { username, password } })),
    setup: async (input) => accept(await api("/api/auth/setup", { method: "POST", body: input })),
    signOut: async () => {
      try {
        await api("/api/auth/logout", { method: "POST" });
      } finally {
        setCsrf("");
        setUser(null);
        setStatus("signedOut");
      }
    },
    refresh,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** Renders the app only for a signed-in user; otherwise the setup or sign-in screen. */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  if (status === "loading") return <AuthFrame><p className="auth-muted" role="status">Checking your session…</p></AuthFrame>;
  if (status === "offline") return <OfflineScreen />;
  if (status === "setup") return <SetupScreen />;
  if (status === "signedOut") return <SignInScreen />;
  return <>{children}</>;
}

function AuthFrame({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) {
  return (
    <div className="auth-page">
      <section className="auth-story" aria-hidden="true">
        <div className="auth-brand">
          <span className="brand-mark">
            <svg viewBox="0 0 24 24">
              <path d="M12 2.5 20.5 7.4v9.2L12 21.5 3.5 16.6V7.4z" />
              <path d="M8.5 12.6 11 15l4.5-5" />
            </svg>
          </span>
          CryptoShift
        </div>
        <p className="auth-tagline">Post-quantum migration you can prove.</p>
        <ol className="auth-rail">
          <li><span>01</span> Find every RSA, ECC and SHA-1 use, with file and line</li>
          <li><span>02</span> Plan migration waves around service dependencies</li>
          <li><span>03</span> Test each candidate patch for real before anyone can approve it</li>
          <li><span>04</span> A second person signs off; every step lands in a tamper-evident log</li>
        </ol>
        <p className="auth-foot">NIST IR 8547: quantum-vulnerable public-key algorithms are deprecated after 2030 and disallowed after 2035.</p>
      </section>
      <main className={wide ? "auth-panel auth-panel-wide" : "auth-panel"}>{children}</main>
    </div>
  );
}

function ErrorLine({ error }: { error: string | null }) {
  return error ? (
    <p className="auth-error" role="alert">
      {error}
    </p>
  ) : null;
}

function SignInScreen() {
  const { signIn } = useAuth();
  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  return (
    <AuthFrame>
      <h1>Sign in</h1>
      <p className="auth-muted">Use the account your CryptoShift administrator created for you.</p>
      <form
        className="auth-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError(null);
          try {
            await signIn(username, password);
          } catch (err) {
            setError((err as ApiError).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Username
          <input autoComplete="username" autoCapitalize="none" spellCheck={false} required value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
        </label>
        <label>
          Password
          <input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <ErrorLine error={error} />
        <button className="btn btn-primary auth-submit" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="auth-hint">Forgot your password? Ask an administrator to reset your account. Five wrong attempts lock sign-in for 15 minutes.</p>
    </AuthFrame>
  );
}

function SetupScreen() {
  const { setup, passwordMin } = useAuth();
  const [form, setForm] = React.useState({ token: "", username: "", displayName: "", password: "", confirm: "" });
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });
  const length = [...form.password].length;
  const mismatch = form.confirm.length > 0 && form.confirm !== form.password;
  return (
    <AuthFrame wide>
      <h1>Set up CryptoShift</h1>
      <p className="auth-muted">
        Create the first administrator. The <strong>setup code</strong> was printed in the terminal where the server started (and saved to <code>backend/data/setup-token</code>). It works once.
      </p>
      <form
        className="auth-form"
        onSubmit={async (e) => {
          e.preventDefault();
          if (mismatch) return setError("The two passwords do not match");
          setBusy(true);
          setError(null);
          try {
            await setup({ token: form.token, username: form.username, displayName: form.displayName, password: form.password });
          } catch (err) {
            setError((err as ApiError).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <label>
          Setup code
          <input required autoComplete="one-time-code" spellCheck={false} value={form.token} onChange={set("token")} className="mono" autoFocus />
        </label>
        <div className="auth-row">
          <label>
            Username
            <input required autoComplete="username" autoCapitalize="none" spellCheck={false} pattern="[a-z0-9][a-z0-9._\-]{2,31}" title="3–32 lowercase letters, digits, dot, dash or underscore" value={form.username} onChange={set("username")} />
          </label>
          <label>
            Display name <span className="auth-optional">shown on approvals</span>
            <input autoComplete="name" value={form.displayName} onChange={set("displayName")} />
          </label>
        </div>
        <label>
          Password
          <input type="password" required autoComplete="new-password" minLength={passwordMin} value={form.password} onChange={set("password")} aria-describedby="pw-help" />
        </label>
        <div className="auth-meter" aria-hidden="true">
          <span style={{ width: `${Math.min(100, (length / passwordMin) * 100)}%` }} data-ok={length >= passwordMin ? "" : undefined} />
        </div>
        <p id="pw-help" className="auth-hint">
          {length >= passwordMin ? "Length is good." : `At least ${passwordMin} characters: ${passwordMin - length} to go. A few unrelated words are easy to remember and hard to guess.`}
        </p>
        <label>
          Confirm password
          <input type="password" required autoComplete="new-password" value={form.confirm} onChange={set("confirm")} aria-invalid={mismatch} />
        </label>
        {mismatch ? <p className="auth-error">The two passwords do not match</p> : null}
        <ErrorLine error={error} />
        <button className="btn btn-primary auth-submit" disabled={busy}>
          {busy ? "Creating account…" : "Create administrator and continue"}
        </button>
      </form>
    </AuthFrame>
  );
}

function OfflineScreen() {
  const { refresh } = useAuth();
  return (
    <AuthFrame>
      <h1>Server unreachable</h1>
      <p className="auth-muted">The CryptoShift server is not responding. Start it with <code>npm start</code> in <code>cryptoshift_app</code>, then try again.</p>
      <button className="btn btn-primary auth-submit" onClick={() => void refresh()}>
        Try again
      </button>
    </AuthFrame>
  );
}
