# Rulespec Core — Vocabulary v0.2

**Status:** Pre-release, normative.
**Supersedes:** `archive/v0.1/spec/rkaf-core-v0.1.md` (historical, retained for archival reference only).
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

**Projected edges and reified assertions [Normative].** The same edge can be
stated twice: once as a direct predicate on a node — `rkaf:hasDocket` on a
`rkaf:Proceeding`, `rkaf:publishedInProceeding` on an `rkaf:Artifact` — and
once as a `rkaf:RelationshipAssertion` whose subject, predicate, and object are
that same triple. The two are not competing designs and neither is deprecated.
They have fixed and different roles:

- A **direct edge is the queryable projection.** It is what a consumer that
  does not reason over assertions can traverse, and it carries no provenance,
  no polarity, no confidence, and no consumer disposition.
- A **`rkaf:RelationshipAssertion` is the provenance-bearing source of truth.**
  It carries the origin, the evidence, the claimant, the extraction run, the
  attestations, and the polarity, and it is the record every other primitive
  keyed to an assertion IRI points at.

Where both are present in one graph and the direct edge's subject, predicate,
and object equal an assertion's `rkaf:assertsSubject`,
`rkaf:assertsPredicate`, and `rkaf:assertsObject`, the direct edge IS the
projection of that assertion. A consumer MUST treat the pair as ONE statement —
the edge derived from the assertion — and MUST NOT count it twice, aggregate it
twice, or read the redundancy as two independent sources agreeing. This is the
deduplication rule; it is what makes emitting both safe.

A producer emitting a `rkaf:affirmed` assertion whose triple a profile predicate
can express SHOULD also emit that direct edge. The projection is what makes the
fact reachable to a consumer that has not adopted the assertion model, and the
deduplication rule above is what makes the redundancy free.

A producer MUST NOT emit the direct edge for a `rkaf:denied` assertion, for an
assertion it has superseded, or for one whose attestations retract it. A plain
edge carries no polarity and no disposition, so projecting a denial asserts its
opposite, and projecting a retracted claim asserts a claim the producer has
withdrawn. A graph containing a direct edge that a co-present assertion denies
is non-conforming; the assertion is the source of truth and the edge is the
error.

A direct edge with no matching assertion in the graph is legal and common. It
is a statement the producer makes on its own account with no provenance record
attached. A consumer that requires provenance MUST treat such an edge as
unbacked — it MUST NOT assume an assertion exists elsewhere, and it MUST NOT
manufacture one.

None of this is mechanically checked, and it cannot be: no shape can require a
producer to project an edge it chose not to project, and matching a direct
predicate against a reified triple means comparing a predicate IRI to a
property VALUE, which SHACL does not express. These are producer obligations
and consumer rules, in the same class as §4.7.3 rule 3.

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

The value object is therefore CLOSED, and closure — not merely the absence of
`@language` from the required members — is what every compiled target
enforces: `additionalProperties: false` in JSON Schema, `deny_unknown_fields`
on the Rust `crate::TypedLiteral`, and in TypeScript both halves of what that
language can express — every JSON-LD value-object member the source does not
declare is typed `never`, which is what rejects `@language` on a value the
compiler has already widened, and the generated validator rejects any member
outside the declared set, which is what catches a member TypeScript's
structural typing cannot forbid. SHACL needs no separate rule: a
language-tagged literal arrives with the datatype gone, so no `sh:datatype`
alternative matches it.

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
`rkaf:importedRecord`), `rkaf:extractionRun`, `rkaf:extractedBy`, and
`rkaf:extractorVersion`.

When `rkaf:extractionMethod` is `rkaf:modelExtraction`, two further properties
are REQUIRED: `rkaf:extractionModelRef` and `rkaf:requestContractDigest`. A
record that says a model produced a candidate while leaving the model unnamed
is not provenance, and a model call whose contract is unnamed cannot be checked
against the contract a consumer audited.

`rkaf:requestContractDigest` is REQUIRED for `rkaf:modelExtraction` and
OPTIONAL for the other four methods, because the field presumes a
REQUEST-SHAPED extraction: a run that sent instructions, a schema, and a
configuration somewhere and received an answer. A deterministic table parse
sends nothing and has no such contract. Requiring the digest universally left a
producer one conforming move — define an envelope, hash it, and cite the
result — which yields a real digest naming a contract the run never published.
An absent field is the honest record; a fabricated contract is not.

A producer using one of the other four methods MAY still supply the digest, and
SHOULD whenever the run genuinely issued a contract — a
`rkaf:ruleBasedExtraction` over a versioned, published ruleset is the common
case. When present, under any method, `rkaf:requestContractDigest` MUST be a
lowercase `sha256:<64 hex>` digest of the complete, secret-free request
contract — instructions, schema, model configuration, and input payload hashed
together — and it MUST name a contract the run actually issued. One digest,
because the question a consumer asks is whether a candidate came from the
contract they audited, and that question has a single answer only if the whole
contract is covered. Schema descriptions and LLM hints are part of the
contract; they do not substitute for it. A digest over an envelope minted to
satisfy the field is non-conforming.

Consumers MUST NOT read an absent `rkaf:requestContractDigest` as an unaudited
run. Absence under a non-model method means the run had no request contract to
name; what it did consume is recorded by `rkaf:inputDigest`,
`rkaf:extractedBy`, and `rkaf:extractorVersion`, which are the reproduction
handles for a deterministic method.

`rkaf:ExtractionActivity` MUST NOT require a human approver, and the kernel
declares none. An unreviewed model candidate is representable exactly as it
is: an extraction happened, and no `rkaf:Attestation` targets it yet. Asking a
model to review its own answer produces another opinion, not an approval.

Provider neutrality is structural. Every `rkaf:ExtractionActivity` field is a
Rulespec-owned IRI, a version string, or an opaque digest. No provider request
object, response object, SDK type, billing record, or configuration blob
appears in the kernel or is referenced by a kernel shape.

**Model derivation lineage.** `rkaf:AILineage` (§5.3) is NOT duplicated by
`rkaf:ExtractionActivity`. It records the model derivation — model id, version,
prompt template, temperature, seed, input context hash — and remains REQUIRED
for AI-touched `rkaf:assertionOrigin` values. `rkaf:ExtractionActivity` may
link it via `rkaf:hasAILineage` when both exist; the two fields
`rkaf:extractionModelRef` and `rkaf:extractionPromptRef` are opaque references
for a run that may never be reviewed, not a second lineage record.

`rkaf:AILineage` MUST NOT require a human approver, and as of v0.2
`rkaf:humanApprover` is OPTIONAL (0..1). An AI-touched assertion still MUST
carry `rkaf:hasAILineage`; that requirement is satisfied by an approver-free
lineage. An unreviewed model candidate is therefore representable exactly as it
is — a model produced it, and no `rkaf:Attestation` targets it yet.

> **Resolved.** Earlier drafts of this section recorded an open conflict:
> `rkaf:AILineage` required `rkaf:humanApprover` while the AI-touched
> `rkaf:assertionOrigin` values — including `rkaf:aiSuggested`, whose entire
> meaning is *unreviewed candidate* — required `rkaf:hasAILineage`. Together
> they forced an approver onto an unreviewed candidate, so the only way to
> record an honest candidate was to invent a reviewer. The contract is
> unreleased and the target architecture is canonical, so the requirement was
> removed rather than documented. `rkaf:humanApprover` is now optional, and
> approval is where it always belonged: an `rkaf:Attestation` whose
> `rkaf:targets` includes the assertion.
>
> The lineage shape still refuses a review attributed to nobody. When
> `rkaf:humanRationale` is present — a human's stated reason for accepting the
> output — `rkaf:humanApprover` is REQUIRED. A rationale with no approver reads
> as approved while naming no one accountable, which is worse than an
> unreviewed candidate.
>
> Two negative fixtures were affected. `fixtures/negatives/`
> `a-i-lineage-missing-human-approver-negative.jsonld` keeps its verdict and its
> name: it states a `rkaf:humanRationale`, so it now fails the rule above.
> `fixtures/ailineage-missing-approver-negative.jsonld` no longer describes a
> defect and was replaced by
> `fixtures/ailineage-malformed-input-context-hash-negative.jsonld`, which
> catches one that is still real — an input-context hash that is not a digest.
> No coverage was dropped.

**Human approval.** Approval has no dedicated contract because
`rkaf:Attestation` (§3.1) already is one: it carries the attestor, the attestor
kind, the decision, the scope, the time, the optional effective period, and the
revocation marker. Minting a parallel approval record would create two places
to look for the same fact. A reviewer approving an extraction records an
`rkaf:Attestation` whose `rkaf:targets` includes the assertion IRI.

**Deterministic origin.** `rkaf:assertionOrigin` gains one v0.2 value:
`rkaf:deterministicExtraction`. It means the record was produced by a
deterministic parser or join over identified inputs — a mechanically
reproducible derivation, NOT an interpretive judgment. Re-running the named
run over the same inputs MUST yield the same proposition; nothing about the
record is a claim that anyone read the source and decided anything.

The value is therefore not `rkaf:humanAsserted` with a machine in the loop, and
it is not any AI-touched value: it carries no `rkaf:hasAILineage` requirement,
and the §3.5 inverse rule applies to it — a deterministic-origin assertion MUST
NOT carry `rkaf:hasAILineage`, because there is no model derivation to record.

`rkaf:hasExtractionProvenance` is REQUIRED when the origin is
`rkaf:deterministicExtraction`, and the requirement is mechanical on every
compiled target. A claim of reproducibility that names no run is not one: the
`rkaf:ExtractionActivity` is what carries the method, the run, the extractor,
its version, and the input digests a consumer needs to reproduce the result.
Without the requirement the method would sit on an optional edge that a
provenance-stripping projection could drop with no gate noticing — which is
exactly what happened when a producer with no deterministic value available
claimed `rkaf:imported` and demoted its real method to that edge.

The referenced activity's `rkaf:extractionMethod` MUST be
`rkaf:deterministicParse` or `rkaf:ruleBasedExtraction`. This one is a producer
obligation rather than a mechanical check, for the same reason §4.7.3 rule 3
is: the activity may legally live in another document, so no shape can require
agreement it cannot see. A record claiming a deterministic origin over a
`rkaf:modelExtraction` or `rkaf:humanExtraction` run is non-conforming.

`rkaf:imported` keeps its own meaning and is not deprecated: it says a record
was re-serialized from another system's published records, which is a statement
about where the record came from and not about how the proposition was derived.
A producer re-publishing someone else's table uses `rkaf:imported`; a producer
deriving propositions from source text or source tables by fixed rule uses
`rkaf:deterministicExtraction`.

**Derivation.** `prov:wasDerivedFrom` (0..*) records what a record was derived
from. Its object is not a bare IRI: the declared range is `prov:Entity`
(`constraints/semantics/l0-ranges.cue`), and every compiled shape that carries
the edge enforces it with `sh:class prov:Entity` —
`compiled/shacl/core/assertion.ttl`, `relationship-assertion.ttl`, and
`concept-assignment.ttl` all do.

At L1–L4, where the unit of validation is a graph, a producer citing a
derivation source MUST therefore materialize that source as a node typed
`prov:Entity` in the same document. An IRI that is described nowhere is legal —
a cross-document reference does not require the graph to inline the world — but
an IRI described in the document under some OTHER type, or a document that
names its derivation sources and describes none of them while the shape can see
them, does not conform. The typed node is the whole requirement; it may carry
nothing but its `@id` and `@type`.

The rule is stated here because it is otherwise undiscoverable from prose. This
section formerly presented `prov:wasDerivedFrom` as an IRI list and left the
class to the compiled SHACL, which is where the one authoring failure in the
2026-07-28 single-document consumer projection landed — six `sh:class
prov:Entity` violations, all mechanical, none predictable from the spec. The
same class discipline applies wherever the edge appears: `rkaf:CommentPeriod`
and `rkaf:AgendaProceedingRelationship` require it 1..* rather than 0..*
(`spec/rkaf-rulemaking.md` §4, §2.2), and the range is the same.

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
- `rkaf:coordinateSystem` (§4.2)
- `rkaf:assignmentSubjectType`, `rkaf:assignmentRole`, and
  `rkaf:assignmentDerivation` (§4.7)

The experimental US rulemaking module adds
`rkaf:proceedingIdentifierScheme`, `rkaf:docketIdentifierScheme`, and
`rkaf:proceedingStage`; see `spec/rkaf-rulemaking.md`. Their values follow the
same release-bound closed-taxonomy discipline.

`rkaf:assertionOrigin` is the one inherited enum v0.2 EXTENDS. It gains
`rkaf:deterministicExtraction` (§2.4) and loses nothing; the six v0.1 values
keep their meanings. The addition is breaking for consumers under §3's
reject-unrecognized-values rule, which is why it lands before the first
release rather than after it.

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
  `rkaf:hash-sha256`, `rkaf:urn-persistent`, `rkaf:formspec-need`,
  `rkaf:partner-defined`.

An Artifact identifier MUST resolve to, or be derived from, one immutable
edition, publication, snapshot, or content payload. Examples include a
content hash, an edition-scoped GovInfo package or granule URL, a permanent
Federal Register document URL, and a producer-scoped snapshot URN. A current
eCFR URL, an unversioned U.S. Code locator, or a citation such as “40 CFR
60.1” does not establish Artifact identity.

**Formspec Need identity.** `rkaf:formspec-need` names a Formspec Needs
Document `url` plus `need.id` pair — `<docUrl>#<needId>`, with an OPTIONAL
`@<revision>` suffix. A Formspec Need carries an integer `revision` covering
its statement and its grounding: an assertion pinning the wording it saw uses
the suffixed form, one tracking the Need as currently worded omits it.

The value exists to buy one edge Formspec cannot reach from its own side. A
Need already cites a Rulespec assertion as evidence that the need is
legitimate; registering the scheme makes the reverse direction first-class, so
a compliance finding, an adopted policy position, or a regulator's
determination can name the product commitment it is about. Without the value
the same citation is expressible under `rkaf:partner-defined`, but a Need
citation is then indistinguishable from any other partner URI in federation
queries — which is the whole cost of not registering it.

The scheme tag is a declaration of the grammar the producer is claiming, not a
mechanical check on it. A bare Needs Document URL is a current-state URL, the
class this section rejects for eCFR; the `#<needId>@<revision>` form is what
makes the identifier an edition rather than a live page, and a producer
asserting the scheme over a bare document URL is non-conforming. The kernel
does NOT close a grammar over the value: `rkaf:hasArtifactIdentifier` and
`rkaf:artifactIdentifierScheme` are both 1..*, so no positional
correspondence exists between an identifier and a scheme, and the per-scheme
grammar idiom is available only where the pair is scalar — as it is for the US
regulatory identifiers in `spec/rkaf-rulemaking.md` §5.2. This is the same
producer-obligation posture as §4.7.3 rule 3 and the `rkaf:extractionMethod`
agreement in §2.4: a shape cannot require what it cannot see.

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
  type. Because the stable resource is owned by whichever public model applies,
  `dcterms:isVersionOf` carries NO Rulespec class range — declaring one would
  be the Work class this paragraph declines to mint.
- `prov:wasRevisionOf` (0..*) links a later Artifact to the exact earlier
  Artifact from which it derives substantial content. Every referenced
  revision MUST identify an immutable source state; the range is
  `rkaf:Artifact`.
- `dcterms:hasFormat` and `dcterms:isFormatOf` remain the relations for
  substantially identical content in another format or registry posting. They
  are NOT version relations — two renderings of the same state are the same
  state — so neither carries the evidence requirement below.

Producers MUST NOT infer either version relation from a shared title, topic,
identifier fragment, embedding score, or retrieval rank. A legal profile
SHOULD use ELI's native LegalResource and LegalExpression relations when ELI
owns the resource model. Publication, effective, and observation times remain
separate profile or provenance properties; a revision link alone establishes
no legal effect.

That prohibition is mechanically enforced, because a prohibition a schema
cannot check is a prohibition producers discover only in review:

- An Artifact declaring `dcterms:isVersionOf` or `prov:wasRevisionOf` MUST
  carry `rkaf:versionLineageEvidence` (1..*), naming the `rkaf:SourceFragment`
  regions that STATE the relation — a masthead line, an amendment note, a
  registry supersession field.
- An Artifact carrying `rkaf:versionLineageEvidence` MUST carry
  `rkaf:hasContentDigest` (1), a lowercase `sha256:<64 hex>` digest of the
  immutable state it names.

Neither rule asserts that a lineage claim is TRUE. Together they make it
CHECKABLE: the claim resolves to exact coordinates in an actual source, and the
state that carries it is addressable by content. A similarity score has neither
property, which is precisely why it cannot satisfy the rules.

`rkaf:hasContentDigest` is otherwise OPTIONAL (0..1). Any Artifact used as
comparison evidence MUST resolve to one immutable source state AND a content
digest; a consumer performing comparison rejects an Artifact that carries
neither.

`rkaf:Proceeding` and `rkaf:Docket` have distinct identity predicates in the
experimental rulemaking module. Neither class reuses Artifact identity.
`rkaf:uslm-section` remains a selector for substructure inside USLM markup; it
is distinct from the U.S. Code citation identity defined by the rulemaking
profile.

### 4.2 SourceFragment

**rkaf:SourceFragment** — an addressable region within an Artifact. `rkaf:SourceFragment rdfs:subClassOf oa:SpecificResource` (W3C Web Annotation Ontology 1.0 — §9.1 Cohort A alignment).

Fragment identity is the three REQUIRED bindings below taken together. Drop any
one and the record stops naming a region:

| Binding | Property | Answers |
| --- | --- | --- |
| Artifact | `oa:hasSource` | Which document |
| Selector | `oa:hasSelector` | Which region of it |
| Selector kind | `rkaf:selectorKind` | How to read that region |

A fourth binding is required by the selector rather than by the fragment:
`rkaf:coordinateSystem` (1) lives on the offset-bearing selector, never on the
fragment — see **Selector contracts** below for why, and for the rule that binds
a declared `rkaf:selectorKind` to a selector of that type so the requirement
cannot be evaded by leaving the selector node untyped.

The **state binding**, `rkaf:sourceArtifactDigest`, is RECOMMENDED in general
and REQUIRED for any fragment used as comparison evidence or as evidence for an
accepted assertion. This mirrors §4.1's treatment of `rkaf:hasContentDigest` on
the Artifact: identity says WHICH document region, state says which BYTES that
region was read from, and only a consumer performing comparison needs both.

Required properties:
- `oa:hasSource` (1) — the parent Artifact IRI, as an absolute IRI. OA canonical predicate for the source resource in a SpecificResource pattern. Its range is `rkaf:Artifact`: a fragment of a workspace, a proceeding, or an actor addresses no document region at all.
- `oa:hasSelector` (1..*) — at least one selector object. OA canonical predicate.
- `rkaf:selectorKind` (1..*) — closed enum declaring the selector type(s):
  - Foundational (W3C Web Annotation Ontology — `oa:`): `oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`.
  - Domain selectors: `rkaf:aknt-eId`, `rkaf:uslm-section`, `rkaf:eli-fragment`, `rkaf:jsonpath`, `rkaf:doi-fragment`, `rkaf:partner-defined`.

Optional properties (shape cardinality; see the state-binding rule above for
when a producer is nonetheless obliged to carry them):
- `rkaf:sourceArtifactDigest` (0..1) — lowercase `sha256:<64 hex>` digest of the Artifact STATE the coordinates were taken against. RECOMMENDED on every fragment; REQUIRED on a fragment cited as comparison evidence or as evidence for an accepted assertion.
- `rkaf:fragmentContentDigest` (0..1) — the same lexical form, over the exact region text those coordinates select. RECOMMENDED.

The two digests answer different questions — "did the document change under me"
and "is this the text I quoted" — and the shape requires neither, because a
fragment recorded for navigation is not yet a fragment relied on. What makes
them matter is the reliance: an Artifact is immutable by definition, but nothing
stops a producer pointing `oa:hasSource` at an identifier whose backing bytes
were quietly replaced, and `rkaf:sourceArtifactDigest` makes that substitution
detectable rather than invisible. Neither digest is enforced by cardinality at
L1 or L3; the obligation is stated normatively here and belongs to the consumer
profile that accepts the assertion.

**Selector contracts.** Rulespec constrains two OA selector shapes and declines
L1/L3 constraints over the rest; producers conform to OA 1.0's own
domain/range.

- `oa:TextQuoteSelector` MUST carry `oa:exact` (xsd:string, the verbatim quoted text). `oa:prefix` and `oa:suffix` (xsd:string, surrounding context anchors) are OPTIONAL.
- `oa:TextPositionSelector` MUST carry `oa:start` and `oa:end` (xsd:integer, >= 0) and `rkaf:coordinateSystem` (1). `oa:start` MUST be less than or equal to `oa:end`; `start == end` is a legal insertion point, not an inverted range.

A fragment whose `rkaf:selectorKind` includes `oa:TextPositionSelector` MUST
attach at least one `oa:hasSelector` value that is typed `oa:TextPositionSelector`.
Without this rule the selector contract is opt-in: the offset and ordering
requirements fire only on a node the producer voluntarily typed, so a dangling
selector IRI, or an untyped node carrying `oa:start` and `oa:end` and no unit,
satisfied every target. The rule is scoped to the position selector because
that is the kind whose reproducibility Rulespec constrains; the remaining kinds
carry no Rulespec-side selector contract and MAY be attached as bare values.

**Validation-layer note.** L2 (shape) gates dispatch on the document root and
the members of a top-level `@graph`. A selector attached INLINE as a nested
object inside a fragment is therefore not an L2 target — L3 sees it either way,
because RDF has no notion of nesting. Producers whose consumers rely on the L2
gate SHOULD attach selectors by reference.

`rkaf:coordinateSystem` is the closed enum `rkaf:unicode-codepoint`,
`rkaf:utf8-byte`, `rkaf:utf16-code-unit`, `rkaf:xml-node-path`,
`rkaf:page-region`, `rkaf:partner-defined`. An offset without a declared unit is
not a coordinate: `4180` names three different positions depending on whether
the producer counted Unicode code points, UTF-8 bytes, or UTF-16 code units, and
the three disagree the moment the source contains a non-ASCII character — which
legal text, with its section symbols, dashes, and curly quotes, always does.

The unit is declared on the SELECTOR, not on the fragment, because it belongs to
whatever counts in it: a fragment carrying a quote selector and a position
selector has exactly one coordinate system, and it is the position selector's.

**Fragment identity schemes.** `rkaf:FragmentIdentityScheme` is the closed
two-value enum naming HOW a cited region is identified:

- `rkaf:published-fragment` — the cited IRI names a `rkaf:SourceFragment` node
  the producer publishes, and the identity bindings above are read off it. This
  is the form every other Rulespec record uses.
- `rkaf:carrier-local-fragment` — the cited IRI is a **carrier-local fragment
  URN** and carries the bindings itself.

The derived form exists because the published form was, for a tabular carrier,
a requirement to publish a table rather than a requirement to know anything. A
carrier that already stores an artifact identifier, a start offset, an end
offset, and a digest of the selected text holds every binding a fragment needs;
making it also maintain and join a fragments table before it may cite evidence
adds no information and blocked the term outright for carriers that will not
maintain one.

The URN is:

```text
urn:rkaf:fragment:<artifact>:<start>:<end>:sha256-<64 lowercase hex>
```

| Component | Content |
| --- | --- |
| `<artifact>` | The parent Artifact IRI, percent-encoded against the RFC 3986 unreserved set (`A-Za-z0-9-._~`) with UPPERCASE hex triplets — the encoding SPARQL's `ENCODE_FOR_URI` produces. |
| `<start>` | First Unicode code point of the region. Decimal, no leading zeroes. |
| `<end>` | One past the last. Decimal, no leading zeroes. |
| digest | SHA-256 over the UTF-8 bytes of the selected text. |

Four properties of the grammar are load-bearing:

1. **The interval is half-open `[start, end)`, counted in Unicode code
   points.** `start == end` is an insertion point, and two abutting regions
   share no code point. The unit is FIXED by the scheme rather than declared
   per value, because a derived identifier that left the unit to be guessed
   would reintroduce the exact instability `rkaf:coordinateSystem` exists to
   remove. `rkaf:selectorKind` is fixed to `oa:TextPositionSelector` for the
   same reason.
2. **The artifact component is percent-encoded.** Encoding is what keeps it a
   single unambiguous component inside a colon-delimited URN, and it is what
   makes the parent Artifact recoverable by a reader that dereferences nothing.
3. **The digest is spelled `sha256-`, not `sha256:`.** Same algorithm, same
   64 lowercase hex characters as every other Rulespec digest; the hyphen keeps
   the component from contributing a colon. Its SCOPE is the selected text —
   what `rkaf:fragmentContentDigest` covers — and not the Artifact.
4. **`rkaf:sourceArtifactDigest` is not carried.** The derived form pins the
   quoted text and not the document state around it, so a producer that needs
   the substitution check described above publishes a fragment node. This is
   the one binding the derived form gives up, and it is stated rather than
   quietly absent.

A carrier-local fragment URN DENOTES the `rkaf:SourceFragment` its components
describe; it does not name a different kind of thing. At L0 that is the whole
story, and no fragments carrier is required. At L1–L4 the unit of validation is
a GRAPH, so a graph that cites the URN materializes the node it denotes — an
expansion that is mechanical, introduces no fact the URN did not already carry,
and is shown end to end in
`fixtures/conceptassignment-carrier-local-fragment-positive.jsonld`.
`rkaf:CarrierLocalFragmentUrnSourceAgreementShape`
(`shapes/rkaf-shapes-core.ttl`) checks that the expansion is faithful for the
binding that matters most: a materialized fragment MUST carry the `oa:hasSource`
its own URN encodes. That the offsets and the digest also agree with the source
is a PRODUCER obligation — checking them needs the selected text, which
validation does not have — and it is stated here rather than implied.

Selector stability across Artifact revisions is a partner obligation. Supersession (§6.1, inherited) resolves fragment continuity. For ELI artifacts, ELI-I edges are the canonical fragment-continuity model.

A temporary processing segment — a bounded model input assembled from source
structure to fit a context window — is NOT a `rkaf:SourceFragment` unless it
corresponds to a stable, meaningful region. Segments may combine or overlap
regions and may produce proposals; every accepted assertion MUST still resolve
back to the actual fragments that support it. Rulespec does not define a
processing-segment class: segment policy, tokenizer, token counts, truncation
records, and retry lineage are producer-side operational records, reachable from
an assertion through `rkaf:ExtractionActivity` (§2.4).

### 4.3 EvidenceBinding

**rkaf:EvidenceBinding** — links an Assertion to one or more SourceFragments (or declares a permitted absence of source evidence).

Required properties:
- `rkaf:bindsAssertion` (1) — the assertion being bound.
- One of:
  - `rkaf:bindsSourceFragment` (1..*) — at least one SourceFragment, OR
  - `rkaf:noEvidenceReason` (1) — closed enum: `rkaf:axiomatic`, `rkaf:inferred-from-warrant-class`, `rkaf:consensus-without-citation`, `rkaf:permitted-by-safety-label`, `rkaf:declared-hypothesis`. The Assertion's `rkaf:hasSafetyLabel` MUST permit the chosen reason. This rule is uniform over the enum: it applies to every member, including `rkaf:declared-hypothesis`, with no per-value exceptions.

Optional properties:
- `rkaf:warrantKind` (0..1) — overrides the Assertion's warrant kind for this binding.
- `rkaf:hasAccessScope` (0..1) — narrows the binding's visibility.

An assertion lacking either an EvidenceBinding-with-fragment OR an explicit `noEvidenceReason` permitted by its safety level is **not operationally valid**. Layer 2 enforces this.

**Declared hypothesis.** `rkaf:declared-hypothesis` means the assertion is a
deliberately held, not-yet-validated belief. It is distinct from both
neighbours, and the distinction is the point:

| Value | Means |
| --- | --- |
| `rkaf:axiomatic` | needs no evidence; evidence would be circular |
| `rkaf:consensus-without-citation` | has social grounding, just no citable source |
| `rkaf:declared-hypothesis` | has no grounding at all, says so, and intends to be validated |

Without it a hypothesis has no honest landing. A producer holding one must
choose between fabricating evidence and claiming
`rkaf:consensus-without-citation`, which asserts social grounding the producer
does not have. Both are worse than the gap, and declared absence over silent
absence is this framework's own posture.

An assertion whose binding carries `rkaf:declared-hypothesis` MUST NOT exceed
`rkaf:searchOnly` or `rkaf:reviewQueueOnly` in `rkaf:usageEligibility` until
an EvidenceBinding-with-fragment replaces the reason. The cap is graded rather
than binary on purpose: a hypothesis that is invisible is worse than one that
is findable but not actionable, which is the whole reason the value exists.
The rule above — that the safety label must permit the reason — GRANTS
operational validity and does not bound it, so it cannot express this cap;
the two rules compose rather than substitute.

This cap is a **producer obligation, not a mechanical check**, and no compiled
target enforces it. `rkaf:usageEligibility` is a property of the assertion
envelope (§2.3) while `rkaf:noEvidenceReason` is a property of the binding,
and `rkaf:bindsAssertion` is a bare IRI: the conditional idiom that carries
every other conditional requirement in this specification needs the guard and
the requirement to be properties of ONE shape. Putting eligibility on the
binding would create two places to look for the same consumer-scoped fact,
which §2.3 forbids. This is the same posture as §4.7.3 rule 3 and the
`rkaf:extractionMethod` agreement in §2.4 — a shape cannot require what it
cannot see — and closing it mechanically is tracked in TODO.md.

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

### 4.7 ConceptScheme and ConceptAssignment

SKOS owns concept-scheme semantics. `skos:inScheme`, `skos:hasTopConcept`,
`skos:prefLabel`, `skos:altLabel`, `skos:definition`, `skos:broader`,
`skos:narrower`, `skos:related`, and the SKOS mapping properties are used with
their own meanings, and Rulespec restates none of them. This section defines
only what SKOS leaves open and Rulespec must check mechanically: which facet a
scheme controls, who governs it, and what an assignment stands on.

Companion normative detail for the registry lifecycle is in
`spec/rkaf-concept-registry.md`.

#### 4.7.1 rkaf:ConceptScheme

**rkaf:ConceptScheme** — one facet, one controlled category system. Compatible
with `skos:ConceptScheme`; a producer MAY type a node as both.

Required properties:
- `skos:prefLabel` (1).
- `rkaf:schemeFacet` (1, IRI) — which facet the scheme controls.
- `rkaf:conceptStatus` (1) — the same closed enum concepts use.
- One of `rkaf:managedByRegistry` (1, IRI) or `rkaf:definedInScope` (1, IRI).

Optional: `skos:definition` (0..1), `skos:hasTopConcept` (0..*).

Facets MUST stay explicit. Topic, industry, regulated entity, affected
population, legal authority, place, organization, document role, obligation,
outcome, and legal status are different questions, and a scheme that never says
which one it answers is how they merge — every one of them holds terms, and only
the declared facet distinguishes them. `rkaf:schemeFacet` is a producer- or
profile-owned IRI and NOT a kernel enum: closing that set universally would be
Rulespec minting a facet taxonomy it has no standing to own.

The ownership disjunction is the seam `rkaf:RegisteredConcept` and
`rkaf:LocalConcept` already draw for concepts, applied to their container: a
scheme is either governed by a registry or defined in a workspace scope.

Authoritative structured values stay typed properties rather than fuzzy tags. An
organization is a relationship, a document state is a profile enum, a date is a
typed literal (§2.2), and a citation is a normalized identifier. Only genuinely
taxonomic meaning belongs in a scheme.

#### 4.7.2 Concepts

`rkaf:RegisteredConcept` and `rkaf:LocalConcept` (§6, `spec/rkaf-concept-registry.md` §2.1)
each MUST carry `skos:inScheme` (1). A facet-free concept is exactly the term
that later merges with a same-spelled term from another facet. The referenced
scheme MAY be an `rkaf:ConceptScheme` or an external `skos:ConceptScheme`, so
Rulespec declares no class range over `skos:inScheme`.

**Rulespec narrows `skos:inScheme` to exactly one scheme.** SKOS places no
cardinality restriction on the predicate — a `skos:Concept` may belong to
several schemes — and this is the one place §4.7's "Rulespec restates none of
them" is qualified. A concept belongs to exactly one facet: a term that answers
both "which industry" and "which topic" is two terms wearing one IRI, and the
merge it invites is precisely what the facet discipline exists to prevent.
Multi-facet membership is modelled as separate concepts joined by a SKOS mapping
property (§4.7 and `spec/rkaf-concept-registry.md`), which keeps the alignment
explicit and reviewable instead of implicit in a membership list.

`skos:definition` (0..1) is REQUIRED when `rkaf:conceptStatus` is
`rkaf:promoted`. Promotion is rare: it requires a definition, scope, examples,
counterexamples, mappings, usage evidence, conflicts, lineage, a steward, a
human approver, and a rationale. The definition is the piece a shape can check,
and its absence means the shared vocabulary gained a term nobody wrote down.
Query popularity, click counts, and model confidence MAY guide review; they
never establish meaning and never promote a concept.

#### 4.7.3 rkaf:ConceptAssignment

**rkaf:ConceptAssignment** — an evidence-bearing, versioned record that one
Artifact or one SourceFragment is associated with one concept.

Required properties:
- `rkaf:assignmentSubject` (1, IRI) — the tagged thing.
- `rkaf:assignmentSubjectType` (1) — closed enum `rkaf:Artifact`, `rkaf:SourceFragment`.
- `rkaf:assignedConcept` (1, IRI).
- `skos:inScheme` (1, IRI) — the facet, restated at the point of use so a consumer reading assignments alone can tell an industry tag from a topic tag without resolving the concept.
- `rkaf:assignmentRole` (1) — closed enum `rkaf:assignmentPrimary`, `rkaf:assignmentSubstantive`, `rkaf:assignmentMention`, `rkaf:assignmentContextual`. Editorial ordering only; nothing in Rulespec compares two roles.
- `rkaf:assignmentDerivation` (1) — closed enum `rkaf:directAssignment`, `rkaf:derivedAssignment`.
- `rkaf:assertionOrigin` (1), inherited from the envelope below.

Conditional properties:
- When `rkaf:assignmentSubjectType` is `rkaf:SourceFragment`, `rkaf:assignmentEvidence` (1..*) is REQUIRED.
- When `rkaf:assignmentDerivation` is `rkaf:directAssignment`, `rkaf:assignmentEvidence` (1..*) is REQUIRED.
- When `rkaf:assignmentDerivation` is `rkaf:derivedAssignment`, `rkaf:supportingAssignment` (1..*) is REQUIRED.
- When `rkaf:supportingAssignment` is present, `rkaf:assignmentPolicyVersion` (1) is REQUIRED.
- When `rkaf:assignmentEvidence` is present, `rkaf:assignmentEvidenceScheme` (1) is REQUIRED.
- When `rkaf:assignmentEvidenceScheme` is `rkaf:carrier-local-fragment`, every `rkaf:assignmentEvidence` value MUST match the carrier-local fragment URN grammar (§4.2).

`rkaf:assignmentEvidence` has range `rkaf:SourceFragment`, so "exact evidence"
resolves to real coordinates in a real Artifact rather than to any IRI at all.
`rkaf:supportingAssignment` has range `rkaf:ConceptAssignment`.

`rkaf:assignmentEvidenceScheme` (1 when evidence is present, closed enum
`rkaf:FragmentIdentityScheme`) says WHICH of the two identity forms in §4.2 the
cited values use. It is required for the same reason
`rkaf:regulatoryIdentifierScheme` is required whenever
`rkaf:hasRegulatoryIdentifier` is present: a published fragment IRI and a
carrier-local fragment URN are both absolute IRIs, the grammar a value must
satisfy is not recoverable from the value, and only the declaration says which
one the producer is claiming. Declaring
`rkaf:carrier-local-fragment` binds every cited value to the derived grammar on
all six compiled targets. Naming a value in the `urn:rkaf:fragment:` namespace
WITHOUT that declaration is a violation
(`rkaf:ConceptAssignmentCarrierLocalEvidenceDeclaredShape`,
`shapes/rkaf-shapes-core.ttl`): registering the derived form has to mean the
namespace is checked wherever it appears, not merely wherever a producer
volunteers the declaration. That rule is L3-only because it is a per-VALUE
conditional keyed on that value's own lexical form, which the compiled
list-of-string carrier — one pattern for the whole list — cannot express.

The derived form changes where the bindings live, not whether they exist. The
class range stands, the same-Artifact rule below still applies to the
materialized fragment, and a carrier-local URN cited as evidence for a
carrier-local subject still has to name the same Artifact.

Two further rules constrain WHICH fragment may be cited, and one obligation is
left to the producer. Both rules are L3-only: each compares one node's value
against another node's class or property, which no JSON Schema can follow.

1. When `rkaf:assignmentSubject` RESOLVES to a `rkaf:SourceFragment`,
   `rkaf:assignmentEvidence` (1..*) is REQUIRED — whatever
   `rkaf:assignmentSubjectType` declares. The subject-type conditional above
   keys on a self-declared literal, so on its own it is defeated by relabelling
   a segment assignment `rkaf:Artifact`; that relabelling would let a document
   tag prove a section tag, which is exactly what the directional rule forbids.
2. Every cited `rkaf:assignmentEvidence` fragment MUST name the same
   `oa:hasSource` Artifact as the subject fragment. Without it, one fragment of
   one unrelated document satisfies the evidence requirement for every segment
   in a corpus.
3. Producers MUST cite regions OF THE SUBJECT FRAGMENT. Rule 2 is the floor a
   shape can check; whether the cited region is the subject's own needs selector
   arithmetic across coordinate systems and unit conversions, which Rulespec
   does not require an implementation to perform. This is a producer obligation,
   not a mechanical check, and it is stated here rather than implied.

**The envelope is composed, not restated.** `rkaf:ConceptAssignment` composes
`#AssertionEnvelope` (§2.3), so everything an assignment records about its own
trustworthiness has exactly one home:

| Fact | Where it lives |
| --- | --- |
| Construction origin | `rkaf:assertionOrigin` |
| Model derivation | `rkaf:hasAILineage` (§5.3, AI-touched origins) |
| Extraction run | `rkaf:hasExtractionProvenance` (§2.4) |
| Source claimant | `rkaf:hasSourceClaimant` (§2.4) |
| Confidence | `rkaf:hasConfidence` (0..*, §4.5) |
| Approval, rejection, revocation | an `rkaf:Attestation` targeting the assignment — never a field |
| Consumer state | `rkaf:usageEligibility`, `rkaf:consumerLifecycleState`, `rkaf:hasAccessScope` |
| Supersession | `rkaf:supersedesAssertion` |
| Assertion time | `rkaf:assertedAt` |

`#AssertionProposition` (§2.3) is deliberately NOT composed: an assignment's
proposition is the subject-concept pair, not a subject/predicate/object triple,
and composing it would demand an `rkaf:assertsPredicate` every assignment would
fill with the same placeholder. The producer's extraction profile version
belongs in `rkaf:ExtractionActivity`'s `rkaf:extractorVersion`, not in a second
version field here.

Assignment history is append-only. A revised assignment is a NEW record naming
its predecessor through `rkaf:supersedesAssertion`; the predecessor stays
addressable.

**The directional rule.** Both Artifacts and meaningful SourceFragments are
taggable, and the two directions are not symmetric:

```text
accepted segment assignments
  -> policy-bound document aggregation
  -> document assignment with supporting-assignment proof
  -> candidate context for other segment passes
  -> fresh segment proposals
  -> local evidence requirement
  -> accepted new segment assignments
```

Segment evidence MAY support a document tag. A document tag MAY shortlist
candidate concepts for a segment, and it MUST NOT prove one: the segment
assignment still requires its own `rkaf:assignmentEvidence`, drawn from the same
Artifact as the subject fragment. Three rules carry that together — the
subject-type conditional, the resolved-subject rule, and the same-Artifact rule
above. Without them one mistaken document tag propagates to every segment and
the segments then confirm the document.

Inherited document context remains non-evidentiary context. A zero-tag segment
MUST NOT remove another segment's assignment or the document's supported tag;
missing tags remain unknown, never negative.

`rkaf:assignmentPolicyVersion` is what makes "a documented rule may combine
approved segment tags into a document tag" checkable: the record says WHICH
documented rule, at which version, so the same inputs can be replayed against
the same policy.

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
- `rkaf:inputContextHash` (1, `xsd:string`) — lowercase `sha256:<64 hex>`. A hash field that accepts any string cannot be compared across runs, which is the only thing an input-context hash exists to do.
- `rkaf:humanApprover` (0..1, IRI) — the actor who approved the AI output, when one has. OPTIONAL: see §2.4. An unreviewed model candidate MUST be representable, and approval is an `rkaf:Attestation` targeting the assertion.
- `rkaf:humanRationale` (0..1, `xsd:string`).

When `rkaf:humanRationale` is present, `rkaf:humanApprover` is REQUIRED. A stated human reason with no human named is a review attributed to nobody, which reads as approved while leaving no one accountable.

An assertion with `rkaf:assertionOrigin ∈ {rkaf:aiSuggested, rkaf:aiPromoted, rkaf:humanQualified, rkaf:humanRevalidation}` MUST carry an `rkaf:hasAILineage` reference. Layer 2 enforces this. The requirement is satisfied by an approver-free lineage: it demands that the derivation be recorded, not that it be reviewed.

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

Inherited name-for-name from `archive/v0.1/spec/rkaf-core-v0.1.md`:

- **Assertion model:** `rkaf:Assertion`, `rkaf:assertsSubject`, `rkaf:assertsPredicate`, `rkaf:assertsObject`, `rkaf:hasApplicability`, `rkaf:effectivePeriod`.
- **Relationship assertion specialization:** `rkaf:RelationshipAssertion`, `rkaf:assertionPolarity`.
- **Attestation / adoption:** `rkaf:Attestation`, `rkaf:LocalAdoption`, `rkaf:adoptionAuthorityKind`, `rkaf:adoptionStatus`.
- **Justification:** `rkaf:Justification`, `rkaf:hasJustification`, `rkaf:justifiedByAssertion`, `rkaf:GeneratedWorkProduct`.
- **Authority (now specialization of Warrant):** `rkaf:Authority`, `rkaf:hasAuthority`, `rkaf:derivesAuthorityFrom`, `rkaf:DelegationInstrument`.
- **Lifecycle:** `rkaf:LifecycleEvent`, `rkaf:supersedesAssertion`, `rkaf:lifecycleEvent` enum, amendment / rescission / supersession / material-revision packets, `rkaf:RevalidationEvent`, `rkaf:PointInTimeException`.
- **Usage / trust / safety:** `rkaf:usageEligibility` lattice, `rkaf:hasTrustZone` (Z0–Z8), `rkaf:hasSafetyLabel` (D0/S1/R2/A3/P4).
- **Concepts:** `rkaf:Concept`, `rkaf:RegisteredConcept`, `rkaf:LocalConcept`, `rkaf:ConceptRegistry`, `rkaf:ConceptMapping`, `rkaf:ConceptResolutionResult`, `rkaf:ConceptCacheEntry`. v0.2 adds `rkaf:ConceptScheme` and `rkaf:ConceptAssignment` (§4.7) and requires `skos:inScheme` on both concept flavors.
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
3. **AI lineage.** AI-touched assertions MUST carry `rkaf:hasAILineage`. The lineage records the model derivation; it does NOT record approval, and it MUST NOT require a human approver (§2.4). Approval, when it happens, is an `rkaf:Attestation` targeting the assertion. A model asked to review its own output produces another opinion, not an approval.
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
| **W3C Web Annotation Ontology (OA)** | `oa:` | Rulespec v0.2 composes **OA 1.0** (W3C Recommendation 2017-02-23; namespace `http://www.w3.org/ns/oa#`, stable). Predicate-level imports: `oa:hasSource` (parent-resource edge on a SpecificResource), `oa:hasSelector` (selector attachment), `oa:exact` / `oa:prefix` / `oa:suffix` (TextQuoteSelector payload), `oa:start` / `oa:end` (TextPositionSelector offsets). Rulespec adds one rkaf-namespaced predicate to the position selector, `rkaf:coordinateSystem`, because OA does not name the unit its offsets count in and an offset without a unit is not reproducible (§4.2). `rkaf:SourceFragment rdfs:subClassOf oa:SpecificResource`. Foundational selector kinds (`oa:FragmentSelector`, `oa:TextQuoteSelector`, `oa:TextPositionSelector`, `oa:RangeSelector`, `oa:XPathSelector`, `oa:CssSelector`) MUST be supported by every Rulespec implementation handling source fragments. Rulespec declines L1/L3 constraints over OA predicate ranges with one exception: `oa:hasSource` carries an L3 `sh:class rkaf:Artifact` range (§4.2), because a fragment of a workspace, a proceeding, or an actor addresses no document region at all. Everywhere else partner producers conform to OA's own domain/range. Breaking changes in a future OA 2.0 trigger an alignment-row re-evaluation. |
| **W3C SKOS** | `skos:` | Concept relations for the Concept Registry (`spec/rkaf-concept-registry.md`): the cross-scheme mapping properties (`exactMatch`, `closeMatch`, `broadMatch`, `narrowMatch`, `relatedMatch`), the in-scheme semantic relations SKOS distinguishes from them (`broader`, `narrower`, `related`), and `mappingRelation`. v0.2 additionally imports `skos:inScheme` (concept-to-scheme membership, REQUIRED on both concept flavors and on every `rkaf:ConceptAssignment`), `skos:definition`, and `skos:hasTopConcept` (§4.7). SKOS owns concept-scheme semantics; Rulespec declares no class range over these predicates, because a concept or scheme may live in an external thesaurus. |
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
