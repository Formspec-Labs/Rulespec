# Rulespec JSON-LD Contexts

Rulespec uses JSON-LD for serialization. The context files in this directory define how Rulespec terms map to IRIs and how property values are typed.

## Files

### `rkaf-context-v0.1.jsonld` (frozen historical)

The original v0.1 context shipped with v0.1-rc1. Preserved unchanged as a historical record.

### `rkaf-context-v0.2.jsonld` (current)

The current published context for v0.1.1. A strict additive superset of v0.1 — no semantic changes, only additions:

- Added `rkaf:definedInScope` as `@type: @id` (was missing in v0.1, treated as string literal)

Documented via `_meta` block at the top of the file. JSON-LD processors ignore keys not in `@context`, so the `_meta` block has no semantic effect on data; it's documentation that travels with the file.

## Hosting (planned)

Once published, these contexts will be hosted at stable URIs:

- `https://rulespec.org/context/v1.jsonld` → `rkaf-context-v0.1.jsonld` (frozen)
- `https://rulespec.org/context/v2.jsonld` → `rkaf-context-v0.2.jsonld` (current)

Fixtures and consumer artifacts reference one of these URIs via their `@context` field. Until hosting is set up, fixtures inline the full context as a literal object in their `@context` field; the file `fixtures/context.jsonld` is the canonical source for that inlined content.

## Why both versions ship

The v0.1 context is preserved because:

1. **Reproducibility.** Anyone wanting to validate against the v0.1-rc1 frozen package needs the v0.1 context exactly as it shipped.
2. **Provenance.** The single change (adding `definedInScope` typing) was discovered during Batch 2 validation; the audit trail starts with v0.1 and ends with v0.2.
3. **Forward compatibility.** Consumer systems that adopted v0.1 should continue to work; v0.2 is a strict superset, so existing v0.1 data validates under v0.2 without changes.

## Inlined contexts in fixtures

Each fixture file in `fixtures/` carries its `@context` inline (a full copy of the v0.2 context content, minus the `_meta` block). This is the canonical reference state for fixture validation.

The `fixtures/context.jsonld` file is the source from which the inline contexts are refreshed. It is **identical** to `context/rkaf-context-v0.2.jsonld` in content. The two files exist for distinct purposes:

- `context/rkaf-context-v0.2.jsonld` → the **published** context (the canonical artifact for hosting)
- `fixtures/context.jsonld` → the **fixture-prep source** (used by tooling to refresh fixture inlined contexts)

If you edit one, edit both. A future tooling improvement could collapse this duplication.

## Extension URIs

Several Rulespec properties accept either a closed enum value OR a declared extension URI (HTTP/HTTPS):

- `rkaf:evaluationAnchor` — closed v0.1 enum or declared extension URI
- `rkaf:scope` (on Attestation) — closed v0.1 enum or declared extension URI
- `rkaf:decision` (on Attestation) — closed v0.1 enum or declared extension URI
- `rkaf:adoptionScope` (on LocalAdoption) — string or declared extension URI

Extension URIs must be HTTP(S) IRIs and SHOULD be declared in a `rkaf:EvaluationAnchorExtensionRegistry` (per Rulespec Core §4.7) so consumers can discover and validate them. The current v0.1.1 release does not include any active extension URIs in the fixtures.

The shape files validate this either/or pattern via `sh:or` with the closed enum and an IRI-with-pattern alternative.
