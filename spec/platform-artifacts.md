# Rulespec platform artifacts 1.0

Status: normative. REF-048 assigns catalog ownership and leaves this document
only the generic byte format, identity rules, and structural verification. The
local `rulespec-artifacts` 1.0.9 wheel implements this surface without product
schemas or graph dependencies, and `rulespec-conformance` consumes that wheel.
Neither distribution is published yet.

## 1. Purpose

A platform artifact is one immutable, versioned directory or object-store
prefix. Any product may define an artifact kind and canonical `spec` object.
Every publication that opts into this platform-artifact family uses this
container and the installed `rulespec_artifacts` implementation. Independently
governed artifact families, including RefSpec
Atlas releases and search views, keep their own roots and enter a consumer only
through that product's separately pinned admission boundary.

The format does not enumerate product kinds or fields inside their `spec`
objects. It has one root, one membership form, and one structural verification
path. There are no compatibility roots, inline member lists, mutable database
reads, or required platform services.

## 2. Canonical JSON

Every JSON file governed by this specification MUST use UTF-8 without a byte
order mark and MUST equal the output of the shared canonical encoder:

- object keys sort by their UTF-16 code units;
- strings use JSON escaping with no insignificant whitespace;
- integers stay within `-(2^53-1)` through `2^53-1`;
- binary floating-point and non-finite numbers are forbidden; and
- duplicate object keys are forbidden.

Noncanonical bytes are invalid even when a general JSON parser could read them.
This profile is RFC 8785 on its admitted value domain.

Whenever this specification says an array is sorted, compare strings by their
unsigned UTF-16 code-unit sequences with no locale or normalization. Compare
tuples lexicographically by those string keys, then by any declared numeric
key. This is the same string order used for canonical object keys; a language's
native string comparator is not authoritative. A named semantic-order array,
such as `totalOrderKey`, preserves its declared order and is only required to
be duplicate-free unless its product specification says otherwise.

### 2.1 Canonical-encoder change control

Any change that alters canonical bytes for one value in the admitted domain, or
newly refuses a value that an earlier format admitted, is a platform-artifact
format MAJOR change with a new `formatVersion`; it MUST NOT reinterpret an old
root under the new encoder or ship as a package MINOR or PATCH change. The prior
major `rulespec-artifacts` wheel, specification, and golden corpus remain
available to verify roots that declare that version. A behavior-preserving
implementation change may use an ordinary package release and MUST reproduce
all prior canonical bytes.

Before a product moves a current pointer to the new major, its owner uses the
product's existing release configuration, package or image registry, and
consumer smoke tests to prove that every current reader can open the replacement
pin. Do not create a second platform inventory, source archive, or file-hash
ledger for this purpose. Historical immutable roots need no re-emission: they
retain their old format and verifier. Retiring support for an old major is a
product release decision; neither Rulespec nor a cross-product registry claims
that every historical root was globally enumerated.

Every dependent package declares one load-bearing `rulespec-artifacts`
major-version bound and proves it in an isolated installed-wheel test. The
`rulespec-artifacts` wheel ships a
golden corpus covering every admitted JSON value class, refusal boundary,
UTF-16 ordering edge, and integer limit with exact expected bytes. Every
language binding and dependent that emits an artifact runs the same corpus.
Release automation compares the previous and candidate encoders: any changed
golden byte or refusal requires the new format major and blocks a product
pointer cutover until its existing consumer checks pass against the replacement.

### 2.2 Streaming framed-section digest

`framedSectionDigest` is the sole platform algorithm for an ordered digest over
canonical record sections. It initializes SHA-256 with the nonempty UTF-8 domain
string followed by one NUL byte. For each section in declared order, it appends
an unsigned 64-bit big-endian section-name byte length, the UTF-8 section name,
an unsigned 64-bit big-endian item count, and, for each item in declared record
order, an unsigned 64-bit big-endian canonical-JSON byte length followed by
those bytes. Counts or lengths outside the unsigned 64-bit range, duplicate
section names, a declared/observed count mismatch, or a value rejected by the
platform canonical encoder fail.

The implementation accepts a declared count and iterable for each section,
streams every item, and never materializes a section or corpus array. It returns
a qualified SHA-256 digest.

A product digest definition declares only its domain string, ordered section
names, closed record projection for each section, and total-order key including
null handling. The product verifier rejects duplicate or out-of-order keys
before passing records to this function. Products MUST call the installed
Rulespec implementation and MUST NOT restate or fork the framing algorithm.

## 3. Root

`artifact.json` MUST be a canonical JSON object with exactly these required
fields and the optional `knownLimits` and `supersedes` fields defined below:

```json
{
  "artifactDigest": "sha256:...",
  "counts": {
    "manifestCount": 1,
    "memberCount": 1,
    "totalMemberByteSize": 100,
    "totalRecordCount": 1
  },
  "format": "spicy-artifact",
  "formatVersion": "1.0",
  "inputs": [],
  "kind": "example-kind",
  "logicalId": "urn:spicy:artifact:example-kind:...",
  "memberManifests": [
    {
      "byteSize": 400,
      "manifestId": "global:all",
      "memberCount": 1,
      "objectKey": "manifests/all.json",
      "scopeId": "all",
      "scopeKind": "global",
      "sha256": "sha256:...",
      "totalMemberByteSize": 100,
      "totalRecordCount": 1
    }
  ],
  "producer": {
    "implementationId": "oci://registry.example/example-publisher@sha256:...",
    "product": "example",
    "verifierId": "urn:example:artifact-verifier",
    "verifierImplementationId": "oci://registry.example/example-verifier@sha256:...",
    "verifierVersion": "1.0.0"
  },
  "spec": {}
}
```

The root MUST NOT exceed 1 MiB. Optional fields are absent, never `null` or
empty placeholders.

`inputs` is an array of closed objects containing `role`, `logicalId`, and
`artifactDigest`. Each logical ID ends in a 64-character lowercase hexadecimal
logical digest as defined in section 6. Inputs sort by `(role, logicalDigest)`
and that pair is duplicate-free; the declared namespace and `artifactDigest` are
not ordering tiebreakers because a namespace-only rename or physical repack must
not reorder logical inputs. `role` is lowercase kebab case. The array contains no
storage locator. A deployment resolves the declared logical ID and artifact
digest to storage through its own injected edge adapter.

`counts` is the exact aggregate of all declared members. Completeness, coverage,
selection, and disposition
are product meaning and MUST live in the
owning product's `spec` or payload members. The generic root does not force an
unrelated product to invent a coverage model.

`knownLimits`, when present, is a nonempty sorted, duplicate-free array of
closed objects containing exactly `code`, `scope`, `statement`, and
`evidenceDigests`. `code` and `scope` are nonempty lowercase kebab-case strings;
`statement` is nonempty human-readable text; and `evidenceDigests` is a nonempty
sorted, duplicate-free array of qualified SHA-256 digests that resolve to a
declared member or exact input artifact. The array sorts by `(scope, code)`.
These records keep artifact-specific operational, evidentiary, and coverage
limits available to offline consumers. They are publication knowledge, not
logical content: Rulespec excludes them from `logicalId` and includes them in
`artifactDigest`. A product verifier may require or interpret product-specific
codes but cannot hide or discard the generic records.

`supersedes`, when present, is a closed object containing exactly `logicalId`,
`artifactDigest`, and `reason`. The identities name the exact prior root in the
same product series; `reason` is nonempty free text that distinguishes a
correction, refresh, replacement, or other product-owned cause. The field is
publication succession evidence, not a logical input: Rulespec excludes it from
`logicalId` and includes it in `artifactDigest`. The structural verifier checks
only its closed shape and digest syntax. Before moving a mutable product-series
pointer, the publisher MUST resolve the pair, verify that it equals the
pointer's current root, and use its product verifier to prove that the prior and
candidate roots belong to the same series. A first generation omits the field;
an unrelated series starts under a different pointer. A candidate with a
missing, empty, mismatched, or unresolvable succession record cannot replace a
current pointer.

`producer` is required publication provenance with exactly `product`,
`implementationId`, `verifierId`, `verifierVersion`, and
`verifierImplementationId`.
`product` is a nonempty lowercase kebab-case identifier. `implementationId` is
an absolute immutable identity for the exact package bytes, digest-pinned
container image, or repository plus full Git commit object ID used to build the
artifact; a mutable package version, image tag, branch, path, or worktree name
alone is invalid. Package and image identities include their published digest.
A package download URL MAY use its registry-published `#sha256=<hex>` fragment;
an OCI identity uses its registry digest such as `@sha256:<hex>`.
A Git identity relies on Git's full commit object ID and MUST NOT add a
project-owned source-tree digest. `verifierId` is absolute and
`verifierVersion` is nonempty. `verifierImplementationId` identifies the exact
released verifier through the same package, OCI, or Git-native forms as
`implementationId`; it does not add a second hash of those bytes. It may equal
`implementationId` when one release contains both publisher and verifier.

Structural verification checks the closed shape and syntax. The product
verifier compares the producer tuple and the receipt's verifier tuple with the
accepted installed producer and verifier descriptors before product use. A
missing, mutable, unknown, or mismatched tuple fails closed. Consumer admission
does not fetch or execute producer code from the artifact.

Wheels, executables, container manifests, source trees, implementation archives,
and verifier or oracle code MUST NOT be added as members solely to prove the
producer record. There are no generic producer-evidence payload roles. Products
may still define semantic build-receipt members; a receipt that has no records
omits `recordCount` and `schemaId` under that product's rules.

The complete `producer` record is excluded from `logicalId` and included in
`artifactDigest`. An implementation rewrite that produces the same logical
state therefore preserves logical identity, while changed or missing provenance
moves or invalidates the exact artifact.

## 4. Product kind and specification

`kind` MUST be a nonempty lowercase kebab-case identifier. `spec` MUST be a
canonical JSON object. Both are identity-bearing. Rulespec treats the object as
opaque and MUST NOT whitelist product kinds, fields, roles, policies, or
relationships. Product specifications MUST keep schema namespaces and other
representation locators out of `spec`; they bind schema meaning by digest and
put optional human-readable identifiers in artifact evidence. A reader keys a
schema on its declared digest and may warn on an unfamiliar identifier namespace
but MUST NOT refuse otherwise valid bytes because a local namespace constant
differs. Every identity-bearing product schema digest MUST call the installed
Rulespec `schemaBundleDigest` function; products do not define another
schema-family preimage.

`schemaBundleDigest` accepts a nonempty map from normalized product-relative
schema path to one canonical JSON Schema document. It omits only the top-level
artifact-authored `$id` in each document and retains the semantic `$schema`
dialect declaration. For every `$ref`, it resolves a fragment-only reference
against the referring schema and a relative reference against the referring
schema's directory. The normalized target MUST remain in the input map. It then
rewrites the reference to `#/$defs/<path-token><fragment>`, where `path-token`
is the target path encoded as one JSON Pointer token (`~` becomes `~0` and `/`
becomes `~1`) and `fragment` is empty or the original fragment's JSON Pointer
path without its leading `#`.
Absolute, network, non-JSON-Pointer, escaped, or unresolved references fail.

The function forms one exact canonical object with only key `$defs`; its value
maps every normalized path to the transformed schema. The qualified digest is
SHA-256 over UTF-8 `rulespec-schema-bundle/1`, one NUL byte, and that object's
canonical JSON bytes. Canonical object-key ordering supplies the total path
order. Duplicate normalized paths fail. A single-schema family uses the same
function with one map entry. The semantic schema bytes are bound by
`schemaBundleDigest`. A product may also carry a product-owned schema member
when offline schema bytes are part of its format; its exact installed files,
declared IDs, and byte digests are then bound by `artifactDigest`. A product
cannot place a declared ID elsewhere in `spec` or another logical-state
preimage.

The product that owns a kind defines and validates its `spec`, required input
roles, product payload roles and schemas, completeness meaning, and logical
invariants after Rulespec structural admission. Unknown product meaning fails
in that product; it does not become a Rulespec schema change.

A conformance fixture MUST define a test-owned fourth kind with an opaque
`spec` object and prove that the installed structural reader admits it without
knowing its fields. Product-specific valid and invalid fixtures live with the
product owner, not in the Rulespec structural corpus.

### 4.1 Optional product-neutral relation profiles

Rulespec also supplies two opt-in semantic helpers so products do not copy
common artifact-relation logic. They do not run during structural admission,
reserve a `kind`, or prevent another product from using an opaque `spec`.
Composition roots inject the selected helper into the owning product's semantic
verifier after the shared structural reader succeeds.

`DerivationRelation` has exactly `relationKind`, `processorId`,
`processorVersion`,
`processorDigest`, `policyId`, `policyVersion`, `policyDigest`,
`parametersDigest`, `partitioningId`, `partitioningDigest`, and a nonempty,
sorted, duplicate-free `expectedOutputRoles` array. The partitioning digest
binds the complete partition plan and its behavior. Handoff IDs, task IDs,
attempts, timestamps, workers, and task ledgers are execution evidence, not
logical inputs. Local and distributed execution of the same processor, policy,
parameters, partitioning, and logical inputs therefore describes the same
logical derivation. `relationKind` is `derivation`.

An opted-in derivation requires one or more inputs and nonempty product payload
membership. After structural admission, the helper MUST compare the complete
set of admitted product roles with `expectedOutputRoles`: every expected role
appears at least once and no undeclared product role appears. A mismatch fails
before the product reads a member.

`CompositionRelation` has exactly `relationKind`, `mergePolicyId`,
`mergePolicyVersion`,
`mergePolicyDigest`, and a nonempty, duplicate-free `totalOrderKey` array. Its
inputs have role `member` and pin one or more independently published artifacts.
A reference-only composition MUST NOT carry or reproduce an input's payload. Its
owning product MAY require bounded semantic build-receipt members that prove the
composition-specific state derived at its producer gate; those receipts are
product evidence, not input records, and omit `recordCount` and `schemaId`.
Rulespec does not define or interpret their roles or fields. The composition
MUST NOT copy, hardlink, wrap, rewrite, migrate, or rebuild input payloads. It
opens each admitted input through the owning product's injected provider
session.

These are nested relation descriptions or separately supplied verifier inputs;
they are never the complete root `spec` and do not set or dispatch on root
`kind`. Each product owns a distinct root kind and closed product `spec`, embeds
the applicable relation description when useful, and explicitly invokes the
helper after structural admission. Rulespec MUST NOT reserve `derivation` or
`composition` as root kinds. `CompositionRelation.relationKind` is
`composition`.

The helper implementations and fixtures remain in Rulespec. A product that
uses one owns the additional input-role, output-role, ordering, coverage, and
domain invariants that make that relation meaningful for the product.

## 5. Member manifests

`memberManifests` is an array sorted by `(scopeKind, scopeId, objectKey)` and
duplicate-free. It MAY be empty when the owning product defines a genuinely
reference-only artifact with no receipt or payload; its root counts are then
zero. Each reference is a closed object containing:

- `manifestId`, equal to `scopeKind + ":" + scopeId`;
- `scopeKind`, either `global` or `partition`, and `scopeId`;
- normalized relative `objectKey`;
- `byteSize` and qualified `sha256`; and
- `memberCount`, `totalMemberByteSize`, and `totalRecordCount`.

A referenced manifest MUST NOT exceed 64 MiB. It is a canonical closed object:

```json
{
  "counts": {
    "memberCount": 1,
    "totalMemberByteSize": 100,
    "totalRecordCount": 1
  },
  "format": "spicy-artifact-members",
  "formatVersion": "1.0",
  "manifestId": "partition:0001",
  "members": [
    {
      "byteSize": 100,
      "mediaType": "application/jsonl",
      "objectKey": "records/items.jsonl",
      "recordCount": 1,
      "role": "records",
      "sha256": "sha256:..."
    }
  ],
  "scope": {"id": "0001", "kind": "partition"}
}
```

The verifier streams `members`; it does not materialize the manifest as one
JSON tree. Each descriptor has a location key: `("object-key", objectKey)` for
a local member or `("blob-ref", blobRef)` for an external member. Entries sort
by that tuple and the location key is duplicate-free across the artifact. Every
declared product member appears exactly once across all manifests.

A member descriptor has exactly one of these two closed location forms, plus
`role`, `mediaType`, `byteSize`, and absent-or-present `recordCount` and
`schemaId`:

- a local member has `objectKey` and qualified `sha256`; or
- an external immutable member has `blobRef`, whose value is itself the
  qualified SHA-256 digest of the referenced bytes.

`blobRef` is a content identity, not a URL or mutable storage locator. The
artifact edge resolves it through an injected source. This lets a successor
artifact reuse a large unchanged member without copying it into a new prefix,
while the manifest still binds the exact bytes and counts. A descriptor MUST
NOT carry both forms or omit both. `recordCount`, when present, contributes to
root and manifest `totalRecordCount`; the owning product decides which member
roles contain records. Paths are normalized portable relative keys. Empty
segments, `.`, `..`, NUL,
backslashes, absolute paths, drive prefixes, symbolic links, escaped paths, and
special files are invalid.

## 6. Identity

The last colon-delimited component of `logicalId` is `logicalDigest`:

```text
logicalDigest = hex_sha256(canonical_json({
  "format": format,
  "formatVersion": formatVersion,
  "kind": kind,
  "logicalInputs": [
    {"logicalDigest": suffix(input.logicalId), "role": input.role}, ...
  ],
  "spec": spec
}))

logicalId = artifact_declared_absolute_urn_namespace + logicalDigest
```

The namespace MUST be a syntactically valid absolute URN ending in `:` and MUST
include the product kind, but it is not identity-bearing. The shared builder
defaults to `urn:spicy:artifact:<kind>:`. The verifier validates the declared
namespace syntax and kind component, recomputes `logicalDigest`, and compares
only the final 64 hexadecimal characters for identity. It MUST NOT compare the
namespace with a mutable producer-side constant or reject an otherwise valid
artifact because its namespace differs from the builder default. It may emit a
warning. Product logical references use the digest suffix in their own logical
preimages and retain the complete declared ID only as exact artifact evidence.

`artifactDigest` is the qualified SHA-256 of the canonical complete root with
only `artifactDigest` omitted. It binds exact input artifacts, manifest
references, member bytes through their digests, counts, producer evidence,
limits, and succession evidence.

Equivalent work retains its `logicalDigest`; a namespace-only change may change
the declared `logicalId` string and exact `artifactDigest` but not logical
identity. Any different admitted input bytes, payload bytes, or publication
evidence changes `artifactDigest`. Reuse keys use the tuple `(kind,
logicalDigest)`; admission uses the complete declared logical ID, exact artifact
pin, and all nested digests.

## 7. Verification and dependency injection

Rulespec exposes one `verify_artifact` result-returning entry point and one
`admit_artifact` raising entry point over the same implementation. Both accept
an injected `MemberSource` with `keys()` and `open(objectKey)` for the
artifact's local files and an injected `BlobSource` with `open(blobRef)` for
digest-addressed external members. A versioned object-store adapter MAY also
implement `ReceiptMemberSource.receipt(objectKey)`. That method returns the
provider's exact object key, byte size, SHA-256 checksum, and non-null immutable
version ID. Rulespec compares those values with the admitted descriptor instead
of downloading the payload solely to hash it. The root and manifests are always
read and verified as bytes.

The receipt is live provider metadata, not a second artifact, cache ticket, or
project-owned checksum ledger. One adapter instance MUST obtain the receipt,
open the exact version, and derive any downstream versioned object address from
the same provider namespace and version. An unversioned store, a store without
an exact SHA-256 checksum, or an adapter that cannot bind those operations MUST
omit `receipt()`; Rulespec then streams and hashes every payload byte. The
package ships `LocalMemberSource` and a local content-addressed `BlobSource`;
deployments adapt object stores at that outer edge. Rulespec itself performs no
network access. A caller may omit `BlobSource` only when no declared member uses
`blobRef`.

For a child artifact or blob store inside one larger local distribution, the
package exposes
`PinnedLocalDirectory(parent_path, expected_identity=(device, inode))`. The
optional expected identity lets a caller carry forward an already admitted
parent identity: the constructor compares the same opened parent descriptor it
will pin before returning, without a path re-stat or second open. Its
`member_source(child_key)` and `blob_source(child_key)` methods accept only a
normalized, contained relative child key. The returned source pins both the
real parent directory and the child root. Every list or open operation reopens
the parent, verifies its device and inode identity, and traverses the child and
member paths through no-follow directory descriptors. A replaced parent or
child, a symbolic link, or an escaped path fails closed. Products use this
shared reader instead of copying local path-safety code.

`LocalBlobSource` verifies the SHA-256 content address before it exposes local
blob bytes on every open, then serves the same opened regular file while the
member source checks that its file state stays unchanged. This keeps the local
adapter's immutability check at the read boundary instead of relying on a prior
admission or a digest-shaped filename.

The local adapters coordinate cooperative processes that use these APIs.
Deployments isolate mutually untrusted writers with separate operating-system
accounts, filesystem permissions, or storage credentials. Within one local
account, descriptor-relative traversal, kernel conditional creation, advisory
locks, and digest verification provide path containment, crash recovery,
concurrency control, and fail-closed reads; they are not an authorization
boundary against another process that already has permission to rename or
rewrite every path owned by that account.

The package exposes `publish_directory_no_replace(source, destination)` for
same-filesystem local directories. It syncs the complete real-file tree, coordinates
cooperative writers through an advisory lock on the pinned destination parent,
and uses the host kernel's no-replace directory rename. Process death releases
the lock, no sentinel pathname is created, and an existing destination remains
unchanged. Unsupported platforms fail before publication. Products use this
shared primitive rather than maintaining a second lock or rename implementation.
`publish_child_directory_no_replace` provides the same operation relative to
already-open source and destination parent descriptors; the matching
`PinnedLocalDirectory` method reopens and checks named pinned parents for callers
without retained descriptors. `move_child_directory_no_replace` provides the
underlying no-replace move for safe transaction cleanup without forcing a
durability pass over bytes being discarded.

Structural verification MUST, in order, check canonical and bounded root bytes,
the exact version and closed generic root shape, kind grammar, opaque canonical
`spec`, and the closed producer-record shape; rederive identities and check any
external pin; parse and bound every manifest; build the exact descriptor index;
and check file membership, safe paths, declared sizes, digests, and aggregate
counts. Product verifiers compare the producer and receipt verifier tuples with
their installed or explicitly allowed descriptors, then check role sets,
completeness or coverage, and other semantic invariants. Payload hashing and
manifest parsing use bounded reads; an exact immutable provider receipt may
replace only the payload hashing pass. Changed, missing, extra, linked, unknown,
or incomplete data is refused before product use.

`MemberSource.open` and `BlobSource.open` raise `MemberNotFoundError` for
deterministic absence and `MemberSourceError` for operational storage failures.
Absence becomes an artifact diagnostic; transient or unavailable storage
remains an operational exception rather than being misreported as invalid
bytes. `MemberSource.keys()` governs exact local membership: a `blobRef` is not
a local key and unrelated objects in the external content store are irrelevant.
The verifier streams every external member, checks its size, and requires its
SHA-256 digest to equal `blobRef`. Callers may inject a scratch directory for
the disk-backed exact-membership index.

A product semantic verifier may be injected into the same entry point. It runs
only after structural verification and may validate product schemas, evidence,
coverage, or query invariants. It MUST NOT repeat canonicalization, identity,
membership, path, size, or digest checks. Expensive semantic recomputation runs
at the build gate; admission and open repeat structural checks and either byte
digests or exact immutable provider checksum/version checks.

The common diagnostic vocabulary is `invalid.root-syntax`, `invalid.format`,
`invalid.identity`, `invalid.path`, `invalid.manifest`,
`invalid.membership-missing`, `invalid.membership-extra`,
`invalid.member-digest`, `invalid.schema`, `invalid.statistics`, and
`invalid.limit`. Products may add semantic issue messages but not a second
structural diagnostic type.

## 8. Generated and installed surfaces

`constraints/platform/platform-artifact.cue` is the shape source. The existing
Rulespec compiler emits closed plain-JSON Schema, TypeScript, and Rust carriers.
The Rulespec-owned `rulespec-artifacts` distribution contains the canonical JSON
encoder, framed-section digester, schema-bundle digester, root and manifest
types, structural builder and verifier, source protocols, diagnostics, this
specification, and the common structural fixture corpus. Its import package is
`rulespec_artifacts`.

`rulespec-artifacts` has no RDF, JSON-LD, SHACL, `rdflib`, `pyshacl`, or RDF
canonicalization dependency. The full `rulespec-conformance` distribution
depends on a compatible `rulespec-artifacts` major and does not copy its
implementation or fixtures. A product that only builds or verifies platform
artifacts installs `rulespec-artifacts`; it does not acquire the graph
conformance stack. Consumer repositories install a built wheel; they do not
import a Rulespec checkout or keep copies of this protocol.

An isolated wheel test imports every public artifact surface, runs the
structural fixture corpus, and proves the installed dependency closure contains
none of the excluded RDF/SHACL packages.
