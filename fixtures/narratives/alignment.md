# Fixture Narrative Alignment Notes

Reference document for the editorial pass that brings the `/docs/fixtures/*.md` narratives into alignment with the canonical `.jsonld` files after the 14 v0.1-rc1 patches.

The `.jsonld` files are authoritative. Narratives should be updated to match.

## Why this document exists

During v0.1-rc1 validation, 14 missing fields were patched into the JSON-LD fixtures. The Markdown narratives that introduced those fixtures were not updated in lockstep. This file enumerates each delta so the narrative editorial pass is mechanical, not interpretive.

After the editorial pass, this document can be archived.

## Mapping Fixture v0.1 — 2 narrative deltas

**Step 19 (Successor mappings).** Both `caa-42-mapping-002a` and `caa-42-mapping-002b` need a `rkaf:hasEvidence` field added in their JSON-LD blocks.

For `mapping-002a` (W2Filers successor):
```json
"rkaf:hasEvidence": [
  {
    "@type": "rkaf:EvidenceBinding",
    "rkaf:evidenceRole": "rkaf:mappingRationale",
    "rkaf:rationaleText": "Successor mapping created during revalidation after HouseholdIncomeEvidence split. CAA-42 determined the W2Filers successor concept remains applicable within CSBG benefit category B intake for applicants who file W-2 forms.",
    "rkaf:supportingEvent": "https://registry.example.gov/packets/lifecycle-001"
  }
]
```

For `mapping-002b` (NonW2Filers successor): same structure, with "NonW2Filers" substituted in the rationale text.

Narrative section to update: the prose preceding Step 19. Add one sentence noting that successor mappings carry mapping-rationale evidence linking back to the triggering lifecycle packet.

## Statutory Authority Fixture v0.1 — 2 narrative deltas

**Step 10 (state regulation derives from federal).** The `state-derives-from-federal` assertion needs three fields:

```json
"rkaf:assertionOrigin": "rkaf:importedFromSource",
"rkaf:hasApplicability": {
  "@type": "rkaf:ApplicabilityContext",
  "rkaf:jurisdiction": ["example-us-state"],
  "rkaf:programArea": "csbg",
  "rkaf:effectivePeriodStart": "2022-10-01T00:00:00-05:00"
},
"rkaf:hasEvidence": [
  {
    "@type": "rkaf:EvidenceBinding",
    "rkaf:evidenceRole": "rkaf:authorityCitation",
    "rkaf:supportingQuote": "Authority: 45 CFR Part 96 Subpart I. State regulation adopts and implements federal CSBG intake requirements including identity verification under 45 CFR § 96.30."
  }
]
```

Narrative section to update: Step 10. The original narrative noted state adoption as "included but not load-bearing." That framing is no longer accurate — validation confirmed the assertion needs the same A3 completeness as any other authority chain hop. Update narrative to note that even non-primary chain branches must be structurally complete.

**Step 16 (Formspec BridgeValidationResult).** The abbreviated BridgeValidationResult block needs:

```json
"rkaf:bridgeContractVersion": "rkaf-bridge/1.0"
```

Narrative section to update: the "(Abbreviated for length.)" parenthetical in Step 16. Either remove the abbreviation entirely (the result is now in the canonical .jsonld) or keep the parenthetical but note that the bridgeContractVersion field is mandatory and present in the canonical fixture.

## Registry Failure and Conflict Fixture v0.1 — 9 narrative deltas

**Eight BridgeValidationResults missing `bridgeContractVersion`.** Affected: case-2, case-3, case-4, case-5, case-6, case-7, case-8, case-9.

Each needs:
```json
"rkaf:bridgeContractVersion": "rkaf-bridge/1.0"
```

Narrative section to update: There's no single section to fix. Update each case's introductory prose to acknowledge that the BridgeValidationResult carries `bridgeContractVersion` — or fold it into a general note at the top of the fixture that all BridgeValidationResults in v0.1 carry this field. The latter is cleaner.

**Step 8 (canonical-mapping-001 attestation).** Needs:
```json
"rkaf:visibility": "rkaf:publicVisible"
```

Narrative section to update: Step 8's prose. The canonical-mapping attestation is by a registry's ConceptMintingAuthority with public scope; the narrative should make explicit that public visibility is the natural pairing for canonical attestations, not an oversight.

## General narrative guidance

Two observations from the patch pass that are worth folding into the v0.1 narrative style:

1. **Don't abbreviate fixtures.** The phrase "(Abbreviated for length.)" appeared in two places in v0.1 and produced four validation violations. Conformance fixtures should be boringly complete; length is the price of being a test artifact. If a fixture grows too long for inline reading, split it across steps but don't drop required fields.

2. **`bridgeContractVersion` is mandatory on every BridgeValidationResult.** The shape correctly enforces this. Any future fixture that exercises the bridge contract must include this field on every result, no exceptions. Worth a one-line callout at the top of any fixture that emits validation results.

## Status when complete

After this editorial pass:

- All four `/docs/fixtures/*.md` narratives describe the same content as the canonical `/fixtures/*.jsonld` files
- Step-by-step prose matches step-by-step JSON blocks line for line
- No "abbreviated" or "(omitted for brevity)" notes remain in the conformance fixtures
- This alignment-notes document can be deleted or archived

The alignment is mechanical: copy each JSON snippet above into the corresponding `.md` step's code block, update the surrounding prose to match, run `python3 ci_validate.py` to confirm nothing accidentally broke, commit.
