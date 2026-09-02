# `rkaf:us-frdoc-legacy` implementation run notes

## Result

Implemented option B as amended: `rkaf:us-frdoc-legacy` uses the exact
date-qualified lexical space
`^urn:rkaf:us:frdoc-legacy:[0-9]{2}-[0-9]{1,6}:[0-9]{4}-[0-9]{2}-[0-9]{2}$`.
The existing `rkaf:us-frdoc` grammar and its `94-120124` family-negative
fixture remain unchanged. The release version is `0.2.0-pre.17`.

## Corpus derivation

I queried
`/Users/mikewolfd/Work/corpora/_preserved-2026-08-27/rulespec-stabilization-baseline-final/federal_register.parquet`
with DuckDB v1.5.5. The parquet schema names the date column
`publication_date` and stores it as `VARCHAR`.

The family predicate was exactly
`regexp_matches(document_number,'^[0-9]{2}-[0-9]+$')`. Grouping by
`LENGTH(SPLIT_PART(document_number,'-',2))` produced:

| Tail length | Rows |
|---:|---:|
| 1 | 112 |
| 2 | 1,258 |
| 3 | 13,226 |
| 4 | 119,770 |
| 5 | 261,125 |
| 6 | 7 |

The totals match the brief: 1,004,233 parquet rows, 395,498 bare-legacy rows,
and heads spanning `00`–`99`. The null-or-empty `publication_date` refusal
population is **0 rows**. Grouping the family by `document_number` and keeping
groups with `COUNT(*) > 1` found **0 colliding values** and **0 rows in
collision groups** inside this rolled-up parquet.

The zero within-parquet count does not contradict the amendment. The parquet
contains the `00-111`, 2000-01-14 Rule; the ADR amendment records the API's
separate `00-111`, 2000-01-18 Notice. Their two valid identifiers differ by
date.

## Fixtures

Added seven positive fixtures: one parquet specimen for each measured tail
length, plus the API half of the `00-111` collision. The length-three specimen
is the parquet half of that pair.

| Tail | Number | Publication date | Evidence |
|---:|---|---|---|
| 1 | `00-1` | `2000-01-20` | parquet row |
| 2 | `00-10` | `2000-01-04` | parquet row |
| 3 | `00-111` | `2000-01-14` | parquet Rule row |
| 4 | `00-1000` | `2000-01-18` | parquet row |
| 5 | `00-02053` | `2000-02-04` | parquet row |
| 6 | `94-120124` | `1994-04-28` | parquet row |
| 3 | `00-111` | `2000-01-18` | ADR amendment, API Notice |

Each positive fixture's `_comment` cites its number-and-date evidence. Added
seven negatives for empty tail, seven-digit tail, one-digit head, three-digit
head, modern form, missing date, and malformed date. Total fixtures added:
**14** (7 positive, 7 negative).

## Sites changed

- `constraints/profiles/us-rulemaking/us-regulatory-artifact.cue`: added the
  enum member and guarded grammar; updated the scheme count.
- `spec/rkaf-rulemaking.md`: documented the sibling scheme, refusal rule,
  collision rationale, and re-derived measurements in the normative §5/§5.2
  home. `spec/rkaf-core.md` now says seven profile grammars.
- `docs/adr/2026-09-02-us-frdoc-legacy-space-request.md`: restored the
  amendment present in the sibling authoritative checkout and recorded the
  local DuckDB re-derivation, null-date count, and within-parquet count.
- `fixtures/artifact-us-frdoc-legacy-*-positive.jsonld` and
  `fixtures/negatives/artifact-us-frdoc-legacy-*-negative.jsonld`: added the
  14 cases above. The pre-existing `artifact-us-frdoc-legacy-year-negative`
  file stayed byte-identical to the sibling baseline.
- `tools/constraints_parity.py`, `tools/test_semantic_carriers.py`, and
  `tools/test_constraints_compile.py`: added positive/negative parity cases,
  profile-isolation cases, the seventh scheme, and an exact-pattern assertion.
- `src/rulespec_conformance/contract/enums.py` and `terms.py`: regenerated the
  public Python enum and term exports from CUE.
- `compiled/{json-schema,typescript,shacl,rego}/profiles/us-rulemaking/`
  `us-regulatory-artifact.*`: regenerated all four portable targets. The
  ignored `compiled/` tree now contains 234 generated files in total.
- `crates/rkaf-core/src/generated/profiles/us_rulemaking/`
  `us_regulatory_artifact.rs`: regenerated the Rust enum carrier.
- `spec/rkaf-conformance.md` and
  `reference-corpora/us-rulemaking/v0.2/manifest.dcat.jsonld`: repinned by the
  compiler to contract digest
  `sha256:f7fc0587b3da5ccdc690f8ce8f5119c899c375634de796f3cea5c4650aed0542`;
  the manifest's validation date is 2026-09-02.
- `VERSION`, `pyproject.toml`, `crates/Cargo.toml`, `crates/Cargo.lock`,
  `context/rkaf-context.jsonld`, and `uv.lock`: synchronized to pre.17
  (`uv.lock` uses the PEP 440 form `0.2.0rc17`). `CHANGELOG.md` records the
  feature and measurements.

## Generation path

The repository documents `make compile` as the entry point. It sets `PYTHON`
and runs `tools/compile_all.sh`; that wrapper invokes
`tools/constraints_compile.py` for JSON Schema, TypeScript, SHACL, Rego, and
Rust, then runs `tools/repin_contract_digest.py`. The repository path is
`compiled/<target>/profiles/us-rulemaking/`, not the brief's
`compiled/.../us-rulemaking/v0.2/`; `v0.2` belongs to the reference-corpus
manifest path. No compiled output was hand-edited.

The first `make compile` attempt stopped before generation because `uv` could
not fetch uncached `rfc8785` without network access. The same canonical wrapper
then passed with its supported `PYTHON=python3` override, using installed local
dependencies. `tools/codegen_drift_audit.py` later recompiled the tree and
confirmed byte-for-byte lock-step.

## Verification

- PASS — CUE v0.10.0 `make cue-vet`, using the sibling checkout's binary that
  matches `tools/install-cue.sh`'s exact pin. The worktree-local `.tools/cue`
  was absent, so the default invocation failed before validation.
- PASS — 307 audit unit tests after regenerating contract exports. The initial
  run correctly caught the stale six-member Python export.
- PASS — positive gate: 121 fixtures, 1,866 triples, 0 violations.
- PASS — negative gate: every negative failed as expected, including all seven
  new legacy negatives.
- PASS — constraints parity: 0 core divergences; the two existing adversarial
  findings remain documented.
- PASS — conformance report: 530 fixtures, 0 divergences.
- PASS — reference corpus through Rust and Python validators: 0 violations.
- PASS — full Rust workspace tests; L4 coverage; all 13 projector-parity
  checks; version sync; digest pins; contract exports; code-generation drift.
- FAIL (pre-existing, unrelated) — `make test-audits` stops at
  `tools/rename_audit.py`: one `brand-pkaf` string in
  `wiki/temp/dependency_graphs/rulespec_dependency_graph.json`. The failing
  file was not changed.
- FAIL (test-launch configuration) — exact command `uv run pytest -q` selects
  the global `/Users/mikewolfd/.pyenv/versions/3.12.9/bin/pytest`, because
  pytest is not declared by this project, then stops with eight collection
  import errors for `tools` and `rulespec_artifacts`. The project environment
  imports both packages; the repository's documented `unittest` suite passes.

## Other observations

The brief names `spec/rkaf-conformance.md` as the scheme-documentation site,
but that file contains no scheme table in either checkout. The repository
declares `spec/rkaf-rulemaking.md` §5.2 as the normative home, so the scheme
text landed there; generation touched `spec/rkaf-conformance.md` only to repin
its embedded contract digest. Verification created only ignored local build
artifacts under `.venv/`, `.pytest_cache/`, `compiled/`, `crates/target/`, and
Python `__pycache__/` directories.
