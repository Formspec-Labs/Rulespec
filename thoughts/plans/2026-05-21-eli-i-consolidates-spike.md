# Spike — ELI-I direct import vs `rkaf:consolidates` single predicate

**Status:** Queued · **Scope:** ~1 day · **Target repo:** `PKAF` · **Parent ADR:** [stack 0149](../../../thoughts/adr/0149-pkaf-compose-patterns-vs-ai-governance-vocabulary.md)

## Context

The 2026-05-20 vocabulary review (ADR 0149) rejected all six proposed AI-governance vocabulary additions except for one residual open question: multi-predecessor source consolidation. The existing `rkaf:supersedesAssertion` is many-to-many but semantically denotes "supersedes" rather than "consolidates from multiple predecessors." ELI 1.5 provides `eli:consolidates` (and `eli:isConsolidatedBy`) for exactly this case.

Two viable paths:

1. **Direct import** — Alias `eli:consolidates` into the rkaf context via `owl:equivalentProperty`, document the import in `spec/rkaf-core.md §9.2` (ELI-I alignment), and add nothing else.
2. **Native predicate** — Add a single `rkaf:consolidates` predicate (no class), one Pattern-C SHACL shape over predecessor temporal alignment, positive / negative / edge fixtures.

Choose by ergonomic fit + interop cost, not by general preference.

## Goal

A decision artifact written by 2026-05-22 that selects one path and either (a) lands the direct-import change in the same commit or (b) opens a follow-up plan with the single-predicate addition. Net new vocabulary classes: 0 in both paths.

## Investigation steps

1. **Read the canonical ELI sources.**
   - ELI Ontology 1.5 — http://data.europa.eu/eli/ontology
   - ELI-I (impact) — Publications Office guidance
   - Confirm the exact predicate name, domain, range, cardinality, and any required companion predicates (`eli:isConsolidatedBy`, lifecycle ties).
   - Confirm `eli:` namespace stability and whether the Publications Office publishes a versioned context URL suitable for direct JSON-LD import.

2. **Check repo-side composition friction.**
   - Read `context/rkaf-context.jsonld` ELI alignment block (around L869-878 PROV-O block; ELI alignment is at §9.2 normatively but may not be wired in context — verify).
   - If `eli:` is not currently mapped, draft the prefix declaration + `owl:equivalentProperty` triple in a sandbox context.
   - Try the import against `fixtures/edges/effective-period-with-sunset-edge.jsonld` and one synthetic multi-predecessor fixture; verify the existing constraint stack handles it.

3. **Evaluate ergonomic gap.**
   - Would partner consumers (Studio, future legal-corpus consumers) find `eli:consolidates` ergonomic in their JSON-LD documents, or is a rkaf-namespaced alias materially easier to discover / cite / lint?
   - Specifically: does `tools/vocab_audit.py` and the constraint-compile pipeline tolerate cross-namespace predicates in core artifacts, or does it expect rkaf-namespaced terms for L1 vocabulary coverage?

4. **Check non-EU jurisdictional fit.**
   - USLM, US OLRC consolidation tooling, UK Statute Law Database — do they use ELI-aligned predicates, or jurisdiction-local names?
   - If non-EU jurisdictions diverge significantly, a rkaf-namespaced predicate aliased to ELI may be the more interoperable choice. If they align, direct ELI import is canonical.

5. **Adversarial check.**
   - Is there a case where `rkaf:supersedesAssertion` (existing, many-to-many) actually carries the multi-predecessor consolidation already, and the apparent gap is semantic clarification only? If so, the spike outcome may be "no new predicate; clarify §9.2 semantics."

## Decision criteria

| Outcome | Conditions |
|---|---|
| **Direct import of `eli:consolidates`** | (a) ELI namespace is stable + versioned; (b) constraint pipeline handles cross-namespace predicates; (c) non-EU jurisdictions either align or do not require local naming. |
| **Native `rkaf:consolidates` predicate (aliased to ELI)** | (a) Constraint pipeline expects rkaf-namespaced terms for L1 coverage; OR (b) non-EU jurisdictional divergence warrants a Rulespec-native synonym; OR (c) ergonomic survey of consumers strongly prefers rkaf-namespaced. |
| **No new vocabulary; clarify §9.2 prose only** | `rkaf:supersedesAssertion` semantics + existing `LifecycleEvent` kinds (incl. `supersession`) cover multi-predecessor consolidation with prose clarification rather than a new predicate. |

## Files likely to change

**For direct-import outcome:**
- `context/rkaf-context.jsonld` — add `eli:` prefix + `owl:equivalentProperty` alias (if needed).
- `spec/rkaf-core.md §9.2` — extend ELI-I alignment paragraph naming `eli:consolidates`.
- `context/COMPOSE-PATTERNS.md` Pattern 4 — replace "open question" note with the resolved alias guidance.

**For native-predicate outcome:**
- `context/rkaf-context.jsonld` — add `rkaf:consolidates` predicate definition + `owl:equivalentProperty` alias.
- `spec/rkaf-vocabulary.md` — extend the temporal-validity row group with the predicate row.
- `shapes/consolidates-shape.ttl` — single Pattern-C shape: predecessors must terminate at successor's `effectivePeriodStart`.
- `constraints/core/` — no new file; predicate added to the appropriate existing CUE constraint (likely the assertion or source-fragment shape).
- `fixtures/` — positive (≥2 predecessors with aligned termination), negative (overlap), edge (3+ predecessors).
- `compiled/{json-schema,rust,shacl,typescript}/` — regenerated via `tools/constraints_compile.py`.
- `context/COMPOSE-PATTERNS.md` Pattern 4 — replace "open question" note with the new-predicate citation.

**For clarification-only outcome:**
- `spec/rkaf-core.md §9.2` — prose extension only.
- `context/COMPOSE-PATTERNS.md` Pattern 4 — close the open-question note.

## Out of scope

- All five other proposals from the 2026-05-20 review (Projection, Proposal+Promotion, RetrievalPolicy, AnswerTraceBundle, MaterializedEdge). ADR 0149 closed these.
- Retrieval-policy extension profile incubation. Separate quarter-out plan if demand surfaces.
- Trellis-envelope wrapping pattern for AnswerTraceBundle exchange. Documented in COMPOSE-PATTERNS Pattern 5; no implementation work in this spike.

## Test plan

- For any predicate change, regenerate compiled artifacts and run `make test`.
- For direct-import outcome, add one synthetic multi-predecessor fixture and verify it validates at L1 + L2.
- For native-predicate outcome, full positive / negative / edge fixture family + L3 SHACL coverage.

## Done criteria

- A written decision recorded in this file (status: decided) naming one of the three outcomes.
- If outcome is "direct import" or "clarification only": change landed in same commit.
- If outcome is "native predicate": follow-up plan opened with implementation scope (~half-day).
- COMPOSE-PATTERNS Pattern 4 updated to reflect the resolution.
