# US Regulatory Identifiers, L0 Vocabulary Tier, and Rulemaking-Process Module

- **Date:** 2026-07-23
- **Status:** Draft for review
- **Type:** Design memo (`thoughts/specs/`), targeting normative changes in `spec/`
- **Companion:** spicy-regs `docs/superpowers/specs/2026-07-23-metadata-ontology-layer-design.md` (spec 1 of this pair — the consumer this memo serves)

## 1. Motivation

Spicy-regs is building a rule-identity metadata layer over the US federal regulatory corpus (regulations.gov dockets, Federal Register documents, Unified Agenda entries, CFR sections) and wants to be a Rulespec-conformant consumer. It cannot be one today, for three reasons:

1. **No US regulatory identifier schemes.** `rkaf:artifactIdentifierScheme` (core §4.1) covers ELI for EU legal resources and USLM/Akoma Ntoso for legislative markup, but has no scheme for CFR citations, RINs, Federal Register document numbers, or regulations.gov docket identifiers — the four identifiers the entire US regulatory system runs on.
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

Extend the closed enum `rkaf:artifactIdentifierScheme` (core §4.1). Per the closed-taxonomy discipline (§3), this ships in the next vocabulary release after the `v0.2.0-pre.7` consolidation lands.

New enum values and canonical identifier templates:

| Scheme | Identifies | Canonical form (candidate) | Notes |
| --- | --- | --- | --- |
| `rkaf:us-cfr` | A CFR unit (title, part, optional section) | `urn:rkaf:us:cfr:40:60.1` (`:40:60` at part level) | Normalization grammar normative: numeric title, part, dotted section, no spaces. GovInfo/eCFR URIs compose as additional identifiers (mode 3). |
| `rkaf:us-usc` | A U.S. Code unit (title, section) | `urn:rkaf:us:usc:42:7401` | Citation identity, distinct from the existing `rkaf:uslm-section` *selector* (which addresses substructure inside USLM markup — both compose on one Artifact). |
| `rkaf:us-rin` | A Regulation Identifier Number | `urn:rkaf:us:rin:2060-AV12` | Uppercase normalized. Identifies the *rulemaking*, not a document — pairs with the Proceeding entity (Deliverable C). |
| `rkaf:us-frdoc` | A Federal Register document | `urn:rkaf:us:frdoc:2017-07442` | The FR document number is GPO's persistent id; federalregister.gov URLs compose as mode-3 additional identifiers (mutable-URL-alone stays non-conformant per §4.1). |
| `rkaf:us-regsgov` | A regulations.gov docket, document, or comment | `urn:rkaf:us:regsgov:EPA-HQ-OAR-2021-0317` (docket); document/comment ids follow the same scheme | Agency-issued ids are already globally unique in practice; the normalization note documents known legacy exceptions. The comment-id form is fixture-exercised only until a consumer ingests comment ids (spicy-regs defers comment-level work). |
| `rkaf:us-pl` | A public law | `urn:rkaf:us:pl:117-58` | Bridges to statute artifacts before codification. Consumer exercise: spicy-regs `authority_edges.pl_number` (joins `congress_bills`). |
| `rkaf:us-eo` | An Executive order | `urn:rkaf:us:eo:14094` | Numeric normalization. EOs appear in Unified Agenda legal-authority strings alongside statutes; without a scheme those rows would stay raw-only. |

Exact URN syntax is a spec-PR decision; the normative content of this deliverable is: one scheme per identifier class above, a normalization grammar for each, and a statement of what each identifies (registry citation identity — the analog of ELI URIs for EU sources, per §9.4's do-not-reinvent rule: no US public body mints citation URIs today, so Rulespec minting them is composition-consistent).

**Validation-contract cost (§10):** each new enum value requires at least one positive and one negative fixture. Budget ~14 fixtures. Spicy-regs supplies real-world values (Deliverable D).

## 4. Deliverable B — L0 "Vocabulary" conformance tier

Add **L0** below L1 in `spec/rkaf-conformance.md`. Target: consumers whose carrier is not JSON-LD (tabular, SQL, parquet, CSV) but who want term-faithful use of the vocabulary.

An L0 implementation MUST:

1. Publish a **carrier-mapping document**: every column/field that carries Rulespec semantics maps to the `rkaf:` (or composed `skos:`/`prov:`/…) term it implements, with the term's IRI.
2. Use conformant identifier values (Deliverable A schemes, or existing schemes) for every identifier column, or document the compact↔canonical expansion (e.g. spicy-regs stores `40-60.1`, expands to `urn:rkaf:us:cfr:40:60.1`).
3. Preserve closed-enum discipline: enum-valued columns carry only registered values for that enum; no minted values (core §3).
4. NOT claim L1+ (no JSON-LD carrier is exercised).
5. Self-certify via the existing `conformance/partners/<implementation>.yaml`, extended with a `carrier_mapping:` field pointing at the mapping document and a `terms_used:` list.

**Carrier-mapping format (normative, part of this deliverable):** the mapping document embeds one or more fenced `yaml rkaf-l0-mapping` code blocks, each a list of entries `{table, column, term, enum_map?}` — `term` is the full IRI; `enum_map` gives column-value → registered-enum-value correspondences where the column carries an enum. Prose around the blocks is free. This format is defined here, not left to the audit tool's author, because the mapping document is the one artifact carrying obligations in both directions (spec 1's design record and this repo's L0 certification input) and its shape must not drift.

**Falsifiability gate:** a new `tools/l0_mapping_audit.py` that parses the fenced mapping blocks and verifies every referenced term and enum value exists in the vocabulary, including `enum_map` targets. Deliberately cheap — L0's guarantees are semantic fidelity and identifier conformance, not shape validation.

L0 composes with the adoption-depth axis unchanged: spicy-regs declares (L0, D1). The conformance doc's ladder table gains one row; L1–L4 are untouched.

## 5. Deliverable C — Rulemaking-process module (experimental)

New spec doc `spec/rkaf-rulemaking.md`, **Status: Experimental** — terms ship in a release (closed-taxonomy discipline applies) but the doc carries an explicit instability warning until spicy-regs' implementation has exercised the shapes against the full corpus. This is deliberate sequencing: vocabulary stabilizes *after* a real consumer proves it (the inverse of how the rest of Rulespec was built, and the lesson of it).

Entities, composing existing primitives rather than duplicating them:

- **`rkaf:Proceeding`** — a rulemaking proceeding. Identity: `rkaf:us-rin` and/or `rkaf:us-regsgov` docket identifier (a proceeding MAY span multiple dockets; a docket MAY host non-rulemaking activity — the entity is the proceeding, the docket is an identifier + container Artifact). Properties: `rkaf:proceedingStage` (closed enum: `rkaf:prerule`, `rkaf:proposed`, `rkaf:supplemental`, `rkaf:final`, `rkaf:withdrawn`, `rkaf:longterm`), issuing authority via existing `rkaf:hasAuthority`.
- **`rkaf:CommentPeriod`** — interval attached to a Proceeding; supports reopenings (0..* periods per proceeding); dates as `xsd:date`.
- **FR documents are plain `rkaf:Artifact`s** with `rkaf:us-frdoc` identifiers — no new document class. A new relation `rkaf:publishedInProceeding` links Artifact → Proceeding.
- **Stage transitions are `rkaf:LifecycleEvent`s** on the Proceeding — the existing lifecycle enum gains proceeding-stage event values rather than a parallel event system.
- **Rule targeting:** `rkaf:proceedingAffects` links a Proceeding to the CFR-unit Artifacts it amends or proposes to amend. This is the vocabulary-level twin of spicy-regs' `rule_targets` table.
- **Authority grounding:** a Proceeding's statutory basis uses the existing `rkaf:derivesAuthorityFrom` chain to `rkaf:us-usc` Artifacts — completing agency → *how the agency acted* → rule.

Composition citations: **ELI-DL** is the EU analog for pre-enactment lifecycle and is cited mode-4 (pattern) in this doc; promotion to an alignment row waits for an EU-corpus consumer, per §9.2.2 discipline.

**Non-goals:** comment content, commenter identity, campaign detection, and descriptive topic tagging stay consumer-side (spicy-regs spec 1). This module models the proceeding's structure and provenance, not public-participation analytics.

**Corpus-scale exercise (gates stabilization):** the reference corpus (Deliverable D) supplies fixtures; it is not a consumer. The consumer exercise for `Proceeding`, `proceedingStage`, `CommentPeriod`, and `publishedInProceeding` is spicy-regs' follow-on `proceedings` and `comment_periods` tables (spec 1 §7, promoting its existing `rulemaking_lifecycles` rollup), run at full corpus scale. That run is what surfaces the hard cases this module exists for — proceedings spanning multiple dockets, reopened comment periods, stage-transition sequences — and C does not stabilize without it.

**Validation-contract cost:** new class + relation fixtures, supplied from the reference corpus (Deliverable D). Budget ~15 fixtures.

## 6. Deliverable D — First L0 partner and US reference corpus

1. **`conformance/partners/spicy-regs.yaml`** — first L0 self-certification, filed when spicy-regs' `rule_targets` table and `docs/ontology.md` mapping document ship.
2. **`reference-corpora/us-rulemaking/`** — one complete real proceeding (docket, its FR documents, Unified Agenda entry, CFR targets, statutory authorities) as JSON-LD fixtures exercising Deliverables A and C end-to-end. Sourced from spicy-regs data; small (one proceeding), curated, and stable.

This is the falsifiability loop closing in both directions: Rulespec's §10 validation contract gets real-world US material; spicy-regs gets a conformance target that isn't self-referential.

## 7. Sequencing and release mechanics

1. **Land `v0.2.0-pre.7` consolidation first** (already on TODO) — this memo's changes do not ride that release.
2. **Release N+1 (small):** Deliverable A (enum extension + fixtures) and Deliverable B (L0 tier + audit tool). These are spicy-regs spec 1's prerequisites; spec 1's delivery order blocks on them and nothing else. If N+1 slips, spec 1 proceeds on provisional `x-` prefixed local terms with a committed rename after release — the enum, not the calendar, is the contract.
3. **Spicy-regs builds** `rule_targets` / `authority_edges` against N+1. Friction found here feeds back before C freezes anything.
4. **Release N+2:** Deliverable C (rulemaking module, experimental) shaped by step 3's experience, plus Deliverable D (partner YAML + reference corpus).
5. **Stabilization of C** (experimental → pre-release normative) only after the spicy-regs full-corpus `proceedings`/`comment_periods` run (spec 1 §7) and at least one non-spicy-regs consumer review. Candidate reviewer: the Axiom Foundation corpus pipeline, which keys on the same identifier space as Deliverable A and is the natural third consumer of the schemes.

## 8. Explicit non-changes

- No point-in-time work (exists at L4).
- No runtime restructuring (ladder already isolates it).
- No new concept/tagging vocabulary (SKOS composition already covers it; tags stay consumer-side).
- No change to L1–L4 semantics, the composition-mode framework, or the closed-taxonomy discipline — every addition above plays by the existing rules.
