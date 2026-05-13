# Rulespec JSON Schema Projector — Carrier Convention v0.2

**Status:** Pre-release, normative.
**Carrier-convention version:** 0.2.0
**Spec:** Source spec §8.1 (Projector contract).

## 1. Carrier

A Rulespec overlay attaches to a JSON document via a single root-level extension key:

```json
{
  "<native fields>": "...",
  "x-rkaf": {
    "rkaf-version": "0.2.0-pre.5",
    "rkaf-depth":   "D1" | "D2" | "D3" | "D4" | "D5",
    "rkaf:overlay": "<a JSON-LD graph using context/rkaf-context-v0.2.jsonld>"
  }
}
```

The `x-rkaf` key is reserved; native artifacts MUST NOT use `x-rkaf` for any other purpose.

## 2. Operations

- **Attach:** writes `merged = {...native, "x-rkaf": {rkaf-version, rkaf-depth, "rkaf:overlay": overlay}}`.
- **Extract:** returns `(native, overlay)` where `native` is `merged - "x-rkaf"` and `overlay` is `merged["x-rkaf"]["rkaf:overlay"]`.
- **Validate:** runs the compiled JSON Schema 2020-12 validator (from `compiled/json-schema/`) over the overlay graph.
- **Round-trip:** `Attach(native, overlay) → Extract` MUST equal `(native, overlay)` byte-identically when serialized canonically.
- **Derive:** invokes `tools/constraints_compile.py --in <profile.cue> --target json-schema`. Output is a JSON Schema Draft 2020-12 document expressing the profile.

## 3. Carrier collision

JSON Schema's existing `x-` extension namespace is partner-shareable; the `x-rkaf` key is reserved by this convention. Implementations encountering a non-Rulespec `x-rkaf` payload (no `rkaf-version` key) MUST refuse to extract.

## 4. AI-tractability

Derive output MUST emit closed enums as JSON Schema `enum` (not `oneOf` of literal `const`s) and MUST emit each Vocabulary class as a `$defs` entry whose name matches the Vocabulary class name without the `rkaf:` prefix. This keeps LLM tool-use APIs (which target JSON Schema) tractable.

## 5. `rkaf:llmHint` carriage

The `rkaf:llmHint` annotation property (v0.2 §5.4) is carried into Derive output as `x-rkaf-llmHint` annotations on the matching `$defs` node. Other `x-rkaf-*` annotations are reserved for future Vocabulary-bound annotations.
