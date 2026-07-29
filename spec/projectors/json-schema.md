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
    "rkaf-version": "<current Rulespec VERSION>",
    "rkaf-depth":   "D1" | "D2" | "D3" | "D4" | "D5",
    "rkaf:overlay": "<a JSON-LD graph using context/rkaf-context.jsonld>"
  }
}
```

The `x-rkaf` key is reserved; native artifacts MUST NOT use `x-rkaf` for any other purpose.

## 2. Operations

- **Attach:** writes `merged = {...native, "x-rkaf": {rkaf-version, rkaf-depth, "rkaf:overlay": overlay}}`.
- **Extract:** returns `(native, overlay)` where `native` is `merged - "x-rkaf"` and `overlay` is `merged["x-rkaf"]["rkaf:overlay"]`.
- **Validate:** dispatches every typed overlay node to every generated JSON
  Schema 2020-12 definition targeting that `@type` under
  `compiled/json-schema/`.
- **Round-trip:** `Attach(native, overlay) → Extract` MUST equal `(native, overlay)` byte-identically when serialized canonically.
- **Derive:** invokes `tools/constraints_compile.py --in <profile.cue> --target json-schema`. Output is a JSON Schema Draft 2020-12 document expressing the profile.

Generated definitions use two Rulespec extension keywords for CUE constraints
that JSON Schema Draft 2020-12 cannot express:

- `x-rkaf-order` compares two sibling values and rejects an inverted pair.
- `x-rkaf-not-equal` compares two sibling values and rejects the record when
  both are present and equal.

The **Validate** operation MUST enforce both keywords. A generic JSON Schema
processor may ignore them as annotations, so its verdict alone does not
satisfy the Rulespec L2 gate.

## 3. Carrier collision

JSON Schema's existing `x-` extension namespace is partner-shareable; the `x-rkaf` key is reserved by this convention. Implementations encountering a non-Rulespec `x-rkaf` payload (no `rkaf-version` key) MUST refuse to extract.

## 4. AI-tractability

Derive output MUST emit closed enums as JSON Schema `enum` (not `oneOf` of literal `const`s) and MUST emit each Vocabulary class as a `$defs` entry whose name matches the Vocabulary class name without the `rkaf:` prefix. This keeps LLM tool-use APIs (which target JSON Schema) tractable.

## 5. `rkaf:llmHint` carriage

The `rkaf:llmHint` annotation property (v0.2 §5.4) is carried into Derive output as `x-rkaf-llmHint` annotations on the matching `$defs` node. Other `x-rkaf-*` annotations are reserved for future Vocabulary-bound annotations.
