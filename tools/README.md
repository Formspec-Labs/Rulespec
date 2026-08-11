# Rulespec tools

## Canonical release records

[`rulespec_release.py`](rulespec_release.py) validates content-addressed
`RulespecCoreRelease` and `ExtrapolationRelease` JSON without a sibling
repository or mutable database. It rejects non-canonical inputs, verifies exact
release pins and reference closure, checks source coordinates and reversible
text projections, and applies the baseline and deterministic-selection gates.

[`build_rulespec_release_fixtures.py`](build_rulespec_release_fixtures.py)
reproduces the sealed M2 positive release and negative controls from a
publisher-owned SpicyRegs release and Rulespec's own atlas-membership stub
(see below). Refreshing the vendored document copy requires an explicit
upstream path; the stub atlas regenerates deterministically with `--write`.
Normal tests read only the checked files under `release-records/fixtures/`.

```sh
python3 tools/rulespec_release.py validate \
  release-records/fixtures/m2-extrapolation-release-positive.json \
  --input release-records/fixtures/rulespec-core-release-m2.json \
  --input release-records/fixtures/m2-input-releases.json \
  --vocabulary-atlas release-records/fixtures/rulespec-atlas-membership-stub
python3 -m unittest tools.test_rulespec_releases -v
```

## SourceCatalogRelease v1 candidate

[`source_catalog_release.py`](source_catalog_release.py) (a shim; the
implementation is `rulespec_conformance.source_catalog_release`) verifies a
materialized `SourceCatalogRelease` v1 bundle: root identity, member manifest,
member digests, the two canonical set digests over `U` and `S`, the source-item
schema, the five selection dispositions, and the counts and coverage accounting.
It reports one diagnostic per defect and a first failure under a declared total
order. `spec/rulespec-source-catalog-release.md` is the normative statement.

[`build_source_catalog_release_fixtures.py`](build_source_catalog_release_fixtures.py)
rebuilds the sealed corpus — one valid bundle and one invalid bundle per
diagnostic code, each a single-rule mutation of the valid one — plus
`release-records/source-catalog-release-v1-candidate.json`, a
`RulespecCoreRelease` whose `release_id` is the candidate bundle digest.

```sh
python3 tools/build_source_catalog_release_fixtures.py --check   # drift gate
python3 tools/source_catalog_validate.py                          # candidate gate
python3 -m unittest tools.test_source_catalog_release -v
```

Editing any pinned byte changes the bundle digest, which is the point: a
candidate is immutable, and an edit starts a new one.

## Atlas-membership reader seam

`rulespec_release.py` and `extrapolation_release_v2.py` each declare an
`AtlasMembershipReader` Protocol (`pin()`, `rulespec_core_pin()`,
`require_member(...)`): a release may pin an external, product-owned atlas
asset that proves reference-resource membership, and the validators verify
that pin against whatever reader a caller supplies. Neither module knows or
cares whose atlas that is.

[`atlas_membership_stub.py`](atlas_membership_stub.py) is a minimal,
rulespec-native implementation of that Protocol for this repository's own
tests and fixture builders: a tiny, tamper-evident `manifest.json` +
`members.json` pair expressed in Rulespec's own canonical-JSON conventions,
with no downstream namespace, wire format, or vocabulary baked in. It is not
a vendored copy of any product's atlas format, and production code never
constructs it directly — validators only ever receive an
`AtlasMembershipReader` through dependency injection. A real deployment that
needs to verify a release against an external, product-owned atlas supplies
its own reader satisfying the same three-method Protocol.

Run the local gate with:

```sh
python3 -m unittest tools.test_atlas_membership_stub -v
```

`test_atlas_membership_stub.py` builds synthetic stub atlases in a temp
directory and asserts tampering with either file is caught before
`require_member` can be reached; it depends on nothing outside this repo.

## Semantic carrier tests

[`test_semantic_carriers.py`](test_semantic_carriers.py) checks that MEANING
survives the carrier, not just shape. `test_constraints_compile.py` proves the
compiled artifacts have the right fields; these tests push real documents
through real carriers — JSON-LD expansion and compaction via `rdflib`, SHACL
validation via `pySHACL`, an actual recompilation via `constraints_compile` —
and check what comes out the other side.

One test class per category, so a reviewer can map them one to one:

| Category | Class | Sample question |
|---|---|---|
| identity | `IdentityCarrierTests` | does a fragment's digest binding still equal its Artifact's after a round trip? |
| direction | `DirectionCarrierTests` | does transposing two class-ranged edges change the verdict? |
| typed values | `TypedValueCarrierTests` | does an `xsd:date` survive expand → compact → expand? |
| transformations | `TransformationStabilityTests` | does a regenerated shape graph return the same verdicts? |
| evidence resolution | `EvidenceResolutionCarrierTests` | does an evidence IRI dereference to a fragment of the named Artifact? |
| composition | `CompositionCarrierTests` | does every `#AssertionEnvelope` field reach every composer in every target? |
| profile isolation | `ProfileIsolationCarrierTests` | does kernel-only validation differ from composed validation exactly where documented? |

Two halves live in Rust, where the carrier does:
`crates/rkaf-core/tests/fixture_round_trip.rs` (typed SDK round trip) and
`crates/rkaf-runtime/tests/profile_isolation_carrier.rs` (whether a
profile-contributed lifecycle kind still drives the kernel stale transition).

```sh
python3 -m unittest tools.test_semantic_carriers -v
```

Requires `compiled/` to exist — run `make compile` first. `make test-audits`
runs the module as part of the gate sweep, and the `Contract unit suites` step
of [`.github/workflows/constraints-parity.yml`](../.github/workflows/constraints-parity.yml)
runs it on every PR, immediately after `tools/compile_all.sh` regenerates
`compiled/`.

## L0 carrier-mapping audit

[`l0_mapping_audit.py`](l0_mapping_audit.py) validates the normative fenced mapping blocks defined in `spec/rkaf-conformance.md`. It checks full term IRIs, closed-enum targets, duplicate column mappings, and the L0-only fields in partner self-certifications — including the optional `excluded_terms` and `excluded_tables` carve-outs, where every excluded term must be a registered contract term the mapping does NOT claim and every excluded table must be one the mapping does not cover. Both keys are optional; a declaration that omits them is audited exactly as before.

```sh
python3 tools/l0_mapping_audit.py docs/ontology.md
python3 tools/l0_mapping_audit.py conformance/partners/rulespec-reference.yaml
python3 -m unittest tools.test_l0_mapping_audit -v
```

With no path, the audit discovers every L0 declaration under `conformance/partners/`.

## Studio profile `schemas-derived/`

[`studio_schemas_derive_manifest.py`](studio_schemas_derive_manifest.py) is the orchestrator for policy-studio’s manifest-driven derive. The regression fixture [`fixtures/projectors/json-schema/derive-studio-profile-manifest.json`](../fixtures/projectors/json-schema/derive-studio-profile-manifest.json) holds `expectedSchemaCount` and related paths. Optional field **`schemasDeriveManifest`** documents the sibling policy-studio file (`policy-studio/profiles/studio/schemas-derive-manifest.json` in a formspec-stack checkout). Path alignment between the two is checked on the policy-studio side; this repo ships only [`profiles/studio/README.md`](../profiles/studio/README.md), which records what the studio profile is and where its deriver lives.

Run unit tests from the Rulespec root:

```sh
python3 -m unittest tools.test_studio_schemas_derive_manifest -v
```
