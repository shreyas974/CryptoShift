import { useQuery } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { api, type Me } from "../api/client";
import { GROUPS, PAGES, type PageId } from "../lib/pages";
import type { Prefs } from "../lib/prefs";
import { plainText } from "../lib/status";

/** Close a popover on Escape or a click outside `ref`. */
function useDismiss(open: boolean, close: () => void, ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) close();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onDown);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onDown);
    };
  }, [open, close, ref]);
}

function Menu({
  label,
  current,
  children,
  align = "left",
  buttonClass = "menu-btn",
  buttonContent,
}: {
  label: string;
  current?: boolean;
  children: (close: () => void) => ReactNode;
  align?: "left" | "right";
  buttonClass?: string;
  buttonContent?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const id = useId();
  const close = () => setOpen(false);
  useDismiss(open, close, ref);
  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className={`${buttonClass} ${current ? "is-current" : ""}`}
        aria-expanded={open}
        aria-controls={id}
        aria-label={buttonContent ? label : undefined}
        onClick={() => setOpen((o) => !o)}
      >
        {buttonContent ?? (
          <>
            {label}
            <span aria-hidden="true" className="text-xs">
              ▾
            </span>
          </>
        )}
      </button>
      {open && (
        <div id={id} className={`menu-panel ${align === "right" ? "align-right" : ""}`}>
          {children(close)}
        </div>
      )}
    </div>
  );
}

const SEEN_KEY = "cryptoshift.activity.seen";
function readSeen(): number {
  try {
    return Number(localStorage.getItem(SEEN_KEY) ?? 0) || 0;
  } catch {
    return 0;
  }
}

function Bell() {
  const q = useQuery({ queryKey: ["activity", 8], queryFn: () => api.activity(8), refetchInterval: 30_000 });
  const [seen, setSeen] = useState(readSeen);
  const items = q.data?.items ?? [];
  const unread = items.filter((i) => i.id > seen).length;
  const markSeen = () => {
    const latest = q.data?.latest_id ?? 0;
    setSeen(latest);
    try {
      localStorage.setItem(SEEN_KEY, String(latest));
    } catch {
      /* storage blocked: the count just resets next visit */
    }
  };
  return (
    <Menu
      label={unread ? `Activity, ${unread} new` : "Activity"}
      align="right"
      buttonClass="icon-btn"
      buttonContent={
        <>
          <span aria-hidden="true">🔔</span>
          {unread > 0 && (
            <span className="bell-dot" aria-hidden="true">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </>
      }
    >
      {(close) => (
        <div className="w-[min(380px,86vw)]">
          <div className="flex items-center gap-2 px-2 pt-1 pb-2">
            <strong>Activity</strong>
            <span className="flex-1" />
            <button type="button" className="arrow-link text-sm" onClick={markSeen}>
              Mark all read
            </button>
          </div>
          <ul className="news-list">
            {items.map((i) => (
              <li key={i.id} className="px-2 py-2 text-sm" style={{ borderBottom: "1px solid var(--edge-lo)" }}>
                <div className={i.id > seen ? "font-semibold" : ""}>{plainText(i.title, 120)}</div>
                <div className="t-muted text-xs">{i.ts.replace("T", " ").slice(0, 19)}</div>
              </li>
            ))}
            {!items.length && <li className="t-muted p-2 text-sm">Nothing yet.</li>}
          </ul>
          <a
            className="arrow-link mt-2 inline-flex px-2 pb-1"
            href="#/activity"
            onClick={() => {
              markSeen();
              close();
            }}
          >
            View all activity
          </a>
        </div>
      )}
    </Menu>
  );
}

export function TopBar({
  me,
  page,
  prefs,
  setPrefs,
  palette,
  dataMode,
  cloudAi,
  onSignOut,
}: {
  me: Me;
  page: PageId;
  prefs: Prefs;
  setPrefs: (p: Partial<Prefs>) => void;
  palette: ReactNode;
  dataMode: string;
  cloudAi: string;
  onSignOut: () => void;
}) {
  const toggle = (label: string, on: boolean, flip: () => void) => (
    <button type="button" className="menu-item w-full text-left" aria-pressed={on} onClick={flip}>
      <span className="mi-icon" aria-hidden="true">
        {on ? "◉" : "○"}
      </span>
      <span>{label}</span>
      <span className="mi-desc">{on ? "On" : "Off"}</span>
    </button>
  );
  return (
    <header className="topbar">
      <div className="container flex items-center gap-2 py-2">
        <a href="#/overview" className="brand mr-3">
          <span className="brand-mark" aria-hidden="true" />
          CryptoShift
        </a>
        <nav aria-label="Main navigation" className="hidden items-center gap-0.5 whitespace-nowrap xl:flex">
          {GROUPS.map((g) => {
            const pages = PAGES.filter((p) => p.group === g && (!p.minRole || roleAtLeast(me.role, p.minRole)));
            return (
              <Menu key={g} label={g} current={pages.some((p) => p.id === page)}>
                {(close) => (
                  <ul className="m-0 list-none p-0">
                    {pages.map((p) => (
                      <li key={p.id}>
                        <a
                          className="menu-item"
                          href={`#/${p.id}`}
                          aria-current={p.id === page ? "page" : undefined}
                          onClick={close}
                        >
                          <span className="mi-icon" aria-hidden="true">
                            {p.icon}
                          </span>
                          <span className="font-semibold">{p.label}</span>
                          <span className="mi-desc">{p.desc}</span>
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </Menu>
            );
          })}
        </nav>
        <nav aria-label="Main navigation (compact)" className="xl:hidden">
          <Menu label="Menu">
            {(close) => (
              <ul className="m-0 max-h-[70vh] list-none overflow-auto p-0">
                {PAGES.filter((p) => !p.minRole || roleAtLeast(me.role, p.minRole)).map((p) => (
                  <li key={p.id}>
                    <a
                      className="menu-item"
                      href={`#/${p.id}`}
                      aria-current={p.id === page ? "page" : undefined}
                      onClick={close}
                    >
                      <span className="mi-icon" aria-hidden="true">
                        {p.icon}
                      </span>
                      <span className="font-semibold">{p.label}</span>
                      <span className="mi-desc">{p.group}</span>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </Menu>
        </nav>
        <span className="flex-1" />
        {/* wrappers carry the responsive display: .badge sets its own display outside Tailwind's layers */}
        <span className="hidden 2xl:inline">
          <span className="badge t-info" title="Data mode">
            ● {dataMode} data
          </span>
        </span>
        <span className="hidden sm:inline">
          <span className={`badge ${cloudAi === "ON" ? "t-warn" : "t-ok"}`} title="Cloud AI">
            Cloud AI {cloudAi}
          </span>
        </span>
        <span className="hidden sm:inline">{palette}</span>
        <Bell />
        <Menu
          label={`Account: ${me.username}`}
          align="right"
          buttonClass="icon-btn"
          buttonContent={<span aria-hidden="true">{me.username.slice(0, 1).toUpperCase()}</span>}
        >
          {() => (
            <div className="w-[min(300px,86vw)]">
              <div className="px-2 pt-1 pb-2 text-sm">
                Signed in as <strong>{me.username}</strong> ({me.role})
                <div className="t-muted mt-1 text-xs">
                  {dataMode} data · Cloud AI {cloudAi}
                </div>
              </div>
              {toggle(prefs.theme === "dark" ? "Light theme" : "Dark theme", prefs.theme === "light", () =>
                setPrefs({ theme: prefs.theme === "dark" ? "light" : "dark" }),
              )}
              {toggle("Reduce transparency", prefs.reduceTransparency, () =>
                setPrefs({ reduceTransparency: !prefs.reduceTransparency }),
              )}
              {toggle("High contrast", prefs.highContrast, () => setPrefs({ highContrast: !prefs.highContrast }))}
              {toggle("Reduce motion", prefs.reduceMotion, () => setPrefs({ reduceMotion: !prefs.reduceMotion }))}
              <button type="button" className="btn mt-2 w-full" onClick={onSignOut}>
                Sign out
              </button>
            </div>
          )}
        </Menu>
        <a href="#/runs" className="btn btn-primary hidden whitespace-nowrap no-underline md:inline-flex">
          Run a pipeline
        </a>
      </div>
    </header>
  );
}

export function roleAtLeast(role: string, min: string): boolean {
  const rank = ["viewer", "analyst", "approver"];
  return rank.indexOf(role) >= rank.indexOf(min);
}

export function PageHead({ id }: { id: PageId }) {
  const p = PAGES.find((x) => x.id === id);
  if (!p) return null;
  return (
    <div className="page-head">
      <div className="eyebrow">{p.group}</div>
      <h1 className="h-section">{p.label}</h1>
      <p>{p.desc}</p>
    </div>
  );
}

export function Footer({ me }: { me: Me }) {
  return (
    <footer className="site-footer" aria-label="Site footer">
      <div className="container">
        <div className="grid grid-cols-2 gap-8 md:grid-cols-3 lg:grid-cols-[1.4fr_repeat(6,1fr)]">
          <div className="col-span-2 md:col-span-1">
            <a href="#/overview" className="brand">
              <span className="brand-mark" aria-hidden="true" />
              CryptoShift
            </a>
            <p className="t-muted mt-3 text-sm">
              Find, plan and verify a post-quantum cryptography migration. Local prototype for the PQC-01 hackathon.
            </p>
          </div>
          {GROUPS.filter((g) => g !== "Admin" || me.role === "approver").map((g) => (
            <div key={g}>
              <h3>{g}</h3>
              <ul>
                {PAGES.filter((p) => p.group === g && (!p.minRole || roleAtLeast(me.role, p.minRole))).map((p) => (
                  <li key={p.id}>
                    <a href={`#/${p.id}`}>{p.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div
          className="t-muted mt-10 flex flex-wrap gap-x-6 gap-y-2 pt-6 text-xs"
          style={{ borderTop: "1px solid var(--edge-lo)" }}
        >
          <span>Runs on 127.0.0.1 only · no data leaves this machine unless Cloud AI is ON</span>
          <span>Backgrounds and figures are decorative illustrations, not evidence</span>
          <span>QpiAI QCloud results are simulator runs</span>
        </div>
      </div>
    </footer>
  );
}
