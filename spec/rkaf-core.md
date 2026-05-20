# Rulespec Core — Vocabulary v0.2

**Status:** Pre-release, normative.
**Supersedes:** `spec/rkaf-core-v0.1.md` (historical, retained for archival reference only).
**Companion docs:** `spec/rkaf-concept-registry.md`, `spec/rkaf-vocabulary.md`.

## 0. Conformance language

Per RFC 2119 / RFC 8174 (uppercase keywords are normative). Sections marked `[Informative]` are non-normative.

## 1. Namespaces

The Rulespec vocabulary namespace is `https://rulespec.org/ns/v1#` with prefix `rkaf:`.

**Imported namespaces** (direct dependencies; see §9):
- `prov:` → `http://www.w3.org/ns/prov#`
- `oa:` → `http://www.w3.org/ns/oa#`
- `skos:` → `http://www.w3.org/2004/02/skos/core#`
- `dcterms:` → `http://purl.org/dc/terms/`
- `cito:` → `http://purl.org/spar/cito/`
- `dcat:` → `http://www.w3.org/ns/dcat#`
- `rdf:` → `http://www.w3.org/1999/02/22-rdf-syntax-ns#`
- `rdfs:` → `http://www.w3.org/2000/01/rdf-schema#`
- `xsd:` → `http://www.w3.org/2001/XMLSchema#`
- `sh:` → `http://www.w3.org/ns/shacl#` (compilation target only)

**Aligned namespaces** (predicate-name and pattern compatibility; see §9):
- `eli:` → `http://data.europa.eu/eli/ontology#`
- `aknt:` → `http://docs.oasis-open.org/legaldocml/ns/akn/3.0/`
- `uslm:` → `https://uslm.gov/2.1.0/`
- `lrml:` → `http://docs.oasis-open.org/legalruleml/ns/v1.0/`
- `rrmv:` → `http://data.europa.eu/m8g/rrmv/`
- `eco:` → `http://purl.obolibrary.org/obo/ECO_`
- `sepio:` → `http://purl.obolibrary.org/obo/SEPIO_`
- `dpv:` → `https://w3id.org/dpv#`
- `odrl:` → `http://www.w3.org/ns/odrl/2/`
- `nano:` → `http://www.nanopub.org/nschema#`
- `schemaorg:` → `https://schema.org/`

## 2. Three-axis claim model [Normative]

Every Rulespec assertion is positioned on three orthogonal axes:

- **Truth axis** — what the world is. Carried by `rkaf:assertsSubject`, `rkaf:assertsPredicate`, `rkaf:assertsObject`, `rkaf:hasWarrant`, `rkaf:hasConfidence`, `rkaf:EvidenceBinding`.
- **Social axis** — who endorses, attests, disputes, supersedes. Carried by `rkaf:Attestation`, `rkaf:LocalAdoption`, `rkaf:supersedesAssertion`, `rkaf:LifecycleEvent`.
- **Consumer axis** — who may see, who may act, under what scope. Carried by `rkaf:hasAccessScope`, `rkaf:usageEligibility`, `rkaf:hasSafetyLabel`, `rkaf:hasTrustZone`, `rkaf:hasApplicability`.

Implementations MUST preserve all three axes through retrieval, projection, summarization, federation, and AI-assisted consumption.

## 3. Closed-taxonomy discipline [Normative]

Every enum defined in this spec is **closed within a release**. Extending an enum requires a new release with a declared URI. Producers MUST NOT mint unregistered enum values. Consumers MUST reject unrecognized enum values from the closed sets defined below.

The closed enums introduced by v0.2 are:

- `rkaf:artifactIdentifierScheme` (§4.1)
- `rkaf:selectorKind` (§4.2)
- `rkaf:noEvidenceReason` (§4.3)
- `rkaf:warrantKind` and `rkaf:warrantFamily` (§4.4)
- `rkaf:confidenceMethod` and `rkaf:calibrationStatus` (§4.5)
- `rkaf:accessScopeKind` and `rkaf:regulatoryClass` (§4.6)
- `rkaf:mappingState` (§5.1)
- `rkaf:retentionTrigger` and `rkaf:retentionPostExpiry` (§5.2)

The closed enums inherited from v0.1 retain their definitions: `rkaf:assertionOrigin`, `rkaf:hasSafetyLabel`, `rkaf:hasTrustZone`, `rkaf:usageEligibility`, `rkaf:authorityKind`, `rkaf:adoptionAuthorityKind`, `rkaf:adoptionStatus`, `rkaf:result`, `rkaf:resolutionStatus`, `rkaf:resolutionMethod`, `rkaf:cacheStatus`, `rkaf:usageCeiling`, `rkaf:cascadeAlgorithm`, `rkaf:evidenceRole`, `rkaf:severity`, `rkaf:decision`, `rkaf:visibility`, `rkaf:lifecycleEvent`.

## 4. Universal primitives [Normative]

### 4.1 Artifact

**rkaf:Artifact** — an immutable, addressable unit of source material.

Required properties:
- `rkaf:hasArtifactIdentifier` (1..*) — at least one content-addressable or persistent-URI identifier. MUST conform to one of the schemes enumerated by `rkaf:artifactIdentifierScheme`.
- `rkaf:artifactIdentifierScheme` (1..*) — closed enum: `rkaf:eli`, `rkaf:eli-dl`, `rkaf:eli-i`, `rkaf:uslm`, `rkaf:aknt-eId`, `rkaf:doi`, `rkaf:isbn`, `rkaf:issn`, `rkaf:cid`, `rkaf:hash-sha256`, `rkaf:urn-persistent`, `rkaf:partner-defined`.

Citing an Artifact by mutable URL alone is non-conformant. Layer 2 enforces this.

### 4.2 SourceFragment

**rkaf:SourceFragment** — an addressable region within an Artifact.

Required properties:
- `rkaf:bindsArtifact` (1) — the parent Artifact identifier.
- `rkaf:hasSelector` (1..*) — at least one selector.
- `rkaf:selectorKind` (1..*) — closed enum:
  - Foundational (W3C Web Annotation Ontology — `oa:`): `oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`.
  - Domain selectors: `rkaf:aknt-eId`, `rkaf:uslm-section`, `rkaf:eli-fragment`, `rkaf:jsonpath`, `rkaf:doi-fragment`, `rkaf:partner-defined`.

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

Alignments per §9: legal-family warrants align with **LegalRuleML**; reporting-requirement warrants align with **RRMV**; scientific-family warrants align with **ECO** / **SEPIO**.

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

Aligned with **W3C ODRL** (rights expression — overlay-attached, not inline) and **W3C DPV** (privacy classification — overlay-attached for `regulatoryRestricted` cases). Partners requiring full rights expression or full privacy classification attach ODRL / DPV overlays via the Layer 4 projector pattern.

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

Rulespec composes deliberately with the existing public-ontology ecosystem. Three relationship modes are defined: **import** (code-level dependency in the JSON-LD context and SHACL shapes), **align** (predicate-name and pattern compatibility), **project** (partner-side carrier formats reached via the Layer 4 projector layer).

### 9.1 Imports — direct dependencies

| Ontology | Prefix | Role |
|---|---|---|
| **W3C PROV-O** | `prov:` | Provenance vocabulary. `prov:wasDerivedFrom` chains compose with cryptographic anchoring (§7) and AI lineage records (§5.3). |
| **W3C Web Annotation Ontology (OA)** | `oa:` | Selector vocabulary for `SourceFragment` (§4.2). Foundational selector kinds (`oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`) MUST be supported by every Rulespec implementation handling source fragments. |
| **W3C SKOS** | `skos:` | Concept relations (`closeMatch`, `exactMatch`, `broader`, `narrower`, `related`, `mappingRelation`) for the Concept Registry (`spec/rkaf-concept-registry.md`). |
| **DCTERMS** (Dublin Core) | `dcterms:` | Generic metadata + supersession (`dcterms:replaces` / `dcterms:isReplacedBy`). |
| **CiTO** (Citation Typing Ontology) | `cito:` | Scholarly citation typing (`cito:supports`, `cito:disagreesWith`, `cito:extends`). |
| **DCAT** | `dcat:` | Reference Corpora layer metadata. |
| **JSON-LD 1.1** | (carrier) | Primary serialization. Layer 4 projector target. |
| **SHACL** | `sh:` | One Layer 2 compilation target (demoted from authoritative; see Appendix C of source spec). |
| **RDF / RDFS / XSD** | `rdf:` / `rdfs:` / `xsd:` | Base graph model and typed literals. |

### 9.2 Alignments — predicate-name and pattern compatibility

| Ontology | Domain | Alignment posture |
|---|---|---|
| **ELI** (European Legislation Identifier) | EU legal-resource identifiers + metadata | Rulespec v0.2 composes **ELI 1.5 core** (2024 release; namespace `http://data.europa.eu/eli/ontology#`, stable across v1.0 → v1.5). Use ELI URIs as the canonical Artifact identifier scheme for EU legal sources (§4.1). Do not duplicate ELI's URI structure or metadata model; compose. For multi-predecessor consolidation edges (one consolidated text incorporating multiple prior versions or amending acts), compose `eli:consolidates` (and inverse `eli:consolidated_by`) directly — both predicates are non-functional in ELI 1.5 and explicitly designed for repeated use. Consolidation is semantically distinct from supersession: `eli:consolidates` denotes editorial restatement that incorporates predecessors which remain legally extant; `rkaf:supersedesAssertion` (§6, Lifecycle primitives) denotes replacement where predecessors become historical. Use both together when appropriate. Breaking changes in a future ELI 2.0 trigger an alignment-row re-evaluation: Rulespec declines L1/L3 constraints over `eli:*` predicates by design (partners conform to ELI's own domain/range), so migration policy must be documented at the alignment layer. |
| **ELI-DL** | Draft legislation | Compose ELI-DL identifiers + metadata for assertions over draft/pending legislation. Lifecycle packets carry ELI-DL state transitions natively. |
| **ELI-I** (Legal Impacts) | Legislative impacts and amendments | Canonical model for fragment-continuity resolution under amendment in EU legal sources. Rulespec implementations targeting EU legal sources SHOULD compose ELI-I edges into supersession traversal (§4.2). |
| **RRMV** (Reporting Requirement Metadata Vocabulary) | Reporting requirements in legal provisions | Align warrant chains for reporting-requirement assertions with RRMV's vocabulary (§4.4). RRMV's "who reports what / due dates / change tracking / requirement-to-artifact association" use cases map directly onto Rulespec assertions over reporting obligations. |
| **Akoma Ntoso / LegalDocML** | Legal-document XML structure | Use Akoma Ntoso `eId` paths as a SourceFragment selector kind for legislative source-document substructure (§4.2). |
| **USLM** (United States Legislative Markup) | US legislative XML structure | Use USLM section identifiers as a SourceFragment selector kind for US legal sources (§4.2). |
| **OASIS LegalRuleML** | Formal legal norms (defeasibility, deontic) | Align legal-family warrants (§4.4); preserve `rkaf:defeasible` boolean for interop. Partners producing formal legal rules emit LegalRuleML and link via `rkaf:hasWarrant`. |
| **ECO** (Evidence & Conclusion Ontology) / **SEPIO** | Scientific evidence types | Align the scientific-warrant family (`methodological` / `empirical` / `replication` / `peerReview`) with ECO's evidence-type vocabulary (§4.4). |
| **Nanopublications** | Portable assertion + provenance + publication-info graphs | Align the overlay-attachment pattern with the nanopublication shape: assertion graph + provenance graph + publication-info graph. A Rulespec overlay is structurally a generalized nanopublication carrying domain-specific warrant chains. |
| **W3C ODRL** | Rights/permission expression | Align `AccessScope` (§4.6) predicate names with ODRL where they overlap; partners requiring full rights expression attach ODRL overlays via the projector. |
| **W3C DPV** | Privacy semantics | Align `AccessScope` `regulatoryRestricted` cases (§4.6) with DPV's privacy / personal-data / legal-basis vocabulary; partners requiring full privacy classification attach DPV overlays. |
| **Schema.org / Schema.org/Legislation** | Public web markup | Align an export projection for SEO-grade public publication of assertions and source artifacts. Public-discovery layer only; not the operating model. |
| **DCAT / VoID** | Dataset catalog / linked-data discovery | Align the Reference Corpora layer for dataset publication. Rulespec corpora SHOULD ship with DCAT-compatible metadata. |

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

The composition discipline is: **do not reinvent**. If a public ontology owns the local problem (ELI for EU legal-resource identity, USLM for US legal source structure, RRMV for reporting requirements, ECO for scientific evidence, OA for selectors), Rulespec uses it. Rulespec's Vocabulary expresses what is genuinely missing — the universal warrant model, the federation contract, the consumer-overlay pattern, the depth gradient, the cross-domain conformance suite. Everything else composes.

## 10. Validation contract [Normative]

Every term defined in §§4-6 MUST be exercised by:
- At least one positive fixture in `fixtures/`.
- At least one negative fixture in `fixtures/` whose violation surfaces a SHACL constraint failure on the v0.2 shape set.
- (For terms reached by the JSON Schema projector — Layer 4 plan) at least one round-trip parity fixture demonstrating Attach + Extract on a representative payload.

Fixture-coverage enforcement is automated by `tools/vocab_audit.py`.

The v0.2 SHACL shape set `shapes/rkaf-shapes-core.ttl` is one **compilation target** of the constraint source-of-truth language defined in Layer 2 (Plan 3). When the Layer 2 constraint DSL lands, the SHACL shapes in this directory become projector outputs and not the source of truth (per source spec §6.1 and Appendix C — SHACL `sh:if` / `sh:then` Pattern B is forbidden; Pattern C — `sh:or` with `sh:not` — is the only conditional pattern permitted in compiled output).

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
- DCTERMS — supersession metadata.
- ELI / ELI-DL / ELI-I — EU legal-resource identifiers.
- USLM — US legislative markup.
- Akoma Ntoso / LegalDocML — legal-document XML structure.
- OASIS LegalRuleML — formal legal norms.
- ECO / SEPIO — scientific evidence types.
- W3C ODRL — rights expression.
- W3C DPV — privacy semantics.

### Informative

- Source spec: `thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md`.
- Companion: `spec/rkaf-concept-registry.md`.
- Full term reference: `spec/rkaf-vocabulary.md`.
- RRMV — reporting requirement metadata.
- CiTO — citation typing.
- Nanopublications — overlay shape pattern.
- DCAT / VoID — dataset catalog metadata.
- Schema.org/Legislation — public-discovery markup.
- HL7 FHIR, NIEM IEPDs — projector partner formats.
- Lynx Legal Knowledge Graph (H2020), LKIF, EuroVoc/ESCO, Toulmin/AIF, Wikidata/Wikibase — reference / influence (studied but not imported).
