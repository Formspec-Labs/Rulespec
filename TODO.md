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
