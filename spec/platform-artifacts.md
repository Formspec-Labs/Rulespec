# Rulespec platform artifacts 1.0

Status: normative. REF-024 assigns the product boundaries; this document owns
only the shared byte format, identity rules, and structural verification.

## 1. Purpose

A platform artifact is one immutable, versioned directory or object-store
prefix. SpicyRegs publishes source catalogs, DocSpec publishes derivations, and
SpicySearch publishes derivations and compositions. All use this format and the
installed `rulespec_conformance.platform_artifact` implementation.

The format has three kinds: `source-catalog`, `derivation`, and `composition`.
It has one root, one membership form, and one structural verification path.
There are no compatibility roots, inline member lists, mutable database reads,
or required platform services.

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

## 3. Root

`artifact.json` MUST be a canonical JSON object with exactly these fields:

```json
{
  "artifactDigest": "sha256:...",
  "counts": {
    "manifestCount": 1,
    "memberCount": 1,
    "totalMemberByteSize": 100,
    "totalRecordCount": 1
  },
  "coverage": {
    "accountedInputCount": 1,
    "complete": true,
    "unaccountedInputCount": 0
  },
  "format": "spicy-artifact",
  "formatVersion": "1.0",
  "inputs": [],
  "kind": "source-catalog",
  "logicalId": "urn:spicy:artifact:source-catalog:...",
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
  "spec": {}
}
```

The root MUST NOT exceed 1 MiB. Optional fields inside nested objects are
absent, never `null` or empty placeholders.

`inputs` is a sorted, duplicate-free array of closed objects containing
`role`, `logicalId`, and `artifactDigest`. It contains no storage locator.
`role` is lowercase kebab case. A deployment resolves the pair of logical ID
and artifact digest to storage through its own injected edge adapter.

`counts` is the exact aggregate of all declared payload members. `coverage`
states whether the producer accounted for every expected product input; a
kind-specific semantic check defines what one input means.

## 4. Kind specifications

`kind` selects one closed `spec` object.

### 4.1 Source catalog

The exact fields are `catalogId`, `sourceSystemId`, `sourceSystemVersion`,
`selectionPolicyId`, `selectionPolicyVersion`, `selectionPolicyDigest`,
`requestedUniverseSetDigest`, and `selectedSourceSetDigest`. IDs are absolute.
Digests are qualified lowercase SHA-256.

The members and product semantic check account for the complete requested
universe and its dispositions. The shared format does not define source APIs or
source-specific record fields.

### 4.2 Derivation

A derivation MUST have at least one input. Its exact fields are `processorId`,
`processorVersion`, `processorDigest`, `policyId`,
`policyVersion`, `policyDigest`, `parametersDigest`, `partitioningId`, and the
`partitioningDigest`, and a nonempty, sorted, duplicate-free
`expectedOutputRoles` array.
The partitioning digest binds the complete partition plan and its behavior.

Handoff IDs, task IDs, attempts, timestamps, workers, and task ledgers are
execution evidence, not logical inputs. Local and distributed execution of the
same processor, policy, parameters, partitioning, and logical inputs therefore
describe the same logical derivation.

### 4.3 Composition

A composition MUST have one or more inputs, all with role `member`. Its exact
fields are `mergePolicyId`, `mergePolicyVersion`,
`mergePolicyDigest`, and the nonempty, duplicate-free `totalOrderKey` array.

Each input pins an independently published artifact in place. A composition
MUST NOT copy, hardlink, rebuild, or wrap the input artifact's payload bytes.
Product code opens each admitted input through its existing provider session.

## 5. Member manifests

`memberManifests` is sorted by `(scopeKind, scopeId, objectKey)` and
duplicate-free. It is nonempty for source catalogs and derivations. A
reference-only composition has no payload and uses an empty array; it does not
publish a dummy manifest. Each reference is a closed object containing:

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
JSON tree. Entries sort by `objectKey` within their manifest. Every payload
member appears exactly once across all manifests.

A member descriptor has exactly `objectKey`, `role`, `mediaType`, `byteSize`,
and qualified `sha256`, plus absent-or-present `recordCount` and `schemaId`.
Paths are normalized portable relative keys. Empty segments, `.`, `..`, NUL,
backslashes, absolute paths, drive prefixes, symbolic links, escaped paths, and
special files are invalid.

## 6. Identity

`logicalId` is:

```text
"urn:spicy:artifact:" + kind + ":" +
hex_sha256(canonical_json({
  "format": format,
  "formatVersion": formatVersion,
  "kind": kind,
  "logicalInputs": [{"logicalId": input.logicalId, "role": input.role}, ...],
  "spec": spec
}))
```

`artifactDigest` is the qualified SHA-256 of the canonical complete root with
only `artifactDigest` omitted. It binds exact input artifacts, manifest
references, member bytes through their digests, counts, and coverage.

Equivalent work retains its `logicalId`. Any different admitted input bytes,
payload bytes, or publication evidence changes `artifactDigest`. Reuse keys use
logical identity; admission uses the exact artifact pin and all nested digests.

## 7. Verification and dependency injection

Rulespec exposes one `verify_artifact` result-returning entry point and one
`admit_artifact` raising entry point over the same implementation. Both accept
an injected `MemberSource` with only `keys()` and `open(objectKey)`. The package
ships `LocalMemberSource`; blob stores implement the same two operations at
their outer edge. Verification performs no network access.

Structural verification MUST, in order, check canonical and bounded root bytes,
the exact version and closed kind shape, identities and any external pin,
manifest framing and bounds, exact file membership, safe paths, declared sizes
and digests, aggregate counts, complete coverage, and declared derivation output
roles. Payload hashing and manifest parsing use bounded reads. Changed, missing,
extra, linked, unknown, or incomplete data is refused before product use.

`MemberSource.open` raises `MemberNotFoundError` for deterministic absence and
`MemberSourceError` for operational storage failures. Absence becomes an
artifact diagnostic; transient or unavailable storage remains an operational
exception rather than being misreported as invalid bytes. Callers may inject a
scratch directory for the disk-backed exact-membership index.

A product semantic verifier may be injected into the same entry point. It runs
only after structural verification and may validate product schemas, evidence,
coverage, or query invariants. It MUST NOT repeat canonicalization, identity,
membership, path, size, or digest checks. Expensive semantic recomputation runs
at the build gate; admission and open repeat structural and digest checks.

The common diagnostic vocabulary is `invalid.root-syntax`, `invalid.format`,
`invalid.identity`, `invalid.path`, `invalid.manifest`,
`invalid.membership-missing`, `invalid.membership-extra`,
`invalid.member-digest`, `invalid.schema`, `invalid.statistics`, and
`invalid.limit`. Products may add semantic issue messages but not a second
structural diagnostic type.

## 8. Generated and installed surfaces

`constraints/platform/platform-artifact.cue` is the shape source. The existing
Rulespec compiler emits closed plain-JSON Schema, TypeScript, and Rust carriers.
The wheel includes the generated JSON Schema, this document, and
`rulespec_conformance.platform_artifact`. Consumer repositories install a built
wheel; they do not import a Rulespec checkout or keep copies of this protocol.
