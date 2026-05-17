# Model Cards Reference Corpus

Structured AI model governance metadata expressed as Rulespec `@graph` bundles.

## Corpus structure

Each model card is a single JSON-LD document composing multiple `@graph` nodes:

| Node type | Role |
|-----------|------|
| `rkaf:AILineage` | Model identity, version, prompt template, temperature, human approval |
| `rkaf:Assertion` | Links lineage → applicable scope → warrant → safety label → evaluation |
| `rkaf:ApplicabilityScope` | Declares jurisdiction + subject scope for intended use |
| `rkaf:EffectivePeriod` | Temporal validity window |
| `rkaf:Warrant` | Grounds evaluation in scientific/legal/methodological warrant family |
| `rkaf:Justification` | Documents evaluation methodology with evidence pointers |
| `rkaf:ConfidenceRecord` | Quantitative evaluation results (score, calibration, benchmark) |
| `rkaf:Attestation` | Human oversight decision (approval, conditions, rejection) |

## Seed records

Records live in `fixtures/`. The corpus prescribes which fixtures form the canonical model-card set:

| File | Scenario | Governance state |
|------|----------|-----------------|
| `../../../fixtures/modelcard-minimal-positive.jsonld` | GPT-x model card for SNAP eligibility classification | Approved with conditions (L3 clean) |
| `../../../fixtures/modelcard-governance-rejection-negative.jsonld` | AI-promoted assertion without lineage | Rejected (§5.3): untraceable AI origin |

## Validation

Every positive record in this corpus validates cleanly through the L3 SHACL shape suite:
```bash
python3 tools/ci_validate.py
```

Negative records (governance rejection) fail exactly the expected shape:
```bash
python3 tools/validate_negatives.py
```
