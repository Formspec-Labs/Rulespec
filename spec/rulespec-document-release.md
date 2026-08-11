# DocumentRelease v2 (candidate)

Rulespec Core owns portable schemas, generated types, identity functions,
validators, diagnostics, and conformance fixtures. DocSpec consumes exactly one
`SourceCatalogRelease`, captures files, extracts representations, creates
structural segments and evidence coordinates, and publishes `DocumentRelease`.
That split is [REF-024](../../spicy-regs/RefSpec/docs/decisions.md); schema
ownership does not grant Rulespec authority over the records these schemas
carry.

This document defines the v2 candidate. It is a **candidate**: the schema and
fixture bytes are immutable and named by one digest, and any edit to any of
them starts a new candidate under a new digest.

## 1. Why version 2.0

DocSpec's live root writes `format: "docspec-document-release"` at
`formatVersion: "1.1"` (`DocSpec/src/docspec/domain/release.py:188,215`). That
is a different artifact: an internal pointer-record of active layers, blob
roots, store receipts, and a partition policy, whose members live in stores this
release format does not describe.

This is the portable wire contract — a self-contained bundle carrying the
dispositions, captures, representations, structure, and segments themselves.
Publishing it as `1.0` under the same token would place the portable shape
*below* the internal one on one version line, so a reader would take 1.1 for a
newer superset of it. `2.0` says what is true: same product, same logical
artifact, not compatible with 1.1.

The token stays in DocSpec's namespace because DocSpec owns the records. The
identity URN follows DocSpec's own `stable_urn` convention
(`urn:docspec:<kind>:v<n>:<digest>`), so this release is
`urn:docspec:document-release:v2:<digest>`. The `v2` is deliberate: DocSpec's
live releases already mint `urn:docspec:document-release:v1:` over a *different*
identity preimage, and two artifacts must not claim one name.

## 2. Bundle shape

```text
release.json                                       root manifest
manifests/global.json                              the one member manifest
schemas/document-release-v2.schema.json            release root schema
schemas/member-manifest-v1.schema.json             member manifest schema
schemas/source-dispositions-v1.schema.json         disposition projection schema
schemas/documents-v1.schema.json                   document/capture/representation schema
schemas/structural-nodes-v1.schema.json            structural node schema
schemas/search-segments-v1.schema.json             search segment schema
data/source-dispositions.json                      one row per member of U
data/documents.json                                one row per document/version
data/structural-nodes.json                         source-derived structure
data/search-segments.json                          bounded, deterministic segments
blobs/<documentId>.<ext>                           exact captured rendition bytes
text/<documentId>.txt                              the selected visible-text representation
```

Only relative POSIX member paths. No absolute path, no parent traversal, no
symlink. Every member carries its exact `byteSize` and `sha256`. v2 does not
partition.

## 3. Identity

```text
urn:docspec:document-release:v2:<sha256 over canonical {format, formatVersion, content}>
```

Canonical JSON is `rulespec-releases.md` §1 over a value domain with no
floating point and no unsafe integer, which equals RFC 8785 on that domain.

`annotations` is excluded from the preimage, and that is where `publishedAt`,
`releaseStatus`, and `buildRunId` live. Two builds of identical corpus content
share one identity.

The format token and version are **inside** the preimage. DocSpec's live
identity digests its content alone, so a future reshape of the same fields could
mint a colliding name; binding the token closes that.

## 4. What the release contains

**Disposition projection.** One row per member of the requested universe `U`,
carrying the catalog's disposition verbatim. A consumer obtains corpus
membership and exclusion coverage from this release alone, without reading the
source catalog. A capture result never feeds a fact back into the catalog.

**The bijection is structural.** A row whose `catalogDisposition` is `selected`
MUST carry a `documentVersionId`; any other disposition MUST carry `null`. There
is no corpus-side disposition that discards a selected item, so a processing
failure cannot become a silent downstream exclusion. A selected item that cannot
be made searchable blocks the build. `processingFailures` records attempts; it is
never load-bearing for membership.

**Capture.** Each document names the exact catalog release, `sourceItemId`,
`documentId`, `sourceIssuedVersion`, and `candidateRenditionId` its bytes came
from, plus the digest-pinned member holding those bytes. When the catalog
declared an `expectedSha256`, it MUST equal the captured digest.

**Representation.** Exactly one human-readable Unicode representation per
document, `text/plain; charset=utf-8`. Markup is not search text: HTML and XML
are extracted to visible text before segmentation.

**Structure and segments.** Source-derived `structuralNode` records form a tree;
a child's range lies inside its parent's, sibling ordinals are dense and
zero-based, and a section node spans its whole section. Each `searchSegment`
carries a `structuralParentId`, a dense document-wide `ordinal`, the
`headingPath` from the root down to its parent, its representation range, and
reversible `evidence` coordinates naming the captured rendition **by digest**.

**Offsets are bytes.** Every range is half-open `[start, end)` over UTF-8 bytes.
`spicy-regs/PLAN.md` §1b decides byte offsets for the ecosystem, and DocSpec's
own `EvidenceMapping` already counts a half-open representation byte interval.

**Coverage.** Every byte of the selected representation is covered by at least
one search segment or by exactly one excluded range, and the two never overlap.
Segments may overlap each other; `segmentedByteTotal` is the size of their
union, so `segmentedByteTotal + excludedByteTotal == representationByteTotal`
holds regardless.

**Set digests and the join receipt.** `selectedSourceSetDigest`,
`documentVersionSetDigest`, and `segmentSetDigest` are canonical set digests over
deduplicated sorted identifier lists. `sourceDocumentMappingDigest` is a **list**
digest over the sorted `[sourceItemId, documentVersionId]` pairs — the pairing is
the fact, so a repeated pair must move the digest rather than be folded away. The
`joinReceipt` seals that digest with both counts; equality plus distinctness is
the proof of the bijection.

## 5. Diagnostics and first-failure order

```text
invalid.root-syntax          invalid.source-catalog-pin
invalid.format               invalid.disposition
invalid.identity             invalid.capture
invalid.path                 invalid.representation
invalid.membership-missing   invalid.structure
invalid.membership-extra     invalid.segment
invalid.member-digest        invalid.coverage
invalid.schema               invalid.join
invalid.duplicate-identity   invalid.set-digest
                             invalid.counts
```

Bundle integrity first: nothing can be judged until the bytes are trusted, and
`invalid.path` outranks the membership codes for the reason given in
`rulespec-source-catalog-release.md` §5. The domain half runs in dependency
order — a segment cannot be judged against a structural parent whose own range
is already known wrong, structure cannot be judged against an untrusted
representation, and a representation cannot be judged before the capture it was
extracted from.

## 6. Deviations from DocSpec's live `docspec-document-release` 1.1

This is DocSpec's migration work, not Rulespec's. Recorded so the delta is a
list rather than a discovery.

| # | Live 1.1 | Portable 2.0 |
| --- | --- | --- |
| 1 | Root is a pointer-record: `activeLayers`, `blobRoots`, `storeReceiptSetDigest`, `runReceipt`, `catalogCommitReceipt`, `partitionPolicy` | Root describes a self-contained bundle: one member manifest, complete member digests, relative paths only |
| 2 | `counts`, `coverage`, `failures`, `partitionPolicy` are open `dict[str, Any]`, validated only as non-negative integers | All closed objects with named, required, recomputed fields |
| 3 | Identity digests `_content` alone (`release.py:64,156`); `format`/`formatVersion` sit outside the preimage | Identity digests `{format, formatVersion, content}` |
| 4 | `canonical_json_file_bytes` appends a trailing newline (`identity.py:98`) | Member and root bytes are exact canonical JSON with **no** trailing newline, matching `ExtrapolationRelease` v2 |
| 5 | No disposition projection over `U`; membership is implied by what is present | One required row per member of `U`, with the catalog disposition projected verbatim |
| 6 | `AcquisitionDisposition` and `ProcessorDisposition` both admit `accepted-failure` and `rejected-run` (`content.py:29,38`) | No corpus-side disposition exists; a selected item is a document or the build fails |
| 7 | No structural-node record. `Segment` carries `kind` and `derivation` but no parent, depth, or heading path (`content.py:652`) | `structuralNode` records with `structuralParentId`, `depth`, dense sibling `ordinal`, and containment; segments carry `headingPath` |
| 8 | `Representation.warnings` is a free string tuple (`content.py:492`) | Explicit `excludedRanges` with byte ranges, machine-legible `reasonCode`, and prose `reason` |
| 9 | No selected-source, document/version, segment, or source-document mapping digest; only `store_receipt_set_digest` and `logical_state_digest` | Four canonical digests plus a sealed one-to-one join receipt |
| 10 | `CapturedFile.acquired_at` is required, and `acquisition_started_at` optional (`content.py:236`) | No wall clock on a capture record. A clock inside a content-derived identity makes two byte-identical captures two releases; the rendition digest is the stronger evidence. Publication time lives once, in `annotations` |
| 11 | `ArtifactRef.locator`/`BlobRef.locator` are free strings and may be absolute | Every member path is a checked relative POSIX `objectKey` |
| 12 | Evidence names its source by `EvidenceCoordinate.source_digest` with optional `start`/`end`/`page`/`region` | Evidence requires `coordinateSystem`, `renditionSha256`, `start`, `end`, and must resolve inside the named rendition |
| 13 | No schema set inside the release | The six schemas ride inside the bundle, digest-pinned, so a consumer verifies with no Rulespec checkout |

Items 1, 3, 4, 5, 7, 8, 9, 10, and 11 are breaking for a 1.1 producer. Items 2,
6, 12, and 13 are tightenings a 1.1 producer can satisfy without reshaping its
own records.

## 7. Conformance fixtures and the candidate bundle digest

`release-records/fixtures/document-release-v2/` holds one valid bundle and one
invalid bundle per diagnostic code, each a single-rule mutation of the valid one
with every downstream digest, count, coverage figure, and identity restamped.
Every byte offset in the corpus is derived from the fixture's own bytes;
hand-written offsets in a corpus about offsets would test the author's
arithmetic instead of the validator.

The valid bundle is built from the sealed `SourceCatalogRelease` v1 fixture, and
pins it by identity and digest — the two candidates are joined, not merely
adjacent.

`release-records/document-release-v2-candidate.json` is a `RulespecCoreRelease`
(`rulespec-releases.md` §2) pinning the six schemas, both validator modules, and
every sealed bundle. Its `release_id` is the candidate's immutable name.
`rulespec-document-validate` re-derives it and replays the corpus from the
installed package, with no checkout on the path.
