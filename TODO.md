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

The plan specified `rkaf-conformance` Rust binary + `suite.index.json` + `conformance/v0.2/levels/` docs. None of that was built. The current architecture (Python reporter + `rkaf-runtime-cli` + directory-walking) delivers L1–L4 gating with 268 fixtures, 0 core divergences. Ratify it.

- [ ] Author `docs/conformance/partner-disclosure-howto.md` — step-by-step instructions for partners to produce a conformance disclosure YAML.
- [ ] Fold any missing L1–L4 level detail into `spec/rkaf-conformance.md` (already has level descriptions at lines 106–118). Do not create separate `conformance/v0.2/levels/` files.
- [ ] Rewrite the Layer 6 plan (`thoughts/plans/2026-05-12-rkaf-layer6-conformance-v0.2.md`) self-review checklist to match what actually shipped.
- [x] Consolidate unreleased CHANGELOG entries (Plans 7a–7e, ADR-0093) into a versioned `v0.2.0-pre.7` release. Bump `VERSION`.

## US regulatory vocabulary and rulemaking follow-through

- [ ] Land and tag the `v0.2.0-pre.7` consolidation before assigning the US identifier and L0 work to a release, as required by the design memo's sequencing.
- [ ] Decide the release shape before tagging: the memo prescribed two releases (N+1: identifiers + L0; N+2: rulemaking module + corpus), but all four deliverables sit together in Unreleased. Either cut them as two tags or record in the memo why one combined release preserves the sequencing intent (2026-07-23 architecture review, FINDING 2).
- [ ] Regenerate `conformance/partners/rulespec-reference.yaml` via `tools/conformance_report.py --self-certify` at the release cut — it is pinned to `0.2.0-pre.6` with a 2026-05-17 corpus run and predates the US-identifier fixtures (2026-07-23 architecture review, FINDING 6).
- [ ] File `conformance/partners/spicy-regs.yaml` only after spicy-regs ships both `rule_targets` and `docs/ontology.md`, then run `tools/l0_mapping_audit.py` against that real mapping.
- [x] Record the 2026-07-24 maintainer-operated adversarial simulated-consumer review and its three agenda decisions. The simulation is evidence, not a non-originating review.
- [ ] Keep `spec/rkaf-rulemaking.md` Experimental until the repair batch below lands and a non-originating consumer reviews the repaired contract or ratifies the simulated review against it.

### Rulemaking stabilization repair batch

Source:
`thoughts/reviews/2026-07-24-rulemaking-condition2-adversarial-review.md`.
Its verdict is **do not graduate as-is**.
F-5, F-11, F-12, and F-14 were refuted and require no implementation work.

- [ ] Enforce declared graph invariants (F-21, F-24, agenda item 1): teach the projector reference-class constraints; emit `sh:maxCount` for every 1 and 0..1 property; constrain stage subjects and proceeding-event targets; preserve the Docket/Proceeding boundary; add the reproduced attack graphs as negative fixtures.
- [ ] Make rule targets producible and unambiguous (F-8, F-15, F-16): add a citation-level target or a documented unresolved-edition path; support letter-suffixed CFR sections; define pre-amendment target direction and optional produced-edition semantics; update the reference corpus.
- [ ] Preserve complete comment-period evidence (F-9, F-17, F-20): support Proceeding or Docket anchors with an at-least-one constraint; name the opening Artifact separately from provenance; define inclusive dates in the governing timezone; add joint, docket-only, reopening, and datetime-conversion fixtures.
- [ ] Represent terminal and external legal events (F-1, F-2, F-3, F-4): define honest terminal-state semantics; add judicial and congressional event kinds; state that proceeding stage does not assert legal operativeness; support partial-vacatur target scope.
- [ ] Preserve identity evidence and continuity (F-6, F-7): add a repeatable non-identity Proceeding evidence-identifier pair with `us-rin`; add a directional merge, split, or supersession relation that does not misuse cascade-seeding `appliesTo`.
- [ ] Implement all three agenda decisions: keep and harden per-posting cross-posting, promote `dcterms:hasFormat`/`isFormatOf` as a mode-1 import (F-19), make Proceeding `hasAuthority` optional with a no-placeholder rule, and replace all six bare stage IRIs.
- [ ] Close grammar and tooling gaps (F-22, F-23, F-18, F-10): widen `us-regsgov` or document its fallback; state and test JSON Schema's date/order limits; add `hasArtifactIdentifier` to the L0 identifier tables and fixtures; implement an official-registry scheme or explicitly defer it with FCC/FERC/SEC named.
- [x] Amend §8 to disclose that the simulated review did not satisfy the non-originating-consumer gate and to keep that gate open.
- [ ] Record F-13 as a non-blocking vocabulary trigger: add `commentPeriodKind` only when an in-scope corpus or consumer supplies the distinction.
- [ ] Regenerate every affected projection and SDK type, run `make compile` and `make test`, publish a review-to-change matrix, and rerun the adversarial fixtures.
- [ ] Coordinate the paired spicy-regs migration: remove agency-stub authority placeholders; update stage enum maps; retain docket-anchored periods; publish RIN evidence and continuity; project citation-level targets; update the L0 map, contract digest, corpus report, and partner certificate.
- [ ] Require the paired gate receipt to bind the Rulespec commit and contract digest, spicy-regs commit, candidate corpus snapshot id, every artifact hash, and every gate result. Do not accept unbound command output as corpus evidence.

**Done when:** Every §5 graduation precondition has a normative decision,
generated enforcement, positive and negative coverage, and corpus evidence;
both repositories pass their full gates against the same released contract; and
a non-originating consumer reviews or ratifies the repaired module.

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
