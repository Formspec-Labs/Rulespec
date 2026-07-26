# Rulespec tools

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

[`l0_mapping_audit.py`](l0_mapping_audit.py) validates the normative fenced mapping blocks defined in `spec/rkaf-conformance.md`. It checks full term IRIs, closed-enum targets, duplicate column mappings, and the L0-only fields in partner self-certifications.

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
