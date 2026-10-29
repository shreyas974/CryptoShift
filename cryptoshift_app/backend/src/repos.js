// Repository registry. Each repository is scanned from a working copy under backend/data/workspaces,
// seeded from sample-repos/ on first start, so released patches and rollbacks change real files.
import fs from "node:fs";
import path from "node:path";
import { ROOT, WORKSPACES } from "./store.js";

const SOURCES = path.join(ROOT, "sample-repos");

export function ensureWorkspaces() {
  fs.mkdirSync(WORKSPACES, { recursive: true });
  for (const name of fs.readdirSync(SOURCES)) {
    const target = path.join(WORKSPACES, name);
    if (!fs.existsSync(target)) fs.cpSync(path.join(SOURCES, name), target, { recursive: true });
  }
}

export function resetWorkspace(id) {
  const target = path.join(WORKSPACES, id);
  fs.rmSync(target, { recursive: true, force: true });
  fs.cpSync(path.join(SOURCES, id), target, { recursive: true });
}

export const repoDir = (id) => path.join(WORKSPACES, id);

export function manifestOf(id) {
  const file = path.join(repoDir(id), "cryptoshift.services.json");
  if (!fs.existsSync(file)) return null;
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

export function listRepos() {
  if (!fs.existsSync(WORKSPACES)) return [];
  return fs
    .readdirSync(WORKSPACES)
    .filter((name) => fs.statSync(path.join(WORKSPACES, name)).isDirectory())
    .map((id) => {
      const manifest = manifestOf(id);
      return {
        id,
        name: manifest?.repository ?? id,
        description: manifest?.description ?? "",
        language: "Python",
        source: "Bundled sample repository (sample-repos/" + id + ")",
        services: manifest?.services?.length ?? 0,
      };
    });
}

export function walk(dir, base = dir, out = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith(".") || entry.name === "__pycache__") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, base, out);
    else out.push(path.relative(base, full).split(path.sep).join("/"));
  }
  return out;
}

export function readFile(id, rel) {
  const full = path.join(repoDir(id), rel);
  if (!full.startsWith(repoDir(id))) throw new Error("path escapes repository");
  return fs.readFileSync(full, "utf8");
}

export function serviceOf(manifest, rel) {
  let best = null;
  for (const service of manifest?.services ?? []) {
    if (rel === service.path || rel.startsWith(service.path)) {
      if (!best || service.path.length > best.path.length) best = service;
    }
  }
  return best;
}
