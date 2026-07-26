# Rulespec Reference Corpora

Structured, validated datasets shipped with the framework. Each corpus is a worked example, an adoption substrate (new partners build against real data), AI training/evaluation data, and a conformance-suite extension.

Every corpus validates cleanly against the applicable v0.2 reference gates,
uses public-ontology or source-owned identifiers, and ships with
DCAT-compatible catalog metadata. A corpus is validation input, not a
Rulespec consumer, so its manifest records validation evidence rather than a
consumer conformance level or adoption depth.

| Corpus | Domain | Identifier scheme | Validation |
|--------|--------|-------------------|------------|
| [model-cards](model-cards/) | AI model governance metadata | `urn:rkaf:corpus:model-cards:*` | Reference JSON-LD and SHACL gates |
| [us-rulemaking](us-rulemaking/v0.2/) | US federal notice-and-comment rulemaking; `us-rin` identifies a durable agenda item, not a Proceeding | `rkaf:us-rin`, `rkaf:us-regsgov`, `rkaf:us-frdoc`, `rkaf:us-cfr`, `rkaf:us-usc`, `rkaf:us-pl`, `rkaf:us-eo` | Reference JSON Schema and SHACL gates |

To validate a corpus locally:
```bash
python3 tools/ci_validate.py
python3 tools/validate_negatives.py
make test-reference-corpora
```

## What a corpus is NOT: contract coverage

A reference corpus is **source-evidenced real-world data**, not a coverage
matrix. Every resource in one traces to a cited, dated public source (see each
corpus README's `## Sources`), and its manifest pins the exact content-addressed
contract digest the validation run used. That is the whole point: a new partner
builds against data that actually exists.

It follows that **a corpus does NOT gain a row when a contract is added or
reshaped**. The v0.2 contract reshape added `rkaf:ValueAssertion`,
`rkaf:SourceClaimant`, `rkaf:ExtractionActivity`, `rkaf:ConceptScheme`,
`rkaf:ConceptAssignment`, and the five document-analysis contracts
(`rkaf:RelationChangeEvent`, `rkaf:RelationComparisonContext`,
`rkaf:ResolverProofRecord`, `rkaf:RelationFinding`, and the disabled
`rkaf:ClosureClaim`). None of them got a corpus row, and none should have:

- The us-rulemaking corpus records what the EPA oil-and-gas docket **says**.
  No Federal Register document states a resolver proof, a comparison context,
  or a typed-literal value assertion, so writing one in would be inventing
  data — precisely the failure mode the corpus exists to rule out. The corpus
  README already declines to model a correction document whose Proceeding
  membership the sources cannot adjudicate; the same standard applies here.
- A comparison, a proof, or a finding is a record a **consumer** produces about
  a corpus, not a fact the corpus's sources assert. It belongs to whoever runs
  the comparison, with its own provenance.

**Where contract coverage is proven instead.** Every contract class carries at
least one positive fixture under `fixtures/` (enforced by
`tools/vocab_audit.py`, which fails the build on a CUE-compiled class with no
vocabulary row and no named fixture), and every fixture is classified
identically by the JSON Schema and SHACL targets
(`tools/constraints_parity.py`). `tools/l0_l3_coverage_audit.py` and
`tools/l4_coverage_audit.py` close the level-by-level coverage question. The
corpora then run through the same gates as ordinary fixture input
(`make test-reference-corpora`), which is what makes them evidence that the
contract works on real documents rather than a second, weaker coverage claim.

A corpus SHOULD gain rows when new **source-evidenced** material arrives — a
further docket, a further model card — not when the contract grows.
