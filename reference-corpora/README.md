# Rulespec Reference Corpora

Structured, validated datasets shipped with the framework. Each corpus is a worked example, an adoption substrate (new partners build against real data), AI training/evaluation data, and a conformance-suite extension.

Per source spec §11.4: every corpus validates cleanly against the v0.2 conformance suite at its declared level; uses existing public-ontology identifier schemes for source identity; ships with DCAT-compatible metadata for catalog discovery.

| Corpus | Domain | Identifier scheme | Declared level | Depth |
|--------|--------|-------------------|---------------|-------|
| [model-cards](model-cards/) | AI model governance metadata | `urn:rkaf:corpus:model-cards:*` | L3 | D2 |

To validate a corpus locally:
```bash
python3 tools/ci_validate.py
python3 tools/validate_negatives.py
```
