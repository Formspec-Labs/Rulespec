# `rkaf:us-frdoc-x` implementation run notes

## Result

Implemented the self-dating X-prefixed Federal Register document-number space
as `rkaf:us-frdoc-x` with lexical shape
`^urn:rkaf:us:frdoc-x:X[0-9]{2}-[0-9]{5,7}$`. The published `X` remains part
of identity. The release version is `0.2.0-pre.18`.

## Corpus re-derivation

I queried the read-only corpus
`/Users/mikewolfd/Work/corpora/_preserved-2026-08-27/rulespec-stabilization-baseline-final/federal_register.parquet`
with DuckDB v1.5.5 before editing. The family predicate was
`regexp_matches(document_number,'^X[0-9]{2}-[0-9]+$')`, deliberately broader
than the proposed lexical space. I split at the hyphen, treated the final four
tail digits as `MMDD`, and treated every preceding tail digit as the sequence.

The results matched the brief exactly:

| Measurement | Re-derived result |
|---|---:|
| X-prefixed rows | 4,400 |
| Tail width 5 | 4,194 |
| Tail width 6 | 206 |
| Sequence width 1 | 4,194 |
| Sequence width 2 | 206 |
| Maximum observed sequence | 30 |
| Encoded date matches `publication_date` | 4,400/4,400 |
| Missing publication dates | 0 |

The specimen rows also matched: `X97-10423` was published 1997-04-23 at
62 FR 19825, and `X09-101207` was published 2009-12-07 at 74 FR 64213.

## Bound decision

Kept the proposed `{5,7}` tail bound. Observed sequences reach 30, but a
seven-digit tail permits a three-digit sequence through 999 documents on one
day. That is bounded capacity headroom rather than a tight fit to historical
data. It avoids repeating the fixed-width failure that would already exclude
206 real six-digit tails, while retaining a finite upper fence.

The space takes no date qualifier. Producers read it from the right and compare
the encoded year and `MMDD` with `publication_date`; a mismatch is defective
source data. The scheme mints all 4,400 X-prefixed rows. `document_type`
carries genre and editorial tier.

## Fixtures

Added nine fixtures, raising the conformance corpus from 531 to 540:

- Three positives: the real five-digit and six-digit specimens, plus a
  clearly marked capacity-only seven-digit tail with sequence 999.
- Six negatives: four-digit and eight-digit tails, one-digit and three-digit
  year heads, missing `X`, and a modern-form value under the X scheme.

## Sites changed

- `constraints/profiles/us-rulemaking/us-regulatory-artifact.cue`: added the
  eighth enum member and the guarded X grammar.
- `spec/rkaf-conformance.md`: added the normative self-dating, right-anchored,
  prefix-preserving, and bounded-capacity rules.
- `spec/rkaf-rulemaking.md` and `spec/rkaf-core.md`: added the canonical form,
  fallback obligations, measurements, and eighth-scheme cross-reference.
- `docs/adr/2026-09-02-us-frdoc-legacy-space-request.md`: recorded execution
  and the bound rationale.
- `fixtures/artifact-us-frdoc-x-*.jsonld` and
  `fixtures/negatives/artifact-us-frdoc-x-*.jsonld`: added all nine cases.
- `tools/constraints_parity.py`, `tools/test_semantic_carriers.py`, and
  `tools/test_constraints_compile.py`: registered every new boundary and the
  exact generated pattern.
- `compiled/{json-schema,typescript,shacl,rego}/profiles/us-rulemaking/`,
  `crates/rkaf-core/src/generated/profiles/us_rulemaking/`, and
  `src/rulespec_conformance/contract/{enums,terms}.py`: regenerated target and
  public export files.
- `spec/rkaf-conformance.md` and
  `reference-corpora/us-rulemaking/v0.2/manifest.dcat.jsonld`: repinned to
  `sha256:e9d02fb26fef5120c1c4e905a377554818c7d22abb9ad18bcdc44912f3557be5`.
- `VERSION`, `pyproject.toml`, `crates/Cargo.toml`, `crates/Cargo.lock`,
  `context/rkaf-context.jsonld`, and `uv.lock`: synchronized to pre.18;
  `CHANGELOG.md` records the release change.

## Generation path

The repository documents `make compile` as the canonical entry point. It sets
`PYTHON` and invokes `tools/compile_all.sh`, which runs
`tools/constraints_compile.py` for JSON Schema, TypeScript, SHACL, Rego, and
Rust, then runs `tools/repin_contract_digest.py`. I ran that wrapper with the
documented `PYTHON=python3` override after the default dependency-isolation
invocation could not reach the package index. I then ran
`tools/build_contract_exports.py` for the generated Python exports and
`uv lock --offline` for the self-referenced wheel version. No generated target
was hand-edited.

## Verification

- PASS — corpus measurement matched every stop condition.
- PASS — canonical generation and contract digest repinning.
- PASS — CUE v0.10.0 vet across core, profiles, semantic ranges, adversarial,
  extraction, and platform constraints.
- PASS — positive gate: 124 fixtures, 1,881 triples, 0 violations; every new
  negative failed as expected; reference corpus passed Rust and Python.
- PASS — `make test-conformance`: 540 fixtures, 0 divergences.
- PASS — constraints parity: 0 core divergences; two documented adversarial
  findings remain non-release-blocking.
- PASS — Rust workspace tests, including 45 generated-carrier round trips,
  runtime behavior, profile isolation, validators, and CLI tests.
- PASS — 307 audit unit tests; L0-L3 and L4 coverage; 13/13 projector parity;
  version sync; contract exports; digest pins; code-generation lock-step.
- PASS — `UV_OFFLINE=1 make test-package-conformance`; the installed wheel's
  CLI, packaged schemas/shapes/context, enums, terms, and exclusions passed.
- BLOCKED OUTSIDE THIS CHANGE — the aggregate `make test-audits` target reaches
  `tools/rename_audit.py` and reports one pre-existing lowercase legacy-brand
  token embedded in `wiki/temp/dependency_graphs/rulespec_dependency_graph.json`.
  The repository contains no documented generator for that generated file, so
  the brief's stop rule applied and the file remains untouched. Every preceding
  audit, including all 307 unit tests, passed.

## Wheel

`dist/conformance/rulespec_conformance-0.2.0rc18-py3-none-any.whl`

SHA-256:
`bd4816dac509ed0a9686fc94104d8463d6e05c53b8e2ce74e9d1ea9a67b76977`

## Surprises

The worktree-local `.tools/cue` was absent; an existing sibling checkout
provided the exact repository-pinned CUE v0.10.0 binary. The default compile
and first package-proof attempts tried to reach the package index. Generation
passed with the Makefile's supported local-Python override, and the package
proof passed with the already populated uv cache in offline mode. The sibling
Python environment needed a temporary, non-repository import bridge for its
missing `yaml`, `pyarrow`, and `rfc8785` packages; the pinned RDF packages
remained those from the sibling environment.
