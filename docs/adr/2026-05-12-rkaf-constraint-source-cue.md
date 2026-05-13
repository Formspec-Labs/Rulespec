# ADR — Rulespec Constraint Source Language: CUE

**Date:** 2026-05-12
**Status:** Accepted
**Decision:** CUE is the source language for Rulespec Layer 2 constraints. JSON Schema, Rust, TypeScript, SHACL, and Rego are compilation targets.

## Context

Rulespec spec §6.1 mandates a single source-of-truth constraint language compilable to multiple targets, with decidable evaluation and cross-property/cross-document expressivity. §6.2 enumerates candidates: Rulespec Constraint DSL (greenfield), CUE, SPARQL ASK, Datalog, Cedar.

Per the source spec Appendix C, SHACL's `sh:if` / `sh:then` Pattern B has silent-pass failure modes that disqualify SHACL as the constraint source. The v0.1.1 patch series rewrote conditional shapes to Pattern C (`sh:or` with `sh:not`); v0.2 demotes SHACL to one compilation target among many.

## Considered

| Candidate | Decidable? | Cross-property? | Native JSON Schema? | Rust target? | TypeScript target? | SHACL target? | Rego target? | Design cost |
|---|---|---|---|---|---|---|---|---|
| Rulespec DSL (greenfield) | yes | yes | YES | yes | yes | yes | yes | weeks |
| **CUE** | **yes** | **yes** | **YES (native exporter)** | **yes (codegen)** | **yes (codegen)** | **yes (codegen)** | **yes (codegen)** | **days** |
| SPARQL ASK | undecidable in general; decidable for ASK | yes | NO | painful | painful | yes (native) | no | high |
| Datalog | yes (function-free) | yes | NO | feasible | feasible | yes | yes | high |
| Cedar | yes | partial | NO | yes | yes | NO | yes | high |

## Decision

CUE. CUE wins on three axes:

1. **Decidable + finite-domain by design** — no silent-pass class failures (the v0.1.1 SHACL Pattern C rewrite was the trigger; CUE simply does not have that failure mode).
2. **JSON Schema is a native CUE output** — `cue export --out openapi` and `cue def --out openapi+jsonschema=jsonschema` ship in the upstream toolchain. The JSON Schema target (load-bearing for depth-D3 reference consumers and LLM tool-use APIs per §6.3) is glue, not a full code generator.
3. **Cross-property and cross-document expressivity** via CUE's `#X & Y` constraint composition and `import` machinery. The §4.3 EvidenceBinding operational-validity invariant, the §4.4 cross-family warrant-transition warning, and the §5.3 AI-touched-origin → AILineage cross-property invariant all express naturally as CUE disjunctions and conditionals.

Rejected:
- **Greenfield Rulespec DSL** — pays weeks of design cost for marginal advantage over CUE.
- **SPARQL ASK** — strong on graph patterns but lossy projection to JSON Schema and TypeScript; not a fit for AI-tractable structured-output targets.
- **Datalog** — strong reasoning power but no native carrier-format projection.
- **Cedar** — policy-language idiom doesn't fit ontology-shape constraints.

## Consequences

- The compilation pipeline is a Rust crate (`rkaf-constraints-compile`) with `cue export --out openapi` driving the JSON Schema target, hand-written codegen drivers for Rust / TypeScript / SHACL / Rego.
- SHACL is demoted to one compilation target. v0.2 SHACL shape files in `shapes/` become hand-written stop-gap projections until the Layer 2 compiler cuts over; `compiled/shacl/` becomes the canonical output going forward.
- `cue` binary becomes a build-time dependency. Pinned to `0.10.0` in `.tool-versions` and installed via `tools/install-cue.sh`.
- Pattern C is the only SHACL conditional pattern emitted. CI grep gate (`compiled/shacl/` MUST NOT contain `sh:if` or `sh:then`).

## Alternatives revisited

None. This decision is final pre-1.0; revisit only if CUE upstream becomes unmaintained.
