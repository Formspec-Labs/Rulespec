# Rulespec tools

## L0 carrier-mapping audit

[`l0_mapping_audit.py`](l0_mapping_audit.py) validates the normative fenced mapping blocks defined in `spec/rkaf-conformance.md`. It checks full term IRIs, closed-enum targets, duplicate column mappings, and the L0-only fields in partner self-certifications.

```sh
python3 tools/l0_mapping_audit.py docs/ontology.md
python3 tools/l0_mapping_audit.py conformance/partners/example.yaml
python3 -m unittest tools.test_l0_mapping_audit -v
```

With no path, the audit discovers every L0 declaration under `conformance/partners/`.

## Studio profile `schemas-derived/`

[`studio_schemas_derive_manifest.py`](studio_schemas_derive_manifest.py) is the orchestrator for policy-studio’s manifest-driven derive. The regression fixture [`fixtures/projectors/json-schema/derive-studio-profile-manifest.json`](../fixtures/projectors/json-schema/derive-studio-profile-manifest.json) holds `expectedSchemaCount` and related paths. Optional field **`schemasDeriveManifest`** documents the sibling policy-studio file (`policy-studio/profiles/studio/schemas-derive-manifest.json` in a formspec-stack checkout); `profiles/studio/studio_profile_derive.py` checks that path alignment when both Rulespec and policy-studio are present.

Run unit tests from the Rulespec root:

```sh
python3 -m unittest tools.test_studio_schemas_derive_manifest -v
```
