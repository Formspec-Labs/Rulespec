# PKAF Shapes Batch 1.1

Status: Editor's Draft patch to Shapes Batch 1
Supersedes: Shapes Batch 1 (the eight delta sections below)
Companion to: PKAF Core v0.1, ConceptRegistry v0.1.2, all four conformance fixtures
Bridge contract: `pkaf-bridge/1.0`

## Scope

Eight surgical patches to Batch 1. No new shapes; no scope expansion. Each patch addresses an issue surfaced in Batch 1 review.

## Patch index

| # | Patch | Section |
|---|---|---|
| 1 | Declare SHACL Advanced profile | §1 |
| 2 | Add `OperationalAssertionEvidenceShape` (R2/A3/P4 require real evidence) | §2 |
| 3 | Broaden A3 evidence-role enum for lifecycle predicates (interim; predicate-specific shapes in Batch 3) | §3 |
| 4 | Generalize `Attestation` target (assertion / workProduct / packet / concept / mappingConflict / bridgeValidationResult) | §4 |
| 5 | Allow extension URIs on attestation decision and scope (open enum via declared extensions) | §5 |
| 6 | `LocalAdoption.adoptionScope` is string-or-IRI | §6 |
| 7 | Remove `implements` from `AuthorityChainHopShape`; reserve it for `JustificationChainHopShape` (later batch) | §7 |
| 8 | `BridgeValidationResult` rejected → SuggestedRemediation OR noRemediationReason | §8 |

---

## §1. SHACL Advanced profile declaration

PKAF SHACL is the **PKAF-SHACL-AF profile** (Advanced Features). It uses `sh:if`/`sh:then` conditional shapes and `sh:qualifiedValueShape` constraints, which require a SHACL-Advanced-capable validator (pySHACL, TopBraid, jena-shacl-af).

```turtle
pkaf:PKAFShapesBatch1.1
  a sh:Shapes ;
  rdfs:label "PKAF Shapes Batch 1.1" ;
  pkaf:shaclProfile "pkaf:SHACL-AF" ;
  pkaf:bridgeContractVersion "pkaf-bridge/1.0" ;
  rdfs:comment "Requires SHACL Advanced Features. Validators supporting SHACL-Core only will not enforce conditional shapes correctly." .
```

A SHACL-Core profile is deferred. If/when needed, conditional logic splits into multiple class-targeted shapes with `sh:targetSubjectsOf` patterns. Not in batch 1.1.

## §2. OperationalAssertionEvidenceShape

The Batch 1 `RelationshipAssertionShape` allows `pkaf:hasEvidence` OR `pkaf:noEvidenceReason`. That's correct for `D0`/`S1`, but operational/authority/published assertions cannot fall back to a no-evidence reason.

```turtle
pkaf:OperationalAssertionEvidenceShape
  a sh:NodeShape ;
  sh:targetClass pkaf:RelationshipAssertion ;
  rdfs:label "Operational Assertion Evidence (R2/A3/P4)" ;

  sh:if [
    sh:property [
      sh:path pkaf:hasSafetyLabel ;
      sh:in (
        pkaf:R2ReviewedOperational
        pkaf:A3AuthorityCritical
        pkaf:P4Published
      )
    ]
  ] ;
  sh:then [
    sh:property [
      sh:path pkaf:hasEvidence ;
      sh:minCount 1 ;
      sh:message "R2, A3, and P4 assertions MUST have at least one pkaf:hasEvidence binding. pkaf:noEvidenceReason is NOT sufficient at these safety levels." ;
    ]
  ] .
```

**Conformance test references:**
- v0.2 Step 13 (`req-002`, Z5/R2): has evidence → valid
- Statutory Step 11 (A3): has authority citation evidence → valid
- Synthetic negative: an R2 assertion with only `pkaf:noEvidenceReason` → fails this shape

## §3. AuthorityAssertionShape evidence-role broadening

Batch 1's `AuthorityAssertionShape` requires evidence roles from `{authorityCitation, officialSourceMetadata, reviewedAuthorityChain, formalAdoptionEvent}`. The statutory fixture's rescission assertion (Step 19) uses `rescissionEvidence`; amendment assertions use `structuralEvidence`. The shape over-restricts lifecycle assertions that are also A3.

**Patch:** broaden the qualified-evidence enum to cover lifecycle evidence roles. (Note: Batch 3 will replace this with predicate-specific shapes — `RescindsAssertionShape`, `AmendsAssertionShape`, `SupersedesAssertionShape`, `HasAuthorityAssertionShape`, `DerivesAuthorityFromAssertionShape`, `CreatesExceptionToAssertionShape`. The broadened enum is the interim form.)

```turtle
pkaf:AuthorityAssertionShape
  a sh:NodeShape ;
  sh:targetClass pkaf:RelationshipAssertion ;
  rdfs:label "Authority-Critical Assertion (A3 conditional, interim)" ;

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
        pkaf:legal pkaf:statutory pkaf:regulatory pkaf:delegated
        pkaf:organizational pkaf:contractual pkaf:localOperational pkaf:publication
      ) ;
    ] ;
    sh:property [
      sh:path pkaf:hasApplicability ;
      sh:minCount 1 ;
    ] ;
    sh:property [
      sh:path pkaf:hasEvidence ;
      sh:minCount 1 ;
      sh:qualifiedValueShape [
        sh:property [
          sh:path pkaf:evidenceRole ;
          sh:in (
            pkaf:authorityCitation
            pkaf:officialSourceMetadata
            pkaf:reviewedAuthorityChain
            pkaf:formalAdoptionEvent
            pkaf:rescissionEvidence
            pkaf:amendmentEvidence
            pkaf:supersessionEvidence
            pkaf:structuralEvidence
          )
        ]
      ] ;
      sh:qualifiedMinCount 1 ;
      sh:message "A3 evidence must include at least one binding with an authority OR lifecycle evidence role." ;
    ]
  ] .
```

**Migration note:** When Batch 3 introduces predicate-specific shapes, the interim broadening here is removed. `HasAuthorityAssertionShape` will require only authority roles; `RescindsAssertionShape` only `rescissionEvidence`; etc.

## §4. AttestationShape — generalized target

The Batch 1 shape required exactly one `pkaf:targetAssertion`. Fixtures use attestations targeting work products (`targetWorkProduct` in v0.2 Step 12), and Batch 1.1 must accept attestations targeting packets, concepts, mapping conflicts, registries, and bridge validation results.

```turtle
pkaf:AttestationShape
  a sh:NodeShape ;
  sh:targetClass pkaf:Attestation ;
  rdfs:label "Attestation (generalized target)" ;

  # At least one target of any supported kind
  sh:or (
    [ sh:property [ sh:path pkaf:targetAssertion         ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
    [ sh:property [ sh:path pkaf:targetWorkProduct       ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
    [ sh:property [ sh:path pkaf:targetPacket            ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
    [ sh:property [ sh:path pkaf:targetConcept           ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
    [ sh:property [ sh:path pkaf:targetMappingConflict   ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
    [ sh:property [ sh:path pkaf:targetBridgeValidation  ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
    [ sh:property [ sh:path pkaf:targetRegistry          ; sh:minCount 1 ; sh:nodeKind sh:IRI ] ]
  ) ;
  sh:message "Attestation must reference at least one target via targetAssertion, targetWorkProduct, targetPacket, targetConcept, targetMappingConflict, targetBridgeValidation, or targetRegistry." ;

  sh:property [
    sh:path pkaf:attestor ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
  ] ;

  sh:property [
    sh:path pkaf:attestorType ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    # Closed enum retained from Batch 1; extension URIs allowed per §5 below
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
  ] ;

  # decision and scope: see §5 below for extension handling

  sh:property [
    sh:path pkaf:visibility ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:in ( pkaf:personalVisible pkaf:teamVisible pkaf:orgVisible pkaf:publicVisible ) ;
  ] ;

  sh:property [
    sh:path prov:generatedAtTime ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:datatype xsd:dateTime ;
  ] .
```

## §5. Extension URIs on attestation decision and scope

Closed enums on `pkaf:decision` and `pkaf:scope` are too tight for federated use. New attestation decisions and scopes will emerge from real deployments (e.g., a registry's `declareCanonicalMapping` decision was added mid-iteration). Allow declared extension URIs; constrain to either the closed enum OR a URI in a declared `pkaf:DecisionExtensionRegistry` / `pkaf:ScopeExtensionRegistry`.

```turtle
pkaf:AttestationDecisionShape
  a sh:NodeShape ;
  sh:targetClass pkaf:Attestation ;
  sh:property [
    sh:path pkaf:decision ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:or (
      [ sh:in (
          pkaf:endorse pkaf:endorseWithQualifier pkaf:object pkaf:qualify
          pkaf:correct pkaf:retract pkaf:markStale pkaf:markNotAuthoritative
          pkaf:addEvidence pkaf:requestLegalReview pkaf:requestProgramReview
          pkaf:adoptForSearch pkaf:adoptForDrafting pkaf:adoptForOperations
          pkaf:approveForPublication pkaf:rejectLocally
          pkaf:promoteCandidate pkaf:declareCanonicalMapping
        ) ]
      [ sh:nodeKind sh:IRI ;
        sh:pattern "^https?://" ;
        sh:description "Extension URIs MUST be HTTP(S) IRIs declared in a pkaf:DecisionExtensionRegistry." ]
    ) ;
  ] .

pkaf:AttestationScopeShape
  a sh:NodeShape ;
  sh:targetClass pkaf:Attestation ;
  sh:property [
    sh:path pkaf:scope ;
    sh:minCount 1 ;
    sh:maxCount 1 ;
    sh:or (
      [ sh:in (
          pkaf:personal pkaf:team pkaf:organization pkaf:community
          pkaf:public pkaf:reviewQueue pkaf:jurisdictional
        ) ]
      [ sh:nodeKind sh:IRI ;
        sh:pattern "^https?://" ]
    ) ;
  ] .
```

**Future direction** (deferred from Batch 1.1): Mike's suggestion to split scope into `scopeKind + scopeResource` is the right long-term shape. For v0.1 we allow extension URIs to avoid rework; for v0.2 the split is on the table.

## §6. LocalAdoptionShape.adoptionScope as string-or-IRI

```turtle
# Patch to LocalAdoptionShape adoptionScope property (replaces Batch 1 §5):

sh:property [
  sh:path pkaf:adoptionScope ;
  sh:minCount 1 ;
  sh:or (
    [ sh:datatype xsd:string ]
    [ sh:nodeKind sh:IRI ]
  ) ;
  sh:message "adoptionScope MUST be a string (for opaque scope identifiers) or an IRI (referencing a Workspace, Program, Workflow, Formspec bundle, or Publication package)." ;
]
```

All other `LocalAdoptionShape` properties from Batch 1 are unchanged.

## §7. AuthorityChainHopShape — remove `implements`

`implements` is a substantive realization relationship, not an authority relationship. A chain that includes `implements` is a *justification* chain, not an *authority* chain. Reserved for `JustificationChainHopShape` in a later batch.

```turtle
pkaf:AuthorityChainHopShape
  a sh:NodeShape ;
  sh:targetClass pkaf:AuthorityChainHop ;
  rdfs:label "Authority Chain Hop (authority predicates only)" ;

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
    sh:in ( pkaf:hasAuthority pkaf:derivesAuthorityFrom ) ;
    sh:message "Authority chain hop predicates are limited to hasAuthority and derivesAuthorityFrom. The implements predicate belongs to a justification chain, not an authority chain." ;
  ] ;

  sh:property [
    sh:path pkaf:subject ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
  ] ;
  sh:property [
    sh:path pkaf:object ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
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
      pkaf:hopValid pkaf:hopBroken pkaf:hopRescindedObject
      pkaf:hopSupersededObject pkaf:hopOutOfJurisdiction pkaf:hopOutOfEffectivePeriod
    ) ;
  ] .
```

**Deferred:** `JustificationChainHopShape` (which allows `hasAuthority`, `derivesAuthorityFrom`, AND `implements`) is added in a later batch when generated-artifact justification shapes are drafted.

## §8. BridgeValidationResult rejected → SuggestedRemediation OR noRemediationReason

Batch 1's shape required `pkaf:suggestedRemediation` whenever `pkaf:result: pkaf:rejected`. For security-, fatal-, or restricted-evidence cases, no remediation is appropriate or shareable. Allow either remediation or a `noRemediationReason`.

```turtle
pkaf:BridgeValidationResultShape
  a sh:NodeShape ;
  sh:targetClass pkaf:BridgeValidationResult ;
  rdfs:label "Bridge Validation Result (minimal, patched)" ;

  # ... packetId, consumer, bridgeContractVersion, result, generatedAtTime as in Batch 1 ...

  sh:if [
    sh:property [ sh:path pkaf:result ; sh:hasValue pkaf:rejected ]
  ] ;
  sh:then [
    sh:or (
      [
        sh:property [
          sh:path pkaf:suggestedRemediation ;
          sh:minCount 1 ;
        ]
      ]
      [
        sh:property [
          sh:path pkaf:noRemediationReason ;
          sh:minCount 1 ;
          sh:maxCount 1 ;
          sh:in (
            pkaf:restrictedEvidenceUnavailable
            pkaf:securityBlocked
            pkaf:unsupportedBridgeVersion
            pkaf:malformedPacket
            pkaf:registryAuthorityBlocked
            pkaf:noActionableRemediation
          ) ;
        ]
      ]
    ) ;
    sh:message "Rejected validation results MUST include either a structured pkaf:SuggestedRemediation OR an enumerated pkaf:noRemediationReason." ;
  ] .
```

---

## Model issues that arose during Batch 1.1 drafting

Two only — kept tight per the editorial-discipline call:

1. **`pkaf:DecisionExtensionRegistry` and `pkaf:ScopeExtensionRegistry`** are referenced in §5 but not modeled. These are governance objects, not core shapes. Recommend: spec them in PKAF Core consolidation as lightweight pointer registries (a URI scheme + a list of declared decision/scope URIs each registry sanctions). Out of scope for shape work.

2. **`pkaf:targetRegistry` on Attestation (§4)** is new — added to enable canonical-mapping attestations from a `ConceptMintingAuthority` to a registry-level decision. Currently no fixture uses it directly (the canonical mapping in the failure fixture targets an assertion, not the registry itself). Worth including for completeness, but verify before freezing whether a future fixture needs it; if not, drop in v0.2.

## What Batch 1.1 does NOT add

Per the editorial discipline rule, Batch 1.1 introduces no new shapes, no new vocabulary terms beyond what's needed to make the patches valid, and no new classes. The eight patches are the entire delta.

## Next step

PKAF Core consolidation. After that, run all four fixtures against Batch 1 + 1.1 and resolve any actual violations before drafting Batch 2.
