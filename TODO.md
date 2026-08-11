# Rulespec TODO

## Constraints (Layer 2) — close as done

- [x] CUE source, 6-target compilation, adversarial fixtures, parity orchestrator, CI gates all green
- [ ] Close the plan: note the architecture delta (Python compiler vs planned Rust `rkaf-constraints-compile` crate) in CHANGELOG. The `constraints/README.md` already documents the deferral. No code needed — declare done.

## Projectors (Layer 4) — two real gaps

- [ ] Implement `validate()` on JSON-LD projector — currently returns `Ok(())`. Extract the rkaf partition and validate against compiled JSON Schema.
- [ ] Implement `validate()` on OpenAPI projector — currently returns `Ok(())`. Validate the `x-rkaf` carrier structure against compiled schema.
- [ ] Add Derive fixture comparison to `tools/projector_parity.py` — currently only exercises round-trip. Add a Derive gate: run derive on a source fixture, compare byte output to expected file.

Gate C (studio-profile CUE derivation) is **not** a projector gap — it's a Studio cutover concern. The CUE projector cannot yet round-trip `$defs`/`x-lm`/prose. Drop from this scope.

## Conformance (Layer 6) — ratify current architecture

The plan specified `rkaf-conformance` Rust binary + `suite.index.json` + `conformance/v0.2/levels/` docs. None of that was built. The current architecture (Python reporter + `rkaf-runtime-cli` + directory-walking) delivers L1–L4 gating with 301 fixtures, 0 core divergences. Ratify it.

- [ ] Author `docs/conformance/partner-disclosure-howto.md` — step-by-step instructions for partners to produce a conformance disclosure YAML.
- [ ] Fold any missing L1–L4 level detail into `spec/rkaf-conformance.md` (already has level descriptions at lines 106–118). Do not create separate `conformance/v0.2/levels/` files.
- [ ] Rewrite the Layer 6 plan (`thoughts/plans/2026-05-12-rkaf-layer6-conformance-v0.2.md`) self-review checklist to match what actually shipped.
- [x] Consolidate unreleased CHANGELOG entries (Plans 7a–7e, ADR-0093) into a versioned `v0.2.0-pre.7` release. Bump `VERSION`.

## US regulatory vocabulary and rulemaking follow-through

- [x] Land and tag the prerequisite `v0.2.0-pre.7` consolidation. The tag points
  to `7205347`; the US identifier, L0, and rulemaking work remains Unreleased.
- [ ] Decide the release shape before tagging: the memo prescribed two releases (N+1: identifiers + L0; N+2: rulemaking module + corpus), but all four deliverables sit together in Unreleased. Either cut them as two tags or record in the memo why one combined release preserves the sequencing intent (2026-07-23 architecture review, FINDING 2). Record in the same decision where the assertion, concept, and analysis contract reshape (section below) lands relative to these tags.
- [ ] Regenerate `conformance/partners/rulespec-reference.yaml` via `tools/conformance_report.py --self-certify` at the release cut — it is pinned to `0.2.0-pre.6` with a 2026-05-17 corpus run and predates the US-identifier fixtures (2026-07-23 architecture review, FINDING 6).
- [ ] File `conformance/partners/spicy-regs.yaml` only after spicy-regs ships both `rule_targets` and `docs/ontology.md`, then run `tools/l0_mapping_audit.py` against that real mapping.
- [x] Record the 2026-07-24 maintainer-operated adversarial simulated-consumer review and its three agenda decisions. The simulation is evidence, not a non-originating review.
- [ ] Keep `spec/rkaf-rulemaking.md` Experimental until a non-originating
  consumer reviews the repaired RIN agenda-item contract or ratifies the
  simulated review against it.

### Rulemaking stabilization repair batch

Source:
`thoughts/reviews/2026-07-24-rulemaking-condition2-adversarial-review.md`.
Its verdict is **do not graduate as-is**.
F-5, F-11, F-12, and F-14 were refuted and require no implementation work.

- [x] Enforce declared graph invariants (F-21, F-24, agenda item 1): teach the projector reference-class constraints; emit `sh:maxCount` for every 1 and 0..1 property; constrain stage subjects and proceeding-event targets; preserve the Docket/Proceeding boundary; add the reproduced attack graphs as negative fixtures.
- [x] Make rule targets producible and unambiguous (F-8, F-15, F-16): add a citation-level target or a documented unresolved-edition path; support letter-suffixed CFR sections; define pre-amendment target direction and optional produced-edition semantics; update the reference corpus.
- [x] Preserve complete comment-period evidence (F-9, F-17, F-20): support Proceeding or Docket anchors with an at-least-one constraint; name the opening Artifact separately from provenance; define inclusive dates in the governing timezone; add joint, docket-only, reopening, and datetime-conversion fixtures.
- [x] Represent terminal and external legal events (F-1, F-2, F-3, F-4): define honest terminal-state semantics; add judicial and congressional event kinds; state that proceeding stage does not assert legal operativeness; support partial-vacatur target scope.
- [x] Preserve agenda identity, relationship evidence, and Proceeding continuity
  (F-6, F-7): model a RIN as a durable `RegulatoryAgendaItem`; connect it to
  independently identified Proceedings through provenance-bearing qualified
  relations; retain directional Proceeding supersession without misusing
  cascade-seeding `appliesTo`.
- [x] Implement all three agenda decisions: keep and harden per-posting cross-posting, promote `dcterms:hasFormat`/`isFormatOf` as a mode-1 import (F-19), make Proceeding `hasAuthority` optional with a no-placeholder rule, and replace all six bare stage IRIs.
- [x] Close grammar and tooling gaps (F-22, F-23, F-18, F-10): widen `us-regsgov` or document its fallback; state and test JSON Schema's date/order limits; add `hasArtifactIdentifier` to the L0 identifier tables and fixtures; implement an official-registry scheme or explicitly defer it with FCC/FERC/SEC named.
- [x] Amend §8 to disclose that the simulated review did not satisfy the non-originating-consumer gate and to keep that gate open.
- [x] Record F-13 as a non-blocking vocabulary trigger: add `commentPeriodKind` only when an in-scope corpus or consumer supplies the distinction.
- [x] Regenerate every affected projection and SDK type, run `make compile` and `make test`, publish a review-to-change matrix, and rerun the adversarial fixtures.
- [x] Complete the local paired Spicy Regs carrier migration: materialize agenda
  items, editioned observations, and evidence-qualified item-to-Proceeding
  relations; remove agenda-state/authority/CFR fan-out to Proceedings; and
  update the L0 map, candidate digest, corpus report, and local receipt. Filing
  the partner certificate remains a separate release task above.
- [x] Require the paired gate receipt to bind the Rulespec commit and contract digest, spicy-regs commit, candidate corpus snapshot id, every artifact hash, and every gate result. Do not accept unbound command output as corpus evidence.

**Done when:** Every §5 graduation precondition has a normative decision,
generated enforcement, positive and negative coverage, and corpus evidence;
both repositories pass their full gates against the same released contract; and
a non-originating consumer reviews or ratifies the repaired module.

## Assertion, concept, and analysis contract reshape (paired with Spicy Regs)

Execution source of truth: `../spicy-regs/TODO-RULE.md` Milestone A, governed
by the canonical vision
(`../spicy-regs/docs/superpowers/specs/2026-07-25-rulespec-spicy-regs-complete-vision-goal.md`).
Carrier evidence: the corpus receipts and evaluation records linked from that
backlog. This contract must release before Spicy Regs publishes relationship,
value, or concept data under it.

- [x] Move U.S. identifiers, `publishedInProceeding`, and domain lifecycle
      values out of the universal kernel into explicit profiles.
      Done 2026-07-25: commits `2cdf3ee` (US identifiers,
      `publishedInProceeding`, and the rulemaking module into
      `constraints/profiles/us-rulemaking/` with overlay-wins bindings and
      duplicate-collision hard errors) and `fcd8ba6` (profile-extended
      lifecycle closure per the decision below, ownership audit across all
      compiled sinks, cross-file enum projection restored). Both
      adversarially reviewed; gates green at digest `sha256:ce795eab…`,
      315 conformance fixtures, 0 divergences.
      Maintainer decision 2026-07-25 for the lifecycle half: keep one
      `rkaf:LifecycleEvent` class (`spec/rkaf-rulemaking.md` §6 stands) and
      adopt profile-extended closure — the kernel CUE owns only the 10
      universal kinds, the US rulemaking profile contributes the 12
      `proceeding-*` kinds, and the compiler assembles the closed value
      union at build time. Conditions: compiled artifacts must expose the
      layering honestly (kernel target without profile kinds, composed
      target with them, conformance walking the composed one), and a
      compile-time ownership audit must prove every kind is owned by
      exactly one module (replacing the interim
      `test_kernel_domain_value_debt_does_not_grow` allowlist).
- [x] Fix CUE shape composition in every projector so generated formats
      preserve composed constraints. Done 2026-07-25: commit `c7055cb`
      (facet-level unification, loud failure on unresolvable/cyclic bases,
      `#AssertionEnvelope` extracted and composed by `#Assertion` and
      `#RelationshipAssertion` with deliberate narrowings; adversarially
      reviewed; all gates green at digest `sha256:4b5d224c…`).
- [x] Define `AssertionEnvelope` with distinct `RelationshipAssertion` and
      typed-literal `ValueAssertion`; keep immutable proposition content
      separate from acceptance, disposition, confidence, attestation, and
      mutable consumer state. Done 2026-07-25: commit `85f6cbb`
      (ValueAssertion with closed typed-literal carriage on all six
      targets; AssertionProposition/ConsumerDisposition split; chained
      adversarial review, 343 fixtures, 0 divergences).
- [x] Separate source claimant, extraction provenance, model derivation, and
      human approval. Done 2026-07-25: commit `85f6cbb` (SourceClaimant,
      ExtractionActivity, mapped AILineage/Attestation roles; open
      conflict on AILineage's required humanApprover recorded in
      `spec/rkaf-core.md` §2.4 pending its own task).
- [x] Finish immutable Artifact version and revision identity; stabilize
      `SourceFragment` identity with exact artifact, selector,
      coordinate-system, and content-digest bindings. Done 2026-07-25:
      commit `177ace3` (evidence-or-nothing lineage, typed OA selectors
      with required coordinate system, content digests; chained
      adversarial review, 392 fixtures, 0 divergences).
- [x] Add `ConceptScheme`, SKOS-compatible concepts and mappings, and
      evidence-bearing `ConceptAssignment` for Artifacts and SourceFragments.
      Done 2026-07-25: commit `177ace3` (ConceptScheme, SKOS *Match trio,
      required skos:inScheme, ConceptAssignment composing the shared
      assertion envelope with same-artifact evidence enforcement).
- [x] Place relation changes, comparison contexts, resolver proofs, and
      neutral findings outside the kernel; keep `ClosureClaim` Experimental
      and disabled. Done 2026-07-26: commit `f01391d` — constraints/analysis/ module, five contracts,
      four-mechanism ClosureClaim disablement, omission unrepresentable;
      chained adversarial review, 420 fixtures, 0 divergences.
- [x] Regenerate normative prose, CUE, context, vocabulary, SHACL, SDK types,
      runtime behavior, fixtures, and reference corpora; add semantic carrier
      tests; run all gates from a clean checkout. Done 2026-07-26: commit
      `56686d9` (cross-surface completeness sweep; 30-test semantic carrier
      suite over the seven mandated categories, mutation-verified; runtime
      and reference-corpora decisions documented). Clean-checkout record
      2026-07-26: detached worktree at `56686d9`, cold `make compile`
      reproduces the committed pins (`sha256:5f287a1e…`), `make test`
      exit 0, 420 conformance fixtures, 0 divergences.
- [x] Close the carried follow-up from the Spicy Regs v3 second-half handoff:
      TypeScript closure of language-tagged value objects. Done 2026-07-26,
      LOCAL AND UNCOMMITTED — no hash yet; the orchestrator commits it.
      The generated TypeScript now closes the value object on both halves it
      can express: `_ts_type` types every JSON-LD value-object member the CUE
      does not declare as `never` (`"@language"?: never` today), and the same
      value-object emitter path in `target_typescript` emits one
      `Object.keys(...).some(...)` guard closing over the declared members, so
      an arbitrary extra key is caught where structural typing cannot forbid
      it. TypeScript was the last unclosed target — JSON Schema already emitted
      `additionalProperties: false`, Rust `deny_unknown_fields`, and SHACL
      rejects a language-tagged literal because expansion drops the datatype.
      Language-tagged literals remain OUTSIDE the v0.2 `ValueAssertion`
      carrier; this closes the hole, it does not admit them.
      Evidence (local, pending commit): new
      `TypedLiteralCarriageTests.test_typescript_closes_the_value_object`
      failed on both halves before the emitter change and passes after;
      `spec/rkaf-core.md` §2.2 now names TypeScript closure as an enforcement
      surface, and the CHANGELOG's "CLOSED on every target" parenthetical is no
      longer overstated; `make compile` reproduces the pins
      (`sha256:5f287a1e…`, unchanged — only
      `compiled/typescript/core/value-assertion.ts` moved, and `compiled/` is
      untracked, so no generated file was hand-edited); `make test` exit 0 —
      154 cargo tests, 170 Python unit tests, 0 core parity divergences (the
      two documentation-class adversarial findings are the unchanged
      baseline), 420 conformance fixtures, 0 divergences.
- [ ] Complete the non-originating-consumer review, then cut one reviewed
      pre-1.0 release with an immutable contract digest (maintainer
      authorization required).

**Release train:** decided with the release-shape item above. Default: a
separate release after the pending US-identifier/L0/rulemaking tag(s); record
the final decision in both this file and `../spicy-regs/TODO-RULE.md`.

## Consumer-requested contract simplifications (Spicy Regs)

Consumer evidence: `../spicy-regs/docs/decisions.md`, entry
"2026-07-27 — Contract-assumption validation results", which recorded three
optional Rulespec simplifications as informational and non-blocking after an
adversarial validation of the consumer plan's contract assumptions. The
maintainer authorized landing them ahead of the pre-1.0 release cut. RULE-005
is satisfied: each is driven by a named consumer finding, not by a
repo-internal preference.

- [x] Normative tabular/inlined Attestation pattern for L0 implementers.
      Done 2026-07-27: `spec/rkaf-conformance.md` §0.1 gains
      "Attestation as a table" — a separate attestations table, one row per
      Attestation node, `rkaf:targets` as the outward join, six required
      columns, and four rules (an `approved_by` column is not an Attestation;
      rejection is a row and an absent row means unreviewed; revocation is
      `rkaf:revokedAt`, not a delete; `rkaf:targets` is many). Inlining is
      permitted as a storage choice and capped at one attestation per record.
      "Never a field" is unchanged and restated — the pattern shows how a
      separate table SATISFIES it.
      The worked mapping is gated:
      `L0MappingAuditTests.test_the_normative_conformance_examples_are_executable`
      audits every `rkaf-l0-mapping` block in the conformance spec, and
      `fixtures/attestation-tabular-projection-positive.jsonld` (one approval
      and one rejection over the same `rkaf:ConceptAssignment`) is gated at
      L1-L3. The pattern needed one audit fix to be expressible:
      `enum_map` now covers closed enums the context coerces with `@type: @id`
      (`rkaf:decision`, `rkaf:assertionOrigin`), which previously had no way to
      declare closed-enum discipline at all. Contract digest UNCHANGED at
      `sha256:5f287a1e…` — no CUE, context, or range-registry byte moved.
- [x] Carrier-local fragment URN for `rkaf:assignmentEvidence`.
      Done 2026-07-27: `rkaf:FragmentIdentityScheme` (Core §4.2) registers a
      second identity form for a cited region —
      `urn:rkaf:fragment:<percent-encoded artifact IRI>:<start>:<end>:sha256-<64 hex>`,
      half-open `[start, end)` over Unicode code points, unit and selector kind
      FIXED by the scheme, digest scoped to the selected text. The offsets match
      `../spicy-regs/docs/ontology.md` "Anchor semantics" exactly.
      `rkaf:assignmentEvidenceScheme` is REQUIRED whenever evidence is present,
      mirroring `rkaf:regulatoryIdentifierScheme`; declaring
      `rkaf:carrier-local-fragment` binds every value to the derived grammar on
      all six targets. The class range STANDS — the URN satisfies it by
      construction. Two hand-authored shapes close the per-value conditional
      and the URN/`oa:hasSource` agreement CUE cannot express.
      Coverage: 1 positive, 4 negatives, 3 parity rows, 3 L0 audit tests, and a
      worked L0 mapping in Conformance §0.1 gated by the executable-examples
      test. Contract digest MOVED
      `sha256:5f287a1e…` -> `sha256:5aaac340bc21c7728fa70c250b7f74134dbb855804076f571a31144923d65cb7`;
      `make compile` re-pinned `spec/rkaf-conformance.md` and the corpus
      manifest, and no generated file was hand-edited.
      BREAKING for producers already emitting `rkaf:assignmentEvidence`: they
      add `rkaf:assignmentEvidenceScheme: rkaf:published-fragment`. Sixteen
      in-tree fixtures were updated accordingly.
- [x] Machine-legible scope carve-outs (`excluded_terms:`) in the L0
      conformance-file format, replacing freeform notes prose the audit never
      parsed. Done 2026-07-27: `tools/l0_mapping_audit.py` validates optional
      `excluded_terms` and `excluded_tables` on an L0 declaration — each a
      non-empty duplicate-free list; every excluded term registered AND
      unmapped, every excluded table unmapped. `MappingAudit` gained `tables`
      to carry that comparison. Absent means the declaration said NOTHING about
      scope, never "everything else is out"; backward compatibility is a test,
      not an assumption. Documented in Conformance §0.1 ("Scope carve-outs"),
      §6, `conformance/self-certification.template.yaml`, and `tools/README.md`.
      Five new audit tests. Contract digest UNCHANGED at
      `sha256:5aaac340…` — the declaration format is not part of the CUE,
      context, or range-registry contract.

## Single-document projection findings (Spicy Regs)

Consumer evidence: `../spicy-regs/docs/evidence/`
`single-document-rulespec-projection-2026-07-28/README.md` (spicy-regs
`3b48d00`) — one real Federal Register document (FSIS 2026-03227, 91 FR 7926)
hand-authored end to end as a complete RKAF object and driven through this
repo's own L1/L2/L3 gates. Its "Judgment calls" and "What the contract could
not express" sections carry the six findings below, each with its cite.
RULE-005 is satisfied: every item names a consumer finding, not a repo-internal
preference. The contract is unreleased with one consumer, so the breaking items
are batched into one revision rather than deferred into compatibility debt.

- [x] G1 — the `prov:Entity` class range on `prov:wasDerivedFrom` is enforced
      by every compiled shape and stated by no prose.
      Done 2026-07-28: Core §2.4 gains a **Derivation** paragraph — the range
      is `prov:Entity`, a producer citing a derivation source at L1–L4 MUST
      materialize it as a typed node in the same document, an IRI described
      nowhere stays legal as a cross-document reference, and the typed node
      needs nothing but `@id` and `@type`. Documentation only; no shape,
      fixture, or generated artifact moved and the contract digest is
      unchanged at `sha256:50929102…`.
      NOT closed by this item: the `prov:wasDerivedFrom` row in
      `spec/rkaf-vocabulary.md` still sits in the rulemaking-profile table and
      names only the two profile domains, so the kernel assertion envelope's
      use of the edge has no vocabulary row. Fixing that means restructuring
      the universal-primitives table, which is a separate change.
- [x] G3 / J1 — `#AssertionOrigin` has no value for a record a deterministic
      parser or join produced, so the projection claimed `rkaf:imported` and
      demoted its real method to an optional edge.
      Done 2026-07-28: `rkaf:deterministicExtraction` added to the closed enum
      (Core §2.4 "Deterministic origin", §3, vocabulary closed-enum list). It
      means a mechanically reproducible derivation, not an interpretive
      judgment, and it REQUIRES `rkaf:hasExtractionProvenance` on every
      compiled target — the same conditional idiom the AI-touched origins use
      for `rkaf:hasAILineage` — so the seam J1 named is closed: the method is
      no longer droppable. The referenced activity's `rkaf:extractionMethod`
      MUST be `rkaf:deterministicParse` or `rkaf:ruleBasedExtraction`; that
      half is a producer obligation, not a mechanical check, because the
      activity may live in another document. `rkaf:imported` is unchanged and
      undeprecated. Coverage: 1 positive, 1 negative, 2 parity rows; the stale
      `reviewClassified`/`systemDerived` names in
      `shapes/rkaf-shapes-pattern-c.ttl`'s message were corrected en route.
      Contract digest MOVED
      `sha256:50929102…` -> `sha256:162eb506edf161b47683bdbae2d76e2853f04d5d38758b6890fe566f43f30d17`.
      `make test` exit 0 — 154 cargo tests, 185 Python unit tests, 428
      conformance fixtures, 0 divergences.
      BREAKING under §3's reject-unrecognized-values rule.
- [x] J2 / G4 — `rkaf:requestContractDigest` is REQUIRED on every
      `rkaf:ExtractionActivity` but presumes a request-shaped extraction, so a
      deterministic table parse had to fabricate a canonical-json envelope to
      satisfy it.
      Done 2026-07-28: the digest is now REQUIRED for `rkaf:modelExtraction`
      and OPTIONAL for the other four methods, expressed with the shape's own
      `if extractionMethod == …` idiom rather than made optional everywhere —
      the guard that requires a model call to name its model now requires it
      to name its contract too. Core §2.4 states the producer rule (a digest
      over an envelope minted to satisfy the field is non-conforming) and the
      consumer rule (an absent digest is not an unaudited run; for a
      deterministic method the reproduction handles are `rkaf:inputDigest`,
      `rkaf:extractedBy`, `rkaf:extractorVersion`). The existing negative
      fixture was re-pointed from a deterministic parse to a model call and
      keeps its name and verdict; one new positive covers the new capability.
      Surfaced a real compiler bug en route: the SHACL emitter wrote only
      `then_require[0]` of a conditional, so the two-property guard compiled to
      a one-property guard while JSON Schema and TypeScript carried both.
      `tools/constraints_parity.py` caught it as a core divergence. Fixed, with
      `ShapeCompositionTests::test_a_conditional_requiring_two_properties_reaches_shacl_intact`
      as the regression; every single-requirement guard compiles
      byte-identically. Contract digest MOVED
      `sha256:162eb506…` -> `sha256:6b957d68cf91f3bf6d95979debdbf3205ab592bdd0a346a197d173352f23d636`.
      `make test` exit 0 — 154 cargo tests, 186 Python unit tests, 429
      conformance fixtures, 0 divergences.
- [x] G2 / J4 — no document→docket predicate; the only docket edge hangs off
      `Proceeding`, so a producer with dockets and no proceedings model cannot
      express an FR-native fact.
      Done 2026-07-28: `rkaf:publishedInDocket` (domain `rkaf:Artifact`, range
      `rkaf:Docket`, 0..*) added to the US rulemaking profile and registered in
      its `l0-ranges.cue`, so the compiled SHACL carries `sh:class
      rkaf:Docket`. New rulemaking §5.3 states how it relates to the
      Proceeding-scoped `rkaf:hasDocket`: independent, not substitutes; neither
      implies the other; a consumer MUST NOT infer either from the other; and
      §3.2's rule that docket membership never establishes proceeding identity
      is unchanged. Purely additive — no existing document changes verdict.
      Coverage: 1 positive with a parity row, 1 class-range negative gated via
      `tools/validate_negatives.py` (the route every `sh:class` negative takes,
      since JSON Schema cannot follow a reference). Contract digest MOVED
      `sha256:6b957d68…` -> `sha256:7d45dcd2f5ff6391b185fd98099740b34d3b6cac8ed66c99196e6ac368806553`.
      `make test` exit 0 — 154 cargo tests, 186 Python unit tests, 431
      conformance fixtures, 0 divergences.
- [x] G5 — direct profile edges and reified `RelationshipAssertion`s can state
      the same edge twice with no guidance, so a provenance-stripping consumer
      double-counts.
      Maintainer decision 2026-07-28, implemented the same day in
      `spec/rkaf-core.md` §2.1 ("Projected edges and reified assertions"):
      the direct edge is the QUERYABLE PROJECTION and the assertion is the
      PROVENANCE-BEARING SOURCE OF TRUTH; where both are present over the same
      triple the edge IS that assertion's projection and a consumer MUST count
      one statement, never two agreeing sources. A producer emitting an
      affirmed assertion whose triple a profile predicate can express SHOULD
      also emit the edge; it MUST NOT emit the edge for a denied, superseded,
      or retracted assertion, because a plain edge carries no polarity and
      projecting a denial asserts its opposite. A direct edge with no matching
      assertion is legal and unbacked — a consumer MUST NOT manufacture the
      missing assertion. `spec/rkaf-rulemaking.md` §5.3 and §8 point at the
      rule rather than restating it.
      Not mechanically checked, and the spec says why: no shape can require a
      producer to project an edge it declined to project, and matching a
      direct predicate against a reified triple compares a predicate IRI to a
      property VALUE, which SHACL does not express. Same class as §4.7.3 rule
      3. Documentation only; contract digest unchanged at `sha256:7d45dcd2…`.
      `make test` exit 0 — 154 cargo tests, 186 Python unit tests, 431
      conformance fixtures, 0 divergences.
- [x] G6 — `rkaf:attestedAt`, `rkaf:revokedAt`, and `rkaf:rationale` have no
      context terms, so attestation timestamps expand as plain strings while
      `rkaf:assertedAt` expands as `xsd:dateTime`.
      Done 2026-07-28: the sweep found the defect is not three terms but ten.
      Every property annotated `// xsd:dateTime` in the CUE now carries that
      coercion in `context/rkaf-context.jsonld` — `attestedAt`, `revokedAt`,
      `adoptedAt`, `openedAt`, `closedAt`, `declaredAt`, `resolvedAt`,
      `validatedAt`, `retroactiveFrom`, `sunsetAt` — and `rkaf:rationale` is
      declared `xsd:string`. The convention `context/README.md` listed as
      ungated is a gate:
      `TypedValueCarrierTests::test_every_xsd_annotated_term_carries_that_datatype_in_the_context`
      reads the annotation off the source and requires the coercion; it
      reported exactly these ten before the fix. No term added since the
      tabular-attestation change `b613ba3` is missing — `bc88c02`'s
      `rkaf:assignmentEvidenceScheme` was declared with it. The remaining 20
      unentered CUE property terms are reference- and string-valued and stay
      under the by-hand convention; `@id` coercion changes what a value MEANS
      and is not a sweep-safe edit. Contract digest MOVED
      `sha256:5aaac340…` -> `sha256:50929102ff3cf8e047fa116dbd67f99790e0b2f6cdbb82fb12c05cc8ff15eeca`;
      `make compile` re-pinned the conformance example and the corpus
      manifest. `make test` exit 0 — 154 cargo tests, 185 Python unit tests,
      426 conformance fixtures, 0 divergences.

## Rust SDK (Layer 5) — umbrella crate

Registry client + federation are blocked on Plan 4. The ~80% below is buildable today from existing ingredients.

- [ ] `crates/rkaf/Cargo.toml` — umbrella crate depending on `rkaf-core`, `rkaf-validate`, `rkaf-projector-core`, `rkaf-projector-json-schema`, `rkaf-projector-json-ld`, `rkaf-projector-openapi`, `rkaf-runtime`. Substitute `rkaf-validate` for the non-existent `rkaf-constraints-runtime`.
- [ ] `crates/rkaf/src/lib.rs` — facade: `pub mod vocabulary/constraints/projectors/registries;` + `pub fn parse_and_validate()` wrapping `rkaf_validate::Validator`.
- [ ] `crates/rkaf/src/vocabulary.rs` — `pub use rkaf_core::*` (30+ types already exist).
- [ ] `crates/rkaf/src/constraints.rs` — `pub use rkaf_validate::*` (`Validator`, `ValidationError`, `ValidatorError`).
- [ ] `crates/rkaf/src/projectors.rs` — re-export `Projector` trait + 3 concrete projector structs.
- [ ] `crates/rkaf/src/registries.rs` — stub module, compiles but returns "not yet implemented" for registry ops. Real impl gated on Plan 4.
- [ ] `crates/rkaf/tests/conformance.rs` — vocab round-trips + validation + projector ops. Skip registry/federation.
- [ ] `crates/rkaf/README.md` — `cargo add rkaf` + validate + attach-overlay examples.
- [ ] Bump workspace version in `crates/Cargo.toml` to match `VERSION` (`0.2.0-pre.6`).

## Formspec Needs layer — three incoming proposals

Filed 2026-07-27 alongside the Formspec Needs Specification
(`formspec-stack/formspec/specs/needs/needs-spec.md`), whose Appendix C
re-litigated every point where Formspec chose mirror-not-import and recorded a
verdict. Four of the seven came back **KEEP-LOCAL** and are not filed here; the
three below are the ones Formspec cannot do from its side of the boundary.

Each has its own document with the mapping, the acceptance criteria, the
charter cost, and the open questions the maintainer owns.

- [ ] **RS-P1 — Observation intake profile.** New informative companion
  `spec/rkaf-observation-intake.md` defining the mechanical mapping from a
  Formspec Observation Grounding to a conformant assertion, landing at
  `rkaf:usageEligibility: rkaf:searchOnly`. Adds no vocabulary; Layer 4 posture.
  **Done when:** one positive fixture pair (Observation JSON in, assertion
  JSON-LD out) lives in `fixtures/` and is exercised by `tools/vocab_audit.py`.
  → [`thoughts/specs/2026-07-27-formspec-observation-intake-profile.md`](thoughts/specs/2026-07-27-formspec-observation-intake-profile.md)

- [x] **RS-P3 — `rkaf:formspec-need` identifier scheme.** One value added to the
  closed `rkaf:artifactIdentifierScheme` enum (§4.1), denoting a Needs Document
  `url` + `need.id` pair. Release-gated per §3. Buys the reverse edge: an
  assertion citing a product commitment first-class, which is unreachable from
  Formspec's side.
  **Done when:** the enum value is declared, one positive fixture cites a
  product Need as evidence subject, and one negative fixture rejects a mutable
  URL carried without the scheme tag.
  Done 2026-07-28 in `c283d94`: all three criteria met, with one correction
  to the third.
  The enum is now 13 values (Core §4.1 "Formspec Need identity", vocabulary
  closed-enum list). The kernel closes the VALUE SET but NOT a grammar over
  it: `rkaf:hasArtifactIdentifier` and `rkaf:artifactIdentifierScheme` are
  both 1..*, so there is no positional correspondence to hang a per-scheme
  pattern on, and the scalar-pair idiom the six US regulatory schemes use
  (rulemaking §5.2) does not apply. §4.1's immutable-edition rule has never
  been mechanically checked for ANY scheme, so the negative fails on the
  MISSING DECLARATION rather than on detected mutability — the proposal's
  "a mutable URL … is rejected" reads as if mutability were checkable, and it
  is not. Both facts are now stated in §4.1 as producer obligations, the same
  posture as §4.7.3 rule 3. Coverage: 1 positive, 1 negative, 2 parity rows.
  Contract digest MOVED
  `sha256:7d45dcd2…` -> `sha256:8166af8af1e06823e224dd2344b211bc66ff3ed5d5911a22426ddeb6fe334047`.
  BREAKING under §3's reject-unrecognized-values rule.
  → [`thoughts/specs/2026-07-27-formspec-need-identifier-scheme.md`](thoughts/specs/2026-07-27-formspec-need-identifier-scheme.md)

- [x] **RS-P6 — `rkaf:declared-hypothesis` in `noEvidenceReason`.** One value
  added to the closed enum (§4.3): a deliberately held, not-yet-validated
  belief, distinct from `rkaf:axiomatic` and
  `rkaf:consensus-without-citation`. Closes the only hole in the correspondence
  table, and completes RS-P1 — without it a promoted hypothesis has no honest
  landing. Carries one decision for the maintainer: whether the "not
  operationally usable" cap rides `rkaf:hasSafetyLabel` (consistent with §4.3
  as written) or `rkaf:usageEligibility` (as Formspec proposed).
  **Done when:** the enum value, its shape constraint, and positive/negative
  fixtures land per the §10 validation contract.
  Done 2026-07-28 in `56df3df`, with the shape constraint OPEN — see the
  follow-up below.
  Cap decision: **`rkaf:usageEligibility`**. §4.3's safety-label rule GRANTS
  operational validity and does not bound it, so routing the cap through it
  could only work by never permitting the value under any label — binary
  invisibility instead of the graded findable-but-not-actionable state the
  value exists for. The safety-label rule keeps applying uniformly to all five
  members; the two rules compose. The enum had FOUR members before this, not
  the three the proposal's correspondence table assumed. Coverage: 1 positive,
  1 negative, 1 parity row, the `sh:in` closure in
  `shapes/rkaf-shapes-warrant.ttl`, and a `rkaf:NoEvidenceReason` vocabulary
  entry. Contract digest MOVED
  `sha256:8166af8a…` -> `sha256:6e5506001343c55af2530c89070c79c4f74f54f666ef823c2687bd1460d173ce`.
  BREAKING under §3's reject-unrecognized-values rule.
  → [`thoughts/specs/2026-07-27-declared-hypothesis-no-evidence-reason.md`](thoughts/specs/2026-07-27-declared-hypothesis-no-evidence-reason.md)

- [ ] **RS-P6 follow-up — mechanize the declared-hypothesis eligibility cap.**
  §4.3 requires an assertion whose binding carries `rkaf:declared-hypothesis`
  to stay at `rkaf:searchOnly` or `rkaf:reviewQueueOnly`, and nothing enforces
  it. `rkaf:usageEligibility` is a property of the assertion envelope (§2.3),
  `rkaf:noEvidenceReason` a property of the binding, and `rkaf:bindsAssertion`
  a bare IRI — the conditional idiom needs both on ONE shape, and the compiler
  flattens nested objects instead of traversing them
  (`compiled/shacl/adversarial/nested-noevidencereason.ttl` targets the wrong
  class for exactly this reason). Three candidate routes, none costed:
  teach the compiler a cross-reference conditional; teach it to emit SHACL
  sequence paths (no shape in this repo uses one today, and a SHACL-only
  constraint would break target parity); or accept it permanently as a
  producer obligation alongside §4.7.3 rule 3. **Do NOT** solve it by putting
  `rkaf:usageEligibility` on the EvidenceBinding — that creates two places to
  look for the same consumer-scoped fact, which §2.3 forbids.
  **Done when:** the cap is enforced on every compiled target, or the spec
  records the producer-obligation posture as final.

- [ ] **Decide the `rkaf:permits-*` safety-label family.** Surfaced while
  landing RS-P6. §4.3 says the Assertion's `rkaf:hasSafetyLabel` MUST permit
  the chosen `noEvidenceReason`, but no per-reason permission table exists.
  `#SafetyLabel` holds seven lettered values plus one orphan,
  `rkaf:permits-axiomatic`; `constraints/adversarial/conditional-silent-pass.cue`
  and `nested-noevidencereason.cue` require
  `rkaf:permits-consensus-without-citation` and `rkaf:permits-all`, neither of
  which is an enum member; and `fixtures/evidencebinding-no-evidence-reason-positive.jsonld`
  pairs a LETTERED label (`rkaf:A3AdvisoryAggregated`) with `rkaf:axiomatic`
  and passes. So the rule is producer-obligation-only, and the `permits-*`
  family is a vestige that is neither complete nor consistent with the
  lettered scheme. RS-P6 deliberately did NOT mint a
  `rkaf:permits-declared-hypothesis`: that would extend a v0.1-INHERITED
  closed enum (§3 currently records `rkaf:assertionOrigin` as the one
  inherited enum v0.2 extends) and would add a fourth partial member to an
  already-incoherent family.
  **Done when:** either the `permits-*` values are completed and declared as a
  real table, or they are retired and §4.3's rule is restated against the
  lettered labels.

**Sequencing:** RS-P6 before RS-P1 — the mapping is incomplete without the
enum value, and landing the companion first would document a promotion path
with a known hole in it. RS-P3 is independent of both. All three are enum or
companion additions, so they belong in whatever release the open
"decide the release shape" item above settles on, not in tags of their own.

## Rulespec Core wheel — source and document release schemas

Filed 2026-08-11 from §4 of
`spicysearch/docs/history/2026-08-11-cross-product-reconciliation-recommendations.md`;
the boundary authority is REF-024 and the search-view format authority is
REF-025, both in the RefSpec decisions ledger.
The extrapolator plan at `spicy-regs/docs/rulespec-testbed-path-forward.md` is a
different scope; this work does not merge into it.

Measured 2026-08-11 at `b64ca675e9f0`: `grep -rl SourceCatalogRelease` returns
nothing. `DocumentRelease` occurs as a consumed publisher-owned artifact
name — prose in `spec/rulespec-releases.md:110,170,218`, readers in the
unpackaged `tools/extrapolation_release_v2.py` and `tools/rulespec_release.py`,
two fixture builders, and a vendored publisher schema under `release-records/`
— with no schema, shape, or CUE
constraint under `constraints/`, `compiled/`, or `shapes/`. So both roots are
authored here first and packaged second. The wheel today carries 40 compiled
rkaf kernel schemas under `_data/compiled/json-schema/core/`, force-included by
`pyproject.toml:40-48`.

- [x] **Author the `SourceCatalogRelease` schema set.**
  Done 2026-08-11 as an immutable candidate at bundle digest
  `urn:rulespec:core:d1a7dd831e2ab598c43c67331ed79820acba69f1f8b7e5da25716b70128d7fc6`.
  `spec/rulespec-source-catalog-release.md` is the normative statement.
  Three closed Draft 2020-12 schemas: `source-catalog-release-v1.schema.json`
  (release root — selection policy, `requestedUniverseSetDigest`,
  `selectedSourceSetDigest`, counts, coverage, global manifest reference,
  self-describing schema set), `source-catalog-release-v1/member-manifest-v1.schema.json`
  (the one member manifest and its member descriptors), and
  `source-catalog-release-v1/source-items-v1.schema.json` (source item,
  selection disposition, candidate rendition, normalized MVP metadata,
  source-observed topic, source observation).
  `format` is `spicyregs-source-catalog-release` `1.0` and identity is
  `urn:spicyregs:source-catalog-release:v1:<sha256 over canonical {format,
  formatVersion, content}>`, matching the existing `urn:spicyregs:document-release:v3:`
  convention — Rulespec Core owns the schemas, SpicyRegs owns the records
  (REF-024).

  **PIPELINE DEVIATION, stated because this item's original "Done when" named
  a different one.** The text above said "declared in `constraints/`, compile
  to every target the kernel schemas compile to, and land under
  `_data/compiled/`". That is the rkaf VOCABULARY pipeline: CUE node shapes
  with `@type` and `rkaf:`-prefixed predicates, compiled by
  `tools/constraints_compile.py` to JSON Schema, TypeScript, SHACL, Rego, and
  Rust, with SHACL violations as its diagnostics. A `SourceCatalogRelease` is
  not an RDF node — it is a file bundle with member manifests, object keys,
  byte digests, named diagnostic codes, and a first-failure order, and none of
  those five has a carrier in that pipeline. The repository already has a
  second, equally house pipeline for exactly this shape:
  `spec/rulespec-releases.md` prose + closed JSON Schema under
  `release-records/schemas/` + a portable Python verifier with a code
  precedence list + sealed valid/invalid fixtures with a `corpus.json`, which
  is how `ExtrapolationRelease` v2 is built (`tools/extrapolation_release_v2.py`,
  `release-records/fixtures/extrapolation-release-v2/`). This candidate follows
  that one. No new pipeline was created and `tools/constraints_compile.py` was
  not touched.

- [ ] **Author the `DocumentRelease` schema set.** The name is currently a
  reader-side string; this makes it a Rulespec-owned root.
  NOT IN SCOPE for the 2026-08-11 `SourceCatalogRelease` candidate and not
  begun. `grep -rn DocumentRelease` still returns prose in
  `spec/rulespec-releases.md`, readers in the unpackaged
  `tools/extrapolation_release_v2.py` and `tools/rulespec_release.py`, two
  fixture builders, and a vendored publisher schema under `release-records/`.
  **Done when:** a `DocumentRelease` root and its members are declared under
  `release-records/schemas/` alongside `SourceCatalogRelease` (the pipeline
  deviation above applies equally), carry a verifier, diagnostics, and sealed
  valid and invalid fixtures, and ride in the wheel under their own bundle
  digest.

- [x] **Ship generated types, stable identity and digest helpers, validators,
  diagnostics, and conformance fixtures** — for `SourceCatalogRelease` only.
  Done 2026-08-11. In the wheel and reachable with no checkout on the path:
  the three schema files; `rulespec_conformance.source_catalog_release` with
  `expected_release_id`, `stamp_root`, `source_set_digest`, `canonical_sha256`,
  `tree_digest`, `derive_counts`, `derive_coverage`, `file_sha256`,
  `verify_source_catalog_release`, `verify_corpus`, `candidate_bundle_errors`,
  `bundle_release_id`; the 15 diagnostic codes in `DIAGNOSTIC_CODES` with their
  total order in `CODE_PRECEDENCE`; and 17 sealed fixture bundles.
  `VerificationResult.first` returns the single issue that decides the verdict,
  so both the reported code and the reported path are functions of the bundle
  bytes.
  Fixtures: one valid bundle carrying all five dispositions over a
  six-item universe with two selected, and 16 invalid bundles — each the valid
  bundle copied and mutated in exactly one way with every downstream digest,
  count, and identity restamped. Every diagnostic code has one:
  `noncanonical-root`, `unknown-version`, `wrong-identity`, `unsafe-path`,
  `missing-member`, `extra-member`, `member-digest`, `missing-disposition`,
  `unknown-disposition`, `missing-reason`, `duplicate-source-item`,
  `set-digest-mismatch`, `selected-without-rendition`, `refspec-concept-topic`,
  `counts-mismatch`, `coverage-mismatch`. `corpus.json` seals each by tree
  digest and pins the expected code AND path;
  `test_every_declared_diagnostic_code_has_a_sealed_fixture` fails when a code
  has no fixture.
  NOT SHIPPED: generated types. The rkaf pipeline's TypeScript and Rust
  emitters read CUE, and these schemas are not CUE, so a consumer gets the
  schema bytes and the Python verifier, not a generated struct. Adding a
  JSON-Schema-to-TypeScript/Rust emitter is a separate change and is not
  started.

- [x] **Deliver the schemas as one digest-addressed bundle inside the wheel.**
  Done 2026-08-11. `release-records/source-catalog-release-v1-candidate.json`
  is a `RulespecCoreRelease` (`spec/rulespec-releases.md` §2) pinning the three
  schema files, both validator modules, and all 17 sealed fixture bundles by
  digest; a fixture bundle is pinned by its tree digest under
  `application/vnd.spicy.bundle-tree+json`. Reusing that record type means the
  bundle digest is minted and checked by machinery this repository already has,
  and `tools/rulespec_release.py validate` accepts the manifest unchanged.
  There is no second schema-publication pipeline beside the wheel.
  `candidate_bundle_errors()` re-derives every pinned digest and the manifest's
  own `release_digest`/`release_id` from the installed package.

- [x] **Exercise the installed wheel outside the source checkout.**
  Done 2026-08-11. `rulespec-source-catalog-validate` is a second console
  script; `make test-package` runs it after `rulespec-ci-validate` from
  `$TMPDIR/rulespec-package-check`. It asserts 26 required exports by name,
  five required data files, the bundle digest, and all 17 sealed verdicts.
  `REQUIRED_EXPORTS` is a literal list, not `__all__`, so deleting a symbol and
  its `__all__` entry together still fails.
  Falsified three ways against the built wheel: renaming `verify_corpus` in the
  installed module exits 2 naming the symbol; deleting
  `_data/release-records/schemas/source-catalog-release-v1/source-items-v1.schema.json`
  exits 1; deleting one sealed fixture bundle exits 1 with both the bundle-digest
  failure and the case failure. None becomes a skip.
  It is a separate console script rather than a step inside `ci_validate.py`
  because the sealed M2 `RulespecCoreRelease` pins that file's exact bytes in
  `validator_artifacts`, and its content-derived `release_id`
  (`urn:rulespec:core:777d05c3…`) is pinned in turn by the vendored document
  release, the atlas-membership stub, `m2-input-releases.json`,
  `m2-extrapolation-release-positive.json`, and every
  `extrapolation-release-v2` bundle. Adding a step there moved that digest and
  failed `test_core_manifest_digests_match_repository_artifacts`; the M2 seal is
  unchanged by this work instead.

**Preserve:** `make test-package` (`Makefile:64-70`); the CI step that calls it
(`.github/workflows/constraints-parity.yml:87`); the version-synchronization
gate (`tools/version_sync.py --check`, `Makefile:96` and the workflow step); and
the compatibility-shim docstring at `tools/conformance_lib.py:1-11` explaining
why the shim rebinds `sys.modules` instead of re-exporting names — a
`from X import *` copy would leave a monkeypatched name unpatched in the
implementation module.

Done 2026-08-11: `_resources.py` deleted, `data_root()` inlined into
`src/rulespec_conformance/conformance_lib.py` as `ROOT`. Its one caller was in
the same directory, so the `parents[2]` depth is unchanged.

All four preserved items are intact after the `SourceCatalogRelease` candidate:
`make test-package` still exists and now runs both console scripts, the CI step
still calls that target rather than restating it, `tools/version_sync.py
--check` reports all call sites in sync at `0.2.0-pre.9`, and
`tools/conformance_lib.py`'s shim docstring is unedited — the two new `tools/`
shims copy its `sys.modules` rebinding and cite it rather than restating why.

### What the candidate does not settle

- Generated TypeScript and Rust types for these roots. See the note above.
- Partitioned members. v1 has one global member manifest and one data member;
  sharding a large `U` across partitions is not modeled. `ExtrapolationRelease`
  v2's partition/serving-shard descriptors were deliberately not copied.
- Parquet members. Members are canonical JSON, which keeps `pyarrow` and
  `rfc8785` out of the distribution's dependencies. The member protocol
  (`objectKey`, `role`, `mediaType`, `byteSize`, `sha256`, `recordCount`,
  `schemaId`) is unchanged from v2, so a later Parquet role is additive.
- Cross-product verdict agreement. SpicyRegs, DocSpec, and SpicySearch have not
  run this corpus; that closes at the receiving plan's step 7, not here.
- The candidate is not a release. `release_status` is `candidate`, and cutting
  a release means reusing these exact bytes or minting a new digest.
