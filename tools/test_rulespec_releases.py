"""Canonical Rulespec Core and Extrapolator release conformance tests."""

from __future__ import annotations

import copy
import hashlib
import inspect
import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import jsonschema

from tools.build_rulespec_release_fixtures import (
    FIXTURE_ONLY_SEGMENTATION_POLICY,
    FIXTURE_RELEASE_STATUS,
    build_all,
    fixture_only_prepared_segment,
    open_fixture_atlas,
)
from tools.rulespec_release import (
    apply_negative_control,
    canonical_digest,
    canonical_json_bytes,
    compute_release_digest,
    extrapolation_selection_context_digest,
    index_input_releases,
    load_json,
)
from tools.rulespec_release import main as release_main
from tools.rulespec_release import (
    stable_record_id,
    stamp_release,
    validate_extrapolation_release,
    validate_rulespec_core_release,
)

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "release-records"
FIXTURES = RELEASES / "fixtures"
SCHEMAS = RELEASES / "schemas"
CORE = FIXTURES / "rulespec-core-release-m2.json"
INPUTS = FIXTURES / "m2-input-releases.json"
EXTRAPOLATION = FIXTURES / "m2-extrapolation-release-positive.json"
NEGATIVE_CONTROLS = FIXTURES / "m2-negative-controls.json"
UPSTREAM = FIXTURES / "upstream"


class CanonicalJsonTests(unittest.TestCase):
    def test_utf8_sorted_compact_bytes_are_normative(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"z": "é", "a": [True, None, 3]}),
            b'{"a":[true,null,3],"z":"\xc3\xa9"}',
        )

    def test_loader_rejects_duplicate_keys_and_nonfinite_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            duplicate = Path(directory) / "duplicate.json"
            duplicate.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON object key"):
                load_json(duplicate)
            nonfinite = Path(directory) / "nonfinite.json"
            nonfinite.write_text('{"a":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not permitted"):
                load_json(nonfinite)

    def test_release_digest_omits_only_root_identity(self) -> None:
        release = {
            "record_type": "FixtureRelease",
            "release_id": "urn:fixture:old",
            "release_digest": "sha256:" + "0" * 64,
            "nested": {
                "release_id": "urn:nested:kept",
                "release_digest": "sha256:" + "1" * 64,
            },
        }
        expected = canonical_digest(
            {"record_type": "FixtureRelease", "nested": release["nested"]}
        )
        self.assertEqual(compute_release_digest(release), expected)
        changed = copy.deepcopy(release)
        changed["nested"]["release_id"] = "urn:nested:changed"
        self.assertNotEqual(compute_release_digest(changed), expected)


class CoreReleaseTests(unittest.TestCase):
    def test_core_fixture_is_content_addressed_and_complete_for_m2(self) -> None:
        release = load_json(CORE)
        self.assertEqual(validate_rulespec_core_release(release), [])
        self.assertEqual(
            release["release_id"],
            "urn:rulespec:core:777d05c3ab8749271b432c0a8c69d60a8e4afe23b4a89f2f7c68c3d27c1491eb",
        )
        names = {artifact["name"] for artifact in release["schema_artifacts"]}
        self.assertEqual(
            names,
            {
                "compiled/json-schema/core/artifact.schema.json",
                "compiled/json-schema/core/source-fragment.schema.json",
                "compiled/json-schema/core/concept-assignment.schema.json",
                "compiled/json-schema/core/evidence-binding.schema.json",
                "compiled/json-schema/core/extraction-activity.schema.json",
                "compiled/json-schema/core/ai-lineage.schema.json",
                "compiled/json-schema/core/reference-resource-release.schema.json",
            },
        )
        self.assertEqual(len(release["conformance_fixture_artifacts"]), 8)

    def test_core_schema_accepts_the_fixture(self) -> None:
        schema = load_json(SCHEMAS / "rulespec-core-release.schema.json")
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(load_json(CORE))

    def test_core_manifest_digests_match_repository_artifacts(self) -> None:
        release = load_json(CORE)
        for manifest_name in (
            "schema_artifacts",
            "validator_artifacts",
            "conformance_fixture_artifacts",
        ):
            for artifact in release[manifest_name]:
                with self.subTest(artifact=artifact["name"]):
                    content = (ROOT / artifact["name"]).read_bytes()
                    digest = "sha256:" + hashlib.sha256(content).hexdigest()
                    self.assertEqual(artifact["artifact_digest"], digest)


class InputReleaseIndexTests(unittest.TestCase):
    def test_compact_standalone_vocabulary_release_is_retired(self) -> None:
        legacy = {
            "schema_version": "refspec-vocabulary-release-v1",
            "release_id": "urn:refspec:vocabulary-release:" + "0" * 64,
            "release_digest": "sha256:" + "0" * 64,
        }
        records, issues = index_input_releases([legacy])
        self.assertEqual(records, {})
        self.assertEqual(
            {issue.code for issue in issues},
            {"UNSUPPORTED_INPUT_RELEASE"},
        )


class ExtrapolationReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.core = load_json(CORE)
        self.input_bundle = load_json(INPUTS)
        self.release = load_json(EXTRAPOLATION)
        self.atlas = open_fixture_atlas()
        self.inputs, self.input_issues = index_input_releases(
            [self.core, self.input_bundle]
        )

    def _restamp_validation_graph(self, changed: dict, agent_index: int) -> dict:
        agent = changed["agent_validation_receipts"][agent_index]
        old_agent_id = agent["record_id"]
        agent["record_id"] = stable_record_id(agent)

        baseline = changed["baseline_validation_receipts"][0]
        baseline["agent_validation_receipt_refs"] = [
            agent["record_id"] if ref == old_agent_id else ref
            for ref in baseline["agent_validation_receipt_refs"]
        ]
        old_baseline_id = baseline["record_id"]
        baseline["record_id"] = stable_record_id(baseline)

        selection_context_digest = extrapolation_selection_context_digest(changed)
        changed["selection_context_digest"] = selection_context_digest
        for selection in changed["selection_receipts"]:
            selection["baseline_validation_receipt_ref"] = baseline["record_id"]
            selection["input_record_refs"] = [
                baseline["record_id"] if ref == old_baseline_id else ref
                for ref in selection["input_record_refs"]
            ]
            selection["selection_context_digest"] = selection_context_digest
            selection["record_id"] = stable_record_id(selection)

        return stamp_release(
            changed,
            product="rulespec",
            release_kind="extrapolation",
        )

    def test_checked_in_fixtures_match_the_deterministic_builder(self) -> None:
        built = build_all()
        self.assertEqual(load_json(INPUTS), built["inputs"])
        self.assertEqual(load_json(EXTRAPOLATION), built["extrapolation"])
        self.assertEqual(load_json(NEGATIVE_CONTROLS), built["negative_controls"])

    def test_positive_release_closes_without_sibling_repositories(self) -> None:
        self.assertEqual(self.input_issues, [])
        self.assertEqual(
            validate_extrapolation_release(self.release, self.inputs, self.atlas),
            [],
        )
        self.assertEqual(
            self.release["release_id"],
            "urn:rulespec:extrapolation:b3b8bf2616b7eeb4f45787cf4299f5edf288152a79c3e1da2cfbc91e6ef0d486",
        )
        selected = set(self.release["selected_assignment_refs"])
        selected_kinds = {
            assignment["subject_kind"]
            for assignment in self.release["concept_assignments"]
            if assignment["record_id"] in selected
        }
        self.assertEqual(selected_kinds, {"Artifact", "SourceFragment"})
        self.assertEqual(
            self.release["coverage"]["coverage_id"],
            "urn:rulespec:extrapolation-coverage:5274a5dd8ee1c32d791db89ec327b68eab4e48c61ffbbda31cc2fb22e552d92e",
        )

    def test_cli_validates_the_static_file_seam(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = release_main(
                [
                    "validate",
                    str(EXTRAPOLATION),
                    "--input",
                    str(CORE),
                    "--input",
                    str(INPUTS),
                    "--vocabulary-atlas",
                    str(FIXTURES / "rulespec-atlas-membership-stub"),
                ]
            )
        self.assertEqual(result, 0, stderr.getvalue())
        self.assertIn("PASS ExtrapolationRelease", stdout.getvalue())

    def test_upstream_records_and_assignment_targets_are_authoritative(self) -> None:
        (document,) = self.input_bundle["records"]
        self.assertEqual(
            document,
            load_json(UPSTREAM / "spicyregs-document-release-v1.json"),
        )
        self.assertEqual(
            self.release["input_releases"]["vocabulary_atlas_asset"],
            self.atlas.pin(),
        )
        self.assertEqual(
            document["release_id"],
            "urn:spicyregs:document-release:209cfb23ca4b9e2b3be2ea4632490ddbdf1e3a2efc3540d074bd0e29836f4baa",
        )
        reference_pin = self.atlas.require_member(
            member_id=self.release["concept_assignments"][0]["asserts_object_ref"],
            release_id=self.release["input_releases"]["reference_resource_release"][
                "release_id"
            ],
        )
        self.assertEqual(
            self.release["input_releases"]["reference_resource_release"],
            {
                "release_id": reference_pin.release_id,
                "release_digest": reference_pin.release_digest,
            },
        )
        assignments = self.release["concept_assignments"]
        self.assertEqual(
            assignments[0]["asserts_subject_ref"],
            "urn:spicyregs:artifact:ec1f19077074c2895d4968af2c329d554dcdf523be130fef492631b1886ec98f",
        )
        self.assertEqual(
            assignments[1]["asserts_subject_ref"],
            "urn:spicyregs:source-fragment:8b1ec44153407557c9b58422b100613b60e75896d55b229f95c6efbc393fb07e",
        )
        self.assertEqual(
            {assignment["asserts_object_ref"] for assignment in assignments},
            {"urn:ref:federal-register-thesaurus:2025-04-01:concept:0570"},
        )

    def test_every_candidate_target_uses_verified_atlas_membership(self) -> None:
        class RecordingAtlas:
            def __init__(self, wrapped):
                self.wrapped = wrapped
                self.calls = []

            def pin(self):
                return self.wrapped.pin()

            def rulespec_core_pin(self):
                return self.wrapped.rulespec_core_pin()

            def require_member(self, *, member_id, release_id):
                self.calls.append((member_id, release_id))
                return self.wrapped.require_member(
                    member_id=member_id,
                    release_id=release_id,
                )

        atlas = RecordingAtlas(self.atlas)
        self.assertEqual(
            validate_extrapolation_release(self.release, self.inputs, atlas),
            [],
        )
        self.assertEqual(
            len(atlas.calls),
            len(self.release["concept_assignments"]),
        )
        self.assertEqual(
            set(atlas.calls),
            {
                (
                    assignment["asserts_object_ref"],
                    assignment["assigned_concept_release_ref"],
                )
                for assignment in self.release["concept_assignments"]
            },
        )

    def test_projection_accounts_for_every_derived_character(self) -> None:
        segment = self.release["processing_segments"][0]
        projection = self.release["derived_text_projections"][0]
        slices = projection["ordered_slices"]
        self.assertEqual(slices[0]["derived_start"], 0)
        self.assertEqual(slices[-1]["derived_end"], len(segment["derived_text"]))
        self.assertEqual(
            [(item["derived_start"], item["derived_end"]) for item in slices],
            [(0, 44), (44, 45), (45, 73)],
        )
        self.assertEqual(projection["normalization_policy"], "none")
        self.assertEqual(projection["join_delimiter"], "\n")

    def test_receipts_retain_sealed_inputs_and_independent_attempts(self) -> None:
        artifacts = {
            artifact["artifact_id"]: artifact
            for artifact in self.release["validation_artifacts"]
        }
        groups = set()
        actors = set()
        providers = set()
        for receipt in self.release["agent_validation_receipts"]:
            groups.add(receipt["independence_group"])
            actors.add(receipt["validator_actor_ref"])
            providers.add(receipt["provider_model_id"])
            self.assertEqual(receipt["execution_status"], "completed")
            self.assertIn(receipt["request_contract_ref"], artifacts)
            self.assertIn(receipt["response_artifact_ref"], artifacts)
            self.assertEqual(
                artifacts[receipt["response_artifact_ref"]]["content_digest"],
                receipt["response_artifact_digest"],
            )
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(actors), 2)
        self.assertEqual(len(providers), 2)
        for receipt in self.release["selection_receipts"]:
            self.assertNotIn("output_extrapolation_release_ref", receipt)
            self.assertEqual(
                receipt["selection_context_digest"],
                self.release["selection_context_digest"],
            )

    def test_usable_baseline_requires_distinct_machine_validators(self) -> None:
        first, second = self.release["agent_validation_receipts"][:2]
        for field in ("independence_group", "validator_actor_ref"):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.release)
                changed["agent_validation_receipts"][1][field] = first[field]
                changed = stamp_release(
                    changed,
                    product="rulespec",
                    release_kind="extrapolation",
                )
                codes = {
                    issue.code
                    for issue in validate_extrapolation_release(
                        changed, self.inputs, self.atlas
                    )
                }
                self.assertIn("VALIDATORS_NOT_INDEPENDENT", codes)

        changed = copy.deepcopy(self.release)
        changed_second = changed["agent_validation_receipts"][1]
        original_ref = changed_second["record_id"]
        changed_second["provider_model_id"] = first["provider_model_id"]
        changed_second["record_id"] = stable_record_id(changed_second)
        changed["baseline_validation_receipts"][0]["agent_validation_receipt_refs"] = [
            changed_second["record_id"] if value == original_ref else value
            for value in changed["baseline_validation_receipts"][0][
                "agent_validation_receipt_refs"
            ]
        ]
        changed = stamp_release(
            changed,
            product="rulespec",
            release_kind="extrapolation",
        )
        codes = {
            issue.code
            for issue in validate_extrapolation_release(
                changed, self.inputs, self.atlas
            )
        }
        self.assertIn("VALIDATORS_NOT_INDEPENDENT", codes)

        changed = copy.deepcopy(self.release)
        changed_first, changed_second = changed["agent_validation_receipts"][:2]
        original_ref = changed_second["record_id"]
        changed_second["response_artifact_ref"] = changed_first["response_artifact_ref"]
        changed_second["response_artifact_digest"] = changed_first[
            "response_artifact_digest"
        ]
        changed_second["record_id"] = stable_record_id(changed_second)
        changed["baseline_validation_receipts"][0]["agent_validation_receipt_refs"] = [
            changed_second["record_id"] if value == original_ref else value
            for value in changed["baseline_validation_receipts"][0][
                "agent_validation_receipt_refs"
            ]
        ]
        changed = stamp_release(
            changed,
            product="rulespec",
            release_kind="extrapolation",
        )
        codes = {
            issue.code
            for issue in validate_extrapolation_release(
                changed, self.inputs, self.atlas
            )
        }
        self.assertIn("VALIDATORS_NOT_INDEPENDENT", codes)

    def test_usable_baseline_rejects_hand_restamped_flags_recommendation(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["agent_validation_receipts"][0]["overall_recommendation"] = "flags"
        changed = self._restamp_validation_graph(changed, 0)

        codes = {
            issue.code
            for issue in validate_extrapolation_release(
                changed, self.inputs, self.atlas
            )
        }
        self.assertIn("BASELINE_VALIDATOR_NOT_SUPPORTIVE", codes)
        self.assertNotIn("RECORD_ID_MISMATCH", codes)
        self.assertNotIn("RELEASE_DIGEST_MISMATCH", codes)

    def test_usable_baseline_rejects_hand_restamped_failed_check(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["agent_validation_receipts"][0]["check_outcomes"][0]["outcome"] = "fail"
        changed = self._restamp_validation_graph(changed, 0)

        codes = {
            issue.code
            for issue in validate_extrapolation_release(
                changed, self.inputs, self.atlas
            )
        }
        self.assertIn("BASELINE_VALIDATOR_CHECK_FAILED", codes)
        self.assertNotIn("RECORD_ID_MISMATCH", codes)
        self.assertNotIn("RELEASE_DIGEST_MISMATCH", codes)

    def test_usable_baseline_requires_exactly_two_validators(self) -> None:
        changed = copy.deepcopy(self.release)
        third = copy.deepcopy(changed["agent_validation_receipts"][0])
        third.update(
            {
                "record_id": "urn:rulespec:agent-validation-receipt:pending",
                "attempt_id": "m2-validator-c",
                "independence_group": "model-family-c",
                "validator_actor_ref": "urn:rulespec:validator:m2-fixture-c",
                "provider_model_id": "fixture-provider/model-c@1",
            }
        )
        changed["agent_validation_receipts"].append(third)
        changed["baseline_validation_receipts"][0][
            "agent_validation_receipt_refs"
        ].append(third["record_id"])
        changed = self._restamp_validation_graph(changed, 2)

        codes = {
            issue.code
            for issue in validate_extrapolation_release(
                changed, self.inputs, self.atlas
            )
        }
        self.assertIn("BASELINE_VALIDATOR_COUNT_INVALID", codes)
        self.assertNotIn("RECORD_ID_MISMATCH", codes)
        self.assertNotIn("RELEASE_DIGEST_MISMATCH", codes)

    def test_terminal_receipt_ids_bind_decisions_and_outcomes(self) -> None:
        mutations = (
            ("agent_validation_receipts", "overall_recommendation", "abstains"),
            ("baseline_validation_receipts", "aggregate_result", "deferred"),
            ("selection_receipts", "selection_result", "deferred"),
        )
        for collection, field, value in mutations:
            receipt = copy.deepcopy(self.release[collection][0])
            original_id = receipt["record_id"]
            receipt[field] = value
            self.assertNotEqual(stable_record_id(receipt), original_id)

    def test_selection_receipts_cannot_be_reused_for_another_input_graph(self) -> None:
        changed = copy.deepcopy(self.release)
        changed["input_releases"]["document_release"]["release_digest"] = (
            "sha256:" + "0" * 64
        )
        changed = stamp_release(
            changed, product="rulespec", release_kind="extrapolation"
        )
        codes = {
            issue.code
            for issue in validate_extrapolation_release(
                changed, self.inputs, self.atlas
            )
        }
        self.assertIn("SELECTION_CONTEXT_MISMATCH", codes)

    def test_extrapolation_schema_accepts_the_fixture(self) -> None:
        schema = load_json(SCHEMAS / "extrapolation-release.schema.json")
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(
            schema, format_checker=jsonschema.FormatChecker()
        ).validate(self.release)

    def test_all_sealed_negative_controls_fail_closed(self) -> None:
        controls = load_json(NEGATIVE_CONTROLS)
        self.assertEqual(controls["base_release_id"], self.release["release_id"])
        self.assertEqual(
            [control["name"] for control in controls["controls"]],
            [
                "wrong-vocabulary-atlas",
                "reference-release-digest-mismatch",
                "document-release-digest-mismatch",
                "missing-evidence",
                "missing-ai-lineage",
                "non-search-only-usage",
                "processing-segment-target",
                "validator-abstention",
                "excluded-assignment-selected",
                "unselected-assignment-nonmember",
            ],
        )
        for control in controls["controls"]:
            with self.subTest(control=control["name"]):
                mutated = apply_negative_control(self.release, control)
                issues = validate_extrapolation_release(
                    mutated, self.inputs, self.atlas
                )
                codes = {issue.code for issue in issues}
                self.assertIn(control["expected_error"], codes)
                self.assertNotIn("RELEASE_DIGEST_MISMATCH", codes)
                self.assertNotIn("RELEASE_ID_MISMATCH", codes)

    def test_empty_release_fails_closed(self) -> None:
        empty = copy.deepcopy(self.release)
        empty["selected_assignment_refs"] = []
        empty = stamp_release(empty, product="rulespec", release_kind="extrapolation")
        codes = {
            issue.code
            for issue in validate_extrapolation_release(empty, self.inputs, self.atlas)
        }
        self.assertIn("EXTRAPOLATION_RELEASE_EMPTY", codes)


class FixtureOnlySegmentationTests(unittest.TestCase):
    """Hold the 2026-08-02 execution boundary at the one place it could leak.

    SpicyRegs owns model-input segmentation. This repository owns no segmenter
    and must never grow one. The M2 fixture still needs a sealed segment to
    validate against, so one hand-authored join lives in the fixture builder.
    These tests assert that it stays exactly there and reaches nothing else.
    """

    SOURCE_ROOTS = ("tools", "crates")

    def _repository_sources(self) -> list[Path]:
        """Every Python and Rust source in the tree except this assertion file.

        This module names the fixture-only strings in order to fence them; it is
        the fence, not a code path that could reach the join.
        """

        this_file = Path(__file__).resolve()
        paths: list[Path] = []
        for name in self.SOURCE_ROOTS:
            for path in sorted((ROOT / name).rglob("*")):
                if path.suffix not in {".py", ".rs"} or not path.is_file():
                    continue
                if "target" in path.parts or "__pycache__" in path.parts:
                    continue
                if path.resolve() == this_file:
                    continue
                paths.append(path)
        return paths

    def test_prepared_segment_helper_refuses_a_non_fixture_release_status(self) -> None:
        # The refusal precedes every input read, so the empty mappings below
        # would raise KeyError if the guard ever moved after the join.
        for status in ("candidate", "published", "", "Fixture"):
            with self.subTest(release_status=status):
                with self.assertRaisesRegex(ValueError, "fixture"):
                    fixture_only_prepared_segment(
                        release_status=status,
                        document={},
                        representation={},
                        first_fragment={},
                        second_fragment={},
                    )

    def test_only_fixture_builders_construct_processing_segments(self) -> None:
        construction = '"record_type": "ProcessingSegment"'
        builders = [
            path
            for path in self._repository_sources()
            if construction in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(
            [path.relative_to(ROOT).as_posix() for path in builders],
            [
                "tools/build_extrapolation_release_v2_fixtures.py",
                "tools/build_rulespec_release_fixtures.py",
            ],
        )
        helper_source = inspect.getsource(fixture_only_prepared_segment)
        self.assertIn(construction, helper_source)
        module_source = Path(
            inspect.getsourcefile(fixture_only_prepared_segment) or ""
        ).read_text(encoding="utf-8")
        self.assertEqual(module_source.count(construction), 1)
        self.assertIn("not a segmenter", fixture_only_prepared_segment.__doc__ or "")

    def test_the_fixture_only_segmentation_policy_names_no_other_code_path(
        self,
    ) -> None:
        self.assertEqual(
            FIXTURE_ONLY_SEGMENTATION_POLICY, "join-structural-passages-v1"
        )
        naming = {
            path.relative_to(ROOT).as_posix()
            for path in self._repository_sources()
            if FIXTURE_ONLY_SEGMENTATION_POLICY in path.read_text(encoding="utf-8")
        }
        self.assertEqual(naming, {"tools/build_rulespec_release_fixtures.py"})
        helper_source = inspect.getsource(fixture_only_prepared_segment)
        self.assertNotIn(FIXTURE_ONLY_SEGMENTATION_POLICY, helper_source)
        self.assertIn("FIXTURE_ONLY_SEGMENTATION_POLICY", helper_source)

    def test_the_portable_validator_verifies_derived_text_and_never_builds_it(
        self,
    ) -> None:
        validator = (ROOT / "tools/rulespec_release.py").read_text(encoding="utf-8")
        self.assertIn('derived_text = segment.get("derived_text")', validator)
        self.assertEqual(len(re.findall(r"^\s*derived_text\s*=", validator, re.M)), 1)
        self.assertNotIn(FIXTURE_ONLY_SEGMENTATION_POLICY, validator)

    def test_every_release_the_builder_can_emit_is_fixture_status(self) -> None:
        self.assertEqual(FIXTURE_RELEASE_STATUS, "fixture")
        built = build_all()
        self.assertEqual(
            built["extrapolation"]["release_status"], FIXTURE_RELEASE_STATUS
        )
        for control in built["negative_controls"]["controls"]:
            for operation in control["operations"]:
                with self.subTest(control=control["name"], path=operation["path"]):
                    self.assertNotEqual(operation["path"], "/release_status")


if __name__ == "__main__":
    unittest.main()
