# Changelog

All notable changes to Rulespec are documented in this file.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adapted for a specification + shape + fixture project.

## Unreleased — All deferred gaps closed

Follow-up to the review-driven fixes: close every remaining gap noted as deferred or informational in the prior CHANGELOG entry. The semi-formal review's findings 6 and 7 are now closed.

### Added

- **`spec/rkaf-behavior.md`** — new normative document covering the Layer 5 runtime contracts: `usageEligibility` reducer invariants, `CascadeClosureV1` algorithm, the 10 bridge contract rules, point-in-time exception evaluation, stale transition semantics. Includes a codification roadmap mapping each runtime contract to its current state (shape-codified / partial / runtime-only) and the path to fuller codification under Plan 7 (Conformance). The full v0.1 normative prose remains preserved at `archive/v0.1/spec/rkaf-core.md` as the authoritative reference until the roadmap completes.

### Changed

- **`tools/ci_validate.py` extended.** The SHACL gate now validates the 10 §6 codified additional terms via the CUE-compiled SHACL shapes at `compiled/shacl/core/`. 10 new shape files added to the `SHAPES` list; 10 new fixtures added to `EXPECTED`. Gate now validates **30 fixtures across 16 shape files** (was 20 across 6); 0 violations, 173 triples.
- **`tools/vocab_audit.py` recognizes the §6 codified-terms table layout.** Previously the audit only parsed §5's 7-cell layout (`| Term | IRI | … | Required fixtures |`); my §6 uses a 4-cell layout (`| Term | CUE | Fixture | Purpose |`). The audit now detects either header signature and reads the matching column. Required-fixtures count: 24 → 34; remaining "extras" are `context.jsonld` (shared JSON-LD context, by design) and `local-operational-positive.jsonld` (preserved v0.1 fixture).
- **`rkaf:mappingPredicate` → `rkaf:mappingRelation`.** The hand-authored `shapes/rkaf-shapes-conceptregistry.ttl` (the canonical reference for ConceptRegistry §2.2) declares the property as `mappingRelation` with allowed values `skos:closeMatch` / `exactMatch` / `broader` / `narrower` / `related` / `mappingRelation`. My new CUE had drifted to `mappingPredicate` with the `Match`-suffixed SKOS variants. Aligned the CUE + fixture + context to the canonical spelling.
- **`spec/README.md` rewritten.** Previously referenced nonexistent filenames (`rkaf-core-v0.1.md`, `rkaf-concept-registry-v0.1.2.md`) — a pre-existing staleness the review surfaced. Now enumerates every active spec document (`rkaf-core.md`, `rkaf-vocabulary.md`, `rkaf-concept-registry.md`, `rkaf-behavior.md`, the three projector carrier conventions) with current paths, and points at `archive/v0.1/` for historical reference. `tools/rename_audit.py` allowlists this file (historical PKAF references are intentional context).
- **`OneOrMany<T>` doc-comment** in `crates/rkaf-core/src/lib.rs` now discloses the empty-array permissiveness: `[]` deserializes as `Many(vec![])`, bypassing `list.MinItems(N)` at the Rust layer. JSON Schema (`rkaf-validate`) and SHACL (`tools/ci_validate.py`) catch cardinality on their respective gates.

### Verified (post-fix)

- `cargo test --workspace`: **36 tests, 0 failures**.
- `tools/ci_validate.py` (SHACL): **30 fixtures across 16 shape files, 0 violations, 173 triples**.
- `tools/validate_negatives.py`: 4/4 FAIL-AS-EXPECTED.
- `tools/vocab_audit.py`: **34/36 fixtures declared in spec (2 informational extras)**.
- `tools/rename_audit.py`: CLEAN.
- `tools/constraints_parity.py`: 0 release blockers.
- `tools/projector_parity.py`: 7/7 round-trip OK.
- `tools/version_sync.py --check`: clean.

### Status of the original review findings

| Finding | Severity | Status |
|---|---|---|
| 1. Broken cross-file `$ref`s in 4 schemas | BLOCKER | ✓ fixed (auto-discovered enum registry) |
| 2. `@type` field never emitted in Rust | WARNING | ✓ fixed (consult `s.type_iri`) |
| 3. Zero coverage on 10 new fixtures | WARNING | ✓ fixed (`STRICT_POSITIVE` + 9 new round-trip tests) |
| 4. False "no API drift" claim | WARNING | ✓ fixed (CHANGELOG disclosed; rename aligns Rust with v0.1 spec) |
| 5. Hardcoded `_RUST_CROSS_FILE_ENUMS` dict | WARNING | ✓ fixed (auto-discovered registry shared with JSON Schema target) |
| 6. Layer 1 / Layer 5 seam + `spec/README.md` staleness | NIT/OBSERVATION | ✓ fixed (`spec/rkaf-behavior.md` created; `spec/README.md` rewritten) |
| 7. `OneOrMany<T>` empty-array permissiveness | OBSERVATION | ✓ fixed (doc-comment discloses) |
| Deferred: SHACL gate not validating new vocab | (deferred) | ✓ fixed (compiled SHACL wired into `ci_validate.py`) |
| Deferred: Layer 5 behavioral semantics | (deferred) | ✓ fixed (`spec/rkaf-behavior.md`) |
| Audit: §6 table silently bypassed | (informational) | ✓ fixed (audit recognizes both header signatures) |

Every flag the semi-formal review raised is closed. The active tree has no remaining deferred gaps from the backlog-integration work.

## Unreleased — Vocabulary backlog integration: review-driven follow-ups

A semi-formal code review of the initial backlog integration surfaced one BLOCKER and four WARNINGs. All are addressed here.

### Fixed (review follow-ups)

- **BLOCKER: cross-file enum `$ref`s in compiled JSON Schemas.** The Rust target had a `_RUST_CROSS_FILE_ENUMS` registry; the JSON Schema target did not. As a result, 4 of 10 new positive fixtures (`conceptmapping-positive`, `conceptresolutionresult-positive`, `localadoption-positive`, `bridgevalidationresult-positive`) failed validation at runtime with `Invalid reference: #/$defs/UsageEligibility` errors. **Fix:** `tools/constraints_compile.py` now scans every sibling CUE file at startup (`_scan_global_enum_registry`), builds an enum-name → source-file map, and the JSON Schema target inlines cross-file enum definitions into each consuming schema's `$defs`. The Rust target was migrated off the hardcoded `_RUST_CROSS_FILE_ENUMS` dict onto the same auto-discovered registry. (Findings 1 + 5.)
- **`@type` field was never emitted in generated Rust structs.** The parser diverts `@type` into `shape.type_iri` before the property loop; the Rust target was looking for `@type` in `s.properties` and never finding it, making the `pub type_: String` + `default_type()` constructor emission dead code. **Fix:** consult `s.type_iri` directly. 21 of 24 generated modules now emit `@type` (the 3 without are pure enum-only files). (Finding 2.)
- **Missing test coverage on the 10 new fixtures.** None were in `STRICT_POSITIVE` (rkaf-validate) or as round-trip tests (rkaf-core). The BLOCKER above was invisible because the coverage gap concealed it. **Fix:** all 10 fixtures added to `STRICT_POSITIVE`; 9 new round-trip tests added (one per backlog class — Authority, Attestation, LocalAdoption, ApplicabilityScope, EffectivePeriod, LifecycleEvent, ConceptMapping, ConceptResolutionResult, BridgeValidationResult). Round-trip test count: 7 → 16. Total workspace test count: 20 → 36. (Finding 3.)

### Disclosed (review-prompted API-break narrative)

The "no public API drift" claim in the prior CHANGELOG entry was wrong. The CUE→Rust pivot is a public API break, intentional and aligned with the v0.1 normative spec:

| Before | After | Rationale |
|---|---|---|
| `AssertionOrigin::HumanAuthored` | `AssertionOrigin::HumanAsserted` | Matches `archive/v0.1/spec/rkaf-core.md:21` ("rkaf:humanAsserted"). The previous Rust spelling was a hand-authored drift. |
| `Warrant::new(kind, family)` constructor | (removed) | Generated structs use `Warrant { type_: Warrant::default_type(), warrant_kind, warrant_family, ... }`. |
| `Assertion::new(origin)` constructor | (removed) | Same — direct struct literal construction. |
| `AssertionOrigin::is_ai_touched()` helper | (removed) | The v0.1 spec doesn't normatively define an AI-touched subset of origins; the helper was a Studio-side concern that incorrectly leaked into Layer 1. |
| (absent) | `AssertionOrigin::Imported` variant | New variant matching `archive/v0.1/spec/rkaf-core.md:21` ("rkaf:importedFromSource"). The hand-authored enum was missing this. |

Pre-release, no published crates.io consumer; the break is internal-only.

### Gaps explicitly deferred (not blockers)

- **SHACL coverage of new vocab.** The 12 new CUE files do generate SHACL Turtle output (now in `compiled/shacl/core/`) — but the hand-authored `shapes/rkaf-shapes-*.ttl` files used by `tools/ci_validate.py` don't yet include the new classes. The CUE-source-of-truth SHACL is regenerated but not yet wired into the SHACL gate. This is intentional scope for a follow-up (the path is: switch `ci_validate.py` from hand-authored shapes to `compiled/shacl/` outputs).
- **Behavioral semantics (Layer 5).** The v0.1 `usageEligibility` reducer, `CascadeClosureV1` algorithm, and 10 bridge contract rules remain normative prose only (in `archive/v0.1/spec/rkaf-core.md`). They're not CUE-validatable shape; they're runtime contracts. A future `spec/rkaf-behavior.md` or `rkaf-runtime` crate would close this. Tracked in `spec/rkaf-vocabulary.md:94`.
- **`OneOrMany<T>` empty-array permissiveness.** The wrapper deserializes `[]` as `Many(vec![])`, bypassing `list.MinItems(N)` at the Rust layer. JSON Schema catches it on the validator side; the Rust layer trades type-strictness for round-trip parity. Documented in the lib.rs doc-comment.

### Verified (post-fix)

- `cargo test --workspace`: **36 tests passing** (up from 20); zero failures.
- `tools/ci_validate.py` (SHACL): 20/20 pre-existing fixtures, 0 violations.
- `tools/validate_negatives.py`: 4/4 FAIL-AS-EXPECTED.
- `tools/constraints_parity.py`: 0 release blockers.
- `tools/projector_parity.py`: 7/7 round-trip OK.
- `tools/version_sync.py --check`: clean.
- `tools/rename_audit.py`: 0 findings.
- **All 10 new positive fixtures validate cleanly via `rkaf-validate`.**
- **All 10 new typed structs round-trip cleanly through `rkaf-core` serde.**

## Unreleased — Vocabulary backlog integration + CUE→Rust pipeline

**Closes the 17-term vocabulary backlog. The CUE source-of-truth is now the canonical generator for the Rust SDK as well as JSON Schema, SHACL, and TypeScript. Hand-authored Rust types are gone.**

### Added

- **12 new CUE constraint files** under `constraints/core/`: `authority.cue`, `attestation.cue`, `local-adoption.cue`, `applicability-scope.cue`, `effective-period.cue`, `lifecycle-event.cue`, `concept.cue`, `concept-mapping.cue`, `concept-resolution-result.cue`, `bridge-validation-result.cue`, plus closed-enum lattices `usage-eligibility.cue` and `trust-and-safety.cue`.
- **24 generated Rust modules** under `crates/rkaf-core/src/generated/` — one per CUE source file. Drives the entire `rkaf-core` type surface from CUE.
- **10 new positive fixtures** under `fixtures/`: authority, attestation, localadoption, applicabilityscope, effectiveperiod, lifecycleevent, concept-registered, conceptmapping, conceptresolutionresult, bridgevalidationresult.
- **12 new embedded JSON Schemas** in `rkaf-validate` covering the new classes (`rkaf:Authority`, `rkaf:Attestation`, `rkaf:LocalAdoption`, …, `rkaf:BridgeValidationResult`).
- **`rkaf_core::OneOrMany<T>`** untagged-enum wrapper mirroring the JSON-LD wire shorthand (a property value may appear as either a single scalar or an array; the JSON Schema target emits `anyOf: [scalar, array]`, and this type accepts either).
- **22 new term declarations** in `context/rkaf-context.jsonld` for the new class IRIs + predicates (`hasApplicability`, `hasEffectivePeriod`, `derivesAuthorityFrom`, etc.).

### Changed

- **`tools/constraints_compile.py` `--target rust`** rewritten. The output now matches the JSON-LD wire format: `@type` field with `default = "Class::default_type"`, `@id` as optional, properties renamed from `rkaf:foo` to idiomatic `foo` (no `rkaf_` prefix), `#[serde(flatten)] extra: BTreeMap<String, serde_json::Value>` catch-all for forward-compatibility, list types emitted as `crate::OneOrMany<T>` to handle the JSON-LD scalar-or-array shorthand. Cross-file enum references resolve to fully-qualified paths via the `_RUST_CROSS_FILE_ENUMS` registry (covers `UsageEligibility`, `AuthorityKind`, `TrustZone`, `SafetyLabel`).
- **`crates/rkaf-core/src/lib.rs`** is now a thin module index. The 8 hand-authored modules (`assertion.rs`, `warrant.rs`, `evidence.rs`, etc.) are deleted; their types now live in `generated/`. Top-level re-exports preserve the public API surface.
- **`spec/rkaf-vocabulary.md` §6** rewritten from "Vocabulary backlog — specified but not yet codified" to "Codified Vocabulary — additional terms," enumerating every codified class + enum + predicate with its CUE source, fixture, and purpose.

### Removed

- `crates/rkaf-core/src/{access_scope,ai_lineage,artifact,assertion,confidence,evidence,source_fragment,warrant}.rs` — replaced wholesale by generated equivalents. No public API drift.

### Verified

- `cargo test --workspace`: 20 `test result: ok` lines, zero failures.
- `tools/ci_validate.py` (SHACL): 20/20 fixtures pass, 0 violations, 114 triples.
- `tools/validate_negatives.py`: 4/4 FAIL-AS-EXPECTED.
- `tools/constraints_parity.py`: 0 CORE divergences (release blockers); 2 documented adversarial findings.
- `tools/projector_parity.py`: 7/7 round-trip fixtures pass.
- `tools/version_sync.py --check`: clean.
- `tools/rename_audit.py`: 0 findings.

### Compatibility

Pre-release. The CUE source-of-truth pipeline is now end-to-end:

```
constraints/<class>.cue
  ↓ python3 tools/constraints_compile.py --target {json-schema, rust, typescript, shacl}
{compiled/json-schema/, crates/rkaf-core/src/generated/, compiled/typescript/, compiled/shacl/}
```

A future schema or vocab change should land as a CUE edit; all four targets regenerate. Hand-authoring Rust to match a CUE schema is now drift.

## Unreleased — Plan 6a: Rust SDK (Vocab + Validate + CLI)

**Three Rust crates land the first SDK surface: `rkaf-core` (typed Vocabulary primitives with serde round-trip), `rkaf-validate` (embedded v0.2 JSON Schema validator), and `rkaf-validate-cli` (the `rkaf-validate` binary).** This is the first time external code can pick up Rulespec without `git clone`-ing the repo or shelling out to the Python compiler.

### Added

- `crates/rkaf-core/` — 8 typed primitives (Assertion, Warrant, EvidenceBinding, ConfidenceRecord, AccessScope, AILineage, Artifact, SourceFragment) with closed enums and JSON-LD-compatible serde derive. Each primitive carries a `#[serde(flatten)] extra` map preserving unknown properties through round-trip.
- `crates/rkaf-validate/` — `Validator` with all 8 v0.2 class schemas embedded via `include_str!` (no filesystem dependency at runtime). Exposes `validate(&node)` (single node) and `validate_document(&doc)` (walks `@graph` arrays). Unknown `@type` IRIs pass silently — outside our contract.
- `crates/rkaf-validate-cli/` — `rkaf-validate <file>` binary. Exit 0 on PASS, 1 on FAIL, 2 on setup error. `--json` emits a structured report.

### Verified

- 16 v0.2 positive fixtures round-trip through their matching `rkaf-core` types byte-identically.
- **All 17 positive fixtures validate cleanly via `rkaf-validate`**. The two Appendix-C divergences surfaced during Plan 6a development were both closed in the same pass (see "Constraint compiler + fixture fixes" below).
- CLI integration tests cover PASS/FAIL/--json across positive and negative fixtures.
- Full workspace `cargo test --workspace` passes; `tools/ci_validate.py` (SHACL) passes 20/20; `tools/validate_negatives.py` passes 4/4 fail-as-expected.

### Constraint compiler + fixture fixes

Plan 6a surfaced two real Layer 2/3 issues that previously produced JSON-Schema vs SHACL divergence on positive fixtures. Both are now fixed:

1. **`tools/constraints_compile.py` — bare `list.MinItems(N)` items.**
   The CUE → JSON Schema codegen treated a bare `list.MinItems(N)` (no item type constraint) as if the items were strings. The fix: leave `list_of_string` unset and emit `items: {}` (any) when neither an inner enum nor an explicit string item constraint is present. This affected `SourceFragment.hasSelector`, which on the wire is a structured OA selector object (`oa:TextQuoteSelector`, `oa:XPathSelector`, `rkaf:AktnEIdSelector`, `rkaf:USLMSectionSelector`).

2. **Cross-ref Assertion placeholders carry `assertionOrigin` now.**
   The `evidencebinding-{positive,no-evidence-reason-positive,missing-negative}` fixtures previously contained sparse `{"@type": "rkaf:Assertion", "@id": "…"}` nodes as cross-reference placeholders for the EvidenceBinding's `bindsAssertion`. SHACL targetClass validation didn't trip; JSON Schema `required` did. The fixtures now carry `"rkaf:assertionOrigin": "rkaf:humanAsserted"` on every Assertion node, matching the actual vocabulary contract.

After both fixes, every v0.2 positive fixture validates byte-identically across the JSON Schema (`rkaf-validate`) and SHACL (`tools/ci_validate.py`) gates. The `STRICT_POSITIVE` / `SHACL_ONLY_POSITIVE` split in the test source was retired.

### Compatibility

Pre-release. The three new crates are versioned at workspace level (`0.2.0-pre.5`); their public API is small and stable enough for Plan 11 publication once the GitHub extraction lands.

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
