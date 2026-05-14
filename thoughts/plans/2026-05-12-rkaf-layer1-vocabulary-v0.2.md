# Layer 1 — Vocabulary v0.2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Rulespec Vocabulary v0.2: a normative `spec/rkaf-core-v0.2.md` whose terms (a) promote Studio-derived primitives per Appendix A, (b) elevate Warrant / Artifact / SourceFragment / EvidenceBinding / AccessScope / ConfidenceRecord to first-class status per §§5.5-5.8, and (c) wire the §5.9 ontology imports and alignments into the JSON-LD context, the SHACL shapes (compiled target), and the spec text — without reinventing what existing public ontologies already cover.

**Architecture:** Vocabulary v0.2 supersedes v0.1.x wholesale. The v0.1 spec/context/shapes remain in the tree as historical artifacts but are no longer normative; v0.2 is the version any v0.2-compliant tool resolves. The new context imports `oa:`, `prov:`, `skos:`, `dcterms:`, `cito:`, `eli:`, `aknt:` (Akoma Ntoso), `uslm:`, `eco:`, `sepio:`, `dpv:`, `odrl:`, `lrml:` (LegalRuleML), `rrmv:`, `nano:` (Nanopublications), `dcat:`, `rdf:`, `rdfs:`, `xsd:` as namespaces. Closed-taxonomy enums are emitted as JSON-LD `@vocab`-bound IRIs. Each new term ships with at least one fixture exercising it (per §5.2).

**Tech Stack:** JSON-LD 1.1 context, SHACL Turtle, Markdown spec body, pyshacl for validator parity, rdflib for graph diffing.

---

## File structure

After the repo extract+rename plan, work happens inside `rulespec/` (submodule of formspec-stack). All paths in this plan are absolute under `/Users/mikewolfd/Work/formspec-stack/rulespec/`.

```
rulespec/
├── spec/
│   ├── rkaf-core-v0.1.md                 # historical; not edited
│   ├── rkaf-concept-registry-v0.1.2.md   # historical; not edited
│   ├── rkaf-core-v0.2.md                 # NEW — normative core (this plan)
│   ├── rkaf-concept-registry-v0.2.md     # NEW — normative concept registry (Task 9)
│   └── rkaf-vocabulary-v0.2.md           # NEW — full term reference (Task 4)
├── context/
│   ├── rkaf-context-v0.1.jsonld          # historical
│   ├── rkaf-context-v0.2.jsonld          # REPLACED in this plan with the v0.2 context
│   └── rkaf-context-v0.2.original.bak    # NOT created — git history is the backup
├── shapes/
│   ├── rkaf-shapes-core-v0.1.ttl         # historical
│   ├── rkaf-shapes-core-v0.2.ttl         # NEW — compiled SHACL target for v0.2 vocab
│   ├── rkaf-shapes-warrant-v0.2.ttl      # NEW — Warrant / Artifact / SourceFragment / EvidenceBinding shapes
│   ├── rkaf-shapes-confidence-v0.2.ttl   # NEW — ConfidenceRecord shape
│   ├── rkaf-shapes-accessscope-v0.2.ttl  # NEW — AccessScope shape
│   └── rkaf-shapes-conceptregistry-v0.2.ttl  # NEW — concept registry shapes (subsumes v0.1.2)
├── fixtures/
│   ├── v0.2/                             # NEW — every v0.2 term has fixtures here
│   │   ├── warrant-legal-positive.jsonld
│   │   ├── warrant-legal-negative.jsonld
│   │   ├── warrant-scientific-positive.jsonld
│   │   ├── warrant-cross-family-transition-positive.jsonld
│   │   ├── artifact-eli-positive.jsonld
│   │   ├── artifact-doi-positive.jsonld
│   │   ├── artifact-cid-positive.jsonld
│   │   ├── sourcefragment-oa-textquote-positive.jsonld
│   │   ├── sourcefragment-oa-xpath-positive.jsonld
│   │   ├── sourcefragment-aknt-eid-positive.jsonld
│   │   ├── sourcefragment-uslm-section-positive.jsonld
│   │   ├── evidencebinding-positive.jsonld
│   │   ├── evidencebinding-no-evidence-reason-positive.jsonld
│   │   ├── evidencebinding-missing-negative.jsonld
│   │   ├── confidencerecord-uncalibrated-positive.jsonld
│   │   ├── confidencerecord-calibrated-positive.jsonld
│   │   ├── confidencerecord-score-theater-negative.jsonld
│   │   ├── accessscope-public-positive.jsonld
│   │   ├── accessscope-organizationVisible-positive.jsonld
│   │   ├── accessscope-leak-negative.jsonld
│   │   ├── ailineage-positive.jsonld
│   │   ├── ailineage-missing-approver-negative.jsonld
│   │   ├── retentionpolicy-positive.jsonld
│   │   ├── mappingstate-positive.jsonld
│   │   └── workspace-positive.jsonld
│   └── (v0.1 fixtures retained for v0.1 conformance)
└── tools/
    ├── ci_validate.py                    # extended with --mode v02
    └── vocab_audit.py                    # NEW — fails build if a v0.2 term has zero fixtures (Task 13)
```

---

## Task 1: Draft `spec/rkaf-core-v0.2.md` skeleton (sections + frontmatter)

**Files:**
- Create: `/Users/mikewolfd/Work/formspec-stack/rulespec/spec/rkaf-core-v0.2.md`

- [x] **Step 1: Write the spec skeleton**

Create the file with frontmatter and the section headings the v0.2 vocabulary spec MUST carry. Body content lands in subsequent tasks; this is the contract surface.

```markdown
# Rulespec Core — Vocabulary v0.2

**Status:** Pre-release, normative.
**Supersedes:** `spec/rkaf-core-v0.1.md` (historical, retained for archival reference only).
**Companion docs:** `spec/rkaf-concept-registry-v0.2.md`, `spec/rkaf-vocabulary-v0.2.md`.

## 0. Conformance language
Per RFC 2119 / RFC 8174 (uppercase keywords are normative).

## 1. Namespaces
The Rulespec vocabulary namespace is `https://rulespec.org/ns/v1#` with prefix `rkaf:`.
Imported namespaces: `prov:`, `oa:`, `skos:`, `dcterms:`, `cito:`, `dcat:`, `rdf:`, `rdfs:`, `xsd:`.
Aligned namespaces (referenced by alignment table in §9): `eli:`, `aknt:`, `uslm:`, `lrml:`, `rrmv:`, `eco:`, `sepio:`, `dpv:`, `odrl:`, `nano:`, `schemaorg:`.

## 2. Three-axis claim model
(per source spec §1.6 — Truth axis, Social axis, Consumer axis)

## 3. Closed-taxonomy discipline
(per source spec §5.3 — every enum is closed within a release)

## 4. Universal primitives
Per source spec §5.5-§5.8:
- Artifact (§4.1)
- SourceFragment (§4.2)
- EvidenceBinding (§4.3)
- Warrant (§4.4) with hasWarrant predicate and warrantKind closed taxonomy
- ConfidenceRecord (§4.5)
- AccessScope (§4.6)

## 5. Studio-derived promotions
Per source spec Appendix A:
- rkaf:MappingState — closed enum
- rkaf:RetentionPolicy
- rkaf:AILineage
- rkaf:llmHint annotation property
- rkaf:Workspace
- rkaf:projectsTo

## 6. Inherited Core v0.1 primitives (retained, semantics preserved)
- Assertion, Attestation, LocalAdoption, Justification
- Authority (now specialization of Warrant)
- ApplicabilityScope, EffectivePeriod
- LifecycleEvent, Supersession
- usageEligibility lattice
- Concept, ConceptMapping, ConceptResolutionResult
- TrustZone, SafetyLabel
- BridgeContract, BridgeValidationResult

## 7. Anchoring contract (abstract)
Per source spec §4.6 — the abstract contract; bindings are external (separate spec).

## 8. AI-substrate-accelerator obligations
Per source spec §1.5 (1)-(7).

## 9. Public ontology imports and alignments
Per source spec §5.9 — three relationship modes: import / align / project.

## 10. Validation contract
Each term in §§4-6 MUST be exercised by at least one positive and one negative fixture in `fixtures/v0.2/`.

## 11. Compatibility and migration
None. v0.2 supersedes v0.1.x wholesale. There is no migration shim.

## 12. References
(normative + informative — populated in Task 12)
```

- [x] **Step 2: Verify the file parses as markdown (sanity)**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
test -f spec/rkaf-core-v0.2.md && wc -l spec/rkaf-core-v0.2.md
```

Expected: Line count ~70.

- [x] **Step 3: Commit**

```bash
git add spec/rkaf-core-v0.2.md
git commit -m "spec(rkaf): scaffold spec/rkaf-core-v0.2.md skeleton"
```

## Task 2: Author the v0.2 JSON-LD context (`context/rkaf-context-v0.2.jsonld`)

**Files:**
- Modify: `/Users/mikewolfd/Work/formspec-stack/rulespec/context/rkaf-context-v0.2.jsonld`

The v0.1 file from the rename plan currently contains v0.1 terms only. This task replaces it with the v0.2 context that imports the §5.9 namespaces and declares every new v0.2 term.

- [x] **Step 1: Write the v0.2 context (replace file contents)**

Replace `context/rkaf-context-v0.2.jsonld` with:

```json
{
  "@context": {
    "rkaf": "https://rulespec.org/ns/v1#",
    "prov": "http://www.w3.org/ns/prov#",
    "oa": "http://www.w3.org/ns/oa#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "dcterms": "http://purl.org/dc/terms/",
    "cito": "http://purl.org/spar/cito/",
    "dcat": "http://www.w3.org/ns/dcat#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "eli": "http://data.europa.eu/eli/ontology#",
    "aknt": "http://docs.oasis-open.org/legaldocml/ns/akn/3.0/",
    "uslm": "https://uslm.gov/2.1.0/",
    "lrml": "http://docs.oasis-open.org/legalruleml/ns/v1.0/",
    "rrmv": "http://data.europa.eu/m8g/rrmv/",
    "eco": "http://purl.obolibrary.org/obo/ECO_",
    "sepio": "http://purl.obolibrary.org/obo/SEPIO_",
    "dpv": "https://w3id.org/dpv#",
    "odrl": "http://www.w3.org/ns/odrl/2/",
    "nano": "http://www.nanopub.org/nschema#",
    "schemaorg": "https://schema.org/",

    "rkaf:Artifact": {"@type": "@id"},
    "rkaf:hasArtifactIdentifier": {"@type": "@id"},
    "rkaf:artifactIdentifierScheme": {"@type": "@vocab"},

    "rkaf:SourceFragment": {"@type": "@id"},
    "rkaf:hasSelector": {"@type": "@id"},
    "rkaf:selectorKind": {"@type": "@vocab"},

    "rkaf:EvidenceBinding": {"@type": "@id"},
    "rkaf:bindsAssertion": {"@type": "@id"},
    "rkaf:bindsSourceFragment": {"@type": "@id"},
    "rkaf:noEvidenceReason": {"@type": "@vocab"},

    "rkaf:Warrant": {"@type": "@id"},
    "rkaf:hasWarrant": {"@type": "@id"},
    "rkaf:warrantKind": {"@type": "@vocab"},
    "rkaf:warrantFamily": {"@type": "@vocab"},

    "rkaf:ConfidenceRecord": {"@type": "@id"},
    "rkaf:hasConfidence": {"@type": "@id"},
    "rkaf:confidenceMethod": {"@type": "@vocab"},
    "rkaf:calibrationStatus": {"@type": "@vocab"},
    "rkaf:confidenceBasis": {"@type": "@id"},
    "rkaf:evaluatedAgainst": {"@type": "@id"},
    "rkaf:generatedBy": {"@type": "@id"},

    "rkaf:AccessScope": {"@type": "@id"},
    "rkaf:hasAccessScope": {"@type": "@id"},
    "rkaf:accessScopeKind": {"@type": "@vocab"},
    "rkaf:embargoUntil": {"@type": "xsd:dateTime"},

    "rkaf:AILineage": {"@type": "@id"},
    "rkaf:hasAILineage": {"@type": "@id"},
    "rkaf:modelId": {"@type": "xsd:string"},
    "rkaf:modelVersion": {"@type": "xsd:string"},
    "rkaf:promptTemplateRef": {"@type": "@id"},
    "rkaf:temperature": {"@type": "xsd:float"},
    "rkaf:seed": {"@type": "xsd:integer"},
    "rkaf:inputContextHash": {"@type": "xsd:string"},
    "rkaf:humanApprover": {"@type": "@id"},
    "rkaf:humanRationale": {"@type": "xsd:string"},

    "rkaf:MappingState": {"@type": "@id"},
    "rkaf:mappingState": {"@type": "@vocab"},

    "rkaf:RetentionPolicy": {"@type": "@id"},
    "rkaf:hasRetentionPolicy": {"@type": "@id"},

    "rkaf:Workspace": {"@type": "@id"},
    "rkaf:scopedToWorkspace": {"@type": "@id"},

    "rkaf:projectsTo": {"@type": "@id"},
    "rkaf:llmHint": {"@type": "@id"},

    "rkaf:anchoredBy": {"@type": "@id"},
    "rkaf:anchorType": {"@type": "@id"},

    "rkaf:hasAuthority": {"@type": "@id"},
    "rkaf:authorityKind": {"@type": "@vocab"},
    "rkaf:assertionOrigin": {"@type": "@vocab"},
    "rkaf:hasSafetyLabel": {"@type": "@vocab"},
    "rkaf:hasTrustZone": {"@type": "@vocab"},
    "rkaf:usageEligibility": {"@type": "@vocab"},
    "rkaf:hasApplicability": {"@type": "@id"},
    "rkaf:effectivePeriod": {"@type": "@id"},

    "rkaf:supersedesAssertion": {"@type": "@id"},
    "rkaf:lifecycleEvent": {"@type": "@vocab"},

    "rkaf:assertsSubject": {"@type": "@id"},
    "rkaf:assertsPredicate": {"@type": "@id"},
    "rkaf:assertsObject": {"@type": "@id"},

    "rkaf:adoptionAuthorityKind": {"@type": "@vocab"},
    "rkaf:adoptionStatus": {"@type": "@vocab"},
    "rkaf:result": {"@type": "@vocab"},
    "rkaf:resolutionStatus": {"@type": "@vocab"},
    "rkaf:resolutionMethod": {"@type": "@vocab"},
    "rkaf:cacheStatus": {"@type": "@vocab"},
    "rkaf:usageCeiling": {"@type": "@vocab"},
    "rkaf:cascadeAlgorithm": {"@type": "@vocab"},
    "rkaf:evidenceRole": {"@type": "@vocab"},
    "rkaf:warningCode": {"@type": "@vocab"},
    "rkaf:errorCode": {"@type": "@vocab"},
    "rkaf:severity": {"@type": "@vocab"},
    "rkaf:decision": {"@type": "@vocab"},
    "rkaf:scope": {"@type": "@vocab"},
    "rkaf:visibility": {"@type": "@vocab"}
  }
}
```

- [x] **Step 2: Verify the file parses as JSON**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 -c "import json; json.load(open('context/rkaf-context-v0.2.jsonld')); print('OK')"
```

Expected: `OK`.

- [x] **Step 3: Verify the context expands a sample document via JSON-LD**

```bash
python3 -c "
from pyld import jsonld
doc = {
  '@context': 'file://$(pwd)/context/rkaf-context-v0.2.jsonld',
  '@id': 'urn:rkaf:test:1',
  '@type': 'rkaf:Artifact',
  'rkaf:hasArtifactIdentifier': 'doi:10.1000/test'
}
expanded = jsonld.expand(doc)
assert expanded[0]['@type'][0] == 'https://rulespec.org/ns/v1#Artifact'
print('expand OK:', expanded[0]['@type'])
"
```

Expected: `expand OK: ['https://rulespec.org/ns/v1#Artifact']`.

- [x] **Step 4: Commit**

```bash
git add context/rkaf-context-v0.2.jsonld
git commit -m "spec(rkaf): rewrite context/rkaf-context-v0.2.jsonld with full v0.2 vocab + ontology imports"
```

## Task 3: Define closed taxonomies (warrant kinds, mapping states, etc.) in the spec body

**Files:**
- Modify: `/Users/mikewolfd/Web/formspec-stack/rulespec/spec/rkaf-core-v0.2.md` (Section 4 expansion)

Wait — typo in path. Use `/Users/mikewolfd/Work/formspec-stack/rulespec/spec/rkaf-core-v0.2.md`.

- [x] **Step 1: Replace Section 4 placeholder with normative term definitions**

Insert after `## 4. Universal primitives`:

```markdown
### 4.1 Artifact

**rkaf:Artifact** — an immutable, addressable unit of source material.

Required properties:
- `rkaf:hasArtifactIdentifier` (1..*) — at least one content-addressable or persistent-URI identifier. MUST conform to one of the schemes enumerated by `rkaf:artifactIdentifierScheme`.
- `rkaf:artifactIdentifierScheme` — closed enum: `eli`, `eli-dl`, `eli-i`, `uslm`, `aknt-eId`, `doi`, `isbn`, `issn`, `cid`, `hash-sha256`, `urn-persistent`, `partner-defined`.

Citing an Artifact by mutable URL alone is non-conformant. Layer 2 enforces this.

### 4.2 SourceFragment

**rkaf:SourceFragment** — an addressable region within an Artifact.

Required properties:
- `rkaf:bindsArtifact` (1) — the parent Artifact identifier.
- `rkaf:hasSelector` (1..*) — at least one selector.
- `rkaf:selectorKind` — closed enum: foundational selectors `oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`; domain selectors `aknt:eId`, `uslm:section`, `eli-fragment`, `jsonpath`, `doi-fragment`, `partner-defined`.

Selector stability across Artifact revisions is a partner obligation. Supersession (§6) resolves fragment continuity. For ELI artifacts, ELI-I edges are the canonical fragment-continuity model.

### 4.3 EvidenceBinding

**rkaf:EvidenceBinding** — links an Assertion to one or more SourceFragments.

Required properties:
- `rkaf:bindsAssertion` (1) — the assertion being bound.
- One of:
  - `rkaf:bindsSourceFragment` (1..*) — at least one SourceFragment, OR
  - `rkaf:noEvidenceReason` (1) — closed enum: `axiomatic`, `inferred-from-warrant-class`, `consensus-without-citation`, `permitted-by-safety-label`. The Assertion's `rkaf:hasSafetyLabel` MUST permit the chosen reason.
- `rkaf:warrantKind` (0..1) — overrides the Assertion's warrant kind for this binding.
- `rkaf:hasAccessScope` (0..1) — narrows the binding's visibility.

An assertion lacking either an EvidenceBinding-with-fragment OR an explicit `noEvidenceReason` permitted by its safety level is **not operationally valid**. Layer 2 enforces this.

### 4.4 Warrant

**rkaf:Warrant** — the universal grounding primitive. `Authority` (Core v0.1) is preserved as the specialization for the legal/regulatory family.

Universal predicate: `rkaf:hasWarrant`.
Specialization predicate: `rkaf:hasAuthority` (legal/regulatory family).

Closed taxonomy `rkaf:warrantKind` grouped by family:

- **Legal family:** `legal`, `statutory`, `regulatory`, `delegated`, `organizational`, `contractual`, `localOperational`, `publication`.
- **Scientific family:** `methodological`, `empirical`, `replication`, `peerReview`.
- **Editorial family:** `editorial`, `factCheck`, `correction`.
- **Cryptographic family:** `cryptographic`, `commitment`.
- **Social family:** `consensus`, `expertOpinion`, `communityEndorsement`.
- **Source-class family:** `sourceReliability`, `provenanceClass`.

`rkaf:warrantFamily` is the closed enum: `legal`, `scientific`, `editorial`, `cryptographic`, `social`, `source-class`.

A warrant chain is hop-local: each hop carries its own `warrantKind`, and chains MAY transition between families. Cross-family transitions MUST be surfaced for human review by any consumer traversing them (Layer 2 enforces this surfacing as a warning, not an error).

`defeasible: boolean` is preserved for LegalRuleML interop.

Alignments per §9: legal-family warrants align with **LegalRuleML**; reporting-requirement warrants align with **RRMV**; scientific-family warrants align with **ECO** / **SEPIO**.

### 4.5 ConfidenceRecord

**rkaf:ConfidenceRecord** — first-class structured confidence over an assertion.

Required properties:
- `rkaf:confidenceMethod` — closed enum: `model-inference`, `human-estimation`, `review-consensus`, `source-class-inheritance`, `rule-based`.
- `rkaf:score` — `xsd:float` in [0.0, 1.0] OR `rkaf:scoreCategorical` from closed enum `{very-low, low, medium, high, very-high}`.
- `rkaf:calibrationStatus` — closed enum: `uncalibrated`, `calibratedAgainst`, `humanEstimated`, `consensus`. If `calibratedAgainst`, `rkaf:evaluatedAgainst` (1) MUST point to the calibration corpus.
- `rkaf:confidenceBasis` (1..*) — what evidence the confidence is grounded in (Assertions, SourceFragments, fixtures, datasets).
- `rkaf:generatedBy` (1) — actor: model identity (with version + prompt template ref), human identity, or community process identifier.

A ConfidenceRecord lacking `confidenceMethod`, `confidenceBasis`, or `calibrationStatus` is "score theater" and is non-conformant. Layer 2 rejects these.

Multiple ConfidenceRecord instances on the same assertion are explicitly permitted and represent independently-measured confidences (uncalibrated model + calibrated model + human + review consensus + source reliability MAY coexist). Consumers MUST distinguish them by `confidenceMethod`.

### 4.6 AccessScope

**rkaf:AccessScope** — visibility boundary attachable to Assertions, Attestations, EvidenceBindings, and SourceFragments.

Required property:
- `rkaf:accessScopeKind` — closed enum: `public`, `partnerVisible`, `organizationVisible`, `roleRestricted`, `personalRestricted`, `regulatoryRestricted`, `embargoUntil`.

Conditional properties:
- If `regulatoryRestricted`, `rkaf:regulatoryClass` (1..*) from closed enum `{HIPAA-PHI, GDPR-PII, FERPA, CJIS, classified, legally-privileged, partner-defined}`.
- If `embargoUntil`, `rkaf:embargoUntil` (`xsd:dateTime`) MUST be present.
- If `roleRestricted`, `rkaf:permittedRole` (1..*) URIs.

Consumers MUST preserve AccessScope through retrieval, projection, summarization, federation, and AI-assisted consumption. A consumer that exposes content beyond its declared AccessScope is non-conformant. Layer 6 conformance includes adversarial fixtures designed to surface AccessScope leakage.

Aligned with **W3C ODRL** (rights expression — overlay-attached, not inline) and **W3C DPV** (privacy classification — overlay-attached for `regulatoryRestricted` cases). Partners requiring full rights expression or full privacy classification attach ODRL/DPV overlays via the Layer 4 projector pattern.
```

- [x] **Step 2: Verify the spec compiles to a single readable markdown file**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
wc -l spec/rkaf-core-v0.2.md
grep -c "^### 4\." spec/rkaf-core-v0.2.md
```

Expected: ~250 lines; six §4.x subsection headings (4.1 through 4.6).

- [x] **Step 3: Commit**

```bash
git add spec/rkaf-core-v0.2.md
git commit -m "spec(rkaf): define §4 universal primitives (Artifact, SourceFragment, EvidenceBinding, Warrant, ConfidenceRecord, AccessScope)"
```

## Task 4: Define Studio-derived promotions (§5 of spec body)

**Files:**
- Modify: `spec/rkaf-core-v0.2.md` (Section 5)
- Create: `spec/rkaf-vocabulary-v0.2.md` — full term reference (one row per term)

- [x] **Step 1: Replace Section 5 placeholder with normative promotion definitions**

Insert under `## 5. Studio-derived promotions`:

```markdown
### 5.1 rkaf:MappingState

Closed enum (four values): `mapsToWos`, `authoringOnly`, `requiresSpecExtension`, `unmappedButApproved`.

Property: `rkaf:mappingState`. Domain: any mapping-bearing object (Studio profile uses this on mapping outputs; universal Vocabulary exposes the enum so non-Studio partners may attach it to their own mapping primitives).

### 5.2 rkaf:RetentionPolicy

First-class typed shape. Required properties:
- `rkaf:retentionDurationDays` (`xsd:int`) — non-negative.
- `rkaf:retentionTrigger` — closed enum: `creation`, `lastAccess`, `lastModification`, `lifecycleEvent`.
- `rkaf:retentionPostExpiry` — closed enum: `delete`, `anonymize`, `archive`, `legal-hold-on-trigger`.

Attached to Artifacts, Assertions, Attestations, or EvidenceBindings via `rkaf:hasRetentionPolicy`.

### 5.3 rkaf:AILineage

Required properties:
- `rkaf:modelId` (`xsd:string`)
- `rkaf:modelVersion` (`xsd:string`)
- `rkaf:promptTemplateRef` (IRI)
- `rkaf:temperature` (`xsd:float`)
- `rkaf:seed` (`xsd:integer`, optional)
- `rkaf:inputContextHash` (`xsd:string`)
- `rkaf:humanApprover` (IRI, REQUIRED) — the actor who approved the AI output for the assertion's `assertionOrigin` value.
- `rkaf:humanRationale` (`xsd:string`, REQUIRED if `assertionOrigin = aiPromoted` or `humanQualified`).

An assertion with `assertionOrigin ∈ {aiSuggested, aiPromoted, humanQualified, humanRevalidation}` MUST carry an `rkaf:hasAILineage` reference. Layer 2 enforces this.

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
- `rkaf:workspaceId` (`xsd:string`, REQUIRED) — the local identifier within the workspace's URN scheme.
- `rkaf:workspaceTrustList` (1..*) — IRIs of peer workspaces this workspace declares trust for (Layer 3 federation reference).

URN scheme: `urn:rkaf:workspace:<workspaceId>/<localId>` resolves within the workspace; federable across mutually trusting workspaces.

### 5.6 rkaf:projectsTo

Property. Declares the target schema fragment a Rulespec overlay projects to. Domain: any Rulespec graph node. Range: IRI of a target schema artifact (JSON Schema $defs reference, OpenAPI component reference, etc.).

Generalizes Studio's `wosTarget` projection pattern.
```

- [x] **Step 2: Create `spec/rkaf-vocabulary-v0.2.md`** — flat term reference

This document is the full `term → IRI → type → domain → range → cardinality → fixture-name` table. It exists so the SDK code generators (Plan 6) and the JSON Schema projector (Plan 5) can consume one canonical source.

```markdown
# Rulespec Vocabulary v0.2 — Full Term Reference

> Mechanically-consumable. One row per term. Source of truth for code generators and projectors.

| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |
|---|---|---|---|---|---|---|
| rkaf:Artifact | https://rulespec.org/ns/v1#Artifact | Class | — | — | — | artifact-eli-positive, artifact-doi-positive, artifact-cid-positive |
| rkaf:hasArtifactIdentifier | …#hasArtifactIdentifier | Property | rkaf:Artifact | xsd:string \| IRI | 1..* | (covered by Artifact fixtures) |
| rkaf:artifactIdentifierScheme | …#artifactIdentifierScheme | Property (closed enum) | rkaf:Artifact | rkaf:ArtifactIdentifierScheme | 1..* | (covered by Artifact fixtures) |
| rkaf:SourceFragment | …#SourceFragment | Class | — | — | — | sourcefragment-oa-textquote-positive, sourcefragment-oa-xpath-positive, sourcefragment-aknt-eid-positive, sourcefragment-uslm-section-positive |
| rkaf:hasSelector | …#hasSelector | Property | rkaf:SourceFragment | oa:Selector OR rkaf:Selector | 1..* | (covered) |
| rkaf:selectorKind | …#selectorKind | Property (closed enum) | rkaf:SourceFragment | rkaf:SelectorKind | 1..* | (covered) |
| rkaf:EvidenceBinding | …#EvidenceBinding | Class | — | — | — | evidencebinding-positive, evidencebinding-no-evidence-reason-positive, evidencebinding-missing-negative |
| rkaf:bindsAssertion | …#bindsAssertion | Property | rkaf:EvidenceBinding | rkaf:Assertion | 1 | (covered) |
| rkaf:bindsSourceFragment | …#bindsSourceFragment | Property | rkaf:EvidenceBinding | rkaf:SourceFragment | 0..* | (covered) |
| rkaf:noEvidenceReason | …#noEvidenceReason | Property (closed enum) | rkaf:EvidenceBinding | rkaf:NoEvidenceReason | 0..1 | (covered) |
| rkaf:Warrant | …#Warrant | Class | — | — | — | warrant-legal-positive, warrant-scientific-positive, warrant-cross-family-transition-positive |
| rkaf:hasWarrant | …#hasWarrant | Property | rkaf:Assertion / rkaf:EvidenceBinding | rkaf:Warrant | 1..* | (covered) |
| rkaf:warrantKind | …#warrantKind | Property (closed enum) | rkaf:Warrant | rkaf:WarrantKind | 1 | (covered) |
| rkaf:warrantFamily | …#warrantFamily | Property (closed enum) | rkaf:Warrant | rkaf:WarrantFamily | 1 | (covered) |
| rkaf:hasAuthority | …#hasAuthority | Property (legal specialization of hasWarrant) | rkaf:Assertion | rkaf:Authority | 1..* | (warrant-legal-positive) |
| rkaf:ConfidenceRecord | …#ConfidenceRecord | Class | — | — | — | confidencerecord-uncalibrated-positive, confidencerecord-calibrated-positive, confidencerecord-score-theater-negative |
| rkaf:hasConfidence | …#hasConfidence | Property | rkaf:Assertion | rkaf:ConfidenceRecord | 0..* | (covered) |
| rkaf:confidenceMethod | …#confidenceMethod | Property (closed enum) | rkaf:ConfidenceRecord | rkaf:ConfidenceMethod | 1 | (covered) |
| rkaf:calibrationStatus | …#calibrationStatus | Property (closed enum) | rkaf:ConfidenceRecord | rkaf:CalibrationStatus | 1 | (covered) |
| rkaf:AccessScope | …#AccessScope | Class | — | — | — | accessscope-public-positive, accessscope-organizationVisible-positive, accessscope-leak-negative |
| rkaf:hasAccessScope | …#hasAccessScope | Property | rkaf:Assertion / rkaf:Attestation / rkaf:EvidenceBinding / rkaf:SourceFragment | rkaf:AccessScope | 0..1 | (covered) |
| rkaf:accessScopeKind | …#accessScopeKind | Property (closed enum) | rkaf:AccessScope | rkaf:AccessScopeKind | 1 | (covered) |
| rkaf:AILineage | …#AILineage | Class | — | — | — | ailineage-positive, ailineage-missing-approver-negative |
| rkaf:hasAILineage | …#hasAILineage | Property | rkaf:Assertion | rkaf:AILineage | 0..1 (REQUIRED if assertionOrigin ∈ {aiSuggested, aiPromoted, humanQualified, humanRevalidation}) | (covered) |
| rkaf:MappingState | …#MappingState | Class (closed enum) | — | — | — | mappingstate-positive |
| rkaf:RetentionPolicy | …#RetentionPolicy | Class | — | — | — | retentionpolicy-positive |
| rkaf:hasRetentionPolicy | …#hasRetentionPolicy | Property | rkaf:Artifact / rkaf:Assertion / rkaf:Attestation / rkaf:EvidenceBinding | rkaf:RetentionPolicy | 0..1 | (covered) |
| rkaf:Workspace | …#Workspace | Class | — | — | — | workspace-positive |
| rkaf:projectsTo | …#projectsTo | Property | any | IRI | 0..* | (covered indirectly via projector fixtures, Plan 5) |
| rkaf:llmHint | …#llmHint | Annotation property | any vocabulary term | rkaf:LLMHint | 0..1 | (covered indirectly via projector fixtures, Plan 5) |
| rkaf:anchoredBy | …#anchoredBy | Property | any rkaf:Assertion / rkaf:Overlay | IRI | 0..* | (Plan 9) |
| rkaf:anchorType | …#anchorType | Property | anchor IRI | IRI (binding type URI) | 1 | (Plan 9) |

(Plus all Core v0.1 terms — Assertion, Attestation, LocalAdoption, Justification, Authority, ApplicabilityScope, EffectivePeriod, LifecycleEvent, Supersession, usageEligibility, Concept, ConceptMapping, ConceptResolutionResult, TrustZone, SafetyLabel, BridgeContract, BridgeValidationResult — preserved name-for-name from `spec/rkaf-core-v0.1.md`. Re-listed in `spec/rkaf-vocabulary-v0.2.md` so this file is the single source for code generation.)

> Mechanical consumers: parse the table by markdown row. The `Required fixtures` column is enforced by `tools/vocab_audit.py` (Task 13) — every named fixture MUST exist under `fixtures/v0.2/`.
```

- [x] **Step 3: Commit**

```bash
git add spec/rkaf-core-v0.2.md spec/rkaf-vocabulary-v0.2.md
git commit -m "spec(rkaf): define §5 Studio-derived promotions and full v0.2 term reference"
```

## Task 5: Author SHACL shape file for §4 primitives (warrant + artifact + sourcefragment + evidencebinding)

**Files:**
- Create: `/Users/mikewolfd/Work/formspec-stack/rulespec/shapes/rkaf-shapes-warrant-v0.2.ttl`

- [x] **Step 1: Write the SHACL shape file**

```turtle
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix oa:    <http://www.w3.org/ns/oa#> .
@prefix rkaf:  <https://rulespec.org/ns/v1#> .

# --- Artifact ---
rkaf:ArtifactShape a sh:NodeShape ;
  sh:targetClass rkaf:Artifact ;
  sh:property [
    sh:path rkaf:hasArtifactIdentifier ;
    sh:minCount 1 ;
    sh:message "Artifact MUST carry at least one rkaf:hasArtifactIdentifier (§4.1)." ;
  ] ;
  sh:property [
    sh:path rkaf:artifactIdentifierScheme ;
    sh:minCount 1 ;
    sh:in ( rkaf:eli rkaf:eli-dl rkaf:eli-i rkaf:uslm rkaf:aknt-eId
            rkaf:doi rkaf:isbn rkaf:issn rkaf:cid rkaf:hash-sha256
            rkaf:urn-persistent rkaf:partner-defined ) ;
    sh:message "Artifact identifier scheme MUST be from the closed enum (§4.1)." ;
  ] .

# --- SourceFragment ---
rkaf:SourceFragmentShape a sh:NodeShape ;
  sh:targetClass rkaf:SourceFragment ;
  sh:property [ sh:path rkaf:bindsArtifact ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:message "SourceFragment MUST reference exactly one parent Artifact (§4.2)." ;
  ] ;
  sh:property [ sh:path rkaf:hasSelector ; sh:minCount 1 ;
    sh:message "SourceFragment MUST carry at least one selector (§4.2)." ;
  ] ;
  sh:property [ sh:path rkaf:selectorKind ; sh:minCount 1 ;
    sh:in ( oa:FragmentSelector oa:TextQuoteSelector oa:TextPositionSelector
            oa:RangeSelector oa:XPathSelector oa:CssSelector
            rkaf:aknt-eId rkaf:uslm-section rkaf:eli-fragment
            rkaf:jsonpath rkaf:doi-fragment rkaf:partner-defined ) ;
    sh:message "Selector kind MUST be from the closed enum (§4.2)." ;
  ] .

# --- EvidenceBinding (the load-bearing constraint per §4.3) ---
rkaf:EvidenceBindingShape a sh:NodeShape ;
  sh:targetClass rkaf:EvidenceBinding ;
  sh:property [ sh:path rkaf:bindsAssertion ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:message "EvidenceBinding MUST reference exactly one Assertion (§4.3)." ;
  ] ;
  # Use Pattern C (sh:or with sh:not) per Appendix C — sh:if/sh:then is unreliable.
  sh:or (
    [ sh:property [ sh:path rkaf:bindsSourceFragment ; sh:minCount 1 ; ] ]
    [ sh:property [ sh:path rkaf:noEvidenceReason ; sh:minCount 1 ; sh:maxCount 1 ;
        sh:in ( rkaf:axiomatic rkaf:inferred-from-warrant-class
                rkaf:consensus-without-citation rkaf:permitted-by-safety-label ) ; ] ]
  ) ;
  sh:message "EvidenceBinding MUST either bind ≥1 SourceFragment OR carry a permitted noEvidenceReason (§4.3 — operational-validity invariant)." .

# --- Warrant ---
rkaf:WarrantShape a sh:NodeShape ;
  sh:targetClass rkaf:Warrant ;
  sh:property [ sh:path rkaf:warrantKind ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:in (
      # Legal family (preserved from v0.1 authorityKind)
      rkaf:legal rkaf:statutory rkaf:regulatory rkaf:delegated rkaf:organizational
      rkaf:contractual rkaf:localOperational rkaf:publication
      # Scientific
      rkaf:methodological rkaf:empirical rkaf:replication rkaf:peerReview
      # Editorial
      rkaf:editorial rkaf:factCheck rkaf:correction
      # Cryptographic
      rkaf:cryptographic rkaf:commitment
      # Social
      rkaf:consensus rkaf:expertOpinion rkaf:communityEndorsement
      # Source-class
      rkaf:sourceReliability rkaf:provenanceClass
    ) ;
    sh:message "warrantKind MUST be from the closed v0.2 taxonomy (§4.4)." ;
  ] ;
  sh:property [ sh:path rkaf:warrantFamily ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:in ( rkaf:legal rkaf:scientific rkaf:editorial rkaf:cryptographic
            rkaf:social rkaf:source-class ) ;
    sh:message "warrantFamily MUST be from the closed enum (§4.4)." ;
  ] .
```

- [x] **Step 2: Verify pyshacl parses the shapes file**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 -c "
import rdflib
g = rdflib.Graph(); g.parse('shapes/rkaf-shapes-warrant-v0.2.ttl', format='turtle')
print(f'parsed {len(g)} triples')
"
```

Expected: triple count > 0; no exceptions.

- [x] **Step 3: Commit**

```bash
git add shapes/rkaf-shapes-warrant-v0.2.ttl
git commit -m "spec(rkaf): add SHACL shapes for v0.2 §4 primitives (warrant/artifact/sourcefragment/evidencebinding)"
```

## Task 6: Author SHACL shape files for ConfidenceRecord and AccessScope

**Files:**
- Create: `shapes/rkaf-shapes-confidence-v0.2.ttl`
- Create: `shapes/rkaf-shapes-accessscope-v0.2.ttl`

- [x] **Step 1: Write `rkaf-shapes-confidence-v0.2.ttl`**

```turtle
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix rkaf:  <https://rulespec.org/ns/v1#> .

rkaf:ConfidenceRecordShape a sh:NodeShape ;
  sh:targetClass rkaf:ConfidenceRecord ;
  sh:property [ sh:path rkaf:confidenceMethod ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:in ( rkaf:model-inference rkaf:human-estimation rkaf:review-consensus
            rkaf:source-class-inheritance rkaf:rule-based ) ;
    sh:message "ConfidenceRecord MUST declare confidenceMethod from closed enum (§4.5)." ;
  ] ;
  sh:property [ sh:path rkaf:calibrationStatus ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:in ( rkaf:uncalibrated rkaf:calibratedAgainst rkaf:humanEstimated rkaf:consensus ) ;
    sh:message "ConfidenceRecord MUST declare calibrationStatus (§4.5)." ;
  ] ;
  sh:property [ sh:path rkaf:confidenceBasis ; sh:minCount 1 ;
    sh:message "ConfidenceRecord MUST declare ≥1 basis (§4.5; rejects score theater)." ;
  ] ;
  sh:property [ sh:path rkaf:generatedBy ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:message "ConfidenceRecord MUST declare generatedBy actor (§4.5)." ;
  ] ;
  # Pattern C: if calibrationStatus == calibratedAgainst, evaluatedAgainst MUST be present.
  sh:or (
    [ sh:property [ sh:path rkaf:calibrationStatus ;
        sh:not [ sh:hasValue rkaf:calibratedAgainst ] ] ]
    [ sh:property [ sh:path rkaf:evaluatedAgainst ; sh:minCount 1 ] ]
  ) ;
  sh:message "ConfidenceRecord with calibratedAgainst MUST carry rkaf:evaluatedAgainst (§4.5)." .
```

- [x] **Step 2: Write `rkaf-shapes-accessscope-v0.2.ttl`**

```turtle
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix rkaf:  <https://rulespec.org/ns/v1#> .

rkaf:AccessScopeShape a sh:NodeShape ;
  sh:targetClass rkaf:AccessScope ;
  sh:property [ sh:path rkaf:accessScopeKind ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:in ( rkaf:public rkaf:partnerVisible rkaf:organizationVisible
            rkaf:roleRestricted rkaf:personalRestricted
            rkaf:regulatoryRestricted rkaf:embargoUntil ) ;
    sh:message "AccessScope kind MUST be from closed enum (§4.6)." ;
  ] ;
  # Pattern C: if regulatoryRestricted, regulatoryClass MUST be present
  sh:or (
    [ sh:property [ sh:path rkaf:accessScopeKind ;
        sh:not [ sh:hasValue rkaf:regulatoryRestricted ] ] ]
    [ sh:property [ sh:path rkaf:regulatoryClass ; sh:minCount 1 ] ]
  ) ;
  sh:message "regulatoryRestricted AccessScope MUST declare ≥1 regulatoryClass (§4.6)." ;
  # Pattern C: if embargoUntil kind, embargoUntil dateTime MUST be present
  sh:or (
    [ sh:property [ sh:path rkaf:accessScopeKind ;
        sh:not [ sh:hasValue rkaf:embargoUntil ] ] ]
    [ sh:property [ sh:path rkaf:embargoUntil ;
        sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:dateTime ] ]
  ) ;
  sh:message "embargoUntil AccessScope MUST carry rkaf:embargoUntil (xsd:dateTime) (§4.6)." .
```

- [x] **Step 3: Verify both shape files parse**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 -c "
import rdflib
for f in ['shapes/rkaf-shapes-confidence-v0.2.ttl', 'shapes/rkaf-shapes-accessscope-v0.2.ttl']:
    g = rdflib.Graph(); g.parse(f, format='turtle'); print(f, len(g), 'triples')
"
```

Expected: Both files print non-zero triple count.

- [x] **Step 4: Commit**

```bash
git add shapes/rkaf-shapes-confidence-v0.2.ttl shapes/rkaf-shapes-accessscope-v0.2.ttl
git commit -m "spec(rkaf): add SHACL shapes for ConfidenceRecord and AccessScope (v0.2)"
```

## Task 7: Author SHACL shape file for §5 Studio-derived promotions

**Files:**
- Create: `shapes/rkaf-shapes-studio-promotions-v0.2.ttl`

- [x] **Step 1: Write the shape file**

```turtle
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .
@prefix rkaf:  <https://rulespec.org/ns/v1#> .

# --- MappingState ---
rkaf:MappingStateShape a sh:NodeShape ;
  sh:targetSubjectsOf rkaf:mappingState ;
  sh:property [ sh:path rkaf:mappingState ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:in ( rkaf:mapsToWos rkaf:authoringOnly rkaf:requiresSpecExtension rkaf:unmappedButApproved ) ;
    sh:message "mappingState MUST be from the closed four-value enum (§5.1)." ;
  ] .

# --- RetentionPolicy ---
rkaf:RetentionPolicyShape a sh:NodeShape ;
  sh:targetClass rkaf:RetentionPolicy ;
  sh:property [ sh:path rkaf:retentionDurationDays ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:datatype xsd:int ; sh:minInclusive 0 ; ] ;
  sh:property [ sh:path rkaf:retentionTrigger ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:in ( rkaf:creation rkaf:lastAccess rkaf:lastModification rkaf:lifecycleEvent ) ; ] ;
  sh:property [ sh:path rkaf:retentionPostExpiry ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:in ( rkaf:delete rkaf:anonymize rkaf:archive rkaf:legal-hold-on-trigger ) ; ] .

# --- AILineage ---
rkaf:AILineageShape a sh:NodeShape ;
  sh:targetClass rkaf:AILineage ;
  sh:property [ sh:path rkaf:modelId ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ; ] ;
  sh:property [ sh:path rkaf:modelVersion ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ; ] ;
  sh:property [ sh:path rkaf:promptTemplateRef ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ; ] ;
  sh:property [ sh:path rkaf:temperature ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:float ; ] ;
  sh:property [ sh:path rkaf:inputContextHash ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ; ] ;
  sh:property [ sh:path rkaf:humanApprover ; sh:minCount 1 ; sh:maxCount 1 ; sh:nodeKind sh:IRI ;
    sh:message "AILineage MUST declare humanApprover (§5.3)." ; ] .

# --- Workspace ---
rkaf:WorkspaceShape a sh:NodeShape ;
  sh:targetClass rkaf:Workspace ;
  sh:property [ sh:path rkaf:workspaceId ; sh:minCount 1 ; sh:maxCount 1 ; sh:datatype xsd:string ; ] .
```

- [x] **Step 2: Verify it parses**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 -c "
import rdflib
g = rdflib.Graph(); g.parse('shapes/rkaf-shapes-studio-promotions-v0.2.ttl', format='turtle')
print('triples:', len(g))
"
```

Expected: Triple count > 0.

- [x] **Step 3: Commit**

```bash
git add shapes/rkaf-shapes-studio-promotions-v0.2.ttl
git commit -m "spec(rkaf): add SHACL shapes for v0.2 Studio-derived promotions (MappingState, RetentionPolicy, AILineage, Workspace)"
```

## Task 8: Compose `shapes/rkaf-shapes-core-v0.2.ttl` (umbrella shape file)

**Files:**
- Create: `shapes/rkaf-shapes-core-v0.2.ttl`

This file is the canonical entry point for v0.2 SHACL validation. It imports the v0.1 inherited shapes (Authority/Assertion/etc., subclassed under Warrant) plus the four new v0.2 shape files.

- [x] **Step 1: Write the umbrella file**

```turtle
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix owl:   <http://www.w3.org/2002/07/owl#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix rkaf:  <https://rulespec.org/ns/v1#> .

# Umbrella ontology declaration: imports the v0.2 modular shape files.
<https://rulespec.org/shapes/v0.2/core>
  a owl:Ontology ;
  rdfs:label "Rulespec Core SHACL shapes v0.2 (umbrella)" ;
  owl:imports
    <https://rulespec.org/shapes/v0.2/warrant> ,
    <https://rulespec.org/shapes/v0.2/confidence> ,
    <https://rulespec.org/shapes/v0.2/accessscope> ,
    <https://rulespec.org/shapes/v0.2/studio-promotions> ,
    # v0.1 inherited shape files (still load-bearing for Assertion / Attestation / Authority / etc.):
    <https://rulespec.org/shapes/v0.1/core> ,
    <https://rulespec.org/shapes/v0.1/conceptregistry> ,
    <https://rulespec.org/shapes/v0.1/lifecycle> ,
    <https://rulespec.org/shapes/v0.1/justification> .

# Authority is now a specialization of Warrant (§4.4).
rkaf:Authority rdfs:subClassOf rkaf:Warrant .

# Assertion-level requirement: an Assertion with assertionOrigin in the AI-touched set
# MUST carry rkaf:hasAILineage (§5.3). Pattern C.
rkaf:AssertionAILineageShape a sh:NodeShape ;
  sh:targetClass rkaf:Assertion ;
  sh:or (
    [ sh:property [ sh:path rkaf:assertionOrigin ;
        sh:not [ sh:in ( rkaf:aiSuggested rkaf:aiPromoted
                          rkaf:humanQualified rkaf:humanRevalidation ) ] ] ]
    [ sh:property [ sh:path rkaf:hasAILineage ; sh:minCount 1 ] ]
  ) ;
  sh:message "Assertion with AI-touched assertionOrigin MUST carry rkaf:hasAILineage (§5.3)." .
```

- [x] **Step 2: Verify it parses (without owl:imports resolution — pyshacl loads the union explicitly)**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 -c "
import rdflib
g = rdflib.Graph(); g.parse('shapes/rkaf-shapes-core-v0.2.ttl', format='turtle')
print('triples:', len(g))
"
```

Expected: Triple count > 0.

- [x] **Step 3: Commit**

```bash
git add shapes/rkaf-shapes-core-v0.2.ttl
git commit -m "spec(rkaf): compose v0.2 SHACL umbrella shape file"
```

## Task 9: Author `spec/rkaf-concept-registry-v0.2.md`

**Files:**
- Create: `spec/rkaf-concept-registry-v0.2.md`

Concept registry v0.2 supersedes v0.1.2 — same primitives, extended to:
- Use SKOS predicates (`closeMatch`, `exactMatch`, `broader`, `narrower`, `related`, `mappingRelation`) per §5.9.
- Adopt `rkaf:Workspace` scoping for partner-local concepts.
- Use `rkaf:hasWarrant` instead of `rkaf:hasAuthority` for the warrant on a concept-mapping Justification.

- [x] **Step 1: Write the spec file (sections + normative term updates)**

Structure: copy the v0.1.2 structure (sections + headings) but replace prose where the warrant predicate broadens. Reference SKOS imports per §9 of `rkaf-core-v0.2.md`. Length similar to v0.1.2 (~600 lines).

```markdown
# Rulespec Concept Registry — v0.2

**Status:** Pre-release, normative.
**Supersedes:** `spec/rkaf-concept-registry-v0.1.2.md`.
**Companion docs:** `spec/rkaf-core-v0.2.md`.

## 1. Purpose
The Concept Registry stores canonical concepts, mappings between concepts, applicability contexts, lifecycle events on concepts, and conflict resolution among competing canonical assignments.

## 2. Primitives
(Inherited from v0.1.2 with three v0.2 changes.)

### 2.1 rkaf:Concept
(Definition copied from v0.1.2 §2.1, replacing pkaf:→rkaf:.)

### 2.2 rkaf:ConceptMapping
The mapping relation MUST use a SKOS predicate from the closed set:
`skos:closeMatch`, `skos:exactMatch`, `skos:broader`, `skos:narrower`, `skos:related`, `skos:mappingRelation`.

(Replaces v0.1.2's bespoke `rkaf:mappingRelation` enum. SKOS owns this vocabulary; do not duplicate.)

### 2.3 rkaf:ConceptResolutionResult
(Inherited.)

### 2.4 rkaf:Workspace scoping
A Concept MAY be scoped to a `rkaf:Workspace` via `rkaf:scopedToWorkspace`. Workspace-scoped concepts are federable to peer workspaces declaring mutual trust per Plan 4 (Layer 3 federation).

### 2.5 Justification on a mapping
A `rkaf:ConceptMapping` MAY carry a `rkaf:hasJustification` whose Justification carries `rkaf:hasWarrant` (warrant kind from any family, not only legal). v0.1.2's `rkaf:hasAuthority` remains valid as the legal-family specialization.

## 3. Conflict resolution
(Inherited from v0.1.2 §3.)

## 4. Lifecycle on Concept
(Inherited from v0.1.2 §4.)

## 5. SHACL
Validated by `shapes/rkaf-shapes-conceptregistry-v0.2.ttl` (Task 10).

## 6. Compatibility
None with v0.1.2. Migration not supported. Replace.
```

- [x] **Step 2: Commit**

```bash
git add spec/rkaf-concept-registry-v0.2.md
git commit -m "spec(rkaf): author concept registry v0.2 (SKOS predicates, workspace scoping, warrant generalization)"
```

## Task 10: Author `shapes/rkaf-shapes-conceptregistry-v0.2.ttl`

**Files:**
- Create: `shapes/rkaf-shapes-conceptregistry-v0.2.ttl`

- [x] **Step 1: Write the shape file (subsumes v0.1.2 with SKOS-predicate enum)**

```turtle
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix skos:  <http://www.w3.org/2004/02/skos/core#> .
@prefix rkaf:  <https://rulespec.org/ns/v1#> .

# ConceptMapping uses SKOS predicates only.
rkaf:ConceptMappingShape a sh:NodeShape ;
  sh:targetClass rkaf:ConceptMapping ;
  sh:property [ sh:path rkaf:mappingRelation ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:in ( skos:closeMatch skos:exactMatch skos:broader skos:narrower
            skos:related skos:mappingRelation ) ;
    sh:message "ConceptMapping mappingRelation MUST be a SKOS predicate (concept-registry-v0.2 §2.2)." ;
  ] .

# Workspace-scoped Concept MUST link to a declared Workspace.
rkaf:ConceptWorkspaceShape a sh:NodeShape ;
  sh:targetSubjectsOf rkaf:scopedToWorkspace ;
  sh:property [ sh:path rkaf:scopedToWorkspace ; sh:minCount 1 ; sh:maxCount 1 ;
    sh:nodeKind sh:IRI ;
    sh:message "scopedToWorkspace MUST reference a Workspace IRI (concept-registry-v0.2 §2.4)." ;
  ] .
```

- [x] **Step 2: Verify parse**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 -c "
import rdflib
g = rdflib.Graph(); g.parse('shapes/rkaf-shapes-conceptregistry-v0.2.ttl', format='turtle')
print('triples:', len(g))
"
```

Expected: Triple count > 0.

- [x] **Step 3: Commit**

```bash
git add shapes/rkaf-shapes-conceptregistry-v0.2.ttl
git commit -m "spec(rkaf): add SHACL shapes for concept registry v0.2 (SKOS-bound mapping predicates, workspace scoping)"
```

## Task 11: Author the §9 ontology imports/alignments table in `spec/rkaf-core-v0.2.md`

**Files:**
- Modify: `spec/rkaf-core-v0.2.md` (Section 9)

- [x] **Step 1: Replace the §9 placeholder with the full alignment table**

Insert under `## 9. Public ontology imports and alignments`. The content here MUST match the source spec §5.9 verbatim in normative content (predicate names, prefixes, alignment postures). Copy the three subsections: Imports, Alignments, Projections, Reference/influence — all from spec §5.9.

(The full text is omitted from this plan to avoid duplication — the engineer pastes the §5.9 normative content from `thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md` lines ~456-518 with a heading change to "## 9. Public ontology imports and alignments [Normative]" and any `pkaf:`→`rkaf:` rewrites already covered by repo extract+rename.)

- [x] **Step 2: Verify the section pulled across cleanly**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
grep -c "^| \*\*W3C" spec/rkaf-core-v0.2.md
```

Expected: 6 or more (six W3C-prefixed rows in the §5.9 imports + alignments table: PROV-O, OA, SKOS, ODRL, DPV, Verifiable Credentials, Web Annotation Ontology — depending on whether you count combined rows).

- [x] **Step 3: Commit**

```bash
git add spec/rkaf-core-v0.2.md
git commit -m "spec(rkaf): import §9 ontology composition table into core v0.2 spec"
```

## Task 12: Author the §10 validation contract and §11/§12 sections

**Files:**
- Modify: `spec/rkaf-core-v0.2.md` (Sections 10, 11, 12)

- [x] **Step 1: Replace placeholders with normative text**

Under `## 10. Validation contract`:

```markdown
Every term defined in §§4-6 MUST be exercised by:
- At least one positive fixture in `fixtures/v0.2/`.
- At least one negative fixture in `fixtures/v0.2/` whose violation surfaces a SHACL constraint failure on the v0.2 shape set.
- (For terms reached by the JSON Schema projector — Layer 4 plan) at least one round-trip parity fixture demonstrating Attach + Extract on a representative payload.

Fixture-coverage enforcement is automated by `tools/vocab_audit.py` (Task 13).

The v0.2 SHACL shape set `shapes/rkaf-shapes-core-v0.2.ttl` is one compilation target of the constraint source-of-truth language defined in Layer 2 (Plan 3). When the Layer 2 constraint DSL is selected and integrated, the SHACL shapes in this directory become projector outputs and not the source of truth (per source spec §6.1, Appendix C).
```

Under `## 11. Compatibility and migration`:

```markdown
None. Rulespec v0.2 supersedes v0.1.x wholesale. v0.1.x JSON-LD payloads with `pkaf:` prefix and `https://w3id.org/pkaf/ns/v1#` IRIs are not parseable by v0.2 tooling.

There is no migration shim. There is no compatibility re-export. There is no `pkaf:`-aliased context. Producers of pre-v0.2 artifacts re-emit them under v0.2 vocabulary, or freeze them at v0.1.

This is greenfield. v0.1.x served as the editorial baseline; v0.2 is the contract.
```

Under `## 12. References`:

Copy the normative + informative reference lists from source spec §References, replacing PKAF references with RKAF and updating file paths to `spec/rkaf-core-v0.2.md` etc.

- [x] **Step 2: Final spec sanity check**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
wc -l spec/rkaf-core-v0.2.md
grep -c "^## " spec/rkaf-core-v0.2.md
```

Expected: ~600+ lines; 13 top-level sections (0-12).

- [x] **Step 3: Commit**

```bash
git add spec/rkaf-core-v0.2.md
git commit -m "spec(rkaf): finalize v0.2 §10 validation contract, §11 compatibility (none), §12 references"
```

## Task 13: Author `tools/vocab_audit.py` (fixture coverage enforcement)

**Files:**
- Create: `tools/vocab_audit.py`

- [x] **Step 1: Write the audit script**

```python
#!/usr/bin/env python3
"""Vocab audit — fails the build if a v0.2 vocabulary term has zero fixtures.

Parses spec/rkaf-vocabulary-v0.2.md (the term reference table) and verifies
that every fixture name listed in the `Required fixtures` column exists
under fixtures/v0.2/ as a `<name>.jsonld` file.

Exit codes:
  0  every required fixture present
  1  one or more required fixtures missing
  2  parse error (table malformed)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERM_DOC = ROOT / "spec" / "rkaf-vocabulary-v0.2.md"
FIXTURE_DIR = ROOT / "fixtures" / "v0.2"

FIXTURE_NAME = re.compile(r"[a-z0-9][a-z0-9-]+")

def parse_required_fixtures(text: str) -> set[str]:
    required: set[str] = set()
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Term "):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        # Last cell: "Required fixtures"
        for token in re.split(r"[,\s]+", cells[-1]):
            if FIXTURE_NAME.fullmatch(token) and token not in {"covered"}:
                required.add(token)
    return required

def main() -> int:
    if not TERM_DOC.exists():
        print(f"ERROR: term reference {TERM_DOC} missing", file=sys.stderr)
        return 2
    required = parse_required_fixtures(TERM_DOC.read_text())
    if not FIXTURE_DIR.is_dir():
        print(f"ERROR: fixture dir {FIXTURE_DIR} missing", file=sys.stderr)
        return 2
    present = {p.stem for p in FIXTURE_DIR.glob("*.jsonld")}
    missing = sorted(required - present)
    extra = sorted(present - required)
    print(f"vocab audit — required: {len(required)} present: {len(present)}")
    if missing:
        print(f"\nMISSING ({len(missing)}):")
        for m in missing:
            print(f"  {m}.jsonld")
    if extra:
        print(f"\nEXTRA fixtures (not declared in term reference; ok if intentional): {len(extra)}")
    return 1 if missing else 0

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it and observe failures (no fixtures yet)**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
mkdir -p fixtures/v0.2
python3 tools/vocab_audit.py
```

Expected: Exit 1; lists every fixture from the term-reference `Required fixtures` column as missing.

- [x] **Step 3: Commit the audit tool**

```bash
git add tools/vocab_audit.py fixtures/v0.2/.gitkeep || git add tools/vocab_audit.py
mkdir -p fixtures/v0.2 && touch fixtures/v0.2/.gitkeep
git add fixtures/v0.2/.gitkeep
git commit -m "build(rkaf): add vocab_audit.py — enforces fixture coverage from term reference"
```

## Task 14: Author the v0.2 fixture set

**Files:**
- Create: every file under `fixtures/v0.2/*.jsonld` named in the term-reference table

There are ~25 fixtures named in the term reference (Task 4 step 2). Each is a small JSON-LD file. The Edit/Write tool produces them one per step; this task batches them by primitive group.

- [x] **Step 1: Write the four Artifact + SourceFragment fixtures**

Create `fixtures/v0.2/artifact-eli-positive.jsonld`:

```json
{
  "@context": "../../context/rkaf-context-v0.2.jsonld",
  "@id": "https://rulespec.org/fixtures/v0.2/artifact-eli-positive#a1",
  "@type": "rkaf:Artifact",
  "rkaf:hasArtifactIdentifier": "http://data.europa.eu/eli/dir/2016/680/oj",
  "rkaf:artifactIdentifierScheme": "rkaf:eli"
}
```

Create `fixtures/v0.2/artifact-doi-positive.jsonld`:

```json
{
  "@context": "../../context/rkaf-context-v0.2.jsonld",
  "@id": "https://rulespec.org/fixtures/v0.2/artifact-doi-positive#a1",
  "@type": "rkaf:Artifact",
  "rkaf:hasArtifactIdentifier": "doi:10.1038/s41586-020-2649-2",
  "rkaf:artifactIdentifierScheme": "rkaf:doi"
}
```

Create `fixtures/v0.2/artifact-cid-positive.jsonld`:

```json
{
  "@context": "../../context/rkaf-context-v0.2.jsonld",
  "@id": "https://rulespec.org/fixtures/v0.2/artifact-cid-positive#a1",
  "@type": "rkaf:Artifact",
  "rkaf:hasArtifactIdentifier": "ipfs://bafybeigdyrztmdklm5wvtfa3kxkqx6vbxlikwwykqcjvmprxjcxz5jwlne",
  "rkaf:artifactIdentifierScheme": "rkaf:cid"
}
```

Create `fixtures/v0.2/sourcefragment-oa-textquote-positive.jsonld`:

```json
{
  "@context": "../../context/rkaf-context-v0.2.jsonld",
  "@graph": [
    {
      "@id": "urn:rkaf:fixture:sf-oa-tq:artifact",
      "@type": "rkaf:Artifact",
      "rkaf:hasArtifactIdentifier": "doi:10.1038/s41586-020-2649-2",
      "rkaf:artifactIdentifierScheme": "rkaf:doi"
    },
    {
      "@id": "urn:rkaf:fixture:sf-oa-tq:fragment",
      "@type": "rkaf:SourceFragment",
      "rkaf:bindsArtifact": "urn:rkaf:fixture:sf-oa-tq:artifact",
      "rkaf:hasSelector": {
        "@type": "oa:TextQuoteSelector",
        "oa:exact": "the substrate is dependency-inverted"
      },
      "rkaf:selectorKind": "oa:TextQuoteSelector"
    }
  ]
}
```

Create `fixtures/v0.2/sourcefragment-oa-xpath-positive.jsonld`, `fixtures/v0.2/sourcefragment-aknt-eid-positive.jsonld`, `fixtures/v0.2/sourcefragment-uslm-section-positive.jsonld` analogously, varying selectorKind to `oa:XPathSelector`, `rkaf:aknt-eId`, `rkaf:uslm-section` respectively, with appropriate selector payloads.

- [x] **Step 2: Write the four EvidenceBinding fixtures**

`fixtures/v0.2/evidencebinding-positive.jsonld` — EB binding an Assertion to a SourceFragment.
`fixtures/v0.2/evidencebinding-no-evidence-reason-positive.jsonld` — EB with `noEvidenceReason: rkaf:axiomatic` and an Assertion whose `safetyLabel` permits axiomatic evidence.
`fixtures/v0.2/evidencebinding-missing-negative.jsonld` — EB with neither bindsSourceFragment nor noEvidenceReason; SHACL MUST report a violation.

(Use the same JSON-LD pattern: `@graph` list of typed nodes, `@context` pointing at relative `../../context/rkaf-context-v0.2.jsonld`.)

- [x] **Step 3: Write Warrant fixtures**

`fixtures/v0.2/warrant-legal-positive.jsonld` — Warrant with `warrantKind: rkaf:statutory`, `warrantFamily: rkaf:legal`.
`fixtures/v0.2/warrant-scientific-positive.jsonld` — `warrantKind: rkaf:methodological`, `warrantFamily: rkaf:scientific`.
`fixtures/v0.2/warrant-cross-family-transition-positive.jsonld` — chain of two Warrants, `editorial → methodological` (different families); fixture expects SHACL to PASS but emit a warning surfaced via `sh:Warning` severity (or via Layer 2 constraint annotation in Plan 3).

- [x] **Step 4: Write ConfidenceRecord fixtures**

`fixtures/v0.2/confidencerecord-uncalibrated-positive.jsonld` — method=`model-inference`, calibrationStatus=`uncalibrated`, basis present, generatedBy present.
`fixtures/v0.2/confidencerecord-calibrated-positive.jsonld` — calibrationStatus=`calibratedAgainst`, evaluatedAgainst pointing at a corpus IRI.
`fixtures/v0.2/confidencerecord-score-theater-negative.jsonld` — bare score with no method, no basis, no calibrationStatus; SHACL MUST report violation.

- [x] **Step 5: Write AccessScope fixtures**

`fixtures/v0.2/accessscope-public-positive.jsonld` — kind=`public`.
`fixtures/v0.2/accessscope-organizationVisible-positive.jsonld` — kind=`organizationVisible`.
`fixtures/v0.2/accessscope-leak-negative.jsonld` — `accessScopeKind: rkaf:regulatoryRestricted` without `regulatoryClass`; SHACL MUST report violation.

- [x] **Step 6: Write AILineage fixtures**

`fixtures/v0.2/ailineage-positive.jsonld` — full AILineage with humanApprover IRI present.
`fixtures/v0.2/ailineage-missing-approver-negative.jsonld` — AILineage missing `humanApprover`; SHACL MUST report violation.

- [x] **Step 7: Write the remaining Studio-promotion fixtures**

`fixtures/v0.2/retentionpolicy-positive.jsonld` — full RetentionPolicy.
`fixtures/v0.2/mappingstate-positive.jsonld` — node carrying `rkaf:mappingState: rkaf:mapsToWos`.
`fixtures/v0.2/workspace-positive.jsonld` — Workspace with workspaceId.

- [x] **Step 8: Run the vocab audit — should now PASS**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 tools/vocab_audit.py
```

Expected: Exit 0. "MISSING" section absent.

- [x] **Step 9: Commit the fixture set**

```bash
git add fixtures/v0.2/
git commit -m "spec(rkaf): add v0.2 fixture set (Artifact, SourceFragment, EvidenceBinding, Warrant, Confidence, AccessScope, AILineage, RetentionPolicy, MappingState, Workspace)"
```

## Task 15: Extend `tools/ci_validate.py` with a v0.2 mode

**Files:**
- Modify: `tools/ci_validate.py`

- [ ] **Step 1: Add a `v02` mode entry to `MODES`**

In `tools/ci_validate.py`, add a new dict entry under `MODES`:

```python
"v02": {
    "label": "Rulespec Vocabulary v0.2 (full)",
    "shapes": [
        "shapes/rkaf-shapes-core-v0.2.ttl",
        "shapes/rkaf-shapes-warrant-v0.2.ttl",
        "shapes/rkaf-shapes-confidence-v0.2.ttl",
        "shapes/rkaf-shapes-accessscope-v0.2.ttl",
        "shapes/rkaf-shapes-studio-promotions-v0.2.ttl",
        "shapes/rkaf-shapes-conceptregistry-v0.2.ttl",
        # v0.1 inherited shapes still load Assertion/Authority/Lifecycle/Justification:
        "shapes/rkaf-shapes-core-v0.1.ttl",
        "shapes/rkaf-shapes-conceptregistry-v0.1.ttl",
        "shapes/rkaf-shapes-lifecycle-v0.1.ttl",
        "shapes/rkaf-shapes-justification-v0.1.ttl",
    ],
    "expected": {
        # Each v0.2 fixture is its own slug; expected ranges are loose to start.
        # Tighten after first successful run.
        "v0.2/artifact-eli-positive":                   {"triples": (1, 50)},
        "v0.2/artifact-doi-positive":                   {"triples": (1, 50)},
        "v0.2/artifact-cid-positive":                   {"triples": (1, 50)},
        "v0.2/sourcefragment-oa-textquote-positive":    {"triples": (1, 50)},
        "v0.2/sourcefragment-oa-xpath-positive":        {"triples": (1, 50)},
        "v0.2/sourcefragment-aknt-eid-positive":        {"triples": (1, 50)},
        "v0.2/sourcefragment-uslm-section-positive":    {"triples": (1, 50)},
        "v0.2/evidencebinding-positive":                {"triples": (1, 50)},
        "v0.2/evidencebinding-no-evidence-reason-positive": {"triples": (1, 50)},
        "v0.2/warrant-legal-positive":                  {"triples": (1, 50)},
        "v0.2/warrant-scientific-positive":             {"triples": (1, 50)},
        "v0.2/warrant-cross-family-transition-positive":{"triples": (1, 50)},
        "v0.2/confidencerecord-uncalibrated-positive":  {"triples": (1, 50)},
        "v0.2/confidencerecord-calibrated-positive":    {"triples": (1, 50)},
        "v0.2/accessscope-public-positive":             {"triples": (1, 50)},
        "v0.2/accessscope-organizationVisible-positive":{"triples": (1, 50)},
        "v0.2/ailineage-positive":                      {"triples": (1, 50)},
        "v0.2/retentionpolicy-positive":                {"triples": (1, 50)},
        "v0.2/mappingstate-positive":                   {"triples": (1, 50)},
        "v0.2/workspace-positive":                      {"triples": (1, 50)},
    },
    "expected_total_triples_label": "(loose initial ranges; tighten after first PASS)",
    # NEGATIVE fixtures are validated separately — see Task 16.
},
```

- [ ] **Step 2: Run the validator with `--mode v02`**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 tools/ci_validate.py --mode v02
```

Expected: All positive fixtures PASS (zero violations). Triple counts populate; tighten the ranges in a follow-up commit if drift warnings appear.

- [ ] **Step 3: Commit**

```bash
git add tools/ci_validate.py
git commit -m "build(rkaf): extend ci_validate.py with v02 mode covering v0.2 vocab + Studio promotions"
```

## Task 16: Author negative-fixture validator wrapper

**Files:**
- Create: `tools/validate_negatives.py`

Negative fixtures must FAIL SHACL validation by design; `ci_validate.py` is built around the positive-PASS contract. This is a sibling tool that asserts `violations > 0` for each negative fixture.

- [x] **Step 1: Write the wrapper**

```python
#!/usr/bin/env python3
"""Negative-fixture validator. Asserts each named fixture FAILS SHACL validation
on the v0.2 shape set (i.e., yields ≥1 violation). Used by Layer 2 conformance.

Exit codes:
  0  every negative fixture produced ≥1 violation as expected
  1  one or more negative fixtures unexpectedly PASSED
  2  setup error
"""
import sys
from pathlib import Path
import rdflib
from pyshacl import validate

ROOT = Path(__file__).resolve().parent.parent
SHAPES = [
    "shapes/rkaf-shapes-core-v0.2.ttl",
    "shapes/rkaf-shapes-warrant-v0.2.ttl",
    "shapes/rkaf-shapes-confidence-v0.2.ttl",
    "shapes/rkaf-shapes-accessscope-v0.2.ttl",
    "shapes/rkaf-shapes-studio-promotions-v0.2.ttl",
    "shapes/rkaf-shapes-conceptregistry-v0.2.ttl",
    "shapes/rkaf-shapes-core-v0.1.ttl",
    "shapes/rkaf-shapes-conceptregistry-v0.1.ttl",
    "shapes/rkaf-shapes-lifecycle-v0.1.ttl",
    "shapes/rkaf-shapes-justification-v0.1.ttl",
]
NEGATIVES = [
    "fixtures/v0.2/evidencebinding-missing-negative.jsonld",
    "fixtures/v0.2/confidencerecord-score-theater-negative.jsonld",
    "fixtures/v0.2/accessscope-leak-negative.jsonld",
    "fixtures/v0.2/ailineage-missing-approver-negative.jsonld",
]

def main() -> int:
    shapes_g = rdflib.Graph()
    for s in SHAPES:
        shapes_g.parse(str(ROOT / s), format="turtle")
    failed = 0
    for fx in NEGATIVES:
        data = rdflib.Graph()
        data.parse(str(ROOT / fx), format="json-ld")
        conforms, _, _ = validate(data_graph=data, shacl_graph=shapes_g,
                                  inference="rdfs", advanced=True, meta_shacl=False)
        status = "FAIL-AS-EXPECTED" if not conforms else "UNEXPECTED-PASS"
        print(f"  [{status}] {fx}")
        if conforms:
            failed += 1
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
```

- [x] **Step 2: Run it**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 tools/validate_negatives.py
```

Expected: All four lines report `FAIL-AS-EXPECTED`. Exit 0.

- [x] **Step 3: Commit**

```bash
git add tools/validate_negatives.py
git commit -m "build(rkaf): add validate_negatives.py — asserts negative fixtures fail SHACL as designed"
```

## Task 17: Ratify the v0.2 vocabulary release in CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

- [x] **Step 1: Append a v0.2 entry**

At the top of `CHANGELOG.md`, above the rename entry from plan 1, add:

```markdown
## v0.2.0-pre.2 — Vocabulary v0.2

**Vocabulary Layer 1 lands. Pre-release; CHANGELOG-driven; no compatibility with v0.1.x.**

### New first-class primitives (§§4.1-4.6 of `spec/rkaf-core-v0.2.md`)
- `rkaf:Artifact` with `artifactIdentifierScheme` closed enum (eli, eli-dl, eli-i, uslm, aknt-eId, doi, isbn, issn, cid, hash-sha256, urn-persistent, partner-defined).
- `rkaf:SourceFragment` composing the W3C Web Annotation (`oa:`) selector vocabulary plus domain-specific selectors (Akoma Ntoso eId, USLM section, ELI fragment, JSONPath, DOI fragment).
- `rkaf:EvidenceBinding` with the operational-validity invariant (≥1 source fragment OR a permitted noEvidenceReason).
- `rkaf:Warrant` as the universal grounding primitive; `rkaf:Authority` preserved as the legal-family specialization. Six warrant families: legal, scientific, editorial, cryptographic, social, source-class.
- `rkaf:ConfidenceRecord` with calibrationStatus + basis + generatedBy required (rejects "score theater").
- `rkaf:AccessScope` with seven kinds plus DPV/ODRL alignment for regulatory and rights cases.

### Studio-derived promotions (§5)
- `rkaf:MappingState` (closed four-value enum).
- `rkaf:RetentionPolicy` with retentionTrigger and retentionPostExpiry closed enums.
- `rkaf:AILineage` with mandatory humanApprover.
- `rkaf:llmHint` annotation property (carried through the JSON Schema projector as `x-rkaf-llmHint`).
- `rkaf:Workspace` scoping with workspaceId + workspaceTrustList.
- `rkaf:projectsTo` (generalizes Studio's wosTarget).

### Public ontology composition (§9)
Imports: PROV-O, OA, SKOS, JSON-LD, SHACL, RDF/RDFS/XSD.
Alignments: ELI / ELI-DL / ELI-I, RRMV, Akoma Ntoso, USLM, LegalRuleML, ECO/SEPIO, Nanopublications, ODRL, DPV, DCTERMS, CiTO, Schema.org/Legislation, DCAT/VoID.
Projections (carried by Layer 4 projectors, Plan 5): JSON Schema, JSON-LD, OpenAPI 3.1.

### Shape files (compiled SHACL targets — not source of truth per Layer 2 plan)
- `shapes/rkaf-shapes-core-v0.2.ttl` (umbrella)
- `shapes/rkaf-shapes-warrant-v0.2.ttl`
- `shapes/rkaf-shapes-confidence-v0.2.ttl`
- `shapes/rkaf-shapes-accessscope-v0.2.ttl`
- `shapes/rkaf-shapes-studio-promotions-v0.2.ttl`
- `shapes/rkaf-shapes-conceptregistry-v0.2.ttl`

### Tooling
- `tools/vocab_audit.py` — fails build if a v0.2 term has no fixture.
- `tools/validate_negatives.py` — asserts negative fixtures FAIL as designed.
- `tools/ci_validate.py --mode v02` — full v0.2 positive-fixture validation.

### Compatibility
None with v0.1.x. v0.2 supersedes wholesale.
```

- [x] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(rkaf): CHANGELOG v0.2.0-pre.2 — Vocabulary Layer 1"
```

## Self-review

- [x] Every primitive in source spec §§5.5-5.8 has a class definition in `spec/rkaf-core-v0.2.md`, a SHACL shape, a JSON-LD context entry, and ≥1 positive + ≥1 negative fixture (`vocab_audit.py` enforces).
- [x] Every Studio-derived promotion in source spec Appendix A is either in universal Vocabulary (§5 of v0.2 spec) OR explicitly placed in the Studio profile per §5.2 (Studio profile lives in plan 10; the Vocabulary spec's §5 carries only the generalized promotions).
- [x] §9 ontology table matches source spec §5.9 — every row present (PROV-O, OA, SKOS, ELI/ELI-DL/ELI-I, RRMV, Akoma Ntoso, USLM, LegalRuleML, ECO/SEPIO, DPV, ODRL, DCTERMS, CiTO, Schema.org/Legislation, Nanopublications, DCAT/VoID, plus carrier-format projection rows).
- [x] Closed taxonomies (`warrantKind`, `warrantFamily`, `accessScopeKind`, `confidenceMethod`, `calibrationStatus`, `mappingState`, `retentionTrigger`, `retentionPostExpiry`, `noEvidenceReason`, `assertionOrigin`, `safetyLabel`, `usageEligibility`) are enumerated literally in both the spec body and the SHACL `sh:in` constraints.
- [x] No constraint uses `sh:if` / `sh:then` (per Appendix C of source spec) — all conditional shapes use Pattern C (`sh:or` with `sh:not`).
- [ ] `tools/ci_validate.py --mode v02` exits 0 with all positive fixtures PASS.
- [x] `tools/validate_negatives.py` exits 0 with all four negative fixtures FAIL-AS-EXPECTED.
- [x] `tools/vocab_audit.py` exits 0 (every required fixture present).
- [x] CHANGELOG entry for v0.2.0-pre.2 lands.
- [x] `tools/rename_audit.py` still exits 0 (no `pkaf:`/`PKAF` strings introduced).
