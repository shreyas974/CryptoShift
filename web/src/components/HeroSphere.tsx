import { useEffect, useRef } from "react";

/**
 * Decorative hero illustration, drawn in code: a glowing lattice sphere (latitude and longitude lines in slow
 * rotation) inside three tilted orbits. Each orbit carries `nodes` small points: one per service in the real plan,
 * coloured by its migration state (READY orange, APPROVED green, others violet), so the picture is an honest mood
 * piece for the data, never evidence. Pauses offscreen and when the tab is hidden; still under reduced motion.
 */
export function HeroSphere({
  theme,
  reduceMotion,
  nodes,
}: {
  theme: "dark" | "light";
  reduceMotion: boolean;
  nodes: { id: string; state: string }[];
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const key = nodes.map((n) => `${n.id}:${n.state}`).join(",");
  useEffect(() => {
    const c = ref.current;
    const x = c?.getContext("2d");
    if (!c || !x) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const dark = theme === "dark";
    let S = 0;
    let t = 0;
    let last = 0;
    let raf = 0;
    let visible = true;
    const pts = key ? key.split(",").map((s) => s.split(":")[1] ?? "") : [];
    const size = () => {
      S = c.width = c.height = Math.round(c.getBoundingClientRect().width * dpr) || 400;
    };
    const tone = (state: string) =>
      state === "APPROVED" ? "94,224,138" : state === "READY" ? "253,186,116" : dark ? "196,176,255" : "98,39,201";
    const draw = () => {
      x.clearRect(0, 0, S, S);
      const cx = S / 2;
      const cy = S / 2;
      const R = S * 0.3;
      // halo
      const halo = x.createRadialGradient(cx, cy, R * 0.6, cx, cy, R * 1.65);
      halo.addColorStop(0, dark ? "rgba(167,139,250,.35)" : "rgba(124,58,237,.18)");
      halo.addColorStop(0.55, dark ? "rgba(249,115,22,.10)" : "rgba(249,115,22,.08)");
      halo.addColorStop(1, "rgba(0,0,0,0)");
      x.fillStyle = halo;
      x.fillRect(0, 0, S, S);
      // body
      const body = x.createRadialGradient(cx - R * 0.35, cy - R * 0.4, R * 0.05, cx, cy, R);
      body.addColorStop(0, dark ? "#efe7ff" : "#ffffff");
      body.addColorStop(0.25, dark ? "#8b5cf6" : "#c4b0ff");
      body.addColorStop(0.75, dark ? "#2a1150" : "#7c3aed");
      body.addColorStop(1, dark ? "#7a3418" : "#f97316");
      x.fillStyle = body;
      x.beginPath();
      x.arc(cx, cy, R, 0, Math.PI * 2);
      x.fill();
      // lattice: longitudes rotate, latitudes fixed
      x.save();
      x.beginPath();
      x.arc(cx, cy, R, 0, Math.PI * 2);
      x.clip();
      x.lineWidth = dpr;
      x.strokeStyle = dark ? "rgba(255,255,255,.22)" : "rgba(255,255,255,.45)";
      for (let i = 0; i < 9; i++) {
        const a = ((i / 9) * Math.PI + t * 0.006) % Math.PI;
        const rx = Math.abs(Math.cos(a)) * R;
        x.beginPath();
        x.ellipse(cx, cy, Math.max(rx, 0.5), R, 0, 0, Math.PI * 2);
        x.stroke();
      }
      for (let k = -3; k <= 3; k++) {
        const yy = cy + (k / 4) * R;
        const rr = Math.sqrt(Math.max(R * R - (yy - cy) ** 2, 0));
        x.beginPath();
        x.ellipse(cx, yy, rr, rr * 0.18, 0, 0, Math.PI * 2);
        x.stroke();
      }
      x.restore();
      // orbits with service nodes
      const orbits = [
        [1.32, 0.34, -0.42],
        [1.52, 0.26, 0.38],
        [1.72, 0.2, -0.1],
      ] as const;
      orbits.forEach(([k, flat, tilt], oi) => {
        x.save();
        x.translate(cx, cy);
        x.rotate(tilt);
        x.strokeStyle = dark ? "rgba(220,205,255,.28)" : "rgba(98,39,201,.3)";
        x.lineWidth = dpr;
        x.beginPath();
        x.ellipse(0, 0, R * k, R * k * flat, 0, 0, Math.PI * 2);
        x.stroke();
        const mine = pts.filter((_, i) => i % 3 === oi);
        mine.forEach((state, j) => {
          const a = (j / Math.max(mine.length, 1)) * Math.PI * 2 + t * 0.01 * (oi % 2 ? -1 : 1) + oi;
          const px = Math.cos(a) * R * k;
          const py = Math.sin(a) * R * k * flat;
          const g = x.createRadialGradient(px, py, 0, px, py, 10 * dpr);
          g.addColorStop(0, `rgba(${tone(state)},.9)`);
          g.addColorStop(1, `rgba(${tone(state)},0)`);
          x.fillStyle = g;
          x.beginPath();
          x.arc(px, py, 10 * dpr, 0, Math.PI * 2);
          x.fill();
          x.fillStyle = `rgb(${tone(state)})`;
          x.beginPath();
          x.arc(px, py, 2.6 * dpr, 0, Math.PI * 2);
          x.fill();
        });
        x.restore();
      });
    };
    const loop = (ts: number) => {
      if (visible && !document.hidden && ts - last > 33) {
        t += 1;
        last = ts;
        draw();
      }
      raf = requestAnimationFrame(loop);
    };
    size();
    draw();
    const io =
      typeof IntersectionObserver !== "undefined"
        ? new IntersectionObserver(([e]) => {
            visible = Boolean(e?.isIntersecting);
          })
        : null;
    io?.observe(c);
    const onResize = () => {
      size();
      draw();
    };
    window.addEventListener("resize", onResize);
    if (!reduceMotion) raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      io?.disconnect();
      window.removeEventListener("resize", onResize);
    };
  }, [theme, reduceMotion, key]);
  return <canvas ref={ref} className="hero-sphere" aria-hidden="true" data-testid="hero-sphere" />;
}
