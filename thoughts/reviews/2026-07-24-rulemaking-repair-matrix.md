# US rulemaking stabilization repair matrix

**Status:** Repair implementation complete; clean paired corpus receipt pending  
**Source review:** `2026-07-24-rulemaking-condition2-adversarial-review.md`  
**Contract digest:** `sha256:ea9b899ba92955b83638ece811d7a4b744dd912f72e19290e32c97508674de1c`

This matrix records how the Experimental US rulemaking contract changed in
response to the maintainer-operated adversarial simulation. It does not satisfy
the non-originating-consumer gate. Graduation still requires an independent
consumer to review these repaired artifacts or ratify the source review against
them.

## Review-to-change matrix

| Finding | Normative decision | Enforcement and executable evidence |
| --- | --- | --- |
| F-21 — Docket/Proceeding class boundary | Preserve distinct classes and require typed reference ranges. | The CUE-to-SHACL compiler emits `sh:class` from the L0 range registry. `rulemaking-reference-class-confusion-negative.jsonld` attacks `hasDocket`, `commentPeriodFor`, and `publishedInProceeding`. |
| F-8 — edition-only affected targets were unproducible | Add `proceedingAffectsCitation` for edition-independent compact citations; keep `proceedingAffects` for resolved pre-action editions. | CUE, context, range registry, SDKs, vocabulary prose, reference corpus, and Spicy Regs carrier coverage exercise the citation relation. |
| F-9 — exactly-one Proceeding lost valid comment windows | Make `commentPeriodFor` repeatable and optional; add repeatable `commentPeriodDocket`; require at least one of the two. | The CUE disjunction projects to JSON Schema and SHACL. `commentperiod-docket-only-positive.jsonld`, the joint edge fixture, and the no-anchor negative path cover the rule. |
| F-15 — letter-suffixed CFR sections | Widen `us-cfr` through one-to-three lowercase suffix letters plus hyphenated subsegments. | Identifier grammar, fixtures, compiler tests, reference corpus, and the Spicy Regs row validator cover `40 CFR 60.5375a`. |
| F-1 — no honest terminal state | Add `rkaf:concluded` and require `proceedingTerminationCause` when selected. | Positive and missing-cause negative fixtures exercise the conditional. |
| F-2 — no judicial/congressional event family | Add external legal and congressional lifecycle kinds to the rulemaking event family. | Lifecycle CUE, generated SDK enum, vocabulary prose, and the external-event fixtures cover the extension. |
| F-6 — RIN evidence was lost by split identity | Add repeatable `hasProceedingEvidenceIdentifier` plus its scheme pair; retain `us-rin` as evidence, never forced identity. | Positive RIN-evidence fixture, negative grammar fixture, L0 identifier audit tables, and Spicy Regs corpus receipt cover the pair. |
| F-7 — continuity was trapped in one carrier | Add directional `proceedingSupersedes` between distinct Proceeding identities. | CUE/context/range entries and `proceeding-continuity-positive.jsonld` cover the relation. The Spicy Regs receipt rejects self-supersession. |
| F-22 — real regulations.gov identifiers failed | Permit one or more alphanumeric segments separated by hyphens or underscores. | Updated CUE grammar, fixtures, and source-membership corpus validation cover ordinary, underscore, and single-segment values. |
| F-16 — affected/produced edition direction was ambiguous | Define `proceedingAffects` as the pre-action edition and add `proceedingProduces` for immutable post-action outputs. | Normative §2 prose, CUE/context/ranges, and the reference corpus record both directions; consumers may omit unresolved editions. |
| F-3 — stage implied legal operativeness | Scope `proceedingStage` to agency procedural progress and explicitly deny an operativeness claim. | Normative §2/§5 prose and lifecycle-event separation make the distinction explicit. |
| F-4 — partial vacatur was proceeding-global | External legal events must target a Proceeding and may additionally scope affected Artifacts. | `lifecycleevent-partial-vacatur-positive.jsonld` and the no-Proceeding negative fixture cover the shape. |
| F-10 — official registries collapsed into partner-defined | Add `official-registry` plus mandatory `proceedingIdentifierRegistry`. | Positive and missing-registry negative fixtures cover FCC-style identities without pretending they are partner-defined. |
| F-17 — opening document was conflated with provenance | Add repeatable `commentPeriodOpenedBy` with Artifact range. | CUE/context/range entries, comment fixtures, reference corpus, and carrier validation distinguish opening Artifacts from later evidence. |
| F-19 — cross-posting predicate was undeclarable | Import `dcterms:hasFormat` and `dcterms:isFormatOf` in mode 1; retain one Artifact per posting. | Artifact CUE/context/ranges and `artifact-cross-posting-positive.jsonld` cover canonical direction and inverse. |
| F-20 — date inclusivity/timezone was undefined | Define inclusive calendar days in the governing deadline timezone; conversion precedes truncation. | Normative §3 prose and comment-period transform tests enforce the producer rule. |
| F-23 — JSON Schema overstated date/order coverage | Emit a lexical date pattern and state that calendar validity/order require the Rulespec validator or SHACL. | Compiler tests and §9 capability language prevent JSON-Schema-only overclaiming. |
| F-24 — SHACL missed cardinality, domain, and event-range rules | Emit scalar `sh:maxCount`; constrain stage subjects; require Proceeding targets for stage-family events; enforce latest-stage agreement. | Dedicated negatives cover multiple stages, stage on Docket, Docket-targeted stage event, and latest-stage mismatch. |
| F-13 — comment-period kind | Defer as a non-blocking trigger until an in-scope corpus exposes the distinction. | The canonical TODO retains the trigger; no speculative closed enum was added. |
| F-18 — Artifact identifier audit asymmetry | Add `hasArtifactIdentifier` and `hasProceedingEvidenceIdentifier` to the L0 identifier/scheme tables. | L0 unit fixtures execute both scheme-bearing transforms. |
| Agenda 1 — cross-postings | Keep one immutable Artifact per posting, use permanent posting identity, and link co-emitted formats. | Artifact constraints, DCTERMS imports, cross-posting fixture, L0 mapping, and corpus source-membership filtering implement the decision. |
| Agenda 2 — required authority | Make Proceeding authority optional; prohibit agency-shaped placeholders; move decision-grade completeness to a consumption profile. | CUE/SHACL no longer require `hasAuthority`; unknown-authority positive coverage replaces the old missing-authority negative. |
| Agenda 3 — stage names | Reuse the six `proceeding-*` lifecycle IRIs and require agreement with the latest stage-family event. | CUE/context/generated SDKs, reference corpus, negative fixtures, and the Spicy Regs enum projection use the same values. |

## Corpus-discovered conformance hardening

The repaired full-corpus rehearsal found one additional L0 defect that samples
could not reveal: a raw carrier column may contain uncorroborated values that
must remain available without being projected. The L0 mapping format now
supports `source_membership` on a one-column mapping. It means an exact carrier
value participates only when found in a named source-of-record column. The
mapping audit validates the declaration; a corpus receipt must report projected
and excluded counts and fail any projected nonmember. This is deliberately not
a lexical “drop invalid values” escape hatch.

Spicy Regs uses that rule for `documents.fr_doc_num` against
`federal_register.document_number`. Its final paired receipt is the corpus
evidence for the mapping, including every artifact hash, source/prior-state
hash, exclusion count, and gate log digest.

## Remaining gates

- A clean paired receipt must bind the repaired Rulespec commit and digest, the
  Spicy Regs implementation commit, identical baseline/candidate inputs, all
  seven candidate artifacts, and the full gate sweep.
- A Rulespec maintainer must choose and publish the release.
- A non-originating consumer must review the repaired contract or ratify the
  simulated review against it.

Until all three hold, the module remains Experimental.
