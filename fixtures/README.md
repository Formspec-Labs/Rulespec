# Rulespec Conformance Fixtures

This directory is the reference conformance corpus for Rulespec v0.2.

The corpus is intentionally split by gate:

- Top-level `*-positive.jsonld` fixtures validate cleanly through JSON Schema and SHACL.
- Top-level and `negatives/` `*-negative.jsonld` fixtures must fail at least one shape gate.
- `edges/` fixtures document boundary cases; they are reported but not required to pass or fail.
- `behavior/` fixtures are L4 runtime contracts consumed by `rkaf-behavior-validate`.
- `adversarial/`, `ai-extraction/`, and `projectors/` are cross-gate corpora consumed by their own tools, not by the main conformance reporter.

Current reference counts:

| Corpus | Count | Gate |
|---|---:|---|
| Positive fixtures | 41 | `tools/ci_validate.py`, `rkaf-validate` |
| Negative fixtures | 104 | `tools/validate_negatives.py`, `tools/conformance_report.py` |
| Edge fixtures | 15 | `tools/conformance_report.py` visibility only |
| Behavior fixtures | 33 | `rkaf-behavior-validate`, `tools/conformance_report.py` L4 |
| Total L1-L4 corpus | 193 | `tools/conformance_report.py` |

## Validating

From the repo root:

```bash
python3 tools/ci_validate.py
python3 tools/validate_negatives.py
cargo build --manifest-path crates/Cargo.toml --workspace
python3 tools/conformance_report.py
python3 tools/vocab_audit.py
```

## context.jsonld

The file `context.jsonld` is the fixture-prep source for the inline `@context`
that each fixture carries. It mirrors `context/rkaf-context.jsonld`; see
`context/README.md` for rationale.

## Adding Fixtures

New fixtures should:

1. Carry the v0.2 context.
2. Use `*-positive`, `*-negative`, `*-edge`, or `behavior/` placement to declare the intended gate.
3. Pass the relevant gate before commit.
4. Update `spec/rkaf-vocabulary.md` when adding a new codified class or required fixture row.
5. Add a narrative only when the fixture represents a larger scenario rather than a minimal conformance atom.
