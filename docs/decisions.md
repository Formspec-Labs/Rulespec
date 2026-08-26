# Product and release decisions

## 2026-08-25: Separate the artifact runtime from graph conformance

**Status:** Accepted

### Decision

The Rulespec-owned `rulespec-artifacts` distribution is the one generic
platform-artifact runtime. It contains canonical JSON, the schema-bundle and
streaming framed-section digesters, container types, builder, structural
verifier, source protocols, diagnostics, specification, and structural fixtures.
It has no RDF, JSON-LD, SHACL, `rdflib`, `pyshacl`, or RDF-canonicalization
dependency.

The full `rulespec-conformance` distribution depends on a compatible
`rulespec-artifacts` major and does not copy that implementation or fixture
corpus. Products that only exchange platform artifacts depend on the thin
distribution. This narrows the 2026-08-11 choice below: keeping graph vocabulary
and shape data in `rulespec-conformance` remains accepted, but it does not force
the unrelated artifact runtime and RDF/SHACL dependency closure on every
artifact consumer.

Producer roots pin one immutable package, image, or exact Git commit plus the
verifier tuple. Artifact members never carry duplicate source trees, wheels,
images, or verifier code solely to prove those pins.

### Practical consequences

- `rulespec_artifacts` contains the one implementation and one structural
  fixture corpus; `rulespec-conformance` depends on it.
- The full validator's package test proves it uses the thin distribution. The
  thin package test proves its installed dependency closure contains no graph
  stack.
- Products declare only framed-digest domains, sections, projections, ordering,
  and duplicate rules. They call the installed shared implementation.

## 2026-08-11: The contract ships as an import, not a checkout

**Status:** Accepted

### Decision

Everything a consumer needs to author Rulespec data — the compiled JSON
Schemas, the compiled SHACL, the hand-authored shape suite, the JSON-LD
context, the closed enums and lattices, and the term names themselves — ships
inside the `rulespec-conformance` wheel as importable data and constants
(`rulespec_conformance.contract`). A consumer clones this repository to
contribute to it, never to depend on it.

It is the existing distribution rather than a new one because it is the same
bytes: the wheel already carries `compiled/`, `shapes/` and the context for the
validator's own use, and a second distribution would either duplicate them or
depend on this one to find them. The name says conformance; the contents are
what conforming requires.

### Practical consequences

- The vocabulary is generated, never hand-maintained:
  `tools/build_contract_exports.py` writes `contract/enums.py` and
  `contract/terms.py` from the CUE and the normative specs, and `--check` fails
  `make test-audits` on drift. A term retired upstream stops resolving
  downstream at import, which is the only enforcement that survives a consumer
  who does not run our gates.
- The exports stay generic. A term, enum, or lattice enters them because
  Rulespec declares it — not because a consumer wants somewhere to put one. A
  consumer-specific constant in `contract/` is a boundary violation of the same
  kind as a Rulespec-authored `segmentation_policy`, and the ownership table
  above decides it the same way.
- Consumers must not keep a local copy of anything the package exports. A
  mirrored lattice cannot be kept in order by any check either side owns; that
  is the defect class this export exists to end.
- Packaged data is reached through `importlib.resources`. Paths built from
  `__file__` guess at a layout the build backend owns, and the guess was wrong
  the moment the data moved into `_data/`.

## 2026-07-31: Separate source, vocabulary, extrapolation, and search ownership

**Status:** Accepted

**Ownership update (2026-08-25):** RefSpec REF-048 supersedes only this
decision's assignment of exact document renditions, structural passages, and
`DocumentRelease` to SpicyRegs. DocSpec now owns capture, document processing,
and `DocumentRelease`; SpicyRegs retains source acquisition and faithful
source-native publication. The other rows remain accepted.

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

> **Scope note (updated 2026-08-25, annotation in place — nothing above is
> rewritten):** REF-048 moves capture, representation, passage, and segment
> construction to DocSpec while SpicyRegs retains source-native acquisition and
> publication. What the Extrapolator executes remains narrowed below. Baseline
> validation, selection, and approval remain parked unless a later accepted
> decision assigns them.

## 2026-08-02: The Extrapolator consumes prepared segments and verifies receipts

**Status:** Accepted

### Decision

The Rulespec Extrapolator's execution boundary is narrow and now stated
exactly. Prepared processing segments and a versioned extrapolation profile go
in. Evidence-linked structured document descriptions come out, recording the
exact input segment, source references, prompt, and model lineage.

It does not parse sources, tokenize, handle PDF or HTML, or build segments.
**DocSpec owns under REF-048** document parsing, exact captured text, durable
structural passages, and model-input segmentation. SpicyRegs supplies only the
pinned source-native inputs. **SpicySearch independently owns** search chunks,
indexes, and ranking; retrieval windows are not extrapolation inputs.
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
