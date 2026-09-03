"""Provider-neutral construction and verification for platform artifacts.

The package owns byte identity, manifests, membership, and bounded structural
verification. Products inject storage and semantic checks; this module knows
nothing about catalogs, documents, regulations, or search.
"""

from __future__ import annotations

import codecs
import ctypes
import errno
import functools
import hashlib
import io
import json
import os
import posixpath
import re
import sqlite3
import stat
import struct
import sys
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Protocol, Self, runtime_checkable

try:
    import fcntl
except ImportError:  # pragma: no cover - the local adapter fails closed off POSIX.
    fcntl = None  # type: ignore[assignment]

try:
    # Optional accelerator for _string_bytes: msgspec.json.encode is ~9.6x
    # faster than json.dumps on representative corpus strings and, like
    # json.dumps, raises UnicodeEncodeError (not TypeError, unlike orjson) for
    # a lone Unicode surrogate, so the fail-closed path below is unaffected by
    # which encoder ran. Imported defensively so the package stays
    # dependency-light: install the `fast` extra to get it, run unchanged
    # (falling back to json.dumps) without it.
    import msgspec
except ImportError:  # pragma: no cover - exercised by tests via monkeypatch.
    # Deliberately undeclared, in this package and in its wheel metadata: this
    # wheel proves an empty dependency closure (`make test-package-artifacts`
    # asserts `not requires("rulespec-artifacts")`), so msgspec is used only
    # when a consumer's environment already provides it. Both encoders are
    # byte-identical over the canonical profile -- control characters, non-BMP,
    # combining marks, RTL, U+2028/U+2029 -- and both raise UnicodeEncodeError
    # on a lone surrogate, so which one runs can never move a digest or change
    # a refusal. It is an accelerator, never a behaviour.
    msgspec = None  # type: ignore[assignment]

FORMAT = "spicy-artifact"
FORMAT_VERSION = "1.0"
ROOT_OBJECT_KEY = "artifact.json"
MEMBER_MANIFEST_MEDIA_TYPE = "application/vnd.spicy-artifact-members+json"
MEMBER_MANIFEST_FORMAT = "spicy-artifact-members"
MEMBER_MANIFEST_VERSION = "1.0"
JSON_SAFE_INTEGER_MAX = (1 << 53) - 1
DEFAULT_ROOT_BYTE_LIMIT = 1024 * 1024
DEFAULT_MANIFEST_BYTE_LIMIT = 64 * 1024 * 1024
DEFAULT_READ_CHUNK_BYTES = 1024 * 1024
DEFAULT_MANIFEST_SPOOL_BYTES = 1024 * 1024
DIAGNOSTIC_CODES = (
    "invalid.root-syntax",
    "invalid.format",
    "invalid.identity",
    "invalid.path",
    "invalid.manifest",
    "invalid.membership-missing",
    "invalid.membership-extra",
    "invalid.member-digest",
    "invalid.schema",
    "invalid.statistics",
    "invalid.limit",
)

_ROOT_REQUIRED_FIELDS = frozenset(
    {
        "artifactDigest",
        "counts",
        "format",
        "formatVersion",
        "inputs",
        "kind",
        "logicalId",
        "memberManifests",
        "producer",
        "spec",
    }
)
_ROOT_OPTIONAL_FIELDS = frozenset({"knownLimits", "supersedes"})
_INPUT_FIELDS = frozenset({"artifactDigest", "logicalId", "role"})
_MANIFEST_REFERENCE_FIELDS = frozenset(
    {
        "byteSize",
        "manifestId",
        "memberCount",
        "objectKey",
        "scopeId",
        "scopeKind",
        "sha256",
        "totalMemberByteSize",
        "totalRecordCount",
    }
)
_MEMBER_COMMON_FIELDS = frozenset({"byteSize", "mediaType", "role"})
_MEMBER_OPTIONAL_FIELDS = frozenset({"recordCount", "schemaId"})
_COMMON_COUNT_FIELDS = frozenset(
    {"manifestCount", "memberCount", "totalMemberByteSize", "totalRecordCount"}
)
_PRODUCER_FIELDS = frozenset(
    {
        "implementationId",
        "product",
        "verifierId",
        "verifierImplementationId",
        "verifierVersion",
    }
)
_KNOWN_LIMIT_FIELDS = frozenset({"code", "scope", "statement", "evidenceDigests"})
_SUPERSEDES_FIELDS = frozenset({"artifactDigest", "logicalId", "reason"})
_DERIVATION_RELATION_FIELDS = frozenset(
    {
        "expectedOutputRoles",
        "parametersDigest",
        "partitioningDigest",
        "partitioningId",
        "policyDigest",
        "policyId",
        "policyVersion",
        "processorDigest",
        "processorId",
        "processorVersion",
        "relationKind",
    }
)
_COMPOSITION_RELATION_FIELDS = frozenset(
    {
        "mergePolicyDigest",
        "mergePolicyId",
        "mergePolicyVersion",
        "relationKind",
        "totalOrderKey",
    }
)
_SCOPE_KINDS = frozenset({"global", "partition"})
_ROLE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
_QUALIFIED_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_ABSOLUTE_ID = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:[^\s]+\Z")
_LOGICAL_DIGEST_SUFFIX = re.compile(r"[0-9a-f]{64}\Z")
_PUBLISHED_SHA256 = re.compile(
    r"(?:^|[/:?#&=@])sha256[:=][0-9a-f]{64}(?:$|[/?#&])"
)
_GIT_OBJECT_ID = re.compile(
    r"(?:^|[@/:])(?:[0-9a-f]{40}|[0-9a-f]{64})(?:$|[#?])"
)


@dataclass(frozen=True, slots=True)
class VerificationIssue:
    """Describe one deterministic artifact verification failure."""

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} at {self.path}: {self.message}"


class ArtifactVerificationError(ValueError):
    """Raise one fail-closed artifact verification issue."""

    def __init__(self, issue: VerificationIssue) -> None:
        self.issue = issue
        super().__init__(str(issue))


class MemberSourceError(OSError):
    """Report an operational member-source failure outside artifact validity."""


class MemberNotFoundError(MemberSourceError):
    """Report a deterministic absent object so admission can normalize it."""


def _fail(code: str, path: str, message: str) -> None:
    if code not in DIAGNOSTIC_CODES:
        raise RuntimeError(f"undeclared platform artifact diagnostic: {code}")
    raise ArtifactVerificationError(VerificationIssue(code, path, message))


# Bounds both caches below. The hot-path working set is object keys (schema
# field names, repeated across every record) plus a small vocabulary of
# repeated identifiers (kinds, roles, media types, statuses) -- at most a few
# thousand distinct short strings for any one artifact schema, no matter how
# many records a build processes. 65536 gives generous headroom above that
# working set -- including e.g. a family of schemas sharing one process --
# while still bounding memory (each cached entry is a short byte string, so
# worst case is a few megabytes) instead of growing with the record count.
# Payload values (titles, document numbers, ...) are overwhelmingly unique
# per record: they cost a cache miss like before, and past this bound they
# evict the hot keys instead of growing the cache without limit.
_STRING_ENCODE_CACHE_MAXSIZE = 65536


def _encode_string(value: str) -> bytes:
    """Encode one JSON string value, using msgspec when it is importable."""

    if msgspec is not None:
        return msgspec.json.encode(value)
    return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")


@functools.lru_cache(maxsize=_STRING_ENCODE_CACHE_MAXSIZE)
def _encode_string_cached(value: str) -> bytes | None:
    # `path` is deliberately not a parameter here: it only ever varies the
    # error message on the (rare, terminal) refusal path, so keeping it out
    # of the cache key is what lets millions of repeated object keys and
    # identifiers actually hit this cache. A string that cannot be encoded
    # returns the sentinel None instead of letting the exception propagate,
    # so the caller can fail with a path-specific message on every call
    # without a lone surrogate poisoning the cache with a stale exception
    # instance for every later occurrence of the same string.
    try:
        return _encode_string(value)
    except UnicodeEncodeError:
        return None


def _string_bytes(value: str, *, path: str) -> bytes:
    encoded = _encode_string_cached(value)
    if encoded is not None:
        return encoded
    try:
        _encode_string(value)
    except UnicodeEncodeError as error:
        _fail(
            "invalid.root-syntax",
            path,
            f"text contains a lone Unicode surrogate: {error}",
        )


def _sort_key_bytes(value: str) -> bytes:
    return value.encode("utf-16-be")


@functools.lru_cache(maxsize=_STRING_ENCODE_CACHE_MAXSIZE)
def _sort_key_bytes_cached(value: str) -> bytes | None:
    # Same shape and same reason as _encode_string_cached: _utf16_sort_key
    # runs once per object key per record on the same hot path, its path
    # argument is always the fixed literal "$" rather than a real per-call
    # path, and a failing string must not cache a stale exception.
    try:
        return _sort_key_bytes(value)
    except UnicodeEncodeError:
        return None


def _utf16_sort_key(value: str) -> bytes:
    encoded = _sort_key_bytes_cached(value)
    if encoded is not None:
        return encoded
    try:
        _sort_key_bytes(value)
    except UnicodeEncodeError as error:
        _fail(
            "invalid.root-syntax",
            "$",
            f"object key contains a lone Unicode surrogate: {error}",
        )


def _canonical_json_parts(value: Any, *, path: str) -> bytes:
    if value is None:
        return b"null"
    if value is True:
        return b"true"
    if value is False:
        return b"false"
    if isinstance(value, int):
        if not -JSON_SAFE_INTEGER_MAX <= value <= JSON_SAFE_INTEGER_MAX:
            _fail("invalid.root-syntax", path, "integer is outside the JSON safe range")
        return str(value).encode("ascii")
    if isinstance(value, float):
        _fail("invalid.root-syntax", path, "binary floating-point values are forbidden")
    if isinstance(value, str):
        return _string_bytes(value, path=path)
    if isinstance(value, (list, tuple)):
        return (
            b"["
            + b",".join(
                _canonical_json_parts(item, path=f"{path}/{index}")
                for index, item in enumerate(value)
            )
            + b"]"
        )
    if isinstance(value, Mapping):
        keys = list(value)
        if any(not isinstance(key, str) for key in keys):
            _fail("invalid.root-syntax", path, "object key is not text")
        fields = (
            _string_bytes(key, path=f"{path}/key")
            + b":"
            + _canonical_json_parts(value[key], path=f"{path}/{key}")
            for key in sorted(keys, key=_utf16_sort_key)
        )
        return b"{" + b",".join(fields) + b"}"
    _fail("invalid.root-syntax", path, f"unsupported JSON value {type(value).__name__}")


def canonical_json_bytes(value: Any) -> bytes:
    """Encode identity-bearing data with the artifact canonical JSON profile."""

    return _canonical_json_parts(value, path="$")


class CanonicalSetDigester:
    """Digest a sorted, duplicate-free text stream as one canonical JSON set."""

    def __init__(self) -> None:
        self._digest = hashlib.sha256(b"[")
        self._first = True
        self._previous: str | None = None

    def add(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("set digest values must be text")
        if self._previous is not None and _utf16_sort_key(value) <= _utf16_sort_key(
            self._previous
        ):
            raise ValueError("set digest values must be sorted and distinct")
        payload = canonical_json_bytes(value)
        if not self._first:
            self._digest.update(b",")
        self._digest.update(payload)
        self._first = False
        self._previous = value

    def finish(self) -> str:
        digest = self._digest.copy()
        digest.update(b"]")
        return "sha256:" + digest.hexdigest()


def sha256_digest(value: bytes | Any) -> str:
    """Return a qualified SHA-256 digest for bytes or canonical JSON."""

    payload = value if isinstance(value, bytes) else canonical_json_bytes(value)
    return "sha256:" + hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True, slots=True)
class FramedSection:
    """One named, counted record stream for :func:`framed_section_digest`."""

    name: str
    count: int
    records: Iterable[Any]


def _u64(value: int, *, label: str) -> bytes:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value < 1 << 64
    ):
        raise ValueError(f"{label} must be an unsigned 64-bit integer")
    return struct.pack(">Q", value)


def framed_section_digest(domain: str, sections: Iterable[FramedSection]) -> str:
    """Digest ordered canonical records without materializing a corpus array."""

    if not isinstance(domain, str) or not domain:
        raise ValueError("digest domain must be nonempty text")
    try:
        domain_bytes = domain.encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("digest domain must be valid Unicode") from error
    digest = hashlib.sha256(domain_bytes + b"\0")
    names: set[str] = set()
    for section in sections:
        if not isinstance(section, FramedSection):
            raise TypeError("sections must contain FramedSection values")
        if not section.name or section.name in names:
            raise ValueError("section names must be nonempty and distinct")
        names.add(section.name)
        try:
            name_bytes = section.name.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ValueError("section name must be valid Unicode") from error
        digest.update(_u64(len(name_bytes), label="section name length"))
        digest.update(name_bytes)
        digest.update(_u64(section.count, label="section count"))
        observed = 0
        for record in section.records:
            payload = canonical_json_bytes(record)
            digest.update(_u64(len(payload), label="record length"))
            digest.update(payload)
            observed += 1
            if observed > section.count:
                raise ValueError(f"section {section.name!r} exceeds its declared count")
        if observed != section.count:
            raise ValueError(
                f"section {section.name!r} declared {section.count} records but yielded {observed}"
            )
    return "sha256:" + digest.hexdigest()


def _schema_path(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or "\\" in value
        or value.startswith("/")
    ):
        raise ValueError(f"schema path is not normalized and relative: {value!r}")
    normalized = posixpath.normpath(value)
    if normalized != value or normalized in {".", ".."} or normalized.startswith("../"):
        raise ValueError(f"schema path is not normalized and contained: {value!r}")
    return normalized


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _rewrite_schema_refs(value: Any, *, source_path: str, paths: frozenset[str]) -> Any:
    if isinstance(value, list):
        return [
            _rewrite_schema_refs(item, source_path=source_path, paths=paths)
            for item in value
        ]
    if not isinstance(value, Mapping):
        return deepcopy(value)
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key != "$ref":
            result[key] = _rewrite_schema_refs(
                item, source_path=source_path, paths=paths
            )
            continue
        if not isinstance(item, str):
            raise TypeError(f"$ref in {source_path!r} must be text")
        target_text, marker, fragment = item.partition("#")
        if marker and fragment and not fragment.startswith("/"):
            raise ValueError(
                f"$ref in {source_path!r} must use a JSON Pointer fragment"
            )
        if target_text:
            if _ABSOLUTE_ID.fullmatch(target_text):
                raise ValueError(f"absolute $ref in {source_path!r} is forbidden")
            target = _schema_path(
                posixpath.normpath(
                    posixpath.join(posixpath.dirname(source_path), target_text)
                )
            )
        else:
            target = source_path
        if target not in paths:
            raise ValueError(
                f"$ref in {source_path!r} targets missing schema {target!r}"
            )
        suffix = f"/{fragment.lstrip('/')}" if fragment else ""
        result[key] = f"#/$defs/{_pointer_token(target)}{suffix}"
    return result


def schema_bundle_digest(schemas: Mapping[str, Mapping[str, Any]]) -> str:
    """Return the sole logical digest for a closed JSON Schema family."""

    if not isinstance(schemas, Mapping) or not schemas:
        raise ValueError("schema bundle must be a nonempty mapping")
    normalized: dict[str, Mapping[str, Any]] = {}
    for raw_path, raw_schema in schemas.items():
        path = _schema_path(raw_path)
        if path in normalized:
            raise ValueError(f"duplicate normalized schema path: {path!r}")
        if not isinstance(raw_schema, Mapping):
            raise TypeError(f"schema {path!r} must be an object")
        normalized[path] = raw_schema
    paths = frozenset(normalized)
    definitions: dict[str, Any] = {}
    for path, schema in normalized.items():
        selected = {
            key: deepcopy(value) for key, value in schema.items() if key != "$id"
        }
        definitions[path] = _rewrite_schema_refs(
            selected, source_path=path, paths=paths
        )
    payload = canonical_json_bytes({"$defs": definitions})
    return (
        "sha256:" + hashlib.sha256(b"rulespec-schema-bundle/1\0" + payload).hexdigest()
    )


def _reject_float(value: str) -> None:
    _fail("invalid.root-syntax", "$", f"floating-point value {value!r} is forbidden")


def _reject_constant(value: str) -> None:
    _fail("invalid.root-syntax", "$", f"non-finite value {value!r} is forbidden")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("invalid.root-syntax", "$", f"duplicate object key {key!r}")
        result[key] = value
    return result


def parse_canonical_json(
    raw: bytes, *, path: str = "$", code: str = "invalid.root-syntax"
) -> Any:
    """Parse byte-exact canonical JSON.

    Raises:
        ArtifactVerificationError: The bytes are invalid or noncanonical.
    """

    if raw.startswith(b"\xef\xbb\xbf"):
        _fail(code, path, "a UTF-8 byte order mark is forbidden")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
        encoded = canonical_json_bytes(value)
    except ArtifactVerificationError as error:
        if error.issue.code == code and error.issue.path == path:
            raise
        _fail(code, path, error.issue.message)
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        _fail(code, path, f"invalid JSON: {error}")
    if encoded != raw:
        _fail(code, path, "JSON bytes are not canonical")
    return value


def parse_admitted_json(
    raw: bytes, *, path: str = "$", code: str = "invalid.root-syntax"
) -> Any:
    """Parse one row of an artifact whose member digest has already been checked.

    Same refusals as :func:`parse_canonical_json` at parse time -- byte order
    mark, invalid UTF-8, duplicate keys, floats, and the JSON constants -- but
    it does not re-encode the parsed value to prove the bytes were canonical.

    That proof belongs to the build gate. Admission has already streamed this
    member, hashed it, and refused it unless the bytes matched the digest the
    manifest declares, so re-deriving canonical form per row re-proves nothing
    about integrity: it only re-checks that the producer wrote canonical bytes,
    which no longer varies once the bytes are pinned. Measured on real catalog
    rows, the re-encode was 7x the cost of the parse it followed.

    Use it only while reading a member of an artifact admitted through
    :func:`admit_artifact`. For bytes that have not been through that gate --
    a root object, a manifest, anything read before or outside admission --
    :func:`parse_canonical_json` is still the one to call, because there the
    canonical form is the only thing establishing the bytes are what they claim.
    """

    if raw.startswith(b"\xef\xbb\xbf"):
        _fail(code, path, "a UTF-8 byte order mark is forbidden")
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except ArtifactVerificationError as error:
        if error.issue.code == code and error.issue.path == path:
            raise
        _fail(code, path, error.issue.message)
    except (UnicodeError, json.JSONDecodeError, ValueError) as error:
        _fail(code, path, f"invalid JSON: {error}")


def _closed_mapping(
    value: object, fields: frozenset[str], *, path: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("invalid.schema", path, "value must be an object")
    actual = frozenset(value)
    if actual != fields:
        _fail(
            "invalid.schema",
            path,
            f"fields differ; missing={sorted(fields - actual)}, unknown={sorted(actual - fields)}",
        )
    return value


def _mapping(value: object, *, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail("invalid.schema", path, "value must be an object")
    return value


def _array(value: object, *, path: str) -> Sequence[object]:
    if not isinstance(value, list):
        _fail("invalid.schema", path, "value must be an array")
    return value


def _text(value: object, *, path: str) -> str:
    if not isinstance(value, str) or not value:
        _fail("invalid.schema", path, "value must be nonempty text")
    return value


def _uint(value: object, *, path: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 0 <= value <= JSON_SAFE_INTEGER_MAX
    ):
        _fail("invalid.schema", path, "value must be a JSON-safe unsigned integer")
    return value


def _digest(value: object, *, path: str) -> str:
    selected = _text(value, path=path)
    if _QUALIFIED_SHA256.fullmatch(selected) is None:
        _fail(
            "invalid.schema", path, "value must be a qualified lowercase SHA-256 digest"
        )
    return selected


def _absolute_id(value: object, *, path: str) -> str:
    selected = _text(value, path=path)
    if _ABSOLUTE_ID.fullmatch(selected) is None:
        _fail("invalid.schema", path, "value must be an absolute identifier")
    return selected


def _implementation_id(value: object, *, path: str) -> str:
    selected = _absolute_id(value, path=path)
    if (
        _PUBLISHED_SHA256.search(selected) is None
        and _GIT_OBJECT_ID.search(selected) is None
    ):
        _fail(
            "invalid.schema",
            path,
            "implementation identity must contain a published digest or full Git object ID",
        )
    return selected


def _logical_digest(logical_id: str, *, path: str) -> str:
    suffix = logical_id.rsplit(":", 1)[-1]
    if _LOGICAL_DIGEST_SUFFIX.fullmatch(suffix) is None:
        _fail("invalid.schema", path, "logical ID must end in a 64-character digest")
    return suffix


def _role(value: object, *, path: str) -> str:
    selected = _text(value, path=path)
    if _ROLE.fullmatch(selected) is None:
        _fail("invalid.schema", path, "value must be a lowercase artifact role")
    return selected


def _distinct_text_array(
    value: object,
    *,
    path: str,
    role_values: bool = False,
) -> tuple[str, ...]:
    selected = tuple(
        (
            _role(item, path=f"{path}/{index}")
            if role_values
            else _text(item, path=f"{path}/{index}")
        )
        for index, item in enumerate(_array(value, path=path))
    )
    if not selected:
        _fail("invalid.schema", path, "array must not be empty")
    if len(selected) != len(set(selected)):
        _fail("invalid.schema", path, "array values must be distinct")
    return selected


def validate_object_key(value: object, *, path: str) -> str:
    """Return one normalized portable member key."""

    selected = _text(value, path=path)
    if "\x00" in selected or "\\" in selected or selected.startswith("/"):
        _fail("invalid.path", path, "path is not a portable relative key")
    parts = selected.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        _fail("invalid.path", path, "path is not normalized and contained")
    if len(parts[0]) >= 2 and parts[0][1] == ":":
        _fail("invalid.path", path, "path contains a platform drive prefix")
    return selected


@dataclass(frozen=True, slots=True)
class ArtifactPin:
    """Identify one logical artifact and its exact materialization."""

    logical_id: str
    artifact_digest: str

    def as_dict(self) -> dict[str, str]:
        return {"artifactDigest": self.artifact_digest, "logicalId": self.logical_id}


@dataclass(frozen=True, slots=True)
class ArtifactInput:
    """Bind one logical input role to exact admitted bytes."""

    role: str
    logical_id: str
    artifact_digest: str

    @classmethod
    def from_dict(cls, value: object, *, path: str) -> Self:
        item = _closed_mapping(value, _INPUT_FIELDS, path=path)
        logical_id = _absolute_id(item["logicalId"], path=f"{path}/logicalId")
        _logical_digest(logical_id, path=f"{path}/logicalId")
        return cls(
            role=_role(item["role"], path=f"{path}/role"),
            logical_id=logical_id,
            artifact_digest=_digest(
                item["artifactDigest"], path=f"{path}/artifactDigest"
            ),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "artifactDigest": self.artifact_digest,
            "logicalId": self.logical_id,
            "role": self.role,
        }


@dataclass(frozen=True, slots=True)
class Producer:
    """Standard immutable identities for the publisher and product verifier."""

    product: str
    implementation_id: str
    verifier_id: str
    verifier_version: str
    verifier_implementation_id: str

    @classmethod
    def from_dict(cls, value: object, *, path: str) -> Self:
        item = _closed_mapping(value, _PRODUCER_FIELDS, path=path)
        return cls(
            product=_role(item["product"], path=f"{path}/product"),
            implementation_id=_implementation_id(
                item["implementationId"], path=f"{path}/implementationId"
            ),
            verifier_id=_absolute_id(item["verifierId"], path=f"{path}/verifierId"),
            verifier_version=_text(
                item["verifierVersion"], path=f"{path}/verifierVersion"
            ),
            verifier_implementation_id=_implementation_id(
                item["verifierImplementationId"],
                path=f"{path}/verifierImplementationId",
            ),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "implementationId": self.implementation_id,
            "product": self.product,
            "verifierId": self.verifier_id,
            "verifierImplementationId": self.verifier_implementation_id,
            "verifierVersion": self.verifier_version,
        }


@dataclass(frozen=True, slots=True)
class KnownLimit:
    """One artifact-attached limitation with exact supporting evidence."""

    code: str
    scope: str
    statement: str
    evidence_digests: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: object, *, path: str) -> Self:
        item = _closed_mapping(value, _KNOWN_LIMIT_FIELDS, path=path)
        evidence = tuple(
            _digest(entry, path=f"{path}/evidenceDigests/{index}")
            for index, entry in enumerate(
                _array(item["evidenceDigests"], path=f"{path}/evidenceDigests")
            )
        )
        if not evidence or evidence != tuple(
            sorted(set(evidence), key=_utf16_sort_key)
        ):
            _fail(
                "invalid.schema",
                f"{path}/evidenceDigests",
                "evidence digests must be nonempty, sorted, and distinct",
            )
        return cls(
            code=_role(item["code"], path=f"{path}/code"),
            scope=_role(item["scope"], path=f"{path}/scope"),
            statement=_text(item["statement"], path=f"{path}/statement"),
            evidence_digests=evidence,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "evidenceDigests": list(self.evidence_digests),
            "scope": self.scope,
            "statement": self.statement,
        }


@dataclass(frozen=True, slots=True)
class Supersedes:
    """Exact predecessor evidence for a product-owned current pointer."""

    logical_id: str
    artifact_digest: str
    reason: str

    @classmethod
    def from_dict(cls, value: object, *, path: str) -> Self:
        item = _closed_mapping(value, _SUPERSEDES_FIELDS, path=path)
        return cls(
            logical_id=_absolute_id(item["logicalId"], path=f"{path}/logicalId"),
            artifact_digest=_digest(
                item["artifactDigest"], path=f"{path}/artifactDigest"
            ),
            reason=_text(item["reason"], path=f"{path}/reason"),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "artifactDigest": self.artifact_digest,
            "logicalId": self.logical_id,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class DerivationRelation:
    """Optional shared description of a product-owned derivation."""

    processor_id: str
    processor_version: str
    processor_digest: str
    policy_id: str
    policy_version: str
    policy_digest: str
    parameters_digest: str
    partitioning_id: str
    partitioning_digest: str
    expected_output_roles: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: object, *, path: str = "relation") -> Self:
        item = _closed_mapping(value, _DERIVATION_RELATION_FIELDS, path=path)
        if item["relationKind"] != "derivation":
            _fail("invalid.schema", f"{path}/relationKind", "expected derivation")
        roles = _distinct_text_array(
            item["expectedOutputRoles"],
            path=f"{path}/expectedOutputRoles",
            role_values=True,
        )
        if roles != tuple(sorted(roles, key=_utf16_sort_key)):
            _fail(
                "invalid.schema",
                f"{path}/expectedOutputRoles",
                "expected output roles must be sorted",
            )
        return cls(
            processor_id=_absolute_id(item["processorId"], path=f"{path}/processorId"),
            processor_version=_text(
                item["processorVersion"], path=f"{path}/processorVersion"
            ),
            processor_digest=_digest(
                item["processorDigest"], path=f"{path}/processorDigest"
            ),
            policy_id=_absolute_id(item["policyId"], path=f"{path}/policyId"),
            policy_version=_text(item["policyVersion"], path=f"{path}/policyVersion"),
            policy_digest=_digest(item["policyDigest"], path=f"{path}/policyDigest"),
            parameters_digest=_digest(
                item["parametersDigest"], path=f"{path}/parametersDigest"
            ),
            partitioning_id=_absolute_id(
                item["partitioningId"], path=f"{path}/partitioningId"
            ),
            partitioning_digest=_digest(
                item["partitioningDigest"], path=f"{path}/partitioningDigest"
            ),
            expected_output_roles=roles,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "expectedOutputRoles": list(self.expected_output_roles),
            "parametersDigest": self.parameters_digest,
            "partitioningDigest": self.partitioning_digest,
            "partitioningId": self.partitioning_id,
            "policyDigest": self.policy_digest,
            "policyId": self.policy_id,
            "policyVersion": self.policy_version,
            "processorDigest": self.processor_digest,
            "processorId": self.processor_id,
            "processorVersion": self.processor_version,
            "relationKind": "derivation",
        }


@dataclass(frozen=True, slots=True)
class CompositionRelation:
    """Optional shared description of a reference-only composition."""

    merge_policy_id: str
    merge_policy_version: str
    merge_policy_digest: str
    total_order_key: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: object, *, path: str = "relation") -> Self:
        item = _closed_mapping(value, _COMPOSITION_RELATION_FIELDS, path=path)
        if item["relationKind"] != "composition":
            _fail("invalid.schema", f"{path}/relationKind", "expected composition")
        order = _distinct_text_array(
            item["totalOrderKey"], path=f"{path}/totalOrderKey"
        )
        return cls(
            merge_policy_id=_absolute_id(
                item["mergePolicyId"], path=f"{path}/mergePolicyId"
            ),
            merge_policy_version=_text(
                item["mergePolicyVersion"], path=f"{path}/mergePolicyVersion"
            ),
            merge_policy_digest=_digest(
                item["mergePolicyDigest"], path=f"{path}/mergePolicyDigest"
            ),
            total_order_key=order,
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "mergePolicyDigest": self.merge_policy_digest,
            "mergePolicyId": self.merge_policy_id,
            "mergePolicyVersion": self.merge_policy_version,
            "relationKind": "composition",
            "totalOrderKey": list(self.total_order_key),
        }


@dataclass(frozen=True, slots=True)
class MemberDescriptor:
    """Describe one payload member declared by exactly one manifest."""

    object_key: str | None
    role: str
    media_type: str
    byte_size: int
    sha256: str | None
    record_count: int | None = None
    schema_id: str | None = None
    blob_ref: str | None = None

    @classmethod
    def from_dict(cls, value: object, *, path: str) -> Self:
        if not isinstance(value, Mapping):
            _fail("invalid.schema", path, "member descriptor must be an object")
        fields = frozenset(value)
        allowed = (
            _MEMBER_COMMON_FIELDS
            | _MEMBER_OPTIONAL_FIELDS
            | {
                "blobRef",
                "objectKey",
                "sha256",
            }
        )
        if not _MEMBER_COMMON_FIELDS <= fields <= allowed:
            _fail(
                "invalid.schema",
                path,
                "member descriptor has missing or unknown fields",
            )
        local = "objectKey" in value or "sha256" in value
        external = "blobRef" in value
        if external == local or (local and not {"objectKey", "sha256"} <= fields):
            _fail(
                "invalid.schema",
                path,
                "member must have exactly one local objectKey/sha256 or external blobRef",
            )
        record_count = None
        if "recordCount" in value:
            record_count = _uint(value["recordCount"], path=f"{path}/recordCount")
        schema_id = None
        if "schemaId" in value:
            schema_id = _absolute_id(value["schemaId"], path=f"{path}/schemaId")
        media_type = _text(value["mediaType"], path=f"{path}/mediaType")
        try:
            media_type.encode("ascii")
        except UnicodeEncodeError:
            _fail("invalid.schema", f"{path}/mediaType", "media type must be ASCII")
        return cls(
            object_key=(
                validate_object_key(value["objectKey"], path=f"{path}/objectKey")
                if local
                else None
            ),
            role=_role(value["role"], path=f"{path}/role"),
            media_type=media_type,
            byte_size=_uint(value["byteSize"], path=f"{path}/byteSize"),
            sha256=_digest(value["sha256"], path=f"{path}/sha256") if local else None,
            record_count=record_count,
            schema_id=schema_id,
            blob_ref=(
                _digest(value["blobRef"], path=f"{path}/blobRef") if external else None
            ),
        )

    @property
    def location_key(self) -> tuple[str, str]:
        if self.object_key is not None:
            return ("object-key", self.object_key)
        if self.blob_ref is None:
            raise RuntimeError("member descriptor has no location")
        return ("blob-ref", self.blob_ref)

    def as_dict(self) -> dict[str, object]:
        value: dict[str, object] = {
            "byteSize": self.byte_size,
            "mediaType": self.media_type,
            "role": self.role,
        }
        if self.object_key is not None and self.sha256 is not None:
            value.update({"objectKey": self.object_key, "sha256": self.sha256})
        elif self.blob_ref is not None:
            value["blobRef"] = self.blob_ref
        else:
            raise ValueError("member descriptor must have one valid location")
        if self.record_count is not None:
            value["recordCount"] = self.record_count
        if self.schema_id is not None:
            value["schemaId"] = self.schema_id
        return value


@dataclass(frozen=True, slots=True)
class MemberManifestReference:
    """Pin one bounded manifest and its aggregate accounting."""

    manifest_id: str
    scope_kind: str
    scope_id: str
    object_key: str
    byte_size: int
    sha256: str
    member_count: int
    total_member_byte_size: int
    total_record_count: int

    @classmethod
    def from_dict(cls, value: object, *, path: str) -> Self:
        item = _closed_mapping(value, _MANIFEST_REFERENCE_FIELDS, path=path)
        scope_kind = _text(item["scopeKind"], path=f"{path}/scopeKind")
        if scope_kind not in _SCOPE_KINDS:
            _fail("invalid.schema", f"{path}/scopeKind", "scope kind is not registered")
        scope_id = _text(item["scopeId"], path=f"{path}/scopeId")
        manifest_id = _text(item["manifestId"], path=f"{path}/manifestId")
        if manifest_id != f"{scope_kind}:{scope_id}":
            _fail(
                "invalid.schema",
                f"{path}/manifestId",
                "manifest ID differs from its scope",
            )
        return cls(
            manifest_id=manifest_id,
            scope_kind=scope_kind,
            scope_id=scope_id,
            object_key=validate_object_key(item["objectKey"], path=f"{path}/objectKey"),
            byte_size=_uint(item["byteSize"], path=f"{path}/byteSize"),
            sha256=_digest(item["sha256"], path=f"{path}/sha256"),
            member_count=_uint(item["memberCount"], path=f"{path}/memberCount"),
            total_member_byte_size=_uint(
                item["totalMemberByteSize"], path=f"{path}/totalMemberByteSize"
            ),
            total_record_count=_uint(
                item["totalRecordCount"], path=f"{path}/totalRecordCount"
            ),
        )

    @classmethod
    def for_members(
        cls,
        *,
        scope_kind: str,
        scope_id: str,
        object_key: str,
        members: Sequence[MemberDescriptor],
    ) -> tuple[Self, bytes]:
        """Build one canonical manifest reference and its bytes."""

        output = io.BytesIO()
        reference = write_member_manifest(
            output,
            scope_kind=scope_kind,
            scope_id=scope_id,
            object_key=object_key,
            members=sorted(
                members,
                key=lambda member: tuple(
                    _utf16_sort_key(part) for part in member.location_key
                ),
            ),
        )
        return reference, output.getvalue()

    def as_dict(self) -> dict[str, object]:
        return {
            "byteSize": self.byte_size,
            "manifestId": self.manifest_id,
            "memberCount": self.member_count,
            "objectKey": self.object_key,
            "scopeId": self.scope_id,
            "scopeKind": self.scope_kind,
            "sha256": self.sha256,
            "totalMemberByteSize": self.total_member_byte_size,
            "totalRecordCount": self.total_record_count,
        }


@runtime_checkable
class MemberSource(Protocol):
    """Open immutable artifact members without choosing a storage provider."""

    def keys(self) -> Iterable[str]: ...

    def open(self, object_key: str) -> AbstractContextManager[BinaryIO]: ...


@dataclass(frozen=True, slots=True)
class ImmutableMemberReceipt:
    """Provider-issued identity for one immutable object-store version.

    The storage adapter, not the artifact producer, supplies this receipt at
    admission time.  Providers that cannot return an exact SHA-256 checksum,
    byte size, and immutable version identifier must use ``MemberSource.open``
    so Rulespec verifies the bytes directly.
    """

    object_key: str
    byte_size: int
    sha256: str
    version_id: str

    def __post_init__(self) -> None:
        selected_key = validate_object_key(
            self.object_key,
            path="memberReceipt/objectKey",
        )
        selected_size = _uint(self.byte_size, path="memberReceipt/byteSize")
        selected_digest = _digest(self.sha256, path="memberReceipt/sha256")
        selected_version = _text(
            self.version_id,
            path="memberReceipt/versionId",
        )
        if selected_version == "null" or any(
            character.isspace() for character in selected_version
        ):
            _fail(
                "invalid.schema",
                "memberReceipt/versionId",
                "version ID must name a non-null immutable provider version",
            )
        object.__setattr__(self, "object_key", selected_key)
        object.__setattr__(self, "byte_size", selected_size)
        object.__setattr__(self, "sha256", selected_digest)
        object.__setattr__(self, "version_id", selected_version)


@runtime_checkable
class ReceiptMemberSource(MemberSource, Protocol):
    """Resolve members through exact provider checksum and version metadata."""

    def receipt(self, object_key: str) -> ImmutableMemberReceipt: ...


@runtime_checkable
class BlobSource(Protocol):
    """Open an immutable external blob by its qualified content digest."""

    def open(self, blob_ref: str) -> AbstractContextManager[BinaryIO]: ...


@dataclass(frozen=True, slots=True)
class LocalFileState:
    """Identity of one local file during its shared digest verification."""

    device: int
    inode: int
    size: int
    modified_nanoseconds: int
    changed_nanoseconds: int
    mode: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> Self:
        return cls(
            device=value.st_dev,
            inode=value.st_ino,
            size=value.st_size,
            modified_nanoseconds=value.st_mtime_ns,
            changed_nanoseconds=value.st_ctime_ns,
            mode=value.st_mode,
        )

    def as_dict(self) -> dict[str, int]:
        return {
            "changedNanoseconds": self.changed_nanoseconds,
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
            "modifiedNanoseconds": self.modified_nanoseconds,
            "size": self.size,
        }


class LocalFileStateIndex(Mapping[str, LocalFileState]):
    """Disk-backed local file receipts captured by the digest pass.

    The verifier may admit millions of payload members. Keeping one Python
    object per member would make its memory grow with corpus size, so local
    receipts remain in the same temporary SQLite index used for exact
    membership. The connection owns its anonymous temporary database until the
    index is closed or collected.
    """

    __slots__ = ("_connection",)

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection: sqlite3.Connection | None = connection

    def _open_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("local file-state index is closed")
        return self._connection

    @staticmethod
    def _state(row: Sequence[int]) -> LocalFileState:
        return LocalFileState(*row)

    def __getitem__(self, object_key: str) -> LocalFileState:
        row = (
            self._open_connection()
            .execute(
                "SELECT device, inode, state_size, modified_nanoseconds, "
                "changed_nanoseconds, mode FROM expected "
                "WHERE kind = 'payload' AND object_key = ?",
                (object_key,),
            )
            .fetchone()
        )
        if row is None or any(value is None for value in row):
            raise KeyError(object_key)
        return self._state(row)

    def __iter__(self) -> Iterator[str]:
        rows = self._open_connection().execute(
            "SELECT object_key FROM expected WHERE kind = 'payload' ORDER BY object_key"
        )
        for row in rows:
            yield str(row[0])

    def __len__(self) -> int:
        row = (
            self._open_connection()
            .execute("SELECT COUNT(*) FROM expected WHERE kind = 'payload'")
            .fetchone()
        )
        return int(row[0]) if row is not None else 0

    def close(self) -> None:
        connection, self._connection = self._connection, None
        if connection is not None:
            connection.close()

    def __del__(self) -> None:
        self.close()


class PinnedLocalDirectory:
    """Pin one real directory and open child sources relative to its identity."""

    def __init__(
        self,
        parent_path: Path,
        *,
        expected_identity: tuple[int, int] | None = None,
    ) -> None:
        self._initialize(
            parent_path,
            label="parent directory",
            expected_identity=expected_identity,
        )

    @classmethod
    def _artifact_root(cls, root: Path) -> Self:
        pin = cls.__new__(cls)
        pin._initialize(root, label="artifact root", expected_identity=None)
        return pin

    def _initialize(
        self,
        path: Path,
        *,
        label: str,
        expected_identity: tuple[int, int] | None,
    ) -> None:
        if (
            not getattr(os, "O_NOFOLLOW", 0)
            or not getattr(os, "O_DIRECTORY", 0)
            or os.open not in os.supports_dir_fd
            or os.scandir not in os.supports_fd
        ):
            raise MemberSourceError(
                "local artifact verification requires descriptor-relative no-follow filesystem access"
            )
        unresolved = Path(path).absolute()
        try:
            descriptor = os.open(
                unresolved,
                os.O_RDONLY
                | getattr(os, "O_CLOEXEC", 0)
                | os.O_NOFOLLOW
                | os.O_DIRECTORY,
            )
        except FileNotFoundError as error:
            _fail("invalid.path", "$", f"{label} is unavailable: {error}")
        except OSError as error:
            if error.errno in (errno.ELOOP, errno.ENOTDIR):
                _fail("invalid.path", "$", f"{label} must be a real directory")
            raise MemberSourceError(
                f"cannot open {label} {unresolved}: {error}"
            ) from error
        try:
            root_state = os.fstat(descriptor)
            if not stat.S_ISDIR(root_state.st_mode):
                _fail("invalid.path", "$", f"{label} must be a real directory")
            identity = (root_state.st_dev, root_state.st_ino)
            if expected_identity is not None and identity != expected_identity:
                raise MemberSourceError(
                    f"{label} does not match its expected device and inode identity"
                )
            self._identity = identity
        finally:
            os.close(descriptor)
        self.path = unresolved
        self._label = label

    @staticmethod
    def _open_flags(*, directory: bool = False) -> int:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
        if directory:
            flags |= os.O_DIRECTORY
        return flags

    def _open_pinned(self) -> int:
        try:
            descriptor = os.open(self.path, self._open_flags(directory=True))
        except OSError as error:
            if error.errno in (errno.ELOOP, errno.ENOTDIR):
                _fail("invalid.path", "$", f"{self._label} must be a real directory")
            raise MemberSourceError(
                f"cannot open {self._label} {self.path}: {error}"
            ) from error
        try:
            state = os.fstat(descriptor)
        except BaseException:
            os.close(descriptor)
            raise
        if (state.st_dev, state.st_ino) != self._identity:
            os.close(descriptor)
            raise MemberSourceError(f"{self._label} changed after it was pinned")
        return descriptor

    @staticmethod
    def _open_relative(
        directory_fd: int, name: str, *, directory: bool, path: str
    ) -> int:
        try:
            return os.open(
                name,
                PinnedLocalDirectory._open_flags(directory=directory),
                dir_fd=directory_fd,
            )
        except FileNotFoundError as error:
            raise MemberNotFoundError(path) from error
        except OSError as error:
            if error.errno == errno.ELOOP:
                _fail("invalid.path", path, "member path traverses a symbolic link")
            if directory and error.errno == errno.ENOTDIR:
                _fail("invalid.path", path, "member path traverses a non-directory")
            raise MemberSourceError(
                f"cannot open artifact member {path}: {error}"
            ) from error

    def _open_child(self, child_key: str) -> int:
        descriptor = self._open_pinned()
        parts = child_key.split("/")
        try:
            for index, part in enumerate(parts):
                child_fd = self._open_relative(
                    descriptor,
                    part,
                    directory=True,
                    path="/".join(parts[: index + 1]),
                )
                os.close(descriptor)
                descriptor = child_fd
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def member_source(self, child_key: str) -> LocalMemberSource:
        """Return an artifact reader rooted at one pinned relative child."""

        return LocalMemberSource._from_pinned_parent(self, child_key)

    def blob_source(self, child_key: str) -> LocalBlobSource:
        """Return a content-addressed blob reader at one pinned relative child."""

        return LocalBlobSource._from_member_source(self.member_source(child_key))

    def move_child_directory_no_replace(
        self,
        source_name: str,
        destination_parent: PinnedLocalDirectory,
        destination_name: str,
        *,
        expected_source_identity: tuple[int, int] | None = None,
    ) -> None:
        """Move one real child directory through a kernel no-replace rename."""

        _move_pinned_child_directory_no_replace(
            self,
            source_name,
            destination_parent,
            destination_name,
            expected_source_identity=expected_source_identity,
        )

    def publish_child_directory_no_replace(
        self,
        source_name: str,
        destination_parent: PinnedLocalDirectory,
        destination_name: str,
        *,
        expected_source_identity: tuple[int, int] | None = None,
        wait_for_lock: bool = False,
    ) -> None:
        """Durably publish one real child directory without replacement."""

        _publish_pinned_child_directory_no_replace(
            self,
            source_name,
            destination_parent,
            destination_name,
            expected_source_identity=expected_source_identity,
            wait_for_lock=wait_for_lock,
        )


def _local_child_name(value: str, *, label: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or (len(value) >= 2 and value[1] == ":")
    ):
        raise ValueError(f"{label} must be one portable child name")
    return value


def _open_pinned_parent_pair(
    source_parent: PinnedLocalDirectory,
    destination_parent: PinnedLocalDirectory,
) -> tuple[int, int]:
    source_parent_fd = source_parent._open_pinned()
    try:
        destination_parent_fd = destination_parent._open_pinned()
    except BaseException:
        os.close(source_parent_fd)
        raise
    if os.fstat(source_parent_fd).st_dev != os.fstat(destination_parent_fd).st_dev:
        os.close(source_parent_fd)
        os.close(destination_parent_fd)
        raise OSError(
            errno.EXDEV,
            "publication source and destination use different filesystems",
        )
    return source_parent_fd, destination_parent_fd


def _require_local_directory_descriptor(descriptor: int, *, label: str) -> os.stat_result:
    try:
        state = os.fstat(descriptor)
    except OSError as error:
        raise MemberSourceError(f"cannot inspect {label}: {error}") from error
    if not stat.S_ISDIR(state.st_mode):
        raise MemberSourceError(f"{label} must be an open directory descriptor")
    return state


def _open_pinned_child_directory(
    parent_fd: int,
    name: str,
    *,
    expected_identity: tuple[int, int] | None,
) -> tuple[int, tuple[int, int]]:
    descriptor = PinnedLocalDirectory._open_relative(
        parent_fd,
        name,
        directory=True,
        path=name,
    )
    try:
        state = os.fstat(descriptor)
        identity = (state.st_dev, state.st_ino)
        if expected_identity is not None and identity != expected_identity:
            raise MemberSourceError("publication source changed after it was pinned")
        return descriptor, identity
    except BaseException:
        os.close(descriptor)
        raise


def _require_absent_local_child(parent_fd: int, name: str) -> None:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise FileExistsError(
        errno.EEXIST,
        "immutable publication destination already exists",
        name,
    )


def _require_published_local_identity(
    parent_fd: int,
    name: str,
    expected_identity: tuple[int, int],
) -> None:
    try:
        state = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as error:
        raise MemberSourceError("published directory is unavailable") from error
    if not stat.S_ISDIR(state.st_mode) or (state.st_dev, state.st_ino) != expected_identity:
        raise MemberSourceError("published directory changed during publication")


def _move_pinned_child_directory_no_replace(
    source_parent: PinnedLocalDirectory,
    source_name: str,
    destination_parent: PinnedLocalDirectory,
    destination_name: str,
    *,
    expected_source_identity: tuple[int, int] | None,
) -> None:
    source_parent_fd, destination_parent_fd = _open_pinned_parent_pair(
        source_parent,
        destination_parent,
    )
    try:
        move_child_directory_no_replace(
            source_parent_fd,
            destination_parent_fd,
            source_name,
            destination_name,
            expected_source_identity=expected_source_identity,
        )
    finally:
        os.close(source_parent_fd)
        os.close(destination_parent_fd)


def _publish_pinned_child_directory_no_replace(
    source_parent: PinnedLocalDirectory,
    source_name: str,
    destination_parent: PinnedLocalDirectory,
    destination_name: str,
    *,
    expected_source_identity: tuple[int, int] | None,
    wait_for_lock: bool = False,
) -> None:
    source_parent_fd, destination_parent_fd = _open_pinned_parent_pair(
        source_parent,
        destination_parent,
    )
    try:
        publish_child_directory_no_replace(
            source_parent_fd,
            destination_parent_fd,
            source_name,
            destination_name,
            expected_source_identity=expected_source_identity,
            wait_for_lock=wait_for_lock,
        )
    finally:
        os.close(source_parent_fd)
        os.close(destination_parent_fd)


def move_child_directory_no_replace(
    source_parent_fd: int,
    destination_parent_fd: int,
    source_name: str,
    destination_name: str,
    *,
    expected_source_identity: tuple[int, int] | None = None,
) -> None:
    """Move one child directory relative to already-pinned parent descriptors."""

    selected_source = _local_child_name(source_name, label="publication source")
    selected_destination = _local_child_name(
        destination_name,
        label="publication destination",
    )
    source_parent_state = _require_local_directory_descriptor(
        source_parent_fd,
        label="publication source parent",
    )
    destination_parent_state = _require_local_directory_descriptor(
        destination_parent_fd,
        label="publication destination parent",
    )
    if source_parent_state.st_dev != destination_parent_state.st_dev:
        raise OSError(
            errno.EXDEV,
            "publication source and destination use different filesystems",
        )
    if (
        source_parent_state.st_dev == destination_parent_state.st_dev
        and source_parent_state.st_ino == destination_parent_state.st_ino
        and selected_source == selected_destination
    ):
        raise ValueError("publication source and destination must be distinct")
    source_fd, source_identity = _open_pinned_child_directory(
        source_parent_fd,
        selected_source,
        expected_identity=expected_source_identity,
    )
    try:
        _require_absent_local_child(destination_parent_fd, selected_destination)
        _rename_local_directory_no_replace(
            source_parent_fd,
            selected_source,
            destination_parent_fd,
            selected_destination,
        )
        _require_published_local_identity(
            destination_parent_fd,
            selected_destination,
            source_identity,
        )
    finally:
        os.close(source_fd)


def publish_child_directory_no_replace(
    source_parent_fd: int,
    destination_parent_fd: int,
    source_name: str,
    destination_name: str,
    *,
    expected_source_identity: tuple[int, int] | None = None,
    wait_for_lock: bool = False,
) -> None:
    """Durably publish a child relative to already-pinned parent descriptors."""

    if fcntl is None:
        raise OSError(errno.ENOTSUP, "local publication requires POSIX advisory locks")
    selected_source = _local_child_name(source_name, label="publication source")
    selected_destination = _local_child_name(
        destination_name,
        label="publication destination",
    )
    source_parent_state = _require_local_directory_descriptor(
        source_parent_fd,
        label="publication source parent",
    )
    destination_parent_state = _require_local_directory_descriptor(
        destination_parent_fd,
        label="publication destination parent",
    )
    if source_parent_state.st_dev != destination_parent_state.st_dev:
        raise OSError(
            errno.EXDEV,
            "publication source and destination use different filesystems",
        )
    if (
        source_parent_state.st_ino == destination_parent_state.st_ino
        and selected_source == selected_destination
    ):
        raise ValueError("publication source and destination must be distinct")
    lock_fd = os.open(
        ".",
        PinnedLocalDirectory._open_flags(directory=True),
        dir_fd=destination_parent_fd,
    )
    source_fd: int | None = None
    locked = False
    try:
        try:
            lock_operation = fcntl.LOCK_EX
            if not wait_for_lock:
                lock_operation |= fcntl.LOCK_NB
            fcntl.flock(lock_fd, lock_operation)
        except BlockingIOError as error:
            raise BlockingIOError(
                errno.EWOULDBLOCK,
                "immutable publication destination is locked",
                selected_destination,
            ) from error
        locked = True
        source_fd, source_identity = _open_pinned_child_directory(
            source_parent_fd,
            selected_source,
            expected_identity=expected_source_identity,
        )
        _require_absent_local_child(destination_parent_fd, selected_destination)
        _sync_local_tree(source_fd, path=selected_source)
        _rename_local_directory_no_replace(
            source_parent_fd,
            selected_source,
            destination_parent_fd,
            selected_destination,
        )
        _require_published_local_identity(
            destination_parent_fd,
            selected_destination,
            source_identity,
        )
        os.fsync(source_parent_fd)
        os.fsync(destination_parent_fd)
    finally:
        if source_fd is not None:
            os.close(source_fd)
        if locked:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def _sync_local_tree(directory_fd: int, *, path: str) -> None:
    """Durably sync one real directory tree through no-follow descriptors."""

    try:
        entries = os.scandir(directory_fd)
    except OSError as error:
        raise MemberSourceError(f"cannot inspect publication tree {path}: {error}") from error
    with entries:
        for entry in entries:
            child_path = f"{path}/{entry.name}"
            try:
                state = entry.stat(follow_symlinks=False)
            except OSError as error:
                raise MemberSourceError(
                    f"cannot inspect publication member {child_path}: {error}"
                ) from error
            if stat.S_ISLNK(state.st_mode):
                _fail("invalid.path", child_path, "publication tree contains a symbolic link")
            if stat.S_ISDIR(state.st_mode):
                child_fd = PinnedLocalDirectory._open_relative(
                    directory_fd,
                    entry.name,
                    directory=True,
                    path=child_path,
                )
                try:
                    _sync_local_tree(child_fd, path=child_path)
                finally:
                    os.close(child_fd)
                continue
            if not stat.S_ISREG(state.st_mode):
                _fail("invalid.path", child_path, "publication tree contains a special file")
            member_fd = PinnedLocalDirectory._open_relative(
                directory_fd,
                entry.name,
                directory=False,
                path=child_path,
            )
            try:
                os.fsync(member_fd)
            finally:
                os.close(member_fd)
    os.fsync(directory_fd)


def _rename_local_directory_no_replace(
    source_parent_fd: int,
    source_name: str,
    destination_parent_fd: int,
    destination_name: str,
) -> None:
    """Use the host kernel's atomic no-replace directory rename."""

    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source_name)
    destination_bytes = os.fsencode(destination_name)
    if sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        rename = libc.renameatx_np
        rename.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        rename.restype = ctypes.c_int
        # RENAME_EXCL | RENAME_NOFOLLOW_ANY
        result = rename(
            source_parent_fd,
            source_bytes,
            destination_parent_fd,
            destination_bytes,
            0x4 | 0x10,
        )
    elif sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        rename = libc.renameat2
        rename.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        rename.restype = ctypes.c_int
        result = rename(
            source_parent_fd,
            source_bytes,
            destination_parent_fd,
            destination_bytes,
            1,  # RENAME_NOREPLACE
        )
    else:
        raise OSError(
            errno.ENOTSUP,
            "local publication requires an atomic no-replace directory rename",
        )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise FileExistsError(
            error_number,
            "immutable publication destination already exists",
            destination_name,
        )
    raise OSError(error_number, os.strerror(error_number), destination_name)


def publish_directory_no_replace(source: Path, destination: Path) -> None:
    """Durably publish one same-filesystem directory without replacement.

    An advisory lock on the pinned destination parent coordinates cooperative
    local writers. The operating system releases it after process death, and
    no sentinel pathname can poison a retry. The kernel rename remains the
    no-replace authority.
    """

    selected_source = Path(source).absolute()
    selected_destination = Path(destination).absolute()
    if selected_source == selected_destination:
        raise ValueError("publication source and destination must be distinct")

    source_parent = PinnedLocalDirectory(selected_source.parent)
    destination_parent = PinnedLocalDirectory(selected_destination.parent)
    source_parent.publish_child_directory_no_replace(
        selected_source.name,
        destination_parent,
        selected_destination.name,
    )


class LocalMemberSource:
    """Read one materialized artifact directory without following links."""

    _open_relative = staticmethod(PinnedLocalDirectory._open_relative)

    def __init__(self, root: Path) -> None:
        self._parent = PinnedLocalDirectory._artifact_root(root)
        self._child_key: str | None = None
        self._root_identity = self._parent._identity
        self.root = self._parent.path

    @classmethod
    def _from_pinned_parent(
        cls, parent: PinnedLocalDirectory, child_key: str
    ) -> Self:
        selected = validate_object_key(child_key, path="childKey")
        source = cls.__new__(cls)
        source._parent = parent
        source._child_key = selected
        source.root = parent.path.joinpath(*selected.split("/"))
        try:
            descriptor = parent._open_child(selected)
        except MemberNotFoundError as error:
            _fail("invalid.path", "$", f"artifact root is unavailable: {error}")
        try:
            state = os.fstat(descriptor)
            if not stat.S_ISDIR(state.st_mode):
                _fail("invalid.path", "$", "artifact root must be a real directory")
            source._root_identity = (state.st_dev, state.st_ino)
        finally:
            os.close(descriptor)
        return source

    def _open_root(self) -> int:
        if self._child_key is None:
            return self._parent._open_pinned()
        try:
            descriptor = self._parent._open_child(self._child_key)
        except MemberNotFoundError as error:
            raise MemberSourceError(
                f"cannot open artifact root {self.root}: {error}"
            ) from error
        try:
            state = os.fstat(descriptor)
        except BaseException:
            os.close(descriptor)
            raise
        if (state.st_dev, state.st_ino) != self._root_identity:
            os.close(descriptor)
            raise MemberSourceError(
                "artifact root changed after the member source was created"
            )
        return descriptor

    def keys(self) -> Iterator[str]:
        def visit(directory_fd: int, prefix: tuple[str, ...]) -> Iterator[str]:
            try:
                entries = os.scandir(directory_fd)
            except OSError as error:
                raise MemberSourceError(
                    f"cannot list artifact directory {'/'.join(prefix) or '.'}: {error}"
                ) from error
            with entries:
                for entry in entries:
                    key = "/".join((*prefix, entry.name))
                    validate_object_key(key, path=key)
                    try:
                        state = entry.stat(follow_symlinks=False)
                    except OSError as error:
                        raise MemberSourceError(
                            f"cannot inspect artifact member {key}: {error}"
                        ) from error
                    if stat.S_ISLNK(state.st_mode):
                        _fail("invalid.path", key, "artifact contains a symbolic link")
                    if stat.S_ISDIR(state.st_mode):
                        child_fd = self._open_relative(
                            directory_fd,
                            entry.name,
                            directory=True,
                            path=key,
                        )
                        try:
                            yield from visit(child_fd, (*prefix, entry.name))
                        finally:
                            os.close(child_fd)
                    elif stat.S_ISREG(state.st_mode):
                        yield key
                    else:
                        _fail("invalid.path", key, "artifact contains a special file")

        root_fd = self._open_root()
        try:
            yield from visit(root_fd, ())
        finally:
            os.close(root_fd)

    @contextmanager
    def open(self, object_key: str) -> Iterator[BinaryIO]:
        selected = validate_object_key(object_key, path=object_key)

        member_fd = self._open_member(selected)
        try:
            stream = os.fdopen(member_fd, "rb", closefd=True)
        except BaseException:
            os.close(member_fd)
            raise
        try:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                _fail("invalid.path", selected, "member is not a regular file")
            yield stream
            after = os.fstat(stream.fileno())
            reopened_fd = self._open_member(selected)
            try:
                current = os.fstat(reopened_fd)
            finally:
                os.close(reopened_fd)
            before_state = LocalFileState.from_stat(before)
            after_state = LocalFileState.from_stat(after)
            current_state = LocalFileState.from_stat(current)
            if before_state != after_state or after_state != current_state:
                _fail(
                    "invalid.member-digest",
                    selected,
                    "member changed while it was read",
                )
        finally:
            stream.close()

    def _open_member(self, selected: str) -> int:
        """Open one normalized object key from the pinned root descriptor."""

        parts = selected.split("/")
        directory_fd = self._open_root()
        try:
            for index, part in enumerate(parts[:-1]):
                child_fd = self._open_relative(
                    directory_fd,
                    part,
                    directory=True,
                    path="/".join(parts[: index + 1]),
                )
                os.close(directory_fd)
                directory_fd = child_fd
            member_fd = self._open_relative(
                directory_fd,
                parts[-1],
                directory=False,
                path=selected,
            )
        finally:
            os.close(directory_fd)
        return member_fd


class LocalBlobSource:
    """Read blobs stored as ``sha256/<hex>`` under one local directory."""

    def __init__(self, root: Path) -> None:
        self._source = LocalMemberSource(root)

    @classmethod
    def _from_member_source(cls, source: LocalMemberSource) -> Self:
        blob_source = cls.__new__(cls)
        blob_source._source = source
        return blob_source

    @contextmanager
    def open(self, blob_ref: str) -> Iterator[BinaryIO]:
        selected = _digest(blob_ref, path="blobRef")
        with self._source.open(f"sha256/{selected.removeprefix('sha256:')}") as stream:
            digest = hashlib.sha256()
            while block := stream.read(DEFAULT_READ_CHUNK_BYTES):
                digest.update(block)
            if "sha256:" + digest.hexdigest() != selected:
                _fail(
                    "invalid.member-digest",
                    selected,
                    "local blob bytes differ from their content address",
                )
            stream.seek(0)
            yield stream


class _CanonicalArrayStream:
    def __init__(
        self,
        stream: BinaryIO,
        *,
        path: str,
        byte_limit: int,
        byte_limit_code: str,
        chunk_bytes: int,
        prefix: bytes = b"",
        suffix: bytes = b"",
    ) -> None:
        self._stream = stream
        self._path = path
        self._byte_limit = byte_limit
        self._byte_limit_code = byte_limit_code
        self._chunk_bytes = chunk_bytes
        self._prefix = prefix
        self._suffix = suffix
        self.byte_size = 0
        self.sha256 = ""

    def __iter__(self) -> Iterator[Any]:
        digest = hashlib.sha256()
        utf8 = codecs.getincrementaldecoder("utf-8")()
        decoder = json.JSONDecoder(
            object_pairs_hook=_reject_duplicate_keys,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
        buffer = ""
        position = 0
        eof = False

        def fill() -> bool:
            nonlocal buffer, eof
            raw = self._stream.read(self._chunk_bytes)
            if raw:
                self.byte_size += len(raw)
                if self.byte_size > self._byte_limit:
                    _fail(
                        self._byte_limit_code,
                        self._path,
                        "member manifest exceeds its byte limit",
                    )
                digest.update(raw)
                try:
                    buffer += utf8.decode(raw, final=False)
                except UnicodeError as error:
                    _fail(
                        "invalid.manifest",
                        self._path,
                        f"manifest is not UTF-8: {error}",
                    )
                return True
            if not eof:
                eof = True
                try:
                    buffer += utf8.decode(b"", final=True)
                except UnicodeError as error:
                    _fail(
                        "invalid.manifest",
                        self._path,
                        f"manifest is not UTF-8: {error}",
                    )
            return False

        try:
            try:
                expected_prefix = self._prefix.decode("utf-8")
                expected_suffix = self._suffix.decode("utf-8")
            except UnicodeError as error:
                raise RuntimeError("generated manifest framing is not UTF-8") from error
            while len(buffer) < len(expected_prefix) + 1 and fill():
                pass
            if not buffer.startswith(expected_prefix):
                _fail("invalid.manifest", self._path, "member manifest header differs")
            position = len(expected_prefix)
            if position >= len(buffer) or buffer[position] != "[":
                _fail(
                    "invalid.manifest",
                    self._path,
                    "member manifest has no members array",
                )
            position += 1
            first = True
            while True:
                while position >= len(buffer) and fill():
                    pass
                if position >= len(buffer):
                    _fail(
                        "invalid.manifest", self._path, "member manifest is truncated"
                    )
                if first and buffer[position] == "]":
                    position += 1
                    break
                if not first:
                    if buffer[position] == "]":
                        position += 1
                        break
                    if buffer[position] != ",":
                        _fail(
                            "invalid.manifest",
                            self._path,
                            "member manifest is not canonical",
                        )
                    position += 1
                    while position >= len(buffer) and fill():
                        pass
                start = position
                while True:
                    try:
                        value, end = decoder.raw_decode(buffer, position)
                    except ArtifactVerificationError as error:
                        _fail("invalid.manifest", self._path, error.issue.message)
                    except (json.JSONDecodeError, ValueError) as error:
                        if fill():
                            continue
                        _fail(
                            "invalid.manifest",
                            self._path,
                            f"manifest entry is invalid: {error}",
                        )
                    break
                raw_value = buffer[start:end]
                try:
                    expected = canonical_json_bytes(value).decode("utf-8")
                except ArtifactVerificationError as error:
                    _fail("invalid.manifest", self._path, error.issue.message)
                if expected != raw_value:
                    _fail(
                        "invalid.manifest",
                        self._path,
                        "manifest entry is not canonical JSON",
                    )
                yield value
                first = False
                position = end
                if position > self._chunk_bytes * 2:
                    buffer = buffer[position:]
                    position = 0
            while fill():
                pass
            if buffer[position:] != expected_suffix:
                _fail("invalid.manifest", self._path, "member manifest footer differs")
        finally:
            self.sha256 = "sha256:" + digest.hexdigest()


@dataclass(frozen=True, slots=True)
class VerifiedArtifact:
    """Expose one structurally verified artifact and its closed members."""

    root: Mapping[str, Any]
    pin: ArtifactPin
    inputs: tuple[ArtifactInput, ...]
    manifests: tuple[MemberManifestReference, ...]
    member_count: int
    total_member_byte_size: int
    total_record_count: int
    local_member_states: Mapping[str, LocalFileState] | None = None


@runtime_checkable
class SemanticVerifier(Protocol):
    """Apply product semantics after common structural verification."""

    def __call__(self, artifact: VerifiedArtifact, source: MemberSource) -> None: ...


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Return either one verified artifact or one deterministic issue."""

    artifact: VerifiedArtifact | None
    issues: tuple[VerificationIssue, ...]

    @property
    def code(self) -> str:
        return "valid" if not self.issues else self.issues[0].code


def _manifest_framing(reference: MemberManifestReference) -> tuple[bytes, bytes]:
    counts = canonical_json_bytes(
        {
            "memberCount": reference.member_count,
            "totalMemberByteSize": reference.total_member_byte_size,
            "totalRecordCount": reference.total_record_count,
        }
    )
    prefix = (
        b'{"counts":'
        + counts
        + b',"format":'
        + canonical_json_bytes(MEMBER_MANIFEST_FORMAT)
        + b',"formatVersion":'
        + canonical_json_bytes(MEMBER_MANIFEST_VERSION)
        + b',"manifestId":'
        + canonical_json_bytes(reference.manifest_id)
        + b',"members":'
    )
    suffix = (
        b',"scope":'
        + canonical_json_bytes({"id": reference.scope_id, "kind": reference.scope_kind})
        + b"}"
    )
    return prefix, suffix


def _write_all(stream: BinaryIO, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = stream.write(view)
        if written is None or written <= 0:
            raise MemberSourceError("manifest destination stopped accepting bytes")
        view = view[written:]


def write_member_manifest(
    stream: BinaryIO,
    *,
    scope_kind: str,
    scope_id: str,
    object_key: str,
    members: Iterable[MemberDescriptor],
    byte_limit: int = DEFAULT_MANIFEST_BYTE_LIMIT,
    spool_bytes: int = DEFAULT_MANIFEST_SPOOL_BYTES,
) -> MemberManifestReference:
    """Stream one sorted member iterator into a bounded canonical manifest.

    The descriptor array spools to disk after ``spool_bytes``. This permits a
    one-pass producer iterator while still writing aggregate counts before the
    array in canonical key order.
    """

    if scope_kind not in _SCOPE_KINDS:
        _fail("invalid.schema", "manifest/scopeKind", "scope kind is not registered")
    selected_scope = _text(scope_id, path="manifest/scopeId")
    selected_key = validate_object_key(object_key, path="manifest/objectKey")
    if byte_limit <= 0 or spool_bytes <= 0:
        raise ValueError("manifest byte and spool limits must be positive")
    member_count = 0
    total_member_byte_size = 0
    total_record_count = 0
    previous_key: tuple[str, str] | None = None
    with tempfile.SpooledTemporaryFile(max_size=spool_bytes, mode="w+b") as body:
        for index, raw_member in enumerate(members):
            member = MemberDescriptor.from_dict(
                raw_member.as_dict(),
                path=f"manifest/members/{index}",
            )
            location_key = member.location_key
            if previous_key is not None and tuple(
                _utf16_sort_key(part) for part in location_key
            ) <= tuple(_utf16_sort_key(part) for part in previous_key):
                _fail(
                    "invalid.manifest",
                    selected_key,
                    "producer members must be sorted and distinct",
                )
            if member_count:
                _write_all(body, b",")
            _write_all(body, canonical_json_bytes(member.as_dict()))
            previous_key = location_key
            member_count += 1
            total_member_byte_size += member.byte_size
            total_record_count += member.record_count or 0
            if body.tell() > byte_limit:
                _fail(
                    "invalid.limit",
                    selected_key,
                    "member manifest exceeds its byte limit",
                )

        placeholder = MemberManifestReference(
            manifest_id=f"{scope_kind}:{selected_scope}",
            scope_kind=scope_kind,
            scope_id=selected_scope,
            object_key=selected_key,
            byte_size=0,
            sha256="sha256:" + "0" * 64,
            member_count=member_count,
            total_member_byte_size=total_member_byte_size,
            total_record_count=total_record_count,
        )
        prefix, suffix = _manifest_framing(placeholder)
        byte_size = len(prefix) + 1 + body.tell() + 1 + len(suffix)
        if byte_size > byte_limit:
            _fail(
                "invalid.limit", selected_key, "member manifest exceeds its byte limit"
            )
        digest = hashlib.sha256()

        def emit(payload: bytes) -> None:
            digest.update(payload)
            _write_all(stream, payload)

        emit(prefix)
        emit(b"[")
        body.seek(0)
        while chunk := body.read(DEFAULT_READ_CHUNK_BYTES):
            emit(chunk)
        emit(b"]")
        emit(suffix)

    reference = MemberManifestReference(
        manifest_id=placeholder.manifest_id,
        scope_kind=placeholder.scope_kind,
        scope_id=placeholder.scope_id,
        object_key=placeholder.object_key,
        byte_size=byte_size,
        sha256="sha256:" + digest.hexdigest(),
        member_count=member_count,
        total_member_byte_size=total_member_byte_size,
        total_record_count=total_record_count,
    )
    MemberManifestReference.from_dict(reference.as_dict(), path="memberManifest")
    return reference


def expected_logical_digest(root: Mapping[str, Any]) -> str:
    """Derive the namespace-independent logical digest suffix."""

    kind = _text(root.get("kind"), path="$/kind")
    _role(kind, path="$/kind")
    inputs = tuple(
        ArtifactInput.from_dict(value, path=f"$/inputs/{index}")
        for index, value in enumerate(_array(root.get("inputs"), path="$/inputs"))
    )
    logical_inputs = [
        {
            "logicalDigest": _logical_digest(item.logical_id, path="$/inputs"),
            "role": item.role,
        }
        for item in inputs
    ]
    payload = {
        "format": root.get("format"),
        "formatVersion": root.get("formatVersion"),
        "kind": kind,
        "logicalInputs": logical_inputs,
        "spec": root.get("spec"),
    }
    return sha256_digest(payload).removeprefix("sha256:")


def expected_logical_id(
    root: Mapping[str, Any], *, namespace: str | None = None
) -> str:
    """Derive one logical ID, preserving a valid declared namespace by default."""

    kind = _role(root.get("kind"), path="$/kind")
    if namespace is None and isinstance(root.get("logicalId"), str):
        namespace = str(root["logicalId"])[:-64]
    selected = namespace or f"urn:spicy:artifact:{kind}:"
    if (
        not selected.startswith("urn:")
        or not selected.endswith(":")
        or kind not in selected
    ):
        _fail(
            "invalid.identity",
            "$/logicalId",
            "logical ID namespace must be an absolute URN ending in ':' and include kind",
        )
    return selected + expected_logical_digest(root)


def expected_artifact_digest(root: Mapping[str, Any]) -> str:
    """Derive physical identity from the complete root without self-reference."""

    payload = dict(root)
    payload.pop("artifactDigest", None)
    return sha256_digest(payload)


def stamp_root(
    root: Mapping[str, Any], *, logical_id_namespace: str | None = None
) -> dict[str, Any]:
    """Return a root copy carrying both derived identities."""

    stamped = deepcopy(dict(root))
    stamped.pop("logicalId", None)
    stamped.pop("artifactDigest", None)
    stamped["logicalId"] = expected_logical_id(stamped, namespace=logical_id_namespace)
    stamped["artifactDigest"] = expected_artifact_digest(stamped)
    _validate_root(stamped)
    return stamped


def _validate_root(
    root: Mapping[str, Any],
) -> tuple[tuple[ArtifactInput, ...], tuple[MemberManifestReference, ...]]:
    fields = frozenset(root)
    if (
        not _ROOT_REQUIRED_FIELDS
        <= fields
        <= _ROOT_REQUIRED_FIELDS | _ROOT_OPTIONAL_FIELDS
    ):
        _fail(
            "invalid.schema",
            "$",
            "root has missing or unknown fields",
        )
    item = root
    if item["format"] != FORMAT or item["formatVersion"] != FORMAT_VERSION:
        _fail("invalid.format", "$", "artifact format or exact version is unsupported")
    _role(item["kind"], path="$/kind")
    _mapping(item["spec"], path="$/spec")
    Producer.from_dict(item["producer"], path="$/producer")
    inputs = tuple(
        ArtifactInput.from_dict(value, path=f"$/inputs/{index}")
        for index, value in enumerate(_array(item["inputs"], path="$/inputs"))
    )
    input_keys = tuple(
        (entry.role, _logical_digest(entry.logical_id, path="$/inputs"))
        for entry in inputs
    )
    ordered_input_keys = tuple(
        sorted(
            input_keys,
            key=lambda value: tuple(_utf16_sort_key(part) for part in value),
        )
    )
    if input_keys != ordered_input_keys or len(input_keys) != len(set(input_keys)):
        _fail(
            "invalid.schema",
            "$/inputs",
            "inputs must be sorted and distinct by role and logical digest",
        )

    counts = _closed_mapping(item["counts"], _COMMON_COUNT_FIELDS, path="$/counts")
    for name in _COMMON_COUNT_FIELDS:
        _uint(counts[name], path=f"$/counts/{name}")
    if "knownLimits" in item:
        limits = tuple(
            KnownLimit.from_dict(value, path=f"$/knownLimits/{index}")
            for index, value in enumerate(
                _array(item["knownLimits"], path="$/knownLimits")
            )
        )
        limit_keys = tuple((limit.scope, limit.code) for limit in limits)
        if (
            not limits
            or limit_keys
            != tuple(
                sorted(
                    limit_keys,
                    key=lambda value: tuple(_utf16_sort_key(part) for part in value),
                )
            )
            or len(limit_keys) != len(set(limit_keys))
        ):
            _fail(
                "invalid.schema",
                "$/knownLimits",
                "known limits must be nonempty, sorted, and distinct",
            )
    if "supersedes" in item:
        Supersedes.from_dict(item["supersedes"], path="$/supersedes")

    manifests = tuple(
        MemberManifestReference.from_dict(value, path=f"$/memberManifests/{index}")
        for index, value in enumerate(
            _array(item["memberManifests"], path="$/memberManifests")
        )
    )
    manifest_order = [
        (entry.scope_kind, entry.scope_id, entry.object_key) for entry in manifests
    ]
    if manifest_order != sorted(
        manifest_order,
        key=lambda value: tuple(_utf16_sort_key(part) for part in value),
    ) or len(manifest_order) != len(set(manifest_order)):
        _fail(
            "invalid.schema",
            "$/memberManifests",
            "member manifests must be sorted and distinct",
        )

    logical_id = _absolute_id(item["logicalId"], path="$/logicalId")
    expected_logical = expected_logical_id(item)
    if logical_id != expected_logical:
        _fail(
            "invalid.identity",
            "$/logicalId",
            f"expected digest suffix {expected_logical[-64:]}",
        )
    artifact_digest = _digest(item["artifactDigest"], path="$/artifactDigest")
    expected_physical = expected_artifact_digest(item)
    if artifact_digest != expected_physical:
        _fail("invalid.identity", "$/artifactDigest", f"expected {expected_physical}")
    return inputs, manifests


def _read_bounded(
    source: MemberSource, object_key: str, *, byte_limit: int, code: str
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
        with source.open(object_key) as stream:
            while chunk := stream.read(DEFAULT_READ_CHUNK_BYTES):
                total += len(chunk)
                if total > byte_limit:
                    _fail(
                        "invalid.limit", object_key, f"file exceeds {byte_limit} bytes"
                    )
                chunks.append(chunk)
    except MemberNotFoundError:
        _fail(
            "invalid.membership-missing", object_key, "declared artifact file is absent"
        )
    try:
        return b"".join(chunks)
    except MemoryError:
        _fail(code, object_key, "file could not be read within its declared bound")


def _hash_member(
    source: MemberSource,
    member: MemberDescriptor,
    *,
    blob_source: BlobSource | None,
) -> LocalFileState | None:
    digest = hashlib.sha256()
    byte_size = 0
    local_state: LocalFileState | None = None
    if member.object_key is not None:
        selected_source: MemberSource | BlobSource = source
        location = member.object_key
        expected_digest = member.sha256
        if isinstance(source, ReceiptMemberSource):
            try:
                receipt = source.receipt(location)
            except MemberNotFoundError:
                _fail(
                    "invalid.membership-missing",
                    location,
                    "declared payload is absent",
                )
            if not isinstance(receipt, ImmutableMemberReceipt):
                _fail(
                    "invalid.member-digest",
                    location,
                    "member source returned an invalid immutable receipt",
                )
            if (
                receipt.object_key != location
                or receipt.byte_size != member.byte_size
                or receipt.sha256 != expected_digest
            ):
                _fail(
                    "invalid.member-digest",
                    location,
                    "immutable member receipt differs from its descriptor",
                )
            return None
    else:
        if blob_source is None or member.blob_ref is None:
            _fail(
                "invalid.membership-missing",
                member.blob_ref or "blobRef",
                "external member requires an injected BlobSource",
            )
        selected_source = blob_source
        location = member.blob_ref
        expected_digest = member.blob_ref
    try:
        with selected_source.open(location) as stream:
            while block := stream.read(DEFAULT_READ_CHUNK_BYTES):
                byte_size += len(block)
                if byte_size > member.byte_size:
                    _fail(
                        "invalid.member-digest",
                        location,
                        "member exceeds its declared size",
                    )
                digest.update(block)
            if member.object_key is not None and isinstance(source, LocalMemberSource):
                local_state = LocalFileState.from_stat(os.fstat(stream.fileno()))
    except MemberNotFoundError:
        _fail("invalid.membership-missing", location, "declared payload is absent")
    actual_digest = "sha256:" + digest.hexdigest()
    if byte_size != member.byte_size or actual_digest != expected_digest:
        _fail("invalid.member-digest", location, "member size or digest differs")
    return local_state


@contextmanager
def _open_required(source: MemberSource, object_key: str) -> Iterator[BinaryIO]:
    try:
        with source.open(object_key) as stream:
            yield stream
    except MemberNotFoundError:
        _fail(
            "invalid.membership-missing", object_key, "declared artifact file is absent"
        )


def describe_member(
    source: MemberSource,
    *,
    object_key: str,
    role: str,
    media_type: str,
    record_count: int | None = None,
    schema_id: str | None = None,
) -> MemberDescriptor:
    """Hash one producer-written payload through its injected member source.

    Producers retain ownership of storage and publication. This helper owns
    only the common descriptor shape and hashes the member in bounded reads.
    """

    selected_key = validate_object_key(object_key, path="member/objectKey")
    digest = hashlib.sha256()
    byte_size = 0
    with source.open(selected_key) as stream:
        while block := stream.read(DEFAULT_READ_CHUNK_BYTES):
            byte_size += len(block)
            digest.update(block)
    value: dict[str, object] = {
        "byteSize": byte_size,
        "mediaType": media_type,
        "objectKey": selected_key,
        "role": role,
        "sha256": "sha256:" + digest.hexdigest(),
    }
    if record_count is not None:
        value["recordCount"] = record_count
    if schema_id is not None:
        value["schemaId"] = schema_id
    return MemberDescriptor.from_dict(value, path="member")


def describe_member_from_receipt(
    *,
    object_key: str | None = None,
    blob_ref: str | None = None,
    role: str,
    media_type: str,
    byte_size: int,
    sha256: str | None = None,
    record_count: int | None = None,
    schema_id: str | None = None,
) -> MemberDescriptor:
    """Validate one immutable producer receipt without rereading its bytes."""

    value: dict[str, object] = {
        "byteSize": byte_size,
        "mediaType": media_type,
        "role": role,
    }
    if object_key is not None:
        value["objectKey"] = object_key
    if sha256 is not None:
        value["sha256"] = sha256
    if blob_ref is not None:
        value["blobRef"] = blob_ref
    if record_count is not None:
        value["recordCount"] = record_count
    if schema_id is not None:
        value["schemaId"] = schema_id
    return MemberDescriptor.from_dict(value, path="member")


def build_artifact_root(
    *,
    kind: str,
    spec: Mapping[str, Any],
    producer: Producer,
    inputs: Sequence[ArtifactInput] = (),
    manifests: Sequence[MemberManifestReference] = (),
    known_limits: Sequence[KnownLimit] = (),
    supersedes: Supersedes | None = None,
    logical_id_namespace: str | None = None,
) -> dict[str, Any]:
    """Build and stamp the one closed artifact root from sealed manifests.

    The function derives aggregate counts from the manifest references. It
    sorts inputs and manifests into their required deterministic order, so
    product publishers never reproduce root assembly or identity logic.
    """

    ordered_inputs = tuple(
        sorted(
            inputs,
            key=lambda item: (
                _utf16_sort_key(item.role),
                _utf16_sort_key(
                    _logical_digest(item.logical_id, path="build/inputs/logicalId")
                ),
            ),
        )
    )
    ordered_manifests = tuple(
        sorted(
            manifests,
            key=lambda item: (
                _utf16_sort_key(item.scope_kind),
                _utf16_sort_key(item.scope_id),
                _utf16_sort_key(item.object_key),
            ),
        )
    )
    ordered_limits = tuple(
        sorted(
            known_limits,
            key=lambda item: (_utf16_sort_key(item.scope), _utf16_sort_key(item.code)),
        )
    )
    root: dict[str, Any] = {
        "counts": {
            "manifestCount": len(ordered_manifests),
            "memberCount": sum(item.member_count for item in ordered_manifests),
            "totalMemberByteSize": sum(
                item.total_member_byte_size for item in ordered_manifests
            ),
            "totalRecordCount": sum(
                item.total_record_count for item in ordered_manifests
            ),
        },
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
        "inputs": [item.as_dict() for item in ordered_inputs],
        "kind": kind,
        "memberManifests": [item.as_dict() for item in ordered_manifests],
        "producer": producer.as_dict(),
        "spec": deepcopy(dict(spec)),
    }
    if ordered_limits:
        root["knownLimits"] = [item.as_dict() for item in ordered_limits]
    if supersedes is not None:
        root["supersedes"] = supersedes.as_dict()
    return stamp_root(root, logical_id_namespace=logical_id_namespace)


def _iter_manifest_members(
    source: MemberSource,
    reference: MemberManifestReference,
    *,
    manifest_byte_limit: int,
) -> Iterator[MemberDescriptor]:
    with _open_required(source, reference.object_key) as stream:
        effective_limit = min(manifest_byte_limit, reference.byte_size)
        prefix, suffix = _manifest_framing(reference)
        values = _CanonicalArrayStream(
            stream,
            path=reference.object_key,
            byte_limit=effective_limit,
            byte_limit_code=(
                "invalid.limit"
                if manifest_byte_limit < reference.byte_size
                else "invalid.manifest"
            ),
            chunk_bytes=DEFAULT_READ_CHUNK_BYTES,
            prefix=prefix,
            suffix=suffix,
        )
        previous_member_key: tuple[str, str] | None = None
        member_count = 0
        total_member_byte_size = 0
        total_record_count = 0
        for index, value in enumerate(values):
            member = MemberDescriptor.from_dict(
                value,
                path=f"{reference.object_key}/{index}",
            )
            member_key = member.location_key
            if previous_member_key is not None and tuple(
                _utf16_sort_key(part) for part in member_key
            ) <= tuple(_utf16_sort_key(part) for part in previous_member_key):
                _fail(
                    "invalid.manifest",
                    reference.object_key,
                    "members must be sorted and distinct within their manifest",
                )
            previous_member_key = member_key
            member_count += 1
            total_member_byte_size += member.byte_size
            total_record_count += member.record_count or 0
            yield member
    if values.byte_size != reference.byte_size or values.sha256 != reference.sha256:
        _fail(
            "invalid.manifest", reference.object_key, "manifest size or digest differs"
        )
    if (
        member_count,
        total_member_byte_size,
        total_record_count,
    ) != (
        reference.member_count,
        reference.total_member_byte_size,
        reference.total_record_count,
    ):
        _fail("invalid.statistics", reference.object_key, "manifest accounting differs")


def iter_member_descriptors(
    artifact: VerifiedArtifact,
    source: MemberSource,
    *,
    manifest_byte_limit: int = DEFAULT_MANIFEST_BYTE_LIMIT,
) -> Iterator[MemberDescriptor]:
    """Re-stream verified member descriptors for product semantic checks."""

    for reference in artifact.manifests:
        yield from _iter_manifest_members(
            source,
            reference,
            manifest_byte_limit=manifest_byte_limit,
        )


def validate_derivation_relation(
    artifact: VerifiedArtifact,
    source: MemberSource,
    relation: DerivationRelation,
    *,
    manifest_byte_limit: int = DEFAULT_MANIFEST_BYTE_LIMIT,
) -> None:
    """Check the product-neutral input and role rules for one derivation."""

    selected = DerivationRelation.from_dict(relation.as_dict())
    if not artifact.inputs:
        _fail("invalid.schema", "$/inputs", "a derivation requires an input")
    if artifact.member_count == 0:
        _fail(
            "invalid.schema",
            "$/memberManifests",
            "a derivation requires output members",
        )
    observed_roles = {
        member.role
        for member in iter_member_descriptors(
            artifact,
            source,
            manifest_byte_limit=manifest_byte_limit,
        )
    }
    expected_roles = set(selected.expected_output_roles)
    if observed_roles != expected_roles:
        _fail(
            "invalid.schema",
            "relation/expectedOutputRoles",
            f"expected roles {sorted(expected_roles)}, observed {sorted(observed_roles)}",
        )


def validate_composition_relation(
    artifact: VerifiedArtifact,
    relation: CompositionRelation,
) -> None:
    """Check the product-neutral input rules for one composition."""

    CompositionRelation.from_dict(relation.as_dict())
    if not artifact.inputs:
        _fail("invalid.schema", "$/inputs", "a composition requires member inputs")
    if any(item.role != "member" for item in artifact.inputs):
        _fail("invalid.schema", "$/inputs", "composition inputs must use role 'member'")


def _admit(
    source: MemberSource,
    *,
    blob_source: BlobSource | None,
    expected_pin: ArtifactPin | None,
    root_byte_limit: int,
    manifest_byte_limit: int,
    scratch_directory: Path | None,
) -> VerifiedArtifact:
    root_raw = _read_bounded(
        source,
        ROOT_OBJECT_KEY,
        byte_limit=root_byte_limit,
        code="invalid.root-syntax",
    )
    root = parse_canonical_json(root_raw)
    if not isinstance(root, Mapping):
        _fail("invalid.schema", "$", "artifact root must be an object")
    inputs, manifest_references = _validate_root(root)
    pin = ArtifactPin(
        logical_id=str(root["logicalId"]),
        artifact_digest=str(root["artifactDigest"]),
    )
    if expected_pin is not None and pin != expected_pin:
        _fail("invalid.identity", "$", "artifact differs from its external pin")

    index_path: Path | None = None
    index: sqlite3.Connection | None = None
    try:
        if scratch_directory is None:
            index = sqlite3.connect("", check_same_thread=False)
        else:
            selected_scratch = Path(scratch_directory)
            selected_scratch.mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(
                prefix="platform-artifact-members-",
                suffix=".sqlite3",
                dir=selected_scratch,
            )
            os.close(descriptor)
            index_path = Path(name)
            index = sqlite3.connect(index_path, check_same_thread=False)
        index.execute(
            "CREATE TABLE expected ("
            "location_key TEXT PRIMARY KEY, object_key TEXT, blob_ref TEXT, "
            "kind TEXT NOT NULL, observed INTEGER NOT NULL DEFAULT 0, "
            "role TEXT, media_type TEXT, byte_size INTEGER, sha256 TEXT, "
            "record_count INTEGER, schema_id TEXT, device INTEGER, inode INTEGER, "
            "state_size INTEGER, modified_nanoseconds INTEGER, changed_nanoseconds INTEGER, "
            "mode INTEGER)"
        )
        index.execute(
            "INSERT INTO expected (location_key, object_key, kind) VALUES (?, ?, 'protocol')",
            (f"object-key:{ROOT_OBJECT_KEY}", ROOT_OBJECT_KEY),
        )
        for reference in manifest_references:
            try:
                index.execute(
                    "INSERT INTO expected (location_key, object_key, kind) "
                    "VALUES (?, ?, 'protocol')",
                    (f"object-key:{reference.object_key}", reference.object_key),
                )
            except sqlite3.IntegrityError:
                _fail(
                    "invalid.manifest",
                    reference.object_key,
                    "manifest path is repeated",
                )

        member_count = 0
        total_member_byte_size = 0
        total_record_count = 0
        evidence_digests = {item.artifact_digest for item in inputs}
        for reference in manifest_references:
            for member in _iter_manifest_members(
                source,
                reference,
                manifest_byte_limit=manifest_byte_limit,
            ):
                try:
                    location_kind, location = member.location_key
                    kind = "payload" if member.object_key is not None else "blob"
                    index.execute(
                        "INSERT INTO expected "
                        "(location_key, object_key, blob_ref, kind, observed, role, media_type, "
                        "byte_size, sha256, record_count, schema_id) "
                        "VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)",
                        (
                            f"{location_kind}:{location}",
                            member.object_key,
                            member.blob_ref,
                            kind,
                            member.role,
                            member.media_type,
                            member.byte_size,
                            member.sha256,
                            member.record_count,
                            member.schema_id,
                        ),
                    )
                except sqlite3.IntegrityError:
                    _fail(
                        "invalid.manifest",
                        location,
                        "payload overlaps a protocol file or another manifest",
                    )
                evidence_digests.add(member.sha256 or member.blob_ref or "")
                member_count += 1
                total_member_byte_size += member.byte_size
                total_record_count += member.record_count or 0

        for index_value, value in enumerate(root.get("knownLimits", ())):
            limit = KnownLimit.from_dict(value, path=f"$/knownLimits/{index_value}")
            if any(digest not in evidence_digests for digest in limit.evidence_digests):
                _fail(
                    "invalid.schema",
                    f"$/knownLimits/{index_value}/evidenceDigests",
                    "known-limit evidence must resolve to an input or member",
                )

        first_extra: str | None = None
        for raw_key in source.keys():  # noqa: SIM118 - MemberSource is not a Mapping
            object_key = validate_object_key(raw_key, path=str(raw_key))
            row = index.execute(
                "SELECT observed FROM expected WHERE location_key = ?",
                (f"object-key:{object_key}",),
            ).fetchone()
            if row is None or row[0]:
                first_extra = (
                    min(first_extra, object_key) if first_extra else object_key
                )
                continue
            index.execute(
                "UPDATE expected SET observed = 1 WHERE object_key = ?",
                (object_key,),
            )
        missing = index.execute(
            "SELECT object_key FROM expected WHERE kind IN ('protocol', 'payload') "
            "AND observed = 0 ORDER BY object_key LIMIT 1"
        ).fetchone()
        if missing is not None:
            _fail(
                "invalid.membership-missing",
                missing[0],
                "declared artifact file is absent",
            )
        if first_extra is not None:
            _fail(
                "invalid.membership-extra",
                first_extra,
                "artifact contains an undeclared file",
            )

        capture_local_states = isinstance(source, LocalMemberSource)
        rows = index.execute(
            "SELECT object_key, role, media_type, byte_size, sha256, record_count, schema_id, "
            "blob_ref FROM expected WHERE kind IN ('payload', 'blob') ORDER BY location_key"
        )
        for row in rows:
            member = MemberDescriptor(*row)
            state = _hash_member(source, member, blob_source=blob_source)
            if capture_local_states and member.object_key is not None:
                if state is None:
                    raise RuntimeError(
                        "local member admission did not capture a file state"
                    )
                index.execute(
                    "UPDATE expected SET device = ?, inode = ?, state_size = ?, "
                    "modified_nanoseconds = ?, changed_nanoseconds = ?, mode = ? "
                    "WHERE object_key = ?",
                    (
                        state.device,
                        state.inode,
                        state.size,
                        state.modified_nanoseconds,
                        state.changed_nanoseconds,
                        state.mode,
                        member.object_key,
                    ),
                )

        expected_counts = {
            "manifestCount": len(manifest_references),
            "memberCount": member_count,
            "totalMemberByteSize": total_member_byte_size,
            "totalRecordCount": total_record_count,
        }
        counts = _mapping(root["counts"], path="$/counts")
        for name, expected in expected_counts.items():
            if _uint(counts[name], path=f"$/counts/{name}") != expected:
                _fail("invalid.statistics", f"$/counts/{name}", f"expected {expected}")

        local_member_states: Mapping[str, LocalFileState] | None = None
        if capture_local_states:
            local_member_states = LocalFileStateIndex(index)
            index = None
        return VerifiedArtifact(
            root=root,
            pin=pin,
            inputs=inputs,
            manifests=manifest_references,
            member_count=member_count,
            total_member_byte_size=total_member_byte_size,
            total_record_count=total_record_count,
            local_member_states=local_member_states,
        )
    finally:
        try:
            if index is not None:
                index.close()
        finally:
            if index_path is not None:
                index_path.unlink(missing_ok=True)


def verify_artifact(
    source: MemberSource,
    *,
    blob_source: BlobSource | None = None,
    expected_pin: ArtifactPin | None = None,
    root_byte_limit: int = DEFAULT_ROOT_BYTE_LIMIT,
    manifest_byte_limit: int = DEFAULT_MANIFEST_BYTE_LIMIT,
    semantic_verifier: SemanticVerifier | None = None,
    scratch_directory: Path | None = None,
) -> VerificationResult:
    """Verify one artifact without choosing its storage implementation."""

    try:
        artifact = _admit(
            source,
            blob_source=blob_source,
            expected_pin=expected_pin,
            root_byte_limit=root_byte_limit,
            manifest_byte_limit=manifest_byte_limit,
            scratch_directory=scratch_directory,
        )
        if semantic_verifier is not None:
            semantic_verifier(artifact, source)
    except ArtifactVerificationError as error:
        return VerificationResult(None, (error.issue,))
    return VerificationResult(artifact, ())


def admit_artifact(
    source: MemberSource,
    *,
    blob_source: BlobSource | None = None,
    expected_pin: ArtifactPin | None = None,
    root_byte_limit: int = DEFAULT_ROOT_BYTE_LIMIT,
    manifest_byte_limit: int = DEFAULT_MANIFEST_BYTE_LIMIT,
    semantic_verifier: SemanticVerifier | None = None,
    scratch_directory: Path | None = None,
) -> VerifiedArtifact:
    """Verify one artifact and raise its deterministic issue on refusal.

    Raises:
        ArtifactVerificationError: Structural or identity verification fails.
    """

    artifact = _admit(
        source,
        blob_source=blob_source,
        expected_pin=expected_pin,
        root_byte_limit=root_byte_limit,
        manifest_byte_limit=manifest_byte_limit,
        scratch_directory=scratch_directory,
    )
    if semantic_verifier is not None:
        semantic_verifier(artifact, source)
    return artifact


__all__ = [
    "DIAGNOSTIC_CODES",
    "FORMAT",
    "FORMAT_VERSION",
    "MEMBER_MANIFEST_FORMAT",
    "MEMBER_MANIFEST_MEDIA_TYPE",
    "MEMBER_MANIFEST_VERSION",
    "ROOT_OBJECT_KEY",
    "ArtifactInput",
    "ArtifactPin",
    "ArtifactVerificationError",
    "BlobSource",
    "CanonicalSetDigester",
    "CompositionRelation",
    "DerivationRelation",
    "FramedSection",
    "ImmutableMemberReceipt",
    "KnownLimit",
    "LocalBlobSource",
    "LocalFileState",
    "LocalFileStateIndex",
    "LocalMemberSource",
    "MemberDescriptor",
    "MemberManifestReference",
    "MemberNotFoundError",
    "MemberSource",
    "MemberSourceError",
    "PinnedLocalDirectory",
    "Producer",
    "ReceiptMemberSource",
    "SemanticVerifier",
    "Supersedes",
    "VerificationIssue",
    "VerificationResult",
    "VerifiedArtifact",
    "admit_artifact",
    "build_artifact_root",
    "canonical_json_bytes",
    "describe_member",
    "describe_member_from_receipt",
    "expected_artifact_digest",
    "expected_logical_digest",
    "expected_logical_id",
    "framed_section_digest",
    "iter_member_descriptors",
    "move_child_directory_no_replace",
    "parse_admitted_json",
    "parse_canonical_json",
    "publish_child_directory_no_replace",
    "publish_directory_no_replace",
    "schema_bundle_digest",
    "sha256_digest",
    "stamp_root",
    "validate_composition_relation",
    "validate_derivation_relation",
    "validate_object_key",
    "verify_artifact",
    "write_member_manifest",
]
