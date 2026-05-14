# Rulespec Conformance — L1–L4 levels

Status: Editor's Draft, normative.
Companion to: `spec/rkaf-core.md`, `spec/rkaf-vocabulary.md`, `spec/rkaf-behavior.md`.

## 0. Purpose

This document specifies what "Rulespec-conformant" means at increasing depths of integration. Conformance is **consumer-declared and self-certified** — there is no central certification authority pre-1.0. An implementation declares the highest level it satisfies; the conformance test suite under `fixtures/` is the falsifiability gate.

Four levels are defined:

| Level | What an L`n`-conformant implementation guarantees |
|---|---|
| **L1 — Parse** | Documents claiming to be Rulespec parseable as JSON-LD without error. |
| **L2 — Shape** | Every Rulespec node validates against its compiled JSON Schema. |
| **L3 — Constraint** | Every Rulespec node also passes SHACL constraints, including Pattern-C cross-property invariants. |
| **L4 — Behavior** | Implementation honors the runtime contracts in `spec/rkaf-behavior.md` (reducer, CascadeClosureV1, 10 bridge rules, point-in-time exceptions, stale transition). |

L1 ⊂ L2 ⊂ L3 ⊂ L4 — each level subsumes the prior. An L3-conformant implementation MUST also be L2- and L1-conformant.

## 1. L1 — Parse [Normative]

### 1.1 Requirement

An L1 implementation MUST:

1. Accept any document carrying `@type` values prefixed with `rkaf:` and parse them as JSON-LD 1.1 nodes.
2. Recognize the canonical Rulespec JSON-LD context URL (`https://rulespec.org/context/rkaf-context.jsonld`) and resolve term-to-IRI mappings against it.
3. Round-trip a Rulespec document through JSON-LD expand → compact without loss of `rkaf:*` typed properties.
4. NOT panic, crash, or silently drop nodes on unrecognized `rkaf:*` properties — forward-compatibility requires extension property tolerance.

### 1.2 Gate

`tools/conformance_report.py --level L1 --fixture <path>` exits 0 if the document parses as JSON-LD without error.

### 1.3 Self-certification

Declaring L1 requires that **every fixture under `fixtures/` parses without error** through the implementation's JSON-LD loader.

## 2. L2 — Shape [Normative]

### 2.1 Requirement

An L2 implementation MUST:

1. Satisfy L1.
2. Validate every Rulespec node against the JSON Schema for its `@type` IRI. The canonical schema set is `compiled/json-schema/core/`; the canonical Rust validator is the `rkaf-validate` crate.
3. Refuse to interpret an `@type` outside the v0.2 vocabulary as Rulespec-typed (pass-through is OK; mis-validation is not).
4. Surface validation errors with at least the offending JSON pointer and the violated constraint (`required`, `enum`, `type`, `pattern`).

### 2.2 Gate

`rkaf-validate <file>` exits 0 on L2-conformant input, 1 on any L2 violation. `tools/conformance_report.py --level L2 --fixture <path>` is the Python-side equivalent.

### 2.3 Self-certification

Declaring L2 requires that **every positive fixture validates cleanly** and every embedded JSON Schema type has positive-fixture coverage. Negative fixtures MUST surface at least one L2 or L3 violation across the reference gates.

## 3. L3 — Constraint [Normative]

### 3.1 Requirement

An L3 implementation MUST:

1. Satisfy L2.
2. Validate every Rulespec node against the SHACL shapes under `shapes/` (hand-authored, Pattern-C-bearing) AND `compiled/shacl/core/` (CUE-generated, enum + cardinality).
3. Enforce Pattern-C cross-property invariants — e.g., an Assertion with `assertionOrigin` in the AI-touched subset MUST carry `hasAILineage`.
4. Surface SHACL violations with focus node, result path, source constraint component, and result message.

### 3.2 Gate

`tools/ci_validate.py` is the Python SHACL gate. An L3-conformant implementation produces an equivalent verdict on every fixture.

### 3.3 Self-certification

Declaring L3 requires that **every positive fixture passes the full SHACL shape suite** and **every negative fixture surfaces at least one L2 or L3 violation** through the reference gates.

## 4. L4 — Behavior [Normative]

### 4.1 Requirement

An L4 implementation MUST:

1. Satisfy L3.
2. Implement the `usageEligibility` reducer per `spec/rkaf-behavior.md` §1, honoring narrow-only / LocalAdoption-broadens-within-scope invariants.
3. Implement `CascadeClosureV1` per `spec/rkaf-behavior.md` §2 — the algorithm name in `LifecycleEvent.cascadeAlgorithm` is the conformance identifier.
4. Honor all 10 bridge contract rules per `spec/rkaf-behavior.md` §3.
5. Honor point-in-time exceptions per §4 — refuse unsupported `evaluationAnchor` values.
6. Implement stale transition per §5.
7. Emit a `rkaf:BridgeValidationResult` for every packet ingest, with conformant `result` / `effectiveUsageEligibility` / `authorityChainStatus`.

### 4.2 Gate

L4 conformance is gated by `crates/rkaf-runtime-cli/src/main.rs` (the `rkaf-behavior-validate` binary). `tools/conformance_report.py` shells out to this binary for every fixture under `fixtures/behavior/`, parses the per-fixture JSON verdict, and populates the L4 column with `pass` / `fail` / `error` / `skip`. Exit 0 from the binary across all behavior fixtures (33 today: 2 cascade — base + as_of; 5 reducer — applicability gate, capability cap, local broadens, stale narrows, stale-with-honored-PIT; 2 PIT — base + unsupported anchor; 4 concept-resolution — base conflict + 3-step severity ladder (informational, publicationBlocking, authorityCritical); 20 bridge-rule — positive + negative per all 10 contract rules) is the L4 gate.

When the binary is missing (e.g., the workspace has not been built), the reporter degrades to `L4: skip` with a clear note pointing at `cargo build --manifest-path crates/Cargo.toml --workspace`.

### 4.3 Self-certification

Declaring L4 requires the implementation to file a `conformance/partners/<implementation>.yaml` document enumerating which behavior-spec sections are implemented and the implementation's plan for the ones not yet enforced.

## 5. Test corpus [Normative]

The conformance test corpus lives under `fixtures/`. The §10.1 coverage target per source spec:

| Coverage | Target | Current |
|---|---|---|
| Per-class positive fixtures | every embedded compiled schema type | 41 positive fixtures; `rkaf-validate` asserts coverage for all 31 embedded `@type` schemas |
| Per-class negative fixtures | every codified class with required fields | 104 negative fixtures; `tools/validate_negatives.py` discovers and gates all of them |
| Per-class edge fixtures | every codified class | 15 representative edge fixtures |
| Behavior fixtures | every L4 contract family | 33 behavior fixtures |
| Adversarial fixtures | ≥5 | 6 (in `fixtures/adversarial/`) |
| AI-extraction adversarial fixtures | ≥3 | 3 (in `fixtures/ai-extraction/`) |
| Projector round-trip fixtures | every projector × Attach/Extract | 5 (in `fixtures/projectors/`) |
| Cross-target parity fixtures | every CORE Vocabulary class × {JSON Schema, SHACL} | covered via `tools/constraints_parity.py` |

A class's negative + edge fixtures are housed in `fixtures/negatives/<class>-*.jsonld` and `fixtures/edges/<class>-*.jsonld` respectively to keep the positive set discoverable.

## 6. Self-certification document [Normative]

Implementations declaring a conformance level publish a YAML at `conformance/partners/<implementation>.yaml`. The template at `conformance/self-certification.template.yaml` enumerates the required fields. The minimum fields:

```yaml
partner: "<organization or maintainer name>"
implementation: "<package@version>"
rulespec_version: "<commit hash or pre-release tag>"
declared_levels: [L1, L2, L3, L4]   # or subset
test_corpus_run_at: "<date>"
test_corpus_commit: "<rulespec commit>"
results:
  L1: pass
  L2: pass
  L3: pass
  L4: pass
notes: |
  Free-form. Document what the implementation does and does not enforce.
```

The conformance reporter (`tools/conformance_report.py --self-certify > conformance/partners/<implementation>.yaml`) produces this document from a test run.

## 7. Why consumer-declared and not authority-certified [Informative]

Pre-1.0 Rulespec is a public substrate, not a credentialed-membership organization. The federation thesis (`spec/rkaf-core.md` §1.3) is structural: partners agree on the substrate, not on a body that certifies their conformance. Self-certification with falsifiability through the conformance suite is the appropriate posture for a federation substrate at this stage.

Post-1.0, a governance shell (per `spec/rkaf-core.md` §13.3) MAY introduce third-party conformance audits, but the suite itself remains the falsifiability gate.

## 8. Adoption depth gradient interaction [Informative]

Conformance level (L1–L4) is distinct from adoption depth (D0–D5 per source spec Appendix D). An implementation may be:

- **L2 at D1** — a partner accepting Rulespec overlays in JSON Schema documents (low integration, basic validation).
- **L3 at D3** — a reference consumer (like Studio) whose schemas are CUE-derived from a Rulespec profile, with full SHACL gate enforcement.
- **L4 at D5** — a substrate-level implementation owning the runtime contracts (workflow engine, governance platform).

The matrix is multiplicative: an implementation declares a (level, depth) tuple. Most consumers operate at (L2, D1) or (L3, D2); reference consumers operate at (L3, D3); substrate hosts operate at (L4, D4) or (L4, D5).
