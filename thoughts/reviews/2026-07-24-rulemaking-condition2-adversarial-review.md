# Condition-2 Stabilization Review: Rulespec US Rulemaking-Process Module (spec/rkaf-rulemaking.md §8)

**Review date:** 2026-07-24
**Module:** `rkaf-rulemaking` (Experimental), v0.2.0-pre.7 contract digest
**Terms under review:** `rkaf:Proceeding`, `rkaf:Docket`, `rkaf:CommentPeriod`, `rkaf:hasDocket`, `rkaf:publishedInProceeding`, `rkaf:proceedingAffects`, `rkaf:proceedingStage`, and the six `proceeding-*` `lifecycleEventKind` values
**Status:** Complete. Verdict: **do not graduate as-is; graduation is achievable after the preconditions in §5 land.**

---

## HONESTY DISCLOSURE

This review was conducted by adversarial AI reviewer personas run by the Rulespec maintainer, acting as a stand-in for the §8 condition-2 "non-originating consumer" review. **It is not an external organization's review.** No independent third party operated the review, selected the personas, or controlled the verification pipeline. The personas were instructed to owe the design no deference and every finding passed a refute-by-default verification gate, but the structural independence the §8 gate language contemplates was not present. Accordingly, the §8 gate language should be amended to describe this review accurately (adversarial simulated consumer review, maintainer-operated), **or the condition-2 gate should be held open** until a genuinely external consumer performs or ratifies an equivalent review. This disclosure is a permanent part of the review record.

---

## 1. Method

Six adversarial personas simulated distinct non-originating consumers, each walking the contract against a real corpus posture:

| Persona | Consumer posture |
|---|---|
| **litigation** | Tracker of challenged rules: vacaturs, stays, remands, CRA disapprovals |
| **identity** | Cross-partner identity resolution over reused RINs, joint rulemakings, merges/splits |
| **jurisdiction** | Portability probe: FCC/FERC/SEC registries, state (CA OAL) and EU analogs |
| **eligibility** | Decision-grade runtime answering "which proceedings touch the CFR unit I rely on" |
| **dataeng** | L0 tabular-carrier producer mapping regulations.gov / FR / Unified Agenda bulk data |
| **shapes** | Attack-fixture author probing the gap between prose invariants and compiled shapes |

Every filed finding was then run through **three-lens adversarial verification with refute-by-default**: a *spec lens* (does the contract text actually say what the finding claims, and is the gap a documented decision?), a *mechanical lens* (does the failure reproduce against the CUE sources, compiled projections, and `ci_validate`/`l0_mapping_audit` tooling?), and a *relevance lens* (is the scenario real, in-scope, and load-bearing at corpus scale?). The three §8 agenda items were separately decided by **three-judge panels** with independent written reasoning.

**Filtering evidence:** 4 findings were refuted outright and are reported only in the Appendix. Of the 20 findings that survived, 5 drew one refutation vote each and were retained with narrowed scope or reduced severity; the remaining 15 were confirmed unanimously, most with direct mechanical reproduction (attack fixtures validated or failed exactly as claimed). The originating consumer's evidence (spicy-regs ontology and friction report) was used to avoid re-reporting known friction and to hunt specifically for what the originating run missed — several confirmed findings (letter-suffixed CFR sections, FRDOC underscore dockets, the RIN evidence-loss under the module's own split mandate) are gaps the originating consumer's corpus run did not surface.

---

## 2. Term-Fitness Table

Aggregation rule: worst per-persona verdict wins; dissent noted.

| Term | Verdict | Reasoning (dissent noted) |
|---|---|---|
| `rkaf:Proceeding` | **strained** | Class boundary and partner-scoped identity are corpus-proven (4 personas: fit), but the one-identifier ceiling destroys RIN evidence under the module's own mandated splits, and required `hasAuthority (1..*)` was satisfied in practice only by information-free agency stubs (identity, eligibility: strained). |
| `rkaf:Docket` | **strained** | Mutable-container-not-Artifact is the right call everywhere, but the `us-regsgov` grammar rejects real underscore/FRDOC identifiers with no fallback prose, and every non-regulations.gov registry collapses to `partner-defined` (identity, jurisdiction, shapes: strained; litigation, eligibility, dataeng: fit). |
| `rkaf:CommentPeriod` | **strained** | Interval-per-node plus mandatory provenance is corpus-validated, but the Proceeding-only anchor forced discarding 14,263 real docket-scoped windows, and the shape cannot name the noticed document or distinguish window kinds (4 strained, 2 fit). |
| `rkaf:hasDocket` | **strained** | Semantics are exactly right and survived 21,007 multi-docket components (5 personas: fit); strained solely because the declared `rkaf:Docket` range is unenforced in the compiled shapes — pointing it at a Proceeding validates (shapes). |
| `rkaf:publishedInProceeding` | **strained** | Direction and 0..* cardinality handled cross-posting, joint documents, and principled abstention at corpus scale (5 personas: fit); strained solely because the `rkaf:Proceeding` range is unenforced, reopening the docket-as-proceeding hole (shapes). |
| `rkaf:proceedingAffects` | **unfit** | Three independent personas found it unproducible or wrong in its decision-grade purpose: zero real-corpus coverage across 334,989 rule targets under the edition-pinning MUST, a grammar that cannot cite the sections its own reference proceeding created, and ambiguous pre/post-amendment edition semantics (identity, eligibility, dataeng: unfit; litigation, jurisdiction, shapes: strained). |
| `rkaf:proceedingStage` | **unfit** | Optional-with-absence-means-unknown is corpus-validated and correct (identity, dataeng: fit), but for any corpus containing challenged or concluded rules the closed enum has no honest terminal value — producers must assert `rkaf:final` for void rules, misuse agency-only `rkaf:withdrawn`, or falsely claim ignorance (litigation, jurisdiction: unfit; eligibility, shapes: strained). |
| `proceeding-*` lifecycleEventKind values | **strained** | The six agency-action kinds accurately mirror Unified Agenda stages (dataeng, shapes: fit), but the family is blind to every judicial and congressional event and to merge/split continuity, and the closed-enum rejection rule converts those gaps into forced silence (litigation, identity, jurisdiction, eligibility: strained). |

---

## 3. Confirmed Findings

Severity reflects post-verification synthesis (filed severity adjusted where verifier downgrades carried the argument). All citations were verified against source; mechanically reproduced findings are marked **[repro]**.

### Blockers

**F-21. The module's central invariant — a docket is not a proceeding — is prose-only; no shape enforces any proceeding/docket reference class** *(shapes)* **[repro]**
*Scenario:* A regulations.gov-centric ingester mints one "proceeding" per docket: `hasProceedingIdentifier` set to `urn:rkaf:us:regsgov:EPA-HQ-OAR-2021-0317` under `partner-defined`, `commentPeriodFor` and `publishedInProceeding` pointed at the `rkaf:Docket` node, `hasDocket` pointed at a Proceeding. The full attack graph validates with 0 violations — the exact docket-fanout/RIN-collapse failure class the originating consumer's entire report exists to avoid.
*Evidence:* spec/rkaf-rulemaking.md:24-25, 42-43; spec/rkaf-vocabulary.md:52,56,57 (declared ranges unenforced); compiled/shacl/core/rulemaking.ttl:27,43; compiled/shacl/core/artifact.ttl:19 (pattern-only, no `sh:class`); constraints/core/rulemaking.cue:31,35,47. Verified: zero `sh:class` constraints exist anywhere in compiled/shacl/core/; the CUE→SHACL compiler has no reference-class primitive at all.
*Proposed change:* Teach the projector a reference-class assertion so `hasDocket`, `commentPeriodFor`, and `publishedInProceeding` compile to `sh:class rkaf:Docket` / `rkaf:Proceeding`; add a negative lexical guard (`hasProceedingIdentifier` MUST NOT match `^urn:rkaf:us:regsgov:`); add the attack graph as a negative fixture.

**F-8. `proceedingAffects` edition-pinning is unproducible from every public bulk source — zero real-corpus coverage across 334,989 rule targets** *(identity, dataeng)* **[repro]**
*Scenario:* Any NPRM amending 40 CFR part 60 (e.g. EPA proposal 2021-24202): the citation is known with certainty at publication, but no immutable edition-scoped Artifact exists to point at, and §6 rules an unversioned eCFR URL or compact citation non-conforming. The originating consumer emitted zero `proceedingAffects` edges from 334,989 rule_targets rows; a second consumer with the same public sources cannot either. Only the hand-curated fixture corpus exercises the term. Notably, the term is absent from the four terms the §8 gate required to run at corpus scale — it was never load-tested.
*Evidence:* spec/rkaf-rulemaking.md:151-157; spicy-regs/docs/ontology.md:237-240 (deliberate omission pending an "edition resolver" nobody has); ontology-friction-report.md:19. The mech lens additionally found the MUST is unenforced by any compiled shape (a forbidden unversioned target passes CI) — a second, separate gap.
*Proposed change:* Split the relation: keep `proceedingAffects` edition-pinned as the strong form; add `rkaf:proceedingAffectsCitation` (0..*, value = `urn:rkaf:us:cfr:*` citation IRI, no Artifact required) so bulk producers can publish targets now and upgrade later. Alternatively downgrade edition pinning to SHOULD with an explicit unresolved-edition marker.

**F-9. `commentPeriodFor` exactly-one-Proceeding anchor forces data loss for docket-scoped windows and duplicates joint-rulemaking windows** *(identity, dataeng)* **[repro]**
*Scenario:* regulations.gov serves comment windows on dockets, not proceedings. For any docket in a reused-RIN family resolving to multiple candidate proceedings (FAA RIN 2120-AA64), the window is precisely known but no conforming `CommentPeriod` can be emitted. The originating consumer excluded exactly 14,263 valid intervals (8,297 document + 5,966 FR) as "no unique proceeding component" — loss the contract forces (reproduced via the L0 audit range check). The same cardinality forces the joint EPA/NHTSA NPRM's single 60-day window (74 FR 49454) to be emitted as two duplicate nodes with no sameness link, contradicting `publishedInProceeding`'s 0..* handling of the identical joint-document problem.
*Evidence:* spec/rkaf-rulemaking.md:76; constraints/core/rulemaking.cue:47; constraints/semantics/l0-ranges.cue:10; ontology-friction-report.md:97-98; contrast spec/rkaf-vocabulary.md:56.
*Proposed change:* Relax `commentPeriodFor` to 0..* and add optional `rkaf:commentPeriodDocket` (0..*, range `rkaf:Docket`), with a Pattern-C constraint requiring at least one anchor of either kind. Docket-anchored periods upgrade when identity resolves; nothing valid is discarded meanwhile.

**F-15. `us-cfr` grammar cannot cite letter-suffixed CFR sections — section-level targets are unrepresentable for the module's own reference proceeding** *(eligibility, shapes)* **[repro]**
*Scenario:* RIN 2060-AV16 (the curated corpus proceeding) created 40 CFR part 60 subpart OOOOb, sections 60.5360b–60.5399b — every section letter-suffixed. The pattern `^urn:rkaf:us:cfr:[1-9][0-9]*:[0-9]+(\.[0-9]+)?$` rejects `urn:rkaf:us:cfr:40:60.5375a` (verified, ci_validate FAIL). The reference corpus itself silently retreats to part-level (`urn:rkaf:us:cfr:40:60`, a ~1,800-page part — not a decision-grade citation). Letter-suffixed sections are the standard mechanism for successor subparts (OOOOa, Reg Z 226.5a, FDA 101.9); `us-usc` already normalizes lowercase suffixes, so the asymmetry is unmotivated, and no frdoc-style fallback exists.
*Evidence:* constraints/core/artifact.cue:24-26; compiled/json-schema/core/artifact.schema.json:141; spec/rkaf-core.md:110-111; reference-corpora/us-rulemaking/v0.2/data/epa-oil-and-gas-climate-review.jsonld:106.
*Proposed change:* Extend the section component to `^urn:rkaf:us:cfr:[1-9][0-9]*:[0-9]+(\.[0-9]+[a-z]{0,3}(-[0-9a-z]+)*)?$` (lowercase normalization, matching us-usc); update §4.1 prose, recompile, add positive/negative fixtures, and cite at least one lettered section in the reference corpus.

**F-1. No honest terminal stage exists for proceedings ended by court, Congress, or non-rule completion** *(litigation, eligibility)* **[repro]** *(one verifier voted to downgrade to concern; retained as blocker because the eligibility failure — dead proceedings indistinguishable from live ones — is decision-changing)*
*Scenario:* American Lung Ass'n v. EPA vacated the ACE Rule (RIN 2060-AT67). The known current state is "final rule vacated"; the enum offers only `rkaf:final` (asserts a rule a court voided), `rkaf:withdrawn` (glossed "The agency withdrew the proceeding" — EPA never did), or omission (defined as "stage unknown" — but the state is precisely known). The CRA disapproval of the 2020 methane rule (Pub. L. 117-23) is identical: an act of Congress, not agency withdrawal. 628 Unified Agenda "Completed Actions" rows (merged/completed-without-rule RINs) hit the same gap. Naive producers will shoehorn everything into `rkaf:withdrawn`, the only terminal value.
*Evidence:* constraints/core/rulemaking.cue:15-16; spec/rkaf-rulemaking.md:32-41, 142, 145-147; compiled projections; ontology-friction-report.md:117-120. Mechanically reproduced (`rkaf:vacated` fails SHACL enum check); no exclusionary scope sentence exists anywhere in the spec.
*Proposed change:* Either (a) add `rkaf:terminated` plus required `rkaf:terminationCause` sub-enum {agencyWithdrawal, judicialVacatur, congressionalDisapproval, administrativeConclusion} with matching event kinds; or (b) narrowly redefine `proceedingStage` as agency-procedural-progress-only with a normative deferral sentence, add `rkaf:concluded` for evidence-backed non-rule terminations, and make `withdrawn`'s agency-only semantics unmistakable in the stage table.

**F-2. The event family records only agency actions; every judicial and congressional event is unrepresentable and inextensible** *(litigation)* **[repro]**
*Scenario:* The ACE Rule timeline — final (2019) → vacated (2021) → vacatur reversed by West Virginia v. EPA (2022) → repealed (2024) — has an event kind for only the first transition; the audit trail the module promises silently stops at `proceedingFinal` for three of four transitions. Same for the CPP's 2016 stay and CAIR's remand without vacatur. Because rkaf-core.md:43 requires consumers to REJECT unrecognized enum values, a litigation tracker cannot mint private kinds: the closed-enum policy converts a vocabulary gap into forced silence across the entire judicial-review corpus. Verified: no repurposing escape hatch exists — §5 binds `appliesTo` to the Proceeding for stage events and no generic kind semantically fits a non-agency actor's act.
*Evidence:* constraints/core/lifecycle-event.cue:8-14; spec/rkaf-rulemaking.md:134-147 (all six glosses begin "The agency…"); spec/rkaf-core.md:43.
*Proposed change:* Add `rkaf:proceedingVacated`, `proceedingStayed`, `proceedingRemanded`, `proceedingReinstated`, `proceedingDisapproved` (CRA) in the next release, or a single `proceedingJudicialAction` kind with a required closed qualifier. `rkaf:emittedBy` already accommodates courts and Congress as actors; only the kind space needs extension.

**F-6. Single-identifier Proceeding shape destroys RIN evidence under the module's own mandated splits** *(identity)* **[repro]** *(one verifier downgraded to concern; retained as blocker for the split-mandate case, with the joint-rulemaking illustration narrowed)*
*Scenario:* When FAA RIN 2120-AA64 (reused across 40,620 dockets) is split into partner-scoped Proceedings per rulemaking.md:48-51, the RIN survives only in the partner's Parquet carrier — `hasProceedingIdentifier` is cardinality-1, and the Artifact regulatory-identifier enum has no `rkaf:us-rin`, so the evidence that motivated the split has no home anywhere in the published graph; a second partner cannot join proceedings on RIN at all. (The joint EPA+NHTSA two-RIN illustration is weaker as filed: modeling two Proceedings, one per RIN, cross-linked via the shared Artifact/Docket, preserves both RINs — verifiers correctly narrowed the finding to the split-mandate case, which has no workaround.)
*Evidence:* spec/rkaf-rulemaking.md:24-27, 47-51; constraints/core/rulemaking.cue:31-32; constraints/core/artifact.cue:10-11, 18; ontology-friction-report.md:33-66; ontology.md confirmed to carry no L0 mapping row for the RIN column at all. (Mech lens also noted a projector inconsistency: SHACL lacks `sh:maxCount` here while CUE/JSON-Schema enforce 1.)
*Proposed change:* Add an optional repeatable non-identity pair on Proceeding — `rkaf:hasProceedingEvidenceIdentifier` (0..*) with scheme (`rkaf:us-rin` | `rkaf:partner-defined`) — mirroring the Artifact `hasRegulatoryIdentifier` "never establishes identity" discipline.

**F-7. No vocabulary for proceeding merge/split/supersession; identity continuity is trapped in the partner carrier** *(identity)* *(1 refutation vote of 3; retained — see note)*
*Scenario:* Unified Agenda Completed Actions routinely close RINs with "Merged with RIN …"; the originating assembler records continuity only in a carrier-local `identity_predecessors_json` column. A downstream consumer watches `pr-A` disappear and `pr-B` appear with no connecting edge. The six proceeding-* kinds cover only stage transitions and no Proceeding-to-Proceeding predicate exists.
*Verification note:* The relevance lens refuted the blocker framing by demonstrating the generic `rkaf:supersession` kind with `appliesTo` listing two Proceedings validates today. However, the mech lens showed that workaround is semantically unsound, not merely inelegant: per rkaf-behavior.md §2.1, every `appliesTo` entry is a cascade seed, so listing predecessor and successor together corrupts L4 cascade semantics, and `appliesTo` is unordered so direction is lost. The finding stands, narrowed: continuity is not cleanly or safely expressible, and the real corpus never uses the workaround.
*Evidence:* spec/rkaf-rulemaking.md:134-147; constraints/core/lifecycle-event.cue:8-15; ontology-friction-report.md:56-62; ontology.md:312-322.
*Proposed change:* Add `rkaf:proceedingSupersedes` (0..*, Proceeding → Proceeding), or `proceedingMerged`/`proceedingSplit` event kinds with defined directional semantics, making the friction report's predecessor trail expressible in the exchange format without corrupting cascade semantics.

### Concerns

**F-22. `us-regsgov` grammar rejects real regulations.gov identifiers (underscore FRDOC dockets) and contradicts core prose permitting fewer segments** *(shapes)* **[repro]** *(downgraded from blocker: `partner-defined` is a working escape hatch, so this is a missing-guidance/prose-contradiction defect, not a representability wall)*
*Scenario:* Every agency owns an `<AGENCY>_FRDOC_0001` docket; `urn:rkaf:us:regsgov:EPA_FRDOC_0001` fails the pattern `[A-Z0-9]+(-[A-Z0-9]+)+` (ci_validate FAIL reproduced), and unlike `us-frdoc`, §2.1 defines no fallback for out-of-grammar official IDs, while core prose says "known legacy identifiers may have fewer segments" against a shape hard-requiring ≥2 hyphen segments.
*Evidence:* constraints/core/rulemaking.cue:25; constraints/core/artifact.cue:34; spec/rkaf-core.md:113; spec/rkaf-rulemaking.md:61-68.
*Proposed change:* Widen to `^urn:rkaf:us:regsgov:[A-Z0-9]+([-_][A-Z0-9]+)*$`, or (if the narrow grammar is deliberate) add the frdoc-style normative fallback to §2.1 (out-of-grammar IDs use `partner-defined` and MUST NOT be labeled `us-regsgov`). Either way add `EPA_FRDOC_0001` as a fixture.

**F-16. `proceedingAffects` edition semantics are ambiguous: pre- vs post-amendment targeting is undefined and no relation names the produced edition** *(eligibility)* *(1 refutation vote; narrowed and downgraded from blocker: the "ordering is impossible" sub-claim was mechanically disproved — `proceedingFinal` events with `appliesTo` + `effectiveDate` do order competing amendments — but the direction ambiguity and the missing produced-edition relation stand)*
*Scenario:* §2 says a proceeding targets the unit it "amends or proposes to amend" (pre-change text), yet the curated corpus targets the CFR-2024 edition — text that already contains the final rule's result. Both readings conform; a consumer cannot tell whether a target edition includes the amendment, which is decision-changing for an eligibility runtime. The originating consumer's refusal to populate the term at all (pending an edition resolver) independently corroborates the friction.
*Evidence:* spec/rkaf-rulemaking.md:44, 126-128, 151-153; reference corpus (proceedingAffects → post-final CFR-2024 edition); ontology.md:236-240.
*Proposed change:* Fix the direction normatively (targets = pre-amendment edition in force); add optional `rkaf:proceedingProduces` (0..*, Proceeding → Artifact) for resulting editions; state that when stage is `final` a `proceedingFinal` event SHOULD exist; update §6 and the curated corpus.

**F-3. Stage conflates procedural progress with legal operativeness** *(litigation)*
*Scenario:* The Clean Power Plan (stayed by SCOTUS, never took effect) and CAIR (remanded without vacatur, fully operative) both read identically as `rkaf:proceedingStage rkaf:final`. Nothing scopes operativeness out, so consumers will misread `final` as in-effect. Verifiers confirmed no scoping sentence exists and, further, that the current contract offers no operativeness surface anywhere on Artifact (`hasEffectivePeriod` is domain-restricted to Warrant/Authority/ApplicabilityScope/Attestation) — the proposed remedy's mechanism needs a domain extension.
*Evidence:* spec/rkaf-rulemaking.md:32-41, 145-147; constraints/core/rulemaking.cue:33; spec/rkaf-vocabulary.md:136.
*Proposed change:* Add a normative §5 scope sentence (proceedingStage asserts procedural progress only, no claim of legal effectiveness), pair with the F-2 judicial event kinds so suspension/remand are timestamped, and address the effectiveness carrier (EffectivePeriod domain extension) as follow-on work.

**F-4. Partial vacatur is inexpressible: stage is proceeding-global and affected targets carry no status** *(litigation)*
*Scenario:* Mexichem Fluor v. EPA vacated the 2015 SNAP Rule 20 only in part — some CFR amendments survived, some fell. The contract can only describe the rule as wholly final or wholly gone; severability is the default remedial question in every APA challenge. Verifiers noted rulemaking.md:132 currently *forecloses* the fix (appliesTo "points to the Proceeding"), confirming rather than refuting inexpressibility.
*Evidence:* constraints/core/rulemaking.cue:33, 36; spec/rkaf-rulemaking.md:44, 132, 151-156; constraints/core/lifecycle-event.cue:21.
*Proposed change:* When adding judicial event kinds (F-2), specify their `appliesTo` MAY enumerate the specific CFR-unit Artifacts affected (a subset of `proceedingAffects` targets) — partial-vacatur scope from the existing list, no new node class.

**F-10. Every official registry except regulations.gov and RIN collapses into `partner-defined`, including US federal registries** *(identity, jurisdiction)* **[repro]**
*Scenario:* FCC docket 17-108 (~22M comments in ECFS), FERC RM21-17, SEC S7-31-22 are official federal registry identifiers squarely inside the module's declared scope, yet the two-value scheme enums force all of them to `partner-defined` — the same label the originating consumer uses for synthetic surrogate hashes. Two partners ingesting the same FCC docket mint incompatible IRIs with no graph-level join — exactly the failure the canonical regsgov grammar was minted to prevent.
*Evidence:* constraints/core/rulemaking.cue:11, 13, 24-26; spec/rkaf-rulemaking.md:26-27, 61-66; spec/rkaf-core.md:126-138; ontology.md:26-27.
*Proposed change:* Add one scheme value `rkaf:official-registry`, valid only with a new `rkaf:identifierRegistry` (1) IRI naming the issuing registry — keeps the enums closed and release-bound while preserving the official-vs-surrogate distinction. Alternatively mint release-bound per-system schemes (`us-fcc-ecfs`, `us-ferc`) with canonical grammars.

**F-17. `CommentPeriod` cannot name the document it solicits comment on; `prov:wasDerivedFrom` conflates evidence source with subject** *(eligibility)*
*Scenario:* RIN 2060-AV16 has two CommentPeriods; the corpus distinguishes them only by `@id` naming and by `wasDerivedFrom` happening to point at FR documents — but that relation is defined as "source evidence" and in the corpus itself mixes the noticed proposal with an unrelated extension notice in one array. A procedural-adequacy query ("was the provision added by the SNPRM opened to comment?") cannot bind period to notice.
*Evidence:* spec/rkaf-rulemaking.md:76-86; constraints/core/rulemaking.cue:45-54; reference corpus lines 147-166.
*Proposed change:* Add optional `rkaf:commentPeriodOpenedBy` (0..*, range `rkaf:Artifact`), keeping `wasDerivedFrom` strictly as evidence provenance; add to CUE, registry, and fixtures.

**F-19. The normative cross-posting unification edge (`dcterms:hasFormat`) is outside the registered vocabulary — L0 consumers cannot declare it and cross-org unification is non-interoperable** *(dataeng)* **[repro]**
*Scenario:* §4.1 tells consumers to unify postings "through the format links," but mapping `dcterms:hasFormat` at L0 fails the gate ("unregistered vocabulary term"), core §9.2.2 defers dcterms with no predicate import, the context declares only the prefix (no `@type: @id` coercion), and no shape, registry row, or fixture covers it — while the reference corpus uses it unvalidated. Each partner must mint a local link predicate; posting graphs cannot be unified and per-proceeding document counts double-count.
*Evidence:* spec/rkaf-rulemaking.md:120-127; spec/rkaf-core.md:378; context/rkaf-context.jsonld:7; tools/l0_mapping_audit.py:331-332; reference corpus lines 30, 47.
*Proposed change:* Promote `dcterms:hasFormat`/`isFormatOf` to a mode-1 import: context term definitions, optional Artifact CUE properties, registry rows, a cross-posting positive fixture, and inclusion in the L0-auditable term set. (This resolves agenda item 1 in favor of the current per-posting split — see §4.)

**F-20. `xsd:date` without timezone-normalization or inclusivity semantics lets two conformant producers publish different end dates for the same comment period** *(dataeng)* **[repro]**
*Scenario:* regulations.gov deadlines are 11:59:59 p.m. Eastern serialized as UTC instants; a UTC-truncating pipeline emits a `commentPeriodEnd` one day later than an FR-text-derived pipeline for every Eastern deadline in the corpus. Both pass all projections; the spec never states whether the end date is inclusive. (Mech lens additionally confirmed the compiled JSON Schema accepts even lexically invalid dates — see F-23.)
*Evidence:* spec/rkaf-rulemaking.md:77-78; constraints/core/rulemaking.cue:48-53; compiled projections; spec/rkaf-conformance.md:92-95.
*Proposed change:* Normative §3 note: start/end are inclusive calendar days in the deadline's governing timezone (US Eastern for regulations.gov/FR deadlines); producers deriving dates from instants MUST convert before truncation. In the L0 contract, require transform-with-samples when `value_kind:date` maps a datetime-typed column (noting the mapping DSL currently carries no source-column type metadata — the prose half is immediately actionable).

**F-23. The JSON Schema projection enforces neither interval ordering nor date validity, yet §9 declares the projections a validation authority for exactly those** *(shapes)* **[repro]**
*Scenario:* The corpus contains 7,178 real inverted comment intervals. An off-the-shelf Draft 2020-12 validator accepts all of them — and accepts `start: 2021-13-45, end: not-a-date` — because `format` is non-asserting and `x-rkaf-order` is an unknown keyword honored only by the in-house Rust validator. SHACL rejects both; a JSON-Schema-only consumer gets silent false negatives.
*Evidence:* spec/rkaf-rulemaking.md:204-207; compiled/json-schema/core/rulemaking.schema.json:201-238; crates/rkaf-validate/src/lib.rs:174.
*Proposed change:* Amend §9 to state the JSON Schema projection is partial for dates/ordering (normative only via SHACL or an `x-rkaf-order`-aware validator), and make the projector emit an enforceable approximation (date `pattern` + `$comment`, or require the format-assertion vocabulary).

**F-24. SHACL permits multiple simultaneous stages, stage on non-Proceeding nodes, and proceeding-* events applying to non-Proceedings** *(shapes)* **[repro]**
*Scenario:* One Proceeding carrying both `rkaf:proposed` and `rkaf:final`; a Docket carrying `proceedingStage rkaf:withdrawn`; a `proceedingWithdrawn` event whose `appliesTo` is a Docket — all three violate the declared contract (0..1, domain Proceeding, "appliesTo points to the Proceeding") and all validate with 0 violations in one attack graph. Multi-snapshot Unified Agenda merges make the first case an ordinary ingestion outcome, not a contrivance.
*Evidence:* compiled/shacl/core/rulemaking.ttl:29 (no `sh:maxCount`, target-scoped only); spec/rkaf-vocabulary.md:54; spec/rkaf-rulemaking.md:132; constraints/core/lifecycle-event.cue:21.
*Proposed change:* Emit `sh:maxCount 1` for all declared (1)/(0..1) properties; add a Pattern-C conditional on LifecycleEventShape (proceeding-* kind ⇒ `appliesTo` values `sh:class rkaf:Proceeding`); add `sh:targetSubjectsOf rkaf:proceedingStage` with `sh:class rkaf:Proceeding` so stage cannot ride on other classes.

### Observations

**F-13. No kind/scope discriminator on `CommentPeriod`: a limited-scope re-notice window is indistinguishable from a full reopening** *(jurisdiction)* *(1 refutation vote; downgraded — the named scenarios are out-of-federal-scope (CA) or outside the tested corpus (FCC), the bulk sources do not expose the distinction as structured data today, and §3 asserts only reopening⇒new-node, not the converse)*
*Proposed change (retained as forward-looking):* Optional `rkaf:commentPeriodKind` (0..1), closed enum {initial, extension, reopening, limited-scope, reply}, absence-means-unknown — additive, corpus-mapping-neutral, and useful the day a reply-comment consumer arrives.
*Evidence:* spec/rkaf-rulemaking.md:72-86; constraints/core/rulemaking.cue:45-54.

**F-18. L0 audit rejects `identifier_scheme` on `hasArtifactIdentifier`** *(dataeng)* *(1 refutation vote; downgraded — a spec-conformant two-entry encoding (plain template transform + separate `artifactIdentifierScheme` vocab mapping) passes the audit and asserts the same triples, so §4 identity IS declarable; what remains is an asymmetry: `hasArtifactIdentifier` is missing from `IDENTIFIER_TERMS` while the three rulemaking identifier properties are present)*
*Proposed change:* Add `hasArtifactIdentifier`→`artifactIdentifierScheme` to the audit's identifier tables, add a documents-table mapping example to §0.1, add an L0 fixture, refreeze the digest.
*Evidence:* tools/l0_mapping_audit.py:63-75, 434-438; spec/rkaf-conformance.md:32-34; spec/rkaf-rulemaking.md:90-103.

---

## 4. Agenda Resolutions (§8 stabilization agenda)

### Item 1 — Cross-posting pattern (§4.1): one Artifact per posting vs repeatable regulatory-identifier pair
**Verdict: KEEP (3–0).**
All three judges independently rejected the repeatable pair on the same decisive ground: under JSON-LD/RDF set semantics the {identifier, scheme} pair is two parallel unordered properties, so repetition loses per-pair correlation, and the compiled per-scheme validation (conditional `sh:hasValue`+`sh:pattern` branches; conjunctive `allOf/if/then`) makes a mixed-scheme node fail *both* grammars simultaneously — repeatability is unvalidatable without reifying pair nodes, a far larger change than any observed corpus pressure justifies. Per-posting emission is also row-parallel and monotonic for L0 producers (799,759 FR rows arrive one-per-posting), while merging breaks payload immutability, hash anchoring, and selector stability.
**Converged recommendation (synthesis of the majority's best-argued amendments):** keep the pair at 0..1 and harden the kept contract in the same release: (a) name the normative cross-producer unification key — posting Artifacts are the same posting iff a `hasArtifactIdentifier` value matches; RECOMMEND `@id` = permanent publication URL; upgrade the `dcterms:hasFormat`/`isFormatOf` SHOULD to MUST when one producer emits both postings in the same graph, with a canonical direction; (b) promote `dcterms:hasFormat`/`isFormatOf` to a mode-1 import with context coercion, registry rows, and fixtures (= F-19); (c) strike the unsound "unify at the Proceeding" clause; (d) emit `sh:maxCount 1` for the pair — the "at most one pair" rule is currently unenforced in SHACL; (e) resolve the most-specific-scheme squeeze so presidential documents' FR citations have a home (instrument citations on a distinct instrument Artifact); (f) record the judges' corroboration of F-22 (underscore grammar) and F-8/F-9 companions, which two judges independently rediscovered.

### Item 2 — `rkaf:hasAuthority` required (1..*) on Proceeding
**Verdict: CHANGE (3–0).**
All three judges found the "no friction" evidence from the condition-1 run to be an artifact of vacuous satisfaction: the originating consumer met the requirement by templating `agency_code` into information-free agency-stub Authority nodes (ontology.md:149-161) while its real authority citations were excluded from materialization — i.e., the constraint was satisfied by exactly the placeholder-minting the agenda item asks about. Coverage of genuine authority data is ~1–3% of 334,753 proceedings, official sources publish "Not Yet Determined" as a legal-authority value, and the decision-grade guarantee is hollow anyway because `derivesAuthorityFrom` is optional — required 1..* guarantees a node, not a chain.
**Converged recommendation:** make `hasAuthority` optional (0..*) on Proceeding with absent-means-unknown, symmetric with `proceedingStage`; non-empty when present; add a MUST NOT-placeholder rule (no Authority node minted from agency identity alone to satisfy presence; when a source supplies a citation, SHOULD emit the edge); recompile projections; convert the missing-authority negative fixture into a "Not Yet Determined" positive plus an empty-array negative; split the registry cardinality per domain; and relocate the decision-grade guarantee to a consumption-side profile gate requiring hasAuthority present AND `derivesAuthorityFrom` resolving to edition-scoped Artifacts.
*(Note: the separately filed "placeholder-fabrication pressure" finding was refuted as filed — no fabrication is mechanically forced — but the panel's change verdict rests on independent grounds: semantic degradation of the predicate and vacuous satisfaction at corpus scale.)*

### Item 3 — Stage-value naming: unprefixed shared IRIs vs prefixed forms
**Verdict: CHANGE (3–0).**
All three judges found the documented convention (rulemaking.md:36-41) licenses unprefixed sharing only for values with a genuine generic-status reading — which covers `rkaf:proposed` but not `prerule`, `supplemental`, or `longterm` (Unified Agenda jargon squatting on root tokens in a flat namespace), and only ambiguously covers `final`/`withdrawn` (UA "Final Rule Stage" means *working toward* a final rule — the reference corpus carries `rkaf:final` for a proceeding whose rule was still pending). Property-scoping holds in CUE/JSON but not in the RDF projection, where one IRI bears one definition; §7's planned ELI-DL binding makes collision anticipated, not speculative. This is the declared last cheap moment: the entire migration cost is a handful of repo files plus the originating consumer's six-line enum_map, re-pinned each release anyway.
**Converged recommendation (majority form, judges 1 and 3):** rename the six stage values to the six existing prefixed lifecycleEventKind IRIs — `rkaf:proceedingPrerule`, `proceedingProposed`, `proceedingSupplemental`, `proceedingFinal`, `proceedingWithdrawn`, `proceedingLongterm` — so the stage value space is exactly the proceeding-* subset of the event enum, and add the normative identity "proceedingStage, when present, MUST equal the lifecycleEventKind of the latest stage-family LifecycleEvent when any exists," making the §5 stage/event correspondence machine-checkable. Judge 2 dissented on IRI reuse (state vs transition should not share IRIs), preferring distinct `proceedingStage*` forms; if the maintainer shares that objection, the dissent's form is the sanctioned fallback — but the bare tokens must not ship. Update rulemaking.cue:15-16, projections, vocabulary registry, fixtures, the reference corpus, the §2 rationale paragraph, and coordinate the spicy-regs enum_map edit in the same release. Genuinely generic shared statuses (`rkaf:proposed` on adoptionStatus/conceptStatus) are unaffected.

---

## 5. Overall Verdict

**The module does not merit graduation from Experimental in its current state.** Two of the eight terms are unfit as shipped (`proceedingAffects`, `proceedingStage`), the module's central prose invariant is wholly unenforced by its compiled shapes, and three of its load-bearing contracts (edition-pinned targets, Proceeding-only comment anchors, the single-identifier ceiling) are contradicted by the only corpus-scale deployment in existence.

**However, no finding indicts the module's architecture.** The class boundaries (Proceeding ≠ Docket ≠ Artifact), the identity discipline, the interval-per-node CommentPeriod design, the evidence requirements, and the per-posting cross-posting pattern all survived adversarial review — every confirmed defect is repairable additively or by shape/prose hardening. Graduation is warranted after the following preconditions land:

**Preconditions for graduation:**

1. **Shape enforcement of declared invariants** (F-21, F-24, agenda-1d): reference-class assertions (`sh:class`) on `hasDocket`/`commentPeriodFor`/`publishedInProceeding`; `sh:maxCount` for all declared (1)/(0..1) properties including the regulatory-identifier pair; the proceeding-* `appliesTo` conditional; negative fixtures for the a1/a2 attack graphs.
2. **`proceedingAffects` made producible and unambiguous** (F-8, F-15, F-16): citation-level companion relation (or SHOULD-grade edition pinning with an unresolved marker); letter-suffix `us-cfr` grammar extension; normative pre-amendment direction plus optional `proceedingProduces`; reference corpus updated.
3. **CommentPeriod completeness** (F-9, F-17, F-20): 0..* proceeding anchor + optional docket anchor with a Pattern-C at-least-one rule; `commentPeriodOpenedBy`; timezone/inclusivity note in §3.
4. **Terminal-state and judicial vocabulary** (F-1, F-2, F-3, F-4): terminal stage value(s) with terminating-actor distinction or a normative agency-progress-only scope plus `concluded`; judicial/congressional event kinds; operativeness scope sentence; partial-vacatur `appliesTo` scoping.
5. **Identity evidence and continuity** (F-6, F-7): proceeding evidence-identifier pair (us-rin); a directional Proceeding-to-Proceeding continuity mechanism.
6. **The three agenda resolutions implemented as decided**: keep-and-harden cross-posting (including the dcterms mode-1 promotion, F-19), `hasAuthority` → 0..* with the no-placeholder rule, stage-value renaming.
7. **Grammar and tooling hygiene** (F-22, F-23, F-18, F-10): `us-regsgov` widening or a normative fallback; §9 JSON-Schema partiality statement; `hasArtifactIdentifier` in the L0 audit identifier tables; an `official-registry` scheme decision (may be deferred with an explicit documented-deferral sentence naming FCC/FERC/SEC, which currently does not exist).
8. **§8 gate language amended** per the Honesty Disclosure: either record that condition 2 was satisfied by a maintainer-operated adversarial simulation, or hold the gate open pending an external consumer's review or ratification of this one.

---

## 6. Appendix: Refuted Findings

Reported for transparency; none appear in the findings above. The four refuted
finding IDs are F-5, F-11, F-12, and F-14. They require no implementation work.

| Refuted finding | Term | One-line refutation |
|---|---|---|
| Court-compelled proceedings and judicial instruments have no worked contract surface | `rkaf:hasAuthority` | Already representable today via the existing `rkaf:legal` AuthorityKind plus the generic §4.1 Artifact pattern; a documentation-example gap, not a contract defect (self-rated observation). |
| Unified-Agenda stage semantics minted on generic IRIs in a closed, consumer-unextensible enum | `rkaf:proceedingStage` | Sole concrete scenario (CA OAL/CARB state rulemaking) is outside the module's explicitly declared US-federal scope (rulemaking.md:14); the live naming-convention core of the complaint is agenda item 3, which the panel resolved on its own merits. |
| Generic predicate whose normative range contract is written exclusively in CFR terms | `rkaf:proceedingAffects` | §7 explicitly and deliberately defers EU/ELI-DL integration pending an EU-corpus consumer; the CFR-only prose matches declared scope — a documented decision, not an oversight. |
| Required hasAuthority creates placeholder-fabrication pressure; the saving issuing-agency reading is unstated | `rkaf:hasAuthority` | Mechanically disproved: an organizational Authority with no `derivesAuthorityFrom` validates cleanly, and the "issuing" reading is explicit at rulemaking.md:28; the cited 903-row evidence belongs to a different property. (The agenda-2 panel nonetheless changed the cardinality on independent, verified grounds.) |

Additionally, 5 of the 20 confirmed findings (F-7, F-13, F-16, F-18, F-22) each drew one refutation vote from the three-lens panel and were retained only after their claims were narrowed or their severity reduced, as noted inline — evidence that the refute-by-default filter operated on confirmed findings as well as rejected ones.
