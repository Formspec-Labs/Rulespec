# Rulespec release records

This specification defines two independently releasable Rulespec products:
Rulespec Core and Rulespec Extrapolator. It also defines the canonical JSON and
validation rules that let a consumer verify their artifacts without a
Rulespec, SpicyRegs, RefSpec, or SpicySearch checkout.

> **Execution-boundary correction (2026-08-02, supersession in place — the
> superseded sentences below are struck and annotated, never deleted).** Three
> capability claims in §3 named the Extrapolator as the executor of work this
> repository does not perform, and for one of them does not own. Other products
> read this document as a contract, so the corrections are stated here:
>
> 1. **Segment construction is not a Rulespec capability, and the duty is not
>    Rulespec's.** SpicyRegs owns source parsing, exact text, durable structural
>    passages, and model-input segmentation. The Extrapolator consumes segments a
>    publisher prepared. This repository has no segmenter: zero of its 79 Rust
>    sources name a segment, and the only code that builds a `ProcessingSegment`
>    is `fixture_only_prepared_segment`
>    ([`tools/build_rulespec_release_fixtures.py:167`](../tools/build_rulespec_release_fixtures.py)),
>    which refuses to contribute to any release whose status is not `fixture`.
> 2. **Baseline validation is verified, not executed.** The reference validator
>    checks a *submitted* `BaselineValidationReceipt` for two completed,
>    independent, unanimously supporting attempts
>    ([`tools/rulespec_release.py:1881`](../tools/rulespec_release.py)). Nothing
>    in this repository invokes a validator, a provider, or a model; there is no
>    HTTP client, provider SDK, or API credential in the tree, and the M2
>    fixture's two "validators" are hardcoded strings.
> 3. **Deterministic selection is verified, not executed.** The validator checks
>    selection-receipt consistency and the `selection_context_digest` binding
>    ([`tools/rulespec_release.py:1573`](../tools/rulespec_release.py)). No
>    selection engine exists; the fixture selects the first two candidates by
>    list index.
>
> What survives unchanged, because the code backs it: closed shape validation,
> evidence resolution against the pinned document and atlas, exact model-input
> lineage — `_validate_projection` re-derives every derived character from
> declared source ranges ([`tools/rulespec_release.py:808`](../tools/rulespec_release.py))
> — the `searchOnly` eligibility contract
> ([`:1237`, `:1681`](../tools/rulespec_release.py)), and the three required
> terminal receipt types. The Extrapolator's narrow, true shape is: prepared
> segments plus a versioned extrapolation profile go in; evidence-linked
> structured document descriptions come out, recording the exact input segment,
> source references, prompt, and model lineage.
>
> The producing processes behind approval, selection, and governance are
> **parked with no owner** — see §7. The decision record is
> [`docs/decisions.md`, 2026-08-02](../docs/decisions.md).

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

What goes in? One exact `RulespecCoreRelease`, `DocumentRelease`, static RefSpec
vocabulary atlas, and `ReferenceResourceRelease` identity proven by that atlas,
plus a versioned extraction profile and the processing segments a publisher
prepared.

~~What happens? The Extrapolator builds processing segments, records reversible
source mappings, creates evidence-bound candidates, captures extraction and AI
lineage, runs independent baseline validation, and records deterministic
selection.~~ **Superseded 2026-08-02 by the correction banner at the top of this
document. Retained for reference; do not implement.**

What happens? The Extrapolator consumes prepared segments under a versioned
extrapolation profile, invokes models, and emits evidence-linked structured
document descriptions. It records the exact input segment and its reversible
source mapping, the evidence-bound candidates, and the extraction and AI
lineage — prompt and model identity included. It does not parse sources,
tokenize, handle PDF or HTML, or build segments; those belong to SpicyRegs. It
does not execute baseline validation or run a selection engine; it carries the
receipts those processes must produce, and §7 records that no product owns them
today.

What comes out? A nonempty immutable release with separate document- and
fragment-level assignments. How do we check it? Resolve source references
against the pinned document, verify every concept target through the pinned
atlas and reference release, and then apply the closed schema and fail-closed
semantic gates.

The root fields are:

| Field | Meaning |
| --- | --- |
| `record_type` | Exactly `ExtrapolationRelease` |
| `release_id`, `release_digest`, `release_status`, `version` | Root identity and publication state |
| `profile` | `profile_id`, `profile_version`, and `usage_cap=searchOnly` |
| `input_releases` | Exact Core and document release pins, the atlas `{asset_id, manifest_digest, distribution_digest}` pin, and the selected reference release pin |
| `validation_sample_manifest` | Unique `record_refs[]` and their canonical `manifest_digest` |
| `concept_assignments[]` | Immutable candidate propositions |
| `evidence_bindings[]` | Exact fragment-backed evidence |
| `extraction_activities[]`, `ai_lineage_records[]` | Run and model provenance |
| `processing_segments[]`, `derived_text_projections[]` | The consumed model inputs and their reversible source mapping. The Extrapolator records what it was given; the publisher that prepared the segment owns its `segmentation_policy` |
| `validation_artifacts[]` | Secret-free validator request and exact response artifacts |
| `agent_validation_receipts[]`, `baseline_validation_receipts[]` | Independent attempts and deterministic reduction |
| `selection_context_digest`, `selection_receipts[]`, `selected_assignment_refs[]` | Digest of the complete pre-selection graph, per-candidate decision, and served upstream subset |
| `coverage` | Content-addressed `ExtrapolationCoverage` with candidate, selected, not-selected, deferred, and failure counts |

The document release and static atlas files are copied for offline fixture
validation. They remain owned by their publishers. The validator reads the
atlas files through a product-local reader and does not import RefSpec source.
Copying an artifact does not transfer authority or permit Rulespec to invent a
substitute identifier.

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

`ProcessingSegment` and `DerivedTextProjection` are *carriage* records: they
state which prepared model input was consumed and prove it maps reversibly onto
declared source ranges. Their presence in an `ExtrapolationRelease` is not a
claim that Rulespec produced them. `segmentation_policy` names the preparing
publisher's policy, and a Rulespec-authored value is a boundary violation.

`DerivedTextProjection.ordered_slices[]` uses half-open Unicode code-point
bounds. The slices account for every derived character and distinguish
`source_range`, `inserted_text`, and `transformed_range`. Source ranges resolve
inside declared input fragments. Inserted text carries its exact digest.
Omissions, the join delimiter, and normalization policy remain explicit.

## 5. Validation receipts

Everything in this section is an **acceptance rule for a submitted receipt**,
not a procedure the Extrapolator executes. A release carries receipts; the
reference validator decides whether they are admissible. No code in this
repository invokes a validator, reduces attempts to a baseline, or selects a
candidate — §7 records that those producing processes have no owner.

An `AgentValidationReceipt` records one immutable attempt: exact target and
digest, protocol, sealed input manifest, validator actor, independence group,
provider/model identity, request artifact, execution status, per-check outcomes
and evidence, and either a completed response and recommendation or a failure
reason. A failed execution has no recommendation. Failure and abstention are
distinct. The three terminal receipt kinds are fully content-addressed:
changing an input reference, status, check, rationale, recommendation,
selection result, or limitation creates a new record identifier.

A `BaselineValidationReceipt` names the exact profile, reference resource
release, sample manifest, rubric, aggregation policy, deterministic outcomes,
and agent attempts. A usable baseline requires exactly two completed attempts.
Both must recommend `supports`, every check from both must pass, and the two
attempts must have distinct validator actors, independence groups,
provider/model identities, and response artifacts. A flag, failed check,
abstention, failed execution, or extra attempt blocks a usable result.
`usable_for_search` and `usable_with_nonblocking_limits` qualify only candidate
use; they do not prove truth, approval, adoption, or applicability.

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

Validation rejects a missing or mismatched input release or atlas, root or child
digest mismatch, unresolved reference, unproved reference-resource membership,
invalid fragment coordinates, non-closing projection, missing evidence or
lineage, non-`searchOnly` selected assignment, selected processing-segment
target, unusable baseline, validator abstention, unselected assignment in the
served subset, coverage mismatch, or empty release.

The checked-in conformance set is:

- [`rulespec-core-release-m2.json`](../release-records/fixtures/rulespec-core-release-m2.json)
- [`m2-input-releases.json`](../release-records/fixtures/m2-input-releases.json)
- [`refspec-vocabulary-atlas/`](../release-records/fixtures/upstream/refspec-vocabulary-atlas/)
- [`m2-extrapolation-release-positive.json`](../release-records/fixtures/m2-extrapolation-release-positive.json)
- [`m2-negative-controls.json`](../release-records/fixtures/m2-negative-controls.json)

The negative controls cover wrong atlas and release pins, a concept outside
the selected release, digest mismatch, missing evidence, missing AI lineage,
broader usage, processing-segment target, validator abstention, and inclusion
of an excluded assignment. The fixture builder
[`tools/build_rulespec_release_fixtures.py`](../tools/build_rulespec_release_fixtures.py)
reproduces the static JSON and the test suite checks byte-equivalent data.

These artifacts have `release_status=fixture`. They prove the local file seam,
not the complete cross-product publication gate. Passing fixture validation is
not a tag, package publication, deployment, or activation claim.

## 7. Parked duties with no owner

Sections 3 and 5 require records that some process must produce. For the duties
below, **no product owns the producing process today**. They are recorded here
rather than deleted, and they are not assigned by implication: an unowned duty
does not become the Extrapolator's because the Extrapolator's release format
carries its receipt. Assigning an owner is a decision for the platform owner,
not an inference from this document.

| Parked duty | Contract that exists | What has no owner |
| --- | --- | --- |
| **Baseline validation execution** | `BaselineValidationReceipt`, and the admissibility rules in §5 | The runner that invokes two independent validators, captures request and response bytes, handles abstention and cost, and seals receipts. Nothing in any product invokes a provider for this purpose |
| **Deterministic selection** | `ExtrapolationSelectionReceipt`, `selection_context_digest`, and the served-subset gate | The evaluator that applies a selection policy to a candidate graph and emits `selected` / `not_selected` / `deferred` |
| **Approval and promotion** | `usage_eligibility`, the `searchOnly` cap, and the sealed-receipt requirements | The governance step that promotes a candidate past `searchOnly`. The upstream producer emits review-queue-only assignments by explicit design, so nothing can currently satisfy the §3 admission contract end to end |
| **Extrapolation-profile governance** | `profile_id`, `profile_version`, `usage_cap` | Who versions a profile, who may raise a usage cap, and what evidence a raise requires |

One further gap is **owned but unbuilt**, and is listed separately so it is not
mistaken for an unowned duty: SpicyRegs owns model-input segmentation and has a
measured segmenter, but no publisher-emitted segment file is delivered to a
Rulespec consumer yet. Until one is, the M2 fixture supplies a hand-authored
stand-in behind an explicit fixture-only guard, and §3's "prepared segments go
in" describes the contract rather than a running pipeline.
