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

Current reference run: 193 fixtures, 0 divergences. L4 is populated by
`rkaf-behavior-validate` over `fixtures/behavior/`.

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
