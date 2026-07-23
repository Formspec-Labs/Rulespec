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
| [us-rulemaking](us-rulemaking/v0.2/) | US federal notice-and-comment rulemaking | `rkaf:us-rin`, `rkaf:us-regsgov`, `rkaf:us-frdoc`, `rkaf:us-cfr`, `rkaf:us-usc`, `rkaf:us-pl`, `rkaf:us-eo` | Reference JSON Schema and SHACL gates |

To validate a corpus locally:
```bash
python3 tools/ci_validate.py
python3 tools/validate_negatives.py
make test-reference-corpora
```
