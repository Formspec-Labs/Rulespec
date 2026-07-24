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
| Positive fixtures | 74 | `tools/ci_validate.py`, `rkaf-validate` |
| Negative fixtures | 143 | `tools/validate_negatives.py`, `tools/conformance_report.py` |
| Edge fixtures | 39 | `tools/conformance_report.py` visibility only |
| Behavior fixtures | 45 | `rkaf-behavior-validate`, `tools/conformance_report.py` L4 |
| Total L1-L4 corpus | 301 | `tools/conformance_report.py` |

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

A fixture's `@graph` need not be wholly self-contained. Properties typed
`@id` without a registered class range (for example `rkaf:detectedBy`,
`rkaf:subject`, and `rkaf:targets`) may reference opaque IRIs defined in
sibling fixtures. A property listed in
`constraints/semantics/l0-ranges.cue`, however, compiles to `sh:class`; its
referenced node MUST carry the declared type in the same validation graph.
This includes the rulemaking relationships and `prov:wasDerivedFrom`.
Where a fixture exercises an isolated node and the relationship is
incidental, add a top-level `_comment` key noting the intent.

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
