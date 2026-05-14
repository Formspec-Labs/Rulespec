# Rulespec Tooling

The conformance tools discover their fixture, shape, and schema inputs from
the repository. They do not carry fixture allow-lists, fixed triple-count
ranges, or manually maintained schema maps.

## Shape Gate

`ci_validate.py` validates every positive fixture against the full SHACL suite:
hand-authored shapes in `shapes/` plus compiled shapes in
`compiled/shacl/core/`.

```bash
python3 tools/ci_validate.py
python3 tools/ci_validate.py --json
```

Current reference run: 41 positive fixtures, 39 shape files, 0 violations.

## Negative Gate

`validate_negatives.py` discovers every negative fixture and asserts each one
fails SHACL validation as intended.

```bash
python3 tools/validate_negatives.py
```

Current reference run: 104 negative fixtures, all `FAIL-AS-EXPECTED`.

## Conformance Report

`conformance_report.py` walks the full conformance corpus under `fixtures/`,
excluding cross-gate adversarial/projector envelopes, and reports L1/L2/L3/L4
verdicts per fixture.

```bash
cargo build --manifest-path crates/Cargo.toml --workspace
python3 tools/conformance_report.py
python3 tools/conformance_report.py --self-certify
```

Current reference run: 216 fixtures, 0 divergences. L4 is populated by
`rkaf-behavior-validate` over `fixtures/behavior/`; a missing L4 binary is a
divergence, not a green skip.

## L0-L3 Coverage Audit

`l0_l3_coverage_audit.py` checks that lower-layer fixture coverage is complete,
not just that the existing fixtures produce expected verdicts. It asserts L0
vocabulary/source coverage, L1 JSON-LD parse coverage, L2 positive and negative
type coverage, required-field negative coverage, and L3 edge coverage across
every compiled schema class.

```bash
python3 tools/l0_l3_coverage_audit.py
```

Current reference run: 216 normal fixtures, 31/31 schema classes covered by
positive, negative, and edge fixtures, and 93/93 required-field negative slots
covered.

## L4 Coverage Audit

`l4_coverage_audit.py` checks that the behavior fixture corpus covers every
normative L4 branch, not just that the existing fixtures pass.

```bash
python3 tools/l4_coverage_audit.py
```

Current reference run: 38 behavior fixtures covering 5/5 contracts, 10/10
bridge rules, 6/6 reducer branches, 2/2 PIT branches, all concept outcomes and
severity levels, and 17/17 cascade predicates.

## Vocabulary Audit

`vocab_audit.py` keeps `spec/rkaf-vocabulary.md`, `constraints/core/`,
compiled JSON Schema terms, and named fixture rows aligned.

```bash
python3 tools/vocab_audit.py
```

## Requirements

```bash
pip install -r requirements.txt
```

The SHACL gates require `pyshacl >= 0.31.0` and `rdflib >= 7.0.0`.
