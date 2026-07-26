# Rulespec Specifications

This directory holds the active normative specifications. The CUE source under `constraints/core/` (universal kernel) and `constraints/profiles/` (domain profiles) is the source of truth for shape; `tools/constraints_compile.py` projects each CUE file to JSON Schema, SHACL, TypeScript, and Rust targets. The spec markdown files in this directory describe vocabulary, normative behavior, and the layered architecture.

## Documents

### `rkaf-core.md`

Normative architecture and conformance — the load-bearing surface above the vocabulary. Defines the framework's layered model (vocabulary, constraints, registries, projectors, SDKs, conformance, corpora), the overlay pattern, anchoring contract, adoption-depth gradient, and conformance levels.

### `rkaf-vocabulary.md`

Enumerates every codified Rulespec class and predicate, with the CUE source file, fixture, and purpose for each. §5 covers the v0.2 normative-tier primitives (Assertion, Warrant, Artifact, SourceFragment, EvidenceBinding, ConfidenceRecord, AccessScope, AILineage, RetentionPolicy, MappingState, Workspace, anchoring). §6 covers the codified additional terms (Authority, Attestation, LocalAdoption, ApplicabilityScope, EffectivePeriod, LifecycleEvent, Concept, ConceptMapping, ConceptResolutionResult, BridgeValidationResult, closed-enum lattices, predicates).

### `rkaf-conformance.md`

Defines the two conformance paths: L0 vocabulary fidelity for non-JSON-LD carriers, and the cumulative L1–L4 JSON-LD parse, shape, constraint, and behavior levels. It also specifies the L0 carrier-mapping block and partner self-certification formats.

### `rkaf-rulemaking.md`

Experimental US notice-and-comment rulemaking module. Specializes the general
Artifact-to-subject and qualified-relation patterns for durable
RegulatoryAgendaItems, editioned RegulatoryAgendaObservations, independently
identified Proceedings, CommentPeriods, published-document links, CFR targets,
and authority chains.

### `rkaf-concept-registry.md`

The concept registry specification — companion to `rkaf-vocabulary.md` §6. Defines `RegisteredConcept`, `LocalConcept`, `ConceptRegistry`, `ConceptMintingAuthority`, the SKOS mapping predicates, `MappingApplicabilityContext`, `ConceptResolutionResult`, and the three conformance levels (Core, Lifecycle, Federated).

### `rkaf-behavior.md`

Layer 5 (runtime) behavioral semantics — the contracts that are *not* CUE-validatable shape: the `usageEligibility` reducer, the `CascadeClosureV1` cascade-closure algorithm, the 10 bridge contract rules, point-in-time-exception evaluation, and lifecycle packet ingest semantics. The full v0.1 normative prose is preserved at `archive/v0.1/spec/rkaf-core.md`; this document is the active-tree summary plus codification roadmap.

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
