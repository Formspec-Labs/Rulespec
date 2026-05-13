# PKAF ConceptRegistry v0.1.2

Status: Editor's Draft, normative module
Supersedes: v0.1.1
Companion to: PKAF Core, PKAF Conformance Fixture v0.2, PKAF Mapping Fixture v0.1, PKAF Statutory Authority Fixture v0.1
Bridge contract: `pkaf-bridge/1.0`

## Changes from v0.1.1

1. `pkaf:operationalScope` on `MappingApplicabilityContext` renamed to `pkaf:applicationDomain` to avoid collision with assertion-level `pkaf:scope` (§4.4)
2. `pkaf:resolvedToConcepts` formalized as a non-authoritative consumer-side cache (§5.7)
3. `pkaf:proposedUsageEligibility` added for "validate before promotion" workflows (§5.8)
4. `pkaf:SuggestedRemediation` added as a structured replacement for free-text remediation strings (§5.9)
5. Absence of `pkaf:safeAutomaticMigration` is the default; `pkaf:safeAutomaticMigrationStatus` available for explicit no-safe-migration declarations (§7.5)
6. `pkaf:supersedesAssertion` confirmed many-to-one and many-to-many; consumers MUST query the graph (§9.1)
7. New normative paragraph: concept resolution establishes semantic compatibility, NOT policy authority (§1.1)

## 1. Purpose and scope

PKAF's evidence model is concept-grounded. Every `collectsEvidenceType`, `requiresEvidenceType`, and concept-typed assertion references a concept identifier. ConceptRegistry defines what makes those identifiers stable, resolvable, and operationally trustworthy.

### 1.1 What concept resolution does and does not do

Concept resolution establishes **semantic compatibility**. It does NOT establish **policy authority**. A resolved concept may satisfy a `collectsEvidenceType` or `requiresEvidenceType` reference in a justification packet, but the artifact still requires its own PKAF justification chain (terminating at a valid `hasAuthority`, `derivesAuthorityFrom` chain, or scoped `LocalAdoption` per PKAF Bridge Rule 6) and its own effective `usageEligibility` per the reducer in Bridge Rule 2.

A consumer MUST NOT promote an artifact past `draftGenerationAllowed` on concept resolution alone. Concept resolution is a necessary precondition for operational use, not a sufficient one.

### 1.2 In scope

This document defines: concept types, registry model, mapping assertions with direction/strength/applicability, resolution rules and `ConceptResolutionResult`, concept lifecycle and `ConceptLifecyclePacket`, behavior under registry unavailability, LocalConcept promotion, and mapping disputes with severity.

### 1.3 Out of scope

The contents of any specific registry; legal or regulatory binding force of any concept (a registry MAY witness an authority chain — see §3.3 — but does not confer authority by membership alone); a substitute for ELI, schema.org, or domain-specific vocabularies (registries SHOULD reuse those where they exist).

## 2. Concept types

### 2.1 RegisteredConcept

A concept minted in and governed by a specific `ConceptRegistry`. Every `RegisteredConcept` is also a `skos:Concept`.

```json
{
  "@id": "https://registry.example.gov/concepts/PayStubEvidence",
  "@type": ["skos:Concept", "pkaf:RegisteredConcept"],
  "skos:prefLabel": "Pay stub evidence",
  "skos:altLabel": ["pay stub", "earnings statement"],
  "pkaf:managedByRegistry": "https://registry.example.gov/registries/public-benefits-evidence",
  "pkaf:conceptScope": "pkaf:public",
  "pkaf:conceptStatus": "pkaf:registered",
  "pkaf:registeredAt": "2025-11-01T00:00:00-05:00"
}
```

Required: `skos:prefLabel`, `pkaf:managedByRegistry`, `pkaf:conceptScope`, `pkaf:conceptStatus`.

### 2.2 LocalConcept

A concept defined within an organization or workspace scope.

```json
{
  "@id": "https://example.org/concepts/caa-42/IncomeDocs",
  "@type": ["skos:Concept", "pkaf:LocalConcept"],
  "skos:prefLabel": "Income docs",
  "pkaf:definedInScope": "https://example.org/org/caa-42",
  "pkaf:conceptScope": "pkaf:organization",
  "pkaf:conceptStatus": "pkaf:localActive"
}
```

Operational rules:

1. An unmapped LocalConcept MUST NOT appear in a published justification packet.
2. A LocalConcept used in any artifact MUST be surfaced in `BridgeValidationResult.conceptResolutionResults` as a `conceptResolutionWarning` unless it resolves through a trusted mapping (§4.5).
3. An unmapped LocalConcept is usable only at `usageEligibility: draftGenerationAllowed` or lower.

### 2.3 ConceptScheme

Same semantics as `skos:ConceptScheme`.

## 3. Registry model

### 3.1 ConceptRegistry

```json
{
  "@id": "https://registry.example.gov/registries/public-benefits-evidence",
  "@type": "pkaf:ConceptRegistry",
  "pkaf:registryName": "Public Benefits Evidence Concept Registry",
  "pkaf:namespacePrefix": "https://registry.example.gov/concepts/",
  "pkaf:mintingAuthority": "https://registry.example.gov/authorities/pbe-curation-board",
  "pkaf:governanceModel": "pkaf:federatedCuration",
  "pkaf:resolutionEndpoint": "https://registry.example.gov/api/v1/concepts/",
  "pkaf:registryVersion": "2026-04-01",
  "pkaf:declaresMappingPolicy": "https://registry.example.gov/policy/mapping-v1"
}
```

### 3.2 ConceptMintingAuthority

```json
{
  "@id": "https://registry.example.gov/authorities/pbe-curation-board",
  "@type": "pkaf:ConceptMintingAuthority",
  "pkaf:authorityKind": "pkaf:curationBoard",
  "pkaf:authorizedActions": [
    "pkaf:registerConcept",
    "pkaf:deprecateConcept",
    "pkaf:mergeConcepts",
    "pkaf:splitConcept",
    "pkaf:approveMapping"
  ]
}
```

### 3.3 RegistryGovernanceModel

Enumerated values: `pkaf:singleOrgGovernance`, `pkaf:federatedCuration`, `pkaf:openCommunity`, `pkaf:statutoryRegistry`, `pkaf:externalSkosVocabulary`.

`pkaf:statutoryRegistry` is a registry whose minting authority is established by statute or regulation. Registry status MAY serve as evidence in a `hasAuthority` or `derivesAuthorityFrom` chain (a sufficient witness), but MUST NOT by itself confer `authorityKind: regulatory` on arbitrary assertions. Authority chains remain explicit.

## 4. Concept mappings

Concept mappings are PKAF `RelationshipAssertion` instances whose predicate is a SKOS mapping property. They inherit evidence, attestation, scope, adoption, and lifecycle semantics from the assertion model.

### 4.1 Resolution strength

| Predicate | Semantics | Resolution behavior |
|---|---|---|
| `skos:exactMatch` | Concepts are semantically equivalent | Strong: sufficient for operational resolution **only when** the mapping is trusted per §4.5. The mapping must be trusted, not just present. |
| `skos:closeMatch` | Concepts are sufficiently similar to be used interchangeably in some contexts | Moderate: sufficient for `localOperationalUse` **only with** explicit `LocalAdoption` of the mapping AND a declared `MappingApplicabilityContext` (§4.4). Insufficient for `publicationAllowed` without further review. |
| `skos:broadMatch` | Subject concept is broader than object concept | Discovery only (S1). |
| `skos:narrowMatch` | Subject concept is narrower than object concept | Discovery only (S1). May be safe in some collection contexts but operational use requires a separate review. |
| `skos:relatedMatch` | Concepts are related but not in a hierarchical or equivalence relationship | Discovery only (S1). |

Predicate strength alone is not authorization. The mapping's own assertion-level trust (attestations, adoption, scope) determines what the mapping can authorize.

### 4.2 Direction

In a mapping `RelationshipAssertion`:
- `pkaf:assertsSubject` is the **source** concept being resolved.
- `pkaf:assertsObject` is the **target** concept — typically a `RegisteredConcept` or a concept in a more authoritative namespace.

For `broadMatch` and `narrowMatch`, direction reflects scope relationship: `LocalConcept skos:broadMatch RegisteredConcept` means the local concept is broader; `skos:narrowMatch` means narrower.

### 4.3 Mapping assertion shape

```json
{
  "@id": "https://example.org/assertion/caa-42-mapping-001",
  "@type": "pkaf:RelationshipAssertion",
  "pkaf:assertsSubject": "https://example.org/concepts/caa-42/IncomeDocs",
  "pkaf:assertsPredicate": "skos:closeMatch",
  "pkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "pkaf:assertionOrigin": "pkaf:humanAsserted",
  "pkaf:hasTrustZone": "pkaf:Z4AttestedAssertion",
  "pkaf:hasSafetyLabel": "pkaf:R2ReviewedOperational",
  "pkaf:usageEligibility": "pkaf:reviewQueueOnly",
  "pkaf:hasApplicability": {
    "@type": "pkaf:MappingApplicabilityContext",
    "pkaf:applicationDomain": "csbg-benefit-category-b-intake",
    "pkaf:evidencePurpose": ["eligibility-determination"],
    "pkaf:excludesPurposes": ["fraud-investigation", "tax-audit"]
  },
  "pkaf:scope": "https://example.org/org/caa-42"
}
```

### 4.4 MappingApplicabilityContext

A `closeMatch` mapping used at `localOperationalUse` or higher MUST include `pkaf:hasApplicability` declaring at minimum:

- **`pkaf:applicationDomain`** — the program, workflow, benefit category, process area, or service line in which the mapping is asserted to hold. (Renamed from `operationalScope` in v0.1.2 to avoid collision with assertion-level `pkaf:scope`.)
- **`pkaf:evidencePurpose`** — the evidence-collection purpose(s) the mapping covers.
- **`pkaf:excludesPurposes`** (recommended) — purposes the mapping explicitly does NOT cover.

Consumers MUST refuse to apply the mapping to an artifact whose evidence purpose is in `excludesPurposes` or outside the declared `evidencePurpose` list.

### 4.5 Trusted mapping

A mapping is **trusted** for a consumer when at least one of:

1. It is published in a registry with `RegistryGovernanceModel: federatedCuration | statutoryRegistry` and carries a `pkaf:approvedMapping` annotation from the registry's `ConceptMintingAuthority`.
2. It carries a `pkaf:CanonicalMapping` attestation from the registry's authority.
3. It has been locally adopted by the consumer's organization via a `LocalAdoption` event covering the mapping assertion.
4. It is asserted by an authority that the consumer's `BridgeConsumerRegistration` declares as trusted for mapping purposes.

A mapping present in the assertion ledger but not trusted resolves at most to `searchOnly`.

## 5. Resolution rules

### 5.1 Direct registered concept resolution

A reference to a `RegisteredConcept` URI resolves successfully iff:

1. The URI matches a `ConceptRegistry` namespace the consumer recognizes.
2. The concept's `pkaf:conceptStatus` permits operational use (see §7.1).
3. The registry's `pkaf:registryVersion` falls within the consumer's `pkaf:supportsRegistryVersionRange` or no version constraint applies.

### 5.2 Local concept resolution via mapping

Per §4.5 and the §4.1 resolution-strength table.

### 5.3 LocalConcept used directly without mapping

Per §2.2 rules.

### 5.4 ConceptResolutionResult

```json
{
  "@type": "pkaf:ConceptResolutionResult",
  "pkaf:inputConcept": "https://example.org/concepts/caa-42/IncomeDocs",
  "pkaf:resolvedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "pkaf:resolutionStatus": "pkaf:resolvedViaMapping",
  "pkaf:resolutionMethod": "pkaf:closeMatchLocallyAdopted",
  "pkaf:mappingAssertion": "https://example.org/assertion/caa-42-mapping-001",
  "pkaf:registryVersion": "2026-04-01",
  "pkaf:cacheStatus": "pkaf:fresh",
  "pkaf:usageCeiling": "pkaf:localOperationalUse",
  "pkaf:warnings": [],
  "pkaf:errors": []
}
```

`resolutionStatus` values: `resolvedDirect`, `resolvedViaMapping`, `unresolvedForOperationalUse`, `unresolvedNoMapping`, `unresolvedRegistryUnavailable`, `unresolvedConceptDeprecated`, `unresolvedConceptSplit`, `unresolvedConceptWithdrawn`.

`resolutionMethod` values: `directRegistry`, `exactMatchTrusted`, `closeMatchLocallyAdopted`, `closeMatchAwaitingAdoption`, `broadOrNarrowMatchDiscoveryOnly`, `cacheServed`, `staleCacheServed`.

### 5.5 Registry version compatibility

`BridgeConsumerRegistration` declares the registry-version range it supports via `pkaf:supportsRegistryVersionRange`. Out-of-range registry versions emit `pkaf:registryVersionOutOfRange` warning.

### 5.6 BridgeValidationResult population

ConceptRegistry adds to `BridgeValidationResult`:

- `pkaf:conceptResolutionResults[]` — full resolution record per concept reference
- `pkaf:staleConceptCache[]`
- `pkaf:registryUnavailable[]`
- `pkaf:registryVersionOutOfRange[]`

The deprecated `pkaf:unresolvedConcepts[]` field (kept for compatibility) is now a derived view; consumers SHOULD read from `conceptResolutionResults` filtered by status.

### 5.7 resolvedToConcepts as non-authoritative cache

A generated work product MAY carry `pkaf:resolvedToConcepts` to indicate the registered concept(s) its `collectsEvidenceType` or `requiresEvidenceType` resolved to at validation time. This is a denormalized consumer-side cache.

**Normative rules:**

1. `pkaf:resolvedToConcepts` MUST NOT be treated as authoritative.
2. Consumers MUST recompute it when mappings, registries, lifecycle packets, or local adoption events change.
3. A query about "what registered concept does this artifact collect" MUST traverse the mapping graph if the cache is stale or absent.
4. The cache is parallel to `pkaf:consumerLifecycleState` (Bridge contract): useful for UI/query speed, not source truth.

```json
{
  "pkaf:collectsEvidenceType": "https://example.org/concepts/caa-42/IncomeDocs",
  "pkaf:resolvedToConcepts": [
    "https://registry.example.gov/concepts/HouseholdIncomeEvidence-W2Filers",
    "https://registry.example.gov/concepts/HouseholdIncomeEvidence-NonW2Filers"
  ]
}
```

### 5.8 proposedUsageEligibility

Generated work products in a pre-promotion state MAY declare `pkaf:proposedUsageEligibility` to ask the bridge "would this be allowed at this ceiling?" without committing the artifact to that state.

**Rules:**

1. `pkaf:usageEligibility` is the artifact's **current** effective ceiling.
2. `pkaf:proposedUsageEligibility` is the **requested** promotion target.
3. When both are present, `BridgeValidationResult` evaluates the proposal against the reducer (Bridge Rule 2) and the concept resolution stack:
   - `result: accepted` → proposal can be committed by setting `usageEligibility` to the proposed value
   - `result: acceptedWithWarnings` → proposal can be committed but warnings remain on the validation record
   - `result: rejected` → proposal is refused; consumer SHOULD apply `suggestedRemediation` (§5.9) before retrying

```json
{
  "pkaf:usageEligibility": "pkaf:draftGenerationAllowed",
  "pkaf:proposedUsageEligibility": "pkaf:localOperationalUse"
}
```

### 5.9 SuggestedRemediation

A structured remediation hint emitted on `BridgeValidationResult.result: rejected` (and optionally on `acceptedWithWarnings`).

```json
{
  "@type": "pkaf:SuggestedRemediation",
  "pkaf:remediationAction": "pkaf:createMapping",
  "pkaf:fromConcept": "https://example.org/concepts/caa-77/HouseholdIncomeProof",
  "pkaf:toConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "pkaf:requiredPredicate": "skos:closeMatch",
  "pkaf:requiredApplicability": {
    "@type": "pkaf:MappingApplicabilityContext",
    "pkaf:applicationDomain": "caa-77-intake",
    "pkaf:evidencePurpose": ["eligibility-determination"]
  },
  "pkaf:requiredAdoptionScope": "https://example.org/org/caa-77",
  "pkaf:minimumUsageEligibility": "pkaf:localOperationalUse",
  "pkaf:humanReviewRequired": true
}
```

`remediationAction` enumerated values: `createMapping`, `adoptMapping`, `narrowApplicability`, `obtainAttestation`, `obtainLocalAdoption`, `awaitConceptRegistration`, `disambiguateSplitConcept`, `replaceSupersededReference`, `requestCanonicalMapping`.

Free-text remediation MAY appear additionally in `pkaf:remediationNote` but the structured form is required for `rejected` results.

## 6. Consumer cache and registry unavailability

### 6.1 Cache and TTL

```json
{
  "@type": "pkaf:ConceptCacheEntry",
  "pkaf:concept": "https://registry.example.gov/concepts/PayStubEvidence",
  "pkaf:cachedRegistryVersion": "2026-04-01",
  "pkaf:cachedAt": "2026-05-10T15:00:00-05:00",
  "pkaf:ttlSeconds": 86400
}
```

Recommended TTLs: 24h for `statutoryRegistry`, 4h for `federatedCuration`/`singleOrgGovernance`, 5min or no cache for `LocalConcept` and org-scoped mappings.

### 6.2 Registry unavailability behavior

| Situation | Behavior |
|---|---|
| Concept in cache, within TTL | Use cached; no warning |
| In cache, past TTL, non-critical concept | MAY use stale; emit `acceptedWithWarnings` with `staleConceptCache` |
| In cache, past TTL, A3 authority-critical concept | MUST refuse (`rejected`) |
| Not in cache, registry reachable | Resolve normally |
| Not in cache, registry unreachable | MUST emit `rejected` with `pkaf:registryUnavailable` |

## 7. Concept lifecycle

### 7.1 Status → resolution behavior (normative)

| Status | Resolution behavior |
|---|---|
| `pkaf:proposed` | Resolves at `searchOnly` |
| `pkaf:registered` | Resolves normally |
| `pkaf:deprecated` | Resolves with warning; new published packets refused unless `pkaf:deprecationOverride` attestation present |
| `pkaf:replacedBy` | Resolves to successor with `conceptMigrationWarning`; migration scheduled |
| `pkaf:mergedInto` | Resolves to successor; migration required |
| `pkaf:splitInto` | Unresolved for operational use until disambiguated by attestation or successor mapping |
| `pkaf:withdrawn` | Unresolved; operational use blocked; existing artifacts transition to `staleForCurrentUse` |
| `pkaf:localActive` | LocalConcept; resolves only within `pkaf:definedInScope` and via mappings |

### 7.2–7.4 Deprecation, Merge, Split

[Shapes unchanged from v0.1.1; see prior version for the `pkaf:replacedBy` / `pkaf:absorbedConcepts` / `pkaf:splitInto` patterns. Reproduced briefly in fixtures.]

### 7.5 ConceptLifecyclePacket

```json
{
  "@type": "pkaf:ConceptLifecyclePacket",
  "pkaf:lifecycleEvent": "pkaf:split",
  "pkaf:subjectConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "pkaf:successorConcepts": [...],
  "pkaf:effectiveDate": "2027-01-01T00:00:00-05:00",
  "pkaf:bridgeContractVersion": "pkaf-bridge/1.0",
  "pkaf:cascadeAlgorithm": "pkaf:CascadeClosureV1",
  "pkaf:affectedAssertions": [],
  "pkaf:affectedWorkProducts": [],
  "pkaf:requiredMigrationActions": []
}
```

**`pkaf:safeAutomaticMigration` semantics (v0.1.2):**

- **Absent** (property not present) is the default: no automatic migration is declared; consumers MUST transition affected operational artifacts to `staleForCurrentUse`.
- **Present** with a declared migration type (e.g., `pkaf:replaceInPlace`, `pkaf:pinToHistoricalSuccessor`): consumers MAY auto-migrate if their `BridgeConsumerRegistration` declares support for that migration type.
- **Explicit no-safe-migration declaration:** registries MAY use `pkaf:safeAutomaticMigrationStatus: pkaf:noSafeAutomaticMigration` to declare that no auto-migration is possible (useful for split/merge events where disambiguation is intrinsically manual).

Do NOT use `null` for absent migrations. JSON-LD null semantics are ambiguous; omit the property entirely.

**Normative cascade rule:** A `ConceptLifecyclePacket` whose `lifecycleEvent` is `pkaf:deprecation`, `pkaf:withdrawal`, `pkaf:merge`, `pkaf:split`, or `pkaf:replacedBy` (without `safeAutomaticMigration: replaceInPlace`) and that affects an operational Formspec field or WOS step MUST cause the consumer to transition the affected artifact to `pkaf:staleForCurrentUse`.

## 8. Mapping disputes

Mappings are scoped assertions; disagreement is first-class. `MappingConflict` carries severity:

| Severity | Meaning | Consumer behavior |
|---|---|---|
| `pkaf:informational` | Mappings disagree but no shared operational context affected | Record; no operational impact |
| `pkaf:operationalConflict` | Shared operational artifact depends on incompatible mappings | Affected artifacts → `staleForCurrentUse` |
| `pkaf:publicationBlocking` | Scheduled publication depends on conflicting mappings | Publication MUST be blocked |
| `pkaf:authorityCritical` | Conflict involves mapping in `hasAuthority`/`derivesAuthorityFrom` chain | A3 review required; affected authority assertions → `disputed` |

## 9. Supersession and promotion

### 9.1 Supersession semantics

`pkaf:supersedesAssertion` is **many-to-one and many-to-many**:

- A single assertion MAY be superseded by multiple successor assertions (split case).
- Multiple prior assertions MAY be superseded by one successor assertion (consolidation case).
- Both can occur simultaneously (rare but valid: a reorganization of related assertions).

Consumers MUST query the supersession graph rather than assume a single successor. The PKAF Core SHACL shape for `pkaf:supersedesAssertion` is `0..*` cardinality on both sides of the relationship.

### 9.2 LocalConcept promotion

[Unchanged from v0.1.1: registration request → `ConceptRegistrationEvent` by `ConceptMintingAuthority` → new `RegisteredConcept` published → automatic `exactMatch` mapping with `pkaf:trusted: true` (canonical) from LocalConcept → existing references resolve via mapping → consumers MAY migrate at discretion.]

## 10. Conformance levels

| Level | Required |
|---|---|
| `ConceptRegistry-Core` | §§1–5: concept shapes, registry model, mapping assertions with direction and applicability, direct resolution, LocalConcept resolution, `ConceptResolutionResult`, `BridgeValidationResult` integration including `resolvedToConcepts`/`proposedUsageEligibility`/`SuggestedRemediation`, minimum registry-unavailable behavior (refuse on unreachable) |
| `ConceptRegistry-Lifecycle` | Core + §§6–7: full cache/TTL, lifecycle statuses with normative resolution behavior, `ConceptLifecyclePacket` with `staleForCurrentUse` propagation, full registry-unavailability handling |
| `ConceptRegistry-Federated` | Lifecycle + §§8–9: mapping disputes with severity, `CanonicalMapping` attestations, cross-registry mappings, scoped conflict handling, many-to-many supersession, LocalConcept promotion |

## 11. Open questions

1. Should `ConceptUse` become first-class? Deferred.
2. Mapping predicates beyond SKOS for legal contexts? Extension point.
3. SHACL shape-match for LocalConcept promotion? Registry governance, not core.
4. `safeAutomaticMigration` enumeration scope? Currently `replaceInPlace` and `pinToHistoricalSuccessor` recommended; extensions via URI.
5. Access controls for private federated registries? Separate spec.
