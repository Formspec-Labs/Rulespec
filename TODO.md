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
- [ ] Consolidate unreleased CHANGELOG entries (Plans 7a–7e, ADR-0093) into a versioned `v0.2.0-pre.7` release. Bump `VERSION`.

## US regulatory vocabulary and rulemaking follow-through

- [ ] Land and tag the `v0.2.0-pre.7` consolidation before assigning the US identifier and L0 work to a release, as required by the design memo's sequencing.
- [ ] File `conformance/partners/spicy-regs.yaml` only after spicy-regs ships both `rule_targets` and `docs/ontology.md`, then run `tools/l0_mapping_audit.py` against that real mapping.
- [ ] Keep `spec/rkaf-rulemaking.md` Experimental until a full-corpus spicy-regs `proceedings` / `comment_periods` run publishes a friction report and a non-originating consumer completes review.

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
