# SourceCatalogRelease v1 (candidate)

Rulespec Core owns portable schemas, generated types, identity functions,
validators, diagnostics, and conformance fixtures. SpicyRegs discovers and
selects regulatory sources and publishes `SourceCatalogRelease`. That split is
[REF-024](../../spicy-regs/RefSpec/docs/decisions.md); schema ownership does not
grant Rulespec authority over the records these schemas carry.

This document defines the v1 candidate. It is a **candidate**: the schema and
fixture bytes are immutable and named by one digest, and any edit to any of
them starts a new candidate under a new digest. A later Rulespec release reuses
tested candidate bytes unchanged or is a different candidate.

`DocumentRelease` is a separate root with a separate owner (DocSpec) and is not
defined here.

## 1. Bundle shape

A release is a materialized tree of immutable files. No symlink, no absolute
path, no parent traversal.

```text
release.json                                         root manifest
manifests/global.json                                the one member manifest
schemas/source-catalog-release-v1.schema.json        release root schema
schemas/member-manifest-v1.schema.json               member manifest schema
schemas/source-items-v1.schema.json                  source item schema
data/source-items.json                               the requested universe U
```

v1 does not partition. Every member is listed once in `manifests/global.json`,
sorted by `objectKey`, each with its exact `byteSize`, `sha256`, `recordCount`,
and `schemaId`. The schemas travel inside the release so a consumer verifies it
with no Rulespec checkout.

`format` is `spicyregs-source-catalog-release`, `formatVersion` is `1.0`.

## 2. Identity

The release identity is derived from the exact identity-bearing payload:

```text
urn:spicyregs:source-catalog-release:v1:<sha256 over canonical {format, formatVersion, content}>
```

`annotations` is excluded from that preimage, so an operator note never renames
a release. Canonical JSON is `rulespec-releases.md` §1 — sorted keys, `,`/`:`
separators, UTF-8, no non-finite numbers — over a value domain with no floating
point and no integer outside the JSON safe range. On that domain the encoding
equals RFC 8785 byte for byte, which the conformance suite asserts against an
independent RFC 8785 implementation.

Both set digests are SHA-256 over the canonical JSON of the **deduplicated,
sorted** `sourceItemId` list:

| Field | Membership |
| --- | --- |
| `requestedUniverseSetDigest` | every source item in the release (`U`) |
| `selectedSourceSetDigest` | every item whose disposition is `selected` (`S`) |

A repeated identifier does not move a set digest. Duplication is a separate
defect with its own diagnostic, so neither masks the other. Counts are
diagnostics derived from the members; the set digests are the proof of
membership, never the counts.

## 3. Source items

Each member of `U` carries a stable `sourceItemId`, a regulatory `documentId`,
and the `sourceIssuedVersion` the **source** issued. `sourceIssuedVersion` is
not a capture digest; a later DocSpec capture never writes back into a published
catalog release.

`sourceNativeMetadata` carries the source's own record verbatim and
uninterpreted. `normalizedMetadata` carries the interpreted MVP view: `title`,
`agencies`, `documentType`, `publicationDate`, `lastUpdatedDate`, `docketIds`,
`regulationIdentifierNumbers`, `commentCloseDate`, `language`, `sourceUrl`.
Every one of those keys is present on every normalized block; a fact the source
did not state is `null`, never absent, so a consumer never reads "not stated" as
"not modeled". A `selected` item MUST carry a complete normalized block. A
non-selected item MAY carry `null` when the source never served usable metadata.

`sourceObservedTopics` are the SOURCE's topics. They are not RefSpec concepts,
they carry no concept identifier, and a value in RefSpec's URN space is
rejected. Mapping a source topic to a concept happens downstream and elsewhere.

`candidateRenditions` name what the source offers for capture: `renditionId`,
`mediaType`, `locator`, and an `expectedSha256`/`expectedByteSize` pair that is
non-null only when the source supplies enough to know the bytes before capture.
Every `selected` item requires at least one candidate rendition.

## 4. Selection disposition

Every item carries exactly one disposition from `selected`, `excluded`,
`deleted`, `unavailable`, `failed`.

The disposition is a required **object property** on the item, not a row in a
dispositions table. A table admits zero rows and two rows and needs a rule
against each; one required object closes both by construction. Every
non-selected disposition requires both a machine-legible `reasonCode` and a
human-readable `reason`.

For the MVP a selected `sourceItemId` and `documentId` map one to one. Grouping
several source items into one document is out of scope.

## 5. Diagnostics and first-failure order

Every defect is one diagnostic — a code, a path, and a message. A verdict is the
**first** failure under this total order:

```text
invalid.root-syntax
invalid.format
invalid.identity
invalid.path
invalid.membership-missing
invalid.membership-extra
invalid.member-digest
invalid.schema
invalid.duplicate-identity
invalid.disposition
invalid.set-digest
invalid.rendition
invalid.topic-scope
invalid.counts
invalid.coverage
```

Diagnostics are appended in a deterministic walk and the minimum is stable, so
both the reported code and the reported path are functions of the bundle bytes
alone.

The order matches `ExtrapolationRelease` v2's with one deliberate difference:
`invalid.path` outranks the membership codes. A bundle that names a path outside
itself is refused before any membership claim about that path is judged;
ordering it below `invalid.membership-missing` would report an unresolvable
`objectKey` as an absent file and hide the traversal.

## 6. Conformance fixtures

`release-records/fixtures/source-catalog-release-v1/` holds one valid bundle and
one invalid bundle per diagnostic code. Each invalid bundle is the valid bundle
copied and mutated in exactly one way, with every downstream digest, count, and
identity restamped, so it violates the rule it is named for and nothing else.

`corpus.json` seals each bundle by tree digest and records the code and path the
verifier must report first. Every code in §5 has a fixture: a code with no
fixture is a claim, not a gate.

## 7. The candidate bundle digest

`release-records/source-catalog-release-v1-candidate.json` is a
`RulespecCoreRelease` (`rulespec-releases.md` §2) pinning the three schema
files, the validator module, and every sealed fixture bundle by digest. Its
`release_id` is the candidate's immutable name, and re-deriving it from the
bytes is what makes immutability checkable rather than asserted. Changing any
pinned byte changes that name.

The bundle rides inside the `rulespec-conformance` wheel; there is no second
schema-publication pipeline beside it. `rulespec-ci-validate` re-derives the
bundle digest and replays the whole sealed corpus from the installed package,
with no checkout on the path.
