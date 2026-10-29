/**
 * Automated WCAG contrast check (design.md §2–3). Reads the real tokens from src/styles/index.css, composites
 * scrim + glass over the background's brightest and darkest colours (conservative: brighter / darker than the canvas
 * ever paints), and fails below AA: 4.5:1 for body text, 3:1 for large text and UI parts.
 */
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const css = readFileSync(`${process.cwd()}/src/styles/index.css`, "utf8"); // vitest runs from web/

function block(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`);
  const body = css.slice(start, css.indexOf("}", start));
  return Object.fromEntries([...body.matchAll(/--([\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
}

type RGBA = [number, number, number, number];
function parse(c: string): RGBA {
  const hex = /^#([0-9a-f]{6})$/i.exec(c);
  if (hex) {
    const n = parseInt(hex[1], 16);
    return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 1];
  }
  const m = /rgba?\(([^)]+)\)/.exec(c);
  if (!m) throw new Error(`unparsed colour ${c}`);
  const [r, g, b, a = "1"] = m[1].split(",").map((s) => s.trim());
  return [Number(r), Number(g), Number(b), Number(a)];
}
const over = ([r, g, b, a]: RGBA, [R, G, B]: RGBA): RGBA => [
  r * a + R * (1 - a),
  g * a + G * (1 - a),
  b * a + B * (1 - a),
  1,
];
const lum = ([r, g, b]: RGBA) => {
  const f = (v: number) => {
    const s = v / 255;
    return s <= 0.04045 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
const ratio = (a: RGBA, b: RGBA) => {
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
};

const dark = block(":root");
const light = { ...dark, ...block('[data-theme="light"]') };
const BACKGROUND = {
  dark: { brightest: "#f97316", darkest: "#07060c" }, // orange glow at FULL strength (canvas uses <= 30%)
  light: { brightest: "#ffffff", darkest: "#b9a3ec" }, // conservative extremes for the light canvas
};
const TEXT = ["text", "muted", "accent", "accent-2", "ok", "warn", "bad", "sim", "info", "neutral"];
const SURFACES = ["glass", "glass-strong", "surface-solid"];

describe("text on every glass surface meets WCAG AA over the background extremes", () => {
  for (const [theme, tokens] of [
    ["dark", dark],
    ["light", light],
  ] as const) {
    for (const region of ["brightest", "darkest"] as const) {
      for (const surface of SURFACES) {
        it(`${theme} / ${surface} / ${region} background`, () => {
          const bg = parse(BACKGROUND[theme][region]);
          const behind = over(parse(tokens["scrim"]), bg);
          const panel = over(parse(tokens[surface]), behind);
          for (const t of TEXT) {
            const r = ratio(parse(tokens[t]), panel);
            expect(r, `${t} on ${surface}: ${r.toFixed(2)}:1`).toBeGreaterThanOrEqual(4.5);
          }
        });
      }
    }
  }
});

it("control: the check really fails a low-contrast colour (the kit grey axe flagged)", () => {
  const panel = over(parse(dark["glass"]), over(parse(dark["scrim"]), parse(BACKGROUND.dark.darkest)));
  expect(ratio(parse("#6e6e6e"), panel)).toBeLessThan(4.5);
});
