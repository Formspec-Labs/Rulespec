# Product and release decisions

## 2026-07-31: Separate source, vocabulary, extrapolation, and search ownership

**Status:** Accepted

### Decision

The system has four products with independent ownership and releases:

| Product | Owns | Does not own |
| --- | --- | --- |
| SpicyRegs | Immutable source documents, exact text representations, structural passages, acquisition history, and `DocumentRelease` | Vocabulary policy, derived semantic assignments, or search ranking |
| RefSpec | Vocabulary capture, managed releases, crosswalk publication, and static `VocabularyAtlasAsset` files | Source documents, generic Rulespec shapes, extrapolation execution, or search ranking |
| Rulespec | Portable evidence and provenance shapes plus evidence-bound extrapolation | Source acquisition, managed vocabulary content, or search serving |
| SpicySearch | Disposable indexes, ranking, queries, result explanations, feedback, and `SearchSnapshot` | Canonical documents, vocabulary authority, or extrapolation authority |

Rulespec has two independent release units:

- **Rulespec Core** publishes `RulespecCoreRelease`, generic schemas, generated
  types, validators, and conformance fixtures. Core has no source dependency on
  RefSpec, SpicyRegs, or SpicySearch.
- **Rulespec Extrapolator** consumes pinned Core, `DocumentRelease`, a static
  vocabulary atlas, and the `ReferenceResourceRelease` identity proven by that
  atlas. It publishes a nonempty `ExtrapolationRelease` containing evidence-bound
  candidates, provenance, validation receipts, deterministic selection receipts,
  processing records, and reversible text projections.

The RefSpec open-label profile remains portable schema source in this
repository, but it belongs to the Extrapolator release boundary. It is not
generated into or exported from the `rkaf-core` Rust crate.

Published-data dependencies are acyclic:

```text
RulespecCoreRelease -> DocumentRelease ------------------+
RulespecCoreRelease -> RefSpec managed release -> atlas -+-> ExtrapolationRelease -> SearchSnapshot
```

`DocumentRelease` and RefSpec managed releases can be produced independently
after they pin Core. `ExtrapolationRelease` pins the exact document, atlas
asset, and reference release it consumed. SpicySearch may index those
artifacts but cannot rewrite them.

### Practical consequences

- Repositories exchange immutable JSON artifacts and digests. They do not
  import another product's source tree or read its mutable database.
- A source, vocabulary, model, prompt, evidence, validation, or selection
  change creates a new owning release. It never silently changes an existing
  release.
- Processing segments are model inputs. They are not citable source evidence
  and cannot be served assignment targets.
- Search may narrow upstream eligibility. It cannot turn `unverified` into
  `verified`, broaden `searchOnly`, or create source or vocabulary authority.
- A fixture or candidate is not a published release. Publication remains a
  separate, explicit action.

This decision supersedes designs that placed source acquisition, vocabulary
operations, model extraction, and search serving behind one application
boundary. The implementation detail and compatibility rules are normative in
[`spec/rulespec-releases.md`](../spec/rulespec-releases.md).

> **Scope note (2026-08-02, annotation in place — nothing above is rewritten):**
> the ownership table and the release-contents sentence stand. What the
> Extrapolator *executes* is narrowed by the decision below: segment
> construction moves to SpicyRegs, and the processes that produce baseline
> validation, selection, and approval are parked with no owner.

## 2026-08-02: The Extrapolator consumes prepared segments and verifies receipts

**Status:** Accepted

### Decision

The Rulespec Extrapolator's execution boundary is narrow and now stated
exactly. Prepared processing segments and a versioned extrapolation profile go
in. Evidence-linked structured document descriptions come out, recording the
exact input segment, source references, prompt, and model lineage.

It does not parse sources, tokenize, handle PDF or HTML, or build segments.
**SpicyRegs owns** source parsing, exact text, durable structural passages, and
model-input segmentation, and its `structure-overlap-1800` segmenter preserves
reversible source offsets and digests. **SpicySearch independently owns** search
chunks, indexes, and ranking; retrieval windows are not extrapolation inputs.
Rulespec may record consumed segment references and digests. It must not build a
parallel document pipeline.

This decision consumes the platform's 2026-08-02 document-processing
correction, and it was taken against the code rather than the prose. The
repository contains a segment *fixture builder* and a *validator*: no
production segmenter, no baseline-validation runner, no selection engine, and
no producer of an `ExtrapolationRelease` outside the fixture path — which stamps
`release_status: fixture` and now refuses anything else. Three claims in
[`spec/rulespec-releases.md`](../spec/rulespec-releases.md) §3 asserted
otherwise; they are struck in place under a dated correction banner, with the
file and line evidence recorded there.

What the code does back, and what therefore survives unchanged: closed shape
validation, evidence resolution against the pinned document and atlas, exact
model-input lineage that re-derives every derived character from declared
source ranges, the `searchOnly` eligibility contract, and the three required
terminal receipt types.

**Parked with no owner.** The producing processes behind baseline validation,
deterministic selection, approval and promotion past `searchOnly`, and
extrapolation-profile governance have no owning product. They are recorded in
[`spec/rulespec-releases.md` §7](../spec/rulespec-releases.md), not deleted and
not assigned by implication. Carrying a receipt's contract is not owning the
process that produces it. Assigning an owner is a decision for the platform
owner.

### Practical consequences

- A Rulespec-authored `segmentation_policy` is a boundary violation.
  `ProcessingSegment` and `DerivedTextProjection` are carriage records: they
  state which prepared input was consumed and prove it maps reversibly onto
  source ranges. Their presence is not a claim that Rulespec produced them.
- The M2 fixture's join stays, because no publisher-emitted segment file exists
  to vendor and the sealed conformance set needs a segment to validate against.
  It is fenced: one named function, a docstring stating it is not a segmenter
  and must never become one, refusal on any non-`fixture` release status, and
  tests asserting it is the only construction site in the tree.
- Read every selection, baseline, and accepted-output sentence in this
  repository's specs as a shape a submitted receipt must satisfy, never as a
  capability that runs.
- Consuming a real prepared segment is the remaining half of the SpicyRegs
  segmentation seam. When one is delivered, vendor it under
  `release-records/fixtures/upstream/` and delete the fixture-only join.
