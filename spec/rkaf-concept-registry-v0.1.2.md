# Rulespec ConceptRegistry v0.1.2

Status: Editor's Draft, normative module
Supersedes: v0.1.1
Companion to: Rulespec Core, Rulespec Conformance Fixture v0.2, Rulespec Mapping Fixture v0.1, Rulespec Statutory Authority Fixture v0.1
Bridge contract: `rkaf-bridge/1.0`

## Changes from v0.1.1

1. `rkaf:operationalScope` on `MappingApplicabilityContext` renamed to `rkaf:applicationDomain` to avoid collision with assertion-level `rkaf:scope` (§4.4)
2. `rkaf:resolvedToConcepts` formalized as a non-authoritative consumer-side cache (§5.7)
3. `rkaf:proposedUsageEligibility` added for "validate before promotion" workflows (§5.8)
4. `rkaf:SuggestedRemediation` added as a structured replacement for free-text remediation strings (§5.9)
5. Absence of `rkaf:safeAutomaticMigration` is the default; `rkaf:safeAutomaticMigrationStatus` available for explicit no-safe-migration declarations (§7.5)
6. `rkaf:supersedesAssertion` confirmed many-to-one and many-to-many; consumers MUST query the graph (§9.1)
7. New normative paragraph: concept resolution establishes semantic compatibility, NOT policy authority (§1.1)

## 1. Purpose and scope

Rulespec's evidence model is concept-grounded. Every `collectsEvidenceType`, `requiresEvidenceType`, and concept-typed assertion references a concept identifier. ConceptRegistry defines what makes those identifiers stable, resolvable, and operationally trustworthy.

### 1.1 What concept resolution does and does not do

Concept resolution establishes **semantic compatibility**. It does NOT establish **policy authority**. A resolved concept may satisfy a `collectsEvidenceType` or `requiresEvidenceType` reference in a justification packet, but the artifact still requires its own Rulespec justification chain (terminating at a valid `hasAuthority`, `derivesAuthorityFrom` chain, or scoped `LocalAdoption` per Rulespec Bridge Rule 6) and its own effective `usageEligibility` per the reducer in Bridge Rule 2.

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
  "@type": ["skos:Concept", "rkaf:RegisteredConcept"],
  "skos:prefLabel": "Pay stub evidence",
  "skos:altLabel": ["pay stub", "earnings statement"],
  "rkaf:managedByRegistry": "https://registry.example.gov/registries/public-benefits-evidence",
  "rkaf:conceptScope": "rkaf:public",
  "rkaf:conceptStatus": "rkaf:registered",
  "rkaf:registeredAt": "2025-11-01T00:00:00-05:00"
}
```

Required: `skos:prefLabel`, `rkaf:managedByRegistry`, `rkaf:conceptScope`, `rkaf:conceptStatus`.

### 2.2 LocalConcept

A concept defined within an organization or workspace scope.

```json
{
  "@id": "https://example.org/concepts/caa-42/IncomeDocs",
  "@type": ["skos:Concept", "rkaf:LocalConcept"],
  "skos:prefLabel": "Income docs",
  "rkaf:definedInScope": "https://example.org/org/caa-42",
  "rkaf:conceptScope": "rkaf:organization",
  "rkaf:conceptStatus": "rkaf:localActive"
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
  "@type": "rkaf:ConceptRegistry",
  "rkaf:registryName": "Public Benefits Evidence Concept Registry",
  "rkaf:namespacePrefix": "https://registry.example.gov/concepts/",
  "rkaf:mintingAuthority": "https://registry.example.gov/authorities/pbe-curation-board",
  "rkaf:governanceModel": "rkaf:federatedCuration",
  "rkaf:resolutionEndpoint": "https://registry.example.gov/api/v1/concepts/",
  "rkaf:registryVersion": "2026-04-01",
  "rkaf:declaresMappingPolicy": "https://registry.example.gov/policy/mapping-v1"
}
```

### 3.2 ConceptMintingAuthority

```json
{
  "@id": "https://registry.example.gov/authorities/pbe-curation-board",
  "@type": "rkaf:ConceptMintingAuthority",
  "rkaf:authorityKind": "rkaf:curationBoard",
  "rkaf:authorizedActions": [
    "rkaf:registerConcept",
    "rkaf:deprecateConcept",
    "rkaf:mergeConcepts",
    "rkaf:splitConcept",
    "rkaf:approveMapping"
  ]
}
```

### 3.3 RegistryGovernanceModel

Enumerated values: `rkaf:singleOrgGovernance`, `rkaf:federatedCuration`, `rkaf:openCommunity`, `rkaf:statutoryRegistry`, `rkaf:externalSkosVocabulary`.

`rkaf:statutoryRegistry` is a registry whose minting authority is established by statute or regulation. Registry status MAY serve as evidence in a `hasAuthority` or `derivesAuthorityFrom` chain (a sufficient witness), but MUST NOT by itself confer `authorityKind: regulatory` on arbitrary assertions. Authority chains remain explicit.

## 4. Concept mappings

Concept mappings are Rulespec `RelationshipAssertion` instances whose predicate is a SKOS mapping property. They inherit evidence, attestation, scope, adoption, and lifecycle semantics from the assertion model.

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
- `rkaf:assertsSubject` is the **source** concept being resolved.
- `rkaf:assertsObject` is the **target** concept — typically a `RegisteredConcept` or a concept in a more authoritative namespace.

For `broadMatch` and `narrowMatch`, direction reflects scope relationship: `LocalConcept skos:broadMatch RegisteredConcept` means the local concept is broader; `skos:narrowMatch` means narrower.

### 4.3 Mapping assertion shape

```json
{
  "@id": "https://example.org/assertion/caa-42-mapping-001",
  "@type": "rkaf:RelationshipAssertion",
  "rkaf:assertsSubject": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:assertsPredicate": "skos:closeMatch",
  "rkaf:assertsObject": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:assertionOrigin": "rkaf:humanAsserted",
  "rkaf:hasTrustZone": "rkaf:Z4AttestedAssertion",
  "rkaf:hasSafetyLabel": "rkaf:R2ReviewedOperational",
  "rkaf:usageEligibility": "rkaf:reviewQueueOnly",
  "rkaf:hasApplicability": {
    "@type": "rkaf:MappingApplicabilityContext",
    "rkaf:applicationDomain": "csbg-benefit-category-b-intake",
    "rkaf:evidencePurpose": ["eligibility-determination"],
    "rkaf:excludesPurposes": ["fraud-investigation", "tax-audit"]
  },
  "rkaf:scope": "https://example.org/org/caa-42"
}
```

### 4.4 MappingApplicabilityContext

A `closeMatch` mapping used at `localOperationalUse` or higher MUST include `rkaf:hasApplicability` declaring at minimum:

- **`rkaf:applicationDomain`** — the program, workflow, benefit category, process area, or service line in which the mapping is asserted to hold. (Renamed from `operationalScope` in v0.1.2 to avoid collision with assertion-level `rkaf:scope`.)
- **`rkaf:evidencePurpose`** — the evidence-collection purpose(s) the mapping covers.
- **`rkaf:excludesPurposes`** (recommended) — purposes the mapping explicitly does NOT cover.

Consumers MUST refuse to apply the mapping to an artifact whose evidence purpose is in `excludesPurposes` or outside the declared `evidencePurpose` list.

### 4.5 Trusted mapping

A mapping is **trusted** for a consumer when at least one of:

1. It is published in a registry with `RegistryGovernanceModel: federatedCuration | statutoryRegistry` and carries a `rkaf:approvedMapping` annotation from the registry's `ConceptMintingAuthority`.
2. It carries a `rkaf:CanonicalMapping` attestation from the registry's authority.
3. It has been locally adopted by the consumer's organization via a `LocalAdoption` event covering the mapping assertion.
4. It is asserted by an authority that the consumer's `BridgeConsumerRegistration` declares as trusted for mapping purposes.

A mapping present in the assertion ledger but not trusted resolves at most to `searchOnly`.

## 5. Resolution rules

### 5.1 Direct registered concept resolution

A reference to a `RegisteredConcept` URI resolves successfully iff:

1. The URI matches a `ConceptRegistry` namespace the consumer recognizes.
2. The concept's `rkaf:conceptStatus` permits operational use (see §7.1).
3. The registry's `rkaf:registryVersion` falls within the consumer's `rkaf:supportsRegistryVersionRange` or no version constraint applies.

### 5.2 Local concept resolution via mapping

Per §4.5 and the §4.1 resolution-strength table.

### 5.3 LocalConcept used directly without mapping

Per §2.2 rules.

### 5.4 ConceptResolutionResult

```json
{
  "@type": "rkaf:ConceptResolutionResult",
  "rkaf:inputConcept": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:resolvedConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:resolutionStatus": "rkaf:resolvedViaMapping",
  "rkaf:resolutionMethod": "rkaf:closeMatchLocallyAdopted",
  "rkaf:mappingAssertion": "https://example.org/assertion/caa-42-mapping-001",
  "rkaf:registryVersion": "2026-04-01",
  "rkaf:cacheStatus": "rkaf:fresh",
  "rkaf:usageCeiling": "rkaf:localOperationalUse",
  "rkaf:warnings": [],
  "rkaf:errors": []
}
```

`resolutionStatus` values: `resolvedDirect`, `resolvedViaMapping`, `unresolvedForOperationalUse`, `unresolvedNoMapping`, `unresolvedRegistryUnavailable`, `unresolvedConceptDeprecated`, `unresolvedConceptSplit`, `unresolvedConceptWithdrawn`.

`resolutionMethod` values: `directRegistry`, `exactMatchTrusted`, `closeMatchLocallyAdopted`, `closeMatchAwaitingAdoption`, `broadOrNarrowMatchDiscoveryOnly`, `cacheServed`, `staleCacheServed`.

### 5.5 Registry version compatibility

`BridgeConsumerRegistration` declares the registry-version range it supports via `rkaf:supportsRegistryVersionRange`. Out-of-range registry versions emit `rkaf:registryVersionOutOfRange` warning.

### 5.6 BridgeValidationResult population

ConceptRegistry adds to `BridgeValidationResult`:

- `rkaf:conceptResolutionResults[]` — full resolution record per concept reference
- `rkaf:staleConceptCache[]`
- `rkaf:registryUnavailable[]`
- `rkaf:registryVersionOutOfRange[]`

The deprecated `rkaf:unresolvedConcepts[]` field (kept for compatibility) is now a derived view; consumers SHOULD read from `conceptResolutionResults` filtered by status.

### 5.7 resolvedToConcepts as non-authoritative cache

A generated work product MAY carry `rkaf:resolvedToConcepts` to indicate the registered concept(s) its `collectsEvidenceType` or `requiresEvidenceType` resolved to at validation time. This is a denormalized consumer-side cache.

**Normative rules:**

1. `rkaf:resolvedToConcepts` MUST NOT be treated as authoritative.
2. Consumers MUST recompute it when mappings, registries, lifecycle packets, or local adoption events change.
3. A query about "what registered concept does this artifact collect" MUST traverse the mapping graph if the cache is stale or absent.
4. The cache is parallel to `rkaf:consumerLifecycleState` (Bridge contract): useful for UI/query speed, not source truth.

```json
{
  "rkaf:collectsEvidenceType": "https://example.org/concepts/caa-42/IncomeDocs",
  "rkaf:resolvedToConcepts": [
    "https://registry.example.gov/concepts/HouseholdIncomeEvidence-W2Filers",
    "https://registry.example.gov/concepts/HouseholdIncomeEvidence-NonW2Filers"
  ]
}
```

### 5.8 proposedUsageEligibility

Generated work products in a pre-promotion state MAY declare `rkaf:proposedUsageEligibility` to ask the bridge "would this be allowed at this ceiling?" without committing the artifact to that state.

**Rules:**

1. `rkaf:usageEligibility` is the artifact's **current** effective ceiling.
2. `rkaf:proposedUsageEligibility` is the **requested** promotion target.
3. When both are present, `BridgeValidationResult` evaluates the proposal against the reducer (Bridge Rule 2) and the concept resolution stack:
   - `result: accepted` → proposal can be committed by setting `usageEligibility` to the proposed value
   - `result: acceptedWithWarnings` → proposal can be committed but warnings remain on the validation record
   - `result: rejected` → proposal is refused; consumer SHOULD apply `suggestedRemediation` (§5.9) before retrying

```json
{
  "rkaf:usageEligibility": "rkaf:draftGenerationAllowed",
  "rkaf:proposedUsageEligibility": "rkaf:localOperationalUse"
}
```

### 5.9 SuggestedRemediation

A structured remediation hint emitted on `BridgeValidationResult.result: rejected` (and optionally on `acceptedWithWarnings`).

```json
{
  "@type": "rkaf:SuggestedRemediation",
  "rkaf:remediationAction": "rkaf:createMapping",
  "rkaf:fromConcept": "https://example.org/concepts/caa-77/HouseholdIncomeProof",
  "rkaf:toConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:requiredPredicate": "skos:closeMatch",
  "rkaf:requiredApplicability": {
    "@type": "rkaf:MappingApplicabilityContext",
    "rkaf:applicationDomain": "caa-77-intake",
    "rkaf:evidencePurpose": ["eligibility-determination"]
  },
  "rkaf:requiredAdoptionScope": "https://example.org/org/caa-77",
  "rkaf:minimumUsageEligibility": "rkaf:localOperationalUse",
  "rkaf:humanReviewRequired": true
}
```

`remediationAction` enumerated values: `createMapping`, `adoptMapping`, `narrowApplicability`, `obtainAttestation`, `obtainLocalAdoption`, `awaitConceptRegistration`, `disambiguateSplitConcept`, `replaceSupersededReference`, `requestCanonicalMapping`.

Free-text remediation MAY appear additionally in `rkaf:remediationNote` but the structured form is required for `rejected` results.

## 6. Consumer cache and registry unavailability

### 6.1 Cache and TTL

```json
{
  "@type": "rkaf:ConceptCacheEntry",
  "rkaf:concept": "https://registry.example.gov/concepts/PayStubEvidence",
  "rkaf:cachedRegistryVersion": "2026-04-01",
  "rkaf:cachedAt": "2026-05-10T15:00:00-05:00",
  "rkaf:ttlSeconds": 86400
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
| Not in cache, registry unreachable | MUST emit `rejected` with `rkaf:registryUnavailable` |

## 7. Concept lifecycle

### 7.1 Status → resolution behavior (normative)

| Status | Resolution behavior |
|---|---|
| `rkaf:proposed` | Resolves at `searchOnly` |
| `rkaf:registered` | Resolves normally |
| `rkaf:deprecated` | Resolves with warning; new published packets refused unless `rkaf:deprecationOverride` attestation present |
| `rkaf:replacedBy` | Resolves to successor with `conceptMigrationWarning`; migration scheduled |
| `rkaf:mergedInto` | Resolves to successor; migration required |
| `rkaf:splitInto` | Unresolved for operational use until disambiguated by attestation or successor mapping |
| `rkaf:withdrawn` | Unresolved; operational use blocked; existing artifacts transition to `staleForCurrentUse` |
| `rkaf:localActive` | LocalConcept; resolves only within `rkaf:definedInScope` and via mappings |

### 7.2–7.4 Deprecation, Merge, Split

[Shapes unchanged from v0.1.1; see prior version for the `rkaf:replacedBy` / `rkaf:absorbedConcepts` / `rkaf:splitInto` patterns. Reproduced briefly in fixtures.]

### 7.5 ConceptLifecyclePacket

```json
{
  "@type": "rkaf:ConceptLifecyclePacket",
  "rkaf:lifecycleEvent": "rkaf:split",
  "rkaf:subjectConcept": "https://registry.example.gov/concepts/HouseholdIncomeEvidence",
  "rkaf:successorConcepts": [...],
  "rkaf:effectiveDate": "2027-01-01T00:00:00-05:00",
  "rkaf:bridgeContractVersion": "rkaf-bridge/1.0",
  "rkaf:cascadeAlgorithm": "rkaf:CascadeClosureV1",
  "rkaf:affectedAssertions": [],
  "rkaf:affectedWorkProducts": [],
  "rkaf:requiredMigrationActions": []
}
```

**`rkaf:safeAutomaticMigration` semantics (v0.1.2):**

- **Absent** (property not present) is the default: no automatic migration is declared; consumers MUST transition affected operational artifacts to `staleForCurrentUse`.
- **Present** with a declared migration type (e.g., `rkaf:replaceInPlace`, `rkaf:pinToHistoricalSuccessor`): consumers MAY auto-migrate if their `BridgeConsumerRegistration` declares support for that migration type.
- **Explicit no-safe-migration declaration:** registries MAY use `rkaf:safeAutomaticMigrationStatus: rkaf:noSafeAutomaticMigration` to declare that no auto-migration is possible (useful for split/merge events where disambiguation is intrinsically manual).

Do NOT use `null` for absent migrations. JSON-LD null semantics are ambiguous; omit the property entirely.

**Normative cascade rule:** A `ConceptLifecyclePacket` whose `lifecycleEvent` is `rkaf:deprecation`, `rkaf:withdrawal`, `rkaf:merge`, `rkaf:split`, or `rkaf:replacedBy` (without `safeAutomaticMigration: replaceInPlace`) and that affects an operational Formspec field or WOS step MUST cause the consumer to transition the affected artifact to `rkaf:staleForCurrentUse`.

## 8. Mapping disputes

Mappings are scoped assertions; disagreement is first-class. `MappingConflict` carries severity:

| Severity | Meaning | Consumer behavior |
|---|---|---|
| `rkaf:informational` | Mappings disagree but no shared operational context affected | Record; no operational impact |
| `rkaf:operationalConflict` | Shared operational artifact depends on incompatible mappings | Affected artifacts → `staleForCurrentUse` |
| `rkaf:publicationBlocking` | Scheduled publication depends on conflicting mappings | Publication MUST be blocked |
| `rkaf:authorityCritical` | Conflict involves mapping in `hasAuthority`/`derivesAuthorityFrom` chain | A3 review required; affected authority assertions → `disputed` |

## 9. Supersession and promotion

### 9.1 Supersession semantics

`rkaf:supersedesAssertion` is **many-to-one and many-to-many**:

- A single assertion MAY be superseded by multiple successor assertions (split case).
- Multiple prior assertions MAY be superseded by one successor assertion (consolidation case).
- Both can occur simultaneously (rare but valid: a reorganization of related assertions).

Consumers MUST query the supersession graph rather than assume a single successor. The Rulespec Core SHACL shape for `rkaf:supersedesAssertion` is `0..*` cardinality on both sides of the relationship.

### 9.2 LocalConcept promotion

[Unchanged from v0.1.1: registration request → `ConceptRegistrationEvent` by `ConceptMintingAuthority` → new `RegisteredConcept` published → automatic `exactMatch` mapping with `rkaf:trusted: true` (canonical) from LocalConcept → existing references resolve via mapping → consumers MAY migrate at discretion.]

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
