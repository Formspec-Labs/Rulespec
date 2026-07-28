# Rulespec SHACL Shapes

This directory holds the **hand-authored** half of the SHACL suite. The other
half is compiled from the CUE source of truth into `compiled/shacl/` by
`tools/constraints_compile.py`, and the validation gate loads both together:
`tools/conformance_lib.py::shacl_shape_paths()` returns `shapes/*.ttl` followed
by every `compiled/shacl/**/*.ttl`.

## Why two halves

The compiled shapes carry every constraint that is a property of ONE node — a
required property, a closed value set, a datatype, a pattern, a cardinality, a
conditional requirement inside one node. Those are generated, never written by
hand, and hand-editing one is a codegen-drift failure
(`tools/codegen_drift_audit.py`).

The files here carry what Layer 2 cannot emit:

- **Cross-node agreement** — a rule about the relationship between two nodes
  (a fragment's declared `selectorKind` versus the `@type` of the selector it
  actually carries; an assignment's evidence versus the artifact its subject
  belongs to). CUE constrains one struct; these rules span two.
- **Required ABSENCE** — a property that MUST NOT appear on a class
  (`rkaf:assertionPolarity` on a `RelationChangeEvent` or a `ClosureClaim`).
  CUE closes a struct, but the compiled carriers are open by construction, so
  absence has to be asserted in SHACL.
- **Transitive reachability** — `rkaf:ClosureClaimNotFindingEvidenceShape`
  walks proof-citation chains of unbounded depth via SPARQL. A one-hop form of
  the same rule was walked around by interposing one extra proof record
  (`spec/rkaf-analysis.md` §6.4).
- **Class hierarchy** — `rdfs:subClassOf` declarations the projector does not
  emit (`rkaf:Authority rdfs:subClassOf rkaf:Warrant`).

SHACL is conjunctive: loading both halves can only ever ADD constraints. A
compiled profile overlay therefore never relaxes a kernel shape.

## Files

`rkaf-shapes-core.ttl` is the umbrella: it `owl:imports` the other modules and
adds the core cross-node rules. Every file is loaded by the gate regardless, so
the imports document structure rather than drive loading.

| File | Shapes | What it carries |
|---|---|---|
| `rkaf-shapes-core.ttl` | `AssertionAILineageShape`, `AssertionEvidenceShape`, `SourceFragmentSelectorKindAgreementShape`, migration-rejection shapes | Umbrella imports, `rkaf:Authority rdfs:subClassOf rkaf:Warrant`, the `aiSuggested` lineage and provisional-use requirements, universal inverse EvidenceBinding rule, carrier-local fragment agreement, and rejection of retired assertion/concept shadow fields |
| `rkaf-shapes-warrant.ttl` | `WarrantShape`, `EvidenceBindingShape`, `SourceFragmentShape` | Warrant family/kind structure; fragment-backed EvidenceBindings require separate evidence-role and evidentiary-function values; fragment anchoring (Core §§4.2–4.4) |
| `rkaf-shapes-confidence.ttl` | `ConfidenceRecordShape` | Measured-confidence structure; a bare score is not a confidence record (Core §4.5) |
| `rkaf-shapes-accessscope.ttl` | `AccessScopeShape` | Access-scope structure and regulatory-class carriage |
| `rkaf-shapes-conceptregistry.ttl` | `ConceptMappingShape`, `ConceptWorkspaceShape`, release-membership and migration-rejection shapes | The five concrete SKOS mapping predicates, exact release pins, complete-membership checks, workspace-scoped concepts, and rejection of retired concept/mapping fields |
| `rkaf-shapes-studio-promotions.ttl` | `AILineageShape`, `MappingStateShape`, `RetentionPolicyShape`, `WorkspaceShape` | The Studio-derived promotions of `spec/rkaf-vocabulary.md` |
| `rkaf-shapes-analysis.ttl` | `RelationChangeEventNoPolarityShape`, `RelationFindingContextOutcomeAgreementShape`, `ResolverProofComparisonBindingShape`, `ClosureClaimNoPolarityShape`, `ClosureClaimNotFindingEvidenceShape` | The document-analysis module's cross-node and required-absence rules (`spec/rkaf-analysis.md` §§4–6), including the transitive closure-claim citation ban |
| `rkaf-shapes-pattern-c.ttl` | `AssertionNonAITouchedNoLineageShape`, `WarrantFamilyKindAgreementShape`, `BridgeValidationResultRejectedRemediationShape`, `PointInTimeExceptionRetainsShape`, `CommentPeriodAnchorShape`, `ProceedingIdentifierBoundaryShape`, `ProceedingStageDomainShape`, `ProceedingStageEventTargetShape`, `ProceedingExternalLegalEventTargetShape`, `ProceedingLatestStageAgreementShape` | Every conditional expressed in the Pattern C idiom, kernel and US-rulemaking profile alike |

## SHACL profile

- Profile: **Rulespec-SHACL-AF**
- All conditional shapes use **Pattern C** (`sh:or` with `sh:not`). pySHACL
  0.31.0 does not correctly evaluate `sh:if` / `sh:then`: eight v0.1 shapes
  parsed and reported PASS without evaluating their constraints at all. See
  `reports/batch4-validation-report.md` for the discovery trail. The compiled
  output is lint-checked for the same thing —
  `grep -rE 'sh:if|sh:then' compiled/shacl/` MUST find nothing.
- `sh:qualifiedValueShape` / `sh:qualifiedMinCount` and the SPARQL constraints
  in `rkaf-shapes-analysis.ttl` require SHACL Advanced Features; everything
  else is SHACL Core.
- Validation requires `pyshacl >= 0.31.0` with `advanced=True` and
  `inference="rdfs"`.

## Pattern C idiom

```turtle
ShapeX
  sh:targetClass T ;
  sh:or (
    [ sh:not [ <precondition> ] ]
    <requirement-branches-flattened>
  ) ;
  sh:message "..." .
```

For multi-requirement conditionals the requirement branch uses `sh:and`:

```turtle
sh:or (
  [ sh:not [ <precondition> ] ]
  [ sh:and (
      [ <requirement-A> ]
      [ <requirement-B> ]
  ) ]
) .
```

See `CONTRIBUTING.md` for the full rationale.

## Running the suite

```bash
python3 tools/ci_validate.py          # positive fixtures + reference corpora
python3 tools/validate_negatives.py   # every negative fixture must FAIL
python3 tools/constraints_parity.py   # JSON Schema and SHACL must agree
```

## The v0.1 shape set

The four v0.1.1 files — `rkaf-shapes-core-v0.1.ttl`,
`rkaf-shapes-conceptregistry-v0.1.ttl`, `rkaf-shapes-lifecycle-v0.1.ttl`, and
`rkaf-shapes-justification-v0.1.ttl` — were wholesale-superseded and now live
at `archive/v0.1/shapes/`. No active gate loads them. Their per-shape fixture
coverage matrix, including four accepted coverage gaps, is preserved in
`archive/v0.1/v0.1.1-release-manifest.md`.
