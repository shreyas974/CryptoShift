# Architecture and workflow

## Intended workflow

1. **Scope:** select a repository/revision and document supported file types and exclusions.
2. **Discover:** analyze source, configuration, and dependency files; retain path/line or key evidence.
3. **Classify:** infer operation purpose separately from algorithm clues; attach rationale and confidence; allow `unknown`.
4. **Inventory:** normalize findings with owner, library/protocol, dependencies, status, and review notes where known.
5. **Plan:** order migration tasks against dependency and capacity constraints; expose scoring assumptions.
6. **Verify:** record compatibility checks, traces, measured overhead, human approval, and rollback criteria.
7. **Report:** connect every claim to a pinned input, rule version, and test record.

## Components in the current project

The project tree includes scanner/rule/model/dependency/scoring/proposal/verification/reporting/rollback modules, a CLI, and an optimization package. Confirm actual call paths and package entry points before describing any component as complete. The local source-layout optimization files must not become a second independent implementation.

## Trust boundaries

- Static detection is evidence, not proof of complete cryptographic discovery.
- The planner is decision support; a human owns security and rollout decisions.
- QpiAI Opt/QCloud are optional scheduling experiment tools, not PQC algorithms.
- A mock trace is not a real handshake or cryptographic security test.
- Secret values must never be stored in inventory records or reports.