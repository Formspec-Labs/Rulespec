# Rulespec Concept Registry — v0.2

**Status:** Pre-release, normative.
**Supersedes:** `spec/rkaf-concept-registry-v0.1.2.md` (historical).
**Companion docs:** `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`.

## 1. Purpose

The Concept Registry stores canonical concepts, mappings between concepts, applicability contexts, lifecycle events on concepts, and conflict resolution among competing canonical assignments.

Concept resolution establishes **semantic compatibility**. It does NOT establish **policy authority**. A resolved concept may satisfy a `rkaf:collectsEvidenceType` or `rkaf:requiresEvidenceType` reference, but the artifact still requires its own Rulespec justification chain (terminating at a valid `rkaf:hasAuthority`, `rkaf:hasWarrant`, or scoped `rkaf:LocalAdoption`) and its own effective `rkaf:usageEligibility`.

## 2. Primitives

(Inherited from v0.1.2 with three v0.2 changes: SKOS-bound mapping predicates, Workspace scoping, generalized warrant on mappings.)

### 2.1 rkaf:Concept

(Definition preserved from `spec/rkaf-concept-registry-v0.1.2.md` §2.1.)

Required properties on a canonical `rkaf:RegisteredConcept`:
- `@type`: includes `skos:Concept` and `rkaf:RegisteredConcept`.
- `skos:prefLabel` (1).
- `rkaf:managedByRegistry` (1, IRI).
- `rkaf:conceptScope` (1, closed enum).
- `rkaf:conceptStatus` (1, closed enum).
- `rkaf:registeredAt` (1, `xsd:dateTime`).

Local concepts use `rkaf:LocalConcept` typed nodes, with `rkaf:definedInScope` (IRI of the owning Workspace or organizational scope).

### 2.2 rkaf:ConceptMapping

The mapping relation MUST use a SKOS predicate from the closed set:

`skos:closeMatch`, `skos:exactMatch`, `skos:broader`, `skos:narrower`, `skos:related`, `skos:mappingRelation`.

This replaces v0.1.2's bespoke `rkaf:mappingRelation` enum. SKOS owns this vocabulary; do not duplicate.

A `rkaf:ConceptMapping` is a `rkaf:RelationshipAssertion` whose `assertsPredicate` is one of the SKOS predicates above and whose subject/object are concept IRIs. It inherits the full assertion model — evidence, attestation, scope, adoption, lifecycle — from `spec/rkaf-core.md` §6.

### 2.3 rkaf:ConceptResolutionResult

(Inherited from v0.1.2 §2.3.)

Structured output of registry lookup. Carries `rkaf:resolutionStatus`, `rkaf:resolutionMethod`, `rkaf:cacheStatus`, `rkaf:usageCeiling`, and the resolved `rkaf:mappingAssertion` IRI when resolution proceeded via a mapping. AI consumers MUST consume the `rkaf:usageCeiling` and respect it (no draft-generation usage on `rkaf:reviewQueueOnly` resolutions).

### 2.4 rkaf:Workspace scoping

A Concept MAY be scoped to a `rkaf:Workspace` via `rkaf:scopedToWorkspace` (1, IRI). Workspace-scoped concepts are federable to peer workspaces declaring mutual trust per Layer 3 federation (Plan 4).

URN scheme: `urn:rkaf:workspace:<workspaceId>/<localConceptId>` resolves within the workspace.

### 2.5 Justification on a mapping

A `rkaf:ConceptMapping` MAY carry a `rkaf:hasJustification` whose `rkaf:Justification` carries `rkaf:hasWarrant` (warrant kind from any family, not only legal). v0.1.2's `rkaf:hasAuthority` remains valid as the legal-family specialization (`rkaf:Authority rdfs:subClassOf rkaf:Warrant`).

## 3. Conflict resolution

(Inherited from v0.1.2 §3.)

Conflict resolution among competing canonical assignments uses the v0.1.2 procedure: applicability scope intersection, attestation count, recency, then registry-declared tiebreaker. SHACL shape `rkaf:ConceptResolutionConflictShape` (in `shapes/rkaf-shapes-conceptregistry-v0.1.ttl`) is preserved unchanged.

## 4. Lifecycle on Concept

(Inherited from v0.1.2 §4.)

Concept lifecycle events — `rkaf:registered`, `rkaf:deprecated`, `rkaf:superseded`, `rkaf:split`, `rkaf:merged` — are carried by the v0.1 `rkaf:LifecycleEvent` mechanism. Cascade algorithm `rkaf:CascadeClosureV1` is preserved. New: `rkaf:safeAutomaticMigrationStatus` MAY take `rkaf:noSafeAutomaticMigration` to declare manual disambiguation required.

## 5. SHACL

Validated by `shapes/rkaf-shapes-conceptregistry.ttl` (new) **plus** the inherited `shapes/rkaf-shapes-conceptregistry-v0.1.ttl` (lifecycle and applicability rules).

`skos:prefLabel(1)` is enforced at **L1** (CUE → `constraints/core/concept.cue` → `compiled/json-schema/core/concept.schema.json`) and **L3** (`compiled/shacl/core/concept.ttl` — `sh:property [ sh:path skos:prefLabel ; sh:minCount 1 ]` on both `rkaf:RegisteredConceptShape` and `rkaf:LocalConceptShape`). Producers omitting `skos:prefLabel` are rejected at both validation layers.

## 6. Compatibility

None with v0.1.2. Migration not supported. Replace.
