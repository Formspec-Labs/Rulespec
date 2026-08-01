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
