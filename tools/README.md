# PKAF tools

## Studio profile `schemas-derived/`

[`studio_schemas_derive_manifest.py`](studio_schemas_derive_manifest.py) is the orchestrator for policy-studio’s manifest-driven derive. The regression fixture [`fixtures/projectors/json-schema/derive-studio-profile-manifest.json`](../fixtures/projectors/json-schema/derive-studio-profile-manifest.json) holds `expectedSchemaCount` and related paths. Optional field **`schemasDeriveManifest`** documents the sibling policy-studio file (`policy-studio/profiles/studio/schemas-derive-manifest.json` in a formspec-stack checkout); `profiles/studio/studio_profile_derive.py` checks that path alignment when both PKAF and policy-studio are present.

Run unit tests from PKAF root:

```sh
python3 -m unittest tools.test_studio_schemas_derive_manifest -v
```
