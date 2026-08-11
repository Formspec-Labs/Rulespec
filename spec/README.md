# Rulespec Specifications

This directory holds the active normative specifications. The CUE source under `constraints/core/` (universal kernel), `constraints/analysis/` (the generic document-analysis module), and `constraints/profiles/` (domain profiles) is the source of truth for shape; `tools/constraints_compile.py` projects each CUE file to JSON Schema, SHACL, TypeScript, and Rust targets. The spec markdown files in this directory describe vocabulary, normative behavior, and the layered architecture.

## Documents

### `rkaf-core.md`

Normative architecture and conformance — the load-bearing surface above the vocabulary. Defines the framework's layered model (vocabulary, constraints, registries, projectors, SDKs, conformance, corpora), the overlay pattern, anchoring contract, adoption-depth gradient, and conformance levels.

### `rkaf-vocabulary.md`

Enumerates every codified Rulespec class and predicate. Two documentation tiers, and the difference is deliberate:

- **Per-term tables** — one row per term, with IRI, kind, domain, range,
  cardinality, and required fixtures. These cover the universal primitives
  (§§4.1–4.6 of `rkaf-core.md`), concept vocabulary, lifecycle, assignments,
  and resolution (§4.7 plus `rkaf-concept-registry.md`), the document-analysis
  module, the Experimental US rulemaking-process module, the RefSpec
  application profile, the Studio-derived promotions, and the abstract
  anchoring contract.
- **Per-class tier (§6)** — one row per class with its CUE source, fixture, and purpose, plus bullet sections for the closed enums and the traversal predicates. A class here is fully specified by its CUE file; the row records what it is FOR.

`tools/vocab_audit.py` enforces the floor across both tiers: every class a CUE file compiles must appear as `rkaf:<Term>`, and every fixture named in a `Required fixtures` cell must exist.

### `rkaf-conformance.md`

Defines the two conformance paths: L0 vocabulary fidelity for non-JSON-LD carriers, and the cumulative L1–L4 JSON-LD parse, shape, constraint, and behavior levels. It also specifies the L0 carrier-mapping block and partner self-certification formats.

### `rulespec-releases.md`

Defines the independent `RulespecCoreRelease` and `ExtrapolationRelease`
artifacts, canonical JSON and stable identifiers, pinned upstream inputs,
validation and selection receipts, reversible processing-segment projections,
coverage, and the sealed M2 fail-closed controls.

Read its execution-boundary correction banner (2026-08-02) first: the
Extrapolator consumes prepared segments and verifies submitted baseline and
selection receipts. It does not segment documents, execute baseline validation,
or run a selection engine, and §7 lists the duties that have no owner.

### `rulespec-source-catalog-release.md`

Defines the `SourceCatalogRelease` v1 candidate: the bundle shape and its one
member manifest, content-derived release identity, the two canonical set
digests over `U` and `S`, the source item with its exact source-native
metadata and normalized MVP fields, source-observed topics held apart from
RefSpec concepts, candidate renditions, the five selection dispositions, the
diagnostic codes and their first-failure order, the sealed valid and invalid
fixture corpus, and the candidate bundle digest.

Rulespec Core owns these schemas; SpicyRegs owns the records they carry
(REF-024). `DocumentRelease` is a separate root with a separate owner and is
not defined there.

### `rkaf-analysis.md`

The document-analysis module — generic, jurisdiction-free contracts for comparing relations across document versions. Defines `RelationChangeEvent` (source-stated adoption, removal, suspension, replacement, with polarity structurally absent), `RelationComparisonContext` (the immutable frame and the five closed comparison outcomes), `ResolverProofRecord` / `ResolverProofIssuer` (content-bound gate decisions, `pass`/`fail`/`unknown` plus the six scope relations), the neutral `RelationFinding`, and the Experimental, **disabled** `ClosureClaim`. It sits between the kernel and the profiles: the kernel never depends on it, it may compose kernel shapes, and profiles may depend on it. Domain interpretation — legal effect, policy exclusion, rescission — belongs to profiles, never here.

### `rkaf-rulemaking.md`

Experimental US notice-and-comment rulemaking module. Specializes the general
Artifact-to-subject and qualified-relation patterns for durable
RegulatoryAgendaItems, editioned RegulatoryAgendaObservations, independently
identified Proceedings, CommentPeriods, published-document links, CFR targets,
and authority chains.

### `rkaf-concept-registry.md`

The governed-concept specification — companion to `rkaf-vocabulary.md`.
Defines multilingual native SKOS carriage, typed notation, scheme-internal
multi-parent hierarchy, `RegisteredConcept`, `LocalConcept`, mappings,
complete-membership release pins, concept lifecycle events, and
`ConceptResolutionResult`. Registry and actor IRIs remain externally
described; the retired v0.1 `ConceptRegistry` and `ConceptMintingAuthority`
object models are not active classes. `ConceptScheme` and `ConceptAssignment`
are normatively introduced in `rkaf-core.md` §4.7 and detailed here.

### `rkaf-refspec.md`

The portable open-label profile used with RefSpec vocabulary releases. It
defines the `rkaf:openLabel` `ValueAssertion`, its required facet and assignment
role, language materialization, provenance, and grounded evidence. Rulespec
Extrapolator owns the portable profile release boundary; RefSpec owns source
capture, managed vocabulary releases, coverage, crosswalk evidence, and static
atlas publication. Rulespec Extrapolator owns derived selection and
accepted-output decisions; SpicySearch owns query processing, indexes, and
ranking. Rulespec Core neither depends on nor exports the profile.

> **Scope note (2026-08-02, annotation in place — nothing above is rewritten):**
> "owns derived selection and accepted-output decisions" names the *record and
> validation contract*, which is real and enforced. The producing processes
> behind selection and accepted-output have no owner today and are parked in
> [`spec/rulespec-releases.md` §7](rulespec-releases.md#7-parked-duties-with-no-owner).
> Read those sentences as shapes a receipt must satisfy, never as capabilities
> that run. This is the twin of the note at
> [`spec/rkaf-refspec.md`](rkaf-refspec.md).

### `rkaf-behavior.md`

Layer 5 (runtime) behavioral semantics — the contracts that are *not* CUE-validatable shape: the `usageEligibility` reducer, the `CascadeClosureV1` cascade-closure algorithm, the 10 bridge contract rules, point-in-time-exception evaluation, and lifecycle packet ingest semantics. The full v0.1 normative prose is preserved at `archive/v0.1/spec/rkaf-core-v0.1.md`; this document is the active-tree summary plus codification roadmap.

### `projectors/json-schema.md`, `projectors/json-ld.md`, `projectors/openapi.md`

Carrier conventions per source spec §8.1 — how a Rulespec overlay attaches to JSON Schema, JSON-LD, and OpenAPI documents. Each projector implements Attach / Extract / Validate / RoundTrip / Derive.

## What's NOT in spec/

The spec defines the data model, the carrier conventions, and the behavioral contracts. It does NOT define:

- Consumer-system internals (Formspec schema, WOS workflow runtime, Policy Studio compiler, etc.) — those live in their own repos.
- Cryptographic anchoring substrates (Trellis, COSE, JWS, VC, Sigstore, IPFS) — Rulespec defines the abstract anchoring contract; the bindings depend on Rulespec, never the reverse.

## Where the historical v0.1 line lives

The pre-rebrand PKAF v0.1.1 corpus is preserved at `archive/v0.1/` (spec, shapes, context, fixtures, release manifest). It's not loaded by any active gate; it's reference material for the `rkaf-behavior.md` codification work and any consumer wanting to understand the supersession path.

## Spec evolution policy

Pre-1.0, no migration shims. CUE source is authoritative for shape; spec markdown is authoritative for behavior. A vocab addition lands as a CUE edit + spec text update + at least one positive fixture; the four target projections (JSON Schema, Rust, TypeScript, SHACL) regenerate together via `tools/constraints_compile.py`. Tests gate every fixture through both `rkaf-validate` (JSON Schema) and `tools/ci_validate.py` (SHACL).
