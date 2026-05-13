# PKAF Core v0.1

Status: Editor's Draft, normative consolidation
Companion to: ConceptRegistry v0.1.2, Shapes Batch 1 + 1.1, conformance fixtures (Local Operational v0.2, Mapping v0.1, Statutory Authority v0.1, Registry Failure and Conflict v0.1)
Bridge contract: `pkaf-bridge/1.0`

## 0. Editorial note

This document consolidates normative content that has accumulated across fixtures and review cycles. It is deliberately concise — not the W3C-style essay PKAF began as. New definitions are added only where a fixture would fail validation without them; everything else stays in fixtures, ConceptRegistry, or shape documents.

Sections marked **N** are new normative content (consolidated from review comments and fixture observations). Sections marked **R** are restatements of decisions previously made.

## 1. Assertion model

### 1.1 (R) Assertions are units; state is computed

Every PKAF claim is a `pkaf:RelationshipAssertion` with subject, predicate, object, evidence, trust zone, safety label, usage eligibility, applicability context, and assertion origin. **`assertionState` is NOT a stored property.** Effective review/adoption state is computed per scope from attestations and adoptions over the assertion. Implementations MAY cache an effective state per scope but MUST recompute on attestation/adoption events.

### 1.2 (R) AssertionOrigin (closed enum, v0.1)

`pkaf:humanAsserted`, `pkaf:aiSuggested`, `pkaf:aiPromoted`, `pkaf:humanQualified`, `pkaf:humanRevalidation`, `pkaf:reviewClassified`, `pkaf:importedFromSource`, `pkaf:systemDerived`. Extensions via declared URIs in v0.2; not in v0.1.

### 1.3 (R) Trust zones and safety labels

Trust zones Z0–Z8 and safety labels D0/S1/R2/A3/P4 retain the definitions from the original PKAF draft Sections 7.1 and 7.2. Trust zone is structural (what kind of object); safety label is operational (what the consumer may do with it).

### 1.4 (R) Usage eligibility is a lattice

```
notEligible < searchOnly < reviewQueueOnly < draftGenerationAllowed
            < localOperationalUse < publicationAllowed < officialUse
```

Effective `usageEligibility` for an artifact is computed by a **reducer**, not a simple minimum. The reducer combines: assertion baseline, scoped LocalAdoption grants, lifecycle status (can lower or block), applicability constraints, consumer capabilities. Consumers MAY narrow but MUST NOT broaden. `LocalAdoption` MAY broaden within its declared scope; this is the only authorized broadening.

### 1.5 (R) Supersession is many-to-many

`pkaf:supersedesAssertion` is `0..*` on both sides. A single assertion MAY be superseded by multiple successors (split); multiple priors MAY be superseded by one successor (consolidation). Consumers MUST query the graph; assuming a single successor is incorrect.

## 2. Authority model

### 2.1 (N) Authority predicates

| Predicate | Subject | Object | Authority establishment |
|---|---|---|---|
| `pkaf:hasAuthority` | Policy / Section / Requirement / FormField / WorkflowStep / GeneratedWorkProduct | LegalResource / Regulation / Statute / OfficialPolicy / DelegationInstrument | Establishes that the object grants legal basis for the subject |
| `pkaf:derivesAuthorityFrom` | LegalResource / Regulation / OfficialPolicy / DelegationInstrument | LegalResource / Regulation / Statute / DelegationInstrument | Records one hop in an authority chain |
| `pkaf:implements` | Policy / Workflow / Form / FormField / WorkflowStep | LegalResource / OfficialPolicy / NormativeStatement | Records substantive realization, NOT authority. MUST be paired with `hasAuthority` for operational use. |

### 2.2 (N) authorityKind is hop-local

`pkaf:authorityKind` describes the kind of authority conveyed by a single hop, not a global label on a chain. A chain `requirement → regulation → delegation → statute` carries `regulatory → delegated → statutory` across hops. `BridgeValidationResult.chainTerminusKind` records the kind at chain end.

Enumerated values: `pkaf:legal`, `pkaf:statutory`, `pkaf:regulatory`, `pkaf:delegated`, `pkaf:organizational`, `pkaf:contractual`, `pkaf:localOperational`, `pkaf:publication`.

### 2.3 (N) DelegationInstrument as first-class type

`pkaf:DelegationInstrument` is a typed subclass of `pkaf:PolicyResourceVersion`. Required properties beyond the base `PolicyResourceVersion`:

- `pkaf:delegatingAuthority` — IRI of the delegating actor
- `pkaf:delegatedTo` — IRI of the delegate
- `pkaf:delegationScope` — string or IRI declaring the scope of delegated authority
- `pkaf:effectivePeriodStart`, optional `pkaf:effectivePeriodEnd`

Delegation instruments are common in real authority chains and benefit from a recognizable type; consumers SHOULD treat `DelegationInstrument` objects specially in chain traversal (e.g., display the delegating authority and delegated scope explicitly).

### 2.4 (N) AuthorityChainHop as first-class type

`pkaf:AuthorityChainHop` records one edge of a traversal. Required properties: `pkaf:assertion`, `pkaf:predicate` (limited to `hasAuthority` or `derivesAuthorityFrom`), `pkaf:subject`, `pkaf:object`, `pkaf:authorityKind`. Optional: `pkaf:status` from `{hopValid, hopBroken, hopRescindedObject, hopSupersededObject, hopOutOfJurisdiction, hopOutOfEffectivePeriod}`.

`pkaf:implements` is reserved for `JustificationChainHop` (later batch); it does NOT appear in authority chains.

### 2.5 (N) LocalAdoption is not legal authority — invariant

**A `LocalAdoption` MAY authorize local operational use of an assertion within a declared scope. It MUST NOT substitute for a broken, expired, rescinded, or missing `hasAuthority` / `derivesAuthorityFrom` chain when the adopted assertion requires external legal, regulatory, or delegated authority.**

This is enforced structurally via the shape constraint that `LocalAdoption.adoptionAuthorityKind` is restricted to `organizational`, `localOperational`, `contractual`, or `publication` (NEVER `statutory`/`regulatory`/`delegated`/`legal`), and behaviorally via the cascade closure that includes `LocalAdoption.targetAssertion` inverse edges so adoptions of broken-authority assertions are surfaced as `LocalAdoptionOrphanedWarning` in `BridgeValidationResult`.

## 3. Attestation and adoption

### 3.1 (R) Attestations are scoped, multi-target

An `Attestation` may target an assertion, work product, packet, concept, mapping conflict, registry, or bridge validation result (at least one). Attestor types include human user, AI model, AI agent, automated parser, team, organization, community, formal reviewer, and `ConceptMintingAuthority`.

Decisions and scopes accept the closed v0.1 enums OR declared extension URIs (see PKAF Decision/Scope Extension Registries — pointer registries documented at the PKAF organizational level, not in core).

### 3.2 (R) LocalAdoption shape requirements

Required: `pkaf:organization`, `pkaf:targetAssertion`, `pkaf:adoptionStatus`, `pkaf:usageEligibility`, `pkaf:adoptionAuthorityKind` (restricted per §2.5), `pkaf:adoptionScope` (string or IRI), `pkaf:authorizedBy`, `prov:generatedAtTime`. Optional: `pkaf:adoptsApplicability`, `pkaf:basedOnAttestation`.

### 3.3 (R) Effective state is per-scope

An assertion can simultaneously be AI-suggested, community-endorsed, locally adopted by Org A, and rejected by Org B. These are not contradictory; they are scoped facts. Consumers compute effective state for their scope via a reducer over attestations and adoptions.

## 4. Lifecycle model

### 4.1 (R) Version classification gate

Every artifact revision MUST be classified before any lifecycle predicate emits. The classification (`pkaf:RevisionClassification`) decides between `pkaf:editorialRevisionOf` (D0, no cascade) and `pkaf:materiallyRevises` (A3, cascade required). Without classification, no cascade fires. This prevents typo-edit cascade storms.

### 4.2 (R) Lifecycle predicates target ResourceVersions, not Artifacts

`pkaf:amends`, `pkaf:supersedes`, `pkaf:rescinds` MUST target `pkaf:PolicyResourceVersion` (or specialization such as `DelegationInstrument`), NOT raw `pkaf:Artifact` instances. Artifact-level differences live on `RevisionClassification`. PolicyResourceVersion wraps Artifacts via `pkaf:realizedByArtifact`.

### 4.3 (R) CascadeClosureV1

The normative cascade closure algorithm is transitive closure over the **inverse** of these edges, scoped to active/adopted state at packet `effectiveDate`:

- `pkaf:derivedFromFragment`
- `pkaf:justifiedByAssertion`
- `pkaf:hasAuthority`
- `pkaf:derivesAuthorityFrom`
- `pkaf:implements`
- `pkaf:requiresEvidenceType`
- `pkaf:collectsEvidenceType`
- `pkaf:operationallyDependsOn`
- `pkaf:supersedesAssertion`
- `pkaf:supersedesWorkProduct`
- **`pkaf:LocalAdoption.targetAssertion`** (N — added per statutory fixture truth-table)
- (For `ConceptLifecyclePacket`) `pkaf:collectsEvidenceType`, `pkaf:requiresEvidenceType`, `pkaf:assertsObject` (where object is a concept), and SKOS mapping edges (`exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`, `relatedMatch`)

The closure output is the set of affected assertions, authority assertions, work products, and adoptions. Lifecycle packets MUST emit this set; the algorithm name `pkaf:CascadeClosureV1` is the conformance identifier.

### 4.4 (R) Lifecycle packet types

`pkaf:AmendmentPacket`, `pkaf:SupersessionPacket`, `pkaf:RescissionPacket`, `pkaf:MaterialRevisionPacket`, `pkaf:ConceptLifecyclePacket`. All MUST include `pkaf:cascadeAlgorithm`, `pkaf:effectiveDate`, `pkaf:bridgeContractVersion`, computed affected sets, and `pkaf:requiredRevalidationActions[]`.

### 4.5 (R) Stale transition

When a consumer receives a lifecycle packet affecting an operational artifact, the artifact transitions to `pkaf:staleForCurrentUse` unless the packet declares a `pkaf:safeAutomaticMigration` the consumer supports. Stale artifacts MUST NOT be used for new operational cases.

### 4.6 (R) PointInTimeException

A lifecycle packet MAY include `pkaf:pointInTimeExceptions[]`, each declaring an `pkaf:evaluationAnchor` (from the EvaluationAnchor vocabulary), a scope description, and `pkaf:retainsAssertion` / `pkaf:retainsWorkProduct`. Consumers honor the exception only if they support the referenced anchor; otherwise they MUST refuse the packet rather than ignore the anchor.

### 4.7 (R) EvaluationAnchor vocabulary

`pkaf:applicationSubmissionTime`, `pkaf:eventOccurrenceTime`, `pkaf:eligibilityDeterminationTime`, `pkaf:noticeGenerationTime`, `pkaf:workflowStartTime`, `pkaf:workflowStepStartTime`, `pkaf:currentTime`, `pkaf:effectivePeriodStart`, `pkaf:publicationTime`. Extensions via declared URIs.

### 4.8 (R) RevalidationEvent and RevalidationClosureEvent

`pkaf:RevalidationEvent` is emitted on cascade ingest and remains open until a `pkaf:RevalidationClosureEvent` references it with a `pkaf:closureDecision` and successor assertion / work product. Closure events are explicit; prose `closesWhen` rules are NOT permitted in v0.1.

## 5. Bridge model

### 5.1 (R) BridgeConsumerRegistration

Every bridge consumer publishes a registration declaring: `pkaf:consumer`, `pkaf:bridgeContractVersion`, `pkaf:supportedEvaluationAnchors`, `pkaf:supportsRegistryVersionRange[]`, `pkaf:supportedAutomaticMigrations[]`, `pkaf:supportedAuthorityKinds[]`. Registration is published once and referenced by validation results.

### 5.2 (R) BridgeValidationResult is the control plane

Every packet ingestion produces a `pkaf:BridgeValidationResult` with: `pkaf:packetId`, `pkaf:consumer`, `pkaf:bridgeContractVersion`, `pkaf:result` (`accepted` | `acceptedWithWarnings` | `rejected`), `pkaf:effectiveUsageEligibility`, `pkaf:effectiveUsageEligibilityRationale`, `pkaf:conceptResolutionResults[]`, `pkaf:warnings[]`, `pkaf:errors[]`, `pkaf:staleDependencies[]`, `pkaf:registryUnavailable[]`, `pkaf:registryVersionOutOfRange[]`, optionally `pkaf:authorityChainTraversal[]`, `pkaf:chainTerminus`, `pkaf:chainTerminusKind`, `pkaf:authorityChainStatus`. Rejected results MUST include `pkaf:suggestedRemediation` OR `pkaf:noRemediationReason`.

### 5.3 (R) authorityChainStatus on BridgeValidationResult

When the result reflects authority-chain validation: `pkaf:authorityChainStatus` is one of `valid`, `broken`, `staleForCurrentUse`, `validForPointInTimeOnly`, `brokenForNewCases`, `missingAuthority`, `unsupportedAuthorityKind`.

### 5.4 (R) Bridge contract rules (consolidated, normative)

Ten rules govern consumer behavior. Restated here for normative reference; full text in Pass 3 bridge contract derivation.

1. No PKAF-backed authority inference outside of `hasAuthority` / `derivesAuthorityFrom` / `LocalAdoption`.
2. `usageEligibility` is computed via the reducer (§1.4); consumers MAY narrow, MUST NOT broaden.
3. `authorityKind` preserved and surfaced; consumers MUST NOT substitute one kind for another.
4. Declared `EvaluationAnchor` support; refuse unsupported anchors with structured errors.
5. Cascade-driven `staleForCurrentUse` transition; no operational use outside valid `PointInTimeException` until `RevalidationClosureEvent`.
6. Concept resolution rules per ConceptRegistry (resolved concepts ≠ authority).
7. Justification chains MUST terminate at `hasAuthority` / `derivesAuthorityFrom` (A3) or `LocalAdoption` (localOperational or stronger).
8. Bridge-emitted attestations for consumer-detected issues.
9. `pkaf:bridgeContractVersion` declared; unsupported versions refused with structured errors.
10. Generated artifacts preserve PKAF justification metadata.

## 6. Generated work products

### 6.1 (R) GeneratedWorkProduct typing is overlay

`pkaf:GeneratedWorkProduct` is an overlay type on existing consumer types (`formspec:Field`, `wos:WorkflowStep`, others). Preexisting artifacts not created by PKAF tooling MAY carry `pkaf:justifiedByAssertion` without being typed as `GeneratedWorkProduct`. Only PKAF-generated artifacts receive the GeneratedWorkProduct type.

### 6.2 (R) consumerLifecycleState

Generated work products MAY carry `pkaf:consumerLifecycleState` (e.g., `draft`, `proposedForOperational`, `operational`, `staleForCurrentUse`, `published`). This is a **denormalized consumer-side cache**, not authoritative. Authoritative state derives from the reducer (§1.4) and lifecycle events.

### 6.3 (R) proposedUsageEligibility

Generated work products in pre-promotion states MAY declare `pkaf:proposedUsageEligibility` to ask the bridge "would this be allowed at this ceiling?" `pkaf:usageEligibility` is current effective; `pkaf:proposedUsageEligibility` is requested target. Bridge validation evaluates the proposal.

## 7. Concept resolution interaction

### 7.1 (R) Concept resolution is semantic compatibility, not authority

Per ConceptRegistry v0.1.2 §1.1. Concept resolution establishes that two evidence-type references refer to the same evidence concept. It does NOT establish that the artifact has legal/regulatory/local authority to require or collect that evidence. Authority and concept resolution are orthogonal validations; both must pass independently for operational use.

### 7.2 (R) ConceptRegistry dependency

PKAF Core depends on ConceptRegistry v0.1.2 for all `collectsEvidenceType` / `requiresEvidenceType` resolution behavior. Consumers MUST implement both PKAF Core conformance AND ConceptRegistry-Core (at minimum) to be PKAF-conformant.

## 8. Extension governance

### 8.1 (N) Extension registries (lightweight)

Several enums permit extension via declared URIs:

- `pkaf:DecisionExtensionRegistry` — declares attestation decision URIs beyond the v0.1 closed set
- `pkaf:ScopeExtensionRegistry` — declares attestation scope URIs beyond the v0.1 closed set
- `pkaf:EvaluationAnchorExtensionRegistry` — declares evaluation anchor URIs
- `pkaf:SafeAutomaticMigrationRegistry` — declares migration type URIs

Each registry is a JSON-LD document published at a stable URI listing sanctioned extension URIs. Consumers MAY accept extension URIs from any registry they trust; they MUST NOT accept arbitrary URIs not declared in any trusted registry.

### 8.2 (N) Closed in v0.1, open in v0.2

Where extensions are permitted, the v0.1 closed enums remain authoritative for v0.1 conformance. Extension acceptance is implementation-specific. v0.2 will standardize registry discovery and trust declaration.

## 9. Conformance profiles

### 9.1 PKAF Core conformance

Implementations claiming PKAF Core v0.1 conformance MUST validate:

- All structural shapes in Shapes Batch 1 + 1.1
- ConceptRegistry-Core (per ConceptRegistry v0.1.2 §10)
- The four conformance fixtures with zero shape violations
- The ten bridge contract rules (§5.4)
- The LocalAdoption-is-not-authority invariant (§2.5)
- The cascade closure algorithm `CascadeClosureV1` (§4.3) including LocalAdoption inverse edges

### 9.2 Higher conformance profiles (future)

- PKAF-Authority: PKAF Core + ConceptRegistry-Lifecycle + full authority-chain validation including DelegationInstrument
- PKAF-Federated: above + ConceptRegistry-Federated + cross-org assertion sync
- PKAF-Publication: above + publication state machine + canonical mapping resolution

These are documented in profile-specific specs, not core.

## 10. What v0.1 deliberately omits

Per editorial discipline, v0.1 omits:

- A complete predicate registry for all PKAF predicates (only the load-bearing ones — authority, lifecycle, evidence, mapping — are normatively defined)
- A complete vocabulary for warnings and errors (each fixture introduces specific warning/error subtypes; consolidation deferred to v0.2)
- A SHACL-Core compatibility profile (v0.1 requires SHACL Advanced Features)
- Cross-org SaaS synchronization semantics (assertion packet exchange between PKAF instances)
- A search profile (the PKAF-Search profile from the original draft remains future work)
- A studio profile (PKAF-Studio remains future work; bridge contract substitutes for the studio-level concerns in v0.1)

These are explicit non-goals for v0.1, not oversights.

## 11. Open questions for v0.2

Carried forward from various reviews; not actionable in v0.1:

1. Scope split: `scopeKind` + `scopeResource` instead of single `scope` URI
2. Extension registry discovery: how does a consumer discover trusted registries?
3. SaaS↔local sync semantics: signed packet exchange, replay protection, trust boundaries
4. PROV-O alignment shapes: full validation of `prov:wasGeneratedBy`, `prov:wasAttributedTo`, `prov:wasDerivedFrom` chains
5. Federated mapping conflict resolution: multilateral canonical-mapping coordination
6. Concept-side post-promotion lifecycle (LocalConcept marked `promoted`?)
7. Privacy and access control on attestation visibility scopes
8. A `JustificationChainHop` shape that allows `implements` in chains
9. ConceptUse as first-class object
10. EU AI Act and other regulatory mapping profiles

## Bibliography

- Original PKAF draft (May 2026)
- ConceptRegistry v0.1.2
- Conformance Fixture v0.2 (Local Operational)
- Mapping Fixture v0.1
- Statutory Authority Fixture v0.1
- Registry Failure and Conflict Fixture v0.1
- Shapes Batch 1 + 1.1
- PKAF Bridge Contract Pass 3 (December 2025 review cycle)

## Document status

This consolidation supersedes scattered normative content in fixture review comments and is the authoritative reference for shape drafting from Batch 2 forward. Future fixtures and shape batches reference this document by section number rather than restating definitions.
