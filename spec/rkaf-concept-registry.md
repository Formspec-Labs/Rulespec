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

`skos:exactMatch`, `skos:closeMatch`, `skos:broadMatch`, `skos:narrowMatch`, `skos:relatedMatch`, `skos:broader`, `skos:narrower`, `skos:related`, `skos:mappingRelation`.

v0.2 ADDS `skos:broadMatch`, `skos:narrowMatch`, and `skos:relatedMatch`; no value was removed, and every mapping valid before this release stays valid. SKOS draws a real line the earlier set collapsed: `skos:broader` / `skos:narrower` / `skos:related` are semantic relations WITHIN one scheme, while the `*Match` properties are the mapping properties used BETWEEN schemes (SKOS Reference §10). Aligning a local concept to an external thesaurus needs the `*Match` half; without it a producer had to reach for the in-scheme relation and misstate the alignment as if both concepts lived in one vocabulary.

This replaces v0.1.2's bespoke `rkaf:mappingRelation` enum. SKOS owns this vocabulary; do not duplicate.

The closed set is declared twice — `#SkosMappingPredicate` in `constraints/core/concept-mapping.cue` and the `sh:in` list in `shapes/rkaf-shapes-conceptregistry.ttl` — and the two MUST stay identical. SHACL is conjunctive: a value present in one list and absent from the other is rejected by the merged shape suite regardless of what the compiled artifact says.

A `rkaf:ConceptMapping` is a `rkaf:RelationshipAssertion` whose `assertsPredicate` is one of the SKOS predicates above and whose subject/object are concept IRIs. It inherits the full assertion model — evidence, attestation, scope, adoption, lifecycle — from `spec/rkaf-core.md` §6.

### 2.3 rkaf:ConceptResolutionResult

(Inherited from v0.1.2 §2.3.)

Structured output of registry lookup. Carries `rkaf:resolutionStatus`, `rkaf:resolutionMethod`, `rkaf:cacheStatus`, `rkaf:usageCeiling`, and the resolved `rkaf:mappingAssertion` IRI when resolution proceeded via a mapping. AI consumers MUST consume the `rkaf:usageCeiling` and respect it (no draft-generation usage on `rkaf:reviewQueueOnly` resolutions).

### 2.4 rkaf:Workspace scoping

A Concept MAY be scoped to a `rkaf:Workspace` via `rkaf:scopedToWorkspace` (1, IRI). Workspace-scoped concepts are federable to peer workspaces declaring mutual trust per Layer 3 federation (Plan 4).

URN scheme: `urn:rkaf:workspace:<workspaceId>/<localConceptId>` resolves within the workspace.

### 2.5 Justification on a mapping

A `rkaf:ConceptMapping` MAY carry a `rkaf:hasJustification` whose `rkaf:Justification` carries `rkaf:hasWarrant` (warrant kind from any family, not only legal). v0.1.2's `rkaf:hasAuthority` remains valid as the legal-family specialization (`rkaf:Authority rdfs:subClassOf rkaf:Warrant`).

### 2.6 rkaf:ConceptScheme and facets

A `rkaf:ConceptScheme` is one facet's controlled category system, compatible with `skos:ConceptScheme`. Its normative shape is defined in `spec/rkaf-core.md` §4.7.1 and is not restated here.

Two rules matter to the registry:

1. Every `rkaf:RegisteredConcept` and `rkaf:LocalConcept` MUST carry `skos:inScheme` (1). A facet-free concept is the term that later merges with a same-spelled term from another facet.
2. A scheme MUST declare `rkaf:schemeFacet` and MUST be owned — either `rkaf:managedByRegistry` (federation-shared) or `rkaf:definedInScope` (workspace-local). That disjunction is the same seam this section already draws between registered and local concepts, applied to their container.

SKOS owns scheme membership, top concepts, labels, and definitions. Rulespec adds the facet declaration and the ownership rule and nothing else; in particular it declares no class range over `skos:inScheme`, so a concept MAY belong to an external `skos:ConceptScheme`.

### 2.7 Promotion

The normal path from retrieval candidate to shared vocabulary is:

```text
retrieval candidate
  -> LocalConcept
  -> evidence-backed assignments
  -> measured usefulness and quality
  -> human-reviewed promotion packet
  -> RegisteredConcept
```

Promotion is rare. It requires a definition, scope, examples, counterexamples, mappings, usage evidence, conflicts, lineage, a steward, a human approver, and a rationale. Of those, `skos:definition` is the one a shape can check, and it is REQUIRED when `rkaf:conceptStatus` is `rkaf:promoted` (`spec/rkaf-core.md` §4.7.2).

Model confidence, query popularity, and click counts MAY guide review. They never establish meaning and MUST NOT promote a concept. Promotion creates a separate reviewed record; it does not rewrite the local history that produced it.

### 2.8 rkaf:ConceptAssignment

Assignments of concepts to Artifacts and SourceFragments are normatively defined in `spec/rkaf-core.md` §4.7.3. They are registry-adjacent rather than registry-owned: an assignment cites a concept, and the concept's governance stays with its scheme and registry.

The registry-relevant consequence is that a `rkaf:LocalConcept` accumulates evidence-backed assignments before it is eligible for the promotion packet above, and those assignments are themselves append-only, evidence-bearing records — not counters.

## 3. Conflict resolution

(Inherited from v0.1.2 §3.)

Conflict resolution among competing canonical assignments uses the v0.1.2 procedure: applicability scope intersection, attestation count, recency, then registry-declared tiebreaker. SHACL shape `rkaf:ConceptResolutionConflictShape` (in `shapes/rkaf-shapes-conceptregistry-v0.1.ttl`) is preserved unchanged.

## 4. Lifecycle on Concept

(Inherited from v0.1.2 §4.)

Concept lifecycle events — `rkaf:registered`, `rkaf:deprecated`, `rkaf:superseded`, `rkaf:split`, `rkaf:merged` — are carried by the v0.1 `rkaf:LifecycleEvent` mechanism. Cascade algorithm `rkaf:CascadeClosureV1` is preserved. New: `rkaf:safeAutomaticMigrationStatus` MAY take `rkaf:noSafeAutomaticMigration` to declare manual disambiguation required.

## 5. SHACL

Validated by `shapes/rkaf-shapes-conceptregistry.ttl` (new) **plus** the inherited `shapes/rkaf-shapes-conceptregistry-v0.1.ttl` (lifecycle and applicability rules).

`skos:prefLabel(1)` and `skos:inScheme(1)` are enforced at **L1** (CUE → `constraints/core/concept.cue` → `compiled/json-schema/core/concept.schema.json`) and **L3** (`compiled/shacl/core/concept.ttl` — `sh:property [ sh:path skos:prefLabel ; sh:minCount 1 ]` and `sh:property [ sh:path skos:inScheme ; sh:minCount 1 ; sh:maxCount 1 ]`, both on `rkaf:RegisteredConceptShape` and `rkaf:LocalConceptShape`). Producers omitting either are rejected at both validation layers. The `sh:maxCount 1` on `skos:inScheme` is a deliberate Rulespec narrowing of an unrestricted SKOS predicate — one concept, one facet; see Core §4.7.2.

## 6. Compatibility

None with v0.1.2. Migration not supported. Replace.
