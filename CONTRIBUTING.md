# Contributing to Rulespec

Rulespec development is structured around a disciplined iteration model that surfaced across four shape batches between v0.1-rc1 and v0.1.1. Contributors should follow the same model.

## The shape-batch method

Every change to Rulespec shapes, fixtures, or specification proceeds through the same arc:

1. **Anchor on spec sections.** Each new shape or constraint cites a specific section of the spec it enforces. No constraint exists without a textual basis.

2. **Validate against all fixtures.** Run the relevant discovery-based gate (`python3 tools/ci_validate.py`, `python3 tools/validate_negatives.py`, `python3 tools/conformance_report.py`, or `python3 tools/vocab_audit.py`). Capture the initial violation count.

3. **Classify violations.** Every violation falls into exactly one category:
   - **Shape over-strictness** — the shape requires more than the spec text. Patch the shape.
   - **Shape under-coverage** — the shape doesn't enforce what the spec text says. Patch the shape.
   - **Fixture defect** — the fixture doesn't represent the spec correctly. Patch the fixture.
   - **Spec ambiguity** — the spec text doesn't decide. Open an issue; do not silently patch.
   - **Intended failure** — the fixture is supposed to demonstrate a violation. Put it in the negative corpus and verify it fails through `tools/validate_negatives.py`; do not hide it with an allow-list.

4. **Patch evidence-driven.** Each patch addresses a specific classified violation. No speculative spec changes. No new vocabulary unless validation forces it.

5. **Converge to clean.** Iterate until the relevant gate reports 0 unexpected violations or 0 divergences. Document the iteration arc in a batch report under `reports/` when the change affects release posture.

This method produced four clean iteration arcs (251→14→0, 7→0, 2→0, 0→6→0) with zero spec drift across v0.1-rc1 through v0.1.1.

## Three boundaries that hold

### 1. Universal ontology, not consumer-coupled

Rulespec is not a form spec, workflow spec, search engine spec, or policy studio spec. Rulespec is a universal evidence-backed assertion, authority, concept, lifecycle, and consumer-justification data ontology.

The conceptual center of the justification overlay is the **predicate-targeted generic shapes** (`ConsumerArtifactJustificationShape`, `DataCollectionArtifactJustificationShape`, `ProcessArtifactJustificationShape`). The Formspec and WOS shapes are documented example specializations and are not load-bearing. New consumer-specific shapes (e.g., for a CMS, search index, AI assistant) follow the same pattern: predicate-targeted generic + optional named specialization.

### 2. Structural validation, not behavioral

SHACL validates the structure of Rulespec data: required fields, types, enum membership, conditional requirements. It does NOT validate:

- Whether `CascadeClosureV1` computed the correct transitive closure
- Whether the `usageEligibility` reducer produced the correct lattice ceiling
- Whether the authority chain traversal materialized the correct chain
- Whether registry cache TTL behavior is correct
- Whether `safeAutomaticMigration` `replaceInPlace` is correct

Behavioral correctness is the runtime conformance test layer (planned for v0.2). Do not add SHACL constraints that attempt to verify behavior.

### 3. Rulespec overlay only, not consumer internals

When validating consumer artifacts (form fields, workflow steps, search index entries, etc.), Rulespec shapes ONLY validate Rulespec overlay properties (`rkaf:justifiedByAssertion`, `rkaf:bridgeContractVersion`, `rkaf:usageEligibility`, `rkaf:collectsEvidenceType`, `rkaf:requiresEvidenceType`, etc.). Rulespec does NOT validate consumer-native schemas (Formspec field syntax, WOS workflow runtime, etc.).

## Accepted coverage gaps

Per the editorial discipline (no fixture force-fits to satisfy coverage vanity), four shapes have no fixture target. They remain structurally correct and will activate when future fixtures instantiate the relevant entity type:

- `ConceptMintingAuthorityShape`
- `SupersessionPacketShape`
- `MaterialRevisionPacketShape`
- `JustificationChainHopShape`

If you add a fixture that exercises one of these shapes, update the coverage matrix in `reports/v0.1.1-release-manifest.md`.

## SHACL idiom: use Pattern C, avoid sh:if/sh:then

pySHACL 0.31.0 does not reliably evaluate `sh:if`/`sh:then` patterns. Conditional shape requirements should use Pattern C:

```turtle
# WRONG (will not fire reliably):
sh:if   [ <precondition> ] ;
sh:then [ <requirement> ] .

# RIGHT:
sh:or (
  [ sh:not [ <precondition> ] ]
  <requirement-branches-flattened>
) .
```

For multi-requirement conditionals (e.g., A3 assertions requiring authorityKind + hasApplicability + qualified evidence), use `sh:and` inside the requirement branch:

```turtle
sh:or (
  [ sh:not [ <precondition> ] ]
  [ sh:and (
      [ <requirement-A> ]
      [ <requirement-B> ]
      [ <requirement-C> ]
  ) ]
) .
```

All eight conditional shapes in v0.1.1 follow this pattern. New conditional shapes should too.

## Verification: synthetic defect injection

After adding or modifying a shape, verify it fires by injecting a synthetic defect:

```python
import json, copy, rdflib
from pyshacl import validate
from pathlib import Path

shapes = rdflib.Graph()
for f in ["shapes/rkaf-shapes-core-v0.1.ttl", ...]:
    shapes.parse(f, format="turtle")

data = copy.deepcopy(json.loads(Path("fixtures/<fixture>.jsonld").read_text()))
# Mutate `data` to introduce a defect the shape should catch
g = rdflib.Graph()
g.parse(data=json.dumps(data), format="json-ld")

c, r, _ = validate(data_graph=g, shacl_graph=shapes,
                   inference="rdfs", advanced=True, meta_shacl=False)
print("CAUGHT" if not c else "MISSED")
```

A shape that doesn't fire on its target defect class is broken, even if it parses correctly and reports PASS on the fixtures.

## Pull request expectations

A shape, fixture, or context PR should include:

- Rationale citing the relevant spec section
- Initial validation output (count of violations before the change)
- Final validation output from the relevant discovery-based gates after the change
- Synthetic defect tests for any new conditional logic (CAUGHT confirmation)
- Coverage matrix update if a previously-gap shape gains a fixture target
- Hash table update in `reports/v0.1.1-release-manifest.md` if any shipped file's SHA-256 changes

Spec text changes require a separate discussion before any shape or fixture changes. The shape-batch method assumes spec text is stable; if a batch reveals a spec ambiguity, surface it as an issue rather than silently patching.

## Versioning

- Spec text changes → bump second digit (`v0.1` → `v0.2`)
- Shape implementation fixes that don't change semantics → bump patch digit (`v0.1` → `v0.1.1`)
- New shapes that extend coverage without changing existing semantics → bump patch digit
- Fixture defect patches → bump patch digit (because they materially change the conformance signature)

## Code of conduct

Contributors are expected to engage constructively. Disagreement on technical decisions is welcome; ad hominem is not. The shape-batch method is itself a code-of-conduct mechanism: it forces disagreement to be expressed as classified violations against the existing artifacts, which keeps debate concrete.
