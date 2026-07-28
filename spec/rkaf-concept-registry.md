# Rulespec Concept Registry — v0.2

**Status:** Pre-release, normative.
**Supersedes:** `archive/v0.1/spec/rkaf-concept-registry-v0.1.2.md`
(historical).
**Companion docs:** `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`,
`spec/rkaf-behavior.md`.

## 1. Purpose

This profile defines portable records for governed concepts, concept
assignments, mappings, immutable releases of any governed reference resource
(including entity registries and mapping sets), and concept resolution.
Rulespec owns these semantic and trust records. An application
owns ingestion, search indexes, deployment, cache policy, workflow, and user
interface state.

Concept resolution establishes semantic compatibility. It does not establish
policy authority or authorize use. Evidence, attestations, local adoption,
access scope, and consumer eligibility remain independent.

## 2. Native SKOS vocabulary carriage

SKOS owns concept-scheme semantics. Producers MUST use native
`skos:ConceptScheme`, `skos:Concept`, `skos:prefLabel`, `skos:altLabel`,
`skos:definition`, `skos:inScheme`, `skos:broader`, `skos:narrower`, and
`skos:related` properties with their SKOS meanings. Language-tagged labels and
definitions stay on those SKOS properties.

`rkaf:ConceptScheme` adds two Rulespec requirements:

- `rkaf:schemeFacet` identifies the question this scheme answers; and
- exactly one of `rkaf:managedByRegistry` or `rkaf:definedInScope` identifies
  its governing scope.

`rkaf:RegisteredConcept` carries `skos:prefLabel`, exactly one
`skos:inScheme`, `rkaf:managedByRegistry`, `rkaf:conceptScope`, and
`rkaf:registeredAt`. `rkaf:LocalConcept` carries `skos:prefLabel`, exactly one
`skos:inScheme`, `rkaf:definedInScope`, and `rkaf:conceptScope`.

`rkaf:conceptStatus` is not part of this release. Immutable release membership
records what a release contains. `rkaf:Attestation` records review or
publication decisions. `rkaf:LifecycleEvent` records deprecation,
supersession, split, and merge events. Producers MUST NOT collapse those facts
into a mutable status field on a concept.

## 3. Reference-resource releases

Every assignment and mapping endpoint MUST pin the exact
`rkaf:ReferenceResourceRelease` whose meaning it used. Core §4.1.1 defines the
generic release manifest, its membership modes, distributions, and RDFC-1.0
digest.

A pin used to validate an endpoint MUST name a release with
`rkaf:completeMembership`, and that release MUST list the endpoint concept in
`prov:hadMember`. Partial or non-enumerated membership can describe a release,
but absence from those manifests proves nothing and cannot validate a pin.

Release identity and publication are separate. A release becomes
publication-relevant for concept resolution only when:

1. its manifest is internally valid and digest-pinned;
2. an unrevoked `rkaf:Attestation` approves it for publication in the
   applicable scope; and
3. no effective `rkaf:LifecycleEvent` has withdrawn or superseded that
   publication for the same scope.

Applications may activate, index, cache, roll back, or deploy a release. Those
operations do not change its portable identity or publication attestation.

## 4. ConceptAssignment

`rkaf:ConceptAssignment` is a strict `rkaf:RelationshipAssertion`
specialization:

- `rkaf:assertsSubject` names the Artifact or SourceFragment;
- `rkaf:assertsPredicate` is one of `rkaf:assignmentPrimary`,
  `rkaf:assignmentSubstantive`, `rkaf:assignmentMention`, or
  `rkaf:assignmentContextual`;
- `rkaf:assertsObject` names the concept;
- `rkaf:assertionPolarity` is `rkaf:affirmed`; and
- `rkaf:assignedConceptRelease` pins the complete release containing the
  concept.

It inherits `rkaf:assertionOrigin`, `rkaf:epistemicBasis`, provenance,
confidence, scope, retention, and consumer disposition from the durable
assertion envelope. Evidence uses the universal inverse
`rkaf:EvidenceBinding` path. A fragment-backed binding carries
`rkaf:bindsSourceFragment`, `rkaf:evidenceRole`, and
`rkaf:evidentiaryFunction`.

The retired assignment-specific shadow fields are non-conforming:
`rkaf:assignmentSubject`, `rkaf:assignmentSubjectType`,
`rkaf:assignedConcept`, `rkaf:assignmentRole`,
`rkaf:assignmentDerivation`, `rkaf:assignmentEvidence`,
`rkaf:assignmentEvidenceScheme`, `rkaf:supportingAssignment`, and
`rkaf:assignmentPolicyVersion`.

## 5. ConceptMapping

`rkaf:ConceptMapping` is a strict `rkaf:RelationshipAssertion`
specialization:

- `rkaf:assertsSubject` names the source concept;
- `rkaf:assertsPredicate` is exactly one of `skos:exactMatch`,
  `skos:closeMatch`, `skos:broadMatch`, `skos:narrowMatch`, or
  `skos:relatedMatch`;
- `rkaf:assertsObject` names the target concept;
- `rkaf:assertionPolarity` is `rkaf:affirmed`;
- `rkaf:sourceConceptRelease` pins the complete release containing the
  subject; and
- `rkaf:targetConceptRelease` pins the complete release containing the object.

`skos:broader`, `skos:narrower`, and `skos:related` are in-scheme semantic
relations, not mapping predicates. `skos:mappingRelation` is an abstract
super-property, not a concrete claim. All four are non-conforming as a
ConceptMapping predicate.

The canonical proposition fields replace
`rkaf:sourceConcept`, `rkaf:targetConcept`, and `rkaf:mappingRelation`.
Publication or approval state MUST NOT appear inline on the mapping;
`rkaf:Attestation`, release membership, and lifecycle events carry those facts.
Mapping evidence uses the same inverse EvidenceBinding path as every other
durable assertion.

## 6. Local concepts and promotion

A local candidate may accumulate evidence-backed assignments and mappings.
Promotion to a shared vocabulary is a governed publication act, not a field
mutation:

```text
retrieval candidate
  -> LocalConcept
  -> evidence-backed assertions
  -> reviewed ReferenceResourceRelease
  -> publication Attestation
```

Model confidence, query popularity, and click counts may guide review. They do
not establish meaning, publish a release, or authorize use. The local history
remains addressable after a shared concept is published.

## 7. Concept resolution

`rkaf:ConceptResolutionResult` carries `rkaf:resolutionStatus`,
`rkaf:resolutionMethod`, `rkaf:cacheStatus`, `rkaf:usageCeiling`, and the
resolved `rkaf:mappingAssertion` when resolution used a mapping.

The normative runtime procedure is in `spec/rkaf-behavior.md` §6. It evaluates
canonical mapping propositions, exact endpoint release pins, publication
attestations, lifecycle, scope, and registry trust. A consumer MUST respect
`rkaf:usageCeiling`; semantic resolution alone never authorizes drafting,
publication, or official use.

## 8. Validation

Structural constraints compile from:

- `constraints/core/concept.cue`;
- `constraints/core/concept-assignment.cue`;
- `constraints/core/concept-mapping.cue`; and
- `constraints/core/reference-resource-release.cue`.

Hand-authored SHACL in `shapes/rkaf-shapes-conceptregistry.ttl` carries only
graph-wide rules and explicit migration rejection that the structural compiler
cannot express. The compiled and hand-authored shape suites load together.

## 9. Compatibility

None with v0.1.2 or earlier v0.2 drafts. Producers must replace retired
concept-status, assignment-shadow, mapping-shadow, and inline publication-state
fields with the records defined above.
