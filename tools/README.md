# Rulespec Tooling

## `ci_validate.py`

The Rulespec CI validation gate. A multi-mode tool that loads SHACL shape files, validates fixtures against them, and reports conformance.

### Modes

```bash
python3 tools/ci_validate.py --mode core     # Core shapes only (baseline)
python3 tools/ci_validate.py --mode batch2   # Core + ConceptRegistry
python3 tools/ci_validate.py --mode batch3   # Core + ConceptRegistry + Lifecycle
python3 tools/ci_validate.py --mode batch4   # All four shape files (DEFAULT)
```

Each mode loads a specific shape set and validates all four fixtures. Modes are intended for downstream consumers who target a specific conformance level (e.g., a search engine that only needs Core conformance can validate against `--mode core`).

### Output

Per-fixture PASS/FAIL with triple count and violation count. Summary at the bottom:

```
Mode:       batch4 (Core + ConceptRegistry + Lifecycle + Justification)
Shapes:     4 files
Fixtures:   4
Triples:    1,206
Violations: 0
Result:     PASS
```

JSON output mode for CI pipelines:

```bash
python3 tools/ci_validate.py --json
```

### Exit codes

- `0` — all invariants pass
- `1` — validation failed (one or more fixtures has violations)
- `2` — setup error (missing files, wrong pyshacl version, parse failure)

### Drift detection

The tool tracks expected triple-count ranges per fixture. If a fixture's triple count drifts outside the expected range, the tool reports a non-fatal drift warning. Drift warnings indicate fixture content may have changed unexpectedly; they don't fail the build but they should be investigated.

### Working directory

The tool resolves shape and fixture paths relative to the `--repo-root` flag (default: current directory). Run from the repo root, or pass `--repo-root /path/to/rkaf-repo`.

### Requirements

```
pyshacl >= 0.31.0
rdflib >= 7.0.0
```

Install via:

```bash
pip install -r requirements.txt
```

### Why a custom gate instead of `pyshacl` CLI

The custom gate:

1. **Multi-mode support** — load different shape subsets in one tool
2. **Triple-count drift detection** — catches accidental fixture changes
3. **Structured output** — JSON mode for CI pipelines
4. **Environment checks** — verifies pyshacl version before validation (because conditional shape evaluation depends on pyshacl version behavior)
5. **Clean exit codes** — distinguishes validation failure from setup error

The raw `pyshacl` CLI is fine for ad-hoc validation; for sustained development the gate provides better feedback loops.

## Future tools (planned for v0.2)

The runtime conformance test layer (planned post-v0.1.1) will add:

- `tools/runtime_conformance.py` — runs cascade closure, reducer, and authority chain traversal tests against an implementation under test, diffing actual output against expected output in fixture-specific JSON files

- `tools/fixture_prep.py` — refreshes the inline `@context` in fixtures from `context/rkaf-context.jsonld` (currently this is done ad-hoc; codifying it prevents drift between the canonical context and inline fixture contexts)

- `tools/synthetic_defect.py` — runs the synthetic defect injection test suite (currently embedded in batch reports) as a standing CI gate

These are not in scope for v0.1.1.
