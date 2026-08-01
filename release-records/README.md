# Rulespec release records

This directory contains closed JSON Schemas and offline conformance fixtures
for the independent Rulespec Core and Rulespec Extrapolator release units. See
[`spec/rulespec-releases.md`](../spec/rulespec-releases.md) for the normative
identity and validation rules.

`fixtures/upstream/` holds byte-for-byte copies of publisher-owned
`DocumentRelease` and `VocabularyRelease` artifacts. Rulespec pins and
validates those copies; it does not own their contents. The bundled
`m2-input-releases.json` repeats the same JSON records so the portable validator
can consume one file.

`m2-extrapolation-release-positive.json` and `m2-negative-controls.json` are
deterministic generated fixtures. Rebuild them with:

```sh
python3 tools/build_rulespec_release_fixtures.py all --write
```

To refresh publisher artifacts, provide both reviewed source paths in the same
operation:

```sh
python3 tools/build_rulespec_release_fixtures.py all --write \
  --vendor-document-release /path/to/document-release.json \
  --vendor-vocabulary-release /path/to/vocabulary-release.json
```

Every checked-in release has `release_status=fixture` or is a copied upstream
fixture. These files do not claim a tag, package publication, deployment, or
activation.
