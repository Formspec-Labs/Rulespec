# Rulespec — Policy Knowledge Assertion Framework

**Version:** v0.1.1 — Structural validation fix and consumer-justification shapes
**Bridge contract:** `rkaf-bridge/1.0`
**Profile:** Rulespec-SHACL-AF
**Conformance:** 1,206 triples / 0 violations across 4 fixtures and 4 shape files

## What Rulespec is

Rulespec is a machine-validatable assertion framework for evidence-backed policy knowledge, designed to be consumed by downstream systems such as search engines, wikis, form builders, workflow engines, case systems, document generators, AI assistants, and publication tools.

Rulespec is **not** a form spec. Rulespec is **not** a workflow spec. Rulespec is **not** a policy studio spec. Rulespec is **not** a search engine spec.

Rulespec is a universal evidence-backed assertion, authority, concept, lifecycle, and consumer-justification data ontology.

## Strategic positioning

Rulespec is upstream of consumer systems.

**Rulespec owns:** evidence-backed assertions, source authority, attestations, local adoption, concept resolution, lifecycle packets, usage eligibility, consumer validation results, justification metadata.

**Consumer systems own:** their own runtime behavior, rendering, storage, workflows, forms, search UX, or publication logic.

Consumers may attach a Rulespec overlay to their native artifacts. Rulespec validates only that overlay, not the consumer's native schema.

The fixtures in `fixtures/` include form-like and workflow-like artifacts (typed as `formspec:Field` and `wos:WorkflowStep`) to stress-test the consumer overlay pattern. **They are examples, not dependencies.** A search engine indexing policy fragments, a wiki linking to authority chains, a CMS attaching adoption metadata to a published rule, or an AI assistant providing citation-backed answers would all wear the same overlay shape.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the validation gate (default mode: batch4, the full v0.1.1 surface)
python3 tools/ci_validate.py

# Expected output:
#   Mode:       batch4 (Core + ConceptRegistry + Lifecycle + Justification)
#   Triples:    1,206
#   Violations: 0
#   Result:     PASS
```

To validate against narrower conformance subsets:

```bash
python3 tools/ci_validate.py --mode core      # Core only (v0.1-rc1 baseline)
python3 tools/ci_validate.py --mode batch2    # + ConceptRegistry
python3 tools/ci_validate.py --mode batch3    # + Lifecycle
python3 tools/ci_validate.py --mode batch4    # + Justification (default)
```

## Repository layout

```
.
├── README.md                          ← you are here
├── LICENSE                            ← dual-license pointer
├── LICENSE-SPEC                       ← specification surface license (CC BY 4.0 placeholder)
├── LICENSE-CODE                       ← tooling license (Apache 2.0 placeholder)
├── CHANGELOG.md                       ← v0.1-rc1 → v0.1.1 history
├── CONTRIBUTING.md                    ← shape-batch method and editorial discipline
├── VERSION                            ← 0.1.1
├── requirements.txt                   ← Python deps for tools/
├── .gitignore
│
├── spec/                              ← Rulespec specification text (unchanged from v0.1-rc1)
│   ├── README.md
│   ├── rkaf-core-v0.1.md
│   └── rkaf-concept-registry-v0.1.2.md
│
├── context/                           ← Published JSON-LD contexts
│   ├── README.md
│   ├── rkaf-context-v0.1.jsonld       ← Frozen historical
│   └── rkaf-context-v0.2.jsonld       ← Current; additive superset of v0.1
│
├── shapes/                            ← SHACL shape files (Pattern C, pySHACL-evaluable)
│   ├── README.md
│   ├── rkaf-shapes-core-v0.1.ttl
│   ├── rkaf-shapes-conceptregistry-v0.1.ttl
│   ├── rkaf-shapes-lifecycle-v0.1.ttl
│   └── rkaf-shapes-justification-v0.1.ttl
│
├── fixtures/                          ← Conformance fixtures (4)
│   ├── README.md
│   ├── context.jsonld                 ← Inline-context source-of-truth (== context/rkaf-context-v0.2.jsonld)
│   ├── local-operational-v0.2.jsonld
│   ├── mapping-v0.1.jsonld
│   ├── statutory-authority-v0.1.jsonld
│   ├── registry-failure-conflict-v0.1.jsonld
│   └── narratives/                    ← Prose narratives for each fixture
│
├── tools/                             ← Validation tooling
│   ├── README.md
│   └── ci_validate.py                 ← Multi-mode CI gate
│
└── reports/                           ← Per-batch validation reports (provenance)
    ├── README.md
    ├── v0.1-rc1-manifest.md
    ├── batch1-shapes.md
    ├── batch1.1-patches.md
    ├── batch2-validation-report.md
    ├── batch3-validation-report.md
    ├── batch4-validation-report.md
    └── v0.1.1-release-manifest.md
```

Each directory has its own README explaining its contents in detail. Start with whichever directory matches your interest:

- **Implementing a consumer?** Start with `spec/README.md` and `fixtures/narratives/`
- **Validating data against Rulespec?** Start with `tools/README.md` and `shapes/README.md`
- **Contributing?** Start with `CONTRIBUTING.md`
- **Understanding decision history?** Start with `reports/README.md`

## v0.1.1 release summary

v0.1.1 preserves Rulespec v0.1 semantics but rewrites conditional SHACL constraints into pySHACL-evaluated Pattern C form, patches six fixture defects exposed by the corrected constraints, and adds generated-artifact / consumer-justification overlay shapes. The combined package validates cleanly across **1,206 triples with 0 violations**.

### What changed from v0.1-rc1

| Category | Change |
|---|---|
| Spec semantics | No change |
| JSON-LD context | Additive only (`rkaf:definedInScope` typing added) |
| Shape files | Pattern C rewrite for 8 conditional shapes; 3 new generic consumer-overlay shapes |
| Fixtures | Six latent defect patches (+20 triples) |
| CI gate | Multi-mode (`core` / `batch2` / `batch3` / `batch4`) |
| Public framing | README rewritten — Rulespec positioned as universal ontology |

See `CHANGELOG.md` for the full change list and `reports/v0.1.1-release-manifest.md` for SHA-256 hashes.

### The pySHACL discovery

During Batch 4 validation, synthetic defect injection testing revealed that pySHACL 0.31.0 does not reliably evaluate the `sh:if` / `sh:then` conditional shape pattern. **Eight conditional shapes across Batches 1.1, 2, 3, and 4 were parsing correctly and reporting PASS, but were not actually evaluating their constraints against fixture data.**

All eight have been rewritten using Pattern C (`sh:or` with `sh:not`), which pySHACL evaluates reliably. The rewrites surfaced six latent fixture defects that had been hidden for the entire v0.1-rc1 era; those defects are now patched.

This is not a semantic change. The intended constraints of every conditional shape were always what their TTL prose described. Pattern C is a faithful expression of that intent in a SHACL idiom that pySHACL evaluates correctly. See `reports/batch4-validation-report.md` for the full discovery and verification trail.

## Validation invariants enforced

Beyond the consumer-overlay shapes, the full four-shape-file package structurally enforces (with all conditional shapes actually firing):

### Assertion semantics
- Every `rkaf:RelationshipAssertion` declares trust zone, safety label, evidence or `noEvidenceReason`, and applicability
- R2 / A3 / P4 assertions MUST have at least one `rkaf:hasEvidence` binding (noEvidenceReason is insufficient at these safety levels)
- A3 authority-critical assertions MUST declare `authorityKind` + `hasApplicability` + at least one evidence binding with an authority or lifecycle evidence role

### Authority chain
- `AuthorityChainHop.predicate` restricted to `hasAuthority` and `derivesAuthorityFrom` only (`implements` forbidden)
- `JustificationChainHop.predicate` may include `hasAuthority`, `derivesAuthorityFrom`, AND `implements`

### Local adoption
- `LocalAdoption.adoptionAuthorityKind` restricted to {`organizational`, `localOperational`, `contractual`, `publication`}; cannot claim legal/statutory/regulatory/delegated authority

### Bridge contract
- `BridgeValidationResult` with `result=rejected` MUST include `suggestedRemediation` OR enumerated `noRemediationReason`
- `BridgeValidationResult` with `result=acceptedWithWarnings` OR `result=rejected` MUST include at least one structured indicator

### Concept registry
- `LocalConcept` MUST declare `definedInScope` as IRI
- `skos:closeMatch` mapping at `localOperationalUse` or higher MUST declare `MappingApplicabilityContext`
- `ConceptResolutionResult` MUST include `usageCeiling`
- `BridgeConsumerRegistration` MUST declare `supportedEvaluationAnchors`
- Operational/publication mapping conflicts MUST name the affected artifact
- `ConceptLifecyclePacket` MUST carry `successorConcepts` for split/merge/replacedBy events

### Lifecycle packets
- All lifecycle packets MUST declare `emittedBy`, `effectiveDate`, `bridgeContractVersion`, `cascadeAlgorithm`
- `RevalidationEvent` MUST target an assertion or work product
- `RevalidationClosureEvent` MUST close a specific `RevalidationEvent`
- `revalidatedWithSuccessor` MUST name successor assertion(s) or work product
- `PointInTimeException` MUST name an `EvaluationAnchor` and retained assertion or work product

### Consumer artifact overlay (new in v0.1.1)
- Every `rkaf:GeneratedWorkProduct` MUST declare `justifiedByAssertion` + `bridgeContractVersion` + eligibility (current or proposed)
- ANY consumer artifact carrying `rkaf:justifiedByAssertion` MUST declare `bridgeContractVersion`
- ANY consumer artifact declaring `rkaf:collectsEvidenceType` MUST declare `justifiedByAssertion` + `bridgeContractVersion`
- ANY consumer artifact declaring `rkaf:requiresEvidenceType` MUST declare `justifiedByAssertion` + `bridgeContractVersion`

## What v0.1.1 does NOT do

Per the explicit boundary maintained across all four batches:

- Does not validate consumer-system internals (Formspec schema, WOS workflow runtime, search ranking, CMS storage, etc.)
- Does not validate cascade closure correctness (runtime test, not structural shape)
- Does not validate reducer output correctness (runtime test)
- Does not validate concept cache TTL or registry liveness (runtime test)

These belong in the next layer: **runtime conformance tests** (see "What's next" below).

## What's next: runtime conformance tests

With v0.1.1 the structural validation surface is functionally complete for v0.1.x. The next layer of work is runtime conformance tests — fixture-specific expected-output JSON files that consumer implementations diff against their actual output. SHACL validates structure; runtime tests validate behavior.

Initial test suite (planned for v0.2):

| Test | Validates |
|---|---|
| CascadeClosureV1 affected-set output | Cascade algorithm correctness on rescission/amendment |
| usageEligibility reducer output | Lattice reduction correctness |
| Authority chain traversal output | Chain materialization correctness |
| Concept cache TTL behavior | Registry freshness handling |
| Registry-unavailable behavior | Degraded-mode reasoning |
| PointInTimeException behavior | Anchor support and exception acceptance |
| LocalAdoption orphaning | Adoption cascade on rescission |
| safeAutomaticMigration replaceInPlace | Auto-migration semantics |

Format:

```yaml
input:
  fixture: statutory-authority-v0.1
  trigger: rescission-001
expected:
  affectedAssertions:
    - caa-42-identity-req-001
  affectedAdoptions:
    - caa-42-identity-req-001-adoption
  affectedWorkProducts:
    - caa-42-intake/verify-identity/v1
    - caa-42-intake/identity-document/v1
  authorityChainStatus: brokenForNewCases
  pointInTimeExceptionAccepted: true
```

Consumer implementations import the fixture, run their own cascade computation, and diff against the expected output. Differences are conformance failures.

This work begins in the next iteration cycle after external review of v0.1.1.

## Citing

If you use Rulespec in your system, please cite:

```
Rulespec — Policy Knowledge Assertion Framework, v0.1.1
[publication URL]
```

A formal citation will be provided once the spec is hosted at its canonical URL.

## License

See `LICENSE` (top-level pointer to dual-license arrangement).

- **Specification surface** (`spec/`, `shapes/`, `context/`, `fixtures/`, `reports/`, documentation): see `LICENSE-SPEC` (CC BY 4.0 placeholder)
- **Tooling** (`tools/`): see `LICENSE-CODE` (Apache 2.0 placeholder)

Both license files are placeholders pending final selection by the publishing organization.
