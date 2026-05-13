# Rulespec JSON-LD Projector — Carrier Convention v0.2

**Status:** Pre-release, normative.
**Carrier-convention version:** 0.2.0
**Spec:** Source spec §8.1 (Projector contract).

## 1. Carrier

A Rulespec overlay attaches to a JSON-LD artifact via shared graph composition. Both native and overlay nodes appear under a single `@graph`:

```json
{
  "@context": [
    "<native context>",
    "https://rulespec.org/context/rkaf-context-v0.2.jsonld"
  ],
  "@graph": [
    { "@id": "...", "@type": "<native type>" },
    { "@id": "...", "@type": "rkaf:Assertion" }
  ]
}
```

The native artifact's `@context` is preserved; the v0.2 Rulespec context is appended. Conflicts are resolved by prefix discipline (`rkaf:` is reserved; native namespaces are partner-controlled).

## 2. Operations

- **Attach:** merges `@graph` arrays; appends rkaf-context to `@context`.
- **Extract:** partitions `@graph` into (native nodes — those with no `rkaf:` prefix in `@type`) and (overlay nodes — those with `rkaf:` prefix in `@type`).
- **Validate:** validates each overlay node against its compiled JSON Schema 2020-12 (matched by `@type`).
- **Round-trip:** `Attach(native, overlay) → Extract` MUST equal `(native, overlay)` after canonical normalization (the Rust reference implementation also preserves byte-equality on the common shape — single-element `@context` is unwrapped back to a string on Extract).
- **Derive:** invokes `tools/constraints_compile.py --in <profile.cue> --target cue`. Emits a JSON-LD context fragment plus a companion SHACL pointer keyed at the canonical rkaf context URL.

## 3. Canonicalization

Round-trip parity is asserted on URDNA2015 canonical N-Quads when the Rust `rdf-canon` integration lands (Plan 6 SDK work). For v0.2 MVP, the reference projector asserts byte-equality on the common shape: native `@context` either a string or a single-element array; overlay `@context` either a string or a single-element array; `@graph` an array of typed nodes. Inputs outside this shape MAY round-trip canonically but are not guaranteed to round-trip byte-identically.

## 4. Type-namespace partition

Extract partitions `@graph` nodes by the prefix of `@type`. Nodes whose `@type` starts with `rkaf:` are overlay nodes; all others are native. A node with no `@type` is native. A node carrying both a `rkaf:` `@type` and a native `@type` (multi-type) is overlay; the native side MUST replicate the node minus the `rkaf:` type if it needs to be addressable from native consumers.
