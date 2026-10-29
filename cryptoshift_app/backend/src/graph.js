// Dependency graph and dependency-aware migration sequencing.
// Edges "A -> B" mean A depends on B, so B must be migrated (or made dual-capable) before A.
// Known edges come from the repository manifest; inferred edges come from Python imports.
import { serviceOf } from "./repos.js";

export function buildGraph(manifest, imports = []) {
  const services = manifest?.services ?? [];
  const nodes = services.map((s) => ({ id: s.id, name: s.name, kind: s.kind, path: s.path, exposure: s.exposure ?? null, owner: s.owner ?? null }));
  const edges = [];
  const key = (a, b) => `${a}->${b}`;
  const seen = new Map();
  for (const dep of manifest?.dependencies ?? []) {
    const edge = { id: key(dep.from, dep.to), from: dep.from, to: dep.to, basis: "known", evidence: [{ source: "cryptoshift.services.json" }] };
    edges.push(edge);
    seen.set(edge.id, edge);
  }
  for (const imp of imports) {
    const fromService = serviceOf(manifest, imp.file);
    for (const name of imp.names) {
      const base = imp.module.replace(/\./g, "/");
      const target = serviceOf(manifest, `${base}/${name}.py`) ?? serviceOf(manifest, `${base}.py`) ?? serviceOf(manifest, `${base}/`);
      if (!fromService || !target || fromService.id === target.id) continue;
      const id = key(fromService.id, target.id);
      const existing = seen.get(id);
      const evidence = { file: imp.file, line: imp.line, text: `from ${imp.module} import ${imp.names.join(", ")}` };
      if (existing) {
        if (existing.basis === "known") existing.confirmedByImport = true;
        if (existing.basis === "inferred") existing.evidence.push(evidence);
        continue;
      }
      const edge = { id, from: fromService.id, to: target.id, basis: "inferred", evidence: [evidence] };
      edges.push(edge);
      seen.set(id, edge);
    }
  }
  return graphApi(nodes, edges);
}

function graphApi(nodes, edges) {
  const out = (id, list) => list.filter((e) => e.from === id).map((e) => e.to);
  const inn = (id, list) => list.filter((e) => e.to === id).map((e) => e.from);
  const closure = (id, step, list) => {
    const seen = new Set();
    const queue = [...step(id, list)];
    while (queue.length) {
      const next = queue.shift();
      if (seen.has(next) || next === id) continue;
      seen.add(next);
      queue.push(...step(next, list));
    }
    return [...seen];
  };
  return {
    nodes,
    edges,
    dependenciesOf: (id) => closure(id, out, edges),
    dependentsOf: (id) => closure(id, inn, edges),
    plan: (options = {}) => planOf(nodes, options.includeInferred === false ? edges.filter((e) => e.basis === "known") : edges),
  };
}

// Tarjan's strongly connected components.
function components(nodes, edges) {
  let index = 0;
  const stack = [];
  const on = new Set();
  const idx = new Map();
  const low = new Map();
  const result = [];
  const visit = (v) => {
    idx.set(v, index);
    low.set(v, index);
    index++;
    stack.push(v);
    on.add(v);
    for (const w of edges.filter((e) => e.from === v).map((e) => e.to)) {
      if (!idx.has(w)) {
        visit(w);
        low.set(v, Math.min(low.get(v), low.get(w)));
      } else if (on.has(w)) low.set(v, Math.min(low.get(v), idx.get(w)));
    }
    if (low.get(v) === idx.get(v)) {
      const comp = [];
      let w;
      do {
        w = stack.pop();
        on.delete(w);
        comp.push(w);
      } while (w !== v);
      result.push(comp);
    }
  };
  for (const n of nodes) if (!idx.has(n.id)) visit(n.id);
  return result;
}

function planOf(nodes, edges) {
  const cycles = components(nodes, edges)
    .filter((c) => c.length > 1)
    .map((members) => ({ members, edges: edges.filter((e) => members.includes(e.from) && members.includes(e.to)) }));
  const inCycle = new Set(cycles.flatMap((c) => c.members));
  const deps = (id) => edges.filter((e) => e.from === id).map((e) => e.to);
  const done = new Set();
  const waves = [];
  let remaining = nodes.map((n) => n.id).filter((id) => !inCycle.has(id));
  // Kahn-style layering: a node is ready once every dependency is migrated.
  while (remaining.length) {
    const ready = remaining.filter((id) => deps(id).every((d) => done.has(d)));
    if (!ready.length) break;
    waves.push(ready);
    ready.forEach((id) => done.add(id));
    remaining = remaining.filter((id) => !done.has(id));
  }
  const steps = [];
  waves.forEach((wave, w) => wave.forEach((id) => steps.push({ node: id, wave: w + 1, status: "schedulable", prerequisites: deps(id), blockedBy: [] })));
  for (const id of inCycle) {
    const cycle = cycles.find((c) => c.members.includes(id));
    steps.push({ node: id, wave: null, status: "blocked-cycle", prerequisites: deps(id), blockedBy: cycle.members.filter((m) => m !== id) });
  }
  for (const id of remaining) {
    steps.push({ node: id, wave: null, status: "blocked-upstream", prerequisites: deps(id), blockedBy: deps(id).filter((d) => !done.has(d)) });
  }
  return {
    valid: cycles.length === 0,
    waves,
    steps,
    cycles,
    edgeCount: { known: edges.filter((e) => e.basis === "known").length, inferred: edges.filter((e) => e.basis === "inferred").length },
  };
}
