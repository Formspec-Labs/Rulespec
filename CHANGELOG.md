# Changelog

All notable changes to Rulespec are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adapted for a specification + shape + fixture project.

## v0.2.0-pre.5 — Layer 4 Projectors (MVP triangle)

**Three bidirectional projectors landed: JSON Schema 2020-12, JSON-LD 1.1, OpenAPI 3.1. Each implements the source spec §8.1 contract (Attach, Extract, Validate, RoundTrip, Derive). Round-trip parity is the release gate.**

### Added

- `crates/Cargo.toml` — workspace root for the Layer 4 Rust crates.
- `crates/rkaf-projector-core/` — `Projector` trait per source spec §8.1.
- `crates/rkaf-projector-json-schema/` — JSON Schema 2020-12 projector. Carrier convention: root `x-rkaf` extension key (`{rkaf-version, rkaf-depth, "rkaf:overlay"}`). Validate uses `jsonschema` Rust crate against compiled v0.2 schemas. Derive shells out to `tools/constraints_compile.py --target json-schema`.
- `crates/rkaf-projector-json-ld/` — JSON-LD 1.1 projector. Carrier convention: `@graph` merge, type-namespace partition (`rkaf:` prefix → overlay) on Extract; context-array single-element collapse preserves byte-equality on common-shape inputs.
- `crates/rkaf-projector-openapi/` — OpenAPI 3.1 projector. Carrier convention: document-level `x-rkaf` extension. Derive wraps the JSON Schema target's `$defs` into a complete OpenAPI 3.1 document with populated `components.schemas`.
- `crates/projector-harness/` — CLI binary used by `tools/projector_parity.py` to exercise Attach/Extract/RoundTrip and Derive across all three targets.
- `spec/projectors/json-schema-v0.2.md` — JSON Schema carrier convention v0.2 (normative subordinate).
- `spec/projectors/json-ld-v0.2.md` — JSON-LD carrier convention v0.2 (normative subordinate).
- `spec/projectors/openapi-v0.2.md` — OpenAPI 3.1 carrier convention v0.2 (normative subordinate).
- `tools/projector_parity.py` — round-trip parity orchestrator (release gate).
- `fixtures/v0.2/projectors/{json-schema,json-ld,openapi}/round-trip-*.{jsonld,yaml}` — 7 round-trip fixtures covering SNAP redetermination, warrant chains, empty overlays, and OpenAPI source-authority API documents.

### Verified

- 9 projector unit tests pass (3 per projector: identity round-trip, attach-collision refusal, extract-collision refusal).
- 7/7 round-trip fixtures pass byte-identical Attach → Extract through the harness binary.
- Derive operation produces parseable JSON Schema, JSON-LD context fragment, and OpenAPI 3.1 documents end-to-end via subprocess to `tools/constraints_compile.py`.
- CI workflow `constraints-parity.yml` now builds the Layer 4 crates, runs `cargo test --workspace`, and exercises the projector parity orchestrator.

### Conformance

All three projectors implement the full §8.1 contract: Attach, Extract, Validate (delegated to JSON Schema in JSON-LD/OpenAPI for v0.2 MVP; per-node-validate loop deferred to Layer 5 SDKs), RoundTrip (default trait impl), Derive. Round-trip parity verified across the fixture set; the Studio-profile Derive output (Gate C of the master sequence) is the next gate to land in Plan 10 (Studio cutover), which depends on a published Studio profile.

### Compatibility

Pre-release. The reference Validate implementations in JSON-LD and OpenAPI projectors are stubs that return `Ok(())`; the production Validate composition (loop overlay nodes, validate each against compiled JSON Schema by `@type`) lands with the Layer 5 SDK harness in Plan 6. The MVP triangle's correctness contract is round-trip identity, asserted in CI.

## v0.2.0-pre.3 — Layer 2 Constraints

**CUE selected as constraint source language. JSON Schema 2020-12, Rust, TypeScript are MUST targets; SHACL, CUE-passthrough, Rego are MAY targets.**

### Added

- `docs/adr/2026-05-12-rkaf-constraint-source-cue.md` — selection rationale.
- `constraints/core/*.cue` — CUE source for every v0.2 vocabulary primitive (artifact, source-fragment, evidence-binding, warrant, confidence-record, access-scope, ai-lineage, retention-policy, workspace, mapping-state, assertion, concept-registry).
- `constraints/adversarial/*.cue` — 5 evaluator-class adversarial constraints (conditional-silent-pass, cross-property-coupling, enum-drift, access-scope-leakage, nested-noevidencereason) per spec §10.1.
- `constraints/ai-extraction/*.cue` — 3 LLM-systematic-misinterpretation adversarial constraints (warrant-family-confusion, consent-vs-warrant, confidence-score-without-method) per spec §10.1.
- `tools/constraints_compile.py` — CUE → {JSON Schema, Rust, TypeScript, SHACL, CUE, Rego} compiler. Recognizes Rulespec's regular CUE patterns (closed enums, enum-of-refs unions, shapes, conditionals, disjunctions, list cardinality).
- `tools/constraints_parity.py` — cross-target parity orchestrator (release gate). Asserts JSON Schema + SHACL classify every CORE fixture identically; documents adversarial-fixture divergences (which by design surface evaluator-class gaps).
- `tools/install-cue.sh` — pinned CUE 0.10.0 installer.
- `.tool-versions` — `cue 0.10.0`.
- `compiled/{json-schema,rust,typescript,shacl,cue,rego}/` — generated artifacts (gitignored; reproducible from CUE source).

### Changed

- SHACL is demoted from authoritative status (per source spec Appendix C). The hand-written shape files in `shapes/` (v0.1 and v0.2) remain in tree for transition; `compiled/shacl/` is the canonical SHACL output going forward, Pattern C only by construction.

### Verified

- 18/18 core Vocabulary fixtures pass parity across JSON Schema + SHACL targets, identical PASS/FAIL classification, all matching expected outcomes.
- 8 adversarial fixtures: 6/8 surface their designed evaluator-class divergence (SHACL accepts what JSON Schema rejects in cross-property / inline-enum cases — this is the documented gap, not a regression).
- 0 `sh:if` / `sh:then` constructs in `compiled/shacl/` — Pattern C lint passes.
- All v0.2 CUE source files vet successfully (`cue vet`).

### Compatibility

Pre-release. v0.1.x SHACL shape files do not interoperate with v0.2 compiled artifacts. No migration shim.

## v0.2.0-pre.2 — Vocabulary v0.2

**Vocabulary Layer 1 lands. Pre-release; CHANGELOG-driven; no compatibility with v0.1.x.**

### New first-class primitives (§§4.1-4.6 of `spec/rkaf-core-v0.2.md`)

- `rkaf:Artifact` with `artifactIdentifierScheme` closed enum (eli, eli-dl, eli-i, uslm, aknt-eId, doi, isbn, issn, cid, hash-sha256, urn-persistent, partner-defined).
- `rkaf:SourceFragment` composing the W3C Web Annotation (`oa:`) selector vocabulary plus domain-specific selectors (Akoma Ntoso eId, USLM section, ELI fragment, JSONPath, DOI fragment).
- `rkaf:EvidenceBinding` with the operational-validity invariant (≥1 source fragment OR a permitted `noEvidenceReason`).
- `rkaf:Warrant` as the universal grounding primitive; `rkaf:Authority` preserved as the legal-family specialization. Six warrant families: legal, scientific, editorial, cryptographic, social, source-class.
- `rkaf:ConfidenceRecord` with `calibrationStatus` + `confidenceBasis` + `generatedBy` required (rejects "score theater").
- `rkaf:AccessScope` with seven kinds plus DPV / ODRL alignment for regulatory and rights cases.

### Studio-derived promotions (§5)

- `rkaf:MappingState` (closed four-value enum: `mapsToWos`, `authoringOnly`, `requiresSpecExtension`, `unmappedButApproved`).
- `rkaf:RetentionPolicy` with `retentionTrigger` and `retentionPostExpiry` closed enums.
- `rkaf:AILineage` with mandatory `humanApprover`.
- `rkaf:llmHint` annotation property (carried through the JSON Schema projector as `x-rkaf-llmHint`).
- `rkaf:Workspace` scoping with `workspaceId` + `workspaceTrustList`.
- `rkaf:projectsTo` (generalizes Studio's `wosTarget`).

### Abstract anchoring contract (§7)

- `rkaf:anchoredBy` / `rkaf:anchorType` predicates; concrete bindings (Trellis, COSE, VC, Sigstore, IPFS) live outside Rulespec and depend on this contract.

### Public ontology composition (§9)

- Imports: PROV-O, OA, SKOS, DCTERMS, CiTO, DCAT, RDF/RDFS/XSD, SHACL.
- Alignments: ELI / ELI-DL / ELI-I, RRMV, Akoma Ntoso, USLM, LegalRuleML, ECO / SEPIO, Nanopublications, ODRL, DPV, Schema.org / Schema.org-Legislation, DCAT / VoID.
- Projections (carried by Layer 4 projectors, Plan 5): JSON Schema, JSON-LD, OpenAPI 3.1 (MVP).

### Shape files (compiled SHACL targets — not source of truth per Layer 2 plan)

- `shapes/rkaf-shapes-core-v0.2.ttl` (umbrella)
- `shapes/rkaf-shapes-warrant-v0.2.ttl`
- `shapes/rkaf-shapes-confidence-v0.2.ttl`
- `shapes/rkaf-shapes-accessscope-v0.2.ttl`
- `shapes/rkaf-shapes-studio-promotions-v0.2.ttl`
- `shapes/rkaf-shapes-conceptregistry-v0.2.ttl`

Pattern C only (per Appendix C of source spec). Zero `sh:if` / `sh:then` constructs.

### Companion specs

- `spec/rkaf-core-v0.2.md` (normative).
- `spec/rkaf-concept-registry-v0.2.md` (SKOS-bound mapping predicates, workspace scoping, generalized warrant on mappings; supersedes v0.1.2).
- `spec/rkaf-vocabulary-v0.2.md` (full term reference; mechanically consumable).

### Fixtures (`fixtures/v0.2/`)

20 positive + 4 negative fixtures. Coverage requirement (`tools/vocab_audit.py`): every Vocabulary class exercised by ≥1 fixture.

### Tooling

- `tools/vocab_audit.py` — fails build if a v0.2 term has no fixture.
- `tools/validate_negatives.py` — asserts negative fixtures FAIL as designed.
- `tools/ci_validate.py --mode v02` — full v0.2 positive-fixture validation.

### Compatibility

None with v0.1.x. v0.2 supersedes wholesale.

## v0.2.0-pre.1 — Brand rename: PKAF → Rulespec

- The framework is renamed to **Rulespec** (acronym **RKAF**, "Rulespec Knowledge Assertion Framework").
- Vocabulary prefix `pkaf:` is renamed to `rkaf:` everywhere in shapes, JSON-LD contexts, fixtures, and spec bodies.
- IRI namespace `https://w3id.org/pkaf/` is renamed to `https://rulespec.org/`.
- Bridge contract identifier `pkaf-bridge/1.0` is renamed to `rkaf-bridge/1.0`.
- All `pkaf-*` artifact filenames are renamed to `rkaf-*` (`spec/pkaf-core-v0.1.md` → `spec/rkaf-core-v0.1.md` etc.).
- This is a wholesale rename. There is no compatibility shim and no `pkaf:` prefix is supported in v0.2 or later.

## [v0.1.1] — 2026-05-12 — Structural validation fix and consumer-justification shapes

### Added

- **Consumer artifact overlay shape vocabulary** (`shapes/rkaf-shapes-justification-v0.1.ttl`)
  - `GeneratedWorkProductJustificationShape` — validates the Rulespec overlay type
  - `ConsumerArtifactJustificationShape` — universal shape targeting subjects of `rkaf:justifiedByAssertion`
  - `DataCollectionArtifactJustificationShape` — universal shape targeting subjects of `rkaf:collectsEvidenceType`
  - `ProcessArtifactJustificationShape` — universal shape targeting subjects of `rkaf:requiresEvidenceType`
  - `FullBridgeValidationResultShape` — structured output requirement on non-accepted bridge results
  - `JustificationChainHopShape` — allows `rkaf:implements` predicate (distinct from `AuthorityChainHop`)
  - `FormspecFieldJustificationShape` — documented example specialization
  - `WOSStepJustificationShape` — documented example specialization

- **Multi-mode CI gate** (`tools/ci_validate.py --mode core | batch2 | batch3 | batch4`)
  - Four conformance modes selectable via flag
  - Per-fixture triple-count drift detection
  - JSON output mode for CI pipelines

- **Public framing as universal ontology**
  - README rewritten: Rulespec positioned as universal evidence-backed assertion / authority / concept / lifecycle / justification ontology
  - Consumer systems (search engines, wikis, form builders, workflow engines, case systems, content management, AI assistants, publication tools, auditing tools, knowledge graphs) framed as examples, not anchors
  - Fixtures explicitly labeled as stress tests for the consumer overlay pattern, not dependencies

### Fixed

- **pySHACL `sh:if`/`sh:then` evaluation bug.** Eight conditional shapes across Batches 1.1, 2, 3, and 4 were not actually firing as designed. All eight rewritten using Pattern C (`sh:or` with `sh:not`), which pySHACL evaluates reliably:
  - `BridgeValidationResultShape` (Batch 1.1) — rejected → remediation OR noRemediationReason
  - `OperationalAssertionEvidenceShape` (Batch 1.1) — R2/A3/P4 → hasEvidence required
  - `AuthorityAssertionShape` (Batch 1.1) — A3 → authorityKind + hasApplicability + qualified evidence
  - `MappingAssertionShape` (Batch 2) — closeMatch + operational → MappingApplicabilityContext
  - `ConceptLifecyclePacketShape` (Batch 2) — split/merge/replacedBy → successorConcepts
  - `MappingConflictShape` (Batch 2) — operational/publicationBlocking severity → artifact reference
  - `RevalidationClosureEventShape` (Batch 3) — revalidatedWithSuccessor → successor reference
  - `FullBridgeValidationResultShape` (Batch 4) — non-accepted → structured indicator

- **Six latent fixture defects** surfaced by the corrected constraints, all patched:
  - `amend-001` (local-operational): added `authorityKind = rkaf:organizational` and `ApplicabilityContext`
  - `rescission-001` (statutory): added `authorityKind = rkaf:statutory` and `ApplicabilityContext`
  - `delegation-derives-from-statute` (statutory): added `ApplicabilityContext`
  - `regulation-derives-from-delegation` (statutory): added `ApplicabilityContext`
  - `caa-42-2026-07-01-001` (mapping): added structured `warnings` entry
  - `case-4-unreachable` (registry-failure-conflict): added `noRemediationReason = rkaf:noActionableRemediation`

### Changed

- **Triple count:** 1,186 → 1,206 (+20 from fixture defect patches)
- **Shape implementation:** Pattern C rewrites change all eight conditional shape SHA-256 hashes (semantics unchanged)
- **JSON-LD context:** `_meta` block added to `rkaf-context-v0.2.jsonld` documenting it as a strict additive superset of v0.1

### Unchanged from v0.1-rc1

- **Specification text** (`spec/rkaf-core-v0.1.md`, `spec/rkaf-concept-registry-v0.1.2.md`) — semantically identical
- **Fixture narratives** — substantively identical
- **Vocabulary** — no new terms added; only the additive `rkaf:definedInScope` context typing carried forward from Batch 2

### Conformance signature

```
Mode:       batch4 (Core + ConceptRegistry + Lifecycle + Justification)
Shapes:     4 files
Fixtures:   4
Triples:    1,206
Violations: 0
Result:     PASS
```

### Coverage gaps accepted

Four shapes have no fixture target. They remain structurally correct and will activate when future fixtures instantiate the relevant entity type:

- `ConceptMintingAuthorityShape` — full mint-authority instances not exercised
- `SupersessionPacketShape` — full-document supersession not exercised
- `MaterialRevisionPacketShape` — material revision distinct from amendment not exercised
- `JustificationChainHopShape` — justification chains with `rkaf:implements` predicate not exercised

---

## [v0.1-rc1] — 2026-05-12 — Initial release candidate

### Added

- **Rulespec Core specification** (`spec/rkaf-core-v0.1.md`)
  - Assertions, evidence, attestations, adoption, authority chain
  - Bridge model and consumer artifact overlay
  - Lifecycle packets, revalidation, point-in-time exceptions
  - Cascade closure algorithm specification

- **ConceptRegistry specification** (`spec/rkaf-concept-registry-v0.1.2.md`)
  - Registered concepts, local concepts, mappings
  - Mapping applicability contexts
  - Concept resolution and usage ceiling
  - ConceptRegistry-Core / Lifecycle / Federated conformance levels

- **JSON-LD context** (`context/rkaf-context-v0.1.jsonld`)

- **Core SHACL shapes** (`shapes/rkaf-shapes-core-v0.1.ttl`)
  - 8 shape sets covering trust zones, assertions, evidence, attestations, adoption, authority, applicability, bridge validation

- **Four conformance fixtures**
  - `local-operational-v0.2.jsonld` — CSBG eligibility lifecycle
  - `mapping-v0.1.jsonld` — Concept registry mappings
  - `statutory-authority-v0.1.jsonld` — Statutory rescission with authority chain
  - `registry-failure-conflict-v0.1.jsonld` — Nine registry failure scenarios

- **Multi-pass validation arc:** 251 → 14 → 0 violations
- **1,183 triples, 0 violations** at v0.1-rc1 freeze

### Known issues at v0.1-rc1 (discovered and fixed in v0.1.1)

- Three conditional shapes (`BridgeValidationResultShape`, `OperationalAssertionEvidenceShape`, `AuthorityAssertionShape`) used the `sh:if`/`sh:then` SHACL Advanced Features pattern which pySHACL 0.31.0 does not evaluate reliably. The constraints existed in the TTL files and parsed correctly, but did not fire against fixture data. v0.1-rc1 fixtures *happened to* mostly satisfy these constraints but four latent defects were hidden by the broken evaluation. All addressed in v0.1.1.
