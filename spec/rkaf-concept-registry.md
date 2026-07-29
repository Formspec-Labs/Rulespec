# Rulespec Concept Registry — v0.2

**Status:** Pre-release, normative.
**Supersedes:** `archive/v0.1/spec/rkaf-concept-registry-v0.1.2.md`
(historical).
**Companion docs:** `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`,
`spec/rkaf-behavior.md`.

## 1. Purpose

This profile defines portable records for governed concepts, concept
assignments, mappings, immutable releases of any governed reference resource
(including entity registries and mapping sets), concept lifecycle, and concept
resolution. Rulespec owns these semantic and trust records. An application owns
ingestion, search indexes, deployment, cache policy, workflow, and user
interface state.

Concept resolution establishes semantic compatibility. It does not establish
policy authority or authorize use. Evidence, attestations, local adoption,
access scope, and consumer eligibility remain independent.

## 2. Native SKOS vocabulary carriage

SKOS owns concept-scheme semantics. Producers MUST use native
`skos:ConceptScheme`, `skos:Concept`, label, note, notation, membership, and
semantic-relation properties with their SKOS meanings. Rulespec narrows the
JSON-LD authoring form so multilingual content survives every generated target.
These rules apply to project-authored `rkaf:ConceptScheme`,
`rkaf:RegisteredConcept`, and `rkaf:LocalConcept` records. An external native
SKOS distribution remains canonical and need not be rewritten merely because a
Rulespec release names it.

### 2.1 Language maps

`skos:prefLabel` MUST be a non-empty JSON-LD language map. Each key MUST be a
well-formed BCP 47 language tag, and each value MUST be exactly one non-empty
string. The one-value rule is per concept and language; a producer cannot
publish two preferred labels for the same language by using an array or
duplicate object members.

The following optional properties use language maps whose values are one
non-empty string or a non-empty array of strings per present language:

- `skos:altLabel` and `skos:hiddenLabel`;
- `skos:definition` and `skos:example`; and
- `skos:note`, `skos:scopeNote`, `skos:changeNote`,
  `skos:editorialNote`, and `skos:historyNote`.

When one of those optional maps is present, the map, each string, and every
array MUST be non-empty. An untagged string and the JSON-LD `@none` language
bucket are non-conforming. The tag `und` is permitted only when the language is
genuinely unknown; it is not a substitute for a producer's omitted default
language. Script belongs in the BCP 47 tag, for example `zh-Hant`, and MUST NOT
be copied into a parallel script field.

Within one concept or scheme, the same language-tagged RDF literal MUST NOT
appear under more than one of `skos:prefLabel`, `skos:altLabel`, and
`skos:hiddenLabel`. Language tags compare case-insensitively for this rule.
Rulespec does not impose global label uniqueness across concepts: two concepts
may share wording while retaining distinct IRIs, schemes, and meanings.

### 2.2 Typed notation

On an `rkaf:RegisteredConcept` or `rkaf:LocalConcept`, `skos:notation`, when
present, MUST be a non-empty JSON array of closed JSON-LD typed-literal
objects. Each object contains exactly:

- `@value`, a string preserving the notation's lexical form; and
- `@type`, an absolute datatype IRI identifying the notation system.

A notation MUST NOT be an untyped string or a language-tagged literal. The
datatype IRI is open because notation systems belong to their governing
vocabularies; Rulespec checks that it is absolute but does not mint a universal
notation-system enum.

### 2.3 Scheme membership, hierarchy, and governance

`rkaf:ConceptScheme` adds two Rulespec requirements:

- `rkaf:schemeFacet` identifies the question this scheme answers; and
- exactly one of `rkaf:managedByRegistry` or `rkaf:definedInScope` identifies
  its governing scope.

`rkaf:RegisteredConcept` carries a non-empty `skos:prefLabel` language map,
exactly one `skos:inScheme`, an absolute `rkaf:managedByRegistry` IRI,
`rkaf:conceptScope`, and exactly one `rkaf:registeredAt` timestamp.
`rkaf:LocalConcept` carries a non-empty `skos:prefLabel` language map, exactly
one `skos:inScheme`, `rkaf:definedInScope`, and `rkaf:conceptScope`.

`skos:broader`, `skos:narrower`, and `skos:related` are zero-or-more IRI
relations. A concept may have multiple `skos:broader` parents, and every
conforming projection MUST preserve all of them. Every such relation MUST
connect concepts in the same `skos:inScheme`; a `skos:hasTopConcept` target
MUST also be a member of that scheme. Cross-scheme relations use
`rkaf:ConceptMapping` and one of the five concrete SKOS mapping predicates.
They MUST NOT be encoded as hierarchy or `skos:related`.

`rkaf:managedByRegistry` names an externally described registry. Rulespec does
not require an in-graph `rkaf:ConceptRegistry` object, namespace declaration,
resolution endpoint, or minting-authority object. Governance is expressed
through external IRIs plus Rulespec `rkaf:Authority`, `rkaf:Attestation`,
release, and lifecycle records. The v0.1 `rkaf:ConceptRegistry` and
`rkaf:ConceptMintingAuthority` object models are not active v0.2 classes.

`rkaf:conceptStatus` is not part of this release. Immutable release membership
records what a release contains. `rkaf:Attestation` records review or
publication decisions. `rkaf:LifecycleEvent` records concept changes.
Producers MUST NOT collapse those facts into mutable fields such as
`rkaf:conceptStatus`, `rkaf:replacedBy`, or `rkaf:splitInto` on a concept.

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

## 6. Concept lifecycle

A concept change is one `rkaf:LifecycleEvent` whose
`rkaf:lifecycleEventKind` is `rkaf:conceptLifecycle`. It carries exactly one
`rkaf:conceptLifecycleOperation` from this closed set:

- `rkaf:deprecation`;
- `rkaf:withdrawal`;
- `rkaf:replacement`;
- `rkaf:split`;
- `rkaf:merge`;
- `rkaf:promotion`; or
- `rkaf:demotion`.

The event carries `rkaf:predecessorConcepts` and
`rkaf:successorConcepts` as IRI collections. Their cardinalities are:

| Operation | Predecessors | Successors |
| --- | ---: | ---: |
| `rkaf:deprecation` | 1 | 0 |
| `rkaf:withdrawal` | 1 | 0 |
| `rkaf:replacement` | 1 | 1 |
| `rkaf:split` | 1 | 2..* |
| `rkaf:merge` | 2..* | 1 |
| `rkaf:promotion` | 1 | 1 |
| `rkaf:demotion` | 1 | 1 |

Every event MUST carry exactly one
`rkaf:predecessorConceptRelease`. That release MUST use
`rkaf:completeMembership`, and every predecessor MUST appear in its
`prov:hadMember` set. An event with successors MUST carry exactly one
`rkaf:successorConceptRelease`, also using complete membership and containing
every successor. An event without successors MUST NOT carry a successor
release pin. A partial or non-enumerated release cannot validate lifecycle
participation.

When an event has both release pins, they MUST name distinct release IRIs.
Each release's `rkaf:referenceReleaseDigest` independently proves its semantic
manifest, but a different digest does not turn one release IRI into two release
identities. Reusing one complete-membership release for both pins is
non-conforming, even when that release contains every predecessor and
successor.

For concept lifecycle events, `rkaf:appliesTo` MUST contain exactly the
predecessor concepts. Successors are outputs of the change, not cascade seeds,
and MUST NOT be added to `rkaf:appliesTo`. Participant collections are sets:
duplicate IRIs do not satisfy a cardinality, and one concept IRI MUST NOT
appear in both the predecessor and successor sets.

Deprecation and withdrawal keep the predecessor IRI addressable for history
but provide no automatic successor. Replacement names one successor. Split
requires consumer disambiguation rather than choosing one successor by rank.
Merge names the one successor to the predecessor set. Promotion records a
`rkaf:LocalConcept` predecessor and an `rkaf:RegisteredConcept` successor;
demotion records the reverse governance transition. Neither operation rewrites
the predecessor or erases its history.

The standalone lifecycle-event-kind values `rkaf:promotion` and
`rkaf:demotion` are retired. A producer MUST use
`rkaf:lifecycleEventKind = rkaf:conceptLifecycle` and place promotion or
demotion in `rkaf:conceptLifecycleOperation`. Review or rejection of an
assertion is not concept lifecycle and remains an `rkaf:Attestation` or
`rkaf:LocalAdoption` fact. Migration fixtures MUST reject the retired
standalone event forms.

## 7. Local concepts and promotion

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
remains addressable after a shared concept is published. The transition from
the local concept to the shared concept is the `rkaf:promotion` operation
defined in §6; it is not an in-place class or status mutation.

## 8. Concept resolution

Every `rkaf:ConceptResolutionResult` carries exactly one:

- `rkaf:inputConcept`, an absolute IRI;
- `rkaf:resolutionStatus`;
- `rkaf:resolutionMethod`;
- `rkaf:cacheStatus`;
- `rkaf:usageCeiling`; and
- `rkaf:resolvedAt`.

It MAY carry one `rkaf:resolverId`.

`rkaf:resolutionStatus` uses the existing closed values
`rkaf:resolved`, `rkaf:unresolved`, `rkaf:ambiguous`,
`rkaf:conflicting`, `rkaf:registryUnavailable`, and
`rkaf:staleCacheFallback`.

`rkaf:resolutionMethod` uses the existing closed values
`rkaf:directRegistry`, `rkaf:exactMatchTrusted`,
`rkaf:closeMatchLocallyAdopted`, `rkaf:closeMatchAwaitingAdoption`,
`rkaf:broadOrNarrowMatchDiscoveryOnly`, `rkaf:cacheServed`, and
`rkaf:staleCacheServed`. `rkaf:cacheStatus` is exactly one of
`rkaf:fresh`, `rkaf:stale`, or `rkaf:notCached`.

A result with status `rkaf:resolved` or `rkaf:staleCacheFallback` MUST carry
exactly one `rkaf:resolvedConcept`; a result that did not select one concept
MUST omit it. A result whose selected path depends on an
`rkaf:ConceptMapping` MUST carry exactly one `rkaf:mappingAssertion` naming
that mapping. This includes selected paths using
`rkaf:exactMatchTrusted`, `rkaf:closeMatchLocallyAdopted`,
`rkaf:closeMatchAwaitingAdoption`, or
`rkaf:broadOrNarrowMatchDiscoveryOnly`. A direct registry result MUST omit
`rkaf:mappingAssertion`. A cached mapping result retains its underlying mapping
method and mapping assertion while `rkaf:cacheStatus` records freshness;
`rkaf:cacheServed` and `rkaf:staleCacheServed` are reserved for cached direct
resolution and therefore carry no mapping assertion.

`rkaf:usageCeiling` is required even when resolution fails. It records the
highest use the resolution evidence can support, not an authorization or an
effective consumer decision. A consumer MAY narrow it and MUST combine it with
attestation, adoption, access, lifecycle, and its own capability ceiling. It
MUST NOT broaden it because a concept resolved.

The normative runtime procedure is in `spec/rkaf-behavior.md` §6. It evaluates
canonical mapping propositions, exact endpoint release pins, publication
attestations, lifecycle, scope, and registry trust. A consumer MUST respect
`rkaf:usageCeiling`; semantic resolution alone never authorizes drafting,
publication, or official use.

## 9. Validation

Structural constraints compile from:

- `constraints/core/concept.cue`;
- `constraints/core/concept-assignment.cue`;
- `constraints/core/concept-mapping.cue`;
- `constraints/core/concept-resolution-result.cue`;
- `constraints/core/lifecycle-event.cue`; and
- `constraints/core/reference-resource-release.cue`.

Hand-authored SHACL in `shapes/rkaf-shapes-conceptregistry.ttl` carries only
graph-wide rules and explicit migration rejection that the structural compiler
cannot express. The compiled and hand-authored shape suites load together.

## 10. Compatibility

None with v0.1.2 or earlier v0.2 drafts. Producers must replace retired
concept-status, concept-registry object, concept-minting-authority object,
assignment-shadow, mapping-shadow, inline publication-state, singular
`skos:broader`, and standalone promotion/demotion event forms with the records
defined above.
