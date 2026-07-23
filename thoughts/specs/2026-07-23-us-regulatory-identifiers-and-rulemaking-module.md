# US Regulatory Identifiers, L0 Vocabulary Tier, and Rulemaking-Process Module

- **Date:** 2026-07-23
- **Status:** Implemented with architecture-review, full-corpus consumer, and
  2026-07-23 post-implementation review corrections (cross-posting pattern,
  `us-regsgov` legacy fallback, full-scheme corpus); independent review
  remains pending
- **Type:** Design memo (`thoughts/specs/`), targeting normative changes in `spec/`
- **Companion:** spicy-regs `docs/superpowers/specs/2026-07-23-metadata-ontology-layer-design.md` (spec 1 of this pair — the consumer this memo serves)

## 1. Motivation

Spicy-regs is building a rule-identity metadata layer over the US federal regulatory corpus (regulations.gov dockets, Federal Register documents, Unified Agenda entries, CFR sections) and wants to be a Rulespec-conformant consumer. It cannot be one today, for three reasons:

1. **No US regulatory identifier schemes.** Artifact identity covers immutable
   source material, but Rulespec has no separate vocabulary for CFR citations,
   RINs, Federal Register document numbers, or regulations.gov docket
   identifiers—the identifiers the US regulatory system runs on.
2. **No conformance tier below L1.** The ladder starts at L1 (parse JSON-LD). Spicy-regs is parquet/SQL — it will never emit JSON-LD as its primary carrier, yet it wants to use Rulespec term semantics, identifier schemes, and closed enums with a documented mapping. There is currently no conformant way to do that.
3. **No rulemaking-process vocabulary.** Rulespec models rules and their lifecycle but not the proceeding that produces them. A rule's origin story — docket opened, NPRM published, comment period run, final rule issued — has no entities. ELI-DL covers the EU draft-legislation analog; the US notice-and-comment process has nothing.

This memo also matters beyond spicy-regs: it gives Rulespec its first real Level-0 partner, its first US regulatory reference corpus, and the upstream half of the legal-family warrant story (a regulation's `rkaf:derivesAuthorityFrom` chain currently jumps from agency to rule with no account of how the agency acted).

## 2. Current-state audit (what this memo does NOT need to build)

Verified against the repo at `f63327e`:

- **Point-in-time semantics exist.** `rkaf:PointInTimeException`, `evaluationAnchor` handling, and L4 behavior contracts (§4 of `rkaf-behavior.md`) with PIT fixtures. No change proposed.
- **Runtime optionality exists.** The L1–L4 ladder already makes the Rust runtime an L4-only concern. No "demote the runtime" work is needed; this memo only adds a rung below L1.
- **Concept machinery is SKOS-native.** `rkaf:RegisteredConcept` composes `skos:Concept`; mappings use SKOS predicates exclusively. Spicy-regs' descriptive tags stay consumer-side (retrieval-grade, fast-churn) and align via `skos:exactMatch` to `rkaf:LocalConcept`/`RegisteredConcept` nodes where warranted — no new concept vocabulary is proposed.
- **Composition discipline (§9) governs everything below.** Where a public scheme owns an identifier, we compose; we mint only what nothing else owns.

## 3. Deliverable A — US regulatory identifier schemes

Do not extend `rkaf:artifactIdentifierScheme`: that enum identifies an
immutable edition, publication, snapshot, or payload. Add separate US
regulatory-identifier properties for Artifacts and dedicated identity
properties for Proceedings and Dockets. Per the closed-taxonomy discipline
(§3), these ship in the next vocabulary release after the
`v0.2.0-pre.7` consolidation lands.

New enum values and canonical identifier templates:

| Scheme | Identifies | Canonical form (candidate) | Notes |
| --- | --- | --- | --- |
| `rkaf:us-cfr` | A CFR unit (title, part, optional section) | `urn:rkaf:us:cfr:40:60.1` (`:40:60` at part level) | `rkaf:regulatoryIdentifierScheme`; the Artifact still needs an edition-scoped GovInfo URI, hash, or snapshot identity. |
| `rkaf:us-usc` | A U.S. Code unit (title, section) | `urn:rkaf:us:usc:42:7401` | `rkaf:regulatoryIdentifierScheme`; distinct from the `rkaf:uslm-section` selector. |
| `rkaf:us-rin` | A Regulation Identifier Number | `urn:rkaf:us:rin:2060-AV12` | `rkaf:proceedingIdentifierScheme`; a reused RIN cannot be the unique key for split Proceedings. |
| `rkaf:us-frdoc` | A Federal Register document | `urn:rkaf:us:frdoc:2017-07442` | `rkaf:regulatoryIdentifierScheme`; the strict grammar is `YYYY-NNNNN`. Other official forms use the permanent federalregister.gov URL as Artifact identity and MUST NOT be labeled `rkaf:us-frdoc`. |
| `rkaf:us-regsgov` | A regulations.gov docket, document, or comment | `urn:rkaf:us:regsgov:EPA-HQ-OAR-2021-0317` (docket); document/comment ids follow the same scheme | `rkaf:docketIdentifierScheme` for mutable Dockets; `rkaf:regulatoryIdentifierScheme` for document/comment Artifacts. |
| `rkaf:us-pl` | A public law | `urn:rkaf:us:pl:117-58` | `rkaf:regulatoryIdentifierScheme`; the Artifact also identifies the immutable publication. |
| `rkaf:us-eo` | An Executive order | `urn:rkaf:us:eo:14094` | `rkaf:regulatoryIdentifierScheme`; the Artifact also identifies the immutable publication. |

Exact URN syntax is a spec-PR decision; the normative content of this deliverable is: one scheme per identifier class above, a normalization grammar for each, and a statement of what each identifies (registry citation identity — the analog of ELI URIs for EU sources, per §9.4's do-not-reinvent rule: no US public body mints citation URIs today, so Rulespec minting them is composition-consistent).

**Validation-contract cost (§10):** each new enum value requires positive and
malformed negative coverage in the CUE-generated JSON Schema and SHACL
targets. Docket identity, malformed dates, and reversed intervals receive the
same parity coverage. Spicy-regs supplies real-world values (Deliverable D).

## 4. Deliverable B — L0 "Vocabulary" conformance tier

Add **L0** below L1 in `spec/rkaf-conformance.md`. Target: consumers whose carrier is not JSON-LD (tabular, SQL, parquet, CSV) but who want term-faithful use of the vocabulary.

An L0 implementation MUST publish a version-pinned carrier map that declares
each mapping's source columns, subject type, predicate, relationship
direction, value kind, collection behavior, class range, and deterministic
transform. IRI transforms include executable examples; identifier transforms
name their scheme. Closed enum mappings remain explicit. The self-certificate
uses `[L0]` alone and lists the exact mapped term set.

**Carrier-mapping format (normative, part of this deliverable):** the mapping
document embeds one or more fenced `yaml rkaf-l0-mapping` blocks. Each block
contains the exact CUE/context/range contract digest and a non-empty
`mappings` list. The normative field rules live in
`spec/rkaf-conformance.md`; prose around the blocks is free.

**Falsifiability gate:** `tools/l0_mapping_audit.py` verifies the contract
digest, entry schema, registered subject/domain/range, forward or inverse
direction, value kind, enum targets, transform behavior, and expected samples.
Given a certificate, it also checks the exact term set and rejects a mixed
L0/L1+ declaration.

L0 deliberately omits adoption depth. Appendix D defines integration depth for
the structured Rulespec substrate, not for a vocabulary-only non-JSON-LD
carrier; calling L0 “D1” would silently redefine that axis. L1–L4 are
otherwise untouched.

## 5. Deliverable C — Rulemaking-process module (experimental)

New spec doc `spec/rkaf-rulemaking.md`, **Status: Experimental** — terms ship
in a release (closed-taxonomy discipline applies), and the doc carries an
explicit instability warning until an independent consumer reviews the
full-corpus-corrected shapes. Spicy Regs completed the first stabilization gate
on 2026-07-23. This is deliberate sequencing: vocabulary stabilizes *after* a
real consumer proves it (the inverse of how the rest of Rulespec was built, and
the lesson of it).

Entities, composing existing primitives rather than duplicating them:

- **`rkaf:Proceeding`** — a rulemaking proceeding, identified by a RIN when
  that RIN is unambiguous or by a stable partner-scoped identifier otherwise.
  A docket identifier never establishes Proceeding identity.
- **`rkaf:Docket`** — the mutable administrative container, with its own
  `hasDocketIdentifier` and scheme. `rkaf:hasDocket` links Proceedings to
  Dockets many-to-many. A Docket is not an immutable Artifact.
- **`rkaf:CommentPeriod`** — interval attached to a Proceeding; supports
  reopenings (0..* periods per proceeding); dates as `xsd:date`; requires
  `prov:wasDerivedFrom` evidence so disagreements and quarantined source dates
  remain attributable.
- **FR documents are plain `rkaf:Artifact`s** whose permanent publication URL
  establishes Artifact identity and whose `rkaf:us-frdoc` value is a separate
  regulatory identifier. A new relation `rkaf:publishedInProceeding` links
  Artifact → Proceeding. A document cross-posted to more than one registry
  (the same proposed rule as FR document and regulations.gov docket document)
  is one Artifact per posting — each with at most one regulatory-identifier
  pair — linked with `dcterms:hasFormat`/`isFormatOf` (spec §4.1, added by
  the 2026-07-23 post-implementation review).
- **Stage transitions are `rkaf:LifecycleEvent`s** on the Proceeding — the
  existing lifecycle enum gains proceeding-stage event values rather than a
  parallel event system. `rkaf:proceedingStage` is optional; absent evidence
  means unknown and is never coerced to prerule.
- **Rule targeting:** `rkaf:proceedingAffects` links a Proceeding to a
  versioned CFR Artifact. A compact or unversioned citation is insufficient
  until resolved to an edition.
- **Authority grounding:** a Proceeding's statutory basis uses the existing `rkaf:derivesAuthorityFrom` chain to `rkaf:us-usc` Artifacts — completing agency → *how the agency acted* → rule.

Composition citations: **ELI-DL** is the EU analog for pre-enactment lifecycle and is cited mode-4 (pattern) in this doc; promotion to an alignment row waits for an EU-corpus consumer, per §9.2.2 discipline.

**Non-goals:** comment content, commenter identity, campaign detection, and descriptive topic tagging stay consumer-side (spicy-regs spec 1). This module models the proceeding's structure and provenance, not public-participation analytics.

**Corpus-scale exercise (first stabilization gate, completed 2026-07-23):**
the reference corpus (Deliverable D) supplies fixtures; it is not a consumer.
Spicy Regs ran `Proceeding`, `proceedingStage`, `CommentPeriod`, and
`publishedInProceeding` through its full public corpus. The run required stable
partner-scoped identity for reused RINs, a normative permanent-URL fallback for
non-`YYYY-NNNNN` Federal Register numbers, qualified CommentPeriod evidence,
and an optional unknown stage. Those corrections are now part of the contract.
Independent consumer review remains required.

**Validation-contract cost:** new class + relation fixtures, supplied from the reference corpus (Deliverable D). Budget ~15 fixtures.

## 6. Deliverable D — First L0 partner and US reference corpus

1. **Spicy-regs L0 self-certification** — filed in the consumer repository
   beside `docs/ontology.md`, its exact carrier map, and corpus evidence.
2. **`reference-corpora/us-rulemaking/`** — one complete real proceeding (docket, its FR documents, Unified Agenda entry, CFR targets, statutory authorities) as JSON-LD fixtures exercising Deliverables A and C end-to-end. Sourced from spicy-regs data; small (one proceeding), curated, and stable.

This is the falsifiability loop closing in both directions: Rulespec's §10 validation contract gets real-world US material; spicy-regs gets a conformance target that isn't self-referential.

## 7. Sequencing and release mechanics

1. **Land `v0.2.0-pre.7` consolidation first** (already on TODO) — this memo's changes do not ride that release.
2. **Release N+1 (small):** Deliverable A (enum extension + fixtures) and Deliverable B (L0 tier + audit tool). These are spicy-regs spec 1's prerequisites; spec 1's delivery order blocks on them and nothing else. If N+1 slips, spec 1 proceeds on provisional `x-` prefixed local terms with a committed rename after release — the enum, not the calendar, is the contract.
3. **Spicy-regs builds** `rule_targets` / `authority_edges` against N+1. Friction found here feeds back before C freezes anything.
4. **Release N+2:** Deliverable C (rulemaking module, experimental) shaped by step 3's experience, plus Deliverable D (partner YAML + reference corpus).
5. **Stabilization of C** (experimental → pre-release normative) after at
   least one non-Spicy Regs consumer review. The Spicy Regs full-corpus
   `proceedings`/`comment_periods` gate completed on 2026-07-23. Candidate
   reviewer: the Axiom Foundation corpus pipeline, which keys on the same
   identifier space as Deliverable A and is the natural third consumer of the
   schemes.

## 8. Explicit non-changes

- No point-in-time work (exists at L4).
- No runtime restructuring (ladder already isolates it).
- No new concept/tagging vocabulary (SKOS composition already covers it; tags stay consumer-side).
- No change to L1–L4 semantics, the composition-mode framework, or the closed-taxonomy discipline — every addition above plays by the existing rules.
