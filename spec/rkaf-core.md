# Rulespec Core — Vocabulary v0.2

**Status:** Pre-release, normative.
**Supersedes:** `spec/rkaf-core-v0.1.md` (historical, retained for archival reference only).
**Companion docs:** `spec/rkaf-concept-registry.md`, `spec/rkaf-vocabulary.md`.

## 0. Conformance language

Per RFC 2119 / RFC 8174 (uppercase keywords are normative). Sections marked `[Informative]` are non-normative.

## 1. Namespaces

The Rulespec vocabulary namespace is `https://rulespec.org/ns/v1#` with prefix `rkaf:`.

**Imported namespaces** (mode-1 direct predicate imports; see §9.1):
- `prov:` → `http://www.w3.org/ns/prov#`
- `oa:` → `http://www.w3.org/ns/oa#`
- `skos:` → `http://www.w3.org/2004/02/skos/core#`
- `eli:` → `http://data.europa.eu/eli/ontology#`
- `rdf:` → `http://www.w3.org/1999/02/22-rdf-syntax-ns#`
- `rdfs:` → `http://www.w3.org/2000/01/rdf-schema#`
- `xsd:` → `http://www.w3.org/2001/XMLSchema#`
- `sh:` → `http://www.w3.org/ns/shacl#` (compilation target only)

**Aligned namespaces** (mode-2/3 class-tag or URI-value composition; see §9.2):
- `aknt:` → `http://docs.oasis-open.org/legaldocml/ns/akn/3.0/`
- `uslm:` → `https://uslm.gov/2.1.0/`
- `dpv:` → `https://w3id.org/dpv#`
- `odrl:` → `http://www.w3.org/ns/odrl/2/`

## 2. Three-axis claim model [Normative]

Every Rulespec assertion is positioned on three orthogonal axes:

- **Truth axis** — what the world is. Carried by `rkaf:assertsSubject`, `rkaf:assertsPredicate`, `rkaf:assertsObject`, `rkaf:hasWarrant`, `rkaf:hasConfidence`, `rkaf:EvidenceBinding`.
- **Social axis** — who endorses, attests, disputes, supersedes. Carried by `rkaf:Attestation`, `rkaf:LocalAdoption`, `rkaf:supersedesAssertion`, `rkaf:LifecycleEvent`.
- **Consumer axis** — who may see, who may act, under what scope. Carried by `rkaf:hasAccessScope`, `rkaf:usageEligibility`, `rkaf:hasSafetyLabel`, `rkaf:hasTrustZone`, `rkaf:hasApplicability`.

Implementations MUST preserve all three axes through retrieval, projection, summarization, federation, and AI-assisted consumption.

## 3. Closed-taxonomy discipline [Normative]

Every enum defined in this spec is **closed within a release**. Extending an enum requires a new release with a declared URI. Producers MUST NOT mint unregistered enum values. Consumers MUST reject unrecognized enum values from the closed sets defined below.

The closed enums introduced by v0.2 are:

- `rkaf:artifactIdentifierScheme` and `rkaf:regulatoryIdentifierScheme` (§4.1)
- `rkaf:selectorKind` (§4.2)
- `rkaf:noEvidenceReason` (§4.3)
- `rkaf:warrantKind` and `rkaf:warrantFamily` (§4.4)
- `rkaf:confidenceMethod` and `rkaf:calibrationStatus` (§4.5)
- `rkaf:accessScopeKind` and `rkaf:regulatoryClass` (§4.6)
- `rkaf:mappingState` (§5.1)
- `rkaf:retentionTrigger` and `rkaf:retentionPostExpiry` (§5.2)

The experimental US rulemaking module adds
`rkaf:proceedingIdentifierScheme`, `rkaf:docketIdentifierScheme`, and
`rkaf:proceedingStage`; see `spec/rkaf-rulemaking.md`. Their values follow the
same release-bound closed-taxonomy discipline.

The closed enums inherited from v0.1 retain their definitions: `rkaf:assertionOrigin`, `rkaf:hasSafetyLabel`, `rkaf:hasTrustZone`, `rkaf:usageEligibility`, `rkaf:authorityKind`, `rkaf:adoptionAuthorityKind`, `rkaf:adoptionStatus`, `rkaf:result`, `rkaf:resolutionStatus`, `rkaf:resolutionMethod`, `rkaf:cacheStatus`, `rkaf:usageCeiling`, `rkaf:cascadeAlgorithm`, `rkaf:evidenceRole`, `rkaf:severity`, `rkaf:decision`, `rkaf:visibility`, `rkaf:lifecycleEvent`.

## 4. Universal primitives [Normative]

### 4.1 Artifact

**rkaf:Artifact** — an immutable, addressable unit of source material.

Required properties:
- `rkaf:hasArtifactIdentifier` (1..*) — at least one identifier for the
  immutable resource itself.
- `rkaf:artifactIdentifierScheme` (1..*) — closed enum:
  `rkaf:eli`, `rkaf:eli-dl`, `rkaf:eli-i`, `rkaf:uslm`,
  `rkaf:aknt-eId`, `rkaf:doi`, `rkaf:isbn`, `rkaf:issn`, `rkaf:cid`,
  `rkaf:hash-sha256`, `rkaf:urn-persistent`, `rkaf:partner-defined`.

An Artifact identifier MUST resolve to, or be derived from, one immutable
edition, publication, snapshot, or content payload. Examples include a
content hash, an edition-scoped GovInfo package or granule URL, a permanent
Federal Register document URL, and a producer-scoped snapshot URN. A current
eCFR URL, an unversioned U.S. Code locator, or a citation such as “40 CFR
60.1” does not establish Artifact identity.

An Artifact MAY also carry one US regulatory citation or agency identifier:

- `rkaf:hasRegulatoryIdentifier` (0..1) — canonical identifier IRI from the
  table below.
- `rkaf:regulatoryIdentifierScheme` (0..1) — corresponding value from the
  closed US regulatory-identifier enum.

These properties MUST occur together. They identify the cited legal or
administrative resource independently of the immutable Artifact edition.
They never satisfy the required `rkaf:hasArtifactIdentifier` /
`rkaf:artifactIdentifierScheme` pair.

An Artifact represents one source posting. A document published in more than
one registry — for example a Federal Register document that also appears as a
regulations.gov docket document — is represented as one Artifact per posting,
each carrying at most one regulatory-identifier pair. Producers MUST NOT merge
postings into a single Artifact to carry a second pair, and SHOULD choose the
scheme that names the cited resource most specifically (an Executive order's
Federal Register posting carries `rkaf:us-eo`, not `rkaf:us-frdoc`). The
normative cross-posting pattern, including how postings link to each other and
to Proceedings, is defined in `spec/rkaf-rulemaking.md` §4.

The US regulatory schemes use these canonical forms:

| Scheme | Identifies | Canonical form and normalization |
|---|---|---|
| `rkaf:us-cfr` | A CFR part or section | `urn:rkaf:us:cfr:<title>:<part>[.<section>]`, for example `urn:rkaf:us:cfr:40:60` or `urn:rkaf:us:cfr:40:60.1`. Title, part, and section components are decimal digits without spaces; title has no leading zero. Subparts are outside this identifier grammar. |
| `rkaf:us-usc` | A U.S. Code section | `urn:rkaf:us:usc:<title>:<section>`, for example `urn:rkaf:us:usc:42:7411`. Omit subsection parentheses. Preserve internal hyphens and normalize alphabetic suffixes to lowercase. |
| `rkaf:us-frdoc` | A Federal Register document | `urn:rkaf:us:frdoc:<document-number>`, for example `urn:rkaf:us:frdoc:2024-00366`. The document number is a four-digit year, a hyphen, and a five-digit sequence. Official source values outside this grammar use the permanent-publication fallback below. |
| `rkaf:us-regsgov` | A regulations.gov document or comment Artifact | `urn:rkaf:us:regsgov:<agency-issued-id>`, for example `urn:rkaf:us:regsgov:EPA-HQ-OAR-2021-0317-0184`. Normalize ASCII letters to uppercase and preserve the agency-issued hyphen-separated segments. Known legacy identifiers may have fewer segments; producers MUST NOT invent missing segments. Docket containers use the same lexical scheme on `rkaf:Docket`, not on `rkaf:Artifact`; see `spec/rkaf-rulemaking.md`. |
| `rkaf:us-pl` | A public law | `urn:rkaf:us:pl:<congress>-<law-number>`, for example `urn:rkaf:us:pl:117-58`. Both components are positive decimal integers without leading zeroes. |
| `rkaf:us-eo` | An Executive order | `urn:rkaf:us:eo:<order-number>`, for example `urn:rkaf:us:eo:14094`. The order number is a positive decimal integer without leading zeroes. |

These URNs supply normalized citation and agency identity where no US public
body publishes a canonical citation URI. They preserve, rather than replace,
the identifier classes owned by the CFR, U.S. Code, Federal Register,
regulations.gov, Congress, and the Executive Office. This is
composition-consistent minting under §9.4.

For an official Federal Register document number outside the
`YYYY-NNNNN` grammar, a producer MUST identify the Artifact with its permanent
`https://www.federalregister.gov/d/<source-value>` URL and
`rkaf:artifactIdentifierScheme: rkaf:urn-persistent`. It MUST NOT assert
`rkaf:regulatoryIdentifierScheme: rkaf:us-frdoc` for the unsupported lexical
form. Producers MAY retain the source value in provenance metadata. This
fallback preserves the source document without broadening the normalized
`rkaf:us-frdoc` citation space.

The same fallback discipline applies to `rkaf:us-regsgov`: an agency-issued
identifier outside the canonical grammar — including a legacy value with a
single lexical segment — keeps its permanent
`https://www.regulations.gov/document/<source-value>` URL as
`rkaf:hasArtifactIdentifier` with `rkaf:artifactIdentifierScheme:
rkaf:urn-persistent`, and the producer MUST NOT label the source value
`rkaf:us-regsgov`.

`rkaf:Proceeding` and `rkaf:Docket` have distinct identity predicates in the
experimental rulemaking module. Neither class reuses Artifact identity.
`rkaf:uslm-section` remains a selector for substructure inside USLM markup; it
is distinct from the `rkaf:us-usc` citation identity for a U.S. Code section.

### 4.2 SourceFragment

**rkaf:SourceFragment** — an addressable region within an Artifact. `rkaf:SourceFragment rdfs:subClassOf oa:SpecificResource` (W3C Web Annotation Ontology 1.0 — §9.1 Cohort A alignment).

Required properties:
- `oa:hasSource` (1) — the parent Artifact IRI. OA canonical predicate for the source resource in a SpecificResource pattern.
- `oa:hasSelector` (1..*) — at least one selector object. OA canonical predicate.
- `rkaf:selectorKind` (1..*) — closed enum declaring the selector type(s):
  - Foundational (W3C Web Annotation Ontology — `oa:`): `oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`.
  - Domain selectors: `rkaf:aknt-eId`, `rkaf:uslm-section`, `rkaf:eli-fragment`, `rkaf:jsonpath`, `rkaf:doi-fragment`, `rkaf:partner-defined`.

For `rkaf:selectorKind: "oa:TextQuoteSelector"`, the selector object MUST carry `oa:exact` (xsd:string, the verbatim quoted text). `oa:prefix` and `oa:suffix` (xsd:string, surrounding context anchors) are optional. Rulespec declines L1/L3 constraints over the OA TextQuoteSelector range beyond these three predicates; producers conform to OA 1.0's own domain/range.

Selector stability across Artifact revisions is a partner obligation. Supersession (§6.1, inherited) resolves fragment continuity. For ELI artifacts, ELI-I edges are the canonical fragment-continuity model.

### 4.3 EvidenceBinding

**rkaf:EvidenceBinding** — links an Assertion to one or more SourceFragments (or declares a permitted absence of source evidence).

Required properties:
- `rkaf:bindsAssertion` (1) — the assertion being bound.
- One of:
  - `rkaf:bindsSourceFragment` (1..*) — at least one SourceFragment, OR
  - `rkaf:noEvidenceReason` (1) — closed enum: `rkaf:axiomatic`, `rkaf:inferred-from-warrant-class`, `rkaf:consensus-without-citation`, `rkaf:permitted-by-safety-label`. The Assertion's `rkaf:hasSafetyLabel` MUST permit the chosen reason.

Optional properties:
- `rkaf:warrantKind` (0..1) — overrides the Assertion's warrant kind for this binding.
- `rkaf:hasAccessScope` (0..1) — narrows the binding's visibility.

An assertion lacking either an EvidenceBinding-with-fragment OR an explicit `noEvidenceReason` permitted by its safety level is **not operationally valid**. Layer 2 enforces this.

### 4.4 Warrant

**rkaf:Warrant** — the universal grounding primitive. `rkaf:Authority` (Core v0.1) is preserved as the legal/regulatory-family specialization (`rkaf:Authority rdfs:subClassOf rkaf:Warrant`).

Universal predicate: `rkaf:hasWarrant`.
Specialization predicate: `rkaf:hasAuthority` (legal/regulatory family).

Closed taxonomy `rkaf:warrantKind` grouped by family:

- **Legal family:** `rkaf:legal`, `rkaf:statutory`, `rkaf:regulatory`, `rkaf:delegated`, `rkaf:organizational`, `rkaf:contractual`, `rkaf:localOperational`, `rkaf:publication`.
- **Scientific family:** `rkaf:methodological`, `rkaf:empirical`, `rkaf:replication`, `rkaf:peerReview`.
- **Editorial family:** `rkaf:editorial`, `rkaf:factCheck`, `rkaf:correction`.
- **Cryptographic family:** `rkaf:cryptographic`, `rkaf:commitment`.
- **Social family:** `rkaf:consensus`, `rkaf:expertOpinion`, `rkaf:communityEndorsement`.
- **Source-class family:** `rkaf:sourceReliability`, `rkaf:provenanceClass`.

`rkaf:warrantFamily` is the closed enum: `rkaf:legal`, `rkaf:scientific`, `rkaf:editorial`, `rkaf:cryptographic`, `rkaf:social`, `rkaf:source-class`.

A warrant chain is hop-local: each hop carries its own `rkaf:warrantKind`, and chains MAY transition between families. Cross-family transitions MUST be surfaced for human review by any consumer traversing them (Layer 2 enforces this surfacing as a warning, not an error).

`rkaf:defeasible` (`xsd:boolean`, 0..1) is preserved for LegalRuleML interop.

Future-projection alignments per §9.2.2: legal-family warrants have affinity with **LegalRuleML** (mode-4 pattern citation; `rkaf:defeasible` is the current interop point); reporting-requirement warrants have affinity with **RRMV**; scientific-family warrants have affinity with **ECO** / **SEPIO**. These promote to §9.2 when a partner consumer arrives with a named use case.

### 4.5 ConfidenceRecord

**rkaf:ConfidenceRecord** — first-class structured confidence over an assertion.

Required properties:
- `rkaf:confidenceMethod` (1) — closed enum: `rkaf:model-inference`, `rkaf:human-estimation`, `rkaf:review-consensus`, `rkaf:source-class-inheritance`, `rkaf:rule-based`.
- `rkaf:score` (1) — `xsd:float` in `[0.0, 1.0]` **OR** `rkaf:scoreCategorical` from closed enum `{rkaf:very-low, rkaf:low, rkaf:medium, rkaf:high, rkaf:very-high}`.
- `rkaf:calibrationStatus` (1) — closed enum: `rkaf:uncalibrated`, `rkaf:calibratedAgainst`, `rkaf:humanEstimated`, `rkaf:consensus`. If `rkaf:calibratedAgainst`, `rkaf:evaluatedAgainst` (1) MUST point to the calibration corpus.
- `rkaf:confidenceBasis` (1..*) — what evidence the confidence is grounded in (Assertions, SourceFragments, fixtures, datasets).
- `rkaf:generatedBy` (1) — actor: model identity (with version + prompt template ref), human identity, or community process identifier.

A `ConfidenceRecord` lacking `confidenceMethod`, `confidenceBasis`, or `calibrationStatus` is "score theater" and is non-conformant. Layer 2 rejects these.

Multiple `ConfidenceRecord` instances on the same assertion are explicitly permitted and represent independently-measured confidences (uncalibrated model + calibrated model + human + review consensus + source reliability MAY coexist). Consumers MUST distinguish them by `rkaf:confidenceMethod`.

### 4.6 AccessScope

**rkaf:AccessScope** — visibility boundary attachable to Assertions, Attestations, EvidenceBindings, and SourceFragments.

Required property:
- `rkaf:accessScopeKind` (1) — closed enum: `rkaf:public`, `rkaf:partnerVisible`, `rkaf:organizationVisible`, `rkaf:roleRestricted`, `rkaf:personalRestricted`, `rkaf:regulatoryRestricted`, `rkaf:embargoUntil`.

Conditional properties:
- If `rkaf:regulatoryRestricted`, `rkaf:regulatoryClass` (1..*) from closed enum `{rkaf:HIPAA-PHI, rkaf:GDPR-PII, rkaf:FERPA, rkaf:CJIS, rkaf:classified, rkaf:legally-privileged, rkaf:partner-defined}`.
- If `rkaf:embargoUntil`, `rkaf:embargoUntil` (`xsd:dateTime`) MUST be present.
- If `rkaf:roleRestricted`, `rkaf:permittedRole` (1..*) IRIs.

Consumers MUST preserve `AccessScope` through retrieval, projection, summarization, federation, and AI-assisted consumption. A consumer that exposes content beyond its declared `AccessScope` is non-conformant. Layer 6 conformance includes adversarial fixtures designed to surface `AccessScope` leakage.

For `accessScopeKind = regulatoryRestricted` cases, AccessScope SHOULD compose `dpv:hasPersonalDataCategory` naming the specific personal-data category (e.g. `dpv:Health` for HIPAA-PHI cases, appropriate `dpv:*` personal-data subclasses for GDPR-PII cases) and SHOULD compose `dpv:hasLegalBasis` where applicable (e.g. a GDPR Art. 6 IRI). `dpv:hasPurpose` MAY additionally be composed to name the processing purpose. These predicates are cross-namespace annotations only; L1 and L3 impose no range constraints over `dpv:*` predicates — partner producers conform to DPV's own taxonomy (DPV 2.3, namespace `https://w3id.org/dpv#`).

Aligned with **W3C ODRL** (rights expression — overlay-attached, not inline) and **W3C DPV** (privacy classification — composed directly for `regulatoryRestricted` cases via the three predicates above; see §9.2). Partners requiring full rights expression attach ODRL overlays via the Layer 4 projector pattern.

## 5. Studio-derived promotions [Normative]

### 5.1 rkaf:MappingState

Closed enum (four values): `rkaf:mapsToWos`, `rkaf:authoringOnly`, `rkaf:requiresSpecExtension`, `rkaf:unmappedButApproved`.

Property: `rkaf:mappingState`. Domain: any mapping-bearing object. (Studio profile uses this on mapping outputs; universal Vocabulary exposes the enum so non-Studio partners may attach it to their own mapping primitives.)

### 5.2 rkaf:RetentionPolicy

First-class typed shape. Required properties:
- `rkaf:retentionDurationDays` (1, `xsd:int`, non-negative).
- `rkaf:retentionTrigger` (1) — closed enum: `rkaf:creation`, `rkaf:lastAccess`, `rkaf:lastModification`, `rkaf:lifecycleEvent`.
- `rkaf:retentionPostExpiry` (1) — closed enum: `rkaf:delete`, `rkaf:anonymize`, `rkaf:archive`, `rkaf:legal-hold-on-trigger`.

Attached to Artifacts, Assertions, Attestations, or EvidenceBindings via `rkaf:hasRetentionPolicy`.

### 5.3 rkaf:AILineage

Required properties:
- `rkaf:modelId` (1, `xsd:string`).
- `rkaf:modelVersion` (1, `xsd:string`).
- `rkaf:promptTemplateRef` (1, IRI).
- `rkaf:temperature` (1, `xsd:float`).
- `rkaf:seed` (0..1, `xsd:integer`).
- `rkaf:inputContextHash` (1, `xsd:string`).
- `rkaf:humanApprover` (1, IRI) — the actor who approved the AI output for the assertion's `assertionOrigin` value.
- `rkaf:humanRationale` (0..1, `xsd:string`; REQUIRED if `assertionOrigin = rkaf:aiPromoted` or `rkaf:humanQualified`).

An assertion with `rkaf:assertionOrigin ∈ {rkaf:aiSuggested, rkaf:aiPromoted, rkaf:humanQualified, rkaf:humanRevalidation}` MUST carry an `rkaf:hasAILineage` reference. Layer 2 enforces this.

### 5.4 rkaf:llmHint

Annotation property. Attaches LLM-extraction hints to other vocabulary terms.

Sub-properties:
- `rkaf:llmHint:critical` (`xsd:boolean`)
- `rkaf:llmHint:intent` (`xsd:string`)
- `rkaf:llmHint:exampleValue` (literal)

Carried into JSON Schema projector output as `x-rkaf-llmHint` annotations on schema nodes (Layer 4 projector contract).

### 5.5 rkaf:Workspace

A scoping container for partner-local URN issuance and registry partitioning.

Properties:
- `rkaf:workspaceId` (1, `xsd:string`) — the local identifier within the workspace's URN scheme.
- `rkaf:workspaceTrustList` (1..*, IRIs) — IRIs of peer workspaces this workspace declares trust for (Layer 3 federation reference).

URN scheme: `urn:rkaf:workspace:<workspaceId>/<localId>` resolves within the workspace; federable across mutually trusting workspaces.

### 5.6 rkaf:projectsTo

Property. Declares the target schema fragment a Rulespec overlay projects to. Domain: any Rulespec graph node. Range: IRI of a target schema artifact (JSON Schema `$defs` reference, OpenAPI component reference, etc.).

Generalizes Studio's `wosTarget` projection pattern.

## 6. Inherited Core v0.1 primitives [Normative]

Inherited name-for-name from `spec/rkaf-core-v0.1.md`:

- **Assertion model:** `rkaf:Assertion`, `rkaf:assertsSubject`, `rkaf:assertsPredicate`, `rkaf:assertsObject`, `rkaf:hasApplicability`, `rkaf:effectivePeriod`.
- **Attestation / adoption:** `rkaf:Attestation`, `rkaf:LocalAdoption`, `rkaf:adoptionAuthorityKind`, `rkaf:adoptionStatus`.
- **Justification:** `rkaf:Justification`, `rkaf:hasJustification`, `rkaf:justifiedByAssertion`, `rkaf:GeneratedWorkProduct`.
- **Authority (now specialization of Warrant):** `rkaf:Authority`, `rkaf:hasAuthority`, `rkaf:derivesAuthorityFrom`, `rkaf:DelegationInstrument`.
- **Lifecycle:** `rkaf:LifecycleEvent`, `rkaf:supersedesAssertion`, `rkaf:lifecycleEvent` enum, amendment / rescission / supersession / material-revision packets, `rkaf:RevalidationEvent`, `rkaf:PointInTimeException`.
- **Usage / trust / safety:** `rkaf:usageEligibility` lattice, `rkaf:hasTrustZone` (Z0–Z8), `rkaf:hasSafetyLabel` (D0/S1/R2/A3/P4).
- **Concepts:** `rkaf:Concept`, `rkaf:RegisteredConcept`, `rkaf:LocalConcept`, `rkaf:ConceptRegistry`, `rkaf:ConceptMapping`, `rkaf:ConceptResolutionResult`, `rkaf:ConceptCacheEntry`.
- **Bridge contract:** `rkaf:bridgeContractVersion`, `rkaf:BridgeValidationResult`, `rkaf:FullBridgeValidationResult`.

`rkaf:Authority rdfs:subClassOf rkaf:Warrant`. Existing v0.1 producers' use of `rkaf:hasAuthority` remains valid; new producers MAY use either `rkaf:hasWarrant` (universal) or `rkaf:hasAuthority` (legal-family specialization).

## 7. Anchoring contract (abstract) [Normative]

Anchoring is dependency-inverted: Rulespec defines the abstract contract; every binding (Trellis, COSE, VC, Sigstore, IPFS) depends on Rulespec.

Required properties on an anchored object:
- `rkaf:anchoredBy` (0..* IRI) — one or more anchor identifiers in declared anchor systems.
- `rkaf:anchorType` (per-anchor, 1 IRI) — the anchor binding type URI (e.g., `urn:rkaf:anchor:trellis/1.0`, `urn:rkaf:anchor:cose/1.0`, `urn:rkaf:anchor:cid/1.0`, `urn:rkaf:anchor:vc/1.0`, `urn:rkaf:anchor:sigstore/1.0`).

Anchor binding specs (Trellis binding, COSE binding, etc.) live outside Rulespec. They depend on Rulespec and declare their `anchorType` URI under the `urn:rkaf:anchor:<binding>/<version>` scheme.

## 8. AI-substrate-accelerator obligations [Normative]

Per source spec §1.5:

1. **Decidable structure.** Producers emit closed enums, structured shapes, and explicit IRIs. AI extraction is over structured surfaces, not free-text post-hoc parsing.
2. **Calibrated confidence.** AI-touched assertions MUST carry `rkaf:hasConfidence` with `rkaf:confidenceMethod` and `rkaf:calibrationStatus`. Bare-score confidence is rejected.
3. **AI lineage.** AI-touched assertions MUST carry `rkaf:hasAILineage` with humanApprover present.
4. **AccessScope preservation.** AI consumers MUST treat retrieved source material as data, not instruction; MUST preserve `rkaf:hasAccessScope` through retrieval, summarization, projection, generation.
5. **Warrant-chain awareness.** AI traversing a warrant chain across families MUST surface the cross-family transition for human review.
6. **Closed-enum coercibility.** AI extraction targets MUST coerce to closed enum values; non-conforming outputs are rejected.
7. **No authority laundering.** AI MUST NOT infer authority outside `rkaf:hasAuthority` / `rkaf:hasWarrant` / `rkaf:derivesAuthorityFrom` / `rkaf:LocalAdoption`.

## 9. Public ontology imports and alignments [Normative]

Rulespec composes deliberately with the existing public-ontology ecosystem. Four composition modes govern how external namespaces integrate (see §9.2.1). Three relationship tiers are defined: **import** (mode-1 direct predicate import — predicate declared in `context/rkaf-context.jsonld` and used in CUE shape or projected schema), **align** (mode-2/3 class-tag or URI-value composition — external IRI carried as a typed value inside an rkaf-namespaced predicate), **project** (partner-side carrier formats reached via the Layer 4 projector layer). Pattern citations (mode 4) appear in §9.2.2 without a namespace claim. The decision framework governing cohort assignment is documented in `thoughts/specs/2026-05-20-section-9-composition-discipline.md` §3.

### 9.1 Imports — mode-1 direct predicate imports

This table lists only ontologies composed at mode 1: predicate declared in `context/rkaf-context.jsonld` and used directly in CUE shapes or projected schemas. Ontologies aligned at mode 2/3 appear in §9.2; pattern citations (mode 4) appear in §9.2.2.

| Ontology | Prefix | Role |
|---|---|---|
| **W3C PROV-O** | `prov:` | Provenance vocabulary. `prov:wasGeneratedBy`, `prov:wasAttributedTo`, `prov:wasDerivedFrom`, `prov:generatedAtTime` compose with cryptographic anchoring (§7) and AI lineage records (§5.3). |
| **W3C Web Annotation Ontology (OA)** | `oa:` | Rulespec v0.2 composes **OA 1.0** (W3C Recommendation 2017-02-23; namespace `http://www.w3.org/ns/oa#`, stable). Predicate-level imports: `oa:hasSource` (parent-resource edge on a SpecificResource), `oa:hasSelector` (selector attachment), `oa:exact` / `oa:prefix` / `oa:suffix` (TextQuoteSelector payload). `rkaf:SourceFragment rdfs:subClassOf oa:SpecificResource`. Foundational selector kinds (`oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`) MUST be supported by every Rulespec implementation handling source fragments. Rulespec declines L1/L3 constraints over OA predicate ranges; partner producers conform to OA's own domain/range. Breaking changes in a future OA 2.0 trigger an alignment-row re-evaluation. |
| **W3C SKOS** | `skos:` | Concept relations (`closeMatch`, `exactMatch`, `broader`, `narrower`, `related`, `mappingRelation`) for the Concept Registry (`spec/rkaf-concept-registry.md`). |
| **ELI** (European Legislation Identifier) | `eli:` | Rulespec v0.2 composes **ELI 1.5 core** (2024 release; namespace `http://data.europa.eu/eli/ontology#`, stable across v1.0 → v1.5). Use ELI URIs as the canonical Artifact identifier scheme for EU legal sources (§4.1). Do not duplicate ELI's URI structure or metadata model; compose. For multi-predecessor consolidation edges (one consolidated text incorporating multiple prior versions or amending acts), compose `eli:consolidates` (and inverse `eli:consolidated_by`) directly — both predicates are non-functional in ELI 1.5 and explicitly designed for repeated use. Consolidation is semantically distinct from supersession: `eli:consolidates` denotes editorial restatement that incorporates predecessors which remain legally extant; `rkaf:supersedesAssertion` (§6, Lifecycle primitives) denotes replacement where predecessors become historical. Use both together when appropriate. Breaking changes in a future ELI 2.0 trigger an alignment-row re-evaluation: Rulespec declines L1/L3 constraints over `eli:*` predicates by design (partners conform to ELI's own domain/range), so migration policy must be documented at the alignment layer. |
| **ELI-DL** | (sub-namespace) | Compose ELI-DL identifiers + metadata for assertions over draft/pending legislation. Lifecycle packets carry ELI-DL state transitions natively. |
| **ELI-I** (Legal Impacts) | (sub-namespace) | Canonical model for fragment-continuity resolution under amendment in EU legal sources. Rulespec implementations targeting EU legal sources SHOULD compose ELI-I edges into supersession traversal (§4.2). |
| **JSON-LD 1.1** | (carrier) | Primary serialization. Layer 4 projector target. |
| **SHACL** | `sh:` | One Layer 2 compilation target (demoted from authoritative; see Appendix C of source spec). |
| **RDF / RDFS / XSD** | `rdf:` / `rdfs:` / `xsd:` | Base graph model and typed literals. |

### 9.2 Alignments — mode-2/3 class-tag and URI-value composition

| Ontology | Domain | Alignment posture |
|---|---|---|
| **Akoma Ntoso / LegalDocML** | Legal-document XML structure | Composed as rkaf-namespaced selector kind (`rkaf:aknt-eId`) and identifier scheme. External prefix `aknt:` declared for forward compatibility; no `aknt:*` predicate is currently used directly. Use Akoma Ntoso `eId` paths as a SourceFragment selector kind for legislative source-document substructure (§4.2). |
| **USLM** (United States Legislative Markup) | US legislative XML structure | Composed as rkaf-namespaced selector kind (`rkaf:uslm-section`) and identifier scheme. External prefix `uslm:` declared for forward compatibility; no `uslm:*` predicate is currently used directly. Use USLM section identifiers as a SourceFragment selector kind for US legal sources (§4.2). |
| **W3C ODRL** | Rights/permission expression | ODRL alignment is composed at the overlay-projector layer (mode 2/3), not as predicate-level imports. Partners requiring full rights expression attach ODRL overlays via the Layer 4 projector contract. `rkaf:accessScopeKind` remains the operative predicate; ODRL maps over it at the projector boundary. |
| **W3C DPV** | Privacy semantics | Rulespec v0.2 composes **DPV 2.3** (W3C Community Group Final Report 2026-02-25; namespace `https://w3id.org/dpv#`, stable). Predicate-level imports on `rkaf:AccessScope`: `dpv:hasPersonalDataCategory` (IRI set, naming the specific personal-data category — e.g. `dpv:Health` for HIPAA-PHI cases), `dpv:hasLegalBasis` (single IRI — e.g. a GDPR Art. 6 IRI), `dpv:hasPurpose` (single IRI, optional). All three are optional cross-namespace annotations; L1 and L3 impose no range constraints over `dpv:*` predicates — partner producers conform to DPV's own taxonomy. For `accessScopeKind = regulatoryRestricted` cases, SHOULD compose at minimum `dpv:hasPersonalDataCategory` (see §4.6). Breaking changes in a future DPV version trigger an alignment-row re-evaluation: Rulespec declines L1/L3 constraints over `dpv:*` predicates by design (partners conform to DPV's own domain/range), so migration policy must be documented at the alignment layer. |

#### 9.2.1 Modes of composition

The four composition modes classify how each alignment row integrates with the Rulespec corpus. Each mode carries different debt characteristics; the decision framework for cohort assignment is in `thoughts/specs/2026-05-20-section-9-composition-discipline.md` §2–§3.

| Mode | Name | Description | Debt level | Examples |
|------|------|-------------|------------|---------|
| **1** | Direct predicate import | Predicate declared in `context/rkaf-context.jsonld`; used in CUE shape or projected schema. Highest commitment — context declaration is a release-boundary constraint. | Highest | `prov:wasGeneratedBy`, `eli:consolidates`, `oa:TextQuoteSelector` |
| **2** | Class-tag composition | External IRI used as `@type` value or as a typed-string enum value inside an rkaf-namespaced predicate. No direct predicate import required. | Moderate | `oa:TextQuoteSelector` as `rkaf:selectorKind` value; `skos:exactMatch` as `rkaf:mappingPredicate` |
| **3** | URI-value composition | External URI carried inside an rkaf-namespaced predicate, gated by a scheme enum. External structure is data, not graph shape. | Moderate | ELI URIs in `rkaf:hasArtifactIdentifier` where `rkaf:artifactIdentifierScheme: "rkaf:eli"` |
| **4** | Pattern citation | Architectural prior art with no predicate or URI flow. No namespace declaration required. Preserves design rationale without accruing context debt. | Lowest | Nanopublications (overlay-shape pattern); LegalRuleML (defeasibility-preservation discipline) |

#### 9.2.2 See also — partner ontologies for future projection

The following ontologies have real theoretical value for Rulespec's positioning but no current consumer demand sufficient to validate a specific binding shape. Composing now would lock in an untested binding. Listed here to preserve option value at zero current debt. **Promote each row to §9.2 (Alignments) when a partner consumer arrives with a named use case.**

| Ontology | Domain | Rationale for deferral |
|---|---|---|
| **OASIS LegalRuleML** (`lrml:`) | Formal legal norms (defeasibility, deontic) | Pattern citation only (mode 4). `rkaf:defeasible` boolean already captures the interop point; full `lrml:` predicate import deferred until a partner produces LegalRuleML output requiring a concrete binding. |
| **RRMV** (Reporting Requirement Metadata Vocabulary) (`rrmv:`) | Reporting requirements in legal provisions | Theoretical alignment with warrant chains for reporting-requirement assertions is sound; no named partner demand to validate binding shape. Promote when a reporting-obligation producer arrives. |
| **ECO** (Evidence & Conclusion Ontology) / **SEPIO** (`eco:` / `sepio:`) | Scientific evidence types | Scientific-warrant family (`methodological` / `empirical` / `replication` / `peerReview`) has structural affinity with ECO/SEPIO; no current consumer requiring the cross-namespace annotation. |
| **CiTO** (Citation Typing Ontology) (`cito:`) | Scholarly citation typing | `cito:supports`, `cito:disagreesWith`, `cito:extends` align with EvidenceBinding semantics; no current corpus requiring the citation-typing cross-reference. |
| **DCTERMS** (Dublin Core) (`dcterms:`) | Generic metadata + supersession | `dcterms:replaces` / `dcterms:isReplacedBy` overlap with `rkaf:supersedesAssertion` (§6); no current consumer requiring the DCTERMS supersession cross-namespace predicate. Promote if a linked-data consumer requires DC-compatible supersession edges. |

### 9.3 Projections — partner-side carrier formats reached via Layer 4

| Ontology / Format | Partner audience | Projector status |
|---|---|---|
| **JSON Schema** | Programmer-facing tooling, IDE, AI tool-use APIs | MVP (Layer 4 §8.2) |
| **JSON-LD** | Linked-data partners | MVP (Layer 4 §8.2) |
| **OpenAPI 3.1** | API-surface partners | MVP (Layer 4 §8.2) |
| **HL7 FHIR** | Healthcare-domain partners | Available when partner needs |
| **NIEM IEPDs** | US government data exchange | Available when partner needs |
| **Schema.org/Legislation** | Public discovery / SEO | Available when partner needs |
| GraphQL SDL, Protobuf, Avro, Iceberg, Cedar/Rego | Various | Available when partner needs |

### 9.4 Discipline

The composition discipline is: **do not reinvent**. If a public ontology owns the local problem (ELI for EU legal-resource identity, USLM for US legal source structure, OA for selectors, SKOS for concept relations, PROV-O for provenance), Rulespec uses it. Rulespec's Vocabulary expresses what is genuinely missing — the universal warrant model, the federation contract, the consumer-overlay pattern, the depth gradient, the cross-domain conformance suite. Everything else composes. See `thoughts/specs/2026-05-20-section-9-composition-discipline.md` for the four-cohort decision framework governing future composition decisions.

## 10. Validation contract [Normative]

Every term defined in §§4-6 MUST be exercised by:
- At least one positive fixture in `fixtures/`.
- At least one negative fixture in `fixtures/` whose violation surfaces a SHACL constraint failure on the v0.2 shape set.
- (For terms reached by the JSON Schema projector — Layer 4 plan) at least one round-trip parity fixture demonstrating Attach + Extract on a representative payload.

Fixture-coverage enforcement is automated by `tools/vocab_audit.py`.

The CUE files under `constraints/core/` are the source of truth for structural,
lexical, date, and ordered-field constraints. JSON Schema, Rust, TypeScript,
and SHACL under `compiled/` are deterministic projector outputs from
`tools/compile_all.sh`. Legacy hand-authored SHACL remains only for Pattern-C
invariants not yet expressible by the compiler; it MUST NOT redefine a
CUE-expressible constraint. SHACL `sh:if` / `sh:then` Pattern B is forbidden;
compiled conditionals use Pattern C (`sh:or` with `sh:not`).

## 11. Compatibility and migration [Normative]

None. Rulespec v0.2 supersedes v0.1.x wholesale. v0.1.x JSON-LD payloads with `pkaf:` prefix and `https://w3id.org/pkaf/ns/v1#` IRIs are not parseable by v0.2 tooling.

There is no migration shim. There is no compatibility re-export. There is no `pkaf:`-aliased context. Producers of pre-v0.2 artifacts re-emit them under v0.2 vocabulary, or freeze them at v0.1.

This is greenfield. v0.1.x served as the editorial baseline; v0.2 is the contract.

## 12. References

### Normative

- RFC 2119 / RFC 8174 — conformance keywords.
- W3C JSON-LD 1.1 — serialization.
- W3C SHACL — Pattern C conditional shape pattern (see Appendix C of source spec).
- W3C Web Annotation Ontology — `oa:` selector vocabulary.
- W3C PROV-O — provenance.
- W3C SKOS — concept relations.
- ELI / ELI-DL / ELI-I — EU legal-resource identifiers.
- USLM — US legislative markup.
- Akoma Ntoso / LegalDocML — legal-document XML structure.
- W3C ODRL — rights expression.
- W3C DPV — privacy semantics.

### Informative

- Source spec: `thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md`.
- Companion: `spec/rkaf-concept-registry.md`.
- Full term reference: `spec/rkaf-vocabulary.md`.
- Framework memo: `thoughts/specs/2026-05-20-section-9-composition-discipline.md` — user-value × architectural-debt decision framework for §9 composition decisions.
- DCTERMS — supersession metadata (Cohort C; demoted from Normative per §9.2.2).
- OASIS LegalRuleML — formal legal norms (Cohort C; demoted per §9.2.2; `rkaf:defeasible` is the current interop point).
- ECO / SEPIO — scientific evidence types (Cohort C; demoted per §9.2.2).
- RRMV — reporting requirement metadata (Cohort C per §9.2.2).
- CiTO — citation typing (Cohort C per §9.2.2).
- Nanopublications — overlay shape pattern citation (Cohort D — pattern reference only; no namespace claim per §9.2.2).
- DCAT / VoID — dataset catalog metadata (Cohort D; prefix dropped from context until Reference Corpora layer ships).
- Schema.org/Legislation — public-discovery markup (Cohort D; prefix dropped from context until SEO projector ships).
- HL7 FHIR, NIEM IEPDs — projector partner formats.
- Lynx Legal Knowledge Graph (H2020), LKIF, EuroVoc/ESCO, Toulmin/AIF, Wikidata/Wikibase — reference / influence (studied but not imported).
