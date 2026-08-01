#!/usr/bin/env python3
"""Print deterministic M2 Rulespec release fixtures.

This development helper contains no imports from SpicyRegs or RefSpec. It
builds repository-independent JSON records from fixed values and the sealed
Rulespec Core fixture. Static copies live under ``release-records/fixtures``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from rulespec_release import (
        canonical_digest,
        extrapolation_selection_context_digest,
        load_json,
        stamp_record,
        stamp_coverage,
        stamp_release,
        text_digest,
    )
except ModuleNotFoundError:  # imported as tools.build_rulespec_release_fixtures
    from tools.rulespec_release import (
        canonical_digest,
        extrapolation_selection_context_digest,
        load_json,
        stamp_record,
        stamp_coverage,
        stamp_release,
        text_digest,
    )


ROOT = Path(__file__).resolve().parents[1]
CORE_FIXTURE = ROOT / "release-records/fixtures/rulespec-core-release-m2.json"
UPSTREAM_FIXTURES = ROOT / "release-records/fixtures/upstream"
DOCUMENT_FIXTURE = UPSTREAM_FIXTURES / "spicyregs-document-release-v1.json"
VOCABULARY_FIXTURE = UPSTREAM_FIXTURES / "refspec-vocabulary-release-first-slice.json"
STAMP = "2026-07-31T12:00:00Z"
PROFILE_ID = "urn:rulespec:profile:search-only-concept-extraction"
CONCEPT_ID = (
    "urn:refspec:vocabulary:federal-register-thesaurus:2025-04-01:concept:0570"
)


def _urn(product: str, kind: str, identity: Mapping[str, Any]) -> str:
    digest = canonical_digest(identity).removeprefix("sha256:")
    return f"urn:{product}:{kind}:{digest}"


def build_inputs(core: Mapping[str, Any]) -> dict[str, Any]:
    core_pin = {
        "release_id": core["release_id"],
        "release_digest": core["release_digest"],
    }
    document = load_json(DOCUMENT_FIXTURE)
    vocabulary = load_json(VOCABULARY_FIXTURE)
    for name, release in (("document", document), ("vocabulary", vocabulary)):
        if not isinstance(release, dict):
            raise ValueError(f"vendored {name} release must be a JSON object")
        if release.get("rulespec_core_release") != core_pin:
            raise ValueError(f"vendored {name} release pins another Core release")
    return {"fixture_type": "PinnedReleaseBundle", "records": [document, vocabulary]}


def _check(check_id: str, outcome: str, rationale: str, refs: list[str]) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "outcome": outcome,
        "rationale": rationale,
        "evidence_refs": refs,
    }


def _operational_artifact(artifact_type: str, content: str) -> dict[str, Any]:
    digest = text_digest(content)
    identity = {
        "artifact_type": artifact_type,
        "content_digest": digest,
        "media_type": "application/json",
        "coordinate_system": "not-applicable",
    }
    return {
        "artifact_id": _urn("rulespec", "artifact", identity),
        **identity,
        "evidence_grade": "sealed-operational-fixture",
    }


def _document_inputs(
    document: Mapping[str, Any],
) -> tuple[
    Mapping[str, Any],
    Mapping[str, Any],
    Mapping[str, Any],
    Mapping[str, Any],
]:
    version = next(
        value
        for value in document["document_versions"]
        if value.get("source_issued_version_id") == "2026-03227"
    )
    document_artifact = version["artifact_projection"]
    representation = next(
        value
        for value in document["text_representations"]
        if value.get("document_version_ref") == version["document_version_id"]
        and value.get("representation_kind_and_path") == "source-record-field:body_html"
    )
    source_text = representation["unicode_text"]
    passages = {
        source_text[value["start"] : value["end"]]: value
        for value in document["structural_passages"]
        if value.get("document_version_ref") == version["document_version_id"]
    }
    first = passages["Worker safety attestations document hazards."]
    second = passages["Workers receive protections."]
    return (
        document_artifact,
        representation,
        first["source_fragment_projection"],
        second["source_fragment_projection"],
    )


def _reference_resource(vocabulary: Mapping[str, Any]) -> dict[str, Any]:
    graph = vocabulary["reference_resource_release"]["@graph"]
    node = next(
        value
        for value in graph
        if value.get("@type") == "rkaf:ReferenceResourceRelease"
    )
    if node.get("rkaf:membershipMode") != "rkaf:completeMembership":
        raise ValueError("vendored reference release must publish complete membership")
    members = set(node.get("prov:hadMember", []))
    concepts = {value["concept_id"] for value in vocabulary["concepts"]}
    if members != concepts or CONCEPT_ID not in members:
        raise ValueError("vendored Safety concept must be in the complete release")
    return {
        "release_id": node["@id"],
        "release_digest": node["rkaf:referenceReleaseDigest"],
        "membership_mode": "complete",
        "concepts": vocabulary["concepts"],
    }


def build_extrapolation(
    core: Mapping[str, Any], inputs: Mapping[str, Any]
) -> dict[str, Any]:
    document, vocabulary = inputs["records"]
    reference_resource = _reference_resource(vocabulary)
    document_artifact, representation, first_fragment, second_fragment = (
        _document_inputs(document)
    )

    source_text = representation["unicode_text"]
    first_selector = first_fragment["selector"]
    second_selector = second_fragment["selector"]
    first_text = source_text[first_selector["start"] : first_selector["end"]]
    second_text = source_text[second_selector["start"] : second_selector["end"]]
    derived_text = first_text + "\n" + second_text
    segment = stamp_record(
        {
            "record_type": "ProcessingSegment",
            "document_release_ref": document["release_id"],
            "input_fragment_refs": [
                first_fragment["fragment_id"],
                second_fragment["fragment_id"],
            ],
            "segmentation_policy": "join-structural-passages-v1",
            "derived_text": derived_text,
            "derived_text_digest": text_digest(derived_text),
            "projection_ref": "urn:rulespec:pending-derived-text-projection",
        }
    )
    projection = stamp_record(
        {
            "record_type": "DerivedTextProjection",
            "derived_unit_ref": segment["record_id"],
            "derived_text_digest": segment["derived_text_digest"],
            "derived_coordinate_system": "unicode-code-points",
            "input_fragment_refs": segment["input_fragment_refs"],
            "ordered_slices": [
                {
                    "derived_start": 0,
                    "derived_end": 44,
                    "slice_kind": "source_range",
                    "source_text_representation_ref": representation["representation_id"],
                    "source_coordinate_system": representation["coordinate_system"],
                    "source_start": first_selector["start"],
                    "source_end": first_selector["end"],
                    "source_fragment_refs": [first_fragment["fragment_id"]],
                    "context_only": False,
                    "overlap_or_truncation_flags": [],
                },
                {
                    "derived_start": 44,
                    "derived_end": 45,
                    "slice_kind": "inserted_text",
                    "inserted_text": "\n",
                    "inserted_text_digest": text_digest("\n"),
                    "context_only": True,
                    "overlap_or_truncation_flags": [],
                },
                {
                    "derived_start": 45,
                    "derived_end": 73,
                    "slice_kind": "source_range",
                    "source_text_representation_ref": representation["representation_id"],
                    "source_coordinate_system": representation["coordinate_system"],
                    "source_start": second_selector["start"],
                    "source_end": second_selector["end"],
                    "source_fragment_refs": [second_fragment["fragment_id"]],
                    "context_only": False,
                    "overlap_or_truncation_flags": [],
                },
            ],
            "omitted_source_ranges": [
                {
                    "source_text_representation_ref": representation["representation_id"],
                    "source_start": first_selector["end"],
                    "source_end": second_selector["start"],
                    "reason": "source separator replaced by declared join delimiter",
                }
            ],
            "join_delimiter": "\n",
            "normalization_policy": "none",
            "construction_method": "join-structural-passages-v1",
        }
    )
    segment["projection_ref"] = projection["record_id"]

    activity = stamp_record(
        {
            "record_type": "ExtractionActivity",
            "extraction_run_id": "urn:rulespec:extraction-run:m2-fixture-1",
            "extraction_attempt": 1,
            "extraction_method": "modelExtraction",
            "extracted_by": "urn:rulespec:extrapolator:m2-fixture",
            "extractor_version": "m2-fixture-1",
            "request_contract_digest": canonical_digest(
                {"profile": PROFILE_ID, "version": "1"}
            ),
            "input_release_refs": [
                core["release_id"],
                document["release_id"],
                vocabulary["release_id"],
            ],
            "processing_segment_ref": segment["record_id"],
        }
    )
    lineage = stamp_record(
        {
            "record_type": "AILineage",
            "model_id": "urn:model:fixture-extractor",
            "model_version": "1.0",
            "prompt_contract_digest": activity["request_contract_digest"],
            "input_context_digest": segment["derived_text_digest"],
            "temperature": 0,
            "seed": 7,
        }
    )

    assignment_specs = [
        (document_artifact["artifact_id"], "Artifact", "assignmentPrimary", first_fragment),
        (first_fragment["fragment_id"], "SourceFragment", "assignmentSubstantive", first_fragment),
        (second_fragment["fragment_id"], "SourceFragment", "assignmentMention", second_fragment),
    ]
    assignments: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for subject_ref, subject_kind, predicate, evidence_fragment in assignment_specs:
        assignment = stamp_record(
            {
                "record_type": "ConceptAssignment",
                "asserts_subject_ref": subject_ref,
                "subject_kind": subject_kind,
                "asserts_predicate": predicate,
                "asserts_object_ref": CONCEPT_ID,
                "assertion_polarity": "affirmed",
                "assigned_concept_release_ref": reference_resource["release_id"],
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
                        "source_fragment_ref": evidence_fragment["fragment_id"],
                        "selected_text_digest": evidence_fragment["selected_text_digest"],
                    }
                ],
                "evidence_role": "textualEvidence",
                "evidentiary_function": "supports",
            }
        )
        assignment["evidence_binding_refs"] = [binding["record_id"]]
        assignments.append(assignment)
        bindings.append(binding)

    request_contract = _operational_artifact(
        "agent-validation-request-contract",
        '{"profile":"search-only-concept-extraction","protocol":"semantic-support-rubric-v1"}',
    )
    response_artifacts = [
        _operational_artifact(
            "agent-validation-response",
            '{"attempt":"m2-validator-a","recommendation":"supports"}',
        ),
        _operational_artifact(
            "agent-validation-response",
            '{"attempt":"m2-validator-b","recommendation":"supports"}',
        ),
    ]
    validation_artifacts = [request_contract, *response_artifacts]
    manifest_refs = [
        *(assignment["record_id"] for assignment in assignments),
        *(binding["record_id"] for binding in bindings),
        *(artifact["artifact_id"] for artifact in validation_artifacts),
        first_fragment["fragment_id"],
        second_fragment["fragment_id"],
        CONCEPT_ID,
    ]
    manifest_digest = canonical_digest({"record_refs": manifest_refs})
    manifest_ref = _urn(
        "rulespec", "validation-sample-manifest", {"manifest_digest": manifest_digest}
    )
    profile_digest = canonical_digest(
        {
            "profile_id": PROFILE_ID,
            "profile_version": "1",
            "usage_cap": "searchOnly",
        }
    )
    agent_receipts = []
    for attempt, group, provider_model, actor_ref, response_artifact in (
        (
            "m2-validator-a",
            "model-family-a",
            "fixture-provider/model-a@1",
            "urn:rulespec:validator:m2-fixture-a",
            response_artifacts[0],
        ),
        (
            "m2-validator-b",
            "model-family-b",
            "fixture-provider/model-b@1",
            "urn:rulespec:validator:m2-fixture-b",
            response_artifacts[1],
        ),
    ):
        agent_receipts.append(
            stamp_record(
                {
                    "record_type": "AgentValidationReceipt",
                    "attempt_id": attempt,
                    "owner": "urn:rulespec:extrapolator:m2-fixture",
                    "target_ref": PROFILE_ID,
                    "target_digest": profile_digest,
                    "protocol": "semantic-support-rubric-v1",
                    "input_manifest_ref": manifest_ref,
                    "input_manifest_digest": manifest_digest,
                    "validator_kind": "aiAgent",
                    "validator_actor_ref": actor_ref,
                    "independence_group": group,
                    "provider_model_id": provider_model,
                    "request_contract_ref": request_contract["artifact_id"],
                    "request_contract_digest": request_contract["content_digest"],
                    "response_artifact_ref": response_artifact["artifact_id"],
                    "response_artifact_digest": response_artifact["content_digest"],
                    "execution_status": "completed",
                    "check_outcomes": [
                        _check(
                            "semantic-support",
                            "pass",
                            "The sealed passages support the candidate assignments.",
                            [assignments[0]["record_id"], first_fragment["fragment_id"]],
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
            "owner": "urn:rulespec:extrapolator:m2-fixture",
            "target_profile_ref": PROFILE_ID,
            "target_release_ref": vocabulary["release_id"],
            "sample_manifest_ref": manifest_ref,
            "sample_manifest_digest": manifest_digest,
            "rubric": "semantic-support-rubric-v1",
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
            "known_limitations": ["Fixture evidence does not support an adoption claim."],
            "evaluated_at": STAMP,
        }
    )
    profile = {
        "profile_id": PROFILE_ID,
        "profile_version": "1",
        "usage_cap": "searchOnly",
    }
    input_releases = {
        "rulespec_core_release": {
            "release_id": core["release_id"],
            "release_digest": core["release_digest"],
        },
        "document_release": {
            "release_id": document["release_id"],
            "release_digest": document["release_digest"],
        },
        "vocabulary_release": {
            "release_id": vocabulary["release_id"],
            "release_digest": vocabulary["release_digest"],
        },
    }
    validation_sample_manifest = {
        "record_refs": manifest_refs,
        "manifest_digest": manifest_digest,
    }
    selection_context_source = {
        "input_releases": input_releases,
        "profile": profile,
        "validation_sample_manifest": validation_sample_manifest,
        "concept_assignments": assignments,
        "evidence_bindings": bindings,
        "extraction_activities": [activity],
        "ai_lineage_records": [lineage],
        "processing_segments": [segment],
        "derived_text_projections": [projection],
        "validation_artifacts": validation_artifacts,
        "agent_validation_receipts": agent_receipts,
        "baseline_validation_receipts": [baseline],
        "selection_receipts": [
            {"selection_policy": "m2-search-only-selection-v1"}
        ],
    }
    selection_context_digest = extrapolation_selection_context_digest(
        selection_context_source
    )
    selection_receipts = []
    for index, assignment in enumerate(assignments):
        selected = index < 2
        selection_receipts.append(
            stamp_record(
                {
                    "record_type": "ExtrapolationSelectionReceipt",
                    "assignment_ref": assignment["record_id"],
                    "selection_policy": "m2-search-only-selection-v1",
                    "selection_context_digest": selection_context_digest,
                    "input_record_refs": [
                        assignment["record_id"],
                        bindings[index]["record_id"],
                        activity["record_id"],
                        lineage["record_id"],
                        baseline["record_id"],
                    ],
                    "checks": [
                        _check(
                            "candidate-policy",
                            "pass" if selected else "fail",
                            (
                                "The candidate satisfies the M2 selection policy."
                                if selected
                                else "The control remains outside the selected subset."
                            ),
                            [assignment["record_id"]],
                        )
                    ],
                    "selection_result": "selected" if selected else "not_selected",
                    "reason": "M2 selection fixture" if selected else "sealed exclusion control",
                    "baseline_validation_receipt_ref": baseline["record_id"],
                    "evaluator_ref": "urn:rulespec:extrapolator:m2-fixture",
                    "evaluator_version": "m2-search-only-selection-v1",
                    "evaluated_at": STAMP,
                    "effective_as_of": STAMP,
                }
            )
        )

    return stamp_release(
        {
            "record_type": "ExtrapolationRelease",
            "release_status": "fixture",
            "version": "m2-fixture-1",
            "profile": profile,
            "input_releases": input_releases,
            "validation_sample_manifest": validation_sample_manifest,
            "concept_assignments": assignments,
            "evidence_bindings": bindings,
            "extraction_activities": [activity],
            "ai_lineage_records": [lineage],
            "processing_segments": [segment],
            "derived_text_projections": [projection],
            "agent_validation_receipts": agent_receipts,
            "baseline_validation_receipts": [baseline],
            "selection_context_digest": selection_context_digest,
            "selection_receipts": selection_receipts,
            "validation_artifacts": validation_artifacts,
            "selected_assignment_refs": [
                assignments[0]["record_id"],
                assignments[1]["record_id"],
            ],
            "coverage": stamp_coverage(
                {
                    "record_type": "ExtrapolationCoverage",
                    "candidate_count": 3,
                    "selected_count": 2,
                    "not_selected_count": 1,
                    "deferred_count": 0,
                    "failure_count": 0,
                }
            ),
        },
        product="rulespec",
        release_kind="extrapolation",
    )


def build_negative_controls(release: Mapping[str, Any]) -> dict[str, Any]:
    excluded_ref = release["concept_assignments"][2]["record_id"]
    controls = [
        (
            "wrong-vocabulary-release",
            "PINNED_RELEASE_NOT_FOUND",
            [{"op": "replace", "path": "/input_releases/vocabulary_release/release_id", "value": "urn:refspec:vocabulary:missing"}],
        ),
        (
            "document-release-digest-mismatch",
            "PINNED_RELEASE_DIGEST_MISMATCH",
            [{"op": "replace", "path": "/input_releases/document_release/release_digest", "value": "sha256:" + "0" * 64}],
        ),
        (
            "missing-evidence",
            "MISSING_EVIDENCE",
            [{"op": "remove", "path": "/evidence_bindings/0"}],
        ),
        (
            "missing-ai-lineage",
            "MISSING_AI_LINEAGE",
            [{"op": "remove", "path": "/ai_lineage_records/0"}],
        ),
        (
            "non-search-only-usage",
            "NON_SEARCH_ONLY_ASSIGNMENT",
            [{"op": "replace", "path": "/concept_assignments/0/usage_eligibility", "value": "reviewQueueOnly"}],
        ),
        (
            "processing-segment-target",
            "PROCESSING_SEGMENT_TARGET",
            [{"op": "replace", "path": "/concept_assignments/0/subject_kind", "value": "ProcessingSegment"}],
        ),
        (
            "validator-abstention",
            "VALIDATOR_ABSTENTION",
            [
                {"op": "replace", "path": "/agent_validation_receipts/0/check_outcomes/0/outcome", "value": "abstain"},
                {"op": "replace", "path": "/agent_validation_receipts/0/overall_recommendation", "value": "abstains"},
            ],
        ),
        (
            "excluded-assignment-selected",
            "UNSELECTED_ASSIGNMENT_INCLUDED",
            [{"op": "replace", "path": "/selected_assignment_refs/1", "value": excluded_ref}],
        ),
    ]
    return {
        "fixture_type": "RulespecM2NegativeControlSet",
        "base_release_id": release["release_id"],
        "controls": [
            {"name": name, "expected_error": error, "operations": operations}
            for name, error, operations in controls
        ],
    }


def build_all() -> dict[str, Any]:
    core = load_json(CORE_FIXTURE)
    inputs = build_inputs(core)
    extrapolation = build_extrapolation(core, inputs)
    return {
        "inputs": inputs,
        "extrapolation": extrapolation,
        "negative_controls": build_negative_controls(extrapolation),
    }


def write_static_fixtures(fixtures: Mapping[str, Any]) -> None:
    """Rewrite the three checked-in fixture files deterministically."""

    fixture_dir = ROOT / "release-records/fixtures"
    targets = {
        "inputs": fixture_dir / "m2-input-releases.json",
        "extrapolation": fixture_dir / "m2-extrapolation-release-positive.json",
        "negative_controls": fixture_dir / "m2-negative-controls.json",
    }
    for name, path in targets.items():
        path.write_text(
            json.dumps(
                fixtures[name], indent=2, ensure_ascii=False, allow_nan=False
            )
            + "\n",
            encoding="utf-8",
        )


def vendor_upstream_fixtures(
    document_source: Path, vocabulary_source: Path
) -> None:
    """Copy publisher-owned release artifacts into the offline fixture set."""

    for source, target in (
        (document_source, DOCUMENT_FIXTURE),
        (vocabulary_source, VOCABULARY_FIXTURE),
    ):
        load_json(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("inputs", "extrapolation", "negative-controls", "all"))
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite the checked-in static fixtures before printing",
    )
    parser.add_argument("--vendor-document-release", type=Path)
    parser.add_argument("--vendor-vocabulary-release", type=Path)
    args = parser.parse_args()
    vendor_sources = (
        args.vendor_document_release,
        args.vendor_vocabulary_release,
    )
    if any(vendor_sources) and not all(vendor_sources):
        parser.error("both upstream release paths are required for vendoring")
    if all(vendor_sources):
        vendor_upstream_fixtures(*vendor_sources)
    fixtures = build_all()
    if args.write:
        write_static_fixtures(fixtures)
    value = fixtures if args.kind == "all" else fixtures[args.kind.replace("-", "_")]
    print(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
