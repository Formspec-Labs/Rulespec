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
- `dcterms:` → `http://purl.org/dc/terms/`
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

### 2.1 Proposition-bearing relationship assertions

`rkaf:RelationshipAssertion` is the proposition-bearing specialization of
`rkaf:Assertion`. It restores the mechanically validated shape already defined
by Rulespec v0.1 while leaving the generic `rkaf:Assertion` envelope
backward-compatible during the v0.2 migration.

A `rkaf:RelationshipAssertion` MUST contain exactly one IRI-valued
`rkaf:assertsSubject`, `rkaf:assertsPredicate`, and `rkaf:assertsObject`, plus
exactly one `rkaf:assertionPolarity` from the closed set `rkaf:affirmed` or
`rkaf:denied`. Predicates remain affirmative; polarity records whether the
source-backed assertion affirms or denies that canonical relationship.

Expected and observed are roles assigned by an explicit comparison. They are
not intrinsic assertion modes. Rulespec does not store global assertion state:
approval, rejection, dispute, and revocation remain scoped and temporal
`rkaf:Attestation` records. Evidence remains a separate
`rkaf:EvidenceBinding`; confidence remains a separate
`rkaf:ConfidenceRecord`.

`rkaf:RelationshipAssertion` objects are IRIs and only IRIs. A proposition
whose object is a literal is a `rkaf:ValueAssertion` (§2.2), not a relationship
assertion with a stringified object. Formal deontic operators such as
permission, prohibition, and duty belong in domain profiles aligned with ODRL
or LegalRuleML rather than a universal ordered “force” field.

### 2.2 Value assertions [Normative]

`rkaf:ValueAssertion` is the second proposition-bearing specialization of
`rkaf:Assertion`. It carries the coordinated JSON-LD, CUE, and projector
migration that v0.2's first carrier deferred, and it supersedes that deferral.

A `rkaf:ValueAssertion` MUST contain exactly one IRI-valued
`rkaf:assertsSubject` and `rkaf:assertsPredicate`, exactly one
`rkaf:assertionPolarity` from the same closed set §2.1 defines, and exactly one
`rkaf:assertsValue`.

`rkaf:assertsValue` MUST be a JSON-LD value object: a `@value` member holding
the literal's lexical form as a string, and a `@type` member holding the
datatype IRI. Both members are REQUIRED. The datatype MUST be a member of the
closed `rkaf:ValueDatatype` set:

`xsd:string`, `xsd:token`, `xsd:boolean`, `xsd:integer`, `xsd:decimal`,
`xsd:double`, `xsd:date`, `xsd:dateTime`, `xsd:time`, `xsd:duration`,
`xsd:anyURI`.

The lexical form stays a string on the wire in every datatype, including the
numeric and boolean ones. RDF literals are lexical-form-plus-datatype;
promoting `"42"` to a JSON number would discard the distinction between
`"42"^^xsd:integer` and `"42"^^xsd:decimal` and would not round-trip.

Producers MUST NOT declare a term definition for `rkaf:assertsValue` in a
JSON-LD context that coerces its `@type`. `context/rkaf-context.jsonld`
deliberately defines the term with `@id` alone: any `@type` coercion would
collapse every ValueAssertion in the document to one datatype and silently
discard the declared one.

Consumers MUST reject a datatype outside the closed set. Every compiled target
enforces the same set from the same CUE source: the JSON Schema `@type` enum,
one SHACL `sh:datatype` alternative per member under `sh:nodeKind sh:Literal`,
the generated Rust `crate::TypedLiteral<ValueDatatype>`, and the generated
TypeScript membership check.

Language-tagged literals are NOT part of the v0.2 `rkaf:ValueAssertion`
carrier. A JSON-LD value object carrying `@language` expands to a literal with
no datatype, which no `sh:datatype` closure can constrain; admitting it would
leave SHACL and JSON Schema disagreeing about the same document. Language-
tagged meaning belongs on concepts, where `skos:prefLabel` and `skos:altLabel`
already carry it (`spec/rkaf-concept-registry.md`).

### 2.3 Proposition content and consumer state [Normative]

An assertion's proposition content is immutable and consists of exactly:
`rkaf:assertsSubject`, `rkaf:assertsPredicate`, the form-specific object slot
(`rkaf:assertsObject` or `rkaf:assertsValue`), and `rkaf:assertionPolarity`.

Proposition identity MUST NOT include mutable state. Acceptance, rejection,
dispute, qualification, revocation, consumer eligibility, confidence, and
lifecycle position are all mutable, all scoped, and all separate records or
separate envelope fields. An implementation that content-addresses an assertion
MUST address the proposition content alone; including consumer state would mint
a new assertion identity every time a consumer changed its mind, which
destroys supersession history and breaks every evidence and attestation edge
pointing at the old identifier.

The separation is structural in the source, not editorial. `constraints/core/`
`assertion.cue` declares two named definitions:

| Definition | Holds | Mutability |
| --- | --- | --- |
| `#AssertionProposition` | subject, predicate, polarity | immutable |
| `#ConsumerDisposition` | `rkaf:usageEligibility`, `rkaf:consumerLifecycleState`, `rkaf:hasAccessScope` | mutable, consumer-scoped |

`#AssertionEnvelope` composes `#ConsumerDisposition` and does NOT compose
`#AssertionProposition`: the envelope is context for a proposition, never the
proposition. `#RelationshipAssertion` and `#ValueAssertion` compose both and
supply their own object slot. The generic `rkaf:Assertion` remains an
envelope-only carrier for v0.2 backward compatibility and states no
proposition at all.

Attestation decisions never appear on an assertion. `rkaf:Attestation` targets
the assertion IRI, so a reviewer's decision changes the attestation record and
leaves the proposition byte-identical.

### 2.4 Provenance roles [Normative]

Five questions have five answers, and no record answers two of them:

| Question | Record | Edge from the assertion |
| --- | --- | --- |
| Who does the SOURCE say asserts this? | `rkaf:SourceClaimant` | `rkaf:hasSourceClaimant` |
| Which run produced this candidate? | `rkaf:ExtractionActivity` | `rkaf:hasExtractionProvenance` |
| Which model derivation produced it, as reviewed? | `rkaf:AILineage` | `rkaf:hasAILineage` (§5.3) |
| Who accepted, rejected, or revoked it? | `rkaf:Attestation` | none — the Attestation targets the assertion |
| What was it derived from? | PROV-O | `prov:wasDerivedFrom` |

**Source claimant.** `rkaf:SourceClaimant` records the party the DOCUMENT
attributes a claim to. It MUST carry exactly one `rkaf:claimsAssertion` and
exactly one `rkaf:claimantAttribution` from the closed set
`rkaf:claimantNamedInSource`, `rkaf:claimantImpliedBySource`,
`rkaf:claimantIsDocumentIssuer`, `rkaf:claimantNotStated`. When the attribution
is `rkaf:claimantNamedInSource`, `rkaf:claimantText` is REQUIRED: a record may
not assert that the source names a claimant while withholding the naming text.
`rkaf:claimantNotStated` is a complete, honest answer, not a failure.

Every value in the set is a statement about the DOCUMENT, so the set has no
value for extractor uncertainty. When the extractor cannot determine how the
source attributes a claim, it MUST omit the `rkaf:SourceClaimant` record.
`rkaf:claimantNotStated` asserts that the source made no attribution and MUST
NOT be used to record extractor uncertainty; that uncertainty belongs in a
`rkaf:ConfidenceRecord` or an `rkaf:ExtractionActivity`.

`rkaf:claimantText` (what the document says) and `rkaf:claimantIdentity` (the
resolved party, when the workspace can resolve it) are separate because a
source may name a claimant no registry knows. `rkaf:attributedInFragment`
points at the source regions carrying the attribution, which are not
necessarily the regions supporting the claim — those stay in the assertion's
own `rkaf:EvidenceBinding`.

**Extraction provenance.** `rkaf:ExtractionActivity` records the run. It MUST
carry `rkaf:extractionMethod` (closed set: `rkaf:deterministicParse`,
`rkaf:ruleBasedExtraction`, `rkaf:modelExtraction`, `rkaf:humanExtraction`,
`rkaf:importedRecord`), `rkaf:extractionRun`, `rkaf:extractedBy`,
`rkaf:extractorVersion`, and `rkaf:requestContractDigest`.

`rkaf:requestContractDigest` MUST be a lowercase `sha256:<64 hex>` digest of
the complete, secret-free request contract — instructions, schema, model
configuration, and input payload hashed together. One digest, because the
question a consumer asks is whether a candidate came from the contract they
audited, and that question has a single answer only if the whole contract is
covered. Schema descriptions and LLM hints are part of the contract; they do
not substitute for it.

When `rkaf:extractionMethod` is `rkaf:modelExtraction`,
`rkaf:extractionModelRef` is REQUIRED. A record that says a model produced a
candidate while leaving the model unnamed is not provenance.

`rkaf:ExtractionActivity` MUST NOT require a human approver, and the kernel
declares none. An unreviewed model candidate is representable exactly as it
is: an extraction happened, and no `rkaf:Attestation` targets it yet. Asking a
model to review its own answer produces another opinion, not an approval.

Provider neutrality is structural. Every `rkaf:ExtractionActivity` field is a
Rulespec-owned IRI, a version string, or an opaque digest. No provider request
object, response object, SDK type, billing record, or configuration blob
appears in the kernel or is referenced by a kernel shape.

**Model derivation lineage.** `rkaf:AILineage` (§5.3) is retained unchanged and
is NOT duplicated by `rkaf:ExtractionActivity`. It records the REVIEWED
derivation — model id, version, prompt template, temperature, seed, input
context hash, and the human approver that review implies — and remains
REQUIRED for AI-touched `rkaf:assertionOrigin` values. `rkaf:ExtractionActivity`
may link it via `rkaf:hasAILineage` when both exist; the two fields
`rkaf:extractionModelRef` and `rkaf:extractionPromptRef` are opaque references
for a run that may never be reviewed, not a second lineage record.

> **Open conflict.** `rkaf:AILineage` requires `rkaf:humanApprover`, and the
> AI-touched `rkaf:assertionOrigin` values — including `rkaf:aiSuggested`,
> which means *unreviewed candidate* — require `rkaf:hasAILineage`. Together
> these still force an approver onto an unreviewed candidate, which the target
> architecture forbids. Resolving it means making `rkaf:humanApprover`
> optional and letting the AI-touched conditional be satisfied by
> `rkaf:hasExtractionProvenance`, which flips the verdict of
> `fixtures/ailineage-missing-approver-negative.jsonld` and of
> `fixtures/negatives/a-i-lineage-missing-human-approver-negative.jsonld`.
> That is a deliberate contract change with its own migration, not a side
> effect of adding these records, and it is left to a separate change.

**Human approval.** Approval has no dedicated contract because
`rkaf:Attestation` (§3.1) already is one: it carries the attestor, the attestor
kind, the decision, the scope, the time, the optional effective period, and the
revocation marker. Minting a parallel approval record would create two places
to look for the same fact. A reviewer approving an extraction records an
`rkaf:Attestation` whose `rkaf:targets` includes the assertion IRI.

**Confidence, evidence, applicability, time, access scope.** Each remains its
own record, reached by its own edge: `rkaf:hasConfidence` (0..*, to
`rkaf:ConfidenceRecord`), `rkaf:EvidenceBinding` (which points AT the assertion
via `rkaf:bindsAssertion`, so the assertion does not change when evidence is
added), `rkaf:hasApplicability`, `rkaf:assertedAt`, and `rkaf:hasAccessScope`.
`rkaf:supersedesAssertion` appends supersession history rather than rewriting
the predecessor.

## 3. Closed-taxonomy discipline [Normative]

Every enum defined in this spec is **closed within a release**. Extending an enum requires a new release with a declared URI. Producers MUST NOT mint unregistered enum values. Consumers MUST reject unrecognized enum values from the closed sets defined below.

The closed enums introduced by v0.2 are:

- `rkaf:artifactIdentifierScheme` (§4.1); `rkaf:regulatoryIdentifierScheme` is
  no longer a kernel term — it is defined by the US rulemaking profile, see
  `spec/rkaf-rulemaking.md` §5.2
- `rkaf:selectorKind` (§4.2)
- `rkaf:noEvidenceReason` (§4.3)
- `rkaf:warrantKind` and `rkaf:warrantFamily` (§4.4)
- `rkaf:confidenceMethod` and `rkaf:calibrationStatus` (§4.5)
- `rkaf:accessScopeKind` and `rkaf:regulatoryClass` (§4.6)
- `rkaf:mappingState` (§5.1)
- `rkaf:retentionTrigger` and `rkaf:retentionPostExpiry` (§5.2)
- `rkaf:ValueDatatype` (§2.2)
- `rkaf:claimantAttribution` (§2.4)
- `rkaf:extractionMethod` (§2.4)

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

An Artifact MAY use `foaf:primaryTopic` (0..1) to name its one durable main
subject. This is the general document-to-subject seam: it applies equally to a
report about a watershed, a catalog record about a dataset, or a Unified
Agenda observation about an agenda item. The topic IRI identifies the thing
the document is chiefly about; it never becomes an Artifact identifier and
never implies that two Artifacts with the same topic are editions of one
document. Domain profiles MAY constrain the topic class more narrowly. The
experimental US rulemaking profile does so for agenda observations in
`spec/rkaf-rulemaking.md`.

US regulatory citation identity — `rkaf:hasRegulatoryIdentifier`,
`rkaf:regulatoryIdentifierScheme`, their six canonical URN grammars, the
cross-posting rule, and the permanent-URL fallbacks — is a jurisdiction
profile, not a universal primitive. It is normatively defined in
`spec/rkaf-rulemaking.md` §5.2, whose shapes compose this Artifact
definition; the kernel `#Artifact` in `constraints/core/artifact.cue` does
not declare those terms.

Artifact version and revision identity composes Dublin Core and PROV-O:

- `dcterms:isVersionOf` (0..*) links an immutable Artifact to a stable
  resource of which it is a substantive version, edition, or adaptation.
  Rulespec does not mint a universal document-work class; the referenced
  resource MAY use ELI, BIBFRAME, Schema.org, or another profile-owned public
  type.
- `prov:wasRevisionOf` (0..*) links a later Artifact to the exact earlier
  Artifact from which it derives substantial content. Every referenced
  revision MUST identify an immutable source state.
- `dcterms:hasFormat` and `dcterms:isFormatOf` remain the relations for
  substantially identical content in another format or registry posting.

Producers MUST NOT infer either version relation from a shared title, topic,
identifier fragment, embedding score, or retrieval rank. A legal profile
SHOULD use ELI's native LegalResource and LegalExpression relations when ELI
owns the resource model. Publication, effective, and observation times remain
separate profile or provenance properties; a revision link alone establishes
no legal effect.

`rkaf:Proceeding` and `rkaf:Docket` have distinct identity predicates in the
experimental rulemaking module. Neither class reuses Artifact identity.
`rkaf:uslm-section` remains a selector for substructure inside USLM markup; it
is distinct from the U.S. Code citation identity defined by the rulemaking
profile.

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
- **Relationship assertion specialization:** `rkaf:RelationshipAssertion`, `rkaf:assertionPolarity`.
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
| **W3C PROV-O** | `prov:` | Provenance vocabulary. `prov:wasGeneratedBy`, `prov:wasAttributedTo`, `prov:wasDerivedFrom`, `prov:generatedAtTime` compose with cryptographic anchoring (§7) and AI lineage records (§5.3). `prov:startedAtTime` and `prov:endedAtTime` carry activity timing on `rkaf:ExtractionActivity` (§2.4) — imported rather than re-minted, because PROV-O already names the start and end of an activity. |
| **W3C Web Annotation Ontology (OA)** | `oa:` | Rulespec v0.2 composes **OA 1.0** (W3C Recommendation 2017-02-23; namespace `http://www.w3.org/ns/oa#`, stable). Predicate-level imports: `oa:hasSource` (parent-resource edge on a SpecificResource), `oa:hasSelector` (selector attachment), `oa:exact` / `oa:prefix` / `oa:suffix` (TextQuoteSelector payload). `rkaf:SourceFragment rdfs:subClassOf oa:SpecificResource`. Foundational selector kinds (`oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`) MUST be supported by every Rulespec implementation handling source fragments. Rulespec declines L1/L3 constraints over OA predicate ranges; partner producers conform to OA's own domain/range. Breaking changes in a future OA 2.0 trigger an alignment-row re-evaluation. |
| **W3C SKOS** | `skos:` | Concept relations (`closeMatch`, `exactMatch`, `broader`, `narrower`, `related`, `mappingRelation`) for the Concept Registry (`spec/rkaf-concept-registry.md`). |
| **ELI** (European Legislation Identifier) | `eli:` | Rulespec v0.2 composes **ELI 1.5 core** (2024 release; namespace `http://data.europa.eu/eli/ontology#`, stable across v1.0 → v1.5). Use ELI URIs as the canonical Artifact identifier scheme for EU legal sources (§4.1). Do not duplicate ELI's URI structure or metadata model; compose. For multi-predecessor consolidation edges (one consolidated text incorporating multiple prior versions or amending acts), compose `eli:consolidates` (and inverse `eli:consolidated_by`) directly — both predicates are non-functional in ELI 1.5 and explicitly designed for repeated use. Consolidation is semantically distinct from supersession: `eli:consolidates` denotes editorial restatement that incorporates predecessors which remain legally extant; `rkaf:supersedesAssertion` (§6, Lifecycle primitives) denotes replacement where predecessors become historical. Use both together when appropriate. Breaking changes in a future ELI 2.0 trigger an alignment-row re-evaluation: Rulespec declines L1/L3 constraints over `eli:*` predicates by design (partners conform to ELI's own domain/range), so migration policy must be documented at the alignment layer. |
| **Dublin Core Terms** | `dcterms:` | `dcterms:hasFormat` and `dcterms:isFormatOf` are direct Artifact-to-Artifact imports for registry cross-postings. Rulespec constrains their class range but does not redefine Dublin Core format semantics; the canonical US rulemaking direction is defined in `spec/rkaf-rulemaking.md` §4.1. |
| **FOAF 0.99** | `foaf:` | `foaf:primaryTopic` is the general, functional document-to-main-subject relation on `rkaf:Artifact`. Domain profiles may constrain the topic class; sharing a topic does not merge document identity. |
| **DCAT 3** | `dcat:` | `dcat:qualifiedRelation`, `dcat:Relationship`, and `dcat:hadRole`, composed with `dcterms:relation`, provide the general qualified-relation pattern when a bare edge cannot carry role and provenance. The Experimental US rulemaking profile specializes this pattern for agenda-item-to-Proceeding assertions. Rulespec does not require a subject to be a `dcat:Dataset`. |
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
| **DCTERMS supersession predicates** (`dcterms:`) | Generic metadata + supersession | The namespace is already mode-1 for `hasFormat` / `isFormatOf`; `dcterms:replaces` / `dcterms:isReplacedBy` remain unimported because they overlap with `rkaf:supersedesAssertion` (§6). Promote those additional predicates only if a linked-data consumer requires DC-compatible supersession edges. |

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
- FOAF 0.99 — document-to-primary-topic relation.
- W3C DCAT 3 — resources, catalog records, and qualified relationships.
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
- VoID — linked-dataset description (no current carrier requirement).
- Schema.org/Legislation — public-discovery markup (Cohort D; prefix dropped from context until SEO projector ships).
- HL7 FHIR, NIEM IEPDs — projector partner formats.
- Lynx Legal Knowledge Graph (H2020), LKIF, EuroVoc/ESCO, Toulmin/AIF, Wikidata/Wikibase — reference / influence (studied but not imported).
