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

## JSON-LD context

Fixtures reference the canonical context at `../context/rkaf-context.jsonld`
via the `@context` field. There is no separate fixture-prep copy under
`fixtures/` — the canonical file is the single source.

## Cross-fixture `@id` references

A fixture's `@graph` is **not** required to be self-contained. Properties
typed `@id` (e.g. `rkaf:detectedBy`, `rkaf:subject`, `rkaf:targets`) may
reference IRIs defined in sibling fixtures. JSON-LD treats unresolved `@id`s
as opaque IRIs; SHACL shapes validate the *structure* of references, not
their resolvability. Where a fixture exercises an isolated node (e.g. a
`Finding` not paired with the originating `BridgeValidationResult`), add a
top-level `_comment` key noting the intent.

Inline the referenced node when the fixture's primary purpose is to
exercise the relationship itself (e.g., an Attestation→Finding waiver
pair, a BridgeValidationResult→Finding emission pair); use a
cross-fixture `@id` reference when the fixture isolates a single class
for shape validation and the relationship is incidental.

## Adding Fixtures

New fixtures should:

1. Carry the v0.2 context.
2. Use `*-positive`, `*-negative`, `*-edge`, or `behavior/` placement to declare the intended gate.
3. Pass the relevant gate before commit.
4. Update `spec/rkaf-vocabulary.md` when adding a new codified class or required fixture row.
5. Add a narrative only when the fixture represents a larger scenario rather than a minimal conformance atom.
