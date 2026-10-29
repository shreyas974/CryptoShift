/** Page registry: id (hash route), menu group, icon, label and one-line description used in menus and page heads. */
export const GROUPS = ["Platform", "Discover", "Plan & verify", "Pipelines", "Trust", "Admin"] as const;
export type Group = (typeof GROUPS)[number];

type PageDef = { id: string; group: Group; icon: string; label: string; desc: string; minRole?: string };

const DEFS = [
  {
    id: "overview",
    group: "Platform",
    icon: "◉",
    label: "Overview",
    desc: "Pipeline status, Fig. 1 and the latest activity",
  },
  {
    id: "sources",
    group: "Platform",
    icon: "▤",
    label: "Data & evidence",
    desc: "Every report file, who produced it and its hash",
  },
  {
    id: "activity",
    group: "Platform",
    icon: "🔔",
    label: "Activity",
    desc: "Sign-ins, runs, approvals and changes, newest first",
  },
  {
    id: "inventory",
    group: "Discover",
    icon: "▦",
    label: "Inventory",
    desc: "Cryptography findings with purpose, confidence and HOLD",
  },
  {
    id: "dependencies",
    group: "Discover",
    icon: "⎔",
    label: "Dependencies",
    desc: "Service graph: observed, declared and inferred edges",
  },
  {
    id: "evaluation",
    group: "Discover",
    icon: "◎",
    label: "Detection evaluation",
    desc: "How well the detector does on separate test sets",
  },
  {
    id: "plan",
    group: "Plan & verify",
    icon: "▭",
    label: "Migration plan",
    desc: "Waves, schedule objective and scheduler comparison",
  },
  {
    id: "verification",
    group: "Plan & verify",
    icon: "✓",
    label: "Verification",
    desc: "Gates, compatibility, handshake traces and overhead",
  },
  {
    id: "approval",
    group: "Plan & verify",
    icon: "✎",
    label: "Approval & rollback",
    desc: "Human approval of READY steps and the rollback rehearsal",
  },
  {
    id: "runs",
    group: "Pipelines",
    icon: "⇪",
    label: "Datasets & runs",
    desc: "Upload your own dataset, pick a pipeline and get its outputs",
  },
  {
    id: "reports",
    group: "Pipelines",
    icon: "⎙",
    label: "Reports",
    desc: "A printable migration report you can save as PDF",
  },
  {
    id: "claims",
    group: "Trust",
    icon: "⚖",
    label: "Claims & limits",
    desc: "What every number means and what we do not claim",
  },
  {
    id: "ml",
    group: "Trust",
    icon: "✧",
    label: "ML & AI",
    desc: "Classifier results and the assistant, with its mode shown",
  },
  {
    id: "audit",
    group: "Trust",
    icon: "⛓",
    label: "Audit log",
    desc: "Hash-chained record of every change, with a tamper check",
  },
  {
    id: "users",
    group: "Admin",
    icon: "👥",
    label: "Users & roles",
    desc: "Add people, change roles and turn accounts off",
    minRole: "approver",
  },
  { id: "settings", group: "Admin", icon: "⚙", label: "Settings", desc: "Data mode, scan roots and cloud options" },
] as const satisfies readonly PageDef[];

export type PageId = (typeof DEFS)[number]["id"];
export const PAGES: readonly (PageDef & { id: PageId })[] = DEFS;

export function pageFromHash(): PageId {
  const h = window.location.hash.replace(/^#\/?/, "").split("?")[0] ?? "";
  return (PAGES.find((p) => p.id === h)?.id ?? "overview") as PageId;
}
