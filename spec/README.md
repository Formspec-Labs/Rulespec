# Rulespec Specifications

This directory contains the two specification documents that define Rulespec semantics. The text in these files is **semantically identical to v0.1-rc1**; the v0.1.1 release fixed shape implementations and patched fixtures but introduced no spec text changes.

## Documents

### `rkaf-core-v0.1.md`

The core Rulespec specification. Defines:

- **Assertions** (`rkaf:RelationshipAssertion`): subject-predicate-object claims with trust zone, safety label, evidence
- **Evidence bindings** (`rkaf:EvidenceBinding`): role-typed evidence backing an assertion
- **Attestations** (`rkaf:Attestation`): authoritative actions on assertions (endorse, object, qualify, retract, adopt, etc.)
- **Local adoption** (`rkaf:LocalAdoption`): consumer-side authority to use an assertion in a scope
- **Authority chains** (`rkaf:AuthorityChainHop`): traversal of `hasAuthority` and `derivesAuthorityFrom` edges
- **Applicability context** (`rkaf:ApplicabilityContext`): where an assertion applies
- **Bridge model** (`rkaf:BridgeValidationResult`): structured output for consumer-facing validation
- **Generated work products** (`rkaf:GeneratedWorkProduct`): consumer artifact overlay type
- **Lifecycle packets**: `AmendmentPacket`, `RescissionPacket`, `SupersessionPacket`, `MaterialRevisionPacket`
- **Revalidation events** (`rkaf:RevalidationEvent`, `rkaf:RevalidationClosureEvent`)
- **Point-in-time exceptions** (`rkaf:PointInTimeException`) with evaluation anchors
- **Cascade closure** (`rkaf:CascadeClosureV1`): the transitive closure algorithm for affected sets

The Core spec is the load-bearing surface. All shape files anchor on specific sections of this document.

### `rkaf-concept-registry-v0.1.2.md`

The concept registry specification. Defines:

- **Registered concepts** (`rkaf:RegisteredConcept`): canonical concept IRIs in a registry
- **Local concepts** (`rkaf:LocalConcept`): consumer-side concepts defined in a local scope
- **Concept registries** (`rkaf:ConceptRegistry`): authoritative sources of concepts
- **Concept minting authorities** (`rkaf:ConceptMintingAuthority`): who can introduce new concepts
- **Mapping assertions**: `RelationshipAssertion` with `skos:closeMatch` / `skos:exactMatch` / `skos:broadMatch` / `skos:narrowMatch` / `skos:relatedMatch` predicate
- **Mapping applicability contexts** (`rkaf:MappingApplicabilityContext`): where a mapping applies operationally
- **Concept resolution results** (`rkaf:ConceptResolutionResult`): bridge-side resolution output with usage ceiling
- **Suggested remediation** (`rkaf:SuggestedRemediation`): bridge-side remediation guidance
- **Concept lifecycle packets** (`rkaf:ConceptLifecyclePacket`): split, merge, replacedBy, retire events
- **Mapping conflicts** (`rkaf:MappingConflict`): conflicting mappings with severity
- **Bridge consumer registration** (`rkaf:BridgeConsumerRegistration`): consumer capability declaration

### Three conformance levels

The ConceptRegistry spec defines three conformance levels:

- **ConceptRegistry-Core** — base structural conformance (fully structurally enforced in v0.1.1)
- **ConceptRegistry-Lifecycle** — structurally enforced; runtime cache/TTL behavior remains bridge-implementation conformance
- **ConceptRegistry-Federated** — partial; mapping conflicts validated; cross-org sync deferred

## What's NOT in spec/

The spec defines the data model and the bridge contract. It does NOT define:

- Consumer-system internals (Formspec schema, WOS workflow runtime, search ranking, CMS storage, etc.)
- Behavioral correctness checks (cascade closure output, reducer output, registry cache TTL) — these belong in the runtime conformance test layer planned for v0.2

## Spec evolution policy

Spec text changes require deliberate discussion. The shape-batch discipline (see `CONTRIBUTING.md`) assumes spec text is stable; shapes and fixtures are the artifacts that iterate. If a batch reveals a spec ambiguity, it's raised as an issue and resolved before any shape or fixture patch is applied.

Semantic versioning for spec text:

- Bug fix or clarification (no semantic change): no version bump
- New optional structure: minor version bump (`v0.1` → `v0.2`)
- Breaking semantic change: major version bump (`v0.1` → `v1.0` or new major)

v0.1.1 contains NO spec text changes from v0.1-rc1.
