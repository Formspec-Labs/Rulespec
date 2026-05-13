# Rulespec OpenAPI 3.1 Projector — Carrier Convention v0.2

**Status:** Pre-release, normative.
**Carrier-convention version:** 0.2.0
**Spec:** Source spec §8.1 (Projector contract).

## 1. Carrier

OpenAPI 3.1's vendor-extension mechanism (`x-` prefix on any object) carries the overlay at three levels:

- **Document-level:** root-level `x-rkaf = { rkaf-version, rkaf-depth, "rkaf:overlay": <graph> }`.
- **Operation-level:** `paths.<path>.<method>.x-rkaf = { ... }`.
- **Schema-level:** `components.schemas.<Name>.x-rkaf = { ... }`.

The reference Rust implementation supports document-level Attach/Extract; operation- and schema-level helpers land with the Layer 5 TypeScript SDK (Plan 6) which is the more natural consumer for partial-path overlays.

## 2. Operations

- **Attach:** writes `x-rkaf` at the requested level (default: document).
- **Extract:** walks the document and returns the OpenAPI document minus every `x-rkaf` plus the overlay graph. The MVP returns only the document-level overlay; partial-level Extract is reserved for v0.3.
- **Validate:** validates the overlay against the v0.2 Vocabulary's compiled JSON Schema (delegated to the JSON Schema projector when composed).
- **Round-trip:** Attach → Extract MUST be the identity (byte-equality).
- **Derive:** invokes `tools/constraints_compile.py --in <profile.cue> --target json-schema` and wraps the `$defs` into an OpenAPI 3.1 document with `components.schemas` populated from the profile. Output is a complete OpenAPI document consumable by API tooling.

## 3. Carrier collision

The `x-rkaf` key is reserved. Implementations MUST refuse to attach if `x-rkaf` is already present at the same location with a non-Rulespec payload (detected by absence of `rkaf-version`).

## 4. AI-tractability

OpenAPI is the dominant carrier for LLM tool-use APIs. The Derive output carries each Vocabulary class as a `components.schemas` entry whose name matches the Vocabulary class name without the `rkaf:` prefix; `rkaf:llmHint` properties land as `x-rkaf-llmHint` annotations on the matching schema.
