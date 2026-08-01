# Rulespec release records

This directory contains closed JSON Schemas and offline conformance fixtures
for the independent Rulespec Core and Rulespec Extrapolator release units. See
[`spec/rulespec-releases.md`](../spec/rulespec-releases.md) for the normative
identity and validation rules.

`fixtures/upstream/` holds a byte-for-byte publisher-owned `DocumentRelease`
and a static RefSpec vocabulary atlas. Rulespec pins and validates those
copies; it does not own their contents. The bundled `m2-input-releases.json`
repeats the document record so the portable validator can consume one JSON
input file. The ExtrapolationRelease separately pins the atlas asset and the
exact `ReferenceResourceRelease` used by its assignments.

`m2-extrapolation-release-positive.json` and `m2-negative-controls.json` are
deterministic generated fixtures. Rebuild them with:

```sh
python3 tools/build_rulespec_release_fixtures.py all --write
```

To refresh publisher artifacts, provide the reviewed document and atlas paths
in the same operation:

```sh
python3 tools/build_rulespec_release_fixtures.py all --write \
  --vendor-document-release /path/to/document-release.json \
  --vendor-vocabulary-atlas /path/to/vocabulary-atlas
```

Every checked-in release has `release_status=fixture` or is a copied upstream
fixture. These files do not claim a tag, package publication, deployment, or
activation.

The checked atlas comes from RefSpec's managed-release publisher. Rulespec
reads only its static manifest and N-Quads distribution through
[`tools/refspec_atlas.py`](../tools/refspec_atlas.py); it does not import
RefSpec source or carry a second vocabulary release format. These checked
files are fixture provenance, not proof that the complete cross-product
publication gate has run.
