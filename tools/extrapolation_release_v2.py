#!/usr/bin/env python3
"""Portable verifier for partitioned ``ExtrapolationRelease`` v2 bundles.

The verifier implements the common artifact protocol without importing a
sibling product.  A caller supplies a materialized, already copied
``DocumentRelease`` v3 bundle and, when concept membership is in scope, the
product-local static atlas reader.  All release members remain immutable files;
the verifier does not call a database or a network service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

import jsonschema
import pyarrow as pa
import pyarrow.parquet as pq
import rfc8785

try:
    from rulespec_release import (
        SHA256_RE,
        canonical_digest,
        canonical_json_bytes as v1_canonical_json_bytes,
        load_json as load_v1_json,
        stable_record_id,
    )
except ModuleNotFoundError:  # imported as a tools package
    from tools.rulespec_release import (
        SHA256_RE,
        canonical_digest,
        canonical_json_bytes as v1_canonical_json_bytes,
        load_json as load_v1_json,
        stable_record_id,
    )

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = ROOT / "release-records" / "schemas"
ROOT_SCHEMA = SCHEMA_ROOT / "extrapolation-release-v2.schema.json"
V1_SCHEMA = SCHEMA_ROOT / "extrapolation-release.schema.json"
TABLE_SCHEMA_ROOT = SCHEMA_ROOT / "extrapolation-release-v2"

FORMAT = "rulespec-extrapolation-release"
FORMAT_VERSION = "2.0"
MEMBER_MANIFEST_FORMAT = "spicy-artifact-member-manifest"
MEMBER_MANIFEST_VERSION = "1.0"
MAX_SAFE_INTEGER = (1 << 53) - 1
HEX_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
REASON_CODE_RE = re.compile(r"^[a-z][a-z0-9]*(\.[a-z][a-z0-9-]*){2,}$")

ALLOWED_ROLES = frozenset(
    {
        "schema",
        "assignments",
        "assignment-evidence",
        "assignment-dispositions",
        "coverage",
        "build-receipt",
    }
)
DATA_ROLES = ALLOWED_ROLES - {"schema"}
ROLE_SCHEMA_FILES = {
    "assignments": "assignments-v1.schema.json",
    "assignment-evidence": "assignment-evidence-v1.schema.json",
    "assignment-dispositions": "assignment-dispositions-v1.schema.json",
    "coverage": "coverage-v1.schema.json",
    "build-receipt": "build-receipt-v1.schema.json",
}
ROLE_SCHEMA_IDS = {
    role: json.loads((TABLE_SCHEMA_ROOT / filename).read_text(encoding="utf-8"))["$id"]
    for role, filename in ROLE_SCHEMA_FILES.items()
}
ROOT_SCHEMA_ID = json.loads(ROOT_SCHEMA.read_text(encoding="utf-8"))["$id"]
EXPECTED_SCHEMA_ROLES = {
    ROOT_SCHEMA_ID: ("schema",),
    **{schema_id: (role,) for role, schema_id in ROLE_SCHEMA_IDS.items()},
}

CORE_CODE_PRECEDENCE = {
    code: index
    for index, code in enumerate(
        (
            "invalid.root-syntax",
            "invalid.format",
            "invalid.identity",
            "invalid.membership-missing",
            "invalid.membership-extra",
            "invalid.member-digest",
            "invalid.path",
            "invalid.schema",
            "invalid.duplicate-identity",
            "invalid.foreign-key",
            "invalid.coordinate",
            "invalid.eligibility-evidence",
            "invalid.reconciliation",
            "invalid.privacy",
            "invalid.statistics",
            "invalid.shard",
            "invalid.assignment-pin",
            "invalid.assignment-evidence",
            "invalid.assignment-disposition",
            "invalid.tier",
        )
    )
}

MEMBER_DESCRIPTOR_FIELDS = {
    "objectKey",
    "role",
    "mediaType",
    "byteSize",
    "sha256",
    "recordCount",
    "schemaId",
    "partitionId",
    "servingShardId",
}
MANIFEST_REFERENCE_FIELDS = {
    "manifestId",
    "scopeKind",
    "scopeId",
    "objectKey",
    "byteSize",
    "sha256",
}
SUBORDINATE_MANIFEST_FIELDS = {
    "format",
    "formatVersion",
    "manifestId",
    "scope",
    "members",
    "counts",
}


class AtlasMembershipReader(Protocol):
    """The static atlas operation needed for assignment membership checks."""

    def pin(self) -> Mapping[str, str]:
        """Return the selected atlas asset pin."""

    def require_member(self, *, member_id: str, release_id: str) -> Any:
        """Prove that a concept belongs to the assigned concept release."""


@dataclass(frozen=True)
class VerificationIssue:
    """One deterministic conformance diagnostic."""

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} {self.path}: {self.message}"


@dataclass(frozen=True)
class VerificationResult:
    """The ordered result of verifying one materialized bundle."""

    release_id: str | None
    issues: tuple[VerificationIssue, ...]

    @property
    def code(self) -> str:
        if not self.issues:
            return "valid"
        return min(
            self.issues,
            key=lambda issue: CORE_CODE_PRECEDENCE.get(issue.code, 10_000),
        ).code

    @property
    def valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class DocumentReleaseView:
    """Verified document identities required by assignment verification."""

    release_id: str
    artifact_digest: str
    active_documents: Mapping[str, str]
    passages: Mapping[str, tuple[str, str, str]]
    normalized_text: Mapping[str, str]
    passage_records: Mapping[str, Mapping[str, Any]]

    @property
    def v1_pin(self) -> dict[str, str]:
        return {
            "release_id": self.release_id,
            "release_digest": f"sha256:{self.artifact_digest}",
        }


def _issue(issues: list[VerificationIssue], code: str, path: str, message: str) -> None:
    issues.append(VerificationIssue(code=code, path=path, message=message))


def canonical_json_bytes(value: Any) -> bytes:
    """Encode one identity-bearing value under ``spicy-canonical-json-v1``."""

    _validate_canonical_domain(value)
    return rfc8785.dumps(value)


def canonical_sha256(value: Any) -> str:
    """Return an unqualified digest over canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _validate_canonical_domain(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        if isinstance(value, bool) or abs(value) > MAX_SAFE_INTEGER:
            raise ValueError(f"{path} integer is outside the JSON safe range")
        return
    if isinstance(value, float):
        raise ValueError(f"{path} floating-point values are forbidden")
    if isinstance(value, list):
        for index, member in enumerate(value):
            _validate_canonical_domain(member, f"{path}/{index}")
        return
    if isinstance(value, dict):
        for key, member in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} object key is not a string")
            _validate_canonical_domain(member, f"{path}/{key}")
        return
    raise ValueError(f"{path} contains unsupported JSON value {type(value).__name__}")


def _reject_constant(value: str) -> None:
    raise ValueError(f"JSON constant {value!r} is forbidden")


def _reject_float(value: str) -> None:
    raise ValueError(f"JSON floating-point value {value!r} is forbidden")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def load_strict_canonical_json(path: Path) -> Any:
    """Load a canonical manifest and reject noncanonical source bytes."""

    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("a UTF-8 byte order mark is forbidden")
    value = json.loads(
        raw.decode("utf-8"),
        parse_constant=_reject_constant,
        parse_float=_reject_float,
        object_pairs_hook=_reject_duplicate_keys,
    )
    _validate_canonical_domain(value)
    if canonical_json_bytes(value) != raw:
        raise ValueError("JSON bytes are not canonical")
    return value


def write_canonical_json(path: Path, value: Any) -> None:
    """Write canonical JSON without a trailing newline."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _safe_object_key(value: object) -> bool:
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        return False
    pure = PurePosixPath(value)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        return False
    if re.match(r"^[A-Za-z]:", value):
        return False
    return pure.as_posix() == value


def _member_path(bundle: Path, object_key: str) -> Path:
    return bundle.joinpath(*PurePosixPath(object_key).parts)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_release_id(root: Mapping[str, Any]) -> str:
    """Derive the v2 release identity from the exact identity-bearing payload."""

    payload = {
        "format": root.get("format"),
        "formatVersion": root.get("formatVersion"),
        "content": root.get("content"),
    }
    return f"urn:rulespec:extrapolation:v2:{canonical_sha256(payload)}"


def stamp_root(root: Mapping[str, Any]) -> dict[str, Any]:
    """Return a root copy with its content-derived v2 identity."""

    stamped = json.loads(json.dumps(root))
    stamped.pop("releaseId", None)
    stamped["releaseId"] = expected_release_id(stamped)
    return stamped


ASSIGNMENTS_ARROW_SCHEMA = pa.schema(
    [
        pa.field("document_id", pa.string(), nullable=False),
        pa.field("document_version_id", pa.string(), nullable=False),
        pa.field("assignment_id", pa.string(), nullable=False),
        pa.field("subject_ref", pa.string(), nullable=False),
        pa.field("subject_kind", pa.string(), nullable=False),
        pa.field("predicate", pa.string(), nullable=False),
        pa.field("concept_id", pa.string(), nullable=False),
        pa.field("polarity", pa.string(), nullable=False),
        pa.field("assigned_concept_release_id", pa.string(), nullable=False),
        pa.field("origin", pa.string(), nullable=False),
        pa.field("usage_eligibility", pa.string(), nullable=False),
        pa.field("evidence_binding_refs", pa.list_(pa.string()), nullable=False),
        pa.field("extraction_activity_id", pa.string(), nullable=False),
        pa.field("ai_lineage_id", pa.string(), nullable=False),
        pa.field("selection_result", pa.string(), nullable=False),
        pa.field("confidence", pa.float64(), nullable=True),
    ]
)
EVIDENCE_ARROW_SCHEMA = pa.schema(
    [
        pa.field("record_id", pa.string(), nullable=False),
        pa.field("record_type", pa.string(), nullable=False),
        pa.field("assignment_id", pa.string(), nullable=True),
        pa.field("record_json", pa.string(), nullable=False),
    ]
)
DISPOSITIONS_ARROW_SCHEMA = pa.schema(
    [
        pa.field("document_id", pa.string(), nullable=False),
        pa.field("document_version_id", pa.string(), nullable=False),
        pa.field("disposition", pa.string(), nullable=False),
        pa.field("reason_code", pa.string(), nullable=False),
        pa.field("assignment_count", pa.uint64(), nullable=False),
        pa.field("selected_assignment_count", pa.uint64(), nullable=False),
        pa.field("evidence_record_count", pa.uint64(), nullable=False),
        pa.field("failure_id", pa.string(), nullable=True),
    ]
)
COVERAGE_ARROW_SCHEMA = pa.schema(
    [
        pa.field("scope_kind", pa.string(), nullable=False),
        pa.field("scope_id", pa.string(), nullable=False),
        pa.field("active_document_count", pa.uint64(), nullable=False),
        pa.field("assigned_document_count", pa.uint64(), nullable=False),
        pa.field("abstained_document_count", pa.uint64(), nullable=False),
        pa.field("excluded_document_count", pa.uint64(), nullable=False),
        pa.field("failed_document_count", pa.uint64(), nullable=False),
        pa.field("candidate_assignment_count", pa.uint64(), nullable=False),
        pa.field("selected_assignment_count", pa.uint64(), nullable=False),
        pa.field("not_selected_assignment_count", pa.uint64(), nullable=False),
        pa.field("deferred_assignment_count", pa.uint64(), nullable=False),
    ]
)
BUILD_RECEIPT_ARROW_SCHEMA = pa.schema(
    [
        pa.field("receipt_id", pa.string(), nullable=False),
        pa.field("producer_id", pa.string(), nullable=False),
        pa.field("producer_version", pa.string(), nullable=False),
        pa.field("started_at", pa.string(), nullable=False),
        pa.field("completed_at", pa.string(), nullable=False),
        pa.field("release_status", pa.string(), nullable=False),
        pa.field("input_document_release_id", pa.string(), nullable=False),
        pa.field("assignment_policy_id", pa.string(), nullable=False),
        pa.field("record_count", pa.uint64(), nullable=False),
    ]
)
ROLE_ARROW_SCHEMAS = {
    "assignments": ASSIGNMENTS_ARROW_SCHEMA,
    "assignment-evidence": EVIDENCE_ARROW_SCHEMA,
    "assignment-dispositions": DISPOSITIONS_ARROW_SCHEMA,
    "coverage": COVERAGE_ARROW_SCHEMA,
    "build-receipt": BUILD_RECEIPT_ARROW_SCHEMA,
}


def write_parquet(path: Path, role: str, rows: Sequence[Mapping[str, Any]]) -> None:
    """Write one deterministic v2 Parquet member under its closed Arrow schema."""

    schema = ROLE_ARROW_SCHEMAS[role]
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist([dict(row) for row in rows], schema=schema)
    pq.write_table(
        table,
        path,
        compression="zstd",
        compression_level=9,
        use_dictionary=False,
        write_statistics=True,
        data_page_version="1.0",
        version="2.6",
    )


def _same_arrow_schema(actual: pa.Schema, expected: pa.Schema) -> bool:
    return actual.equals(expected, check_metadata=False)


@dataclass
class _BundleState:
    root: dict[str, Any] | None
    members: list[dict[str, Any]]
    member_paths: dict[str, Path]
    rows: dict[str, list[dict[str, Any]]]
    issues: list[VerificationIssue]


def _schema_issues(
    value: Any,
    schema: Mapping[str, Any],
    *,
    path: str,
    code: str = "invalid.schema",
) -> list[VerificationIssue]:
    validator = jsonschema.Draft202012Validator(
        schema, format_checker=jsonschema.FormatChecker()
    )
    issues: list[VerificationIssue] = []
    for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path)):
        suffix = "".join(f"/{part}" for part in error.path)
        _issue(issues, code, f"{path}{suffix}", error.message)
    return issues


def _read_v2_root(
    bundle: Path, issues: list[VerificationIssue]
) -> dict[str, Any] | None:
    root_path = bundle / "release.json"
    if root_path.is_symlink():
        _issue(issues, "invalid.path", "release.json", "root manifest is a symlink")
        return None
    if not root_path.is_file():
        _issue(
            issues,
            "invalid.membership-missing",
            "release.json",
            "root manifest is absent",
        )
        return None
    try:
        root = load_strict_canonical_json(root_path)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _issue(issues, "invalid.root-syntax", "release.json", str(exc))
        return None
    if not isinstance(root, dict):
        _issue(issues, "invalid.root-syntax", "release.json", "root must be an object")
        return None
    if root.get("format") != FORMAT or root.get("formatVersion") != FORMAT_VERSION:
        _issue(
            issues,
            "invalid.format",
            "release.json",
            f"expected {FORMAT!r} version {FORMAT_VERSION!r}",
        )
    try:
        expected = expected_release_id(root)
    except (TypeError, ValueError, rfc8785.CanonicalizationError) as exc:
        _issue(issues, "invalid.identity", "release.json", str(exc))
    else:
        if root.get("releaseId") != expected:
            _issue(
                issues,
                "invalid.identity",
                "release.json/releaseId",
                f"expected {expected}",
            )
    try:
        root_schema = load_v1_json(ROOT_SCHEMA)
        issues.extend(_schema_issues(root, root_schema, path="release.json"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _issue(issues, "invalid.schema", str(ROOT_SCHEMA), str(exc))
    return root


def _validate_manifest_reference(
    reference: Any,
    *,
    expected_kind: str,
    expected_id: str | None,
    path: str,
    issues: list[VerificationIssue],
) -> dict[str, Any] | None:
    if not isinstance(reference, dict):
        _issue(issues, "invalid.schema", path, "manifest reference must be an object")
        return None
    if set(reference) != MANIFEST_REFERENCE_FIELDS:
        _issue(
            issues,
            "invalid.schema",
            path,
            "manifest reference has an unknown or missing field",
        )
    kind = reference.get("scopeKind")
    scope_id = reference.get("scopeId")
    manifest_id = reference.get("manifestId")
    if kind != expected_kind:
        _issue(
            issues, "invalid.schema", f"{path}/scopeKind", f"expected {expected_kind}"
        )
    if expected_id is not None and scope_id != expected_id:
        _issue(issues, "invalid.schema", f"{path}/scopeId", f"expected {expected_id}")
    if not isinstance(scope_id, str) or not scope_id:
        _issue(issues, "invalid.schema", f"{path}/scopeId", "scope ID must be nonempty")
    if isinstance(kind, str) and isinstance(scope_id, str):
        expected_manifest_id = f"{kind}:{scope_id}"
        if manifest_id != expected_manifest_id:
            _issue(
                issues,
                "invalid.schema",
                f"{path}/manifestId",
                f"expected {expected_manifest_id}",
            )
    object_key = reference.get("objectKey")
    if not _safe_object_key(object_key):
        _issue(issues, "invalid.path", f"{path}/objectKey", "unsafe member path")
    byte_size = reference.get("byteSize")
    if (
        not isinstance(byte_size, int)
        or isinstance(byte_size, bool)
        or not 0 <= byte_size <= MAX_SAFE_INTEGER
    ):
        _issue(issues, "invalid.schema", f"{path}/byteSize", "invalid byte size")
    if not isinstance(reference.get("sha256"), str) or not HEX_DIGEST_RE.fullmatch(
        reference.get("sha256", "")
    ):
        _issue(issues, "invalid.schema", f"{path}/sha256", "invalid SHA-256")
    return reference


def _validate_member_descriptor(
    member: Any,
    *,
    scope_kind: str,
    path: str,
    issues: list[VerificationIssue],
) -> dict[str, Any] | None:
    if not isinstance(member, dict):
        _issue(issues, "invalid.schema", path, "member descriptor must be an object")
        return None
    if set(member) != MEMBER_DESCRIPTOR_FIELDS:
        _issue(
            issues,
            "invalid.schema",
            path,
            "member descriptor has an unknown or missing field",
        )
    if not _safe_object_key(member.get("objectKey")):
        _issue(issues, "invalid.path", f"{path}/objectKey", "unsafe member path")
    role = member.get("role")
    if role not in ALLOWED_ROLES:
        _issue(issues, "invalid.schema", f"{path}/role", f"unknown role {role!r}")
    if scope_kind == "global" and role in {
        "assignments",
        "assignment-evidence",
        "assignment-dispositions",
    }:
        _issue(issues, "invalid.schema", f"{path}/role", "partition data is global")
    if scope_kind == "partition" and role in {"schema", "coverage", "build-receipt"}:
        _issue(issues, "invalid.schema", f"{path}/role", "global data is partitioned")
    expected_media = (
        "application/schema+json"
        if role == "schema"
        else "application/vnd.apache.parquet"
    )
    if member.get("mediaType") != expected_media:
        _issue(
            issues,
            "invalid.schema",
            f"{path}/mediaType",
            f"expected {expected_media}",
        )
    byte_size = member.get("byteSize")
    if (
        not isinstance(byte_size, int)
        or isinstance(byte_size, bool)
        or not 0 <= byte_size <= MAX_SAFE_INTEGER
    ):
        _issue(issues, "invalid.schema", f"{path}/byteSize", "invalid byte size")
    if not isinstance(member.get("sha256"), str) or not HEX_DIGEST_RE.fullmatch(
        member.get("sha256", "")
    ):
        _issue(issues, "invalid.schema", f"{path}/sha256", "invalid SHA-256")
    record_count = member.get("recordCount")
    if role == "schema":
        if record_count is not None:
            _issue(
                issues,
                "invalid.schema",
                f"{path}/recordCount",
                "schema count must be null",
            )
    elif (
        not isinstance(record_count, int)
        or isinstance(record_count, bool)
        or not 0 <= record_count <= MAX_SAFE_INTEGER
    ):
        _issue(issues, "invalid.schema", f"{path}/recordCount", "invalid record count")
    schema_id = member.get("schemaId")
    if not isinstance(schema_id, str) or not schema_id:
        _issue(issues, "invalid.schema", f"{path}/schemaId", "schema ID is required")
    if (
        member.get("partitionId") is not None
        or member.get("servingShardId") is not None
    ):
        _issue(
            issues,
            "invalid.schema",
            path,
            "Rulespec members set partitionId and servingShardId to null",
        )
    return member


def _materialized_files(bundle: Path, issues: list[VerificationIssue]) -> set[str]:
    result: set[str] = set()
    for path in bundle.rglob("*"):
        relative = path.relative_to(bundle).as_posix()
        if path.is_symlink():
            _issue(issues, "invalid.path", relative, "symlinks are forbidden")
            result.add(relative)
            continue
        if path.is_file():
            result.add(relative)
    return result


def _read_subordinate_manifests(
    bundle: Path,
    root: Mapping[str, Any],
    issues: list[VerificationIssue],
) -> tuple[list[dict[str, Any]], dict[str, Path], set[str]]:
    content = root.get("content")
    if not isinstance(content, dict):
        return [], {}, {"release.json"}
    raw_global = content.get("globalManifest")
    raw_partitions = content.get("partitionManifests")
    references: list[tuple[dict[str, Any], str]] = []
    global_ref = _validate_manifest_reference(
        raw_global,
        expected_kind="global",
        expected_id="global",
        path="release.json/content/globalManifest",
        issues=issues,
    )
    if global_ref is not None:
        references.append((global_ref, "release.json/content/globalManifest"))
    if not isinstance(raw_partitions, list) or not raw_partitions:
        _issue(
            issues,
            "invalid.schema",
            "release.json/content/partitionManifests",
            "at least one partition manifest is required",
        )
        raw_partitions = []
    manifest_ids = [
        ref.get("manifestId") for ref in raw_partitions if isinstance(ref, dict)
    ]
    if manifest_ids != sorted(manifest_ids):
        _issue(
            issues,
            "invalid.schema",
            "release.json/content/partitionManifests",
            "partition manifests must be sorted by manifestId",
        )
    for index, raw in enumerate(raw_partitions):
        ref = _validate_manifest_reference(
            raw,
            expected_kind="partition",
            expected_id=None,
            path=f"release.json/content/partitionManifests/{index}",
            issues=issues,
        )
        if ref is not None:
            references.append((ref, f"release.json/content/partitionManifests/{index}"))
    seen_manifest_ids: set[str] = set()
    members: list[dict[str, Any]] = []
    member_paths: dict[str, Path] = {}
    declared = {"release.json"}
    for reference, ref_path in references:
        manifest_id = reference.get("manifestId")
        if isinstance(manifest_id, str):
            if manifest_id in seen_manifest_ids:
                _issue(
                    issues,
                    "invalid.duplicate-identity",
                    f"{ref_path}/manifestId",
                    f"duplicate manifest {manifest_id}",
                )
            seen_manifest_ids.add(manifest_id)
        object_key = reference.get("objectKey")
        if not _safe_object_key(object_key):
            continue
        declared.add(object_key)
        path = _member_path(bundle, object_key)
        if path.is_symlink():
            _issue(issues, "invalid.path", object_key, "manifest is a symlink")
            continue
        if not path.is_file():
            _issue(
                issues, "invalid.membership-missing", object_key, "manifest is absent"
            )
            continue
        actual_size = path.stat().st_size
        actual_digest = _file_sha256(path)
        if actual_size != reference.get("byteSize") or actual_digest != reference.get(
            "sha256"
        ):
            _issue(
                issues,
                "invalid.member-digest",
                object_key,
                "manifest size or digest differs",
            )
        try:
            manifest = load_strict_canonical_json(path)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            _issue(issues, "invalid.schema", object_key, str(exc))
            continue
        if (
            not isinstance(manifest, dict)
            or set(manifest) != SUBORDINATE_MANIFEST_FIELDS
        ):
            _issue(
                issues,
                "invalid.schema",
                object_key,
                "invalid subordinate manifest fields",
            )
            continue
        if (
            manifest.get("format") != MEMBER_MANIFEST_FORMAT
            or manifest.get("formatVersion") != MEMBER_MANIFEST_VERSION
        ):
            _issue(
                issues,
                "invalid.schema",
                object_key,
                "unsupported member manifest format",
            )
        scope = manifest.get("scope")
        expected_scope = {
            "kind": reference.get("scopeKind"),
            "id": reference.get("scopeId"),
        }
        if scope != expected_scope or manifest.get("manifestId") != manifest_id:
            _issue(
                issues,
                "invalid.schema",
                object_key,
                "manifest scope differs from reference",
            )
        raw_members = manifest.get("members")
        if not isinstance(raw_members, list):
            _issue(
                issues,
                "invalid.schema",
                f"{object_key}/members",
                "members must be an array",
            )
            raw_members = []
        object_keys = [
            member.get("objectKey")
            for member in raw_members
            if isinstance(member, dict)
        ]
        if object_keys != sorted(object_keys):
            _issue(
                issues,
                "invalid.schema",
                f"{object_key}/members",
                "members must be sorted by objectKey",
            )
        valid_members: list[dict[str, Any]] = []
        for index, raw_member in enumerate(raw_members):
            member = _validate_member_descriptor(
                raw_member,
                scope_kind=str(reference.get("scopeKind")),
                path=f"{object_key}/members/{index}",
                issues=issues,
            )
            if member is None:
                continue
            member_key = member.get("objectKey")
            if _safe_object_key(member_key):
                declared.add(member_key)
                if member_key in member_paths:
                    _issue(
                        issues,
                        "invalid.duplicate-identity",
                        f"{object_key}/members/{index}/objectKey",
                        f"duplicate member {member_key}",
                    )
                else:
                    member_paths[member_key] = _member_path(bundle, member_key)
            elif isinstance(member_key, str) and member_key:
                # Account for a materialized unsafe spelling without resolving
                # it. This keeps the intended first diagnostic at invalid.path.
                declared.add(member_key)
            valid_members.append(member)
            members.append(member)
        counts = manifest.get("counts")
        expected_counts = {
            "memberCount": len(raw_members),
            "totalByteSize": sum(
                member.get("byteSize", 0)
                for member in raw_members
                if isinstance(member, dict)
                and isinstance(member.get("byteSize"), int)
                and not isinstance(member.get("byteSize"), bool)
            ),
            "totalRecordCount": sum(
                member.get("recordCount", 0) or 0
                for member in raw_members
                if isinstance(member, dict)
                and (
                    member.get("recordCount") is None
                    or (
                        isinstance(member.get("recordCount"), int)
                        and not isinstance(member.get("recordCount"), bool)
                    )
                )
            ),
        }
        if counts != expected_counts:
            _issue(
                issues,
                "invalid.schema",
                f"{object_key}/counts",
                f"expected {expected_counts}",
            )
    return members, member_paths, declared


def _verify_member_files(
    bundle: Path,
    members: Sequence[Mapping[str, Any]],
    member_paths: Mapping[str, Path],
    declared: set[str],
    issues: list[VerificationIssue],
) -> None:
    materialized = _materialized_files(bundle, issues)
    for object_key in sorted(declared - materialized):
        _issue(
            issues,
            "invalid.membership-missing",
            object_key,
            "declared member is absent",
        )
    for object_key in sorted(materialized - declared):
        _issue(issues, "invalid.membership-extra", object_key, "file is not declared")
    for member in members:
        object_key = member.get("objectKey")
        if not isinstance(object_key, str) or object_key not in member_paths:
            continue
        path = member_paths[object_key]
        if path.is_symlink() or not path.is_file():
            continue
        try:
            size = path.stat().st_size
            digest = _file_sha256(path)
        except OSError as exc:
            _issue(issues, "invalid.membership-missing", object_key, str(exc))
            continue
        if size != member.get("byteSize") or digest != member.get("sha256"):
            _issue(
                issues,
                "invalid.member-digest",
                object_key,
                "member size or digest differs",
            )


def _validate_schema_set(
    root: Mapping[str, Any],
    members: Sequence[Mapping[str, Any]],
    member_paths: Mapping[str, Path],
    issues: list[VerificationIssue],
) -> dict[str, Mapping[str, Any]]:
    content = root.get("content")
    schema_set = content.get("schemaSet") if isinstance(content, dict) else None
    if not isinstance(schema_set, dict):
        return {}
    descriptors = schema_set.get("schemas")
    if not isinstance(descriptors, list):
        return {}
    ids = [item.get("schemaId") for item in descriptors if isinstance(item, dict)]
    if ids != sorted(ids):
        _issue(
            issues,
            "invalid.schema",
            "release.json/content/schemaSet/schemas",
            "schemas must be sorted by schemaId",
        )
    if set(ids) != set(EXPECTED_SCHEMA_ROLES) or len(ids) != len(EXPECTED_SCHEMA_ROLES):
        _issue(
            issues,
            "invalid.schema",
            "release.json/content/schemaSet/schemas",
            "schema set must contain exactly the registered v2 root and row schemas",
        )
    try:
        expected_set_id = f"urn:spicy:schema-set:v1:{canonical_sha256(descriptors)}"
    except (TypeError, ValueError, rfc8785.CanonicalizationError) as exc:
        _issue(issues, "invalid.schema", "release.json/content/schemaSet", str(exc))
    else:
        if schema_set.get("schemaSetId") != expected_set_id:
            _issue(
                issues,
                "invalid.schema",
                "release.json/content/schemaSet/schemaSetId",
                f"expected {expected_set_id}",
            )
    schema_members: dict[str, Mapping[str, Any]] = {}
    for member in members:
        if member.get("role") == "schema" and isinstance(member.get("schemaId"), str):
            schema_id = member["schemaId"]
            if schema_id in schema_members:
                _issue(
                    issues,
                    "invalid.duplicate-identity",
                    f"member:{member.get('objectKey')}",
                    f"duplicate schema member {schema_id}",
                )
            schema_members[schema_id] = member
    loaded: dict[str, Mapping[str, Any]] = {}
    descriptor_ids: set[str] = set()
    for index, descriptor in enumerate(descriptors):
        path = f"release.json/content/schemaSet/schemas/{index}"
        if not isinstance(descriptor, dict):
            continue
        schema_id = descriptor.get("schemaId")
        if not isinstance(schema_id, str):
            continue
        if schema_id in descriptor_ids:
            _issue(issues, "invalid.duplicate-identity", f"{path}/schemaId", schema_id)
        descriptor_ids.add(schema_id)
        roles = descriptor.get("roles")
        if isinstance(roles, list) and roles != sorted(roles):
            _issue(issues, "invalid.schema", f"{path}/roles", "roles must be sorted")
        expected_roles = EXPECTED_SCHEMA_ROLES.get(schema_id)
        if expected_roles is None or tuple(roles or ()) != expected_roles:
            _issue(
                issues,
                "invalid.schema",
                f"{path}/roles",
                f"expected {list(expected_roles) if expected_roles is not None else 'a registered schema'}",
            )
        member = schema_members.get(schema_id)
        if member is None:
            _issue(
                issues,
                "invalid.foreign-key",
                f"{path}/schemaId",
                "schema descriptor has no schema member",
            )
            continue
        if member.get("sha256") != descriptor.get("schemaSha256"):
            _issue(
                issues,
                "invalid.member-digest",
                f"{path}/schemaSha256",
                "schema descriptor digest differs from member",
            )
        object_key = member.get("objectKey")
        member_path = (
            member_paths.get(object_key) if isinstance(object_key, str) else None
        )
        if member_path is None or not member_path.is_file():
            continue
        try:
            schema = load_v1_json(member_path)
            jsonschema.Draft202012Validator.check_schema(schema)
        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
            jsonschema.SchemaError,
        ) as exc:
            _issue(issues, "invalid.schema", str(object_key), str(exc))
            continue
        if schema.get("$id") != schema_id:
            _issue(
                issues, "invalid.schema", str(object_key), "$id differs from descriptor"
            )
        loaded[schema_id] = schema
    for role, expected_schema_id in ROLE_SCHEMA_IDS.items():
        matching = [
            descriptor
            for descriptor in descriptors
            if isinstance(descriptor, dict) and role in (descriptor.get("roles") or [])
        ]
        if len(matching) != 1 or matching[0].get("schemaId") != expected_schema_id:
            _issue(
                issues,
                "invalid.schema",
                "release.json/content/schemaSet/schemas",
                f"role {role!r} must resolve exactly to {expected_schema_id}",
            )
    return loaded


def _read_data_rows(
    members: Sequence[Mapping[str, Any]],
    member_paths: Mapping[str, Path],
    schemas: Mapping[str, Mapping[str, Any]],
    issues: list[VerificationIssue],
) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {role: [] for role in DATA_ROLES}
    for member in members:
        role = member.get("role")
        if role not in DATA_ROLES:
            continue
        object_key = member.get("objectKey")
        schema_id = member.get("schemaId")
        if schema_id != ROLE_SCHEMA_IDS[role]:
            _issue(
                issues,
                "invalid.schema",
                f"member:{object_key}/schemaId",
                f"expected {ROLE_SCHEMA_IDS[role]}",
            )
        path = member_paths.get(object_key) if isinstance(object_key, str) else None
        if path is None or path.is_symlink() or not path.is_file():
            continue
        try:
            table = pq.read_table(path)
        except (OSError, pa.ArrowException) as exc:
            _issue(issues, "invalid.schema", str(object_key), f"invalid Parquet: {exc}")
            continue
        if not _same_arrow_schema(table.schema, ROLE_ARROW_SCHEMAS[role]):
            _issue(
                issues,
                "invalid.schema",
                str(object_key),
                f"Arrow schema differs for role {role}",
            )
            continue
        if table.num_rows != member.get("recordCount"):
            _issue(
                issues,
                "invalid.schema",
                f"member:{object_key}/recordCount",
                f"expected {table.num_rows}",
            )
        role_rows = table.to_pylist()
        logical_schema = schemas.get(str(schema_id))
        if logical_schema is None:
            _issue(
                issues, "invalid.foreign-key", str(object_key), "row schema is absent"
            )
        else:
            for index, row in enumerate(role_rows):
                issues.extend(
                    _schema_issues(
                        row,
                        logical_schema,
                        path=f"{object_key}/rows/{index}",
                    )
                )
        rows[role].extend(role_rows)
    return rows


def _load_bundle_state(bundle: Path) -> _BundleState:
    issues: list[VerificationIssue] = []
    root = _read_v2_root(bundle, issues)
    if root is None:
        return _BundleState(None, [], {}, {}, issues)
    members, member_paths, declared = _read_subordinate_manifests(bundle, root, issues)
    _verify_member_files(bundle, members, member_paths, declared, issues)
    schemas = _validate_schema_set(root, members, member_paths, issues)
    rows = _read_data_rows(members, member_paths, schemas, issues)
    return _BundleState(root, members, member_paths, rows, issues)


def load_document_release_view(bundle: Path) -> DocumentReleaseView:
    """Verify the v3 file seam needed to reproduce the active document set.

    This is intentionally a consumer-side reader, not a source-package import.
    It verifies root identity, complete materialized membership, member bytes,
    and the current-document/document/passage keys used by assignment checks.
    The owning SpicyRegs validator remains responsible for the full v3 release
    conformance class.
    """

    root_path = bundle / "release.json"
    root = load_strict_canonical_json(root_path)
    if not isinstance(root, dict):
        raise ValueError("DocumentRelease root must be an object")
    if (
        root.get("format") != "spicyregs-document-release"
        or root.get("formatVersion") != "3.0"
    ):
        raise ValueError("expected spicyregs-document-release version 3.0")
    payload = {
        "format": root["format"],
        "formatVersion": root["formatVersion"],
        "content": root.get("content"),
    }
    artifact_digest = canonical_sha256(payload)
    release_id = f"urn:spicyregs:document-release:v3:{artifact_digest}"
    if root.get("releaseId") != release_id:
        raise ValueError(f"DocumentRelease identity differs; expected {release_id}")
    content = root.get("content")
    if not isinstance(content, dict):
        raise ValueError("DocumentRelease content must be an object")
    references = [
        content.get("globalManifest"),
        *(content.get("partitionManifests") or []),
    ]
    descriptors: list[dict[str, Any]] = []
    declared = {"release.json"}
    seen_keys: set[str] = set()
    for reference in references:
        if (
            not isinstance(reference, dict)
            or set(reference) != MANIFEST_REFERENCE_FIELDS
        ):
            raise ValueError("DocumentRelease contains an invalid manifest reference")
        object_key = reference.get("objectKey")
        if not _safe_object_key(object_key):
            raise ValueError(f"unsafe DocumentRelease manifest path {object_key!r}")
        declared.add(object_key)
        path = _member_path(bundle, object_key)
        if path.is_symlink() or not path.is_file():
            raise ValueError(
                f"DocumentRelease manifest is missing or linked: {object_key}"
            )
        if path.stat().st_size != reference.get("byteSize") or _file_sha256(
            path
        ) != reference.get("sha256"):
            raise ValueError(f"DocumentRelease manifest digest differs: {object_key}")
        manifest = load_strict_canonical_json(path)
        if (
            not isinstance(manifest, dict)
            or set(manifest) != SUBORDINATE_MANIFEST_FIELDS
        ):
            raise ValueError(f"invalid DocumentRelease manifest: {object_key}")
        if (
            manifest.get("format") != MEMBER_MANIFEST_FORMAT
            or manifest.get("formatVersion") != MEMBER_MANIFEST_VERSION
        ):
            raise ValueError(
                f"unsupported DocumentRelease member manifest: {object_key}"
            )
        expected_scope = {
            "kind": reference.get("scopeKind"),
            "id": reference.get("scopeId"),
        }
        if (
            manifest.get("manifestId") != reference.get("manifestId")
            or manifest.get("scope") != expected_scope
        ):
            raise ValueError(f"DocumentRelease manifest scope differs: {object_key}")
        members = manifest.get("members")
        if not isinstance(members, list) or [
            item.get("objectKey") for item in members if isinstance(item, dict)
        ] != sorted(
            item.get("objectKey") for item in members if isinstance(item, dict)
        ):
            raise ValueError(f"DocumentRelease members are not sorted: {object_key}")
        expected_counts = {
            "memberCount": len(members),
            "totalByteSize": sum(item.get("byteSize", 0) for item in members),
            "totalRecordCount": sum(item.get("recordCount") or 0 for item in members),
        }
        if manifest.get("counts") != expected_counts:
            raise ValueError(f"DocumentRelease manifest counts differ: {object_key}")
        for descriptor in members:
            if (
                not isinstance(descriptor, dict)
                or set(descriptor) != MEMBER_DESCRIPTOR_FIELDS
            ):
                raise ValueError(
                    f"invalid DocumentRelease member descriptor: {object_key}"
                )
            member_key = descriptor.get("objectKey")
            if not _safe_object_key(member_key):
                raise ValueError(f"unsafe DocumentRelease member path {member_key!r}")
            if member_key in seen_keys:
                raise ValueError(f"duplicate DocumentRelease member {member_key}")
            seen_keys.add(member_key)
            declared.add(member_key)
            descriptors.append(descriptor)
    actual: set[str] = set()
    for path in bundle.rglob("*"):
        relative = path.relative_to(bundle).as_posix()
        if path.is_symlink():
            raise ValueError(f"DocumentRelease symlink is forbidden: {relative}")
        if path.is_file():
            actual.add(relative)
    if declared != actual:
        missing = sorted(declared - actual)
        extra = sorted(actual - declared)
        raise ValueError(
            f"DocumentRelease membership differs; missing={missing}, extra={extra}"
        )
    role_tables: dict[str, list[pa.Table]] = {
        "current-documents": [],
        "documents": [],
        "passages": [],
    }
    for descriptor in descriptors:
        member_key = descriptor["objectKey"]
        member_path = _member_path(bundle, member_key)
        if member_path.stat().st_size != descriptor.get("byteSize") or _file_sha256(
            member_path
        ) != descriptor.get("sha256"):
            raise ValueError(f"DocumentRelease member digest differs: {member_key}")
        role = descriptor.get("role")
        if role in role_tables:
            table = pq.read_table(member_path)
            if table.num_rows != descriptor.get("recordCount"):
                raise ValueError(f"DocumentRelease record count differs: {member_key}")
            role_tables[role].append(table)
    if not all(role_tables.values()):
        raise ValueError(
            "DocumentRelease lacks current-documents, documents, or passages"
        )
    current_rows = [
        row for table in role_tables["current-documents"] for row in table.to_pylist()
    ]
    document_rows = [
        row for table in role_tables["documents"] for row in table.to_pylist()
    ]
    passage_rows = [
        row for table in role_tables["passages"] for row in table.to_pylist()
    ]
    active_documents: dict[str, str] = {}
    for row in current_rows:
        if row.get("state") != "active":
            continue
        document_id = row.get("document_id")
        version_id = row.get("document_version_id")
        if not isinstance(document_id, str) or not isinstance(version_id, str):
            raise ValueError("DocumentRelease active row lacks document identity")
        if document_id in active_documents:
            raise ValueError(f"duplicate active DocumentRelease identity {document_id}")
        active_documents[document_id] = version_id
    normalized_text: dict[str, str] = {}
    for row in document_rows:
        version_id = row.get("document_version_id")
        text = row.get("normalized_text")
        if isinstance(version_id, str) and isinstance(text, str):
            if version_id in normalized_text:
                raise ValueError(f"duplicate DocumentRelease version {version_id}")
            normalized_text[version_id] = text
    passages: dict[str, tuple[str, str, str]] = {}
    passage_records: dict[str, Mapping[str, Any]] = {}
    for row in passage_rows:
        passage_id = row.get("passage_id")
        document_id = row.get("document_id")
        version_id = row.get("document_version_id")
        digest_value = row.get("text_digest")
        if isinstance(digest_value, memoryview):
            digest_value = digest_value.tobytes()
        if isinstance(digest_value, bytes):
            digest = f"sha256:{digest_value.hex()}"
        elif isinstance(digest_value, str) and SHA256_RE.fullmatch(digest_value):
            digest = digest_value
        else:
            raise ValueError(f"passage {passage_id!r} has an invalid text digest")
        if not all(
            isinstance(value, str) for value in (passage_id, document_id, version_id)
        ):
            raise ValueError("DocumentRelease passage lacks identity")
        if passage_id in passages:
            raise ValueError(f"duplicate passage {passage_id}")
        passages[passage_id] = (document_id, version_id, digest)
        passage_records[passage_id] = row
    for document_id, version_id in active_documents.items():
        if version_id not in normalized_text:
            raise ValueError(f"active document {document_id} has no documents row")
    return DocumentReleaseView(
        release_id=release_id,
        artifact_digest=artifact_digest,
        active_documents=active_documents,
        passages=passages,
        normalized_text=normalized_text,
        passage_records=passage_records,
    )


V1_RECORD_DEFS = {
    "ConceptAssignment": "conceptAssignment",
    "EvidenceBinding": "evidenceBinding",
    "ExtractionActivity": "extractionActivity",
    "AILineage": "aiLineage",
    "ProcessingSegment": "processingSegment",
    "DerivedTextProjection": "derivedTextProjection",
    "PortableArtifact": "portableArtifact",
    "AgentValidationReceipt": "agentValidationReceipt",
    "BaselineValidationReceipt": "baselineValidationReceipt",
    "ExtrapolationSelectionReceipt": "extrapolationSelectionReceipt",
}


def _v1_record_schema(
    root_schema: Mapping[str, Any], record_type: str
) -> dict[str, Any]:
    definition = V1_RECORD_DEFS[record_type]
    # Retain the complete definition registry so local $refs continue to resolve.
    schema = dict(root_schema["$defs"][definition])
    schema["$defs"] = root_schema["$defs"]
    schema["$schema"] = root_schema["$schema"]
    return schema


def _strict_v1_record_json(value: str) -> dict[str, Any]:
    record = json.loads(
        value,
        parse_constant=_reject_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )
    if not isinstance(record, dict):
        raise ValueError("record_json must encode an object")
    if v1_canonical_json_bytes(record).decode("utf-8") != value:
        raise ValueError("record_json is not canonical Rulespec v1 JSON")
    return record


def _assignment_record(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "ConceptAssignment",
        "record_id": row.get("assignment_id"),
        "asserts_subject_ref": row.get("subject_ref"),
        "subject_kind": row.get("subject_kind"),
        "asserts_predicate": row.get("predicate"),
        "asserts_object_ref": row.get("concept_id"),
        "assertion_polarity": row.get("polarity"),
        "assigned_concept_release_ref": row.get("assigned_concept_release_id"),
        "assertion_origin": row.get("origin"),
        "usage_eligibility": row.get("usage_eligibility"),
        "evidence_binding_refs": row.get("evidence_binding_refs"),
        "extraction_activity_ref": row.get("extraction_activity_id"),
        "ai_lineage_ref": row.get("ai_lineage_id"),
    }


def v2_selection_context_digest(
    content: Mapping[str, Any],
    assignments: Sequence[Mapping[str, Any]],
    evidence_records: Sequence[Mapping[str, Any]],
) -> str:
    """Bind packaged selection receipts to the complete pre-selection graph."""

    evidence_without_selection = [
        record
        for record in evidence_records
        if record.get("record_type") != "ExtrapolationSelectionReceipt"
    ]
    normalized_assignments: list[dict[str, Any]] = []
    for raw in assignments:
        row = dict(raw)
        confidence = row.get("confidence")
        if isinstance(confidence, float):
            if not math.isfinite(confidence):
                raise ValueError("confidence must be finite")
            # Manifests prohibit floats.  A normalized decimal string binds the
            # diagnostic column without turning it into a policy threshold.
            row["confidence"] = format(confidence, ".17g")
        normalized_assignments.append(row)
    preimage = {
        "input_releases": content.get("input_releases"),
        "profile": content.get("profile"),
        "assignmentPolicy": content.get("assignmentPolicy"),
        "validation_sample_manifest": content.get("validation_sample_manifest"),
        "assignments": sorted(
            normalized_assignments, key=lambda row: str(row.get("assignment_id"))
        ),
        "assignment_evidence": sorted(
            evidence_without_selection, key=lambda row: str(row.get("record_id"))
        ),
    }
    return f"sha256:{canonical_sha256(preimage)}"


def _text_digest(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _validate_projection_coordinates(
    evidence_records: Mapping[str, Mapping[str, Any]],
    document_release: DocumentReleaseView,
    issues: list[VerificationIssue],
) -> None:
    """Replay every published source slice against the pinned passages."""

    projections = {
        record_id: record
        for record_id, record in evidence_records.items()
        if record.get("record_type") == "DerivedTextProjection"
    }
    for segment_id, segment in evidence_records.items():
        if segment.get("record_type") != "ProcessingSegment":
            continue
        path = f"record:{segment_id}"
        projection = projections.get(str(segment.get("projection_ref")))
        if projection is None:
            continue
        derived_text = segment.get("derived_text")
        if not isinstance(derived_text, str):
            continue
        expected_digest = _text_digest(derived_text)
        if segment.get("derived_text_digest") != expected_digest:
            _issue(
                issues,
                "invalid.coordinate",
                f"{path}/derived_text_digest",
                f"expected {expected_digest}",
            )
        projection_path = f"record:{projection.get('record_id')}"
        if projection.get("derived_unit_ref") != segment_id:
            _issue(
                issues,
                "invalid.coordinate",
                f"{projection_path}/derived_unit_ref",
                "projection and processing segment references must be reciprocal",
            )
        if projection.get("derived_text_digest") != expected_digest:
            _issue(
                issues,
                "invalid.coordinate",
                f"{projection_path}/derived_text_digest",
                f"expected {expected_digest}",
            )
        input_refs = projection.get("input_fragment_refs")
        if not isinstance(input_refs, list) or input_refs != segment.get(
            "input_fragment_refs"
        ):
            _issue(
                issues,
                "invalid.coordinate",
                f"{projection_path}/input_fragment_refs",
                "projection inputs must exactly match the processing segment",
            )
            input_refs = []
        for index, fragment_ref in enumerate(input_refs):
            if fragment_ref not in document_release.passage_records:
                _issue(
                    issues,
                    "invalid.coordinate",
                    f"{projection_path}/input_fragment_refs/{index}",
                    "input passage does not resolve in the pinned DocumentRelease",
                )

        slices = projection.get("ordered_slices")
        if not isinstance(slices, list) or not slices:
            _issue(
                issues,
                "invalid.coordinate",
                f"{projection_path}/ordered_slices",
                "projection requires one or more ordered slices",
            )
            continue
        cursor = 0
        for index, item in enumerate(slices):
            item_path = f"{projection_path}/ordered_slices/{index}"
            if not isinstance(item, dict):
                _issue(
                    issues, "invalid.coordinate", item_path, "slice must be an object"
                )
                continue
            start = item.get("derived_start")
            end = item.get("derived_end")
            if (
                isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
                or start != cursor
                or end < start
                or end > len(derived_text)
            ):
                _issue(
                    issues,
                    "invalid.coordinate",
                    item_path,
                    f"next half-open derived slice must start at {cursor}",
                )
                if isinstance(end, int) and not isinstance(end, bool):
                    cursor = max(cursor, end)
                continue
            derived_slice = derived_text[start:end]
            kind = item.get("slice_kind")
            if kind == "source_range":
                source_refs = item.get("source_fragment_refs")
                if not isinstance(source_refs, list) or not source_refs:
                    _issue(
                        issues,
                        "invalid.coordinate",
                        f"{item_path}/source_fragment_refs",
                        "source range must name at least one input passage",
                    )
                    source_refs = []
                elif any(ref not in input_refs for ref in source_refs):
                    _issue(
                        issues,
                        "invalid.coordinate",
                        f"{item_path}/source_fragment_refs",
                        "source range may use only declared segment inputs",
                    )
                source_start = item.get("source_start")
                source_end = item.get("source_end")
                representation_ref = item.get("source_text_representation_ref")
                if len(source_refs) != 1:
                    _issue(
                        issues,
                        "invalid.coordinate",
                        f"{item_path}/source_fragment_refs",
                        "one source slice must resolve to one exact passage",
                    )
                else:
                    passage = document_release.passage_records.get(source_refs[0])
                    source_text = passage.get("text") if passage is not None else None
                    if (
                        passage is None
                        or passage.get("document_version_id") != representation_ref
                        or not isinstance(source_text, str)
                        or isinstance(source_start, bool)
                        or not isinstance(source_start, int)
                        or isinstance(source_end, bool)
                        or not isinstance(source_end, int)
                        or source_start < 0
                        or source_end < source_start
                        or source_end > len(source_text)
                    ):
                        _issue(
                            issues,
                            "invalid.coordinate",
                            item_path,
                            "source range must resolve within the named pinned passage",
                        )
                    elif source_text[source_start:source_end] != derived_slice:
                        _issue(
                            issues,
                            "invalid.coordinate",
                            item_path,
                            "derived source range differs from the pinned passage text",
                        )
            elif kind == "inserted_text":
                inserted_text = item.get("inserted_text")
                if (
                    not isinstance(inserted_text, str)
                    or inserted_text != derived_slice
                    or item.get("inserted_text_digest") != _text_digest(inserted_text)
                ):
                    _issue(
                        issues,
                        "invalid.coordinate",
                        item_path,
                        "inserted text and digest must reproduce the derived slice",
                    )
            elif kind == "transformed_range":
                if not item.get("transform_method_version"):
                    _issue(
                        issues,
                        "invalid.coordinate",
                        item_path,
                        "transformed range must name its transform version",
                    )
            else:
                _issue(
                    issues,
                    "invalid.coordinate",
                    f"{item_path}/slice_kind",
                    f"unsupported slice kind {kind!r}",
                )
            cursor = end
        if cursor != len(derived_text):
            _issue(
                issues,
                "invalid.coordinate",
                f"{projection_path}/ordered_slices",
                f"projection accounts for {cursor} of {len(derived_text)} code points",
            )
        for index, omitted in enumerate(projection.get("omitted_source_ranges") or []):
            omitted_path = f"{projection_path}/omitted_source_ranges/{index}"
            if not isinstance(omitted, dict):
                _issue(
                    issues,
                    "invalid.coordinate",
                    omitted_path,
                    "omitted range must be an object",
                )
                continue
            source_text = document_release.normalized_text.get(
                str(omitted.get("source_text_representation_ref"))
            )
            start = omitted.get("source_start")
            end = omitted.get("source_end")
            if (
                source_text is None
                or isinstance(start, bool)
                or not isinstance(start, int)
                or isinstance(end, bool)
                or not isinstance(end, int)
                or start < 0
                or end < start
                or end > len(source_text)
            ):
                _issue(
                    issues,
                    "invalid.coordinate",
                    omitted_path,
                    "omitted range must resolve within the pinned document text",
                )


def _validate_root_rollups(
    state: _BundleState,
    dispositions: Sequence[Mapping[str, Any]],
    issues: list[VerificationIssue],
) -> None:
    assert state.root is not None
    content = state.root.get("content")
    if not isinstance(content, dict):
        return
    counts = content.get("counts")
    if not isinstance(counts, dict):
        return
    disposition_counts = Counter(row.get("disposition") for row in dispositions)
    expected = {
        "activeDocumentCount": len(dispositions),
        "assignedDocumentCount": disposition_counts["assigned"],
        "abstainedDocumentCount": disposition_counts["abstained"],
        "excludedDocumentCount": disposition_counts["excluded"],
        "failedDocumentCount": disposition_counts["failed"],
        "assignmentCount": len(state.rows.get("assignments", [])),
        "assignmentEvidenceCount": len(state.rows.get("assignment-evidence", [])),
        "coverageRecordCount": len(state.rows.get("coverage", [])),
        "buildReceiptCount": len(state.rows.get("build-receipt", [])),
        "partitionManifestCount": len(content.get("partitionManifests") or []),
        "memberCount": len(state.members),
        "totalMemberByteSize": sum(
            member.get("byteSize", 0)
            for member in state.members
            if isinstance(member.get("byteSize"), int)
            and not isinstance(member.get("byteSize"), bool)
        ),
    }
    if counts != expected:
        _issue(
            issues,
            "invalid.statistics",
            "release.json/content/counts",
            f"expected {expected}",
        )


def _validate_assignments_and_evidence(
    state: _BundleState,
    document_release: DocumentReleaseView,
    atlas: AtlasMembershipReader | None,
    issues: list[VerificationIssue],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    assert state.root is not None
    content = state.root.get("content")
    if not isinstance(content, dict):
        return {}, {}
    assignment_policy = content.get("assignmentPolicy")
    if isinstance(assignment_policy, dict):
        policy_preimage = {
            key: value
            for key, value in assignment_policy.items()
            if key != "policySha256"
        }
        try:
            expected_policy_digest = canonical_sha256(policy_preimage)
        except (TypeError, ValueError, rfc8785.CanonicalizationError) as exc:
            _issue(
                issues,
                "invalid.schema",
                "release.json/content/assignmentPolicy",
                str(exc),
            )
        else:
            if assignment_policy.get("policySha256") != expected_policy_digest:
                _issue(
                    issues,
                    "invalid.schema",
                    "release.json/content/assignmentPolicy/policySha256",
                    f"expected {expected_policy_digest}",
                )
    input_pins = content.get("input_releases")
    if isinstance(input_pins, dict):
        if input_pins.get("document_release") != document_release.v1_pin:
            _issue(
                issues,
                "invalid.assignment-pin",
                "release.json/content/input_releases/document_release",
                f"expected {document_release.v1_pin}",
            )
        if atlas is not None:
            try:
                atlas_pin = dict(atlas.pin())
            except (TypeError, ValueError) as exc:
                _issue(issues, "invalid.assignment-pin", "$inputs/atlas", str(exc))
            else:
                if input_pins.get("vocabulary_atlas_asset") != atlas_pin:
                    _issue(
                        issues,
                        "invalid.assignment-pin",
                        "release.json/content/input_releases/vocabulary_atlas_asset",
                        "atlas pin differs from verified bytes",
                    )
    try:
        v1_schema = load_v1_json(V1_SCHEMA)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        _issue(issues, "invalid.schema", str(V1_SCHEMA), str(exc))
        return {}, {}
    assignment_rows: dict[str, dict[str, Any]] = {}
    assignments_by_document: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(state.rows.get("assignments", [])):
        path = f"assignments/rows/{index}"
        assignment_id = row.get("assignment_id")
        if not isinstance(assignment_id, str):
            continue
        if assignment_id in assignment_rows:
            _issue(
                issues,
                "invalid.duplicate-identity",
                f"{path}/assignment_id",
                assignment_id,
            )
            continue
        assignment_rows[assignment_id] = row
        document_id = row.get("document_id")
        version_id = row.get("document_version_id")
        if document_release.active_documents.get(document_id) != version_id:
            _issue(
                issues,
                "invalid.foreign-key",
                path,
                "assignment does not resolve to the pinned active document version",
            )
        assignments_by_document.setdefault(str(document_id), []).append(row)
        record = _assignment_record(row)
        issues.extend(
            _schema_issues(
                record,
                _v1_record_schema(v1_schema, "ConceptAssignment"),
                path=path,
                code="invalid.assignment-evidence",
            )
        )
        try:
            expected_id = stable_record_id(record)
        except (TypeError, ValueError) as exc:
            _issue(issues, "invalid.assignment-evidence", path, str(exc))
        else:
            if assignment_id != expected_id:
                _issue(
                    issues,
                    "invalid.assignment-evidence",
                    f"{path}/assignment_id",
                    f"expected {expected_id}",
                )
        confidence = row.get("confidence")
        if confidence is not None and (
            isinstance(confidence, bool)
            or not isinstance(confidence, (int, float))
            or not math.isfinite(confidence)
        ):
            _issue(
                issues,
                "invalid.schema",
                f"{path}/confidence",
                "confidence must be null or a finite diagnostic value",
            )
        if atlas is not None:
            try:
                atlas.require_member(
                    member_id=str(row.get("concept_id")),
                    release_id=str(row.get("assigned_concept_release_id")),
                )
            except (KeyError, TypeError, ValueError) as exc:
                _issue(issues, "invalid.foreign-key", f"{path}/concept_id", str(exc))
        reference_pin = (
            input_pins.get("reference_resource_release")
            if isinstance(input_pins, dict)
            else None
        )
        if isinstance(reference_pin, dict) and row.get(
            "assigned_concept_release_id"
        ) != reference_pin.get("release_id"):
            _issue(
                issues,
                "invalid.assignment-pin",
                f"{path}/assigned_concept_release_id",
                "assignment pins another reference resource release",
            )

    evidence_records: dict[str, dict[str, Any]] = {}
    evidence_rows: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(state.rows.get("assignment-evidence", [])):
        path = f"assignment-evidence/rows/{index}"
        record_id = row.get("record_id")
        record_type = row.get("record_type")
        if not isinstance(record_id, str) or not isinstance(record_type, str):
            continue
        if record_id in evidence_records:
            _issue(issues, "invalid.duplicate-identity", f"{path}/record_id", record_id)
            continue
        try:
            record = _strict_v1_record_json(str(row.get("record_json")))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            _issue(
                issues, "invalid.assignment-evidence", f"{path}/record_json", str(exc)
            )
            continue
        schema_name = V1_RECORD_DEFS.get(record_type)
        if schema_name is None:
            _issue(issues, "invalid.schema", f"{path}/record_type", record_type)
            continue
        schema = dict(v1_schema["$defs"][schema_name])
        schema["$defs"] = v1_schema["$defs"]
        schema["$schema"] = v1_schema["$schema"]
        issues.extend(
            _schema_issues(
                record,
                schema,
                path=f"{path}/record_json",
                code="invalid.assignment-evidence",
            )
        )
        actual_type = record.get("record_type", "PortableArtifact")
        if actual_type != record_type:
            _issue(
                issues,
                "invalid.assignment-evidence",
                f"{path}/record_type",
                f"record carries {actual_type!r}",
            )
        contained_id = (
            record.get("artifact_id")
            if record_type == "PortableArtifact"
            else record.get("record_id")
        )
        if contained_id != record_id:
            _issue(
                issues,
                "invalid.assignment-evidence",
                f"{path}/record_id",
                "packaging identity differs from record_json",
            )
        if record_type not in {"PortableArtifact"}:
            try:
                expected_id = stable_record_id(record)
            except (TypeError, ValueError) as exc:
                _issue(issues, "invalid.assignment-evidence", path, str(exc))
            else:
                if expected_id != record_id:
                    _issue(
                        issues,
                        "invalid.assignment-evidence",
                        f"{path}/record_id",
                        f"expected {expected_id}",
                    )
        evidence_records[record_id] = record
        evidence_rows[record_id] = row

    for assignment_id, row in assignment_rows.items():
        path = f"assignment:{assignment_id}"
        for binding_ref in row.get("evidence_binding_refs") or []:
            binding = evidence_records.get(binding_ref)
            if binding is None or binding.get("record_type") != "EvidenceBinding":
                _issue(
                    issues,
                    "invalid.assignment-evidence",
                    path,
                    f"evidence binding {binding_ref!r} does not resolve",
                )
                continue
            if binding.get("binds_assignment_ref") != assignment_id:
                _issue(
                    issues,
                    "invalid.assignment-evidence",
                    path,
                    "evidence binding points at another assignment",
                )
            for span in binding.get("evidence_spans") or []:
                if not isinstance(span, dict):
                    continue
                passage_id = span.get("source_fragment_ref")
                passage = document_release.passages.get(str(passage_id))
                if passage is None:
                    _issue(
                        issues,
                        "invalid.assignment-evidence",
                        path,
                        f"evidence passage {passage_id!r} does not resolve",
                    )
                    continue
                document_id, version_id, digest = passage
                if (
                    document_id != row.get("document_id")
                    or version_id != row.get("document_version_id")
                    or digest != span.get("selected_text_digest")
                ):
                    _issue(
                        issues,
                        "invalid.assignment-evidence",
                        path,
                        "evidence passage identity or digest differs",
                    )
        for field, record_type in (
            ("extraction_activity_id", "ExtractionActivity"),
            ("ai_lineage_id", "AILineage"),
        ):
            ref = row.get(field)
            target = evidence_records.get(str(ref))
            if target is None or target.get("record_type") != record_type:
                _issue(
                    issues,
                    "invalid.assignment-evidence",
                    f"{path}/{field}",
                    f"{record_type} does not resolve",
                )
        selection_receipts = [
            record
            for record in evidence_records.values()
            if record.get("record_type") == "ExtrapolationSelectionReceipt"
            and record.get("assignment_ref") == assignment_id
        ]
        if len(selection_receipts) != 1:
            _issue(
                issues,
                "invalid.assignment-evidence",
                path,
                "assignment must resolve exactly one selection receipt",
            )
        elif selection_receipts[0].get("selection_result") != row.get(
            "selection_result"
        ):
            _issue(
                issues,
                "invalid.assignment-evidence",
                path,
                "selection receipt differs from assignment row",
            )

    for record in evidence_records.values():
        record_type = record.get("record_type")
        if record_type == "ExtractionActivity":
            target = evidence_records.get(str(record.get("processing_segment_ref")))
            if target is None or target.get("record_type") != "ProcessingSegment":
                _issue(
                    issues,
                    "invalid.assignment-evidence",
                    f"record:{record.get('record_id')}",
                    "processing segment does not resolve",
                )
        elif record_type == "ProcessingSegment":
            if record.get("document_release_ref") != document_release.release_id:
                _issue(
                    issues,
                    "invalid.assignment-pin",
                    f"record:{record.get('record_id')}/document_release_ref",
                    "processing segment pins another DocumentRelease",
                )
            target = evidence_records.get(str(record.get("projection_ref")))
            if target is None or target.get("record_type") != "DerivedTextProjection":
                _issue(
                    issues,
                    "invalid.assignment-evidence",
                    f"record:{record.get('record_id')}",
                    "derived projection does not resolve",
                )
        elif record_type == "BaselineValidationReceipt":
            refs = record.get("agent_validation_receipt_refs") or []
            attempts = [evidence_records.get(str(ref)) for ref in refs]
            if len(attempts) != 2 or any(
                attempt is None
                or attempt.get("record_type") != "AgentValidationReceipt"
                or attempt.get("execution_status") != "completed"
                or attempt.get("overall_recommendation") != "supports"
                for attempt in attempts
            ):
                _issue(
                    issues,
                    "invalid.assignment-evidence",
                    f"record:{record.get('record_id')}",
                    "baseline requires exactly two completed supporting attempts",
                )
            elif any(
                len({str(attempt.get(field)) for attempt in attempts}) != 2
                for field in (
                    "validator_actor_ref",
                    "independence_group",
                    "provider_model_id",
                    "response_artifact_ref",
                )
            ):
                _issue(
                    issues,
                    "invalid.assignment-evidence",
                    f"record:{record.get('record_id')}",
                    "baseline validator attempts are not independent",
                )
    _validate_projection_coordinates(evidence_records, document_release, issues)
    validation_manifest = content.get("validation_sample_manifest")
    if isinstance(validation_manifest, dict):
        refs = validation_manifest.get("record_refs")
        if isinstance(refs, list):
            expected_manifest_digest = canonical_digest({"record_refs": refs})
            if validation_manifest.get("manifest_digest") != expected_manifest_digest:
                _issue(
                    issues,
                    "invalid.assignment-evidence",
                    "release.json/content/validation_sample_manifest/manifest_digest",
                    f"expected {expected_manifest_digest}",
                )
            known_refs = {
                *assignment_rows,
                *evidence_records,
                *document_release.passages,
                *(str(row.get("concept_id")) for row in assignment_rows.values()),
            }
            for index, ref in enumerate(refs):
                if ref not in known_refs:
                    _issue(
                        issues,
                        "invalid.assignment-evidence",
                        f"release.json/content/validation_sample_manifest/record_refs/{index}",
                        f"sample reference {ref!r} does not resolve",
                    )
    expected_context = v2_selection_context_digest(
        content,
        state.rows.get("assignments", []),
        state.rows.get("assignment-evidence", []),
    )
    if content.get("selection_context_digest") != expected_context:
        _issue(
            issues,
            "invalid.assignment-evidence",
            "release.json/content/selection_context_digest",
            f"expected {expected_context}",
        )
    for record in evidence_records.values():
        if (
            record.get("record_type") == "ExtrapolationSelectionReceipt"
            and record.get("selection_context_digest") != expected_context
        ):
            _issue(
                issues,
                "invalid.assignment-evidence",
                f"record:{record.get('record_id')}/selection_context_digest",
                "selection receipt is not bound to this v2 graph",
            )
    return assignment_rows, evidence_rows


def _validate_dispositions_and_coverage(
    state: _BundleState,
    document_release: DocumentReleaseView,
    assignments: Mapping[str, Mapping[str, Any]],
    evidence_rows: Mapping[str, Mapping[str, Any]],
    issues: list[VerificationIssue],
) -> None:
    disposition_rows = state.rows.get("assignment-dispositions", [])
    by_document: dict[str, dict[str, Any]] = {}
    assignments_by_document: dict[str, list[Mapping[str, Any]]] = {}
    for assignment in assignments.values():
        assignments_by_document.setdefault(
            str(assignment.get("document_id")), []
        ).append(assignment)
    for index, row in enumerate(disposition_rows):
        path = f"assignment-dispositions/rows/{index}"
        document_id = row.get("document_id")
        if not isinstance(document_id, str):
            continue
        if document_id in by_document:
            _issue(
                issues,
                "invalid.duplicate-identity",
                f"{path}/document_id",
                document_id,
            )
            continue
        by_document[document_id] = row
        if document_release.active_documents.get(document_id) != row.get(
            "document_version_id"
        ):
            _issue(
                issues,
                "invalid.assignment-disposition",
                path,
                "disposition does not resolve to the pinned active version",
            )
        actual_assignments = assignments_by_document.get(document_id, [])
        actual_selected = [
            assignment
            for assignment in actual_assignments
            if assignment.get("selection_result") == "selected"
        ]
        actual_evidence = [
            row
            for row in evidence_rows.values()
            if row.get("assignment_id")
            in {assignment.get("assignment_id") for assignment in actual_assignments}
        ]
        expected_counts = (
            len(actual_assignments),
            len(actual_selected),
            len(actual_evidence),
        )
        declared_counts = (
            row.get("assignment_count"),
            row.get("selected_assignment_count"),
            row.get("evidence_record_count"),
        )
        if expected_counts != declared_counts:
            _issue(
                issues,
                "invalid.assignment-disposition",
                path,
                f"declared assignment/evidence counts {declared_counts} differ from {expected_counts}",
            )
        disposition = row.get("disposition")
        if disposition == "assigned":
            if not actual_selected or row.get("failure_id") is not None:
                _issue(
                    issues,
                    "invalid.assignment-disposition",
                    path,
                    "assigned requires a selected assignment and no failure",
                )
        elif disposition in {"abstained", "excluded"}:
            if actual_assignments or row.get("failure_id") is not None:
                _issue(
                    issues,
                    "invalid.assignment-disposition",
                    path,
                    f"{disposition} requires zero assignments and no failure",
                )
        elif disposition == "failed":
            if actual_assignments or not isinstance(row.get("failure_id"), str):
                _issue(
                    issues,
                    "invalid.assignment-disposition",
                    path,
                    "failed requires zero assignments and a failure ID",
                )
        if not isinstance(row.get("reason_code"), str) or not REASON_CODE_RE.fullmatch(
            row.get("reason_code", "")
        ):
            _issue(
                issues,
                "invalid.schema",
                f"{path}/reason_code",
                "invalid producer diagnostic code",
            )
    active_set = set(document_release.active_documents)
    disposition_set = set(by_document)
    if active_set != disposition_set:
        _issue(
            issues,
            "invalid.assignment-disposition",
            "assignment-dispositions",
            f"active/disposition sets differ; missing={sorted(active_set - disposition_set)}, "
            f"foreign={sorted(disposition_set - active_set)}",
        )
    coverage_rows = state.rows.get("coverage", [])
    global_rows = [
        row
        for row in coverage_rows
        if row.get("scope_kind") == "global" and row.get("scope_id") == "global"
    ]
    scope_ids = [(row.get("scope_kind"), row.get("scope_id")) for row in coverage_rows]
    if len(scope_ids) != len(set(scope_ids)):
        _issue(
            issues, "invalid.duplicate-identity", "coverage", "duplicate coverage scope"
        )
    if len(global_rows) != 1:
        _issue(
            issues,
            "invalid.statistics",
            "coverage",
            "exactly one global row is required",
        )
    else:
        row = global_rows[0]
        disposition_counts = Counter(
            item.get("disposition") for item in disposition_rows
        )
        selection_counts = Counter(
            item.get("selection_result") for item in state.rows.get("assignments", [])
        )
        expected = {
            "scope_kind": "global",
            "scope_id": "global",
            "active_document_count": len(active_set),
            "assigned_document_count": disposition_counts["assigned"],
            "abstained_document_count": disposition_counts["abstained"],
            "excluded_document_count": disposition_counts["excluded"],
            "failed_document_count": disposition_counts["failed"],
            "candidate_assignment_count": len(state.rows.get("assignments", [])),
            "selected_assignment_count": selection_counts["selected"],
            "not_selected_assignment_count": selection_counts["not_selected"],
            "deferred_assignment_count": selection_counts["deferred"],
        }
        if row != expected:
            _issue(
                issues, "invalid.statistics", "coverage/global", f"expected {expected}"
            )
    build_receipts = state.rows.get("build-receipt", [])
    if len(build_receipts) != 1:
        _issue(
            issues,
            "invalid.schema",
            "build-receipt",
            "exactly one build receipt is required",
        )
    elif state.root is not None and isinstance(state.root.get("content"), dict):
        receipt = build_receipts[0]
        content = state.root["content"]
        expected_record_count = sum(
            len(state.rows.get(role, []))
            for role in (
                "assignments",
                "assignment-evidence",
                "assignment-dispositions",
                "coverage",
            )
        )
        if (
            receipt.get("input_document_release_id") != document_release.release_id
            or receipt.get("assignment_policy_id")
            != (content.get("assignmentPolicy") or {}).get("policyId")
            or receipt.get("record_count") != expected_record_count
        ):
            _issue(
                issues,
                "invalid.statistics",
                "build-receipt/rows/0",
                "receipt inputs or record count differ",
            )
    _validate_root_rollups(state, disposition_rows, issues)


def verify_extrapolation_release_v2(
    bundle: Path,
    *,
    document_release: DocumentReleaseView,
    atlas: AtlasMembershipReader | None = None,
) -> VerificationResult:
    """Verify one copied v2 bundle and return its ordered core code."""

    state = _load_bundle_state(bundle)
    issues = list(state.issues)
    if state.root is None:
        return VerificationResult(None, tuple(issues))
    assignments, evidence_rows = _validate_assignments_and_evidence(
        state, document_release, atlas, issues
    )
    _validate_dispositions_and_coverage(
        state, document_release, assignments, evidence_rows, issues
    )
    # Preserve deterministic encounter order while removing exact duplicates.
    unique: list[VerificationIssue] = []
    seen: set[tuple[str, str, str]] = set()
    for issue in issues:
        key = (issue.code, issue.path, issue.message)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return VerificationResult(str(state.root.get("releaseId")), tuple(unique))


def _validate_command(args: argparse.Namespace) -> int:
    try:
        document_release = load_document_release_view(Path(args.document_release))
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        pa.ArrowException,
    ) as exc:
        print(
            f"invalid.assignment-pin $inputs/document-release: {exc}", file=sys.stderr
        )
        return 1
    state = _load_bundle_state(Path(args.bundle))
    atlas = None
    if state.root is not None:
        content = state.root.get("content")
        input_releases = (
            content.get("input_releases") if isinstance(content, dict) else None
        )
        atlas_pin = (
            input_releases.get("vocabulary_atlas_asset")
            if isinstance(input_releases, dict)
            else None
        )
        if isinstance(atlas_pin, dict):
            try:
                try:
                    from refspec_atlas import RefSpecVocabularyAtlas
                except ModuleNotFoundError:
                    from tools.refspec_atlas import RefSpecVocabularyAtlas

                atlas = RefSpecVocabularyAtlas.open(
                    Path(args.vocabulary_atlas),
                    expected_manifest_digest=atlas_pin.get("manifest_digest"),
                    expected_output_digest=atlas_pin.get("distribution_digest"),
                )
            except (OSError, TypeError, ValueError) as exc:
                print(
                    f"invalid.assignment-pin $inputs/vocabulary-atlas: {exc}",
                    file=sys.stderr,
                )
                return 1
    result = verify_extrapolation_release_v2(
        Path(args.bundle), document_release=document_release, atlas=atlas
    )
    for issue in result.issues:
        print(issue, file=sys.stderr)
    if not result.valid:
        print(result.code, file=sys.stderr)
        return 1
    print(f"valid {result.release_id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="verify a materialized v2 bundle")
    validate.add_argument("bundle")
    validate.add_argument("--document-release", required=True)
    validate.add_argument("--vocabulary-atlas", required=True)
    validate.set_defaults(handler=_validate_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
