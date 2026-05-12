# PKAF Statutory Authority Fixture v0.1

Status: Editor's Draft conformance fixture for the A3 authority layer
Companion to: PKAF Core, PKAF Conformance Fixture v0.2, PKAF Mapping Fixture v0.1, PKAF ConceptRegistry v0.1.2
Bridge contract: `pkaf-bridge/1.0`

## Purpose

The v0.2 local-operational fixture and the v0.1 mapping fixture intentionally avoid the A3 authority-critical layer. This fixture exercises it: `hasAuthority` and `derivesAuthorityFrom` chains, `authorityKind` distinctions, `DelegationInstrument` modeling, and `RescissionPacket` cascade through the full chain. It also demonstrates the critical distinction Mike flagged: **local adoption is operational authorization, not legal authority** — when the legal chain breaks, local adoption alone cannot keep the artifact operational.

## Scenario

Federal benefit program with the canonical authority stack:

1. **Statute.** Congress enacts Section 1234 of a fictional Community Services Block Grant Act, codified at `42 USC § 9908`. The statute requires identity verification for benefit enrollment AND delegates rulemaking authority to the Department of Health and Human Services.

2. **Delegation.** HHS Secretary issues a written delegation memo authorizing the Office of Community Services (OCS) to promulgate regulations implementing the statute.

3. **Regulation.** OCS promulgates `45 CFR § 96.30`, specifying acceptable forms of identity evidence.

4. **State implementation.** A state's Community Services agency adopts the federal regulation as state policy via state regulation.

5. **CAA implementation.** CAA-42 implements intake under state policy, with:
   - A WOS workflow step `verify_identity`
   - A Formspec field `identity_document`

Then Congress rescinds Section 1234 (replacing the program with a different mechanism). The fixture traces what breaks, what survives via `PointInTimeException`, and how WOS and Formspec bridges react.

## Test cases exercised

1. `hasAuthority` with `authorityKind: regulatory` from a requirement to the federal regulation
2. `derivesAuthorityFrom` chain: regulation → delegation → statute (three hops)
3. `DelegationInstrument` modeling as a typed `PolicyResourceVersion`
4. State adoption as a separate `derivesAuthorityFrom` branch
5. `LocalAdoption` granting `localOperational` operational authorization, distinct from the legal chain
6. WOS workflow step justification with full authority chain
7. Formspec field justification sharing the chain
8. `rescinds` assertion at statute level
9. `RescissionPacket` cascading through the full authority graph
10. Bridge response: artifacts transition to `staleForCurrentUse` for new cases
11. `PointInTimeException` preserving in-flight applications via `applicationSubmissionTime` anchor
12. `LocalAdoption` does NOT preserve operational use after authority chain breaks (the critical truth-table)

---

## Phase 1: Federal statute

### Step 1 — Artifact (codified statute text)

```json
{
  "@context": "https://w3id.org/pkaf/context/v1.jsonld",
  "@id": "https://example.gov/artifact/csbg-act-section-1234-codified-2024",
  "@type": "pkaf:Artifact",
  "pkaf:sourceType": "official-codified-statute",
  "pkaf:contentHash": "sha256:f2c8a91b...3d7e",
  "pkaf:mimeType": "application/xml",
  "pkaf:capturedAt": "2024-01-15T00:00:00-05:00",
  "pkaf:capturedBy": "https://example.gov/connector/uscode-mirror",
  "pkaf:sourceUrl": "https://uscode.example.gov/title-42/chapter-106/section-9908",
  "pkaf:accessScope": "public",
  "pkaf:sourceAuthorityHint": "https://example.gov/source-authority/us-code-official"
}
```

### Step 2 — SourceFragment (identity verification provision)

```json
{
  "@id": "https://example.gov/fragment/csbg-act-section-1234/subsec-b-2",
  "@type": "pkaf:SourceFragment",
  "pkaf:artifactId": "https://example.gov/artifact/csbg-act-section-1234-codified-2024",
  "pkaf:fragmentType": "section",
  "pkaf:locator": "section[@num='1234']/subsection[@designation='b']/paragraph[@num='2']",
  "pkaf:selector": {
    "@type": "oa:TextQuoteSelector",
    "oa:exact": "Each individual enrolling for benefits under this section shall provide documentation establishing identity in such form as the Secretary by regulation prescribes."
  },
  "pkaf:accessScope": "public"
}
```

### Step 3 — Statute as PolicyResourceVersion

```json
{
  "@id": "https://example.gov/resource/csbg-act-section-1234/v1",
  "@type": "pkaf:PolicyResourceVersion",
  "pkaf:resourceLineage": "https://example.gov/resource/csbg-act-section-1234",
  "pkaf:versionLabel": "1998-as-codified-through-2024",
  "pkaf:effectivePeriodStart": "1998-01-01T00:00:00-05:00",
  "pkaf:realizedByArtifact": "https://example.gov/artifact/csbg-act-section-1234-codified-2024",
  "pkaf:resourceKind": "federalStatute",
  "pkaf:citation": "42 U.S.C. § 9908",
  "pkaf:accessScope": "public"
}
```

### Step 4 — SourceAuthority for the statute

```json
{
  "@id": "https://example.gov/source-authority/us-code-official",
  "@type": "pkaf:SourceAuthority",
  "pkaf:sourceFamily": "us-code",
  "pkaf:officialStatus": "pkaf:officialLegalEdition",
  "pkaf:legalValue": "pkaf:positiveLaw",
  "pkaf:publicationStatus": "pkaf:enacted",
  "pkaf:jurisdiction": "us-federal",
  "pkaf:publisher": "https://example.gov/agency/office-of-law-revision-counsel"
}
```

## Phase 2: Delegation instrument

### Step 5 — DelegationInstrument as PolicyResourceVersion

```json
{
  "@id": "https://example.gov/resource/hhs-delegation-to-ocs-csbg/v1",
  "@type": ["pkaf:PolicyResourceVersion", "pkaf:DelegationInstrument"],
  "pkaf:resourceLineage": "https://example.gov/resource/hhs-delegation-to-ocs-csbg",
  "pkaf:versionLabel": "delegation-1999-rev-2018",
  "pkaf:effectivePeriodStart": "1999-04-01T00:00:00-05:00",
  "pkaf:resourceKind": "federalDelegationInstrument",
  "pkaf:citation": "HHS Delegation 5-25-99 (as revised 2018)",
  "pkaf:delegatingAuthority": "https://example.gov/agency/hhs-secretary",
  "pkaf:delegatedTo": "https://example.gov/agency/office-of-community-services",
  "pkaf:delegationScope": "csbg-implementing-regulations",
  "pkaf:accessScope": "public"
}
```

### Step 6 — Delegation `derivesAuthorityFrom` statute

```json
{
  "@id": "https://example.gov/assertion/delegation-derives-from-statute",
  "@type": "pkaf:RelationshipAssertion",
  "pkaf:assertsSubject": "https://example.gov/resource/hhs-delegation-to-ocs-csbg/v1",
  "pkaf:assertsPredicate": "pkaf:derivesAuthorityFrom",
  "pkaf:assertsObject": "https://example.gov/resource/csbg-act-section-1234/v1",
  "pkaf:assertionOrigin": "pkaf:importedFromSource",
  "pkaf:hasTrustZone": "pkaf:Z4AttestedAssertion",
  "pkaf:hasSafetyLabel": "pkaf:A3AuthorityCritical",
  "pkaf:usageEligibility": "pkaf:officialUse",
  "pkaf:authorityKind": "pkaf:delegated",
  "pkaf:hasEvidence": [
    {
      "@type": "pkaf:EvidenceBinding",
      "pkaf:evidenceRole": "pkaf:authorityCitation",
      "pkaf:supportingQuote": "Pursuant to 42 U.S.C. § 9908(b)(2), the Secretary delegates to the Office of Community Services..."
    }
  ]
}
```

## Phase 3: Federal regulation

### Step 7 — Regulation as PolicyResourceVersion

```json
{
  "@id": "https://example.gov/resource/45-cfr-96-30/v3",
  "@type": "pkaf:PolicyResourceVersion",
  "pkaf:resourceLineage": "https://example.gov/resource/45-cfr-96-30",
  "pkaf:versionLabel": "2021-revision",
  "pkaf:effectivePeriodStart": "2021-07-01T00:00:00-05:00",
  "pkaf:resourceKind": "federalRegulation",
  "pkaf:citation": "45 CFR § 96.30",
  "pkaf:accessScope": "public"
}
```

### Step 8 — Regulation `derivesAuthorityFrom` delegation

```json
{
  "@id": "https://example.gov/assertion/regulation-derives-from-delegation",
  "@type": "pkaf:RelationshipAssertion",
  "pkaf:assertsSubject": "https://example.gov/resource/45-cfr-96-30/v3",
  "pkaf:assertsPredicate": "pkaf:derivesAuthorityFrom",
  "pkaf:assertsObject": "https://example.gov/resource/hhs-delegation-to-ocs-csbg/v1",
  "pkaf:assertionOrigin": "pkaf:importedFromSource",
  "pkaf:hasTrustZone": "pkaf:Z4AttestedAssertion",
  "pkaf:hasSafetyLabel": "pkaf:A3AuthorityCritical",
  "pkaf:usageEligibility": "pkaf:officialUse",
  "pkaf:authorityKind": "pkaf:regulatory",
  "pkaf:hasEvidence": [
    {
      "@type": "pkaf:EvidenceBinding",
      "pkaf:evidenceRole": "pkaf:authorityCitation",
      "pkaf:supportingQuote": "Authority: HHS Delegation 5-25-99 (as revised 2018); 42 U.S.C. § 9908"
    }
  ]
}
```

## Phase 4: State adoption

### Step 9 — State regulation as PolicyResourceVersion

```json
{
  "@id": "https://example.us-state.gov/resource/state-csbg-implementation/v2",
  "@type": "pkaf:PolicyResourceVersion",
  "pkaf:resourceLineage": "https://example.us-state.gov/resource/state-csbg-implementation",
  "pkaf:versionLabel": "2022-revision",
  "pkaf:effectivePeriodStart": "2022-10-01T00:00:00-05:00",
  "pkaf:resourceKind": "stateRegulation",
  "pkaf:citation": "State Admin Code Title 5 Chapter 92 § 12",
  "pkaf:accessScope": "public"
}
```

### Step 10 — State regulation `derivesAuthorityFrom` federal regulation

```json
{
  "@id": "https://example.us-state.gov/assertion/state-derives-from-federal",
  "@type": "pkaf:RelationshipAssertion",
  "pkaf:assertsSubject": "https://example.us-state.gov/resource/state-csbg-implementation/v2",
  "pkaf:assertsPredicate": "pkaf:derivesAuthorityFrom",
  "pkaf:assertsObject": "https://example.gov/resource/45-cfr-96-30/v3",
  "pkaf:hasTrustZone": "pkaf:Z4AttestedAssertion",
  "pkaf:hasSafetyLabel": "pkaf:A3AuthorityCritical",
  "pkaf:usageEligibility": "pkaf:officialUse",
  "pkaf:authorityKind": "pkaf:regulatory"
}
```

## Phase 5: CAA-42 operationalization

### Step 11 — CAA-42 requirement assertion with `hasAuthority`

The CAA's operational requirement claims `hasAuthority` via the federal regulation. The chain terminates at the statute via `derivesAuthorityFrom`. Note `authorityKind: regulatory` on the `hasAuthority` assertion — the immediate authority object is the regulation.

```json
{
  "@id": "https://example.org/assertion/caa-42-identity-req-001",
  "@type": "pkaf:RelationshipAssertion",
  "pkaf:assertsSubject": "https://example.org/concepts/caa-42/IdentityVerification",
  "pkaf:assertsPredicate": "pkaf:hasAuthority",
  "pkaf:assertsObject": "https://example.gov/resource/45-cfr-96-30/v3",
  "pkaf:assertionOrigin": "pkaf:humanAsserted",
  "pkaf:hasTrustZone": "pkaf:Z4AttestedAssertion",
  "pkaf:hasSafetyLabel": "pkaf:A3AuthorityCritical",
  "pkaf:usageEligibility": "pkaf:localOperationalUse",
  "pkaf:authorityKind": "pkaf:regulatory",
  "pkaf:hasApplicability": {
    "@type": "pkaf:ApplicabilityContext",
    "pkaf:programArea": "csbg",
    "pkaf:jurisdiction": ["us-federal", "example-us-state"],
    "pkaf:effectivePeriodStart": "2022-10-01T00:00:00-05:00"
  },
  "pkaf:hasEvidence": [
    {
      "@type": "pkaf:EvidenceBinding",
      "pkaf:evidenceRole": "pkaf:authorityCitation",
      "pkaf:sourceFragment": "https://example.gov/fragment/45-cfr-96-30/identity-evidence-paragraph",
      "pkaf:supportingQuote": "Eligible entities shall verify each applicant's identity through documentation including but not limited to: state-issued identification, passport, or equivalent."
    }
  ]
}
```

### Step 12 — LocalAdoption (operational authorization, NOT legal authority)

This is the critical distinction. The LocalAdoption authorizes CAA-42 to operationalize the requirement in a specific workflow. It is `localOperational`, NOT `regulatory`. It does NOT grant authority — the regulatory authority is in the `hasAuthority` assertion above. LocalAdoption grants the org's own operational permission to enforce the requirement.

```json
{
  "@id": "https://example.org/adoption/caa-42-identity-req-001",
  "@type": "pkaf:LocalAdoption",
  "pkaf:organization": "https://example.org/org/caa-42",
  "pkaf:targetAssertion": "https://example.org/assertion/caa-42-identity-req-001",
  "pkaf:adoptionStatus": "pkaf:adoptedForLocalOperations",
  "pkaf:usageEligibility": "pkaf:localOperationalUse",
  "pkaf:adoptionAuthorityKind": "pkaf:localOperational",
  "pkaf:adoptionScope": "caa-42-csbg-intake-workflow-v4",
  "pkaf:authorizedBy": "https://example.org/user/caa-42-program-director-1",
  "pkaf:adoptionRationale": "Organizational authorization to operationalize the federally-required identity verification in CAA-42's CSBG intake workflow. This adoption does not assert legal authority; legal authority is provided by the hasAuthority chain to 45 CFR § 96.30.",
  "prov:generatedAtTime": "2022-11-15T10:00:00-05:00"
}
```

## Phase 6: WOS workflow step and Formspec field

### Step 13 — WOS workflow step `verify_identity`

```json
{
  "@id": "https://example.org/wos/caa-42-intake/verify-identity/v1",
  "@type": ["pkaf:GeneratedWorkProduct", "wos:WorkflowStep"],
  "wos:stepName": "verify_identity",
  "wos:stepLabel": "Verify applicant identity",
  "wos:stepType": "data-collection-and-verification",
  "wos:precedingSteps": ["wos:caa-42-intake/applicant-info-collection"],
  "wos:succeedingSteps": ["wos:caa-42-intake/eligibility-determination"],
  "pkaf:requiresEvidenceType": "https://example.org/concepts/caa-42/IdentityVerification",
  "pkaf:justifiedByAssertion": ["https://example.org/assertion/caa-42-identity-req-001"],
  "pkaf:justificationBackedBy": "https://example.org/adoption/caa-42-identity-req-001",
  "pkaf:consumerLifecycleState": "pkaf:operational",
  "pkaf:usageEligibility": "pkaf:localOperationalUse",
  "pkaf:bridgeContractVersion": "pkaf-bridge/1.0",
  "pkaf:hasApplicability": {
    "@type": "pkaf:ApplicabilityContext",
    "pkaf:programArea": "csbg"
  }
}
```

### Step 14 — Formspec field `identity_document`

```json
{
  "@id": "https://example.org/form-field/caa-42-intake/identity-document/v1",
  "@type": ["pkaf:GeneratedWorkProduct", "formspec:Field"],
  "formspec:fieldName": "identity_document",
  "formspec:label": "Identity documentation",
  "formspec:dataType": "file-upload",
  "formspec:required": true,
  "pkaf:collectsEvidenceType": "https://example.org/concepts/caa-42/IdentityVerification",
  "pkaf:justifiedByAssertion": ["https://example.org/assertion/caa-42-identity-req-001"],
  "pkaf:justificationBackedBy": "https://example.org/adoption/caa-42-identity-req-001",
  "pkaf:associatedWorkflowStep": "https://example.org/wos/caa-42-intake/verify-identity/v1",
  "pkaf:consumerLifecycleState": "pkaf:operational",
  "pkaf:usageEligibility": "pkaf:localOperationalUse",
  "pkaf:bridgeContractVersion": "pkaf-bridge/1.0"
}
```

### Step 15 — BridgeValidationResult (WOS, accepted)

```json
{
  "@id": "https://example.org/bridge-validation/caa-42-wos-2022-11-15-001",
  "@type": "pkaf:BridgeValidationResult",
  "pkaf:packetId": "https://example.org/wos/caa-42-intake/verify-identity/v1",
  "pkaf:consumer": "https://example.org/consumer/caa-42-wos",
  "pkaf:bridgeContractVersion": "pkaf-bridge/1.0",
  "pkaf:result": "pkaf:accepted",
  "pkaf:effectiveUsageEligibility": "pkaf:localOperationalUse",
  "pkaf:effectiveUsageEligibilityRationale": "Authority chain validated: caa-42-identity-req-001 hasAuthority(regulatory) → 45 CFR § 96.30 derivesAuthorityFrom(regulatory) → HHS delegation derivesAuthorityFrom(delegated) → statute § 1234 (statutory). LocalAdoption caa-42-identity-req-001 grants localOperationalUse within scope caa-42-csbg-intake-workflow-v4.",
  "pkaf:authorityChainTraversal": [
    {
      "@type": "pkaf:AuthorityChainHop",
      "pkaf:assertion": "https://example.org/assertion/caa-42-identity-req-001",
      "pkaf:predicate": "pkaf:hasAuthority",
      "pkaf:authorityKind": "pkaf:regulatory",
      "pkaf:object": "https://example.gov/resource/45-cfr-96-30/v3"
    },
    {
      "@type": "pkaf:AuthorityChainHop",
      "pkaf:assertion": "https://example.gov/assertion/regulation-derives-from-delegation",
      "pkaf:predicate": "pkaf:derivesAuthorityFrom",
      "pkaf:authorityKind": "pkaf:delegated",
      "pkaf:object": "https://example.gov/resource/hhs-delegation-to-ocs-csbg/v1"
    },
    {
      "@type": "pkaf:AuthorityChainHop",
      "pkaf:assertion": "https://example.gov/assertion/delegation-derives-from-statute",
      "pkaf:predicate": "pkaf:derivesAuthorityFrom",
      "pkaf:authorityKind": "pkaf:statutory",
      "pkaf:object": "https://example.gov/resource/csbg-act-section-1234/v1"
    }
  ],
  "pkaf:chainTerminusKind": "pkaf:statutory",
  "pkaf:errors": [],
  "pkaf:warnings": [],
  "pkaf:conceptResolutionResults": [],
  "prov:generatedAtTime": "2022-11-15T10:30:00-05:00"
}
```

### Step 16 — BridgeValidationResult (Formspec, accepted)

Same authority chain as Step 15. Abbreviated here:

```json
{
  "@id": "https://example.org/bridge-validation/caa-42-formspec-2022-11-15-001",
  "@type": "pkaf:BridgeValidationResult",
  "pkaf:packetId": "https://example.org/form-field/caa-42-intake/identity-document/v1",
  "pkaf:consumer": "https://example.org/consumer/caa-42-formspec",
  "pkaf:result": "pkaf:accepted",
  "pkaf:effectiveUsageEligibility": "pkaf:localOperationalUse",
  "pkaf:chainTerminusKind": "pkaf:statutory",
  "pkaf:errors": [],
  "pkaf:warnings": [],
  "prov:generatedAtTime": "2022-11-15T10:30:05-05:00"
}
```

## Phase 7: Statutory rescission

Years later, Congress passes legislation rescinding Section 1234, replacing the program structure entirely. The fixture traces the cascade.

### Step 17 — Rescinding statute artifact

```json
{
  "@id": "https://example.gov/artifact/csbg-restructure-act-2027",
  "@type": "pkaf:Artifact",
  "pkaf:sourceType": "official-codified-statute",
  "pkaf:capturedAt": "2027-03-01T00:00:00-05:00",
  "pkaf:sourceUrl": "https://uscode.example.gov/public-law-120-15",
  "pkaf:accessScope": "public"
}
```

### Step 18 — Successor (rescinding) PolicyResourceVersion

```json
{
  "@id": "https://example.gov/resource/csbg-restructure-act/v1",
  "@type": "pkaf:PolicyResourceVersion",
  "pkaf:resourceLineage": "https://example.gov/resource/csbg-restructure-act",
  "pkaf:versionLabel": "public-law-120-15",
  "pkaf:effectivePeriodStart": "2027-04-01T00:00:00-05:00",
  "pkaf:realizedByArtifact": "https://example.gov/artifact/csbg-restructure-act-2027",
  "pkaf:resourceKind": "federalStatute"
}
```

### Step 19 — `rescinds` assertion

```json
{
  "@id": "https://example.gov/assertion/rescission-001",
  "@type": "pkaf:RelationshipAssertion",
  "pkaf:assertsSubject": "https://example.gov/resource/csbg-restructure-act/v1",
  "pkaf:assertsPredicate": "pkaf:rescinds",
  "pkaf:assertsObject": "https://example.gov/resource/csbg-act-section-1234/v1",
  "pkaf:assertionOrigin": "pkaf:importedFromSource",
  "pkaf:hasTrustZone": "pkaf:Z4AttestedAssertion",
  "pkaf:hasSafetyLabel": "pkaf:A3AuthorityCritical",
  "pkaf:usageEligibility": "pkaf:officialUse",
  "pkaf:hasEvidence": [
    {
      "@type": "pkaf:EvidenceBinding",
      "pkaf:evidenceRole": "pkaf:rescissionEvidence",
      "pkaf:supportingQuote": "Section 1234 of the Community Services Block Grant Act (42 U.S.C. § 9908) is repealed effective April 1, 2027."
    }
  ],
  "pkaf:rescissionEffectiveDate": "2027-04-01T00:00:00-05:00"
}
```

### Step 20 — RescissionPacket with full authority cascade

```json
{
  "@id": "https://example.gov/packet/rescission-001",
  "@type": "pkaf:RescissionPacket",
  "pkaf:emittedBy": "https://example.gov/assertion/rescission-001",
  "pkaf:effectiveDate": "2027-04-01T00:00:00-05:00",
  "pkaf:bridgeContractVersion": "pkaf-bridge/1.0",
  "pkaf:cascadeAlgorithm": "pkaf:CascadeClosureV1",
  "pkaf:cascadeClosureDescription": "Transitive closure over inverse {derivesAuthorityFrom, hasAuthority, implements, justifiedByAssertion, derivedFromFragment} edges, scoped to active/adopted state at effectiveDate. Authority-chain edges (hasAuthority, derivesAuthorityFrom) propagate breakage downstream when the object resource is rescinded.",
  "pkaf:affectedAuthorityAssertions": [
    "https://example.gov/assertion/delegation-derives-from-statute",
    "https://example.gov/assertion/regulation-derives-from-delegation",
    "https://example.us-state.gov/assertion/state-derives-from-federal",
    "https://example.org/assertion/caa-42-identity-req-001"
  ],
  "pkaf:affectedAssertions": [
    "https://example.org/assertion/caa-42-identity-req-001"
  ],
  "pkaf:affectedAdoptions": [
    "https://example.org/adoption/caa-42-identity-req-001"
  ],
  "pkaf:affectedWorkProducts": [
    "https://example.org/wos/caa-42-intake/verify-identity/v1",
    "https://example.org/form-field/caa-42-intake/identity-document/v1"
  ],
  "pkaf:requiredRevalidationActions": [
    {
      "@type": "pkaf:RevalidationAction",
      "pkaf:targetAssertion": "https://example.org/assertion/caa-42-identity-req-001",
      "pkaf:reason": "hasAuthority object (45 CFR § 96.30) inherits broken authority chain via derivesAuthorityFrom hop to rescinded statute. Assertion's A3 authority chain no longer terminates at a valid source.",
      "pkaf:priority": "critical"
    },
    {
      "@type": "pkaf:RevalidationAction",
      "pkaf:targetWorkProduct": "https://example.org/wos/caa-42-intake/verify-identity/v1",
      "pkaf:reason": "WOS step depends on caa-42-identity-req-001 whose authority chain is broken. Step transitions to staleForCurrentUse for new cases.",
      "pkaf:priority": "critical"
    },
    {
      "@type": "pkaf:RevalidationAction",
      "pkaf:targetWorkProduct": "https://example.org/form-field/caa-42-intake/identity-document/v1",
      "pkaf:reason": "Formspec field depends on caa-42-identity-req-001 whose authority chain is broken. Field transitions to staleForCurrentUse for new cases.",
      "pkaf:priority": "critical"
    },
    {
      "@type": "pkaf:RevalidationAction",
      "pkaf:targetAdoption": "https://example.org/adoption/caa-42-identity-req-001",
      "pkaf:reason": "LocalAdoption target assertion no longer has valid authority chain. LocalAdoption does NOT grant authority; it grants operational authorization conditioned on the underlying assertion remaining valid. Adoption is effectively orphaned until either (a) a new authority chain is established, or (b) the adoption is rescinded.",
      "pkaf:priority": "critical"
    }
  ],
  "pkaf:pointInTimeExceptions": [
    {
      "@type": "pkaf:PointInTimeException",
      "pkaf:scopeDescription": "Applications submitted before 2027-04-01 may continue under prior authority for in-flight processing only",
      "pkaf:retainsAssertion": "https://example.org/assertion/caa-42-identity-req-001",
      "pkaf:evaluationAnchor": "pkaf:applicationSubmissionTime",
      "pkaf:exceptionEffectivePeriodEnd": "2027-04-01T00:00:00-05:00",
      "pkaf:rationale": "Per Public Law 120-15 § 4(c), pending applications under the prior statute shall be adjudicated under prior law."
    }
  ],
  "prov:generatedAtTime": "2027-03-15T00:00:00-05:00"
}
```

### Step 21 — BridgeValidationResult on WOS bridge (rescission cascade)

```json
{
  "@id": "https://example.org/bridge-validation/caa-42-wos-2027-03-15-001",
  "@type": "pkaf:BridgeValidationResult",
  "pkaf:packetId": "https://example.gov/packet/rescission-001",
  "pkaf:consumer": "https://example.org/consumer/caa-42-wos",
  "pkaf:bridgeContractVersion": "pkaf-bridge/1.0",
  "pkaf:result": "pkaf:acceptedWithWarnings",
  "pkaf:warnings": [
    {
      "@type": "pkaf:AuthorityChainBrokenWarning",
      "pkaf:affectedWorkProduct": "https://example.org/wos/caa-42-intake/verify-identity/v1",
      "pkaf:transitionTo": "pkaf:staleForCurrentUse",
      "pkaf:brokenChainHop": "https://example.gov/assertion/delegation-derives-from-statute",
      "pkaf:rescindedObject": "https://example.gov/resource/csbg-act-section-1234/v1",
      "pkaf:detail": "Step's authority chain terminates at statute § 1234 via derivesAuthorityFrom hops. Statute is rescinded effective 2027-04-01. Step transitions to staleForCurrentUse for new cases starting 2027-04-01. PointInTimeException applies: applications with applicationSubmissionTime before 2027-04-01 may continue under prior assertion."
    },
    {
      "@type": "pkaf:LocalAdoptionOrphanedWarning",
      "pkaf:affectedAdoption": "https://example.org/adoption/caa-42-identity-req-001",
      "pkaf:detail": "LocalAdoption's target assertion has broken authority chain. The adoption itself is procedurally still valid as an organizational decision, but it cannot continue to grant localOperationalUse for new cases because its target assertion no longer terminates at valid authority. This is the key truth-table case: LocalAdoption does not save the artifact from a broken authority chain."
    }
  ],
  "pkaf:staleDependencies": [
    "https://example.org/wos/caa-42-intake/verify-identity/v1"
  ],
  "pkaf:supportedPointInTimeAnchors": [
    "pkaf:applicationSubmissionTime"
  ],
  "pkaf:pointInTimeExceptionAccepted": true,
  "prov:generatedAtTime": "2027-03-15T01:00:00-05:00"
}
```

### Step 22 — BridgeValidationResult on Formspec bridge (rescission cascade)

Mirror structure for the Formspec field. Same authority-chain-broken warning, same LocalAdoption-orphaned warning, same PointInTimeException acceptance. (Abbreviated for length.)

### Step 23 — RevalidationEvents on both consumers

```json
{
  "@id": "https://example.org/revalidation/wos-verify-identity-postrescission",
  "@type": "pkaf:RevalidationEvent",
  "pkaf:triggeredByPacket": "https://example.gov/packet/rescission-001",
  "pkaf:targetAssertion": "https://example.org/assertion/caa-42-identity-req-001",
  "pkaf:targetWorkProduct": "https://example.org/wos/caa-42-intake/verify-identity/v1",
  "pkaf:transitionTo": "pkaf:staleForCurrentUse",
  "pkaf:revisedUsageEligibility": "pkaf:reviewQueueOnly",
  "pkaf:retainedPointInTimeException": {
    "@type": "pkaf:PointInTimeException",
    "pkaf:evaluationAnchor": "pkaf:applicationSubmissionTime",
    "pkaf:exceptionEffectivePeriodEnd": "2027-04-01T00:00:00-05:00"
  },
  "pkaf:queuedFor": "https://example.org/user/caa-42-program-director-1",
  "prov:generatedAtTime": "2027-03-15T01:00:05-05:00"
}
```

Same shape for the Formspec field.

## Phase 8: Resolution options (not exercised in detail; sketched)

After rescission, CAA-42 faces three options:

1. **Establish new authority.** If the successor statute (CSBG Restructure Act) requires identity verification under a different mechanism, CAA-42 can create a new `hasAuthority` assertion pointing to the successor regulation when it's promulgated. New `BridgeValidationResult` → accepted; new operational artifacts.

2. **Continue under PointInTimeException only.** In-flight applications can use the existing artifacts via the PointInTimeException for as long as applications submitted before 2027-04-01 remain in process. No new operational use.

3. **Discontinue the workflow entirely.** If no successor authority exists, the workflow step and field cannot be used operationally. CAA-42 either retires them or marks them historical-only.

This fixture stops at the staleForCurrentUse transition; a sibling fixture could exercise option 1 (new authority establishment) as a continuation.

---

## What this fixture proves (truth-table)

| Scenario | LocalAdoption status | Authority chain status | Operational use allowed? |
|---|---|---|---|
| Pre-rescission, normal operation | Active, `localOperational` | Intact | ✅ Yes |
| Post-rescission, new cases | Still active (procedurally) | Broken at statute | ❌ No — LocalAdoption cannot save it |
| Post-rescission, in-flight via PointInTimeException | Active | Was intact at submission time | ✅ Yes, for that case only |
| Post-rescission, no PointInTimeException | Active | Broken at statute | ❌ No |
| If LocalAdoption is rescinded but authority intact | Rescinded | Intact | ❌ No — operational authorization withdrawn |

**The critical row:** Post-rescission new cases. LocalAdoption is still procedurally present, but operational use is blocked because the underlying assertion's authority chain is broken. **LocalAdoption is operational authorization conditioned on valid authority, not authority itself.** This is the truth Mike wanted exercised.

## Model issues surfaced by this fixture

1. **`pkaf:authorityKind` on assertions vs on objects.** I put `authorityKind: regulatory` on the requirement assertion's `hasAuthority` (Step 11) and on the chain hops (Steps 6, 8). It expresses the kind of authority THIS hop represents. But the federal statute itself is `statutory`; the regulation is `regulatory`; the delegation is `delegated`. The chain "is" of mixed kinds. The bridge result records each hop's kind via `AuthorityChainHop` (Step 15). Worth confirming this is the right model: `authorityKind` describes the kind of authority granted by the predicate at that hop, not a global label on the assertion.

2. **`pkaf:chainTerminusKind` in BridgeValidationResult.** I introduced this in Step 15 to record what kind of authority the chain ultimately rests on (`statutory` in this case). Useful for consumers querying "is this artifact backed by statute or only by regulation?" Worth formalizing in PKAF Core's BridgeValidationResult shape.

3. **`pkaf:DelegationInstrument` as a typed subclass of `PolicyResourceVersion`.** Step 5 declares both types. The spec has `realizedByArtifact` and `resourceKind` but not a `DelegationInstrument` first-class type. Recommend adding to PKAF Core: it's a recognizable artifact category with specific fields (`delegatingAuthority`, `delegatedTo`, `delegationScope`).

4. **`AuthorityChainHop` as an explicit traversal record.** Step 15 has it as inline content. For consumers caching chain validation results, this should be a first-class type with its own URI. Worth formalizing.

5. **`pkaf:LocalAdoptionOrphanedWarning` (Step 21).** I introduced this to express the truth-table case. It's a specific subtype of warning that needs to be reachable from the `BridgeValidationResult` warnings list. Worth adding to the warning vocabulary alongside `pkaf:AuthorityChainBrokenWarning` and `pkaf:StaleDependencyWarning`.

6. **`pkaf:supportedPointInTimeAnchors` on BridgeValidationResult (Step 21).** I had `declaredSupportedAnchors` on `BridgeConsumerRegistration` earlier (per Mike's edit). Here I needed a result-side declaration that "yes, the consumer supports the anchor referenced by this packet's PointInTimeException." Worth confirming: should this be derived from the registration (and omitted from validation results), or restated per validation? I'd keep it on registration only, and let validation results have a boolean `pointInTimeExceptionAccepted`.

7. **`pkaf:affectedAdoptions` on RescissionPacket.** Step 20 includes affected adoptions in the cascade. The PKAF Core cascade closure algorithm needs to include `LocalAdoption.targetAssertion` inverse edges so that adoptions of broken-authority assertions are surfaced. Currently the algorithm in v0.2 fixture mentions affected assertions and work products but not adoptions explicitly. Worth updating `CascadeClosureV1` to include `LocalAdoption.targetAssertion` inverse edges.

8. **`pkaf:rescissionEffectiveDate` on the rescission assertion (Step 19).** The packet has `effectiveDate`; the assertion has `rescissionEffectiveDate`. Redundant — recommend keeping only on the packet, since multiple assertions of the same rescission could exist (e.g., separate state-level rescissions following federal).

## Conformance coverage matrix (cumulative across fixtures)

| Element | v0.2 (local-op) | Mapping v0.1 | Statutory v0.1 (this) |
|---|---|---|---|
| Direct concept resolution | ✅ | ✅ | ✅ |
| LocalConcept resolution | ❌ | ✅ | ❌ |
| Mapping conflicts (informational) | ❌ | ✅ | ❌ |
| AmendmentPacket cascade | ✅ | ❌ | ❌ |
| ConceptLifecyclePacket cascade | ❌ | ✅ | ❌ |
| RescissionPacket cascade | ❌ | ❌ | ✅ |
| `hasAuthority` with authorityKind | ❌ | ❌ | ✅ |
| `derivesAuthorityFrom` chain | ❌ | ❌ | ✅ |
| DelegationInstrument | ❌ | ❌ | ✅ |
| LocalAdoption chain terminus | ✅ | ✅ | ✅ |
| LocalAdoption insufficient when authority broken | ❌ | ❌ | ✅ |
| PointInTimeException with applicationSubmissionTime | ✅ | ❌ | ✅ |
| WOS step (not just Formspec field) | ❌ | ❌ | ✅ |
| `staleForCurrentUse` transition | ✅ | ✅ | ✅ |
| RevalidationClosureEvent | ✅ | ✅ | partial (not exercised here; would be in continuation) |
| Registry unavailable behavior | ❌ | ❌ | ❌ |
| Mapping conflicts (operational/publication/authority) | ❌ | ❌ | ❌ |
| CanonicalMapping resolution | ❌ | ❌ | ❌ |

## Remaining gap (one fixture)

A short **Registry Unavailable + High-Severity Conflict** fixture would close the matrix:

- Cache TTL boundaries (fresh, stale-but-usable, stale-but-A3-refused)
- Registry unreachable mid-validation
- Registry version out of declared range
- `operationalConflict` severity blocking two orgs' shared form
- `CanonicalMapping` from a registry authority resolving a conflict

5–10 steps. After that, the conformance fixture set is complete and SHACL drafting can start with full coverage anchors.
