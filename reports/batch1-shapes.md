# PKAF Shapes Batch 1

Status: Editor's Draft, first SHACL package
Companion to: PKAF Core (consolidation pending), ConceptRegistry v0.1.2, all four conformance fixtures
Bridge contract: `pkaf-bridge/1.0`

## Scope of batch 1

This batch covers the core PKAF assertion model and the authority/adoption machinery that every consumer depends on:

1. `RelationshipAssertionShape` — base shape for all assertions
2. `AuthorityAssertionShape` — additional constraints when `hasSafetyLabel: A3AuthorityCritical`
3. `EvidenceBindingShape` — evidence references inside assertions
4. `AttestationShape` — attestations on assertions
5. `LocalAdoptionShape` — organizational adoption events
6. `AuthorityChainHopShape` — chain traversal record (referenced in BridgeValidationResult)
7. `BridgeValidationResultShape` (minimal) — enough to validate the cross-cutting result type used by all consumers

**Out of scope for batch 1** (next batches):
- ConceptRegistry shapes (`RegisteredConceptShape`, `LocalConceptShape`, `MappingAssertionShape`, `ConceptResolutionResultShape`)
- Lifecycle packet shapes (`AmendmentPacketShape`, `RescissionPacketShape`, `ConceptLifecyclePacketShape`)
- `GeneratedWorkProductJustificationShape` (Formspec field / WOS step justifications)
- `BridgeConsumerRegistrationShape`
- `PolicyResourceVersionShape` and `DelegationInstrumentShape`

Batch 2 should be ConceptRegistry shapes; batch 3 lifecycle packets; batch 4 generated artifacts and registration.

## Prefix declarations

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix oa: <http://www.w3.org/ns/oa#> .
@prefix pkaf: <https://w3id.org/pkaf/ns/v1#> .
```

---

## 1. RelationshipAssertionShape

Every `pkaf:RelationshipAssertion` has required subject/predicate/object, declared trust zone, safety label, and usage eligibility, and at least one evidence binding (or an explicit no-evidence reason). `assertionState` is intentionally NOT validated here — it is computed per scope from attestations and adoptions (PKAF Core principle from Pass 3).

```turtle
pkaf:RelationshipAssertionShape
  a sh:NodeShape ;
  sh:targetClass pkaf:RelationshipAssertion ;
  rdfs:label "Relationship Assertion (base)" ;

  sh:property [
    sh:path pkaf:assertsSubject ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
    sh:message "Every assertion must have exactly one IRI-typed subject." ;
  ] ;

  sh:property [
    sh:path pkaf:assertsPredicate ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
    sh:message "Every assertion must have exactly one IRI-typed predicate." ;
  ] ;

  sh:property [
    sh:path pkaf:assertsObject ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:message "Every assertion must have exactly one object (IRI or literal)." ;
  ] ;

  sh:property [
    sh:path pkaf:hasTrustZone ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:Z0RawArtifact
      pkaf:Z1ParsedFragment
      pkaf:Z2ExtractedCandidateClaim
      pkaf:Z3ScoredCandidateRelationship
      pkaf:Z4AttestedAssertion
      pkaf:Z5LocallyAdopted
      pkaf:Z6CanonicalOperational
      pkaf:Z7GeneratedWorkProduct
      pkaf:Z8PublishedOutput
    ) ;
    sh:message "Trust zone must be one of Z0–Z8." ;
  ] ;

  sh:property [
    sh:path pkaf:hasSafetyLabel ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:D0Deterministic
      pkaf:S1SearchOnly
      pkaf:R2ReviewedOperational
      pkaf:A3AuthorityCritical
      pkaf:P4Published
    ) ;
    sh:message "Safety label must be one of D0, S1, R2, A3, P4." ;
  ] ;

  sh:property [
    sh:path pkaf:usageEligibility ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:notEligible
      pkaf:searchOnly
      pkaf:reviewQueueOnly
      pkaf:draftGenerationAllowed
      pkaf:localOperationalUse
      pkaf:publicationAllowed
      pkaf:officialUse
    ) ;
    sh:message "Usage eligibility must be one of the lattice values." ;
  ] ;

  sh:property [
    sh:path pkaf:assertionOrigin ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:humanAsserted
      pkaf:aiSuggested
      pkaf:aiPromoted
      pkaf:humanQualified
      pkaf:humanRevalidation
      pkaf:reviewClassified
      pkaf:importedFromSource
      pkaf:systemDerived
    ) ;
    sh:message "Assertion origin must be from the closed enum or a declared extension URI." ;
  ] ;

  # Evidence: at least one binding required UNLESS explicit no-evidence reason given.
  sh:or (
    [
      sh:property [
        sh:path pkaf:hasEvidence ;
        sh:minCount 1 ;
      ]
    ]
    [
      sh:property [
        sh:path pkaf:noEvidenceReason ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
      ]
    ]
  ) ;
  sh:message "Assertion must have at least one pkaf:hasEvidence binding, or an explicit pkaf:noEvidenceReason." .
```

**Conformance test references** (instances expected to validate):

- v0.2 fixture Step 5 (`cand-001`): valid candidate assertion at Z3/S1
- v0.2 fixture Step 13 (`req-002`): valid qualified assertion at Z5/R2
- Mapping fixture Step 4 (`caa-42-mapping-001`): valid mapping assertion at Z4/R2
- Statutory fixture Step 11 (`caa-42-identity-req-001`): valid A3 assertion (also validates against `AuthorityAssertionShape` below)

**Expected failures** (these are invalid and should be caught):

- Assertion missing `assertsPredicate` → fails minCount on predicate path
- Assertion with `hasSafetyLabel: "approved"` (non-enum value) → fails sh:in constraint
- Assertion with no evidence AND no no-evidence reason → fails sh:or

---

## 2. AuthorityAssertionShape

When an assertion's `hasSafetyLabel` is `A3AuthorityCritical`, additional constraints apply: it MUST declare `authorityKind`, `hasApplicability`, and evidence MUST include at least one authority citation.

```turtle
pkaf:AuthorityAssertionShape
  a sh:NodeShape ;
  sh:targetClass pkaf:RelationshipAssertion ;
  rdfs:label "Authority-Critical Assertion (A3 conditional)" ;

  # Activate only when safety label is A3
  sh:if [
    sh:property [
      sh:path pkaf:hasSafetyLabel ;
      sh:hasValue pkaf:A3AuthorityCritical ;
    ]
  ] ;

  sh:then [
    sh:property [
      sh:path pkaf:authorityKind ;
      sh:minCount 1 ;
      sh:maxCount 1 ;
      sh:in (
        pkaf:legal
        pkaf:statutory
        pkaf:regulatory
        pkaf:delegated
        pkaf:organizational
        pkaf:contractual
        pkaf:localOperational
        pkaf:publication
      ) ;
      sh:message "A3 authority-critical assertions must declare authorityKind." ;
    ] ;
    sh:property [
      sh:path pkaf:hasApplicability ;
      sh:minCount 1 ;
      sh:message "A3 authority-critical assertions must declare applicability context (jurisdiction, effective period, scope)." ;
    ] ;
    sh:property [
      sh:path pkaf:hasEvidence ;
      sh:minCount 1 ;
      sh:qualifiedValueShape [
        sh:property [
          sh:path pkaf:evidenceRole ;
          sh:in ( pkaf:authorityCitation pkaf:officialSourceMetadata pkaf:reviewedAuthorityChain pkaf:formalAdoptionEvent ) ;
        ]
      ] ;
      sh:qualifiedMinCount 1 ;
      sh:message "A3 evidence must include at least one binding with role authorityCitation, officialSourceMetadata, reviewedAuthorityChain, or formalAdoptionEvent." ;
    ]
  ] .
```

**Conformance test references:**

- Statutory fixture Step 6, 8, 10 (chain hops): all valid A3 assertions with `authorityKind: delegated|regulatory|regulatory`
- Statutory fixture Step 11 (`caa-42-identity-req-001`): valid A3 with `authorityKind: regulatory` and applicability declared
- Statutory fixture Step 19 (rescission assertion): valid A3 with statute-level evidence

**Expected failures:**

- An A3 assertion missing `authorityKind` → fails minCount on authorityKind
- An A3 assertion whose only evidence has `evidenceRole: textualEvidence` (not an authority role) → fails qualifiedMinCount

---

## 3. EvidenceBindingShape

Evidence bindings inside assertions must declare a role and either a source fragment, a supporting quote, a supporting event, a basedOnClassification, or a rationaleText. The §15 evidence-typing decision from the v0.2 fixture is reflected.

```turtle
pkaf:EvidenceBindingShape
  a sh:NodeShape ;
  sh:targetClass pkaf:EvidenceBinding ;
  rdfs:label "Evidence Binding" ;

  sh:property [
    sh:path pkaf:evidenceRole ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:textualEvidence
      pkaf:structuralEvidence
      pkaf:retrievalSignal
      pkaf:authorityCitation
      pkaf:officialSourceMetadata
      pkaf:reviewedAuthorityChain
      pkaf:formalAdoptionEvent
      pkaf:mappingRationale
      pkaf:registrationEvent
      pkaf:rescissionEvidence
      pkaf:corroboratingEvidence
      pkaf:counterEvidence
    ) ;
    sh:message "Evidence role must be from the enumerated vocabulary." ;
  ] ;

  # Must have at least one source — fragment, quote, event, classification, or rationale
  sh:or (
    [ sh:property [ sh:path pkaf:sourceFragment ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
    [ sh:property [ sh:path pkaf:supportingQuote ; sh:minCount 1 ; sh:datatype xsd:string ] ]
    [ sh:property [ sh:path pkaf:supportingEvent ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
    [ sh:property [ sh:path pkaf:basedOnClassification ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
    [ sh:property [ sh:path pkaf:rationaleText ; sh:minCount 1 ; sh:datatype xsd:string ] ]
  ) ;
  sh:message "Evidence binding must reference at least one of: sourceFragment, supportingQuote, supportingEvent, basedOnClassification, or rationaleText." .
```

**Conformance test references:**

- v0.2 fixture all evidence bindings: validate against various role values
- Mapping fixture Step 4 evidence: `mappingRationale` role with `rationaleText`
- Statutory fixture Step 6, 8 evidence: `authorityCitation` role with `supportingQuote`
- v0.2 fixture Step 19 evidence: `structuralEvidence` role with `basedOnClassification`

---

## 4. AttestationShape

```turtle
pkaf:AttestationShape
  a sh:NodeShape ;
  sh:targetClass pkaf:Attestation ;
  rdfs:label "Attestation" ;

  sh:property [
    sh:path pkaf:targetAssertion ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
    sh:message "Attestation must reference exactly one target assertion." ;
  ] ;

  sh:property [
    sh:path pkaf:attestor ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
    sh:message "Attestation must identify exactly one attestor by IRI." ;
  ] ;

  sh:property [
    sh:path pkaf:attestorType ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:humanUser
      pkaf:AIModel
      pkaf:AIAgent
      pkaf:automatedParser
      pkaf:team
      pkaf:organization
      pkaf:community
      pkaf:formalReviewer
      pkaf:ConceptMintingAuthority
    ) ;
    sh:message "Attestor type must be from the closed enum." ;
  ] ;

  sh:property [
    sh:path pkaf:decision ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:endorse
      pkaf:endorseWithQualifier
      pkaf:object
      pkaf:qualify
      pkaf:correct
      pkaf:retract
      pkaf:markStale
      pkaf:markNotAuthoritative
      pkaf:addEvidence
      pkaf:requestLegalReview
      pkaf:requestProgramReview
      pkaf:adoptForSearch
      pkaf:adoptForDrafting
      pkaf:adoptForOperations
      pkaf:approveForPublication
      pkaf:rejectLocally
      pkaf:promoteCandidate
      pkaf:declareCanonicalMapping
    ) ;
    sh:message "Attestation decision must be from the closed enum." ;
  ] ;

  sh:property [
    sh:path pkaf:scope ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:personal
      pkaf:team
      pkaf:organization
      pkaf:community
      pkaf:public
      pkaf:reviewQueue
      pkaf:jurisdictional
    ) ;
  ] ;

  sh:property [
    sh:path pkaf:visibility ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:personalVisible
      pkaf:teamVisible
      pkaf:orgVisible
      pkaf:publicVisible
    ) ;
  ] ;

  sh:property [
    sh:path prov:generatedAtTime ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:datatype xsd:dateTime ;
    sh:message "Attestation must have a generation timestamp." ;
  ] .
```

**Conformance test references:**

- v0.2 fixture Step 7 (promotion attestation): AI agent, promoteCandidate, reviewQueue
- v0.2 fixture Step 8 (analyst endorsement): human user, endorseWithQualifier, organization
- v0.2 fixture Step 12 (legal objection): human user, object, organization
- Failure fixture Step 8 (canonical mapping): ConceptMintingAuthority, declareCanonicalMapping, public

---

## 5. LocalAdoptionShape

A LocalAdoption is the organizational authorization to operationalize an assertion within a scope. The shape ensures every adoption identifies an organization, target assertion, status, eligibility, authority kind, and authorizing actor.

```turtle
pkaf:LocalAdoptionShape
  a sh:NodeShape ;
  sh:targetClass pkaf:LocalAdoption ;
  rdfs:label "Local Adoption" ;

  sh:property [
    sh:path pkaf:organization ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
  ] ;

  sh:property [
    sh:path pkaf:targetAssertion ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
  ] ;

  sh:property [
    sh:path pkaf:adoptionStatus ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:notApplicable
      pkaf:watchOnly
      pkaf:searchOnly
      pkaf:needsReview
      pkaf:adoptedForDrafting
      pkaf:adoptedForLocalOperations
      pkaf:approvedForPublication
      pkaf:rejectedLocally
    ) ;
  ] ;

  sh:property [
    sh:path pkaf:usageEligibility ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:notEligible
      pkaf:searchOnly
      pkaf:reviewQueueOnly
      pkaf:draftGenerationAllowed
      pkaf:localOperationalUse
      pkaf:publicationAllowed
      pkaf:officialUse
    ) ;
  ] ;

  sh:property [
    sh:path pkaf:adoptionAuthorityKind ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:organizational
      pkaf:localOperational
      pkaf:contractual
      pkaf:publication
    ) ;
    sh:message "LocalAdoption authority kind must be organizational, localOperational, contractual, or publication. NOT statutory/regulatory/delegated — those flow only through hasAuthority/derivesAuthorityFrom chains." ;
  ] ;

  sh:property [
    sh:path pkaf:adoptionScope ;
    sh:minCount 1 ;
    sh:datatype xsd:string ;
    sh:message "LocalAdoption must declare an explicit adoptionScope string." ;
  ] ;

  sh:property [
    sh:path pkaf:authorizedBy ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
    sh:message "LocalAdoption must identify the authorizing actor by IRI." ;
  ] ;

  sh:property [
    sh:path prov:generatedAtTime ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:datatype xsd:dateTime ;
  ] .
```

**Normative note (PKAF Core):** A `LocalAdoption` MAY authorize local operational use of an assertion within a declared scope. It MUST NOT substitute for a broken, expired, rescinded, or missing `hasAuthority` / `derivesAuthorityFrom` chain when the adopted assertion requires external legal, regulatory, or delegated authority. This invariant is structural (enforced by the shape's restriction on `adoptionAuthorityKind` values) and behavioral (enforced by the bridge cascade closure including `LocalAdoption.targetAssertion` inverse edges, surfaced as `LocalAdoptionOrphanedWarning` in `BridgeValidationResult` per the statutory fixture's truth table).

**Conformance test references:**

- v0.2 fixture Step 9 (CAA-42 adoption of req-001): valid `adoptedForDrafting` with `localOperational`
- v0.2 fixture Step 14 (adoption of req-002): valid `adoptedForLocalOperations`
- Mapping fixture Step 8 (adoption of mapping-001): valid mapping-targeted adoption
- Statutory fixture Step 12 (adoption of identity req): valid `localOperational` adoption with explicit rationale distinguishing organizational permission from legal authority

**Expected failures:**

- LocalAdoption with `adoptionAuthorityKind: statutory` → fails sh:in (statutory must come through hasAuthority chain)
- LocalAdoption missing `adoptionScope` → fails minCount

---

## 6. AuthorityChainHopShape

An authority chain hop records one edge of a traversal: the assertion that asserts it, the predicate, subject, object, and authority kind. Used inside `BridgeValidationResult.authorityChainTraversal`.

```turtle
pkaf:AuthorityChainHopShape
  a sh:NodeShape ;
  sh:targetClass pkaf:AuthorityChainHop ;
  rdfs:label "Authority Chain Hop" ;

  sh:property [
    sh:path pkaf:assertion ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
  ] ;

  sh:property [
    sh:path pkaf:predicate ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in ( pkaf:hasAuthority pkaf:derivesAuthorityFrom pkaf:implements ) ;
    sh:message "Hop predicate must be one of hasAuthority, derivesAuthorityFrom, or implements." ;
  ] ;

  sh:property [
    sh:path pkaf:subject ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
  ] ;

  sh:property [
    sh:path pkaf:object ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
  ] ;

  sh:property [
    sh:path pkaf:authorityKind ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:legal pkaf:statutory pkaf:regulatory pkaf:delegated
      pkaf:organizational pkaf:contractual pkaf:localOperational pkaf:publication
    ) ;
  ] ;

  sh:property [
    sh:path pkaf:status ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:hopValid
      pkaf:hopBroken
      pkaf:hopRescindedObject
      pkaf:hopSupersededObject
      pkaf:hopOutOfJurisdiction
      pkaf:hopOutOfEffectivePeriod
    ) ;
  ] .
```

**Conformance test references:**

- Statutory fixture Step 15 (BridgeValidationResult): three hops, all `hopValid` initially
- Statutory fixture Step 21 (post-rescission): hops with `hopRescindedObject` status

---

## 7. BridgeValidationResultShape (minimal)

This is a partial shape covering the cross-cutting result type. Full shape comes in batch 4 alongside `BridgeConsumerRegistrationShape`.

```turtle
pkaf:BridgeValidationResultShape
  a sh:NodeShape ;
  sh:targetClass pkaf:BridgeValidationResult ;
  rdfs:label "Bridge Validation Result (minimal)" ;

  sh:property [
    sh:path pkaf:packetId ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
  ] ;

  sh:property [
    sh:path pkaf:consumer ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
  ] ;

  sh:property [
    sh:path pkaf:bridgeContractVersion ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:datatype xsd:string ;
    sh:pattern "^pkaf-bridge/[0-9]+\\.[0-9]+$" ;
    sh:message "Bridge contract version must follow pattern pkaf-bridge/MAJOR.MINOR" ;
  ] ;

  sh:property [
    sh:path pkaf:result ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in (
      pkaf:accepted
      pkaf:acceptedWithWarnings
      pkaf:rejected
    ) ;
  ] ;

  sh:property [
    sh:path prov:generatedAtTime ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:datatype xsd:dateTime ;
  ] ;

  # Conditional: if result is rejected, suggestedRemediation MUST be present
  sh:if [
    sh:property [ sh:path pkaf:result ; sh:hasValue pkaf:rejected ]
  ] ;
  sh:then [
    sh:property [
      sh:path pkaf:suggestedRemediation ;
      sh:minCount 1 ;
      sh:message "Rejected results must include a structured pkaf:SuggestedRemediation." ;
    ]
  ] .
```

**Conformance test references:**

- v0.2 fixture Steps 11, 21: valid `accepted` and `acceptedWithWarnings` results
- Failure fixture Steps 4, 5, 9: valid `rejected` results with `suggestedRemediation`

---

## Validation methodology

Each shape is intended to be runnable via pySHACL or rapper against the fixture JSON-LD (converted to TTL). The conformance test references above identify positive cases (instances expected to validate) and selected negative cases (instances expected to fail with specific violation codes).

Recommended initial test harness:

```
pyshacl -s pkaf-shapes-batch-1.ttl -d fixtures/v0.2-fixture.ttl
```

Each shape should produce zero violations on the v0.1 conformance fixture set.

## Model issues surfaced during shape drafting

1. **`assertionState` is properly absent from the shape, but consumers will look for it.** The shape correctly omits `assertionState` validation (state is computed per scope from attestations/adoptions). But every implementation will reach for it on first encounter. Recommend the PKAF Core consolidation include a normative paragraph stating that `assertionState` is a computed property, not a stored one, and pointing implementers to the reducer.

2. **`pkaf:hasApplicability` cardinality on A3 assertions is `1..1` but applicability shapes vary (`ApplicabilityContext` for assertions, `MappingApplicabilityContext` for mappings).** The shape requires `minCount 1` but doesn't constrain the applicability node's type. Batch 2 must include `ApplicabilityContextShape` and `MappingApplicabilityContextShape` with discrimination.

3. **`pkaf:evidenceRole` enumeration is open in practice.** The shape currently uses a closed `sh:in` list. As new fixtures introduce new evidence roles (e.g., `pkaf:registrationEvent` from the failure fixture), the enum grows. Recommend: leave the enum closed in the shape, version it explicitly, and require extensions to declare new role URIs in a registry document.

4. **`pkaf:supersedesAssertion` cardinality is `0..*` per the Pass 3 many-to-many decision, but not validated in batch 1.** The supersession relationship needs its own shape (batch 2 or 3) that enforces no-self-supersession, no-cycles, and lifecycle invariants. Out of scope for batch 1.

5. **Conditional shapes via `sh:if`/`sh:then` are SHACL-Advanced.** Two shapes here use them (AuthorityAssertionShape, BridgeValidationResultShape). Some SHACL validators support only SHACL-Core. Worth flagging conformance level: PKAF SHACL is SHACL-Advanced. If we need SHACL-Core compatibility, the conditional logic must be split into separate shapes targeted by class.

6. **`prov:generatedAtTime` cardinality is `1..1` on attestations and adoptions; the spec earlier allowed it implicitly.** Making it required is a tightening. If existing instances elsewhere lack it, they'll fail validation. Worth confirming as a normative tightening.

7. **`pkaf:authorityKind` on LocalAdoption is restricted to `organizational`, `localOperational`, `contractual`, `publication` — excluding `statutory`, `regulatory`, `delegated`, `legal`.** This is the structural enforcement of the truth-table principle. Worth noting in the spec text accompanying the shape: this is intentional and any LocalAdoption claiming statutory/regulatory authority is malformed.

8. **No PROV-O linking validated.** Assertions, attestations, and adoptions reference `prov:wasGeneratedBy`, `prov:wasAttributedTo`, `prov:wasDerivedFrom`. Batch 1 doesn't validate these. PROV-O alignment shapes should be a small batch of their own or included in batch 4.

## What batch 1 enables

After this batch validates clean against all four fixtures:

- A consumer (Formspec, WOS, or other) can syntactically validate any PKAF assertion, attestation, or adoption it receives.
- A bridge implementation can refuse malformed packets at ingestion rather than failing during cascade processing.
- A registry implementation can validate user-submitted assertions before publishing.
- The structural invariant "LocalAdoption is not legal authority" is enforced at the data level, not only behaviorally.

What's NOT enabled by batch 1 alone:

- ConceptRegistry validation (batch 2)
- Lifecycle packet validation (batch 3)
- Generated artifact justification validation (batch 4)
- Full `BridgeValidationResult` with concept resolution results, point-in-time exceptions, conflict warnings (batch 4)

## Recommended next steps

1. **Test harness.** Convert the four fixture JSON-LD files to TTL and run pySHACL with these shapes. Catalog any violations and decide whether they indicate fixture errors or shape over-restriction.

2. **PKAF Core consolidation pass.** Several normative statements have accumulated across fixtures and reviews but lack a single home document:
   - LocalAdoption normative statement (above)
   - `authorityKind` is hop-local, not global
   - `DelegationInstrument` as first-class typed `PolicyResourceVersion`
   - `AuthorityChainHop` as first-class type
   - `chainTerminusKind` and `authorityChainStatus` on `BridgeValidationResult`
   - Cascade closure must include `LocalAdoption.targetAssertion` inverse edges
   - Outstanding statutory fixture edits (rescissionEffectiveDate removal, supportedPointInTimeAnchors location, explicit sourceAuthority on each authority resource, state adoption chain decision)
   - ConceptRegistry §5.7 resolvedFromConceptResolution addition

   A short PKAF Core editorial pass would consolidate these before batch 2.

3. **Batch 2: ConceptRegistry shapes.** With the consolidation done, the next batch is mechanical.

4. **Continuous validation.** Each new shape batch should re-run all four fixtures to detect regressions.
