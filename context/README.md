# Rulespec JSON-LD Contexts

Rulespec serializes as JSON-LD. `rkaf-context.jsonld` in this directory is the
single active context: it maps every Rulespec term to an IRI and declares how
each property's values are typed on the wire.

## Files

### `rkaf-context.jsonld` (current, v0.2)

The active context for Vocabulary v0.2. It covers the universal kernel
(`constraints/core/`), the document-analysis module (`constraints/analysis/`),
and every domain profile (`constraints/profiles/`) — one context, because a
profile composes kernel shapes rather than minting a parallel vocabulary.

The `_meta` block at the end of the file records the version, what it
supersedes, and the term-by-term delta from v0.1. JSON-LD processors ignore
keys outside `@context`, so `_meta` travels with the file without affecting
any data.

The v0.1 context is preserved unchanged at
`archive/v0.1/context/rkaf-context-v0.1.jsonld` for reproducibility against the
frozen v0.1.1 package. It is not loaded by any active gate.

## Rules this file MUST follow — audited

Two rules are enforced by a gate. Breaking either fails `make test-audits`.

1. **Every CUE-bound class carries a term definition** with `{"@type": "@id"}`.
   A class is CUE-bound when a shape in `constraints/` declares
   `"@type": "<term>"` and the compiled JSON Schema binds it (the same set
   `crates/rkaf-validate/build.rs` registers).
   `tools/test_semantic_carriers.py::CompositionCarrierTests::test_every_schema_bound_class_carries_a_context_term`
   fails the build on a bound class with no term definition here.

   This one is about DECLARATION COMPLETENESS, not about the wire. A class IRI
   only ever appears as an `@type` value, never as a property, so the
   `{"@type": "@id"}` coercion on it never fires, and a class compacts through
   the `rkaf` prefix whether or not a term for it exists — removing a class
   term changes no expanded graph and no compacted document. What the rule buys
   is that this file is a complete inventory of the 52 classes `rkaf-validate`
   dispatches on, so a reader answering "does Rulespec have a class for this"
   from the context gets the same answer the validator would give.

2. **Every enum-valued property carries an `@type: @id` or `@type: @vocab`
   coercion.** The compiled SHACL emits `sh:in` over IRI members, and an
   `sh:in` over IRIs only matches data whose values arrive as IRIs — an
   enum-valued term left uncoerced would arrive as a plain string literal and
   silently miss every value in the set. `constraints/README.md` states the
   rule; `tools/test_semantic_carriers.py::TypedValueCarrierTests::test_every_enum_valued_term_is_iri_coerced_in_the_context`
   checks it across every kernel, analysis, and profile source. This one IS
   about the wire: dropping a coercion changes validation verdicts.

## Conventions — not gated

The two below are conventions the file follows by hand. No gate enforces them,
and roughly 32 of the 295 CUE property terms currently have no entry here at
all. Adding a term that follows them is right; a term that does not will not be
caught by CI, so it has to be caught in review.

3. **Reference-valued properties carry `@type: @id`**, and repeatable ones add
   `"@container": "@set"` so a single value and a one-element array expand
   identically. A reference-valued term with no entry expands as a string
   literal, which nothing downstream flags unless the property also carries a
   declared class range in a `constraints/**/semantics/l0-ranges.cue`.

4. **Digest and timestamp properties carry their XSD datatype**
   (`xsd:string` for `sha256:`-prefixed digests, `xsd:dateTime` /`xsd:date` for
   times) so the value survives an expand/compact round-trip as a typed
   literal rather than a bare string. Ten timestamp terms (`rkaf:attestedAt`,
   `rkaf:revokedAt`, `rkaf:adoptedAt`, and seven more) are the current
   deviations.

## Hosting (planned)

`crates/rkaf-core` exposes the canonical URL as `RKAF_CONTEXT`
(`crates/rkaf-core/src/lib.rs`):

- `https://rulespec.org/context/rkaf-context.jsonld` → `rkaf-context.jsonld`
  (current, **canonical**)

Two version-numbered aliases are planned alongside it, each a redirect to a
pinned file rather than a second canonical name:

- `https://rulespec.org/context/v1.jsonld` → the archived v0.1 context (frozen)
- `https://rulespec.org/context/v2.jsonld` → redirects to
  `rkaf-context.jsonld`

Until hosting exists, fixtures reference the file directly by relative path
(`../context/rkaf-context.jsonld` from `fixtures/`,
`../../../context/rkaf-context.jsonld` from a reference corpus). The canonical
file is the single source — no duplicate copy lives under `fixtures/`.

## Extension URIs

Several Rulespec properties accept either a closed enum value OR a declared
extension URI (HTTP/HTTPS):

- `rkaf:evaluationAnchor` — closed enum or declared extension URI
- `rkaf:scope` (on Attestation) — closed enum or declared extension URI
- `rkaf:decision` (on Attestation) — closed enum or declared extension URI
- `rkaf:adoptionScope` (on LocalAdoption) — string or declared extension URI

Extension URIs must be HTTP(S) IRIs and SHOULD be declared in a
`rkaf:EvaluationAnchorExtensionRegistry` (Core §4.7) so consumers can discover
and validate them. No active extension URI ships in the current fixtures. The
shape files validate the either/or pattern with `sh:or` over the closed enum
and an IRI-with-pattern alternative.

## Composition patterns

`COMPOSE-PATTERNS.md` in this directory answers the adjacent question: which
existing primitives to compose for six common AI-governance needs that look
like they want new vocabulary, and the bright-line test for when an extension
profile is warranted instead.
