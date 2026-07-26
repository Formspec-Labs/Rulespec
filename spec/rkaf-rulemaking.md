# Rulespec US Rulemaking-Process Module

**Status:** Experimental.
**Companion docs:** `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`, `spec/rkaf-conformance.md`.

> Instability warning: these terms ship under the normal release-bound closed-taxonomy rules, but their shapes may change between pre-1.0 releases. Full-corpus exercises have found required identity repairs, including the agenda-item distinction in this revision. The module does not advance to pre-release normative status until the §9 requirements hold.

## 0. Conformance language

RFC 2119 / RFC 8174 keywords are normative when uppercase.

## 1. Scope

This module models the US regulatory agenda item identified by a RIN and the
distinct proceedings that produce federal regulations: their identity, current
stage when known, public-comment intervals, published documents, affected CFR
units, lifecycle events, and authority chains. It composes the universal
Rulespec primitives instead of creating a second document, authority, or
lifecycle system.

The module does not model comment content, commenter identity, campaign detection, or descriptive topic tags.

## 2. Regulatory agenda item

`rkaf:RegulatoryAgendaItem` represents the durable registry object identified
by a Regulation Identifier Number. It is a rulemaking-profile specialization of
`dcat:Resource`. The agenda item is distinct from every edition record,
Proceeding, Docket, and publication associated with it.

Required properties:

- `rkaf:hasAgendaItemIdentifier` (1) — the canonical RIN IRI;
- `rkaf:agendaItemIdentifierScheme` (1) — `rkaf:us-rin`.

The canonical form is
`urn:rkaf:us:rin:<four-digits>-<two-uppercase-letters><two-digits>`, for example
`urn:rkaf:us:rin:2060-AV16`.

`rkaf:agendaScopeStatus` (0..1) is an evidence-state classification:

| Value | Meaning |
|---|---|
| `rkaf:agendaScopeRecurring` | An official source expressly supports a recurring family. |
| `rkaf:agendaScopeSingleObserved` | Current action-specific evidence links exactly one Proceeding; this is not a closed-world claim. |
| `rkaf:agendaScopeUnresolved` | Available evidence establishes neither one action nor an intentional recurring family. |

Several Proceedings sharing a RIN MUST NOT, by itself, produce
`rkaf:agendaScopeRecurring`. One observed Proceeding MUST NOT be described as
proof that no later action exists.

### 2.1 Editioned observations

`rkaf:RegulatoryAgendaObservation` represents one agenda item in one Unified
Agenda edition. It is a specialization of both `rkaf:Artifact` and
`dcat:CatalogRecord`. Its immutable Artifact identity is the edition-specific
source URL. `foaf:primaryTopic` (1) identifies the durable
`rkaf:RegulatoryAgendaItem`.

The optional observation properties are:

- `rkaf:agendaStage` (0..1) — `rkaf:agendaPrerule`,
  `rkaf:agendaProposed`, `rkaf:agendaFinal`, `rkaf:agendaLongterm`, or
  `rkaf:agendaCompleted`;
- `rkaf:agendaPriority` (0..1) — one normalized Unified Agenda priority;
- `rkaf:agendaAffectsCitation` (0..*) — source-reported `rkaf:us-cfr`
  citations;
- `rkaf:agendaAuthorityCitation` (0..*) — source-reported `rkaf:us-usc` or
  `rkaf:us-pl` citations.

An observation's title, abstract, stage, priority, timetable, targets, and
authority citations describe the agenda item in that edition. Producers MUST
NOT copy them to a Proceeding without separate action-specific evidence.

### 2.2 Qualified Proceeding relationships

`dcat:qualifiedRelation` links an agenda item to zero or more
`rkaf:AgendaProceedingRelationship` nodes. That class specializes
`dcat:Relationship` and requires:

- `dcterms:relation` (1) to one `rkaf:Proceeding`;
- `dcat:hadRole` (1), fixed to `rkaf:agendaTracksProceeding`;
- `prov:wasDerivedFrom` (1..*) for the action-specific evidence;
- `prov:wasGeneratedBy` (1), `prov:wasAttributedTo` (1), and
  `prov:generatedAtTime` (1).

The role means that a source assigned the agenda item's RIN to the Proceeding
or to an action-specific docket or publication used to construct it. The role
does not establish Proceeding identity or recurring-series membership.

## 3. Proceeding

`rkaf:Proceeding` represents one rulemaking proceeding. It is distinct from a regulations.gov docket: a proceeding may span several dockets, and a docket may contain activity from several proceedings.

Required properties:

- `rkaf:hasProceedingIdentifier` (1) — an IRI that identifies the proceeding,
  never a docket or published document.
- `rkaf:proceedingIdentifierScheme` (1) — `rkaf:official-registry` or
  `rkaf:partner-defined`. An
  `rkaf:official-registry` identifier also requires
  `rkaf:identifierRegistry` (1), the IRI of the issuing registry.

Optional properties:

- `rkaf:proceedingStage` (0..1) — one value from the closed enum
  `rkaf:proceedingPrerule`, `rkaf:proceedingProposed`,
  `rkaf:proceedingSupplemental`, `rkaf:proceedingFinal`,
  `rkaf:proceedingWithdrawn`, `rkaf:proceedingLongterm`, or
  `rkaf:proceedingConcluded`. Absence means the current stage is unknown.
  Producers MUST NOT infer a stage from missing evidence.
- `rkaf:proceedingTerminationCause` (0..1) — one of
  `rkaf:agencyWithdrawal`, `rkaf:judicialVacatur`,
  `rkaf:congressionalDisapproval`, or `rkaf:administrativeConclusion`.
  It is REQUIRED when the stage is `rkaf:proceedingConcluded`. A partial
  judicial action does not by itself conclude the whole proceeding.
- `rkaf:hasAuthority` (0..*) — IRI of an evidenced issuing or grounding
  `rkaf:Authority`. Absence means unknown. A producer MUST NOT mint an
  Authority from agency identity alone merely to satisfy this property. When a
  source supplies a legal citation, the producer SHOULD emit the edge and its
  authority chain.
- `rkaf:hasDocket` (0..*) — IRI of an associated `rkaf:Docket`. Docket
  membership never establishes proceeding identity.
- `rkaf:proceedingSupersedes` (0..*) — directional link to predecessor
  Proceedings after a merge, split, replacement, or identity repair. This
  relation preserves continuity and MUST NOT be replaced by listing predecessor
  and successor together in lifecycle `appliesTo`, which would corrupt cascade
  semantics.
- `rkaf:proceedingAffectsCitation` (0..*) — a normalized `rkaf:us-cfr`
  citation known to be targeted, even when the applicable edition has not been
  resolved.
- `rkaf:proceedingAffects` (0..*) — IRI of the edition-scoped CFR
  `rkaf:Artifact` in force immediately before the proposed or final amendment.
- `rkaf:proceedingProduces` (0..*) — IRI of an immutable resulting edition or
  publication Artifact produced by the proceeding.

`rkaf:hasProceedingIdentifier` MUST NOT contain a
`urn:rkaf:us:rin:*` or `urn:rkaf:us:regsgov:*` value under any scheme. The
first identifies a RegulatoryAgendaItem. The second identifies a docket,
document, or comment. Neither identifies a Proceeding.

A producer MUST give each Proceeding a stable partner or official-registry
identifier. Shared RIN evidence is retained on
`rkaf:AgendaProceedingRelationship`, never by collapsing the Proceedings.

### 3.1 Legacy RIN migration

A producer migrating a Proceeding previously identified by `rkaf:us-rin` MUST:

1. retain or mint a stable partner or official-registry Proceeding identifier;
2. mint the `rkaf:RegulatoryAgendaItem` identified by the RIN;
3. create a qualified relationship only when action-specific evidence supports
   it; and
4. move Unified Agenda context to editioned
   `rkaf:RegulatoryAgendaObservation` nodes.

Legacy `rkaf:hasProceedingEvidenceIdentifier` values follow the same migration.
Their context aliases remain decodable during this Experimental pre-release
transition, but the properties no longer satisfy the current Proceeding shape.

### 3.2 Docket

`rkaf:Docket` represents a mutable administrative container. It is neither an
immutable `rkaf:Artifact` nor a `rkaf:Proceeding`.

Required properties:

- `rkaf:hasDocketIdentifier` (1) — an IRI identifying the docket.
- `rkaf:docketIdentifierScheme` (1) — `rkaf:us-regsgov` or
  `rkaf:official-registry` or `rkaf:partner-defined`. The official-registry
  form also requires `rkaf:identifierRegistry` (1).

For a regulations.gov docket, the canonical identifier is
`urn:rkaf:us:regsgov:<agency-issued-id>`, for example
`urn:rkaf:us:regsgov:EPA-HQ-OAR-2021-0317`. Normalize ASCII letters to
uppercase and preserve agency-issued hyphen or underscore separators. The
grammar includes source-owned identifiers such as
`urn:rkaf:us:regsgov:EPA_FRDOC_0001`. A docket may link to several Proceedings,
and a Proceeding may link to several dockets.

`rkaf:official-registry` distinguishes an official identifier for systems such
as FCC ECFS, FERC eLibrary, or SEC rulemaking from a partner-minted surrogate.
It does not assert a universal grammar; `rkaf:identifierRegistry` names the
issuer and the producer preserves the issuer's identifier exactly.

## 4. Comment periods

`rkaf:CommentPeriod` represents one continuous interval during which the public may submit comments.

Required properties:

- at least one anchor: `rkaf:commentPeriodFor` (0..*) naming Proceedings or
  `rkaf:commentPeriodDocket` (0..*) naming Dockets. A period may carry both and
  may name multiple Proceedings for a joint action.
- `rkaf:commentPeriodStart` (1) — `xsd:date`.
- `rkaf:commentPeriodEnd` (1) — `xsd:date`, on or after `rkaf:commentPeriodStart`.
- `prov:wasDerivedFrom` (1..*) — IRI of a `prov:Entity` that carries the
  source evidence for this interval.

`rkaf:commentPeriodOpenedBy` (0..*) names the notice or other Artifact that
solicited comment. It is distinct from `prov:wasDerivedFrom`: the former names
the subject-opening document, while the latter records the evidence used to
construct the interval.

A reopening is a new CommentPeriod node linked to the same Proceeding.
Producers MUST NOT overwrite the earlier interval or stretch it across a
closed gap. When sources disagree or one source supplies an invalid interval,
producers MUST preserve the qualified evidence separately and MUST NOT emit an
unsupported CommentPeriod.

Start and end are inclusive calendar days in the deadline's governing
timezone. For Regulations.gov and Federal Register deadlines, the governing
timezone is US Eastern unless the source expressly specifies another one. A
producer deriving a date from an instant MUST convert the instant into the
governing timezone before truncating it to `xsd:date`; UTC truncation is
non-conforming when it changes the source's calendar day.

## 5. Published documents

Federal Register documents remain ordinary `rkaf:Artifact` nodes.
`rkaf:hasArtifactIdentifier` identifies the immutable publication, normally
with its permanent federalregister.gov document URL, while
`rkaf:hasRegulatoryIdentifier` may carry the normalized `rkaf:us-frdoc`
identifier. `rkaf:publishedInProceeding` links an Artifact to one or more
Proceedings.

The `rkaf:us-frdoc` grammar is deliberately strict. If an official source
document number does not match `YYYY-NNNNN`, the Artifact MUST still use its
permanent federalregister.gov document URL as
`rkaf:hasArtifactIdentifier` with `rkaf:artifactIdentifierScheme:
rkaf:urn-persistent`, and the producer MUST NOT label the source value
`rkaf:us-frdoc`. This is the normative fallback for legacy, correction, and
other source-preserved forms.

Federal Register documents need no source-specific subclass. A Unified Agenda
edition entry uses `rkaf:RegulatoryAgendaObservation`, the Artifact subclass
defined in §2.1, because its edition grain and agenda-only state are normative.

### 5.1 Cross-posted documents

A rulemaking document routinely appears in more than one registry: the same
proposed rule is a Federal Register document and a regulations.gov docket
document. Each posting is a distinct immutable publication, so each posting is
its own `rkaf:Artifact` (core §4.1):

- The Federal Register posting uses its permanent federalregister.gov URL as
  Artifact identity and MAY carry the `rkaf:us-frdoc` citation.
- The regulations.gov posting uses its permanent
  `https://www.regulations.gov/document/<id>` URL as Artifact identity and MAY
  carry the `rkaf:us-regsgov` citation.

A producer MUST NOT collapse the postings into one Artifact carrying two
regulatory-identifier pairs. Two nodes represent the same posting if they
share a `rkaf:hasArtifactIdentifier` value; producers SHOULD use the permanent
publication URL as `@id` so that identity converges without a merge heuristic.
When one producer emits both postings, it MUST link the Federal Register
posting to the Regulations.gov posting with `dcterms:hasFormat`; it SHOULD
also emit the inverse `dcterms:isFormatOf`. Both are mode-1 imported predicates
with Artifact domain and range. Every posting Artifact MAY assert
`rkaf:publishedInProceeding`; consumers that need one node per underlying work
unify through the format links, never merely because the postings share a
Proceeding. Relations whose range is a specific edition — such as
`rkaf:proceedingAffects` and `rkaf:derivesAuthorityFrom` — target whichever
posting Artifact carries the edition being cited, not "the document" in the
abstract.

### 5.2 Regulatory citation identity

This subsection is the normative home of the US regulatory identifier pair.
`spec/rkaf-core.md` §4.1 defines the universal Artifact and deliberately does
not declare these terms; the profile shape `#USRegulatoryArtifact` in
`constraints/profiles/us-rulemaking/us-regulatory-artifact.cue` composes the
kernel `#Artifact` and adds them, keeping `@type: rkaf:Artifact`. A consumer
that does not adopt this profile never sees them.

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
to Proceedings, is §5.1 above.

The US regulatory schemes use these canonical forms:

| Scheme | Identifies | Canonical form and normalization |
|---|---|---|
| `rkaf:us-cfr` | A CFR part or section | `urn:rkaf:us:cfr:<title>:<part>[.<section>]`, for example `urn:rkaf:us:cfr:40:60`, `urn:rkaf:us:cfr:40:60.1`, or `urn:rkaf:us:cfr:40:60.5375a`. Title and part are decimal digits without spaces; title has no leading zero. A section may have a lowercase alphabetic suffix of up to three characters and internal lowercase alphanumeric hyphen suffixes. Subparts are outside this identifier grammar. |
| `rkaf:us-usc` | A U.S. Code section | `urn:rkaf:us:usc:<title>:<section>`, for example `urn:rkaf:us:usc:42:7411`. Omit subsection parentheses. Preserve internal hyphens and normalize alphabetic suffixes to lowercase. |
| `rkaf:us-frdoc` | A Federal Register document | `urn:rkaf:us:frdoc:<document-number>`, for example `urn:rkaf:us:frdoc:2024-00366`. The document number is a four-digit year, a hyphen, and a five-digit sequence. Official source values outside this grammar use the permanent-publication fallback below. |
| `rkaf:us-regsgov` | A regulations.gov docket, document, or comment | `urn:rkaf:us:regsgov:<agency-issued-id>`, for example `urn:rkaf:us:regsgov:EPA-HQ-OAR-2021-0317-0184` or `urn:rkaf:us:regsgov:EPA_FRDOC_0001`. Normalize ASCII letters to uppercase and preserve agency-issued hyphen or underscore separators. Single-segment and legacy identifiers remain source values; producers MUST NOT invent missing segments. Docket containers use the scheme on `rkaf:Docket`, while documents and comments use it on `rkaf:Artifact`; see `spec/rkaf-rulemaking.md`. |
| `rkaf:us-pl` | A public law | `urn:rkaf:us:pl:<congress>-<law-number>`, for example `urn:rkaf:us:pl:117-58`. Both components are positive decimal integers without leading zeroes. |
| `rkaf:us-eo` | An Executive order | `urn:rkaf:us:eo:<order-number>`, for example `urn:rkaf:us:eo:14094`. The order number is a positive decimal integer without leading zeroes. |

These URNs supply normalized citation and agency identity where no US public
body publishes a canonical citation URI. They preserve, rather than replace,
the identifier classes owned by the CFR, U.S. Code, Federal Register,
regulations.gov, Congress, and the Executive Office. This is
composition-consistent minting under `spec/rkaf-core.md` §9.4.

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

`rkaf:publishedInProceeding` (0..*) belongs to this profile for the same
reason: a Proceeding is a rulemaking construct, so a universal Artifact cannot
own a relation into it. Its range is `rkaf:Proceeding`, declared in
`constraints/profiles/us-rulemaking/semantics/l0-ranges.cue`.


## 6. Lifecycle events

Proceeding stage transitions use `rkaf:LifecycleEvent`; this module defines no
parallel event class. For the stage-family kinds, every `rkaf:appliesTo` value
MUST be a Proceeding, and `rkaf:effectiveDate` records the transition time.

NOTE (codification detail, no normative change): the twelve kinds below are
CONTRIBUTED BY THIS MODULE to the shared `rkaf:lifecycleEventKind` value set
rather than owned by the kernel. `constraints/core/lifecycle-event.cue`
declares the ten universal kinds and leaves the property open at the carrier
level; `constraints/profiles/us-rulemaking/us-lifecycle-event.cue` declares
these twelve and binds the assembled closed union to `rkaf:LifecycleEvent`
through a profile shape that composes the kernel one. The class, the property,
and the closed set every conforming validator applies are unchanged — a
consumer that loads this module sees exactly the 22 values.

A consumer that loads only the kernel is unconstrained by the property
ENTIRELY, not merely by these twelve. The compiled kernel carrier types
`rkaf:lifecycleEventKind` as an open string and emits no `sh:in`, so the ten
universal kinds ship as a named type that nothing binds to the property; every
closed kind set in this contract is enforced by the profile artifacts. That
openness is deliberate rather than an oversight — SHACL is conjunctive and the
compiled shapes are loaded together, so a kernel closure over the ten would
reject every profile-contributed kind no matter what the overlay says (see
`constraints/README.md`, "Layered value sets").

The `rkaf:lifecycleEventKind` closed enum adds:

| Event kind | Meaning |
|---|---|
| `rkaf:proceedingPrerule` | The proceeding entered prerule development. |
| `rkaf:proceedingProposed` | The agency published or formally entered the proposed-rule stage. |
| `rkaf:proceedingSupplemental` | The agency published or entered a supplemental-proposal stage. |
| `rkaf:proceedingFinal` | The agency published or entered the final-rule stage. |
| `rkaf:proceedingWithdrawn` | The agency withdrew the proceeding. |
| `rkaf:proceedingLongterm` | The agency placed the proceeding on the long-term agenda. |
| `rkaf:proceedingConcluded` | Evidence establishes that the proceeding ended without another stage value accurately describing the terminal state. |

External legal events use these additional closed values:

| Event kind | Meaning |
|---|---|
| `rkaf:proceedingVacated` | A court vacated all or part of a produced rule. |
| `rkaf:proceedingStayed` | A court stayed operation of all or part of a produced rule. |
| `rkaf:proceedingRemanded` | A court remanded all or part of the action. |
| `rkaf:proceedingReinstated` | A later legal event restored a previously displaced action. |
| `rkaf:proceedingDisapproved` | Congress disapproved all or part of the action. |

An external legal event MUST name at least one Proceeding in `rkaf:appliesTo`.
It MAY additionally enumerate affected CFR-unit Artifacts from the
Proceeding's target/produced set, allowing partial vacatur, stay, remand,
reinstatement, or disapproval to preserve severability. An Artifact target
does not imply that every other target shares the legal effect.

`rkaf:proceedingStage` records agency procedural progress or an evidenced
conclusion. It does not assert that a rule is legally effective, operative,
valid, or enforceable; external legal events carry those facts. LifecycleEvent
nodes preserve the event sequence that produced the stage. When stage-family
events exist, `rkaf:proceedingStage` MUST equal the
`rkaf:lifecycleEventKind` of the latest such event. Equal latest timestamps
with different kinds are conflicting evidence and MUST NOT yield a current
stage. No lifecycle event means unknown, not prerule. A final-stage proceeding
SHOULD carry the corresponding `rkaf:proceedingFinal` event.

An agenda observation's `rkaf:agendaStage` is not a stage-family lifecycle
event and MUST NOT determine `rkaf:proceedingStage`. This remains true when the
agenda item has exactly one currently known Proceeding.

## 7. Targets and authority

`rkaf:proceedingAffectsCitation` is the producible citation-level relation for
bulk sources. Its values use the `rkaf:us-cfr` grammar, including
letter-suffixed sections such as
`urn:rkaf:us:cfr:40:60.5375a`. The relation records a known target without
pretending that an edition has been resolved.

`rkaf:proceedingAffects` is the stronger relation to the CFR-unit Artifact in
force immediately before the amendment. Each target MUST identify a specific
immutable CFR edition or snapshot through `rkaf:hasArtifactIdentifier`; its
edition-independent citation may be carried separately through
`rkaf:hasRegulatoryIdentifier`. `rkaf:proceedingProduces` names the immutable
post-action edition or publication. A compact citation alone supports
`proceedingAffectsCitation`, not `proceedingAffects`. Producers SHOULD upgrade a
citation edge after resolution without deleting the citation evidence.

Statutory grounding uses the existing authority chain:

```text
rkaf:Proceeding
  └─ rkaf:hasAuthority → rkaf:Authority
       └─ rkaf:derivesAuthorityFrom → rkaf:Artifact
            ├─ rkaf:hasArtifactIdentifier → edition-scoped GovInfo URI
            ├─ rkaf:hasRegulatoryIdentifier → urn:rkaf:us:usc:42:7411
            └─ rkaf:regulatoryIdentifierScheme → rkaf:us-usc
```

Public-law and Executive-order artifacts MAY appear in the same chain with `rkaf:us-pl` and `rkaf:us-eo`.

The general module permits unknown authority. A decision-grade consumption
profile MUST require `rkaf:hasAuthority` and MUST verify that every required
chain resolves through edition-scoped Artifacts before relying on the
Proceeding for a legal or eligibility decision.

`rkaf:agendaAffectsCitation` and `rkaf:agendaAuthorityCitation` expose what an
editioned agenda record reports without asserting that every linked Proceeding
has the same target or authority. A producer MAY promote one of those values to
a Proceeding relation only when a docket, publication, or other
action-specific source supports that promotion. The qualified relationship's
provenance does not, by itself, qualify the separate target or authority edge.

## 8. Composition

ELI-DL is the EU draft-legislation analog for pre-enactment lifecycle. This
module cites ELI-DL as a mode-4 architectural pattern; it imports no ELI-DL
predicate. Promotion to an alignment row requires an EU-corpus consumer with a
tested binding.

DCAT 3 and FOAF move from deferred pattern citations to scoped mode-1 imports:

- `foaf:primaryTopic` links any document-like Artifact to its one durable main
  subject. The rulemaking profile requires a RegulatoryAgendaItem target for an
  agenda observation.
- `dcat:qualifiedRelation`, `dcat:Relationship`, `dcterms:relation`, and
  `dcat:hadRole` carry the agenda-to-Proceeding relationship and its role.

These are general catalog/document seams, not claims that every Rulespec
Artifact is a dataset. `rkaf:RegulatoryAgendaItem` and `rkaf:Proceeding` are
profile specializations of the DCAT resource extension point. The exact
decision and public-ontology domain/range audit are recorded in
`thoughts/specs/2026-07-24-rin-agenda-item-ontology-decision.md`.

`dcterms:hasFormat` and `dcterms:isFormatOf` are mode-1 predicate imports for
Artifact-to-Artifact cross-posting links. Rulespec does not redefine their
meaning.

## 9. Experimental stabilization gate

The module remains Experimental until both conditions hold:

1. A consumer runs `Proceeding`, `proceedingStage`, `CommentPeriod`, and `publishedInProceeding` across a full regulatory corpus and publishes a friction report covering multi-docket proceedings, reopened comment periods, and stage sequences.
2. A non-originating consumer reviews the terms and shapes.

The Spicy Regs full-corpus reports dated 2026-07-23 and 2026-07-24 satisfied
condition 1 for their respective earlier contracts. The later run exposed the
RIN referent problem that motivated this revision. Those receipts remain
historical evidence; they do not validate the current agenda-item contract.
Condition 1 for this revision requires a new receipt demonstrating ordinary,
officially recurring, and unresolved RIN cases without RIN-only merges or
agenda-context inheritance.

A maintainer-operated adversarial simulated-consumer review dated 2026-07-24 is
recorded in
`thoughts/reviews/2026-07-24-rulemaking-condition2-adversarial-review.md`. It is
not an external organization's review: no non-originating consumer operated or
ratified it. Condition 2 therefore remains open. The review also found that the
module must not graduate as-is. Graduation requires the review's §5
preconditions to land and a non-originating consumer to review the repaired
contract or ratify the review against it.

The simulation resolved three earlier agenda questions:

1. Keep one Artifact per posting and the 0..1 regulatory-identifier pair, then
   harden cross-posting identity, format links, and cardinality enforcement.
2. Change `rkaf:hasAuthority` on Proceeding to 0..* with
   absent-means-unknown, prohibit placeholder Authority nodes, and enforce
   decision-grade authority completeness in a consumption profile.
3. Replace the six bare stage-value IRIs before release. Prefer the existing
   `proceeding-*` IRIs shared with stage-family lifecycle events; distinct
   `proceedingStage*` IRIs remain the documented fallback if state and
   transition IRIs must stay separate.

These are design decisions for the repair batch, not evidence that the module
is stable. The curated corpus under `reference-corpora/us-rulemaking/`
exercises the module but does not itself satisfy either gate condition. A
fixture proves validation; it does not prove corpus-scale fitness.

The RIN agenda-item revision additionally requires the source-of-truth CUE,
generated targets, reference corpus, Spicy Regs L0 mapping, and a hermetic
full-corpus receipt to agree before condition 1 is marked satisfied again.

## 10. Validation surface

- CUE source: `constraints/profiles/us-rulemaking/rulemaking.cue` (the process
  module), `constraints/profiles/us-rulemaking/us-regulatory-artifact.cue`
  (the §5.2 regulatory-identifier overlay, which composes the kernel
  `#Artifact`), and `constraints/profiles/us-rulemaking/us-lifecycle-event.cue`
  (the §6 proceeding kinds, which composes the kernel `#LifecycleEvent` and
  binds the assembled kind union). Class-valued ranges for this module's
  predicates: `constraints/profiles/us-rulemaking/semantics/l0-ranges.cue`.
- Generated JSON Schema, Rust, TypeScript, and SHACL: produced by
  `tools/compile_all.sh` into `compiled/<target>/profiles/us-rulemaking/` and
  `crates/rkaf-core/src/generated/profiles/us_rulemaking/`.
- JSON Schema is an intentionally partial validation projection for calendar
  dates and cross-field ordering. It emits a lexical date pattern, `format:
  date`, and the `x-rkaf-order` annotation, but Draft 2020-12 processors may
  ignore `format` and unknown annotations. Calendar validity and interval
  ordering are normative only through Rulespec's `x-rkaf-order`-aware
  validator or the SHACL projection. A JSON-Schema-only consumer MUST NOT claim
  those checks unless its validator explicitly asserts both capabilities.
- Positive, negative, and edge fixtures: `fixtures/`
