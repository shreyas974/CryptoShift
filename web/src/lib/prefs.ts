import { useEffect, useState } from "react";

export type Prefs = {
  theme: "dark" | "light";
  reduceTransparency: boolean;
  highContrast: boolean;
  reduceMotion: boolean;
};

const KEY = "cryptoshift.prefs.v1";
const mq = (q: string) => (typeof window !== "undefined" && window.matchMedia ? window.matchMedia(q).matches : false);

export function defaultPrefs(): Prefs {
  return {
    theme: mq("(prefers-color-scheme: light)") ? "light" : "dark",
    reduceTransparency: mq("(prefers-reduced-transparency: reduce)"),
    highContrast: mq("(prefers-contrast: more)"),
    reduceMotion: mq("(prefers-reduced-motion: reduce)"),
  };
}

function load(): Prefs {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...defaultPrefs(), ...(JSON.parse(raw) as Partial<Prefs>) } : defaultPrefs();
  } catch {
    return defaultPrefs(); // storage blocked (private window, policy): fall back to system preferences
  }
}

/** Per-viewer display preferences (localStorage); applied as classes on <html>. */
export function usePrefs(): [Prefs, (p: Partial<Prefs>) => void] {
  const [prefs, setPrefs] = useState<Prefs>(load);
  useEffect(() => {
    const el = document.documentElement;
    el.dataset.theme = prefs.theme;
    el.classList.toggle("reduce-transparency", prefs.reduceTransparency);
    el.classList.toggle("high-contrast", prefs.highContrast);
    el.classList.toggle("reduce-motion", prefs.reduceMotion);
    try {
      localStorage.setItem(KEY, JSON.stringify(prefs));
    } catch {
      /* ignore: preferences then last only for this page view */
    }
  }, [prefs]);
  return [prefs, (p) => setPrefs((old) => ({ ...old, ...p }))];
}
