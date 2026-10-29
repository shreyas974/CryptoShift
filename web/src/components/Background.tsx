import { useEffect, useRef } from "react";

/**
 * Decorative, ORIGINAL procedural background (never evidence): a deep plum field with two slow purple and orange
 * glows and a faint dot grid. Fixed seed; capped at 30 fps; paused when the tab is hidden; one static frame under
 * reduced motion. No images, no logos, no network. Glow strength stays <= 30% (the contrast test assumes this).
 */
export function Background({ theme, reduceMotion }: { theme: "dark" | "light"; reduceMotion: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const c = ref.current;
    const x = c?.getContext("2d");
    if (!c || !x) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0;
    let h = 0;
    let t = 0;
    let last = 0;
    let raf = 0;
    const dark = theme === "dark";
    const size = () => {
      w = c.width = window.innerWidth * dpr;
      h = c.height = window.innerHeight * dpr;
    };
    const glow = (px: number, py: number, r: number, rgb: string, a: number) => {
      const g = x.createRadialGradient(px, py, 0, px, py, r);
      g.addColorStop(0, `rgba(${rgb},${a})`);
      g.addColorStop(1, `rgba(${rgb},0)`);
      x.fillStyle = g;
      x.fillRect(0, 0, w, h);
    };
    const draw = () => {
      x.fillStyle = dark ? "#07060c" : "#faf8ff";
      x.fillRect(0, 0, w, h);
      const R = Math.max(w, h);
      glow(w * (0.12 + Math.sin(t * 0.004) * 0.03), h * 0.08, R * 0.55, "124,58,237", dark ? 0.3 : 0.12);
      glow(w * (0.92 + Math.cos(t * 0.003) * 0.03), h * 0.95, R * 0.5, "249,115,22", dark ? 0.2 : 0.1);
      glow(w * 0.6, h * 0.5, R * 0.35, "236,72,153", dark ? 0.06 : 0.04);
      const s = 34 * dpr;
      x.fillStyle = dark ? "rgba(220,205,255,.07)" : "rgba(40,20,80,.07)";
      for (let yy = s / 2; yy < h; yy += s)
        for (let xx = s / 2; xx < w; xx += s) x.fillRect(xx, yy, 1.2 * dpr, 1.2 * dpr);
    };
    const loop = (ts: number) => {
      if (!document.hidden && ts - last > 33) {
        t += 1;
        last = ts;
        draw();
      }
      raf = requestAnimationFrame(loop);
    };
    const onResize = () => {
      size();
      draw();
    };
    size();
    draw();
    if (!reduceMotion) raf = requestAnimationFrame(loop);
    window.addEventListener("resize", onResize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, [theme, reduceMotion]);
  return (
    <>
      <canvas ref={ref} className="bg-canvas" aria-hidden="true" data-testid="quantum-background" />
      <div className="bg-scrim" aria-hidden="true" />
    </>
  );
}
