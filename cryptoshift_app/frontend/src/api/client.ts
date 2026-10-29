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

export async function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  let response: Response;
  try {
    response = await fetch(BASE + path, {
      method: init?.method ?? "GET",
      headers: init?.body !== undefined ? { "content-type": "application/json" } : undefined,
      body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the CryptoShift backend. Is it running on port 8787?", 0);
  }
  const text = await response.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    throw new ApiError(`Backend returned a non-JSON response (HTTP ${response.status})`, response.status);
  }
  const message = (data as { error?: string } | null)?.error;
  if (!response.ok) throw new ApiError(message ?? (response.status >= 500 ? `Cannot reach the CryptoShift backend (HTTP ${response.status}). Is it running on port 8787?` : `HTTP ${response.status}`), response.status);
  return data as T;
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
    const timer = window.setInterval(reload, pollMs);
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
