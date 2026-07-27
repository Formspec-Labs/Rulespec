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

The plan specified `rkaf-conformance` Rust binary + `suite.index.json` + `conformance/v0.2/levels/` docs. None of that was built. The current architecture (Python reporter + `rkaf-runtime-cli` + directory-walking) delivers L1–L4 gating with 238 fixtures, 0 divergences. Ratify it.

- [ ] Author `docs/conformance/partner-disclosure-howto.md` — step-by-step instructions for partners to produce a conformance disclosure YAML.
- [ ] Fold any missing L1–L4 level detail into `spec/rkaf-conformance.md` (already has level descriptions at lines 106–118). Do not create separate `conformance/v0.2/levels/` files.
- [ ] Rewrite the Layer 6 plan (`thoughts/plans/2026-05-12-rkaf-layer6-conformance-v0.2.md`) self-review checklist to match what actually shipped.
- [x] Consolidate unreleased CHANGELOG entries (Plans 7a–7e, ADR-0093) into a versioned `v0.2.0-pre.7` release. Bump `VERSION`.

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

- [ ] **RS-P3 — `rkaf:formspec-need` identifier scheme.** One value added to the
  closed `rkaf:artifactIdentifierScheme` enum (§4.1), denoting a Needs Document
  `url` + `need.id` pair. Release-gated per §3. Buys the reverse edge: an
  assertion citing a product commitment first-class, which is unreachable from
  Formspec's side.
  **Done when:** the enum value is declared, one positive fixture cites a
  product Need as evidence subject, and one negative fixture rejects a mutable
  URL carried without the scheme tag.
  → [`thoughts/specs/2026-07-27-formspec-need-identifier-scheme.md`](thoughts/specs/2026-07-27-formspec-need-identifier-scheme.md)

- [ ] **RS-P6 — `rkaf:declared-hypothesis` in `noEvidenceReason`.** One value
  added to the closed enum (§4.3): a deliberately held, not-yet-validated
  belief, distinct from `rkaf:axiomatic` and
  `rkaf:consensus-without-citation`. Closes the only hole in the correspondence
  table, and completes RS-P1 — without it a promoted hypothesis has no honest
  landing. Carries one decision for the maintainer: whether the "not
  operationally usable" cap rides `rkaf:hasSafetyLabel` (consistent with §4.3
  as written) or `rkaf:usageEligibility` (as Formspec proposed).
  **Done when:** the enum value, its shape constraint, and positive/negative
  fixtures land per the §10 validation contract.
  → [`thoughts/specs/2026-07-27-declared-hypothesis-no-evidence-reason.md`](thoughts/specs/2026-07-27-declared-hypothesis-no-evidence-reason.md)

**Sequencing:** RS-P6 before RS-P1 — the mapping is incomplete without the
enum value, and landing the companion first would document a promotion path
with a known hole in it. RS-P3 is independent of both. All three are enum or
companion additions, so they belong in whatever release the open
"decide the release shape" item above settles on, not in tags of their own.
