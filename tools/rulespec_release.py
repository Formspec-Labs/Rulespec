#!/usr/bin/env python3
"""Validate canonical Rulespec Core and Extrapolator release records.

The module uses only the Python standard library. Consumers can therefore
validate pinned release fixtures without a Rulespec checkout, a RefSpec
checkout, a SpicyRegs checkout, or a mutable database.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ABSOLUTE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:[^\s]+$")


@dataclass(frozen=True)
class ValidationIssue:
    """One fail-closed release validation result."""

    code: str
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.code} {self.path}: {self.message}"


def _reject_constant(value: str) -> None:
    raise ValueError(f"JSON constant {value!r} is not permitted")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON object key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    """Load strict JSON and reject duplicate keys and non-finite numbers."""

    return json.loads(
        path.read_text(encoding="utf-8"),
        parse_constant=_reject_constant,
        object_pairs_hook=_reject_duplicate_keys,
    )


def canonical_json_bytes(value: Any) -> bytes:
    """Return the platform-wide canonical JSON byte representation."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def canonical_digest(value: Any) -> str:
    """Return a lowercase SHA-256 digest over canonical JSON bytes."""

    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


_SELECTION_CONTEXT_FIELDS = (
    "input_releases",
    "profile",
    "validation_sample_manifest",
    "concept_assignments",
    "evidence_bindings",
    "extraction_activities",
    "ai_lineage_records",
    "processing_segments",
    "derived_text_projections",
    "validation_artifacts",
    "agent_validation_receipts",
    "baseline_validation_receipts",
)


def extrapolation_selection_context_digest(release: Mapping[str, Any]) -> str:
    """Bind selection receipts to the complete pre-selection release graph."""

    raw_receipts = release.get("selection_receipts")
    policies = sorted(
        {
            receipt.get("selection_policy")
            for receipt in raw_receipts or []
            if isinstance(receipt, Mapping)
            and isinstance(receipt.get("selection_policy"), str)
        }
    )
    preimage = {
        field: release.get(field)
        for field in _SELECTION_CONTEXT_FIELDS
    }
    preimage["selection_policies"] = policies
    return canonical_digest(preimage)


def content_digest(content: bytes) -> str:
    """Return a lowercase SHA-256 digest over exact content bytes."""

    return "sha256:" + hashlib.sha256(content).hexdigest()


def text_digest(text: str) -> str:
    """Return a digest over exact UTF-8 text bytes."""

    return content_digest(text.encode("utf-8"))


def compute_release_digest(release: Mapping[str, Any]) -> str:
    """Digest a root release after omitting only its identity fields."""

    preimage = dict(release)
    preimage.pop("release_id", None)
    preimage.pop("release_digest", None)
    return canonical_digest(preimage)


def expected_release_id(product: str, release_kind: str, digest: str) -> str:
    """Build the content-derived release identifier for a valid digest."""

    if not SHA256_RE.fullmatch(digest):
        raise ValueError(f"invalid release digest {digest!r}")
    return f"urn:{product}:{release_kind}:{digest.removeprefix('sha256:')}"


def content_addressed_id(
    product: str, record_kind: str, identity: Mapping[str, Any]
) -> str:
    """Build a stable identifier over canonical identity-defining fields."""

    digest = canonical_digest(identity).removeprefix("sha256:")
    return f"urn:{product}:{record_kind}:{digest}"


def stamp_release(
    release: Mapping[str, Any], *, product: str, release_kind: str
) -> dict[str, Any]:
    """Return a copy with a recomputed root digest and release identifier."""

    stamped = copy.deepcopy(dict(release))
    stamped.pop("release_id", None)
    stamped.pop("release_digest", None)
    digest = compute_release_digest(stamped)
    stamped["release_digest"] = digest
    stamped["release_id"] = expected_release_id(product, release_kind, digest)
    return stamped


def stamp_coverage(coverage: Mapping[str, Any]) -> dict[str, Any]:
    """Return a content-addressed ExtrapolationCoverage record."""

    stamped = copy.deepcopy(dict(coverage))
    stamped.pop("coverage_id", None)
    stamped.pop("coverage_digest", None)
    digest = canonical_digest(stamped)
    stamped["coverage_digest"] = digest
    stamped["coverage_id"] = expected_release_id(
        "rulespec", "extrapolation-coverage", digest
    )
    return stamped


RECORD_IDENTITIES: dict[str, tuple[str, tuple[str, ...]]] = {
    "ConceptAssignment": (
        "concept-assignment",
        (
            "asserts_subject_ref",
            "asserts_predicate",
            "asserts_object_ref",
            "assertion_polarity",
            "assigned_concept_release_ref",
        ),
    ),
    "EvidenceBinding": (
        "evidence-binding",
        (
            "binds_assignment_ref",
            "evidence_spans",
            "evidence_role",
            "evidentiary_function",
        ),
    ),
    "ExtractionActivity": (
        "extraction-activity",
        ("extraction_run_id", "extraction_attempt"),
    ),
    "AILineage": (
        "ai-lineage",
        (
            "model_id",
            "model_version",
            "prompt_contract_digest",
            "input_context_digest",
            "temperature",
            "seed",
        ),
    ),
    "ProcessingSegment": (
        "processing-segment",
        (
            "document_release_ref",
            "input_fragment_refs",
            "segmentation_policy",
            "derived_text_digest",
        ),
    ),
    "DerivedTextProjection": (
        "derived-text-projection",
        (
            "derived_unit_ref",
            "derived_text_digest",
            "construction_method",
        ),
    ),
    "AgentValidationReceipt": (
        "agent-validation-receipt",
        (
            "owner",
            "attempt_id",
            "target_ref",
            "target_digest",
            "protocol",
            "input_manifest_digest",
            "independence_group",
            "provider_model_id",
            "request_contract_digest",
        ),
    ),
    "BaselineValidationReceipt": (
        "baseline-validation-receipt",
        (
            "owner",
            "target_profile_ref",
            "target_release_ref",
            "sample_manifest_digest",
            "rubric",
            "aggregation_policy",
            "evaluated_at",
        ),
    ),
    "ExtrapolationSelectionReceipt": (
        "extrapolation-selection-receipt",
        (
            "assignment_ref",
            "selection_policy",
            "selection_context_digest",
            "evaluator_ref",
            "evaluator_version",
            "evaluated_at",
            "effective_as_of",
        ),
    ),
}

CONTENT_ADDRESSED_RECEIPT_TYPES = {
    "AgentValidationReceipt",
    "BaselineValidationReceipt",
    "ExtrapolationSelectionReceipt",
}


def stable_record_id(record: Mapping[str, Any]) -> str:
    """Derive a stable Rulespec record ID from its declared identity fields."""

    record_type = record.get("record_type")
    if record_type not in RECORD_IDENTITIES:
        raise ValueError(f"unsupported durable record type {record_type!r}")
    slug, fields = RECORD_IDENTITIES[record_type]
    missing = [field for field in fields if field not in record]
    if missing:
        raise ValueError(
            f"{record_type} lacks identity fields: {', '.join(sorted(missing))}"
        )
    if record_type in CONTENT_ADDRESSED_RECEIPT_TYPES:
        identity = {
            field: value
            for field, value in record.items()
            if field != "record_id"
        }
    else:
        identity = {field: record[field] for field in fields}
    digest = canonical_digest(identity).removeprefix("sha256:")
    return f"urn:rulespec:{slug}:{digest}"


def stamp_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy with its stable record identifier."""

    stamped = copy.deepcopy(dict(record))
    stamped["record_id"] = stable_record_id(stamped)
    return stamped


def _issue(
    issues: list[ValidationIssue], code: str, path: str, message: str
) -> None:
    issues.append(ValidationIssue(code=code, path=path, message=message))


def _required_fields(
    value: Mapping[str, Any], required: Iterable[str], path: str
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for field in required:
        if field not in value:
            _issue(issues, "MISSING_FIELD", f"{path}/{field}", "field is required")
    return issues


def _check_digest(
    value: object, issues: list[ValidationIssue], path: str
) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        _issue(
            issues,
            "INVALID_DIGEST",
            path,
            "expected lowercase sha256:<64 hex>",
        )


def validate_release_identity(
    release: Mapping[str, Any], *, product: str, release_kind: str, path: str = "$"
) -> list[ValidationIssue]:
    """Validate the shared content-derived root release identity."""

    issues: list[ValidationIssue] = []
    digest = release.get("release_digest")
    release_id = release.get("release_id")
    _check_digest(digest, issues, f"{path}/release_digest")
    try:
        expected_digest = compute_release_digest(release)
    except (TypeError, ValueError) as exc:
        _issue(issues, "INVALID_JSON_VALUE", path, str(exc))
        return issues
    if digest != expected_digest:
        _issue(
            issues,
            "RELEASE_DIGEST_MISMATCH",
            f"{path}/release_digest",
            f"expected {expected_digest}",
        )
    if isinstance(digest, str) and SHA256_RE.fullmatch(digest):
        expected_id = expected_release_id(product, release_kind, digest)
        if release_id != expected_id:
            _issue(
                issues,
                "RELEASE_ID_MISMATCH",
                f"{path}/release_id",
                f"expected {expected_id}",
            )
    return issues


def validate_rulespec_core_release(
    release: Mapping[str, Any], *, path: str = "$"
) -> list[ValidationIssue]:
    """Validate a repository-independent Rulespec Core release record."""

    issues = _required_fields(
        release,
        (
            "record_type",
            "release_id",
            "release_digest",
            "release_status",
            "version",
            "schema_artifacts",
            "validator_artifacts",
            "conformance_fixture_artifacts",
        ),
        path,
    )
    if release.get("record_type") != "RulespecCoreRelease":
        _issue(
            issues,
            "WRONG_RECORD_TYPE",
            f"{path}/record_type",
            "expected RulespecCoreRelease",
        )
    issues.extend(
        validate_release_identity(
            release, product="rulespec", release_kind="core", path=path
        )
    )
    for field in (
        "schema_artifacts",
        "validator_artifacts",
        "conformance_fixture_artifacts",
    ):
        artifacts = release.get(field)
        if not isinstance(artifacts, list) or not artifacts:
            _issue(
                issues,
                "MANIFEST_EMPTY",
                f"{path}/{field}",
                "manifest must contain at least one pinned artifact",
            )
            continue
        for index, artifact in enumerate(artifacts):
            artifact_path = f"{path}/{field}/{index}"
            if not isinstance(artifact, dict):
                _issue(
                    issues,
                    "INVALID_RECORD",
                    artifact_path,
                    "artifact entry must be an object",
                )
                continue
            issues.extend(
                _required_fields(
                    artifact,
                    ("name", "media_type", "artifact_digest"),
                    artifact_path,
                )
            )
            _check_digest(
                artifact.get("artifact_digest"),
                issues,
                f"{artifact_path}/artifact_digest",
            )
    return issues


def _release_kind(record_type: str) -> tuple[str, str] | None:
    return {
        "RulespecCoreRelease": ("rulespec", "core"),
        "DocumentRelease": ("spicyregs", "document-release"),
        "VocabularyRelease": ("refspec", "vocabulary-release"),
        "ReferenceResourceRelease": ("rulespec", "reference-resource"),
        "ExtrapolationRelease": ("rulespec", "extrapolation"),
    }.get(record_type)


def _record_type(record: Mapping[str, Any]) -> object:
    record_type = record.get("record_type")
    if record_type is not None:
        return record_type
    if (
        record.get("schema_version") == "refspec-vocabulary-release-v1"
        and str(record.get("release_id", "")).startswith(
            "urn:refspec:vocabulary-release:"
        )
    ):
        return "VocabularyRelease"
    return None


def fixture_records(value: Any) -> list[dict[str, Any]]:
    """Extract release records from a root record or fixture bundle."""

    if isinstance(value, dict) and value.get("fixture_type") == "PinnedReleaseBundle":
        records = value.get("records")
        if not isinstance(records, list) or not all(
            isinstance(record, dict) for record in records
        ):
            raise ValueError("PinnedReleaseBundle.records must be an object array")
        return records
    if isinstance(value, dict):
        return [value]
    raise ValueError("release input must be a JSON object")


def index_input_releases(
    values: Iterable[Any],
) -> tuple[dict[str, dict[str, Any]], list[ValidationIssue]]:
    """Index pinned input releases and verify each content-derived identity."""

    records: dict[str, dict[str, Any]] = {}
    issues: list[ValidationIssue] = []
    for input_index, value in enumerate(values):
        for record_index, record in enumerate(fixture_records(value)):
            path = f"$inputs/{input_index}/{record_index}"
            record_type = _record_type(record)
            kind = _release_kind(record_type)
            if kind is None:
                _issue(
                    issues,
                    "UNSUPPORTED_INPUT_RELEASE",
                    f"{path}/record_type",
                    f"unsupported input record type {record_type!r}",
                )
                continue
            product, release_kind = kind
            issues.extend(
                validate_release_identity(
                    record, product=product, release_kind=release_kind, path=path
                )
            )
            release_id = record.get("release_id")
            if not isinstance(release_id, str):
                _issue(
                    issues,
                    "MISSING_FIELD",
                    f"{path}/release_id",
                    "release_id is required",
                )
                continue
            if release_id in records:
                _issue(
                    issues,
                    "DUPLICATE_RELEASE_ID",
                    f"{path}/release_id",
                    f"duplicate input release {release_id}",
                )
                continue
            records[release_id] = record
    return records, issues


def _pin_record(
    release: Mapping[str, Any],
    pin_name: str,
    expected_type: str,
    inputs: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> Mapping[str, Any] | None:
    pins = release.get("input_releases")
    pin = pins.get(pin_name) if isinstance(pins, dict) else None
    path = f"$/input_releases/{pin_name}"
    if not isinstance(pin, dict):
        _issue(issues, "MISSING_FIELD", path, "release pin is required")
        return None
    release_id = pin.get("release_id")
    digest = pin.get("release_digest")
    target = inputs.get(release_id) if isinstance(release_id, str) else None
    if target is None:
        _issue(
            issues,
            "PINNED_RELEASE_NOT_FOUND",
            f"{path}/release_id",
            f"input release {release_id!r} is unavailable",
        )
        return None
    if _record_type(target) != expected_type:
        _issue(
            issues,
            "PINNED_RELEASE_TYPE_MISMATCH",
            f"{path}/release_id",
            f"expected {expected_type}, found {_record_type(target)!r}",
        )
    if target.get("release_digest") != digest:
        _issue(
            issues,
            "PINNED_RELEASE_DIGEST_MISMATCH",
            f"{path}/release_digest",
            f"pin does not match {release_id}",
        )
    return target


def _record_index(
    release: Mapping[str, Any],
    field: str,
    expected_type: str,
    issues: list[ValidationIssue],
) -> dict[str, Mapping[str, Any]]:
    records = release.get(field)
    result: dict[str, Mapping[str, Any]] = {}
    if not isinstance(records, list):
        _issue(issues, "MISSING_FIELD", f"$/{field}", "record array is required")
        return result
    for index, record in enumerate(records):
        path = f"$/{field}/{index}"
        if not isinstance(record, dict):
            _issue(issues, "INVALID_RECORD", path, "record must be an object")
            continue
        if record.get("record_type") != expected_type:
            _issue(
                issues,
                "WRONG_RECORD_TYPE",
                f"{path}/record_type",
                f"expected {expected_type}",
            )
            continue
        record_id = record.get("record_id")
        try:
            expected_id = stable_record_id(record)
        except ValueError as exc:
            _issue(issues, "MISSING_IDENTITY_FIELD", path, str(exc))
            continue
        if record_id != expected_id:
            _issue(
                issues,
                "RECORD_ID_MISMATCH",
                f"{path}/record_id",
                f"expected {expected_id}",
            )
        if not isinstance(record_id, str):
            continue
        if record_id in result:
            _issue(
                issues,
                "DUPLICATE_RECORD_ID",
                f"{path}/record_id",
                f"duplicate record {record_id}",
            )
            continue
        result[record_id] = record
    return result


def _document_indexes(
    document: Mapping[str, Any] | None,
) -> tuple[
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
]:
    if document is None:
        return {}, {}, {}
    artifacts: dict[str, Mapping[str, Any]] = {
        value["artifact_id"]: value
        for value in document.get("artifacts", [])
        if isinstance(value, dict) and isinstance(value.get("artifact_id"), str)
    }
    for record in [
        *document.get("document_versions", []),
        *document.get("text_representations", []),
    ]:
        if not isinstance(record, dict):
            continue
        projection = record.get("artifact_projection")
        if isinstance(projection, dict) and isinstance(
            projection.get("artifact_id"), str
        ):
            artifacts[projection["artifact_id"]] = projection
    fragments: dict[str, Mapping[str, Any]] = {
        value["fragment_id"]: value
        for value in document.get("source_fragments", [])
        if isinstance(value, dict) and isinstance(value.get("fragment_id"), str)
    }
    for passage in document.get("structural_passages", []):
        if not isinstance(passage, dict):
            continue
        projection = passage.get("source_fragment_projection")
        if isinstance(projection, dict) and isinstance(
            projection.get("fragment_id"), str
        ):
            fragments[projection["fragment_id"]] = projection
    representations = {
        value["representation_id"]: value
        for value in document.get("text_representations", [])
        if isinstance(value, dict)
        and isinstance(value.get("representation_id"), str)
    }
    return artifacts, fragments, representations


def _representation_artifact_ref(representation: Mapping[str, Any]) -> object:
    projection = representation.get("artifact_projection")
    if isinstance(projection, dict):
        return projection.get("artifact_id")
    return representation.get("representation_id")


def _validate_document_records(
    artifacts: Mapping[str, Mapping[str, Any]],
    fragments: Mapping[str, Mapping[str, Any]],
    representations: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> None:
    """Verify exact fragment coordinates against pinned representation text."""

    for artifact_id, artifact in artifacts.items():
        _check_digest(
            artifact.get("content_digest"),
            issues,
            f"$inputs/document/artifacts/{artifact_id}/content_digest",
        )
    representation_by_artifact = {
        artifact_ref: representation
        for representation in representations.values()
        if isinstance(
            artifact_ref := _representation_artifact_ref(representation), str
        )
    }
    for fragment_id, fragment in fragments.items():
        path = f"$inputs/document/source_fragments/{fragment_id}"
        source_ref = fragment.get("source_artifact_ref")
        artifact = artifacts.get(source_ref)
        representation = representation_by_artifact.get(source_ref)
        if artifact is None or representation is None:
            _issue(
                issues,
                "FRAGMENT_SOURCE_NOT_FOUND",
                path,
                "fragment source must be a published text-representation Artifact",
            )
            continue
        if fragment.get("source_artifact_digest") != artifact.get(
            "content_digest"
        ):
            _issue(
                issues,
                "FRAGMENT_SOURCE_DIGEST_MISMATCH",
                path,
                "fragment must pin the source Artifact content digest",
            )
        source_text = representation.get("unicode_text")
        if not isinstance(source_text, str):
            _issue(
                issues,
                "TEXT_REPRESENTATION_INVALID",
                path,
                "text representation must carry Unicode text",
            )
            continue
        expected_text_digest = text_digest(source_text)
        if representation.get("text_digest") != expected_text_digest or artifact.get(
            "content_digest"
        ) != expected_text_digest:
            _issue(
                issues,
                "TEXT_REPRESENTATION_DIGEST_MISMATCH",
                path,
                f"expected {expected_text_digest}",
            )
        selector = fragment.get("selector")
        if not isinstance(selector, dict) or selector.get(
            "coordinate_system"
        ) not in {"unicode-code-points", "unicode-codepoints-half-open"}:
            _issue(
                issues,
                "FRAGMENT_SELECTOR_INVALID",
                path,
                "fixture fragments require Unicode code-point coordinates",
            )
            continue
        start = selector.get("start")
        end = selector.get("end")
        if (
            not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end < start
            or end > len(source_text)
        ):
            _issue(
                issues,
                "FRAGMENT_SELECTOR_INVALID",
                path,
                "fragment requires valid half-open bounds",
            )
            continue
        expected_selected_digest = text_digest(source_text[start:end])
        if fragment.get("selected_text_digest") != expected_selected_digest:
            _issue(
                issues,
                "FRAGMENT_TEXT_DIGEST_MISMATCH",
                path,
                f"expected {expected_selected_digest}",
            )


def _validate_projection(
    projection: Mapping[str, Any],
    segments: Mapping[str, Mapping[str, Any]],
    fragments: Mapping[str, Mapping[str, Any]],
    representations: Mapping[str, Mapping[str, Any]],
    issues: list[ValidationIssue],
) -> None:
    segment = segments.get(projection.get("derived_unit_ref"))
    if segment is None:
        _issue(
            issues,
            "PROJECTION_UNIT_NOT_FOUND",
            "$/derived_text_projections",
            "projection must reference a published processing segment",
        )
        return
    derived_text = segment.get("derived_text")
    if not isinstance(derived_text, str):
        _issue(
            issues,
            "INVALID_DERIVED_TEXT",
            "$/processing_segments",
            "processing segment must carry Unicode derived_text",
        )
        return
    expected_digest = text_digest(derived_text)
    if segment.get("derived_text_digest") != expected_digest:
        _issue(
            issues,
            "DERIVED_TEXT_DIGEST_MISMATCH",
            "$/processing_segments",
            f"expected {expected_digest}",
        )
    if projection.get("derived_text_digest") != expected_digest:
        _issue(
            issues,
            "DERIVED_TEXT_DIGEST_MISMATCH",
            "$/derived_text_projections",
            f"expected {expected_digest}",
        )
    if segment.get("projection_ref") != projection.get("record_id"):
        _issue(
            issues,
            "PROJECTION_LINK_MISMATCH",
            "$/processing_segments",
            "segment and projection references must be reciprocal",
        )
    input_fragment_refs = projection.get("input_fragment_refs")
    if input_fragment_refs != segment.get("input_fragment_refs") or not isinstance(
        input_fragment_refs, list
    ):
        _issue(
            issues,
            "PROJECTION_INPUT_MISMATCH",
            "$/derived_text_projections/input_fragment_refs",
            "projection inputs must exactly match the processing segment",
        )
        input_fragment_refs = []
    if any(fragment_ref not in fragments for fragment_ref in input_fragment_refs):
        _issue(
            issues,
            "PROJECTION_FRAGMENT_NOT_FOUND",
            "$/derived_text_projections/input_fragment_refs",
            "every projection input must resolve in DocumentRelease",
        )

    slices = projection.get("ordered_slices")
    if not isinstance(slices, list) or not slices:
        _issue(
            issues,
            "PROJECTION_NOT_CLOSED",
            "$/derived_text_projections/ordered_slices",
            "projection requires ordered slices",
        )
        return
    cursor = 0
    for index, item in enumerate(slices):
        path = f"$/derived_text_projections/ordered_slices/{index}"
        if not isinstance(item, dict):
            _issue(issues, "PROJECTION_NOT_CLOSED", path, "slice must be an object")
            continue
        start = item.get("derived_start")
        end = item.get("derived_end")
        if not isinstance(start, int) or not isinstance(end, int):
            _issue(issues, "PROJECTION_NOT_CLOSED", path, "bounds must be integers")
            continue
        if start != cursor or end < start or end > len(derived_text):
            _issue(
                issues,
                "PROJECTION_NOT_CLOSED",
                path,
                f"expected next half-open slice to start at {cursor}",
            )
            cursor = max(cursor, end)
            continue
        derived_slice = derived_text[start:end]
        kind = item.get("slice_kind")
        if kind == "source_range":
            representation = representations.get(
                item.get("source_text_representation_ref")
            )
            source_start = item.get("source_start")
            source_end = item.get("source_end")
            if (
                representation is None
                or not isinstance(source_start, int)
                or not isinstance(source_end, int)
                or not isinstance(representation.get("unicode_text"), str)
            ):
                _issue(
                    issues,
                    "PROJECTION_SOURCE_NOT_FOUND",
                    path,
                    "source range must resolve to exact representation text",
                )
            else:
                source_text = representation["unicode_text"]
                if source_text[source_start:source_end] != derived_slice:
                    _issue(
                        issues,
                        "PROJECTION_TEXT_MISMATCH",
                        path,
                        "derived source range differs from pinned representation",
                    )
            refs = item.get("source_fragment_refs")
            if not isinstance(refs, list) or not refs or any(
                ref not in fragments for ref in refs
            ):
                _issue(
                    issues,
                    "PROJECTION_FRAGMENT_NOT_FOUND",
                    path,
                    "source range must name resolvable source fragments",
                )
            elif any(ref not in input_fragment_refs for ref in refs):
                _issue(
                    issues,
                    "PROJECTION_INPUT_MISMATCH",
                    path,
                    "source slices may reference only declared segment inputs",
                )
            else:
                covered = False
                for fragment_ref in refs:
                    selector = fragments[fragment_ref].get("selector")
                    if not isinstance(selector, dict):
                        continue
                    fragment_start = selector.get("start")
                    fragment_end = selector.get("end")
                    if (
                        isinstance(source_start, int)
                        and not isinstance(source_start, bool)
                        and isinstance(source_end, int)
                        and not isinstance(source_end, bool)
                        and isinstance(fragment_start, int)
                        and not isinstance(fragment_start, bool)
                        and isinstance(fragment_end, int)
                        and not isinstance(fragment_end, bool)
                        and fragments[fragment_ref].get("source_artifact_ref")
                        == _representation_artifact_ref(representation)
                        and fragment_start <= source_start
                        and source_end <= fragment_end
                    ):
                        covered = True
                if not covered:
                    _issue(
                        issues,
                        "PROJECTION_RANGE_OUTSIDE_FRAGMENT",
                        path,
                        "source range must fall within a named input fragment",
                    )
        elif kind == "inserted_text":
            inserted_text = item.get("inserted_text")
            if inserted_text != derived_slice:
                _issue(
                    issues,
                    "PROJECTION_TEXT_MISMATCH",
                    path,
                    "inserted text differs from derived slice",
                )
            if not isinstance(inserted_text, str) or item.get(
                "inserted_text_digest"
            ) != text_digest(inserted_text):
                _issue(
                    issues,
                    "PROJECTION_TEXT_MISMATCH",
                    path,
                    "inserted text digest does not match",
                )
        elif kind == "transformed_range":
            if not item.get("transform_method_version"):
                _issue(
                    issues,
                    "PROJECTION_TRANSFORM_UNDECLARED",
                    path,
                    "transformed ranges require a versioned transform",
                )
        else:
            _issue(
                issues,
                "PROJECTION_SLICE_KIND",
                path,
                f"unsupported slice kind {kind!r}",
            )
        cursor = end
    if cursor != len(derived_text):
        _issue(
            issues,
            "PROJECTION_NOT_CLOSED",
            "$/derived_text_projections/ordered_slices",
            f"projection accounts for {cursor} of {len(derived_text)} code points",
        )
    for index, omitted in enumerate(projection.get("omitted_source_ranges", [])):
        path = f"$/derived_text_projections/omitted_source_ranges/{index}"
        if not isinstance(omitted, dict):
            _issue(issues, "PROJECTION_OMISSION_INVALID", path, "omission must be an object")
            continue
        representation = representations.get(
            omitted.get("source_text_representation_ref")
        )
        start = omitted.get("source_start")
        end = omitted.get("source_end")
        if (
            representation is None
            or not isinstance(representation.get("unicode_text"), str)
            or not isinstance(start, int)
            or isinstance(start, bool)
            or not isinstance(end, int)
            or isinstance(end, bool)
            or start < 0
            or end < start
            or end > len(representation["unicode_text"])
        ):
            _issue(
                issues,
                "PROJECTION_OMISSION_INVALID",
                path,
                "omitted range must resolve against an exact representation",
            )


def _reference_resource_view(
    vocabulary: Mapping[str, Any] | None, issues: list[ValidationIssue]
) -> Mapping[str, Any]:
    if vocabulary is None:
        return {}
    candidate = vocabulary.get("reference_resource_release")
    if not isinstance(candidate, dict):
        _issue(
            issues,
            "REFERENCE_RELEASE_NOT_FOUND",
            "$inputs/vocabulary/reference_resource_release",
            "VocabularyRelease must expose a complete ReferenceResourceRelease",
        )
        return {}
    if candidate.get("record_type") == "ReferenceResourceRelease":
        issues.extend(
            validate_release_identity(
                candidate,
                product="rulespec",
                release_kind="reference-resource",
                path="$inputs/vocabulary/reference_resource_release",
            )
        )
        return candidate

    graph = candidate.get("@graph")
    if not isinstance(graph, list):
        _issue(
            issues,
            "REFERENCE_RELEASE_NOT_FOUND",
            "$inputs/vocabulary/reference_resource_release/@graph",
            "portable reference release must carry a JSON-LD graph",
        )
        return {}
    nodes = [
        value
        for value in graph
        if isinstance(value, dict)
        and value.get("@type") == "rkaf:ReferenceResourceRelease"
    ]
    if len(nodes) != 1:
        _issue(
            issues,
            "REFERENCE_RELEASE_NOT_FOUND",
            "$inputs/vocabulary/reference_resource_release/@graph",
            "expected one rkaf:ReferenceResourceRelease node",
        )
        return {}
    node = nodes[0]
    release_id = node.get("@id")
    release_digest = node.get("rkaf:referenceReleaseDigest")
    _check_digest(
        release_digest,
        issues,
        "$inputs/vocabulary/reference_resource_release/referenceReleaseDigest",
    )
    concepts = vocabulary.get("concepts")
    concept_ids = {
        value.get("concept_id")
        for value in concepts or []
        if isinstance(value, dict) and isinstance(value.get("concept_id"), str)
    }
    members = node.get("prov:hadMember")
    if (
        node.get("rkaf:membershipMode") != "rkaf:completeMembership"
        or not isinstance(members, list)
        or set(members) != concept_ids
    ):
        _issue(
            issues,
            "REFERENCE_RELEASE_INCOMPLETE",
            "$inputs/vocabulary/reference_resource_release",
            "JSON-LD membership must be complete and match published concepts",
        )
    return {
        "release_id": release_id,
        "release_digest": release_digest,
        "membership_mode": "complete",
        "concepts": concepts if isinstance(concepts, list) else [],
    }


def validate_extrapolation_release(
    release: Mapping[str, Any], inputs: Mapping[str, Mapping[str, Any]]
) -> list[ValidationIssue]:
    """Validate one nonempty, evidence-bound ExtrapolationRelease."""

    issues = _required_fields(
        release,
        (
            "record_type",
            "release_id",
            "release_digest",
            "release_status",
            "version",
            "profile",
            "input_releases",
            "validation_sample_manifest",
            "concept_assignments",
            "evidence_bindings",
            "extraction_activities",
            "ai_lineage_records",
            "processing_segments",
            "derived_text_projections",
            "agent_validation_receipts",
            "baseline_validation_receipts",
            "selection_receipts",
            "selection_context_digest",
            "validation_artifacts",
            "selected_assignment_refs",
            "coverage",
        ),
        "$",
    )
    if release.get("record_type") != "ExtrapolationRelease":
        _issue(
            issues,
            "WRONG_RECORD_TYPE",
            "$/record_type",
            "expected ExtrapolationRelease",
        )
    issues.extend(
        validate_release_identity(
            release,
            product="rulespec",
            release_kind="extrapolation",
        )
    )

    core = _pin_record(
        release,
        "rulespec_core_release",
        "RulespecCoreRelease",
        inputs,
        issues,
    )
    document = _pin_record(
        release,
        "document_release",
        "DocumentRelease",
        inputs,
        issues,
    )
    vocabulary = _pin_record(
        release,
        "vocabulary_release",
        "VocabularyRelease",
        inputs,
        issues,
    )
    if core is not None:
        issues.extend(validate_rulespec_core_release(core, path="$inputs/core"))
    profile = release.get("profile")
    if not isinstance(profile, dict) or profile.get("usage_cap") != "searchOnly":
        _issue(
            issues,
            "PROFILE_USAGE_CAP_INVALID",
            "$/profile/usage_cap",
            "M2 extrapolation profiles must cap use at searchOnly",
        )

    assignments = _record_index(
        release, "concept_assignments", "ConceptAssignment", issues
    )
    evidence = _record_index(release, "evidence_bindings", "EvidenceBinding", issues)
    activities = _record_index(
        release, "extraction_activities", "ExtractionActivity", issues
    )
    lineages = _record_index(release, "ai_lineage_records", "AILineage", issues)
    segments = _record_index(
        release, "processing_segments", "ProcessingSegment", issues
    )
    projections = _record_index(
        release, "derived_text_projections", "DerivedTextProjection", issues
    )
    agent_receipts = _record_index(
        release,
        "agent_validation_receipts",
        "AgentValidationReceipt",
        issues,
    )
    baseline_receipts = _record_index(
        release,
        "baseline_validation_receipts",
        "BaselineValidationReceipt",
        issues,
    )
    selection_receipts = _record_index(
        release,
        "selection_receipts",
        "ExtrapolationSelectionReceipt",
        issues,
    )
    expected_selection_context_digest = extrapolation_selection_context_digest(
        release
    )
    if release.get("selection_context_digest") != expected_selection_context_digest:
        _issue(
            issues,
            "SELECTION_CONTEXT_MISMATCH",
            "$/selection_context_digest",
            "selection context must bind the complete pre-selection release graph",
        )
    validation_artifacts: dict[str, Mapping[str, Any]] = {}
    raw_validation_artifacts = release.get("validation_artifacts")
    if not isinstance(raw_validation_artifacts, list) or not raw_validation_artifacts:
        _issue(
            issues,
            "VALIDATION_ARTIFACTS_MISSING",
            "$/validation_artifacts",
            "sealed validator requests and responses are required",
        )
    else:
        for index, artifact in enumerate(raw_validation_artifacts):
            path = f"$/validation_artifacts/{index}"
            if not isinstance(artifact, dict):
                _issue(issues, "INVALID_RECORD", path, "Artifact must be an object")
                continue
            artifact_id = artifact.get("artifact_id")
            identity_fields = (
                "artifact_type",
                "content_digest",
                "media_type",
                "coordinate_system",
            )
            missing = [field for field in identity_fields if field not in artifact]
            if missing:
                _issue(
                    issues,
                    "MISSING_IDENTITY_FIELD",
                    path,
                    f"Artifact lacks {', '.join(missing)}",
                )
                continue
            expected_id = content_addressed_id(
                "rulespec",
                "artifact",
                {field: artifact[field] for field in identity_fields},
            )
            if artifact_id != expected_id:
                _issue(
                    issues,
                    "RECORD_ID_MISMATCH",
                    f"{path}/artifact_id",
                    f"expected {expected_id}",
                )
            _check_digest(
                artifact.get("content_digest"),
                issues,
                f"{path}/content_digest",
            )
            if isinstance(artifact_id, str):
                if artifact_id in validation_artifacts:
                    _issue(
                        issues,
                        "DUPLICATE_RECORD_ID",
                        f"{path}/artifact_id",
                        f"duplicate Artifact {artifact_id}",
                    )
                validation_artifacts[artifact_id] = artifact

    artifacts, fragments, representations = _document_indexes(document)
    _validate_document_records(artifacts, fragments, representations, issues)
    if core is not None:
        expected_core_pin = {
            "release_id": core.get("release_id"),
            "release_digest": core.get("release_digest"),
        }
        for name, upstream in (("document", document), ("vocabulary", vocabulary)):
            if upstream is not None and upstream.get(
                "rulespec_core_release"
            ) != expected_core_pin:
                _issue(
                    issues,
                    "UPSTREAM_CORE_PIN_MISMATCH",
                    f"$inputs/{name}/rulespec_core_release",
                    "upstream release must pin the same Rulespec Core release",
                )
    reference_release = _reference_resource_view(vocabulary, issues)
    if reference_release and reference_release.get("membership_mode") != "complete":
        _issue(
            issues,
            "REFERENCE_RELEASE_INCOMPLETE",
            "$inputs/vocabulary/reference_resource_release/membership_mode",
            "concept assignments require complete membership",
        )
    concepts = {
        concept.get("concept_id")
        for concept in reference_release.get("concepts", [])
        if isinstance(concept, dict)
        and isinstance(concept.get("concept_id"), str)
    }

    for projection in projections.values():
        _validate_projection(
            projection, segments, fragments, representations, issues
        )

    for segment_id, segment in segments.items():
        if document is None or segment.get("document_release_ref") != document.get(
            "release_id"
        ):
            _issue(
                issues,
                "PROCESSING_SEGMENT_RELEASE_MISMATCH",
                f"$/processing_segments/{segment_id}/document_release_ref",
                "segment must pin this ExtrapolationRelease's DocumentRelease",
            )
        refs = segment.get("input_fragment_refs")
        if not isinstance(refs, list) or not refs or any(
            ref not in fragments for ref in refs
        ):
            _issue(
                issues,
                "PROCESSING_SEGMENT_INPUT_NOT_FOUND",
                f"$/processing_segments/{segment_id}/input_fragment_refs",
                "segment inputs must resolve in the pinned DocumentRelease",
            )

    input_pins = release.get("input_releases")
    if not isinstance(input_pins, dict):
        input_pins = {}
    expected_input_refs = {
        pin.get("release_id")
        for pin in input_pins.values()
        if isinstance(pin, dict) and isinstance(pin.get("release_id"), str)
    }
    for activity_id, activity in activities.items():
        if activity.get("processing_segment_ref") not in segments:
            _issue(
                issues,
                "EXTRACTION_SEGMENT_NOT_FOUND",
                f"$/extraction_activities/{activity_id}/processing_segment_ref",
                "extraction activity must resolve its processing segment",
            )
        refs = activity.get("input_release_refs")
        if not isinstance(refs, list) or set(refs) != expected_input_refs:
            _issue(
                issues,
                "EXTRACTION_INPUT_RELEASE_MISMATCH",
                f"$/extraction_activities/{activity_id}/input_release_refs",
                "activity inputs must exactly match the three pinned releases",
            )
        _check_digest(
            activity.get("request_contract_digest"),
            issues,
            f"$/extraction_activities/{activity_id}/request_contract_digest",
        )
    for lineage_id, lineage in lineages.items():
        for field in ("prompt_contract_digest", "input_context_digest"):
            _check_digest(
                lineage.get(field),
                issues,
                f"$/ai_lineage_records/{lineage_id}/{field}",
            )

    for evidence_id, binding in evidence.items():
        assignment_ref = binding.get("binds_assignment_ref")
        if assignment_ref not in assignments:
            _issue(
                issues,
                "EVIDENCE_TARGET_NOT_FOUND",
                f"$/evidence_bindings/{evidence_id}",
                "binding must target an assignment in this release",
            )
        spans = binding.get("evidence_spans")
        if not isinstance(spans, list) or not spans:
            _issue(
                issues,
                "MISSING_EVIDENCE",
                f"$/evidence_bindings/{evidence_id}/evidence_spans",
                "fragment-backed evidence is required",
            )
            continue
        for span in spans:
            if not isinstance(span, dict):
                _issue(
                    issues,
                    "MISSING_EVIDENCE",
                    f"$/evidence_bindings/{evidence_id}/evidence_spans",
                    "evidence span must be an object",
                )
                continue
            fragment = fragments.get(span.get("source_fragment_ref"))
            if fragment is None:
                _issue(
                    issues,
                    "EVIDENCE_FRAGMENT_NOT_FOUND",
                    f"$/evidence_bindings/{evidence_id}",
                    "source fragment does not resolve in DocumentRelease",
                )
                continue
            if span.get("selected_text_digest") != fragment.get(
                "selected_text_digest"
            ):
                _issue(
                    issues,
                    "EVIDENCE_DIGEST_MISMATCH",
                    f"$/evidence_bindings/{evidence_id}",
                    "evidence digest differs from the pinned source fragment",
                )

    for assignment_id, assignment in assignments.items():
        binding_refs = assignment.get("evidence_binding_refs")
        if not isinstance(binding_refs, list) or not binding_refs:
            _issue(
                issues,
                "MISSING_EVIDENCE",
                f"$/concept_assignments/{assignment_id}/evidence_binding_refs",
                "every candidate assignment requires evidence",
            )
        else:
            for binding_ref in binding_refs:
                binding = evidence.get(binding_ref)
                if binding is None or binding.get(
                    "binds_assignment_ref"
                ) != assignment_id:
                    _issue(
                        issues,
                        "MISSING_EVIDENCE",
                        f"$/concept_assignments/{assignment_id}",
                        "evidence binding is missing or targets another assignment",
                    )
        if assignment.get("extraction_activity_ref") not in activities:
            _issue(
                issues,
                "MISSING_EXTRACTION_ACTIVITY",
                f"$/concept_assignments/{assignment_id}",
                "every candidate assignment requires extraction activity lineage",
            )
        if assignment.get("assertion_origin") == "aiSuggested" and assignment.get(
            "ai_lineage_ref"
        ) not in lineages:
            _issue(
                issues,
                "MISSING_AI_LINEAGE",
                f"$/concept_assignments/{assignment_id}",
                "aiSuggested assignments require AILineage",
            )

    selected_refs = release.get("selected_assignment_refs")
    if not isinstance(selected_refs, list) or not selected_refs:
        _issue(
            issues,
            "EXTRAPOLATION_RELEASE_EMPTY",
            "$/selected_assignment_refs",
            "M2 requires at least one selected assignment",
        )
        selected_refs = []
    if len(selected_refs) != len(set(selected_refs)):
        _issue(
            issues,
            "DUPLICATE_SELECTED_ASSIGNMENT",
            "$/selected_assignment_refs",
            "selected assignment references must be unique",
        )

    selection_by_assignment: dict[str, Mapping[str, Any]] = {}
    for receipt_id, receipt in selection_receipts.items():
        assignment_ref = receipt.get("assignment_ref")
        if not isinstance(assignment_ref, str) or assignment_ref not in assignments:
            _issue(
                issues,
                "SELECTION_ASSIGNMENT_NOT_FOUND",
                f"$/selection_receipts/{receipt_id}/assignment_ref",
                "selection receipt must target a candidate in this release",
            )
            continue
        if assignment_ref in selection_by_assignment:
            _issue(
                issues,
                "DUPLICATE_SELECTION_RECEIPT",
                f"$/selection_receipts/{receipt_id}/assignment_ref",
                "each candidate has exactly one selection receipt",
            )
            continue
        selection_by_assignment[assignment_ref] = receipt
        if "output_extrapolation_release_ref" in receipt:
            _issue(
                issues,
                "SELF_REFERENTIAL_SELECTION_RECEIPT",
                f"$/selection_receipts/{receipt_id}/output_extrapolation_release_ref",
                "contained receipts derive output membership from the root release",
            )
        if receipt.get("selection_context_digest") != expected_selection_context_digest:
            _issue(
                issues,
                "SELECTION_CONTEXT_MISMATCH",
                f"$/selection_receipts/{receipt_id}/selection_context_digest",
                "selection receipt belongs to another pre-selection release graph",
            )
        binding_refs = assignments[assignment_ref].get("evidence_binding_refs")
        if not isinstance(binding_refs, list):
            binding_refs = []
        required_inputs = {
            assignment_ref,
            *binding_refs,
            assignments[assignment_ref].get("extraction_activity_ref"),
            assignments[assignment_ref].get("ai_lineage_ref"),
            receipt.get("baseline_validation_receipt_ref"),
        }
        inputs_for_selection = receipt.get("input_record_refs")
        if (
            not isinstance(inputs_for_selection, list)
            or not all(isinstance(value, str) for value in inputs_for_selection)
            or not required_inputs.issubset(set(inputs_for_selection))
        ):
            _issue(
                issues,
                "SELECTION_INPUT_INCOMPLETE",
                f"$/selection_receipts/{receipt_id}/input_record_refs",
                "selection receipt must name its assignment, evidence, lineage, and baseline",
            )
    for assignment_id in assignments:
        if assignment_id not in selection_by_assignment:
            _issue(
                issues,
                "SELECTION_RECEIPT_MISSING",
                f"$/concept_assignments/{assignment_id}",
                "every candidate requires one deterministic selection receipt",
            )
    selected_kinds: set[str] = set()
    for assignment_ref in selected_refs:
        assignment = assignments.get(assignment_ref)
        if assignment is None:
            _issue(
                issues,
                "SELECTED_ASSIGNMENT_NOT_FOUND",
                "$/selected_assignment_refs",
                f"assignment {assignment_ref!r} is absent",
            )
            continue
        subject_kind = assignment.get("subject_kind")
        if subject_kind == "ProcessingSegment":
            _issue(
                issues,
                "PROCESSING_SEGMENT_TARGET",
                f"$/concept_assignments/{assignment_ref}/subject_kind",
                "processing segments cannot be served assignment targets",
            )
        elif subject_kind == "Artifact":
            selected_kinds.add(subject_kind)
            if assignment.get("asserts_subject_ref") not in artifacts:
                _issue(
                    issues,
                    "ASSIGNMENT_SUBJECT_NOT_FOUND",
                    f"$/concept_assignments/{assignment_ref}",
                    "artifact target does not resolve in DocumentRelease",
                )
        elif subject_kind == "SourceFragment":
            selected_kinds.add(subject_kind)
            if assignment.get("asserts_subject_ref") not in fragments:
                _issue(
                    issues,
                    "ASSIGNMENT_SUBJECT_NOT_FOUND",
                    f"$/concept_assignments/{assignment_ref}",
                    "fragment target does not resolve in DocumentRelease",
                )
        else:
            _issue(
                issues,
                "ASSIGNMENT_SUBJECT_KIND",
                f"$/concept_assignments/{assignment_ref}/subject_kind",
                f"unsupported subject kind {subject_kind!r}",
            )

        if assignment.get("assigned_concept_release_ref") != reference_release.get(
            "release_id"
        ):
            _issue(
                issues,
                "ASSIGNED_CONCEPT_RELEASE_MISMATCH",
                f"$/concept_assignments/{assignment_ref}",
                "assignment must pin the complete reference resource release",
            )
        if assignment.get("asserts_object_ref") not in concepts:
            _issue(
                issues,
                "CONCEPT_NOT_IN_RELEASE",
                f"$/concept_assignments/{assignment_ref}",
                "assigned concept is not a member of the pinned release",
            )
        if assignment.get("usage_eligibility") != "searchOnly":
            _issue(
                issues,
                "NON_SEARCH_ONLY_ASSIGNMENT",
                f"$/concept_assignments/{assignment_ref}/usage_eligibility",
                "served M2 assignments must be capped at searchOnly",
            )
        selection = selection_by_assignment.get(assignment_ref)
        if selection is None or selection.get("selection_result") != "selected":
            _issue(
                issues,
                "UNSELECTED_ASSIGNMENT_INCLUDED",
                "$/selected_assignment_refs",
                "selected subset contains a not-selected or deferred assignment",
            )
            continue
        baseline = baseline_receipts.get(
            selection.get("baseline_validation_receipt_ref")
        )
        if baseline is None or baseline.get("aggregate_result") not in {
            "usable_for_search",
            "usable_with_nonblocking_limits",
        }:
            _issue(
                issues,
                "BASELINE_NOT_USABLE",
                f"$/selection_receipts/{selection.get('record_id')}",
                "selection requires a usable baseline validation receipt",
            )
        checks = selection.get("checks")
        if not isinstance(checks, list) or any(
            not isinstance(check, dict) or check.get("outcome") != "pass"
            for check in checks
        ):
            _issue(
                issues,
                "SELECTION_CHECK_FAILED",
                f"$/selection_receipts/{selection.get('record_id')}",
                "every deterministic selection check must pass",
            )

    if selected_refs and selected_kinds != {"Artifact", "SourceFragment"}:
        _issue(
            issues,
            "M2_SCOPE_INCOMPLETE",
            "$/selected_assignment_refs",
            "sealed M2 fixture requires separate document and fragment assignments",
        )

    sample_manifest = release.get("validation_sample_manifest")
    manifest_refs: set[str] = set()
    manifest_digest: object = None
    manifest_ref: str | None = None
    if isinstance(sample_manifest, dict):
        refs = sample_manifest.get("record_refs")
        if isinstance(refs, list) and all(isinstance(ref, str) for ref in refs):
            manifest_refs = set(refs)
            if len(refs) != len(manifest_refs):
                _issue(
                    issues,
                    "VALIDATION_MANIFEST_DUPLICATE_REF",
                    "$/validation_sample_manifest/record_refs",
                    "sealed manifest references must be unique",
                )
            manifest_digest = canonical_digest({"record_refs": refs})
            manifest_ref = content_addressed_id(
                "rulespec",
                "validation-sample-manifest",
                {"manifest_digest": manifest_digest},
            )
            if sample_manifest.get("manifest_digest") != manifest_digest:
                _issue(
                    issues,
                    "VALIDATION_MANIFEST_DIGEST_MISMATCH",
                    "$/validation_sample_manifest/manifest_digest",
                    f"expected {manifest_digest}",
                )
        else:
            _issue(
                issues,
                "VALIDATION_MANIFEST_INVALID",
                "$/validation_sample_manifest/record_refs",
                "record_refs must be a string array",
            )
    if not set(validation_artifacts).issubset(manifest_refs):
        _issue(
            issues,
            "VALIDATION_ARTIFACT_OUTSIDE_MANIFEST",
            "$/validation_artifacts",
            "every sealed request and response Artifact must be in the sample manifest",
        )

    for receipt_id, receipt in agent_receipts.items():
        path = f"$/agent_validation_receipts/{receipt_id}"
        execution_status = receipt.get("execution_status")
        if execution_status == "completed":
            if receipt.get("overall_recommendation") not in {
                "supports",
                "flags",
                "abstains",
            }:
                _issue(
                    issues,
                    "VALIDATOR_RECOMMENDATION_MISSING",
                    path,
                    "completed validator attempts require a recommendation",
                )
            response = validation_artifacts.get(receipt.get("response_artifact_ref"))
            if response is None or response.get("content_digest") != receipt.get(
                "response_artifact_digest"
            ):
                _issue(
                    issues,
                    "VALIDATOR_RESPONSE_NOT_FOUND",
                    path,
                    "completed attempt must retain its exact response Artifact",
                )
        elif execution_status == "failed":
            if receipt.get("overall_recommendation") is not None:
                _issue(
                    issues,
                    "FAILED_VALIDATOR_HAS_RECOMMENDATION",
                    path,
                    "failed execution cannot have a recommendation",
                )
            if not receipt.get("failure_reason"):
                _issue(
                    issues,
                    "VALIDATOR_FAILURE_REASON_MISSING",
                    path,
                    "failed execution requires a reason",
                )
        else:
            _issue(
                issues,
                "VALIDATOR_EXECUTION_STATUS_INVALID",
                path,
                "execution status must be completed or failed",
            )
        request = validation_artifacts.get(receipt.get("request_contract_ref"))
        if request is None or request.get("content_digest") != receipt.get(
            "request_contract_digest"
        ):
            _issue(
                issues,
                "VALIDATOR_REQUEST_NOT_FOUND",
                path,
                "validator must retain its secret-free request contract Artifact",
            )
        expected_profile_digest = (
            canonical_digest(profile) if isinstance(profile, dict) else None
        )
        if receipt.get("target_ref") != (
            profile.get("profile_id") if isinstance(profile, dict) else None
        ) or receipt.get("target_digest") != expected_profile_digest:
            _issue(
                issues,
                "VALIDATOR_TARGET_MISMATCH",
                path,
                "validator target must be the exact profile in this release",
            )
        checks = receipt.get("check_outcomes")
        outcomes = {
            check.get("outcome")
            for check in checks or []
            if isinstance(check, dict)
        }
        if "abstain" in outcomes or receipt.get("overall_recommendation") == "abstains":
            _issue(
                issues,
                "VALIDATOR_ABSTENTION",
                f"$/agent_validation_receipts/{receipt_id}",
                "abstention cannot support a usable baseline",
            )
        for check in checks or []:
            if not isinstance(check, dict):
                continue
            evidence_refs = check.get("evidence_refs", [])
            if any(ref not in manifest_refs for ref in evidence_refs):
                _issue(
                    issues,
                    "VALIDATOR_EVIDENCE_OUTSIDE_MANIFEST",
                    f"$/agent_validation_receipts/{receipt_id}",
                    "validator evidence must resolve inside the sealed manifest",
                )
        if receipt.get("input_manifest_digest") != manifest_digest:
            _issue(
                issues,
                "VALIDATOR_MANIFEST_MISMATCH",
                f"$/agent_validation_receipts/{receipt_id}/input_manifest_digest",
                "validator must use the sealed sample manifest",
            )
        if receipt.get("input_manifest_ref") != manifest_ref:
            _issue(
                issues,
                "VALIDATOR_MANIFEST_MISMATCH",
                f"{path}/input_manifest_ref",
                "validator must name the content-derived sample manifest",
            )

    for baseline_id, baseline in baseline_receipts.items():
        if baseline.get("sample_manifest_digest") != manifest_digest:
            _issue(
                issues,
                "BASELINE_MANIFEST_MISMATCH",
                f"$/baseline_validation_receipts/{baseline_id}/sample_manifest_digest",
                "baseline must evaluate the sealed sample manifest",
            )
        if baseline.get("sample_manifest_ref") != manifest_ref:
            _issue(
                issues,
                "BASELINE_MANIFEST_MISMATCH",
                f"$/baseline_validation_receipts/{baseline_id}/sample_manifest_ref",
                "baseline must name the content-derived sample manifest",
            )
        if vocabulary is None or baseline.get("target_release_ref") != vocabulary.get(
            "release_id"
        ):
            _issue(
                issues,
                "BASELINE_TARGET_MISMATCH",
                f"$/baseline_validation_receipts/{baseline_id}/target_release_ref",
                "baseline must qualify the pinned vocabulary release and profile",
            )
        referenced_agents = [
            agent_receipts.get(ref)
            for ref in baseline.get("agent_validation_receipt_refs", [])
        ]
        if any(receipt is None for receipt in referenced_agents):
            _issue(
                issues,
                "BASELINE_VALIDATOR_NOT_FOUND",
                f"$/baseline_validation_receipts/{baseline_id}",
                "baseline references an unavailable validator receipt",
            )
            continue
        groups = {receipt.get("independence_group") for receipt in referenced_agents}
        if len(groups) < 2:
            _issue(
                issues,
                "VALIDATORS_NOT_INDEPENDENT",
                f"$/baseline_validation_receipts/{baseline_id}",
                "usable baseline requires two independence groups",
            )
        if any(
            receipt.get("execution_status") != "completed"
            for receipt in referenced_agents
        ):
            _issue(
                issues,
                "BASELINE_VALIDATOR_FAILED",
                f"$/baseline_validation_receipts/{baseline_id}",
                "failed validator attempts cannot support a usable baseline",
            )
        if any(
            receipt.get("overall_recommendation") == "abstains"
            or any(
                check.get("outcome") == "abstain"
                for check in receipt.get("check_outcomes", [])
                if isinstance(check, dict)
            )
            for receipt in referenced_agents
        ) and baseline.get("aggregate_result") in {
            "usable_for_search",
            "usable_with_nonblocking_limits",
        }:
            _issue(
                issues,
                "BASELINE_ABSTENTION",
                f"$/baseline_validation_receipts/{baseline_id}",
                "a usable baseline cannot reduce an abstention to success",
            )
        deterministic = baseline.get("deterministic_check_outcomes")
        if not isinstance(deterministic, list) or any(
            not isinstance(check, dict) or check.get("outcome") != "pass"
            for check in deterministic
        ):
            _issue(
                issues,
                "BASELINE_DETERMINISTIC_CHECK_FAILED",
                f"$/baseline_validation_receipts/{baseline_id}",
                "every deterministic baseline check must pass",
            )

    coverage = release.get("coverage")
    if isinstance(coverage, dict):
        if coverage.get("record_type") != "ExtrapolationCoverage":
            _issue(
                issues,
                "WRONG_RECORD_TYPE",
                "$/coverage/record_type",
                "expected ExtrapolationCoverage",
            )
        coverage_preimage = dict(coverage)
        coverage_preimage.pop("coverage_id", None)
        coverage_preimage.pop("coverage_digest", None)
        expected_coverage_digest = canonical_digest(coverage_preimage)
        expected_coverage_id = expected_release_id(
            "rulespec", "extrapolation-coverage", expected_coverage_digest
        )
        if coverage.get("coverage_digest") != expected_coverage_digest:
            _issue(
                issues,
                "COVERAGE_DIGEST_MISMATCH",
                "$/coverage/coverage_digest",
                f"expected {expected_coverage_digest}",
            )
        if coverage.get("coverage_id") != expected_coverage_id:
            _issue(
                issues,
                "COVERAGE_ID_MISMATCH",
                "$/coverage/coverage_id",
                f"expected {expected_coverage_id}",
            )
        expected_counts = {
            "candidate_count": len(assignments),
            "selected_count": len(selected_refs),
            "not_selected_count": sum(
                receipt.get("selection_result") == "not_selected"
                for receipt in selection_receipts.values()
            ),
            "deferred_count": sum(
                receipt.get("selection_result") == "deferred"
                for receipt in selection_receipts.values()
            ),
        }
        for field, expected in expected_counts.items():
            if coverage.get(field) != expected:
                _issue(
                    issues,
                    "COVERAGE_MISMATCH",
                    f"$/coverage/{field}",
                    f"expected {expected}",
                )
    else:
        _issue(issues, "MISSING_FIELD", "$/coverage", "coverage object is required")
    return issues


def _set_pointer(root: Any, pointer: str, value: Any, *, remove: bool) -> None:
    if not pointer.startswith("/"):
        raise ValueError(f"JSON pointer must start with '/': {pointer!r}")
    tokens = [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]
    target = root
    for token in tokens[:-1]:
        target = target[int(token)] if isinstance(target, list) else target[token]
    final = tokens[-1]
    if isinstance(target, list):
        index = int(final)
        if remove:
            target.pop(index)
        else:
            target[index] = value
    elif remove:
        del target[final]
    else:
        target[final] = value


def apply_negative_control(
    base_release: Mapping[str, Any], control: Mapping[str, Any]
) -> dict[str, Any]:
    """Apply one sealed negative mutation and restamp the root release."""

    mutated = copy.deepcopy(dict(base_release))
    operations = control.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("negative control requires operations")
    for operation in operations:
        if not isinstance(operation, dict):
            raise ValueError("negative-control operation must be an object")
        op = operation.get("op")
        if op not in {"replace", "remove"}:
            raise ValueError(f"unsupported negative-control operation {op!r}")
        _set_pointer(
            mutated,
            operation.get("path", ""),
            operation.get("value"),
            remove=op == "remove",
        )
    return stamp_release(mutated, product="rulespec", release_kind="extrapolation")


def _validate_command(args: argparse.Namespace) -> int:
    release = load_json(Path(args.release))
    if not isinstance(release, dict):
        print("INVALID_RECORD $: release must be a JSON object", file=sys.stderr)
        return 2
    if release.get("record_type") == "RulespecCoreRelease":
        issues = validate_rulespec_core_release(release)
    elif release.get("record_type") == "ExtrapolationRelease":
        values = [load_json(Path(path)) for path in args.input]
        inputs, input_issues = index_input_releases(values)
        issues = input_issues + validate_extrapolation_release(release, inputs)
    else:
        issues = [
            ValidationIssue(
                "WRONG_RECORD_TYPE",
                "$/record_type",
                "expected RulespecCoreRelease or ExtrapolationRelease",
            )
        ]
    for issue in issues:
        print(issue, file=sys.stderr)
    if issues:
        return 1
    print(f"PASS {release['record_type']} {release['release_id']}")
    return 0


def _canonical_command(args: argparse.Namespace) -> int:
    value = load_json(Path(args.file))
    sys.stdout.buffer.write(canonical_json_bytes(value) + b"\n")
    return 0


def _stamp_command(args: argparse.Namespace) -> int:
    value = load_json(Path(args.file))
    if not isinstance(value, dict):
        print("release must be a JSON object", file=sys.stderr)
        return 2
    stamped = stamp_release(
        value, product=args.product, release_kind=args.release_kind
    )
    print(json.dumps(stamped, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate canonical Rulespec release records"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate one release")
    validate.add_argument("release")
    validate.add_argument(
        "--input",
        action="append",
        default=[],
        help="pinned input release or fixture bundle; repeat as needed",
    )
    validate.set_defaults(handler=_validate_command)

    canonical = subparsers.add_parser(
        "canonical", help="write canonical JSON bytes"
    )
    canonical.add_argument("file")
    canonical.set_defaults(handler=_canonical_command)

    stamp = subparsers.add_parser(
        "stamp", help="print a release with recomputed identity"
    )
    stamp.add_argument("file")
    stamp.add_argument("--product", required=True)
    stamp.add_argument("--release-kind", required=True)
    stamp.set_defaults(handler=_stamp_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
