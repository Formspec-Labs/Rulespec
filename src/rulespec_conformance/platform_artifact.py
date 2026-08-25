"""Shared identity and structural verification for platform artifacts.

Rulespec owns this byte-level protocol. Product packages supply kind-specific
semantic checks and translate verified members into their own domain models.
The module performs no network access and accepts member I/O through the narrow
``MemberSource`` protocol.
"""

from __future__ import annotations

import codecs
import errno
import hashlib
import io
import json
import os
import re
import sqlite3
import stat
import tempfile
from collections.abc import Iterable, Iterator, Mapping, Sequence
from contextlib import AbstractContextManager, contextmanager
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, ClassVar, Protocol, Self, runtime_checkable

from rulespec_conformance.conformance_lib import ROOT

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
SOURCE_CATALOG_ITEM_SCHEMA_ID = (
    "https://rulespec.org/schemas/releases/source-catalog-release-v1/"
    "source-items-v1.schema.json"
)
_SOURCE_CATALOG_ITEM_SCHEMA = (
    ROOT
    / "release-records"
    / "schemas"
    / "source-catalog-release-v1"
    / "source-items-v1.schema.json"
)

ARTIFACT_KINDS = ("source-catalog", "derivation", "composition")
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

_ROOT_FIELDS = frozenset(
    {
        "artifactDigest",
        "counts",
        "coverage",
        "format",
        "formatVersion",
        "inputs",
        "kind",
        "logicalId",
        "memberManifests",
        "spec",
    }
)
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
_MEMBER_REQUIRED_FIELDS = frozenset(
    {"byteSize", "mediaType", "objectKey", "role", "sha256"}
)
_MEMBER_OPTIONAL_FIELDS = frozenset({"recordCount", "schemaId"})
_COMMON_COUNT_FIELDS = frozenset(
    {"manifestCount", "memberCount", "totalMemberByteSize", "totalRecordCount"}
)
_COVERAGE_FIELDS = frozenset(
    {"accountedInputCount", "complete", "unaccountedInputCount"}
)
_KIND_SPEC_FIELDS = {
    "source-catalog": frozenset(
        {
            "catalogId",
            "requestedUniverseSetDigest",
            "selectedSourceSetDigest",
            "selectionPolicyDigest",
            "selectionPolicyId",
            "selectionPolicyVersion",
            "sourceSystemId",
            "sourceSystemVersion",
        }
    ),
    "derivation": frozenset(
        {
            "expectedOutputRoles",
            "parametersDigest",
            "partitioningId",
            "partitioningDigest",
            "policyDigest",
            "policyId",
            "policyVersion",
            "processorDigest",
            "processorId",
            "processorVersion",
        }
    ),
    "composition": frozenset(
        {
            "mergePolicyDigest",
            "mergePolicyId",
            "mergePolicyVersion",
            "totalOrderKey",
        }
    ),
}
_SCOPE_KINDS = frozenset({"global", "partition"})
_ROLE = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
_QUALIFIED_SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
_ABSOLUTE_ID = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*:[^\s]+\Z")


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


def _string_bytes(value: str, *, path: str) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except UnicodeEncodeError as error:
        _fail("invalid.root-syntax", path, f"text contains a lone Unicode surrogate: {error}")


def _utf16_sort_key(value: str) -> bytes:
    try:
        return value.encode("utf-16-be")
    except UnicodeEncodeError as error:
        _fail("invalid.root-syntax", "$", f"object key contains a lone Unicode surrogate: {error}")


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
        return b"[" + b",".join(
            _canonical_json_parts(item, path=f"{path}/{index}")
            for index, item in enumerate(value)
        ) + b"]"
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
        if self._previous is not None and value <= self._previous:
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


def source_catalog_item_schema_bytes() -> bytes:
    """Return the one packaged source-item schema used by artifact producers."""

    payload = _SOURCE_CATALOG_ITEM_SCHEMA.read_bytes()
    schema = json.loads(payload)
    if schema.get("$id") != SOURCE_CATALOG_ITEM_SCHEMA_ID:
        raise RuntimeError("packaged source-catalog item schema has the wrong identity")
    return payload


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


def parse_canonical_json(raw: bytes, *, path: str = "$", code: str = "invalid.root-syntax") -> Any:
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


def _closed_mapping(value: object, fields: frozenset[str], *, path: str) -> Mapping[str, Any]:
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
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= JSON_SAFE_INTEGER_MAX:
        _fail("invalid.schema", path, "value must be a JSON-safe unsigned integer")
    return value


def _digest(value: object, *, path: str) -> str:
    selected = _text(value, path=path)
    if _QUALIFIED_SHA256.fullmatch(selected) is None:
        _fail("invalid.schema", path, "value must be a qualified lowercase SHA-256 digest")
    return selected


def _absolute_id(value: object, *, path: str) -> str:
    selected = _text(value, path=path)
    if _ABSOLUTE_ID.fullmatch(selected) is None:
        _fail("invalid.schema", path, "value must be an absolute identifier")
    return selected


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
        (_role(item, path=f"{path}/{index}") if role_values else _text(item, path=f"{path}/{index}"))
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
        return cls(
            role=_role(item["role"], path=f"{path}/role"),
            logical_id=_absolute_id(item["logicalId"], path=f"{path}/logicalId"),
            artifact_digest=_digest(item["artifactDigest"], path=f"{path}/artifactDigest"),
        )

    def as_dict(self) -> dict[str, str]:
        return {
            "artifactDigest": self.artifact_digest,
            "logicalId": self.logical_id,
            "role": self.role,
        }


class ArtifactSpec(Protocol):
    """Supply one closed kind-specific spec to the shared root builder."""

    kind: ClassVar[str]

    def as_dict(self) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class SourceCatalogSpec:
    """Logical source-selection identity for a source catalog."""

    kind: ClassVar[str] = "source-catalog"

    catalog_id: str
    source_system_id: str
    source_system_version: str
    selection_policy_id: str
    selection_policy_version: str
    selection_policy_digest: str
    requested_universe_set_digest: str
    selected_source_set_digest: str

    def as_dict(self) -> dict[str, object]:
        return {
            "catalogId": self.catalog_id,
            "requestedUniverseSetDigest": self.requested_universe_set_digest,
            "selectedSourceSetDigest": self.selected_source_set_digest,
            "selectionPolicyDigest": self.selection_policy_digest,
            "selectionPolicyId": self.selection_policy_id,
            "selectionPolicyVersion": self.selection_policy_version,
            "sourceSystemId": self.source_system_id,
            "sourceSystemVersion": self.source_system_version,
        }


@dataclass(frozen=True, slots=True)
class DerivationSpec:
    """Logical processor, policy, and partition identity for a derivation."""

    kind: ClassVar[str] = "derivation"

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

    def as_dict(self) -> dict[str, object]:
        return {
            "expectedOutputRoles": sorted(self.expected_output_roles),
            "parametersDigest": self.parameters_digest,
            "partitioningDigest": self.partitioning_digest,
            "partitioningId": self.partitioning_id,
            "policyDigest": self.policy_digest,
            "policyId": self.policy_id,
            "policyVersion": self.policy_version,
            "processorDigest": self.processor_digest,
            "processorId": self.processor_id,
            "processorVersion": self.processor_version,
        }


@dataclass(frozen=True, slots=True)
class CompositionSpec:
    """Logical merge policy and total order for a composition."""

    kind: ClassVar[str] = "composition"

    merge_policy_id: str
    merge_policy_version: str
    merge_policy_digest: str
    total_order_key: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "mergePolicyDigest": self.merge_policy_digest,
            "mergePolicyId": self.merge_policy_id,
            "mergePolicyVersion": self.merge_policy_version,
            "totalOrderKey": list(self.total_order_key),
        }


@dataclass(frozen=True, slots=True)
class MemberDescriptor:
    """Describe one payload member declared by exactly one manifest."""

    object_key: str
    role: str
    media_type: str
    byte_size: int
    sha256: str
    record_count: int | None = None
    schema_id: str | None = None

    @classmethod
    def from_dict(cls, value: object, *, path: str) -> Self:
        if not isinstance(value, Mapping):
            _fail("invalid.schema", path, "member descriptor must be an object")
        fields = frozenset(value)
        if not _MEMBER_REQUIRED_FIELDS <= fields <= _MEMBER_REQUIRED_FIELDS | _MEMBER_OPTIONAL_FIELDS:
            _fail("invalid.schema", path, "member descriptor has missing or unknown fields")
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
            object_key=validate_object_key(value["objectKey"], path=f"{path}/objectKey"),
            role=_role(value["role"], path=f"{path}/role"),
            media_type=media_type,
            byte_size=_uint(value["byteSize"], path=f"{path}/byteSize"),
            sha256=_digest(value["sha256"], path=f"{path}/sha256"),
            record_count=record_count,
            schema_id=schema_id,
        )

    def as_dict(self) -> dict[str, object]:
        value: dict[str, object] = {
            "byteSize": self.byte_size,
            "mediaType": self.media_type,
            "objectKey": self.object_key,
            "role": self.role,
            "sha256": self.sha256,
        }
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
            _fail("invalid.schema", f"{path}/manifestId", "manifest ID differs from its scope")
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
            total_record_count=_uint(item["totalRecordCount"], path=f"{path}/totalRecordCount"),
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
            members=sorted(members, key=lambda member: member.object_key),
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
        row = self._open_connection().execute(
            "SELECT device, inode, state_size, modified_nanoseconds, "
            "changed_nanoseconds, mode FROM expected "
            "WHERE kind = 'payload' AND object_key = ?",
            (object_key,),
        ).fetchone()
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
        row = self._open_connection().execute(
            "SELECT COUNT(*) FROM expected WHERE kind = 'payload'"
        ).fetchone()
        return int(row[0]) if row is not None else 0

    def close(self) -> None:
        connection, self._connection = self._connection, None
        if connection is not None:
            connection.close()

    def __del__(self) -> None:
        self.close()


class LocalMemberSource:
    """Read one materialized artifact directory without following links."""

    def __init__(self, root: Path) -> None:
        if (
            not getattr(os, "O_NOFOLLOW", 0)
            or not getattr(os, "O_DIRECTORY", 0)
            or os.open not in os.supports_dir_fd
            or os.scandir not in os.supports_fd
        ):
            raise MemberSourceError(
                "local artifact verification requires descriptor-relative no-follow filesystem access"
            )
        unresolved = Path(root).absolute()
        try:
            descriptor = os.open(
                unresolved,
                os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW | os.O_DIRECTORY,
            )
        except FileNotFoundError as error:
            _fail("invalid.path", "$", f"artifact root is unavailable: {error}")
        except OSError as error:
            if error.errno in (errno.ELOOP, errno.ENOTDIR):
                _fail("invalid.path", "$", "artifact root must be a real directory")
            raise MemberSourceError(f"cannot open artifact root {unresolved}: {error}") from error
        try:
            root_state = os.fstat(descriptor)
            if not stat.S_ISDIR(root_state.st_mode):
                _fail("invalid.path", "$", "artifact root must be a real directory")
            self._root_identity = (root_state.st_dev, root_state.st_ino)
        finally:
            os.close(descriptor)
        self.root = unresolved

    @staticmethod
    def _open_flags(*, directory: bool = False) -> int:
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | os.O_NOFOLLOW
        if directory:
            flags |= os.O_DIRECTORY
        return flags

    def _open_root(self) -> int:
        try:
            descriptor = os.open(self.root, self._open_flags(directory=True))
        except OSError as error:
            if error.errno in (errno.ELOOP, errno.ENOTDIR):
                _fail("invalid.path", "$", "artifact root must be a real directory")
            raise MemberSourceError(f"cannot open artifact root {self.root}: {error}") from error
        try:
            state = os.fstat(descriptor)
        except BaseException:
            os.close(descriptor)
            raise
        if (state.st_dev, state.st_ino) != self._root_identity:
            os.close(descriptor)
            raise MemberSourceError("artifact root changed after the member source was created")
        return descriptor

    @staticmethod
    def _open_relative(directory_fd: int, name: str, *, directory: bool, path: str) -> int:
        try:
            return os.open(
                name,
                LocalMemberSource._open_flags(directory=directory),
                dir_fd=directory_fd,
            )
        except FileNotFoundError as error:
            raise MemberNotFoundError(path) from error
        except OSError as error:
            if error.errno == errno.ELOOP:
                _fail("invalid.path", path, "member path traverses a symbolic link")
            if directory and error.errno == errno.ENOTDIR:
                _fail("invalid.path", path, "member path traverses a non-directory")
            raise MemberSourceError(f"cannot open artifact member {path}: {error}") from error

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
                _fail("invalid.member-digest", selected, "member changed while it was read")
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
                    _fail("invalid.manifest", self._path, f"manifest is not UTF-8: {error}")
                return True
            if not eof:
                eof = True
                try:
                    buffer += utf8.decode(b"", final=True)
                except UnicodeError as error:
                    _fail("invalid.manifest", self._path, f"manifest is not UTF-8: {error}")
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
                _fail("invalid.manifest", self._path, "member manifest has no members array")
            position += 1
            first = True
            while True:
                while position >= len(buffer) and fill():
                    pass
                if position >= len(buffer):
                    _fail("invalid.manifest", self._path, "member manifest is truncated")
                if first and buffer[position] == "]":
                    position += 1
                    break
                if not first:
                    if buffer[position] == "]":
                        position += 1
                        break
                    if buffer[position] != ",":
                        _fail("invalid.manifest", self._path, "member manifest is not canonical")
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
                        _fail("invalid.manifest", self._path, f"manifest entry is invalid: {error}")
                    break
                raw_value = buffer[start:end]
                try:
                    expected = canonical_json_bytes(value).decode("utf-8")
                except ArtifactVerificationError as error:
                    _fail("invalid.manifest", self._path, error.issue.message)
                if expected != raw_value:
                    _fail("invalid.manifest", self._path, "manifest entry is not canonical JSON")
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
    suffix = b',"scope":' + canonical_json_bytes(
        {"id": reference.scope_id, "kind": reference.scope_kind}
    ) + b"}"
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
    previous_key: str | None = None
    with tempfile.SpooledTemporaryFile(max_size=spool_bytes, mode="w+b") as body:
        for index, raw_member in enumerate(members):
            member = MemberDescriptor.from_dict(
                raw_member.as_dict(),
                path=f"manifest/members/{index}",
            )
            if previous_key is not None and member.object_key <= previous_key:
                _fail(
                    "invalid.manifest",
                    selected_key,
                    "producer members must be sorted and distinct",
                )
            if member_count:
                _write_all(body, b",")
            _write_all(body, canonical_json_bytes(member.as_dict()))
            previous_key = member.object_key
            member_count += 1
            total_member_byte_size += member.byte_size
            total_record_count += member.record_count or 0
            if body.tell() > byte_limit:
                _fail("invalid.limit", selected_key, "member manifest exceeds its byte limit")

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
            _fail("invalid.limit", selected_key, "member manifest exceeds its byte limit")
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


def expected_logical_id(root: Mapping[str, Any]) -> str:
    """Derive logical identity without physical pins or execution evidence."""

    kind = _text(root.get("kind"), path="$/kind")
    if kind not in ARTIFACT_KINDS:
        _fail("invalid.format", "$/kind", "artifact kind is not registered")
    inputs = tuple(
        ArtifactInput.from_dict(value, path=f"$/inputs/{index}")
        for index, value in enumerate(_array(root.get("inputs"), path="$/inputs"))
    )
    logical_inputs = [
        {"logicalId": item.logical_id, "role": item.role}
        for item in inputs
    ]
    payload = {
        "format": root.get("format"),
        "formatVersion": root.get("formatVersion"),
        "kind": kind,
        "logicalInputs": logical_inputs,
        "spec": root.get("spec"),
    }
    return f"urn:spicy:artifact:{kind}:" + sha256_digest(payload).removeprefix("sha256:")


def expected_artifact_digest(root: Mapping[str, Any]) -> str:
    """Derive physical identity from the complete root without self-reference."""

    payload = dict(root)
    payload.pop("artifactDigest", None)
    return sha256_digest(payload)


def stamp_root(root: Mapping[str, Any]) -> dict[str, Any]:
    """Return a root copy carrying both derived identities."""

    stamped = deepcopy(dict(root))
    stamped.pop("logicalId", None)
    stamped.pop("artifactDigest", None)
    stamped["logicalId"] = expected_logical_id(stamped)
    stamped["artifactDigest"] = expected_artifact_digest(stamped)
    _validate_root(stamped)
    return stamped


def _validate_kind_spec(kind: str, value: object, inputs: tuple[ArtifactInput, ...]) -> None:
    path = "$/spec"
    spec = _closed_mapping(value, _KIND_SPEC_FIELDS[kind], path=path)
    if kind == "source-catalog":
        for name in ("catalogId", "selectionPolicyId", "sourceSystemId"):
            _absolute_id(spec[name], path=f"{path}/{name}")
        for name in ("requestedUniverseSetDigest", "selectedSourceSetDigest", "selectionPolicyDigest"):
            _digest(spec[name], path=f"{path}/{name}")
        for name in ("selectionPolicyVersion", "sourceSystemVersion"):
            _text(spec[name], path=f"{path}/{name}")
        return
    if kind == "derivation":
        if not inputs:
            _fail("invalid.schema", "$/inputs", "a derivation requires at least one input")
        for name in ("partitioningId", "policyId", "processorId"):
            _absolute_id(spec[name], path=f"{path}/{name}")
        for name in ("parametersDigest", "partitioningDigest", "policyDigest", "processorDigest"):
            _digest(spec[name], path=f"{path}/{name}")
        for name in ("policyVersion", "processorVersion"):
            _text(spec[name], path=f"{path}/{name}")
        expected_roles = _distinct_text_array(
            spec["expectedOutputRoles"],
            path=f"{path}/expectedOutputRoles",
            role_values=True,
        )
        if expected_roles != tuple(sorted(expected_roles)):
            _fail(
                "invalid.schema",
                f"{path}/expectedOutputRoles",
                "expected output roles must be sorted",
            )
        return
    if not inputs:
        _fail("invalid.schema", "$/inputs", "a composition requires at least one member")
    if any(item.role != "member" for item in inputs):
        _fail("invalid.schema", "$/inputs", "composition inputs must use the member role")
    _absolute_id(spec["mergePolicyId"], path=f"{path}/mergePolicyId")
    _digest(spec["mergePolicyDigest"], path=f"{path}/mergePolicyDigest")
    _text(spec["mergePolicyVersion"], path=f"{path}/mergePolicyVersion")
    _distinct_text_array(spec["totalOrderKey"], path=f"{path}/totalOrderKey")


def _validate_root(root: Mapping[str, Any]) -> tuple[tuple[ArtifactInput, ...], tuple[MemberManifestReference, ...]]:
    item = _closed_mapping(root, _ROOT_FIELDS, path="$")
    if item["format"] != FORMAT or item["formatVersion"] != FORMAT_VERSION:
        _fail("invalid.format", "$", "artifact format or exact version is unsupported")
    kind = _text(item["kind"], path="$/kind")
    if kind not in ARTIFACT_KINDS:
        _fail("invalid.format", "$/kind", "artifact kind is not registered")
    inputs = tuple(
        ArtifactInput.from_dict(value, path=f"$/inputs/{index}")
        for index, value in enumerate(_array(item["inputs"], path="$/inputs"))
    )
    input_values = [entry.as_dict() for entry in inputs]
    if input_values != sorted(input_values, key=lambda value: (value["role"], value["logicalId"], value["artifactDigest"])):
        _fail("invalid.schema", "$/inputs", "inputs must be sorted")
    if len(input_values) != len({canonical_json_bytes(value) for value in input_values}):
        _fail("invalid.schema", "$/inputs", "inputs must be distinct")
    _validate_kind_spec(kind, item["spec"], inputs)

    counts = _closed_mapping(item["counts"], _COMMON_COUNT_FIELDS, path="$/counts")
    for name in _COMMON_COUNT_FIELDS:
        _uint(counts[name], path=f"$/counts/{name}")
    coverage = _closed_mapping(item["coverage"], _COVERAGE_FIELDS, path="$/coverage")
    if not isinstance(coverage["complete"], bool):
        _fail("invalid.schema", "$/coverage/complete", "value must be boolean")
    _uint(coverage["accountedInputCount"], path="$/coverage/accountedInputCount")
    unaccounted = _uint(
        coverage["unaccountedInputCount"], path="$/coverage/unaccountedInputCount"
    )
    if not coverage["complete"] or unaccounted:
        _fail("invalid.statistics", "$/coverage", "artifact coverage is incomplete")

    manifests = tuple(
        MemberManifestReference.from_dict(value, path=f"$/memberManifests/{index}")
        for index, value in enumerate(_array(item["memberManifests"], path="$/memberManifests"))
    )
    if kind != "composition" and not manifests:
        _fail("invalid.schema", "$/memberManifests", "at least one member manifest is required")
    manifest_order = [(entry.scope_kind, entry.scope_id, entry.object_key) for entry in manifests]
    if manifest_order != sorted(manifest_order) or len(manifest_order) != len(set(manifest_order)):
        _fail("invalid.schema", "$/memberManifests", "member manifests must be sorted and distinct")

    logical_id = _absolute_id(item["logicalId"], path="$/logicalId")
    expected_logical = expected_logical_id(item)
    if logical_id != expected_logical:
        _fail("invalid.identity", "$/logicalId", f"expected {expected_logical}")
    artifact_digest = _digest(item["artifactDigest"], path="$/artifactDigest")
    expected_physical = expected_artifact_digest(item)
    if artifact_digest != expected_physical:
        _fail("invalid.identity", "$/artifactDigest", f"expected {expected_physical}")
    return inputs, manifests


def _read_bounded(source: MemberSource, object_key: str, *, byte_limit: int, code: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
        with source.open(object_key) as stream:
            while chunk := stream.read(DEFAULT_READ_CHUNK_BYTES):
                total += len(chunk)
                if total > byte_limit:
                    _fail("invalid.limit", object_key, f"file exceeds {byte_limit} bytes")
                chunks.append(chunk)
    except MemberNotFoundError:
        _fail("invalid.membership-missing", object_key, "declared artifact file is absent")
    try:
        return b"".join(chunks)
    except MemoryError:
        _fail(code, object_key, "file could not be read within its declared bound")


def _hash_member(source: MemberSource, member: MemberDescriptor) -> LocalFileState | None:
    digest = hashlib.sha256()
    byte_size = 0
    local_state: LocalFileState | None = None
    try:
        with source.open(member.object_key) as stream:
            while block := stream.read(DEFAULT_READ_CHUNK_BYTES):
                byte_size += len(block)
                if byte_size > member.byte_size:
                    _fail("invalid.member-digest", member.object_key, "member exceeds its declared size")
                digest.update(block)
            if isinstance(source, LocalMemberSource):
                local_state = LocalFileState.from_stat(os.fstat(stream.fileno()))
    except MemberNotFoundError:
        _fail("invalid.membership-missing", member.object_key, "declared payload is absent")
    actual_digest = "sha256:" + digest.hexdigest()
    if byte_size != member.byte_size or actual_digest != member.sha256:
        _fail("invalid.member-digest", member.object_key, "member size or digest differs")
    return local_state


@contextmanager
def _open_required(source: MemberSource, object_key: str) -> Iterator[BinaryIO]:
    try:
        with source.open(object_key) as stream:
            yield stream
    except MemberNotFoundError:
        _fail("invalid.membership-missing", object_key, "declared artifact file is absent")


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
    object_key: str,
    role: str,
    media_type: str,
    byte_size: int,
    sha256: str,
    record_count: int | None = None,
    schema_id: str | None = None,
) -> MemberDescriptor:
    """Validate one immutable producer receipt without rereading its bytes."""

    value: dict[str, object] = {
        "byteSize": byte_size,
        "mediaType": media_type,
        "objectKey": object_key,
        "role": role,
        "sha256": sha256,
    }
    if record_count is not None:
        value["recordCount"] = record_count
    if schema_id is not None:
        value["schemaId"] = schema_id
    return MemberDescriptor.from_dict(value, path="member")


def build_artifact_root(
    *,
    spec: ArtifactSpec,
    inputs: Sequence[ArtifactInput],
    manifests: Sequence[MemberManifestReference],
    accounted_input_count: int,
) -> dict[str, Any]:
    """Build and stamp the one closed artifact root from sealed manifests.

    The function derives aggregate counts from the manifest references. It
    sorts inputs and manifests into their required deterministic order, so
    product publishers never reproduce root assembly or identity logic.
    """

    ordered_inputs = tuple(
        sorted(
            inputs,
            key=lambda item: (item.role, item.logical_id, item.artifact_digest),
        )
    )
    ordered_manifests = tuple(
        sorted(
            manifests,
            key=lambda item: (item.scope_kind, item.scope_id, item.object_key),
        )
    )
    return stamp_root(
        {
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
            "coverage": {
                "accountedInputCount": accounted_input_count,
                "complete": True,
                "unaccountedInputCount": 0,
            },
            "format": FORMAT,
            "formatVersion": FORMAT_VERSION,
            "inputs": [item.as_dict() for item in ordered_inputs],
            "kind": spec.kind,
            "memberManifests": [item.as_dict() for item in ordered_manifests],
            "spec": spec.as_dict(),
        }
    )


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
        previous_member_key: str | None = None
        member_count = 0
        total_member_byte_size = 0
        total_record_count = 0
        for index, value in enumerate(values):
            member = MemberDescriptor.from_dict(
                value,
                path=f"{reference.object_key}/{index}",
            )
            if previous_member_key is not None and member.object_key <= previous_member_key:
                _fail(
                    "invalid.manifest",
                    reference.object_key,
                    "members must be sorted and distinct within their manifest",
                )
            previous_member_key = member.object_key
            member_count += 1
            total_member_byte_size += member.byte_size
            total_record_count += member.record_count or 0
            yield member
    if values.byte_size != reference.byte_size or values.sha256 != reference.sha256:
        _fail("invalid.manifest", reference.object_key, "manifest size or digest differs")
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


def _admit(
    source: MemberSource,
    *,
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
            index = sqlite3.connect("")
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
            index = sqlite3.connect(index_path)
        index.execute(
            "CREATE TABLE expected ("
            "object_key TEXT PRIMARY KEY, kind TEXT NOT NULL, observed INTEGER NOT NULL DEFAULT 0, "
            "role TEXT, media_type TEXT, byte_size INTEGER, sha256 TEXT, "
            "record_count INTEGER, schema_id TEXT, device INTEGER, inode INTEGER, "
            "state_size INTEGER, modified_nanoseconds INTEGER, changed_nanoseconds INTEGER, "
            "mode INTEGER)"
        )
        index.execute("CREATE TABLE derivation_roles (role TEXT PRIMARY KEY)")
        index.execute(
            "INSERT INTO expected (object_key, kind) VALUES (?, 'protocol')",
            (ROOT_OBJECT_KEY,),
        )
        for reference in manifest_references:
            try:
                index.execute(
                    "INSERT INTO expected (object_key, kind) VALUES (?, 'protocol')",
                    (reference.object_key,),
                )
            except sqlite3.IntegrityError:
                _fail("invalid.manifest", reference.object_key, "manifest path is repeated")

        member_count = 0
        total_member_byte_size = 0
        total_record_count = 0
        for reference in manifest_references:
            for member in _iter_manifest_members(
                source,
                reference,
                manifest_byte_limit=manifest_byte_limit,
            ):
                try:
                    index.execute(
                        "INSERT INTO expected "
                        "(object_key, kind, observed, role, media_type, byte_size, sha256, "
                        "record_count, schema_id) VALUES (?, 'payload', 0, ?, ?, ?, ?, ?, ?)",
                        (
                            member.object_key,
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
                        member.object_key,
                        "payload overlaps a protocol file or another manifest",
                    )
                member_count += 1
                total_member_byte_size += member.byte_size
                total_record_count += member.record_count or 0

        if root["kind"] == "derivation":
            expected_roles = _mapping(root["spec"], path="$/spec")["expectedOutputRoles"]
            index.executemany(
                "INSERT INTO derivation_roles (role) VALUES (?)",
                ((role,) for role in expected_roles),
            )
            missing_role = index.execute(
                "SELECT derivation_roles.role FROM derivation_roles "
                "LEFT JOIN expected ON expected.kind = 'payload' "
                "AND expected.role = derivation_roles.role "
                "WHERE expected.object_key IS NULL ORDER BY derivation_roles.role LIMIT 1"
            ).fetchone()
            if missing_role is not None:
                _fail(
                    "invalid.schema",
                    "$/spec/expectedOutputRoles",
                    f"declared output role is absent: {missing_role[0]}",
                )
            unexpected_role = index.execute(
                "SELECT expected.role FROM expected "
                "LEFT JOIN derivation_roles ON derivation_roles.role = expected.role "
                "WHERE expected.kind = 'payload' AND derivation_roles.role IS NULL "
                "ORDER BY expected.role LIMIT 1"
            ).fetchone()
            if unexpected_role is not None:
                _fail(
                    "invalid.schema",
                    "$/spec/expectedOutputRoles",
                    f"payload role is undeclared: {unexpected_role[0]}",
                )

        first_extra: str | None = None
        for raw_key in source.keys():  # noqa: SIM118 - MemberSource is not a Mapping
            object_key = validate_object_key(raw_key, path=str(raw_key))
            row = index.execute(
                "SELECT observed FROM expected WHERE object_key = ?",
                (object_key,),
            ).fetchone()
            if row is None or row[0]:
                first_extra = min(first_extra, object_key) if first_extra else object_key
                continue
            index.execute(
                "UPDATE expected SET observed = 1 WHERE object_key = ?",
                (object_key,),
            )
        missing = index.execute(
            "SELECT object_key FROM expected WHERE observed = 0 ORDER BY object_key LIMIT 1"
        ).fetchone()
        if missing is not None:
            _fail("invalid.membership-missing", missing[0], "declared artifact file is absent")
        if first_extra is not None:
            _fail("invalid.membership-extra", first_extra, "artifact contains an undeclared file")

        capture_local_states = isinstance(source, LocalMemberSource)
        rows = index.execute(
            "SELECT object_key, role, media_type, byte_size, sha256, record_count, schema_id "
            "FROM expected WHERE kind = 'payload' ORDER BY object_key"
        )
        for row in rows:
            member = MemberDescriptor(*row)
            state = _hash_member(source, member)
            if capture_local_states:
                if state is None:
                    raise RuntimeError("local member admission did not capture a file state")
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
        expected_pin=expected_pin,
        root_byte_limit=root_byte_limit,
        manifest_byte_limit=manifest_byte_limit,
        scratch_directory=scratch_directory,
    )
    if semantic_verifier is not None:
        semantic_verifier(artifact, source)
    return artifact


__all__ = [
    "ARTIFACT_KINDS",
    "DIAGNOSTIC_CODES",
    "FORMAT",
    "FORMAT_VERSION",
    "MEMBER_MANIFEST_FORMAT",
    "MEMBER_MANIFEST_MEDIA_TYPE",
    "MEMBER_MANIFEST_VERSION",
    "ROOT_OBJECT_KEY",
    "SOURCE_CATALOG_ITEM_SCHEMA_ID",
    "ArtifactInput",
    "ArtifactPin",
    "ArtifactSpec",
    "ArtifactVerificationError",
    "CanonicalSetDigester",
    "CompositionSpec",
    "DerivationSpec",
    "LocalMemberSource",
    "LocalFileState",
    "LocalFileStateIndex",
    "MemberDescriptor",
    "MemberManifestReference",
    "MemberNotFoundError",
    "MemberSource",
    "MemberSourceError",
    "SemanticVerifier",
    "SourceCatalogSpec",
    "VerificationIssue",
    "VerificationResult",
    "VerifiedArtifact",
    "admit_artifact",
    "build_artifact_root",
    "canonical_json_bytes",
    "describe_member",
    "describe_member_from_receipt",
    "expected_artifact_digest",
    "expected_logical_id",
    "iter_member_descriptors",
    "parse_canonical_json",
    "sha256_digest",
    "source_catalog_item_schema_bytes",
    "stamp_root",
    "validate_object_key",
    "verify_artifact",
    "write_member_manifest",
]
