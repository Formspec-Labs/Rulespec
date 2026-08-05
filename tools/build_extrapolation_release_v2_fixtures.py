#!/usr/bin/env python3
"""Build the sealed, partitioned ExtrapolationRelease v2 conformance corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

try:
    from tools.build_rulespec_release_fixtures import (
        PROFILE_ID,
        STAMP,
        _check,
        _operational_artifact,
        _reference_resource,
        _urn,
        open_vendored_atlas,
    )
    from tools.extrapolation_release_v2 import (
        FORMAT,
        FORMAT_VERSION,
        ROLE_SCHEMA_FILES,
        ROLE_SCHEMA_IDS,
        ROOT,
        ROOT_SCHEMA,
        TABLE_SCHEMA_ROOT,
        canonical_sha256,
        load_document_release_view,
        stamp_root,
        v2_selection_context_digest,
        write_canonical_json,
        write_parquet,
    )
    from tools.rulespec_release import canonical_digest, stamp_record
except ModuleNotFoundError:  # executed as ``python tools/<script>.py``
    from build_rulespec_release_fixtures import (
        PROFILE_ID,
        STAMP,
        _check,
        _operational_artifact,
        _reference_resource,
        _urn,
        open_vendored_atlas,
    )
    from extrapolation_release_v2 import (
        FORMAT,
        FORMAT_VERSION,
        ROLE_SCHEMA_FILES,
        ROLE_SCHEMA_IDS,
        ROOT,
        ROOT_SCHEMA,
        TABLE_SCHEMA_ROOT,
        canonical_sha256,
        load_document_release_view,
        stamp_root,
        v2_selection_context_digest,
        write_canonical_json,
        write_parquet,
    )
    from rulespec_release import canonical_digest, stamp_record

FIXTURE_ROOT = ROOT / "release-records" / "fixtures" / "extrapolation-release-v2"
VALID_BUNDLE = FIXTURE_ROOT / "valid"
INVALID_ROOT = FIXTURE_ROOT / "invalid"
UPSTREAM_DOCUMENT_RELEASE = (
    ROOT / "release-records" / "fixtures" / "upstream" / "spicyregs-document-release-v3"
)
CORE_FIXTURE = ROOT / "release-records" / "fixtures" / "rulespec-core-release-m2.json"
FIXTURE_STATUS = "fixture"
FIXTURE_CARRIAGE_POLICY = "spicyregs-passage-carriage-fixture-v1"
CONCEPT_ID = "urn:ref:federal-register-thesaurus:2025-04-01:concept:0570"


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _descriptor(
    path: Path,
    *,
    bundle: Path,
    role: str,
    record_count: int | None,
    schema_id: str,
) -> dict[str, Any]:
    return {
        "objectKey": path.relative_to(bundle).as_posix(),
        "role": role,
        "mediaType": (
            "application/schema+json"
            if role == "schema"
            else "application/vnd.apache.parquet"
        ),
        "byteSize": path.stat().st_size,
        "sha256": _file_digest(path),
        "recordCount": record_count,
        "schemaId": schema_id,
        "partitionId": None,
        "servingShardId": None,
    }


def _manifest(
    manifest_id: str, kind: str, scope_id: str, members: Sequence[dict]
) -> dict:
    ordered = sorted(
        (dict(member) for member in members), key=lambda item: item["objectKey"]
    )
    return {
        "format": "spicy-artifact-member-manifest",
        "formatVersion": "1.0",
        "manifestId": manifest_id,
        "scope": {"kind": kind, "id": scope_id},
        "members": ordered,
        "counts": {
            "memberCount": len(ordered),
            "totalByteSize": sum(item["byteSize"] for item in ordered),
            "totalRecordCount": sum(item["recordCount"] or 0 for item in ordered),
        },
    }


def _manifest_reference(
    path: Path, *, bundle: Path, manifest: Mapping[str, Any]
) -> dict:
    return {
        "manifestId": manifest["manifestId"],
        "scopeKind": manifest["scope"]["kind"],
        "scopeId": manifest["scope"]["id"],
        "objectKey": path.relative_to(bundle).as_posix(),
        "byteSize": path.stat().st_size,
        "sha256": _file_digest(path),
    }


def fixture_only_carriage_records(
    *,
    release_status: str,
    document_release_id: str,
    document_version_id: str,
    passage_id: str,
    passage_text: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Record one prepared upstream passage; this is not a segmenter.

    The fixture copies one publisher-emitted passage without joining, splitting,
    normalizing, or otherwise deriving source text.  The status guard prevents
    this construction helper from becoming a production release path.
    """

    if release_status != FIXTURE_STATUS:
        raise ValueError("fixture-only carriage refuses a non-fixture release")
    digest = "sha256:" + hashlib.sha256(passage_text.encode("utf-8")).hexdigest()
    segment = stamp_record(
        {
            "record_type": "ProcessingSegment",
            "document_release_ref": document_release_id,
            "input_fragment_refs": [passage_id],
            "segmentation_policy": FIXTURE_CARRIAGE_POLICY,
            "derived_text": passage_text,
            "derived_text_digest": digest,
            "projection_ref": "urn:rulespec:derived-text-projection:pending",
        }
    )
    projection = stamp_record(
        {
            "record_type": "DerivedTextProjection",
            "derived_unit_ref": segment["record_id"],
            "derived_text_digest": digest,
            "derived_coordinate_system": "unicode-code-points",
            "input_fragment_refs": [passage_id],
            "ordered_slices": [
                {
                    "derived_start": 0,
                    "derived_end": len(passage_text),
                    "slice_kind": "source_range",
                    "source_text_representation_ref": document_version_id,
                    "source_coordinate_system": "document-release-v3-passage",
                    "source_start": 0,
                    "source_end": len(passage_text),
                    "source_fragment_refs": [passage_id],
                    "context_only": False,
                    "overlap_or_truncation_flags": [],
                }
            ],
            "omitted_source_ranges": [],
            "join_delimiter": "",
            "normalization_policy": "none",
            "construction_method": FIXTURE_CARRIAGE_POLICY,
        }
    )
    # ProcessingSegment identity does not include projection_ref, so the final
    # reference can be attached without changing its stable identifier.
    segment["projection_ref"] = projection["record_id"]
    return segment, projection


def _build_assignment_graph(
    *,
    document_release: Any,
    document_id: str,
    document_version_id: str,
    passage_id: str,
    passage_text: str,
    passage_digest: str,
    core: Mapping[str, Any],
    atlas: Any,
    reference_release: Mapping[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    segment, projection = fixture_only_carriage_records(
        release_status=FIXTURE_STATUS,
        document_release_id=document_release.release_id,
        document_version_id=document_version_id,
        passage_id=passage_id,
        passage_text=passage_text,
    )
    request_digest = canonical_digest({"profile": PROFILE_ID, "version": "2"})
    activity = stamp_record(
        {
            "record_type": "ExtractionActivity",
            "extraction_run_id": "urn:rulespec:extraction-run:scale-v2-fixture-1",
            "extraction_attempt": 1,
            "extraction_method": "modelExtraction",
            "extracted_by": "urn:rulespec:extrapolator:scale-v2-fixture",
            "extractor_version": "scale-v2-fixture-1",
            "request_contract_digest": request_digest,
            "input_release_refs": [
                core["release_id"],
                document_release.release_id,
                atlas.pin()["asset_id"],
                reference_release["release_id"],
            ],
            "processing_segment_ref": segment["record_id"],
        }
    )
    lineage = stamp_record(
        {
            "record_type": "AILineage",
            "model_id": "urn:model:fixture-extractor",
            "model_version": "2.0",
            "prompt_contract_digest": request_digest,
            "input_context_digest": segment["derived_text_digest"],
            "temperature": 0,
            "seed": 11,
        }
    )
    assignment = stamp_record(
        {
            "record_type": "ConceptAssignment",
            "asserts_subject_ref": document_version_id,
            "subject_kind": "Artifact",
            "asserts_predicate": "assignmentPrimary",
            "asserts_object_ref": CONCEPT_ID,
            "assertion_polarity": "affirmed",
            "assigned_concept_release_ref": reference_release["release_id"],
            "assertion_origin": "aiSuggested",
            "usage_eligibility": "searchOnly",
            "evidence_binding_refs": [],
            "extraction_activity_ref": activity["record_id"],
            "ai_lineage_ref": lineage["record_id"],
        }
    )
    binding = stamp_record(
        {
            "record_type": "EvidenceBinding",
            "binds_assignment_ref": assignment["record_id"],
            "evidence_spans": [
                {
                    "source_fragment_ref": passage_id,
                    "selected_text_digest": passage_digest,
                }
            ],
            "evidence_role": "textualEvidence",
            "evidentiary_function": "supports",
        }
    )
    assignment["evidence_binding_refs"] = [binding["record_id"]]

    request_contract = _operational_artifact(
        "agent-validation-request-contract",
        '{"profile":"search-only-concept-extraction","protocol":"semantic-support-rubric-v2"}',
    )
    response_artifacts = [
        _operational_artifact(
            "agent-validation-response",
            '{"attempt":"scale-v2-validator-a","recommendation":"supports"}',
        ),
        _operational_artifact(
            "agent-validation-response",
            '{"attempt":"scale-v2-validator-b","recommendation":"supports"}',
        ),
    ]
    artifacts = [request_contract, *response_artifacts]
    manifest_refs = [
        assignment["record_id"],
        binding["record_id"],
        *(artifact["artifact_id"] for artifact in artifacts),
        passage_id,
        CONCEPT_ID,
    ]
    manifest_digest = canonical_digest({"record_refs": manifest_refs})
    manifest_ref = _urn(
        "rulespec", "validation-sample-manifest", {"manifest_digest": manifest_digest}
    )
    profile_digest = canonical_digest(
        {"profile_id": PROFILE_ID, "profile_version": "2", "usage_cap": "searchOnly"}
    )
    agent_receipts: list[dict[str, Any]] = []
    for attempt, group, provider, actor, response in (
        (
            "scale-v2-validator-a",
            "model-family-a",
            "fixture-provider/model-a@2",
            "urn:rulespec:validator:scale-v2-fixture-a",
            response_artifacts[0],
        ),
        (
            "scale-v2-validator-b",
            "model-family-b",
            "fixture-provider/model-b@2",
            "urn:rulespec:validator:scale-v2-fixture-b",
            response_artifacts[1],
        ),
    ):
        agent_receipts.append(
            stamp_record(
                {
                    "record_type": "AgentValidationReceipt",
                    "attempt_id": attempt,
                    "owner": "urn:rulespec:extrapolator:scale-v2-fixture",
                    "target_ref": PROFILE_ID,
                    "target_digest": profile_digest,
                    "protocol": "semantic-support-rubric-v2",
                    "input_manifest_ref": manifest_ref,
                    "input_manifest_digest": manifest_digest,
                    "validator_kind": "aiAgent",
                    "validator_actor_ref": actor,
                    "independence_group": group,
                    "provider_model_id": provider,
                    "request_contract_ref": request_contract["artifact_id"],
                    "request_contract_digest": request_contract["content_digest"],
                    "response_artifact_ref": response["artifact_id"],
                    "response_artifact_digest": response["content_digest"],
                    "execution_status": "completed",
                    "check_outcomes": [
                        _check(
                            "semantic-support",
                            "pass",
                            "The sealed passage supports the fixture assignment.",
                            [assignment["record_id"], passage_id],
                        )
                    ],
                    "overall_recommendation": "supports",
                    "started_at": STAMP,
                    "completed_at": STAMP,
                }
            )
        )
    baseline = stamp_record(
        {
            "record_type": "BaselineValidationReceipt",
            "owner": "urn:rulespec:extrapolator:scale-v2-fixture",
            "target_profile_ref": PROFILE_ID,
            "target_release_ref": reference_release["release_id"],
            "sample_manifest_ref": manifest_ref,
            "sample_manifest_digest": manifest_digest,
            "rubric": "semantic-support-rubric-v2",
            "aggregation_policy": "independent-unanimous-v1",
            "deterministic_check_receipt_refs": [],
            "deterministic_check_outcomes": [
                _check(
                    "manifest-closure",
                    "pass",
                    "Every sampled record resolves in the sealed fixture.",
                    manifest_refs,
                )
            ],
            "agent_validation_receipt_refs": [
                receipt["record_id"] for receipt in agent_receipts
            ],
            "aggregate_result": "usable_for_search",
            "disagreements_and_flags": [],
            "known_limitations": [
                "Fixture evidence does not establish approval or applicability."
            ],
            "evaluated_at": STAMP,
        }
    )
    evidence = [
        binding,
        activity,
        lineage,
        segment,
        projection,
        *artifacts,
        *agent_receipts,
        baseline,
    ]
    validation_manifest = {
        "record_refs": manifest_refs,
        "manifest_digest": manifest_digest,
    }
    return assignment, evidence, validation_manifest


def _evidence_row(record: Mapping[str, Any], assignment_id: str) -> dict[str, Any]:
    record_type = record.get("record_type", "PortableArtifact")
    record_id = (
        record.get("artifact_id")
        if record_type == "PortableArtifact"
        else record.get("record_id")
    )
    return {
        "record_id": record_id,
        "record_type": record_type,
        "assignment_id": assignment_id,
        "record_json": json.dumps(
            record,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ),
    }


def _copy_schema_members(bundle: Path) -> tuple[list[dict], list[dict]]:
    members: list[dict] = []
    descriptors: list[dict] = []
    root_schema = json.loads(ROOT_SCHEMA.read_text(encoding="utf-8"))
    root_target = bundle / "schemas" / ROOT_SCHEMA.name
    root_target.parent.mkdir(parents=True, exist_ok=True)
    root_target.write_bytes(ROOT_SCHEMA.read_bytes())
    root_schema_id = root_schema["$id"]
    members.append(
        _descriptor(
            root_target,
            bundle=bundle,
            role="schema",
            record_count=None,
            schema_id=root_schema_id,
        )
    )
    descriptors.append(
        {
            "schemaId": root_schema_id,
            "schemaVersion": "1.0",
            "schemaSha256": _file_digest(root_target),
            "roles": ["schema"],
        }
    )
    for role, filename in sorted(ROLE_SCHEMA_FILES.items()):
        source = TABLE_SCHEMA_ROOT / filename
        target = bundle / "schemas" / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        schema_id = ROLE_SCHEMA_IDS[role]
        digest = _file_digest(target)
        members.append(
            _descriptor(
                target,
                bundle=bundle,
                role="schema",
                record_count=None,
                schema_id=schema_id,
            )
        )
        descriptors.append(
            {
                "schemaId": schema_id,
                "schemaVersion": "1.0",
                "schemaSha256": digest,
                "roles": [role],
            }
        )
    return members, sorted(descriptors, key=lambda item: item["schemaId"])


def build_valid_bundle(bundle: Path, upstream_document_release: Path) -> dict[str, Any]:
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir(parents=True)
    document_release = load_document_release_view(upstream_document_release)
    core = json.loads(CORE_FIXTURE.read_text(encoding="utf-8"))
    atlas = open_vendored_atlas()
    reference_release = _reference_resource(atlas)
    core_pin = atlas.rulespec_core_pin()
    if (core_pin.release_id, core_pin.release_digest) != (
        core["release_id"],
        core["release_digest"],
    ):
        raise ValueError("the vendored atlas pins another Rulespec Core release")
    active = sorted(document_release.active_documents.items())
    if len(active) != 4:
        raise ValueError("the scale fixture requires exactly four active documents")
    disposition_names = ("assigned", "abstained", "excluded", "failed")
    disposition_by_document = {
        document_id: disposition
        for (document_id, _), disposition in zip(active, disposition_names, strict=True)
    }
    assigned_document_id, assigned_version_id = active[0]
    candidate_passages = sorted(
        (
            passage_id,
            record,
            document_release.passages[passage_id],
        )
        for passage_id, record in document_release.passage_records.items()
        if record.get("document_id") == assigned_document_id
    )
    if not candidate_passages:
        raise ValueError("assigned fixture document has no passage")
    passage_id, passage_record, (_, _, passage_digest) = candidate_passages[0]
    passage_text = passage_record.get("text")
    if not isinstance(passage_text, str):
        raise ValueError("fixture passage has no text")
    assignment, evidence, validation_manifest = _build_assignment_graph(
        document_release=document_release,
        document_id=assigned_document_id,
        document_version_id=assigned_version_id,
        passage_id=passage_id,
        passage_text=passage_text,
        passage_digest=passage_digest,
        core=core,
        atlas=atlas,
        reference_release=reference_release,
    )
    assignment_policy_source = {
        "policyId": "urn:rulespec:fixture:assignment-policy:scale-v2",
        "emissionPolicyId": "urn:platform:unowned:emission-policy:fixture-v1",
        "candidateMethodId": "urn:rulespec:fixture:candidate-method:known-concept-v1",
        "qualificationProtocolId": "urn:rulespec:fixture:qualification:two-validator-v1",
    }
    assignment_policy = {
        **assignment_policy_source,
        "policySha256": canonical_sha256(assignment_policy_source),
    }
    assignment_row = {
        "document_id": assigned_document_id,
        "document_version_id": assigned_version_id,
        "assignment_id": assignment["record_id"],
        "subject_ref": assignment["asserts_subject_ref"],
        "subject_kind": assignment["subject_kind"],
        "predicate": assignment["asserts_predicate"],
        "concept_id": assignment["asserts_object_ref"],
        "polarity": assignment["assertion_polarity"],
        "assigned_concept_release_id": assignment["assigned_concept_release_ref"],
        "origin": assignment["assertion_origin"],
        "usage_eligibility": assignment["usage_eligibility"],
        "evidence_binding_refs": assignment["evidence_binding_refs"],
        "extraction_activity_id": assignment["extraction_activity_ref"],
        "ai_lineage_id": assignment["ai_lineage_ref"],
        "selection_result": "selected",
        "confidence": 0.91,
    }
    profile = {
        "profile_id": PROFILE_ID,
        "profile_version": "2",
        "usage_cap": "searchOnly",
    }
    input_releases = {
        "rulespec_core_release": {
            "release_id": core["release_id"],
            "release_digest": core["release_digest"],
        },
        "document_release": document_release.v1_pin,
        "vocabulary_atlas_asset": dict(atlas.pin()),
        "reference_resource_release": dict(reference_release),
    }
    producer = {
        "product": "rulespec-extrapolator",
        "implementationId": "rulespec-reference-fixture-builder",
        "implementationVersion": "2.0-fixture",
        "sourceRevision": None,
        "runtimeProfileId": "local-fixture",
    }
    content_for_context = {
        "profile": profile,
        "input_releases": input_releases,
        "assignmentPolicy": assignment_policy,
        "validation_sample_manifest": validation_manifest,
    }
    evidence_rows = [
        _evidence_row(record, assignment["record_id"]) for record in evidence
    ]
    provisional_context = v2_selection_context_digest(
        content_for_context, [assignment_row], evidence_rows
    )
    baseline = next(
        record
        for record in evidence
        if record.get("record_type") == "BaselineValidationReceipt"
    )
    selection = stamp_record(
        {
            "record_type": "ExtrapolationSelectionReceipt",
            "assignment_ref": assignment["record_id"],
            "selection_policy": assignment_policy["policyId"],
            "selection_context_digest": provisional_context,
            "input_record_refs": [
                assignment["record_id"],
                assignment["evidence_binding_refs"][0],
                assignment["extraction_activity_ref"],
                assignment["ai_lineage_ref"],
                baseline["record_id"],
            ],
            "checks": [
                _check(
                    "candidate-policy",
                    "pass",
                    "The fixture candidate satisfies the sealed fixture policy.",
                    [assignment["record_id"]],
                )
            ],
            "selection_result": "selected",
            "reason": "sealed v2 fixture selection",
            "baseline_validation_receipt_ref": baseline["record_id"],
            "evaluator_ref": "urn:platform:unowned:selection-evaluator:fixture-v1",
            "evaluator_version": "fixture-v1",
            "evaluated_at": STAMP,
            "effective_as_of": STAMP,
        }
    )
    evidence_rows.append(_evidence_row(selection, assignment["record_id"]))
    # Selection receipts are excluded from the context preimage, so this value
    # remains stable after the receipt is added.
    selection_context_digest = v2_selection_context_digest(
        content_for_context, [assignment_row], evidence_rows
    )
    if selection_context_digest != provisional_context:
        raise AssertionError("selection context changed after adding its receipt")

    rows_by_partition: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for index, (document_id, version_id) in enumerate(active):
        partition_id = f"{index:04d}"
        disposition = disposition_by_document[document_id]
        if disposition == "assigned":
            rows_by_partition[partition_id]["assignments"].append(assignment_row)
            rows_by_partition[partition_id]["assignment-evidence"].extend(evidence_rows)
        rows_by_partition[partition_id]["assignment-dispositions"].append(
            {
                "document_id": document_id,
                "document_version_id": version_id,
                "disposition": disposition,
                "reason_code": f"fixture.assignment.{disposition}",
                "assignment_count": 1 if disposition == "assigned" else 0,
                "selected_assignment_count": 1 if disposition == "assigned" else 0,
                "evidence_record_count": len(evidence_rows)
                if disposition == "assigned"
                else 0,
                "failure_id": (
                    "urn:rulespec:assignment-failure:fixture-terminal"
                    if disposition == "failed"
                    else None
                ),
            }
        )

    global_members, schema_descriptors = _copy_schema_members(bundle)
    partition_references: list[dict[str, Any]] = []
    for partition_id, role_rows in sorted(rows_by_partition.items()):
        members: list[dict[str, Any]] = []
        for role, rows in sorted(role_rows.items()):
            path = bundle / "data" / f"partition-{partition_id}" / f"{role}.parquet"
            write_parquet(path, role, rows)
            members.append(
                _descriptor(
                    path,
                    bundle=bundle,
                    role=role,
                    record_count=len(rows),
                    schema_id=ROLE_SCHEMA_IDS[role],
                )
            )
        manifest = _manifest(
            f"partition:{partition_id}", "partition", partition_id, members
        )
        path = bundle / "manifests" / f"partition-{partition_id}.json"
        write_canonical_json(path, manifest)
        partition_references.append(
            _manifest_reference(path, bundle=bundle, manifest=manifest)
        )

    coverage_rows = [
        {
            "scope_kind": "global",
            "scope_id": "global",
            "active_document_count": 4,
            "assigned_document_count": 1,
            "abstained_document_count": 1,
            "excluded_document_count": 1,
            "failed_document_count": 1,
            "candidate_assignment_count": 1,
            "selected_assignment_count": 1,
            "not_selected_assignment_count": 0,
            "deferred_assignment_count": 0,
        }
    ]
    coverage_path = bundle / "data" / "coverage.parquet"
    write_parquet(coverage_path, "coverage", coverage_rows)
    global_members.append(
        _descriptor(
            coverage_path,
            bundle=bundle,
            role="coverage",
            record_count=1,
            schema_id=ROLE_SCHEMA_IDS["coverage"],
        )
    )
    build_receipt_rows = [
        {
            "receipt_id": "urn:rulespec:extrapolation-build-receipt:scale-v2-fixture",
            "producer_id": producer["implementationId"],
            "producer_version": producer["implementationVersion"],
            "started_at": STAMP,
            "completed_at": STAMP,
            "release_status": FIXTURE_STATUS,
            "input_document_release_id": document_release.release_id,
            "assignment_policy_id": assignment_policy["policyId"],
            "record_count": 1 + len(evidence_rows) + 4 + 1,
        }
    ]
    receipt_path = bundle / "receipts" / "build.parquet"
    write_parquet(receipt_path, "build-receipt", build_receipt_rows)
    global_members.append(
        _descriptor(
            receipt_path,
            bundle=bundle,
            role="build-receipt",
            record_count=1,
            schema_id=ROLE_SCHEMA_IDS["build-receipt"],
        )
    )
    global_manifest = _manifest("global:global", "global", "global", global_members)
    global_path = bundle / "manifests" / "global.json"
    write_canonical_json(global_path, global_manifest)
    global_reference = _manifest_reference(
        global_path, bundle=bundle, manifest=global_manifest
    )
    all_members = [
        *global_members,
        *(
            member
            for partition_id, role_rows in sorted(rows_by_partition.items())
            for role, rows in sorted(role_rows.items())
            for member in [
                _descriptor(
                    bundle / "data" / f"partition-{partition_id}" / f"{role}.parquet",
                    bundle=bundle,
                    role=role,
                    record_count=len(rows),
                    schema_id=ROLE_SCHEMA_IDS[role],
                )
            ]
        ),
    ]
    counts = {
        "activeDocumentCount": 4,
        "assignedDocumentCount": 1,
        "abstainedDocumentCount": 1,
        "excludedDocumentCount": 1,
        "failedDocumentCount": 1,
        "assignmentCount": 1,
        "assignmentEvidenceCount": len(evidence_rows),
        "coverageRecordCount": 1,
        "buildReceiptCount": 1,
        "partitionManifestCount": 4,
        "memberCount": len(all_members),
        "totalMemberByteSize": sum(member["byteSize"] for member in all_members),
    }
    content = {
        "schemaSet": {
            "schemaSetId": f"urn:spicy:schema-set:v1:{canonical_sha256(schema_descriptors)}",
            "schemas": schema_descriptors,
        },
        "profile": profile,
        "input_releases": input_releases,
        "assignmentPolicy": assignment_policy,
        "validation_sample_manifest": validation_manifest,
        "selection_context_digest": selection_context_digest,
        "producer": producer,
        "globalManifest": global_reference,
        "partitionManifests": sorted(
            partition_references, key=lambda item: item["manifestId"]
        ),
        "counts": counts,
    }
    root = stamp_root(
        {
            "format": FORMAT,
            "formatVersion": FORMAT_VERSION,
            "content": content,
            "annotations": {
                "createdAt": STAMP,
                "buildRunId": "scale-v2-conformance-fixture",
                "releaseStatus": FIXTURE_STATUS,
                "emissionPolicyOwner": "unassigned",
            },
        }
    )
    write_canonical_json(bundle / "release.json", root)
    return root


def vendor_document_release(
    source: Path, target: Path = UPSTREAM_DOCUMENT_RELEASE
) -> None:
    """Copy one publisher-owned v3 distribution byte for byte."""

    load_document_release_view(source)
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, symlinks=True)
    load_document_release_view(target)


def _load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def _all_manifest_paths(bundle: Path) -> list[Path]:
    root = _load_json_object(bundle / "release.json")
    content = root["content"]
    references = [content["globalManifest"], *content["partitionManifests"]]
    return [bundle / reference["objectKey"] for reference in references]


def _descriptor_for_role(bundle: Path, role: str) -> tuple[Path, dict[str, Any]]:
    for manifest_path in _all_manifest_paths(bundle):
        manifest = _load_json_object(manifest_path)
        for descriptor in manifest["members"]:
            if descriptor["role"] == role:
                return manifest_path, descriptor
    raise ValueError(f"bundle has no {role!r} member")


def _rewrite_role_rows(
    bundle: Path, role: str, rows: Sequence[Mapping[str, Any]]
) -> None:
    _, descriptor = _descriptor_for_role(bundle, role)
    write_parquet(bundle / descriptor["objectKey"], role, rows)


def _read_role_rows(bundle: Path, role: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for manifest_path in _all_manifest_paths(bundle):
        manifest = _load_json_object(manifest_path)
        for descriptor in manifest["members"]:
            if descriptor["role"] == role:
                rows.extend(pq.read_table(bundle / descriptor["objectKey"]).to_pylist())
    return rows


def _reseal_bundle(bundle: Path) -> None:
    """Refresh member, manifest, rollup, and root identities after a fixture mutation."""

    root_path = bundle / "release.json"
    root = _load_json_object(root_path)
    content = root["content"]
    references = [content["globalManifest"], *content["partitionManifests"]]
    members: list[dict[str, Any]] = []
    for reference in references:
        manifest_path = bundle / reference["objectKey"]
        manifest = _load_json_object(manifest_path)
        for descriptor in manifest["members"]:
            member_path = bundle / descriptor["objectKey"]
            descriptor["byteSize"] = member_path.stat().st_size
            descriptor["sha256"] = _file_digest(member_path)
            if descriptor["role"] != "schema":
                descriptor["recordCount"] = pq.read_table(member_path).num_rows
        manifest["members"] = sorted(
            manifest["members"], key=lambda item: item["objectKey"]
        )
        manifest["counts"] = {
            "memberCount": len(manifest["members"]),
            "totalByteSize": sum(item["byteSize"] for item in manifest["members"]),
            "totalRecordCount": sum(
                item["recordCount"] or 0 for item in manifest["members"]
            ),
        }
        write_canonical_json(manifest_path, manifest)
        reference["byteSize"] = manifest_path.stat().st_size
        reference["sha256"] = _file_digest(manifest_path)
        members.extend(manifest["members"])
    disposition_rows = _read_role_rows(bundle, "assignment-dispositions")
    disposition_counts = defaultdict(int)
    for row in disposition_rows:
        disposition_counts[row["disposition"]] += 1
    counts = content["counts"]
    counts.update(
        {
            "activeDocumentCount": len(disposition_rows),
            "assignedDocumentCount": disposition_counts["assigned"],
            "abstainedDocumentCount": disposition_counts["abstained"],
            "excludedDocumentCount": disposition_counts["excluded"],
            "failedDocumentCount": disposition_counts["failed"],
            "assignmentCount": len(_read_role_rows(bundle, "assignments")),
            "assignmentEvidenceCount": len(
                _read_role_rows(bundle, "assignment-evidence")
            ),
            "coverageRecordCount": len(_read_role_rows(bundle, "coverage")),
            "buildReceiptCount": len(_read_role_rows(bundle, "build-receipt")),
            "partitionManifestCount": len(content["partitionManifests"]),
            "memberCount": len(members),
            "totalMemberByteSize": sum(member["byteSize"] for member in members),
        }
    )
    write_canonical_json(root_path, stamp_root(root))


def _tree_digest(bundle: Path) -> str:
    inventory = []
    for path in sorted(bundle.rglob("*")):
        if path.is_symlink():
            inventory.append(
                {
                    "objectKey": path.relative_to(bundle).as_posix(),
                    "symlinkTarget": str(path.readlink()),
                }
            )
        elif path.is_file():
            inventory.append(
                {
                    "objectKey": path.relative_to(bundle).as_posix(),
                    "byteSize": path.stat().st_size,
                    "sha256": _file_digest(path),
                }
            )
    return canonical_sha256(inventory)


def build_invalid_bundles(
    valid_bundle: Path, invalid_root: Path
) -> list[dict[str, Any]]:
    """Build sealed negative controls with one intended first core code each."""

    if invalid_root.exists():
        shutil.rmtree(invalid_root)
    invalid_root.mkdir(parents=True)
    cases: list[dict[str, Any]] = []

    def copy_case(name: str) -> Path:
        target = invalid_root / name
        shutil.copytree(valid_bundle, target)
        return target

    def record(name: str, code: str, bundle: Path) -> None:
        cases.append(
            {
                "name": name,
                "expectedCode": code,
                "bundle": f"invalid/{name}",
                "treeSha256": _tree_digest(bundle),
            }
        )

    bundle = copy_case("unknown-version")
    root = _load_json_object(bundle / "release.json")
    root["formatVersion"] = "2.1"
    write_canonical_json(bundle / "release.json", stamp_root(root))
    record("unknown-version", "invalid.format", bundle)

    bundle = copy_case("wrong-identity")
    root = _load_json_object(bundle / "release.json")
    root["releaseId"] = "urn:rulespec:extrapolation:v2:" + "0" * 64
    write_canonical_json(bundle / "release.json", root)
    record("wrong-identity", "invalid.identity", bundle)

    bundle = copy_case("missing-member")
    _, descriptor = _descriptor_for_role(bundle, "assignments")
    (bundle / descriptor["objectKey"]).unlink()
    record("missing-member", "invalid.membership-missing", bundle)

    bundle = copy_case("extra-member")
    (bundle / "undeclared.bin").write_bytes(b"undeclared fixture control")
    record("extra-member", "invalid.membership-extra", bundle)

    bundle = copy_case("member-digest")
    _, descriptor = _descriptor_for_role(bundle, "assignments")
    path = bundle / descriptor["objectKey"]
    path.write_bytes(path.read_bytes() + b"changed")
    record("member-digest", "invalid.member-digest", bundle)

    bundle = copy_case("unsafe-path")
    manifest_path, descriptor = _descriptor_for_role(bundle, "assignments")
    original_path = bundle / descriptor["objectKey"]
    unsafe_key = (
        original_path.with_name("assignments\\unsafe.parquet")
        .relative_to(bundle)
        .as_posix()
    )
    unsafe_path = bundle / unsafe_key
    original_path.rename(unsafe_path)
    manifest = _load_json_object(manifest_path)
    for item in manifest["members"]:
        if item["objectKey"] == descriptor["objectKey"]:
            item["objectKey"] = unsafe_key
    write_canonical_json(manifest_path, manifest)
    _reseal_bundle(bundle)
    record("unsafe-path", "invalid.path", bundle)

    bundle = copy_case("symlink-member")
    _, descriptor = _descriptor_for_role(bundle, "assignments")
    path = bundle / descriptor["objectKey"]
    valid_target = VALID_BUNDLE / descriptor["objectKey"]
    path.unlink()
    path.symlink_to(os.path.relpath(valid_target, start=path.parent))
    record("symlink-member", "invalid.path", bundle)

    bundle = copy_case("unknown-role")
    manifest_path, descriptor = _descriptor_for_role(bundle, "assignments")
    manifest = _load_json_object(manifest_path)
    for item in manifest["members"]:
        if item["objectKey"] == descriptor["objectKey"]:
            item["role"] = "unknown-assignment-role"
    write_canonical_json(manifest_path, manifest)
    root = _load_json_object(bundle / "release.json")
    for reference in root["content"]["partitionManifests"]:
        if reference["objectKey"] == manifest_path.relative_to(bundle).as_posix():
            reference["byteSize"] = manifest_path.stat().st_size
            reference["sha256"] = _file_digest(manifest_path)
    write_canonical_json(bundle / "release.json", stamp_root(root))
    record("unknown-role", "invalid.schema", bundle)

    bundle = copy_case("duplicate-assignment")
    rows = _read_role_rows(bundle, "assignments")
    _rewrite_role_rows(bundle, "assignments", [*rows, copy.deepcopy(rows[0])])
    _reseal_bundle(bundle)
    record("duplicate-assignment", "invalid.duplicate-identity", bundle)

    bundle = copy_case("duplicate-disposition")
    rows = _read_role_rows(bundle, "assignment-dispositions")
    assigned = next(row for row in rows if row["disposition"] == "assigned")
    _rewrite_role_rows(
        bundle,
        "assignment-dispositions",
        [copy.deepcopy(assigned), copy.deepcopy(assigned)],
    )
    _reseal_bundle(bundle)
    record("duplicate-disposition", "invalid.duplicate-identity", bundle)

    bundle = copy_case("foreign-evidence")
    rows = _read_role_rows(bundle, "assignment-evidence")
    binding = next(row for row in rows if row["record_type"] == "EvidenceBinding")
    payload = json.loads(binding["record_json"])
    payload["binds_assignment_ref"] = "urn:rulespec:concept-assignment:" + "f" * 64
    binding["record_json"] = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    _rewrite_role_rows(bundle, "assignment-evidence", rows)
    _reseal_bundle(bundle)
    record("foreign-evidence", "invalid.assignment-evidence", bundle)

    bundle = copy_case("broken-coordinate")
    rows = _read_role_rows(bundle, "assignment-evidence")
    projection_row = next(
        row for row in rows if row["record_type"] == "DerivedTextProjection"
    )
    projection = json.loads(projection_row["record_json"])
    projection["ordered_slices"][0]["source_end"] -= 1
    projection_row["record_json"] = json.dumps(
        projection,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    _rewrite_role_rows(bundle, "assignment-evidence", rows)
    _reseal_bundle(bundle)
    record("broken-coordinate", "invalid.coordinate", bundle)

    bundle = copy_case("disposition-gap")
    rows = _read_role_rows(bundle, "assignment-dispositions")
    rows = [row for row in rows if row["disposition"] != "abstained"]
    # The abstained row lives in its own partition member.
    manifest_path, descriptor = next(
        (manifest_path, descriptor)
        for manifest_path in _all_manifest_paths(bundle)
        for descriptor in _load_json_object(manifest_path)["members"]
        if descriptor["role"] == "assignment-dispositions"
        and pq.read_table(bundle / descriptor["objectKey"]).to_pylist()[0][
            "disposition"
        ]
        == "abstained"
    )
    write_parquet(bundle / descriptor["objectKey"], "assignment-dispositions", [])
    coverage = _read_role_rows(bundle, "coverage")
    coverage[0]["active_document_count"] = 4
    coverage[0]["abstained_document_count"] = 0
    _rewrite_role_rows(bundle, "coverage", coverage)
    receipts = _read_role_rows(bundle, "build-receipt")
    receipts[0]["record_count"] -= 1
    _rewrite_role_rows(bundle, "build-receipt", receipts)
    _reseal_bundle(bundle)
    record("disposition-gap", "invalid.assignment-disposition", bundle)

    bundle = copy_case("assignment-pin")
    root = _load_json_object(bundle / "release.json")
    root["content"]["input_releases"]["document_release"]["release_digest"] = (
        "sha256:" + "0" * 64
    )
    write_canonical_json(bundle / "release.json", stamp_root(root))
    record("assignment-pin", "invalid.assignment-pin", bundle)
    return cases


def write_corpus() -> dict[str, Any]:
    cases = [
        {
            "name": "valid",
            "expectedCode": "valid",
            "bundle": "valid",
            "treeSha256": _tree_digest(VALID_BUNDLE),
        },
        *build_invalid_bundles(VALID_BUNDLE, INVALID_ROOT),
    ]
    corpus = {
        "format": "rulespec-extrapolation-release-v2-conformance",
        "formatVersion": "1.0",
        "inputDocumentRelease": UPSTREAM_DOCUMENT_RELEASE.relative_to(ROOT).as_posix(),
        "inputVocabularyAtlas": (
            ROOT
            / "release-records"
            / "fixtures"
            / "upstream"
            / "refspec-vocabulary-atlas"
        )
        .relative_to(ROOT)
        .as_posix(),
        "cases": cases,
    }
    write_canonical_json(FIXTURE_ROOT / "corpus.json", corpus)
    return corpus


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document-release", type=Path)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if args.document_release is not None:
        vendor_document_release(args.document_release)
    if not UPSTREAM_DOCUMENT_RELEASE.exists():
        parser.error("vendor a DocumentRelease v3 with --document-release first")
    if args.write:
        root = build_valid_bundle(VALID_BUNDLE, UPSTREAM_DOCUMENT_RELEASE)
        write_corpus()
    else:
        if not (VALID_BUNDLE / "release.json").is_file():
            parser.error("build the checked fixture with --write first")
        root = json.loads((VALID_BUNDLE / "release.json").read_text(encoding="utf-8"))
    print(json.dumps(root, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
