import * as React from "react";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

// The session's CSRF token. The session itself lives in an HttpOnly cookie the page cannot read;
// this token is handed out on sign-in and must accompany every POST.
let csrfToken = "";
export const setCsrf = (token: string) => {
  csrfToken = token;
};

export async function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  const method = init?.method ?? "GET";
  let response: Response;
  try {
    response = await fetch(BASE + path, {
      method,
      credentials: "same-origin",
      headers: method === "POST" ? { "content-type": "application/json", "x-csrf-token": csrfToken } : undefined,
      body: method === "POST" ? JSON.stringify(init?.body ?? {}) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the CryptoShift server. Check that it is running.", 0);
  }
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new ApiError(`The server returned an unexpected response (HTTP ${response.status})`, response.status);
  }
  const message = (data as { error?: string } | null)?.error;
  if (response.status === 401 && !path.startsWith("/api/auth/")) window.dispatchEvent(new Event("cryptoshift:unauthorized"));
  if (!response.ok) throw new ApiError(message ?? `Request failed (HTTP ${response.status})`, response.status);
  return data as T;
}

/** Fetch a JSON endpoint and save it as a file (used for the CBOM export). */
export async function downloadJson(path: string, filename: string) {
  const data = await api<unknown>(path);
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: filename });
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export interface Resource<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => void;
}

/** Fetch a resource; refetches when `path` changes or when any API mutation happens. */
export function useApi<T>(path: string | null, pollMs?: number): Resource<T> {
  const [state, setState] = React.useState<{ data: T | null; error: ApiError | null; loading: boolean }>({ data: null, error: null, loading: Boolean(path) });
  const [tick, setTick] = React.useState(0);
  const reload = React.useCallback(() => setTick((t) => t + 1), []);
  React.useEffect(() => {
    const handler = () => reload();
    window.addEventListener("cryptoshift:mutated", handler);
    return () => window.removeEventListener("cryptoshift:mutated", handler);
  }, [reload]);
  React.useEffect(() => {
    if (!path) {
      setState({ data: null, error: null, loading: false });
      return;
    }
    let live = true;
    setState((s) => ({ ...s, loading: true }));
    api<T>(path)
      .then((data) => live && setState({ data, error: null, loading: false }))
      .catch((error: ApiError) => live && setState((s) => ({ data: s.data, error, loading: false })));
    return () => {
      live = false;
    };
  }, [path, tick]);
  React.useEffect(() => {
    if (!pollMs || !path) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") reload(); // no background polling in hidden tabs
    }, pollMs);
    return () => window.clearInterval(timer);
  }, [pollMs, path, reload]);
  return { ...state, reload };
}

/** Run a mutation and tell every mounted resource to refresh. */
export async function mutate<T>(path: string, body: unknown = {}): Promise<T> {
  const result = await api<T>(path, { method: "POST", body });
  window.dispatchEvent(new Event("cryptoshift:mutated"));
  return result;
}
