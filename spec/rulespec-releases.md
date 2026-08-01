# Rulespec release records

This specification defines two independently releasable Rulespec products:
Rulespec Core and Rulespec Extrapolator. It also defines the canonical JSON and
validation rules that let a consumer verify their artifacts without a
Rulespec, SpicyRegs, RefSpec, or SpicySearch checkout.

## 1. Shared canonical JSON

Release and durable-record identities use the same serialization:

1. Parse strict JSON. Reject duplicate object keys, `NaN`, `Infinity`, and
   `-Infinity`.
2. Encode UTF-8 JSON with keys sorted lexicographically, separators `,` and
   `:`, native Unicode (`ensure_ascii=false`), and no non-finite numbers
   (`allow_nan=false`).
3. Compute lowercase SHA-256 and prefix the hex digest with `sha256:`.

For a root release, omit only the root `release_id` and `release_digest` before
serialization. Nested fields with those names remain in the digest. Construct
the identifier as:

```text
urn:<product>:<release-kind>:<64-lowercase-hex-digest>
```

The two Rulespec forms are `urn:rulespec:core:<digest>` and
`urn:rulespec:extrapolation:<digest>`. Durable child records hash only the
identity-defining fields listed in section 4. Exact text content digests use
SHA-256 over the declared UTF-8 bytes, not over a JSON string representation.

[`tools/rulespec_release.py`](../tools/rulespec_release.py) is the portable
reference validator. The JSON Schemas under
[`release-records/schemas/`](../release-records/schemas/) provide the closed
shape gate.

## 2. `RulespecCoreRelease`

What goes in? Generated Core schemas, validators, and positive conformance
fixtures. What happens? The publisher lists each artifact with its exact
digest and stamps the root record. What comes out? One repository-independent
`RulespecCoreRelease`. How do we check it? Recompute the root identity and
verify every manifest is nonempty and every artifact digest is well formed.

The root fields are:

| Field | Meaning |
| --- | --- |
| `record_type` | Exactly `RulespecCoreRelease` |
| `release_id`, `release_digest` | Content-derived root identity |
| `release_status` | `fixture`, `candidate`, or `published` |
| `version` | Publisher version |
| `schema_artifacts[]` | Core schema manifest |
| `validator_artifacts[]` | Core validator manifest |
| `conformance_fixture_artifacts[]` | Positive conformance evidence |

Every artifact entry has exactly `name`, `media_type`, and `artifact_digest`.
The sealed M2 fixture covers the seven shared boundary types: `Artifact`,
`SourceFragment`, `ConceptAssignment`, `EvidenceBinding`,
`ExtractionActivity`, `AILineage`, and `ReferenceResourceRelease`.

Core contains no RefSpec source import or RefSpec-specific Rust export. A
consumer receives the Core artifact or a byte-identical local fixture copy and
pins `{release_id, release_digest}`.

## 3. `ExtrapolationRelease`

What goes in? One exact `RulespecCoreRelease`, `DocumentRelease`, and
`VocabularyRelease`, plus a versioned extraction profile. What happens? The
Extrapolator builds processing segments, records reversible source mappings,
creates evidence-bound candidates, captures extraction and AI lineage, runs
independent baseline validation, and records deterministic selection. What
comes out? A nonempty immutable release with separate document- and
fragment-level assignments. How do we check it? Resolve every reference only
against the three pinned releases and the root's contained records, then apply
the closed schema and fail-closed semantic gates.

The root fields are:

| Field | Meaning |
| --- | --- |
| `record_type` | Exactly `ExtrapolationRelease` |
| `release_id`, `release_digest`, `release_status`, `version` | Root identity and publication state |
| `profile` | `profile_id`, `profile_version`, and `usage_cap=searchOnly` |
| `input_releases` | Exact Core, document, and vocabulary `{release_id, release_digest}` pins |
| `validation_sample_manifest` | Unique `record_refs[]` and their canonical `manifest_digest` |
| `concept_assignments[]` | Immutable candidate propositions |
| `evidence_bindings[]` | Exact fragment-backed evidence |
| `extraction_activities[]`, `ai_lineage_records[]` | Run and model provenance |
| `processing_segments[]`, `derived_text_projections[]` | Reproducible model inputs and reversible source mapping |
| `validation_artifacts[]` | Secret-free validator request and exact response artifacts |
| `agent_validation_receipts[]`, `baseline_validation_receipts[]` | Independent attempts and deterministic reduction |
| `selection_context_digest`, `selection_receipts[]`, `selected_assignment_refs[]` | Digest of the complete pre-selection graph, per-candidate decision, and served upstream subset |
| `coverage` | Content-addressed `ExtrapolationCoverage` with candidate, selected, not-selected, deferred, and failure counts |

The input releases are copied as pinned fixture JSON for offline validation.
They remain owned by their publishers. Copying an artifact does not transfer
authority or permit Rulespec to invent a substitute identifier.

## 4. Durable contained records

Each durable record carries `record_type` and a stable `record_id`. The record
ID is the canonical digest of these identity-defining fields:

| Record | Identity-defining fields |
| --- | --- |
| `ConceptAssignment` | subject, predicate, object, polarity, assigned concept release |
| `EvidenceBinding` | assignment, evidence spans, evidence role, evidentiary function |
| `ExtractionActivity` | extraction run and attempt |
| `AILineage` | model and version, prompt and input digests, temperature, seed |
| `ProcessingSegment` | document release, input fragments, segmentation policy, derived-text digest |
| `DerivedTextProjection` | derived unit, derived-text digest, construction method |
| `AgentValidationReceipt` | complete terminal receipt content except `record_id` |
| `BaselineValidationReceipt` | complete terminal receipt content except `record_id` |
| `ExtrapolationSelectionReceipt` | complete terminal receipt content except `record_id` |

A selected `ConceptAssignment` targets either the document-version `Artifact`
or an exact `SourceFragment`. Document and fragment assignments remain
separate records. Every AI-suggested selected assignment has fragment-backed
`EvidenceBinding`, `ExtractionActivity`, `AILineage`, and
`usage_eligibility=searchOnly`. A `ProcessingSegment` is never a served target.

`DerivedTextProjection.ordered_slices[]` uses half-open Unicode code-point
bounds. The slices account for every derived character and distinguish
`source_range`, `inserted_text`, and `transformed_range`. Source ranges resolve
inside declared input fragments. Inserted text carries its exact digest.
Omissions, the join delimiter, and normalization policy remain explicit.

## 5. Validation receipts

An `AgentValidationReceipt` records one immutable attempt: exact target and
digest, protocol, sealed input manifest, validator identity and independence
group, request artifact, execution status, per-check outcomes and evidence,
and either a completed response and recommendation or a failure reason. A
failed execution has no recommendation. Failure and abstention are distinct.
The three terminal receipt kinds are fully content-addressed: changing an
input reference, status, check, rationale, recommendation, selection result,
or limitation creates a new record identifier.

A `BaselineValidationReceipt` names the exact profile, vocabulary release,
sample manifest, rubric, aggregation policy, deterministic outcomes, and at
least two agent attempts from different independence groups. Any unresolved
abstention blocks a usable result. `usable_for_search` and
`usable_with_nonblocking_limits` qualify only candidate use; they do not prove
truth, approval, adoption, or applicability.

An `ExtrapolationSelectionReceipt` records one candidate's policy inputs,
checks, result, evaluator, and effective time. `selection_result` is
`selected`, `not_selected`, or `deferred`.

`selection_context_digest` binds each receipt to the exact upstream release
pins, profile, candidates, evidence, processing and projection records,
validation artifacts, agent attempts, and baseline reductions that existed
before selection. The root repeats that digest. A changed input release,
validation record, candidate graph, or selection-policy version therefore
requires new selection receipts and new stable receipt identifiers.

The plan-level receipt includes `output_extrapolation_release_ref`. A contained
receipt omits that field because the root release digest determines the output
identifier and the receipt contributes to that digest. Root containment is the
authoritative membership statement. A detached view may add the output release
reference after publication, but that view is not part of the root digest.

`coverage` carries its own `coverage_id` and `coverage_digest`, computed by
omitting only those two fields from the coverage preimage. Root containment
associates it with the release without creating a self-reference. A search
snapshot cites that stable coverage identifier when it records extrapolation
import coverage.

## 6. Fail-closed gates and sealed M2 fixtures

Validation rejects a missing or mismatched input release, root or child digest
mismatch, unresolved reference, incomplete reference-resource membership,
invalid fragment coordinates, non-closing projection, missing evidence or
lineage, non-`searchOnly` selected assignment, selected processing-segment
target, unusable baseline, validator abstention, unselected assignment in the
served subset, coverage mismatch, or empty release.

The checked-in conformance set is:

- [`rulespec-core-release-m2.json`](../release-records/fixtures/rulespec-core-release-m2.json)
- [`m2-input-releases.json`](../release-records/fixtures/m2-input-releases.json)
- [`m2-extrapolation-release-positive.json`](../release-records/fixtures/m2-extrapolation-release-positive.json)
- [`m2-negative-controls.json`](../release-records/fixtures/m2-negative-controls.json)

The negative controls cover wrong release, digest mismatch, missing evidence,
missing AI lineage, broader usage, processing-segment target, validator
abstention, and inclusion of an excluded assignment. The fixture builder
[`tools/build_rulespec_release_fixtures.py`](../tools/build_rulespec_release_fixtures.py)
reproduces the static JSON and the test suite checks byte-equivalent data.

These artifacts have `release_status=fixture`. Passing fixture validation is
not a tag, package publication, deployment, or activation claim.
