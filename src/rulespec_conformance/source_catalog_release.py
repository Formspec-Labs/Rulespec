#!/usr/bin/env python3
"""Portable verifier for sealed ``SourceCatalogRelease`` v1 bundles.

Rulespec Core owns the schemas, identity functions, diagnostics, and
conformance fixtures; SpicyRegs owns the records they carry (REF-024). This
module reads a materialized bundle of immutable files. It opens no database,
makes no network call, and imports no sibling product.

Diagnostics and first-failure order
-----------------------------------
Every defect is one :class:`VerificationIssue` — ``code``, ``path``,
``message``. ``VerificationResult.code`` is the FIRST failure under
:data:`CODE_PRECEDENCE`, and ``VerificationResult.first`` is the issue that
produced it. Issues are appended in a deterministic walk, and ``min`` is
stable, so the reported first failure is a function of the bundle bytes alone.

The precedence list is the same idea as
``tools/extrapolation_release_v2.py``'s, with one deliberate difference:
``invalid.path`` outranks the membership codes here. A bundle that names a
path outside itself is refused before any membership claim about that path is
judged; ordering it after ``invalid.membership-missing`` would report an
unresolvable objectKey as an absent file and hide the traversal.

Canonical bytes
---------------
Manifests use the platform canonical JSON of ``spec/rulespec-releases.md`` §1
(sorted keys, ``,``/``:`` separators, UTF-8, no non-finite numbers) over a safe
value domain that excludes floats and out-of-range integers. On that domain the
encoding agrees byte for byte with RFC 8785, which
``tools/test_source_catalog_release.py`` asserts against ``rfc8785`` directly.
The wheel therefore ships no canonicalization dependency of its own.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import jsonschema

from rulespec_conformance.conformance_lib import ROOT

RELEASE_RECORDS_ROOT = ROOT / "release-records"
SCHEMA_ROOT = RELEASE_RECORDS_ROOT / "schemas"
ROOT_SCHEMA = SCHEMA_ROOT / "source-catalog-release-v1.schema.json"
MEMBER_SCHEMA_ROOT = SCHEMA_ROOT / "source-catalog-release-v1"
MEMBER_MANIFEST_SCHEMA = MEMBER_SCHEMA_ROOT / "member-manifest-v1.schema.json"
SOURCE_ITEMS_SCHEMA = MEMBER_SCHEMA_ROOT / "source-items-v1.schema.json"
FIXTURE_ROOT = RELEASE_RECORDS_ROOT / "fixtures" / "source-catalog-release-v1"
CORPUS_FILE = FIXTURE_ROOT / "corpus.json"
CANDIDATE_MANIFEST = RELEASE_RECORDS_ROOT / "source-catalog-release-v1-candidate.json"

FORMAT = "spicyregs-source-catalog-release"
FORMAT_VERSION = "1.0"
RELEASE_ID_PREFIX = "urn:spicyregs:source-catalog-release:v1:"
MEMBER_MANIFEST_FORMAT = "spicy-artifact-member-manifest"
MEMBER_MANIFEST_VERSION = "1.0"
MAX_SAFE_INTEGER = (1 << 53) - 1

HEX_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
QUALIFIED_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

# Exactly the five dispositions the source-catalog contract admits. Order is
# the reporting order for derived counts, not a ranking.
SELECTION_DISPOSITIONS: tuple[str, ...] = (
    "selected",
    "excluded",
    "deleted",
    "unavailable",
    "failed",
)
NON_SELECTED_DISPOSITIONS = frozenset(SELECTION_DISPOSITIONS) - {"selected"}

ALLOWED_MEMBER_ROLES = frozenset({"schema", "source-items"})
MEMBER_DESCRIPTOR_FIELDS = frozenset(
    {"objectKey", "role", "mediaType", "byteSize", "sha256", "recordCount", "schemaId"}
)
MANIFEST_REFERENCE_FIELDS = frozenset(
    {"manifestId", "scopeKind", "scopeId", "objectKey", "byteSize", "sha256"}
)
SUBORDINATE_MANIFEST_FIELDS = frozenset(
    {"format", "formatVersion", "manifestId", "scope", "members", "counts"}
)

SCHEMA_FILES: dict[str, Path] = {
    "release-root": ROOT_SCHEMA,
    "member-manifest": MEMBER_MANIFEST_SCHEMA,
    "source-items": SOURCE_ITEMS_SCHEMA,
}


def _registered_schema_id(path: Path) -> str:
    """Read one packaged schema's ``$id``, or say plainly that it is not there.

    Read at import so a wheel built without the schema data fails loudly on
    import rather than at the first verification — the same posture
    `pyproject.toml`'s force-include table takes for `compiled/`.
    """

    try:
        return json.loads(path.read_text(encoding="utf-8"))["$id"]
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError(
            f"packaged SourceCatalogRelease schema is missing or unreadable: "
            f"{path} ({exc})"
        ) from exc


# Reference identifiers this repository publishes. A bundle carries its own
# copies; the descriptors must name these exact $id values.
SCHEMA_IDS: dict[str, str] = {
    role: _registered_schema_id(path) for role, path in SCHEMA_FILES.items()
}
# The one member role that is not `schema` is served by the source-items schema.
DATA_ROLE_SCHEMA_ROLE = {"source-items": "source-items"}

# A source-observed topic is not a RefSpec concept. Rejecting the vocabulary
# owner's URN space here keeps that boundary mechanical rather than advisory.
REFSPEC_IDENTIFIER_PREFIXES: tuple[str, ...] = ("urn:ref:", "urn:refspec:")

DIAGNOSTIC_CODES: tuple[str, ...] = (
    "invalid.root-syntax",
    "invalid.format",
    "invalid.identity",
    "invalid.path",
    "invalid.membership-missing",
    "invalid.membership-extra",
    "invalid.member-digest",
    "invalid.schema",
    "invalid.duplicate-identity",
    "invalid.disposition",
    "invalid.set-digest",
    "invalid.rendition",
    "invalid.topic-scope",
    "invalid.counts",
    "invalid.coverage",
)
CODE_PRECEDENCE: dict[str, int] = {
    code: index for index, code in enumerate(DIAGNOSTIC_CODES)
}


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
    def first(self) -> VerificationIssue | None:
        """The single diagnostic that decides the verdict."""

        if not self.issues:
            return None
        return min(
            self.issues,
            key=lambda issue: CODE_PRECEDENCE.get(issue.code, 10_000),
        )

    @property
    def code(self) -> str:
        first = self.first
        return "valid" if first is None else first.code

    @property
    def path(self) -> str | None:
        first = self.first
        return None if first is None else first.path

    @property
    def valid(self) -> bool:
        return not self.issues


# ─── Canonical bytes and digests ───────────────────────────────────────


def _validate_canonical_domain(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        if abs(value) > MAX_SAFE_INTEGER:
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


def canonical_json_bytes(value: Any) -> bytes:
    """Encode one identity-bearing value as platform canonical JSON."""

    _validate_canonical_domain(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    """Return an unqualified digest over canonical JSON bytes."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


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
    """Load a manifest and reject noncanonical source bytes."""

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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_digest(bundle: Path) -> str:
    """Digest a materialized bundle's complete file inventory.

    Names a sealed fixture without naming a filesystem: the inventory carries
    relative object keys, sizes, and content digests only.
    """

    inventory: list[dict[str, Any]] = []
    for path in sorted(bundle.rglob("*")):
        relative = path.relative_to(bundle).as_posix()
        if path.is_symlink():
            inventory.append(
                {"objectKey": relative, "symlinkTarget": str(path.readlink())}
            )
        elif path.is_file():
            inventory.append(
                {
                    "objectKey": relative,
                    "byteSize": path.stat().st_size,
                    "sha256": file_sha256(path),
                }
            )
    return canonical_sha256(inventory)


# ─── Identity and derived sets ─────────────────────────────────────────


def expected_release_id(root: Mapping[str, Any]) -> str:
    """Derive the release identity from the exact identity-bearing payload.

    ``annotations`` is excluded, so an operator note never renames a release.
    """

    payload = {
        "format": root.get("format"),
        "formatVersion": root.get("formatVersion"),
        "content": root.get("content"),
    }
    return RELEASE_ID_PREFIX + canonical_sha256(payload)


def stamp_root(root: Mapping[str, Any]) -> dict[str, Any]:
    """Return a root copy carrying its content-derived identity."""

    stamped = json.loads(json.dumps(root))
    stamped.pop("releaseId", None)
    stamped["releaseId"] = expected_release_id(stamped)
    return stamped


def source_set_digest(source_item_ids: Sequence[str]) -> str:
    """Canonical set digest over a deduplicated, sorted identifier list.

    A SET digest, so a repeated identifier does not change it. Duplicates are
    a separate defect with a separate diagnostic
    (``invalid.duplicate-identity``); folding them into the digest would let
    one defect mask the other.
    """

    return "sha256:" + canonical_sha256(sorted(set(source_item_ids)))


def _disposition_of(item: Any) -> str | None:
    if not isinstance(item, Mapping):
        return None
    selection = item.get("selection")
    if not isinstance(selection, Mapping):
        return None
    disposition = selection.get("disposition")
    return disposition if disposition in SELECTION_DISPOSITIONS else None


def derive_counts(
    items: Sequence[Mapping[str, Any]],
    *,
    member_count: int,
    total_member_byte_size: int,
) -> dict[str, int]:
    """Recompute the diagnostic counts from the members alone."""

    tally = {name: 0 for name in SELECTION_DISPOSITIONS}
    for item in items:
        disposition = _disposition_of(item)
        if disposition is not None:
            tally[disposition] += 1
    return {
        "discoveredCount": len(items),
        "selectedCount": tally["selected"],
        "excludedCount": tally["excluded"],
        "deletedCount": tally["deleted"],
        "unavailableCount": tally["unavailable"],
        "failedCount": tally["failed"],
        "memberCount": member_count,
        "totalMemberByteSize": total_member_byte_size,
    }


def derive_coverage(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    """Recompute the accounting proof from the members alone."""

    accounted = 0
    with_rendition = 0
    selected_document_ids: set[str] = set()
    for item in items:
        disposition = _disposition_of(item)
        if disposition is None:
            continue
        accounted += 1
        if disposition != "selected":
            continue
        renditions = item.get("candidateRenditions")
        if isinstance(renditions, list) and renditions:
            with_rendition += 1
        document_id = item.get("documentId")
        if isinstance(document_id, str):
            selected_document_ids.add(document_id)
    return {
        "accountedCount": accounted,
        "unaccountedCount": len(items) - accounted,
        "selectedWithCandidateRenditionCount": with_rendition,
        "distinctSelectedDocumentIdCount": len(selected_document_ids),
    }


# ─── Verification ──────────────────────────────────────────────────────


def _issue(
    issues: list[VerificationIssue], code: str, path: str, message: str
) -> None:
    issues.append(VerificationIssue(code=code, path=path, message=message))


def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_issues(
    value: Any,
    schema: Mapping[str, Any],
    *,
    path: str,
) -> list[VerificationIssue]:
    validator = jsonschema.Draft202012Validator(schema)
    issues: list[VerificationIssue] = []
    for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path)):
        suffix = "".join(f"/{part}" for part in error.path)
        _issue(issues, "invalid.schema", f"{path}{suffix}", error.message)
    return issues


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


def _read_root(bundle: Path, issues: list[VerificationIssue]) -> dict[str, Any] | None:
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
    except (TypeError, ValueError) as exc:
        _issue(issues, "invalid.identity", "release.json", str(exc))
    else:
        if root.get("releaseId") != expected:
            _issue(
                issues,
                "invalid.identity",
                "release.json/releaseId",
                f"expected {expected}",
            )
    issues.extend(_schema_issues(root, _load_schema(ROOT_SCHEMA), path="release.json"))
    return root


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


def _validate_manifest_reference(
    reference: Any,
    *,
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
    if not _safe_object_key(reference.get("objectKey")):
        _issue(issues, "invalid.path", f"{path}/objectKey", "unsafe member path")
    expected_manifest_id = f"{reference.get('scopeKind')}:{reference.get('scopeId')}"
    if reference.get("manifestId") != expected_manifest_id:
        _issue(
            issues,
            "invalid.schema",
            f"{path}/manifestId",
            f"expected {expected_manifest_id}",
        )
    return reference


def _validate_member_descriptor(
    member: Any,
    *,
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
    if role not in ALLOWED_MEMBER_ROLES:
        _issue(issues, "invalid.schema", f"{path}/role", f"unknown role {role!r}")
    expected_media = (
        "application/schema+json" if role == "schema" else "application/json"
    )
    if member.get("mediaType") != expected_media:
        _issue(
            issues, "invalid.schema", f"{path}/mediaType", f"expected {expected_media}"
        )
    if role == "schema":
        if member.get("recordCount") is not None:
            _issue(
                issues,
                "invalid.schema",
                f"{path}/recordCount",
                "a schema member has no rows and must declare null",
            )
    elif not isinstance(member.get("recordCount"), int) or isinstance(
        member.get("recordCount"), bool
    ):
        _issue(
            issues, "invalid.schema", f"{path}/recordCount", "invalid record count"
        )
    return member


def _read_member_manifest(
    bundle: Path,
    root: Mapping[str, Any],
    issues: list[VerificationIssue],
) -> tuple[list[dict[str, Any]], dict[str, Path], set[str]]:
    declared = {"release.json"}
    content = root.get("content")
    if not isinstance(content, dict):
        return [], {}, declared
    reference = _validate_manifest_reference(
        content.get("globalManifest"),
        path="release.json/content/globalManifest",
        issues=issues,
    )
    if reference is None:
        return [], {}, declared
    object_key = reference.get("objectKey")
    if not _safe_object_key(object_key):
        return [], {}, declared
    declared.add(object_key)
    path = _member_path(bundle, object_key)
    if path.is_symlink():
        _issue(issues, "invalid.path", object_key, "manifest is a symlink")
        return [], {}, declared
    if not path.is_file():
        _issue(issues, "invalid.membership-missing", object_key, "manifest is absent")
        return [], {}, declared
    if path.stat().st_size != reference.get("byteSize") or file_sha256(
        path
    ) != reference.get("sha256"):
        _issue(
            issues,
            "invalid.member-digest",
            object_key,
            "manifest size or digest differs from the root reference",
        )
    try:
        manifest = load_strict_canonical_json(path)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _issue(issues, "invalid.schema", object_key, str(exc))
        return [], {}, declared
    issues.extend(
        _schema_issues(manifest, _load_schema(MEMBER_MANIFEST_SCHEMA), path=object_key)
    )
    if not isinstance(manifest, dict) or set(manifest) != SUBORDINATE_MANIFEST_FIELDS:
        _issue(
            issues, "invalid.schema", object_key, "invalid member manifest fields"
        )
        return [], {}, declared
    if (
        manifest.get("format") != MEMBER_MANIFEST_FORMAT
        or manifest.get("formatVersion") != MEMBER_MANIFEST_VERSION
    ):
        _issue(
            issues, "invalid.schema", object_key, "unsupported member manifest format"
        )
    expected_scope = {
        "kind": reference.get("scopeKind"),
        "id": reference.get("scopeId"),
    }
    if manifest.get("scope") != expected_scope or manifest.get(
        "manifestId"
    ) != reference.get("manifestId"):
        _issue(
            issues,
            "invalid.schema",
            object_key,
            "manifest scope differs from the root reference",
        )
    raw_members = manifest.get("members")
    if not isinstance(raw_members, list):
        _issue(
            issues, "invalid.schema", f"{object_key}/members", "members must be an array"
        )
        return [], {}, declared
    object_keys = [
        member.get("objectKey") for member in raw_members if isinstance(member, dict)
    ]
    if object_keys != sorted(object_keys, key=lambda key: str(key)):
        _issue(
            issues,
            "invalid.schema",
            f"{object_key}/members",
            "members must be sorted by objectKey",
        )
    members: list[dict[str, Any]] = []
    member_paths: dict[str, Path] = {}
    for index, raw_member in enumerate(raw_members):
        member = _validate_member_descriptor(
            raw_member, path=f"{object_key}/members/{index}", issues=issues
        )
        if member is None:
            continue
        member_key = member.get("objectKey")
        if _safe_object_key(member_key):
            if member_key in member_paths:
                _issue(
                    issues,
                    "invalid.duplicate-identity",
                    f"{object_key}/members/{index}/objectKey",
                    f"duplicate member {member_key}",
                )
            else:
                member_paths[member_key] = _member_path(bundle, member_key)
            declared.add(member_key)
        elif isinstance(member_key, str) and member_key:
            # Account for the unsafe spelling without resolving it, so the
            # membership comparison does not also report the file as absent.
            declared.add(member_key)
        members.append(member)
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
            member.get("recordCount") or 0
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
    if manifest.get("counts") != expected_counts:
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
            digest = file_sha256(path)
        except OSError as exc:
            _issue(issues, "invalid.membership-missing", object_key, str(exc))
            continue
        if size != member.get("byteSize") or digest != member.get("sha256"):
            _issue(
                issues,
                "invalid.member-digest",
                object_key,
                "member size or digest differs from its descriptor",
            )


def _validate_schema_set(
    root: Mapping[str, Any],
    members: Sequence[Mapping[str, Any]],
    member_paths: Mapping[str, Path],
    issues: list[VerificationIssue],
) -> None:
    content = root.get("content")
    schema_set = content.get("schemaSet") if isinstance(content, dict) else None
    if not isinstance(schema_set, dict):
        return
    descriptors = schema_set.get("schemas")
    if not isinstance(descriptors, list):
        return
    base = "release.json/content/schemaSet"
    ids = [item.get("schemaId") for item in descriptors if isinstance(item, dict)]
    if ids != sorted(ids, key=lambda value: str(value)):
        _issue(
            issues, "invalid.schema", f"{base}/schemas", "schemas must be sorted by schemaId"
        )
    try:
        expected_set_id = f"urn:spicy:schema-set:v1:{canonical_sha256(descriptors)}"
    except (TypeError, ValueError) as exc:
        _issue(issues, "invalid.schema", base, str(exc))
    else:
        if schema_set.get("schemaSetId") != expected_set_id:
            _issue(
                issues,
                "invalid.schema",
                f"{base}/schemaSetId",
                f"expected {expected_set_id}",
            )
    schema_members = {
        member["schemaId"]: member
        for member in members
        if member.get("role") == "schema" and isinstance(member.get("schemaId"), str)
    }
    seen_roles: dict[str, int] = {}
    for index, descriptor in enumerate(descriptors):
        path = f"{base}/schemas/{index}"
        if not isinstance(descriptor, dict):
            continue
        schema_id = descriptor.get("schemaId")
        roles = descriptor.get("roles")
        role = roles[0] if isinstance(roles, list) and len(roles) == 1 else None
        if role is None or SCHEMA_IDS.get(role) != schema_id:
            _issue(
                issues,
                "invalid.schema",
                f"{path}/roles",
                f"role {role!r} must resolve to the registered schema for {schema_id!r}",
            )
            continue
        seen_roles[role] = seen_roles.get(role, 0) + 1
        member = schema_members.get(schema_id)
        if member is None:
            _issue(
                issues,
                "invalid.membership-missing",
                f"{path}/schemaId",
                "schema descriptor has no schema member",
            )
            continue
        if member.get("sha256") != descriptor.get("schemaSha256"):
            _issue(
                issues,
                "invalid.member-digest",
                f"{path}/schemaSha256",
                "schema descriptor digest differs from the member",
            )
        member_path = member_paths.get(str(member.get("objectKey")))
        if member_path is None or not member_path.is_file():
            continue
        try:
            schema = json.loads(member_path.read_text(encoding="utf-8"))
            jsonschema.Draft202012Validator.check_schema(schema)
        except (OSError, ValueError, jsonschema.SchemaError) as exc:
            _issue(issues, "invalid.schema", str(member.get("objectKey")), str(exc))
            continue
        if schema.get("$id") != schema_id:
            _issue(
                issues,
                "invalid.schema",
                str(member.get("objectKey")),
                "$id differs from the descriptor",
            )
    for role in SCHEMA_IDS:
        if seen_roles.get(role) != 1:
            _issue(
                issues,
                "invalid.schema",
                f"{base}/schemas",
                f"role {role!r} must resolve exactly once",
            )


def _read_source_items(
    members: Sequence[Mapping[str, Any]],
    member_paths: Mapping[str, Path],
    issues: list[VerificationIssue],
) -> list[dict[str, Any]] | None:
    """Load the source-item rows, or ``None`` when they cannot be trusted."""

    data_members = [member for member in members if member.get("role") == "source-items"]
    if len(data_members) != 1:
        _issue(
            issues,
            "invalid.schema",
            "manifests/global.json/members",
            "exactly one source-items member is required",
        )
        return None
    member = data_members[0]
    object_key = str(member.get("objectKey"))
    if member.get("schemaId") != SCHEMA_IDS["source-items"]:
        _issue(
            issues,
            "invalid.schema",
            f"member:{object_key}/schemaId",
            f"expected {SCHEMA_IDS['source-items']}",
        )
    path = member_paths.get(object_key)
    if path is None or path.is_symlink() or not path.is_file():
        return None
    try:
        rows = load_strict_canonical_json(path)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        _issue(issues, "invalid.schema", object_key, str(exc))
        return None
    if not isinstance(rows, list):
        _issue(issues, "invalid.schema", object_key, "source items must be an array")
        return None
    if len(rows) != member.get("recordCount"):
        _issue(
            issues,
            "invalid.schema",
            f"member:{object_key}/recordCount",
            f"expected {len(rows)}",
        )
    schema = _load_schema(SOURCE_ITEMS_SCHEMA)
    for index, row in enumerate(rows):
        issues.extend(_schema_issues(row, schema, path=f"{object_key}/{index}"))
    return [row for row in rows if isinstance(row, dict)]


def _validate_source_items(
    root: Mapping[str, Any],
    items: Sequence[Mapping[str, Any]],
    members: Sequence[Mapping[str, Any]],
    object_key: str,
    issues: list[VerificationIssue],
) -> None:
    seen_source_item_ids: set[str] = set()
    selected_document_ids: set[str] = set()
    for index, item in enumerate(items):
        path = f"{object_key}/{index}"
        source_item_id = item.get("sourceItemId")
        if isinstance(source_item_id, str):
            if source_item_id in seen_source_item_ids:
                _issue(
                    issues,
                    "invalid.duplicate-identity",
                    f"{path}/sourceItemId",
                    f"duplicate sourceItemId {source_item_id}",
                )
            seen_source_item_ids.add(source_item_id)

        disposition = _disposition_of(item)
        selection = item.get("selection")
        if disposition in NON_SELECTED_DISPOSITIONS and isinstance(selection, Mapping):
            for field in ("reasonCode", "reason"):
                if not selection.get(field):
                    _issue(
                        issues,
                        "invalid.disposition",
                        f"{path}/selection/{field}",
                        f"disposition {disposition!r} requires a {field}",
                    )

        renditions = item.get("candidateRenditions")
        seen_rendition_ids: set[str] = set()
        for rendition_index, rendition in enumerate(renditions or []):
            if not isinstance(rendition, Mapping):
                continue
            rendition_id = rendition.get("renditionId")
            if isinstance(rendition_id, str):
                if rendition_id in seen_rendition_ids:
                    _issue(
                        issues,
                        "invalid.duplicate-identity",
                        f"{path}/candidateRenditions/{rendition_index}/renditionId",
                        f"duplicate renditionId {rendition_id}",
                    )
                seen_rendition_ids.add(rendition_id)
        if disposition == "selected":
            if not isinstance(renditions, list) or not renditions:
                _issue(
                    issues,
                    "invalid.rendition",
                    f"{path}/candidateRenditions",
                    "a selected item requires at least one candidate rendition",
                )
            document_id = item.get("documentId")
            if isinstance(document_id, str):
                if document_id in selected_document_ids:
                    _issue(
                        issues,
                        "invalid.duplicate-identity",
                        f"{path}/documentId",
                        f"duplicate selected documentId {document_id}",
                    )
                selected_document_ids.add(document_id)

        for topic_index, topic in enumerate(item.get("sourceObservedTopics") or []):
            if not isinstance(topic, Mapping):
                continue
            for field in ("observedTopicId", "observedTopicScheme"):
                value = topic.get(field)
                if isinstance(value, str) and value.lower().startswith(
                    REFSPEC_IDENTIFIER_PREFIXES
                ):
                    _issue(
                        issues,
                        "invalid.topic-scope",
                        f"{path}/sourceObservedTopics/{topic_index}/{field}",
                        "a source-observed topic must not carry a RefSpec concept identifier",
                    )

    content = root.get("content")
    if not isinstance(content, Mapping):
        return
    universe_ids = [
        item["sourceItemId"]
        for item in items
        if isinstance(item.get("sourceItemId"), str)
    ]
    selected_ids = [
        item["sourceItemId"]
        for item in items
        if isinstance(item.get("sourceItemId"), str) and _disposition_of(item) == "selected"
    ]
    for field, ids in (
        ("requestedUniverseSetDigest", universe_ids),
        ("selectedSourceSetDigest", selected_ids),
    ):
        expected = source_set_digest(ids)
        if content.get(field) != expected:
            _issue(
                issues,
                "invalid.set-digest",
                f"release.json/content/{field}",
                f"expected {expected} over {len(set(ids))} member identifiers",
            )

    expected_counts = derive_counts(
        items,
        member_count=len(members),
        total_member_byte_size=sum(
            member.get("byteSize", 0)
            for member in members
            if isinstance(member.get("byteSize"), int)
            and not isinstance(member.get("byteSize"), bool)
        ),
    )
    if content.get("counts") != expected_counts:
        _issue(
            issues,
            "invalid.counts",
            "release.json/content/counts",
            f"expected {expected_counts}",
        )
    expected_coverage = derive_coverage(items)
    if content.get("coverage") != expected_coverage:
        _issue(
            issues,
            "invalid.coverage",
            "release.json/content/coverage",
            f"expected {expected_coverage}",
        )


def verify_source_catalog_release(bundle: Path) -> VerificationResult:
    """Verify one materialized ``SourceCatalogRelease`` v1 bundle."""

    bundle = Path(bundle)
    issues: list[VerificationIssue] = []
    root = _read_root(bundle, issues)
    if root is None:
        return VerificationResult(None, tuple(issues))
    members, member_paths, declared = _read_member_manifest(bundle, root, issues)
    _verify_member_files(bundle, members, member_paths, declared, issues)
    _validate_schema_set(root, members, member_paths, issues)
    items = _read_source_items(members, member_paths, issues)
    if items is not None:
        data_members = [
            member for member in members if member.get("role") == "source-items"
        ]
        object_key = str(data_members[0].get("objectKey")) if data_members else "data"
        _validate_source_items(root, items, members, object_key, issues)
    release_id = root.get("releaseId")
    return VerificationResult(
        release_id if isinstance(release_id, str) else None, tuple(issues)
    )


def verify_corpus(corpus_file: Path = CORPUS_FILE) -> list[dict[str, Any]]:
    """Verify every sealed fixture and return one row per case.

    Each row carries the case name, whether the sealed tree digest still
    matches, and the observed verdict against the expected one. The caller
    decides how to report; this returns facts.
    """

    corpus = json.loads(Path(corpus_file).read_text(encoding="utf-8"))
    fixture_root = Path(corpus_file).parent
    rows: list[dict[str, Any]] = []
    for case in corpus["cases"]:
        bundle = fixture_root / case["bundle"]
        observed_tree = tree_digest(bundle) if bundle.is_dir() else None
        result = (
            verify_source_catalog_release(bundle)
            if bundle.is_dir()
            else VerificationResult(None, ())
        )
        rows.append(
            {
                "name": case["name"],
                "bundle": case["bundle"],
                "sealed": observed_tree == case["treeSha256"],
                "expectedCode": case["expectedCode"],
                "observedCode": result.code if bundle.is_dir() else "absent",
                "expectedPath": case["expectedPath"],
                "observedPath": result.path if bundle.is_dir() else None,
                "issues": [str(issue) for issue in result.issues],
            }
        )
    return rows


BUNDLE_TREE_MEDIA_TYPE = "application/vnd.spicy.bundle-tree+json"
VALIDATOR_MEDIA_TYPE = "text/x-python"


def candidate_bundle_errors(manifest_path: Path = CANDIDATE_MANIFEST) -> list[str]:
    """Re-derive every digest the candidate manifest binds, and its own identity.

    The manifest is a ``RulespecCoreRelease`` (``spec/rulespec-releases.md`` §2)
    whose ``release_id`` is the candidate's immutable name. Schemas and fixture
    bundles resolve against the data root, so this runs from an installed wheel
    with no checkout in reach; the validator artifact resolves to this module's
    own file, which is where the wheel puts it.

    Returns one message per defect; an empty list is the proof.
    """

    errors: list[str] = []
    manifest_path = Path(manifest_path)
    try:
        record = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{manifest_path}: {exc}"]
    if not isinstance(record, dict):
        return [f"{manifest_path}: candidate manifest must be a JSON object"]

    for field in ("schema_artifacts", "validator_artifacts", "conformance_fixture_artifacts"):
        artifacts = record.get(field)
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(f"{field}: manifest must pin at least one artifact")
            continue
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                errors.append(f"{field}: artifact entry must be an object")
                continue
            name = artifact.get("name")
            media_type = artifact.get("media_type")
            declared = artifact.get("artifact_digest")
            if media_type == VALIDATOR_MEDIA_TYPE:
                # The validator modules live in the package, not under the data
                # root, so they resolve beside this file in either layout.
                target = Path(__file__).resolve().parent / PurePosixPath(str(name)).name
            elif isinstance(name, str):
                target = ROOT / name
            else:
                errors.append(f"{field}: artifact has no name")
                continue
            if media_type == BUNDLE_TREE_MEDIA_TYPE:
                if not target.is_dir():
                    errors.append(f"{name}: sealed fixture bundle is absent")
                    continue
                observed = "sha256:" + tree_digest(target)
            else:
                if not target.is_file():
                    errors.append(f"{name}: pinned artifact is absent")
                    continue
                observed = "sha256:" + file_sha256(target)
            if observed != declared:
                errors.append(f"{name}: expected {declared}, computed {observed}")

    preimage = {
        key: value
        for key, value in record.items()
        if key not in {"release_id", "release_digest"}
    }
    try:
        expected_digest = "sha256:" + canonical_sha256(preimage)
    except (TypeError, ValueError) as exc:
        return errors + [f"{manifest_path}: {exc}"]
    if record.get("release_digest") != expected_digest:
        errors.append(
            f"release_digest: expected {expected_digest}, "
            f"found {record.get('release_digest')}"
        )
    expected_id = f"urn:rulespec:core:{expected_digest.removeprefix('sha256:')}"
    if record.get("release_id") != expected_id:
        errors.append(
            f"release_id: expected {expected_id}, found {record.get('release_id')}"
        )
    return errors


def bundle_release_id(manifest_path: Path = CANDIDATE_MANIFEST) -> str:
    """The candidate bundle's immutable digest-derived name."""

    return json.loads(Path(manifest_path).read_text(encoding="utf-8"))["release_id"]


__all__ = [
    "BUNDLE_TREE_MEDIA_TYPE",
    "CANDIDATE_MANIFEST",
    "CODE_PRECEDENCE",
    "CORPUS_FILE",
    "DIAGNOSTIC_CODES",
    "FIXTURE_ROOT",
    "FORMAT",
    "FORMAT_VERSION",
    "MEMBER_MANIFEST_SCHEMA",
    "RELEASE_ID_PREFIX",
    "ROOT_SCHEMA",
    "SCHEMA_FILES",
    "SCHEMA_IDS",
    "SELECTION_DISPOSITIONS",
    "SOURCE_ITEMS_SCHEMA",
    "VALIDATOR_MEDIA_TYPE",
    "VerificationIssue",
    "VerificationResult",
    "bundle_release_id",
    "candidate_bundle_errors",
    "canonical_json_bytes",
    "canonical_sha256",
    "derive_counts",
    "derive_coverage",
    "expected_release_id",
    "file_sha256",
    "load_strict_canonical_json",
    "source_set_digest",
    "stamp_root",
    "tree_digest",
    "verify_corpus",
    "verify_source_catalog_release",
    "write_canonical_json",
]
