# Web app v2 assets

| Asset | Source | Licence | Notes |
|---|---|---|---|
| "Quantum lab" background | `web/src/components/Background.tsx`, drawn procedurally on a canvas | project code | No external images. Pauses when the tab is hidden; static under reduced motion; hidden under reduced transparency |
| Hero sphere | `web/src/components/HeroSphere.tsx`, drawn on a canvas | project code | Lattice sphere with orbits; one point per real service, coloured by state; decorative, not evidence |
| Fig. 1 "Sorting line" | `web/src/components/PipelineFigure.tsx`, `components/pipeline/` | project code | Built with the anatomy skill; geometry computed in `geometry.ts`; driven by real plan and approval data |
| Anatomy isometric kit | `web/src/components/iso/` (vendored from wheresryan22/anatomy at commit 1482e84, verified by git blob SHA-1) | MIT (`LICENSE-anatomy-MIT.txt`) | Kept byte-identical; excluded from ESLint |
| Fonts | `@fontsource/inter`, `@fontsource/jetbrains-mono` (bundled, no Google Fonts call) | OFL-1.1 | Served from `'self'` per CSP |
| Screenshots | `docs/webapp/screens/*.png` | project | Captured by Playwright from the isolated test backend; no keys, no personal data |

The v2.1 style takes its direction from a reference site chosen by the owner, but no image, logo, text or code was
taken from it. No web background images, stock art or CDN assets are used. Everything is served from `'self'`.
