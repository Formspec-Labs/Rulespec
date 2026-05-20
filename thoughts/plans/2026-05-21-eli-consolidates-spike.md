# Spike — ELI direct import vs `rkaf:consolidates` single predicate

**Status:** Decided 2026-05-20 — Outcome: **Direct import of `eli:consolidates`** (Outcome 1). Landed in same commit. · **Scope:** ~1 day · **Target repo:** `PKAF` · **Parent ADR:** [stack 0149](../../../thoughts/adr/0149-pkaf-compose-patterns-vs-ai-governance-vocabulary.md)

> Note on scope: the spike was originally titled "ELI-I direct import" on the assumption that `eli:consolidates` lived in ELI-I (Legal Impacts). Investigation confirmed the predicate is in **ELI core** (`http://data.europa.eu/eli/ontology#`, created v1.0, refined v1.1, stable through v1.5). ELI-I covers amendment-impact modeling; consolidation is a core-ELI concept. Filename and title were updated post-investigation to reflect this; pre-rename references in ADR 0149, ticket fs-pmf4, and PKAF/CHANGELOG.md were also updated.

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

## Decision

**Outcome: Direct import of `eli:consolidates` (Outcome 1).** All three decision-criteria conditions satisfied.

### Investigation findings

**(1) ELI canonical source** — Fetched the ELI OWL file at `http://data.europa.eu/eli/ontology` (v1.5, 2024 release). `eli:consolidates`:
- Namespace IRI: `http://data.europa.eu/eli/ontology#` — stable across v1.0 → v1.5.
- Domain: `LegalExpression ∪ LegalResource`.
- Range: `LegalExpression ∪ LegalResource`.
- Inverse: `eli:consolidated_by`.
- **Not** FunctionalProperty — many-to-many native, by design.
- rdfs:comment: *"Indicates that this consolidated legal resource or expression takes into account another one. This property should be used multiple times to refer to both the original version or the previous consolidated version."* — purpose-built for multi-predecessor consolidation.
- Created v1.0, definition improved v1.1, stable v1.1–v1.5.
- ELI core property (not ELI-I — ELI-I covers amendment-impact).
- Distinguished in ELI from `eli:changes` (amendment/repeal events).

**(2) Repo-side composition friction** — Zero friction.
- `eli:` prefix already declared in `context/rkaf-context.jsonld:16` → `http://data.europa.eu/eli/ontology#`.
- `tools/vocab_audit.py` audits **classes** emitted by CUE schemas for rkaf-namespace coverage. Predicates are not audited; cross-namespace predicates pass cleanly.
- No constraint-compile pipeline coupling — `constraints/core/*.cue` does not enforce predicate namespace.

**(3) Ergonomic gap** — Direct import is more ergonomic, not less.
- Partner consumers (Studio, future legal-corpus consumers) already see ELI as canonical for EU legal-resource identity (`spec/rkaf-core.md §9.2`). Naming an `rkaf:`-prefixed synonym alongside `eli:consolidates` would create two ways to express the same edge — discoverability *worsens*, not improves.
- §9.4 discipline ("do not reinvent") is exactly this case.

**(4) Non-EU jurisdictional fit** — No competing predicate exists.
- **Akoma Ntoso** (OASIS) models consolidation as a *lifecycle process* (amendment → consolidation step in the legislative lifecycle); does not expose a single `aknt:consolidates` predicate. No conflict.
- **USLM** (US OLRC) — the US Code is itself the consolidation product; USLM does not define a consolidation predicate, just structural markup for consolidated text.
- **UK Statute Law Database / legislation.gov.uk** — represents consolidated versions, not consolidation edges.
- **LegalHTML** (2023 ESWC paper) extends `eli:LegalResource` with `lh:ConsolidatedResource` — explicitly aligns with ELI rather than competing.

→ ELI's `eli:consolidates` is the canonical IRI predicate for legal-source consolidation across jurisdictions surveyed. Aligning rather than naming a synonym is the interop-correct move.

**(5) Adversarial check on `rkaf:supersedesAssertion`** — Rejected as a substitute. Semantic distinction is real:
- `rkaf:supersedesAssertion` denotes *replacement* — predecessors become historical/superseded.
- `eli:consolidates` denotes *editorial restatement* — predecessors remain legally extant; the consolidated text incorporates them in merged form without claiming to retire them.
- ELI itself separates `eli:consolidates` from `eli:changes` (amendment/repeal) precisely to preserve this distinction; PKAF should follow.
- Using `supersedesAssertion` to carry consolidation semantics would conflate two distinct legal concepts and break downstream consumer reasoning (e.g., "is this predecessor still in force?" → consolidated predecessors *are*, superseded predecessors *are not*).

### Why not the native-predicate option

- Would duplicate ELI semantically (violates §9.4).
- Requires Pattern-C SHACL shape, fixtures, compiled artifact regeneration — half-day+ of work with no offsetting discoverability or correctness gain.
- An rkaf-prefixed synonym aliased to ELI introduces two ways to express the same edge.

### Why not the clarification-only option

- Conflates consolidation with supersession (see (5) above). ELI got the distinction right; PKAF aligning with ELI means PKAF must respect that distinction.

### Changes landed (same commit)

- `context/rkaf-context.jsonld` — added `eli:consolidates` and `eli:consolidated_by` JSON-LD term definitions (`@type: @id`, `@container: @set`) immediately after the PROV-O block. Eight lines.
- `spec/rkaf-core.md §9.2` — extended the ELI alignment row to name `eli:consolidates`, document non-functional / repeated-use semantics, and explain the consolidation-vs-supersession distinction with a cross-reference to `rkaf:supersedesAssertion` (§6).
- `context/COMPOSE-PATTERNS.md` Pattern 4 — replaced the "Open question (under spike)" note with: (a) a worked recipe showing one consolidated text incorporating three predecessor acts via `eli:consolidates`; (b) a "Consolidation vs supersession — when to use which" table distinguishing `eli:consolidates`, `rkaf:supersedesAssertion`, and `rkaf:LifecycleEvent`; (c) a pointer to the new fixture.
- `fixtures/edges/consolidates-multi-predecessor-edge.jsonld` — new edge fixture demonstrating multi-predecessor composition (4 assertions: 3 predecessors + 1 consolidated text using `eli:consolidates`).

### What did not change

- `constraints/core/*.cue` — no class added, no constraint extended. PKAF declines to constrain a non-PKAF predicate at L1; partner producers conform to ELI's own domain/range (`LegalExpression ∪ LegalResource`).
- `shapes/*.ttl` — no shape added. PKAF declines to enforce SHACL constraints over an externally-owned predicate; partners can compose ELI-side SHACL if needed.
- `compiled/{json-schema,rust,shacl,typescript}/` — no regeneration; no compiled-artifact-affecting change.
- `rkaf-vocabulary.md` — no row added; the term table is closed to rkaf-namespaced terms by design.

### Follow-up

- None required. The "Conditional follow-up (~2 weeks after spike)" branch in ADR 0149 selected "alias `eli:consolidates` directly … No vocabulary change."
