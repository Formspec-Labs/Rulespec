"""Canonical Rulespec Core and Extrapolator release conformance tests."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

import jsonschema

from tools.build_rulespec_release_fixtures import build_all
from tools.rulespec_release import (
    apply_negative_control,
    canonical_digest,
    canonical_json_bytes,
    compute_release_digest,
    index_input_releases,
    load_json,
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
        expected = canonical_digest({"record_type": "FixtureRelease", "nested": release["nested"]})
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
            "urn:rulespec:core:5ac6ba59929eca874ec603cab0e90f7b15ab1a008b394cec5aefebdafe22564b",
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


class ExtrapolationReleaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.core = load_json(CORE)
        self.input_bundle = load_json(INPUTS)
        self.release = load_json(EXTRAPOLATION)
        self.inputs, self.input_issues = index_input_releases(
            [self.core, self.input_bundle]
        )

    def test_checked_in_fixtures_match_the_deterministic_builder(self) -> None:
        built = build_all()
        self.assertEqual(load_json(INPUTS), built["inputs"])
        self.assertEqual(load_json(EXTRAPOLATION), built["extrapolation"])
        self.assertEqual(
            load_json(NEGATIVE_CONTROLS), built["negative_controls"]
        )

    def test_positive_release_closes_without_sibling_repositories(self) -> None:
        self.assertEqual(self.input_issues, [])
        self.assertEqual(validate_extrapolation_release(self.release, self.inputs), [])
        self.assertEqual(
            self.release["release_id"],
            "urn:rulespec:extrapolation:7fe7cee1549c0be348f843dede0c0b2707bf1bb581b11fae887d2ce2541d9aa9",
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

    def test_upstream_records_and_assignment_targets_are_authoritative(self) -> None:
        document, vocabulary = self.input_bundle["records"]
        self.assertEqual(
            document,
            load_json(UPSTREAM / "spicyregs-document-release-v1.json"),
        )
        self.assertEqual(
            vocabulary,
            load_json(UPSTREAM / "refspec-vocabulary-release-first-slice.json"),
        )
        self.assertEqual(
            document["release_id"],
            "urn:spicyregs:document-release:d0a148e2791a0c537d49a9d6cab87869e21c4dbfb9966da63d59a0c5165f71e4",
        )
        self.assertEqual(
            vocabulary["release_id"],
            "urn:refspec:vocabulary-release:85d675be32b43c15a58435c0faa0c5775de86141352dd6ce8f34890a55835828",
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
            {
                "urn:refspec:vocabulary:federal-register-thesaurus:2025-04-01:concept:0570"
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
        for receipt in self.release["agent_validation_receipts"]:
            groups.add(receipt["independence_group"])
            self.assertEqual(receipt["execution_status"], "completed")
            self.assertIn(receipt["request_contract_ref"], artifacts)
            self.assertIn(receipt["response_artifact_ref"], artifacts)
            self.assertEqual(
                artifacts[receipt["response_artifact_ref"]]["content_digest"],
                receipt["response_artifact_digest"],
            )
        self.assertEqual(len(groups), 2)
        for receipt in self.release["selection_receipts"]:
            self.assertNotIn("output_extrapolation_release_ref", receipt)
            self.assertEqual(
                receipt["selection_context_digest"],
                self.release["selection_context_digest"],
            )

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
            issue.code for issue in validate_extrapolation_release(changed, self.inputs)
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
                "wrong-vocabulary-release",
                "document-release-digest-mismatch",
                "missing-evidence",
                "missing-ai-lineage",
                "non-search-only-usage",
                "processing-segment-target",
                "validator-abstention",
                "excluded-assignment-selected",
            ],
        )
        for control in controls["controls"]:
            with self.subTest(control=control["name"]):
                mutated = apply_negative_control(self.release, control)
                issues = validate_extrapolation_release(mutated, self.inputs)
                codes = {issue.code for issue in issues}
                self.assertIn(control["expected_error"], codes)
                self.assertNotIn("RELEASE_DIGEST_MISMATCH", codes)
                self.assertNotIn("RELEASE_ID_MISMATCH", codes)

    def test_empty_release_fails_closed(self) -> None:
        empty = copy.deepcopy(self.release)
        empty["selected_assignment_refs"] = []
        empty = stamp_release(
            empty, product="rulespec", release_kind="extrapolation"
        )
        codes = {
            issue.code for issue in validate_extrapolation_release(empty, self.inputs)
        }
        self.assertIn("EXTRAPOLATION_RELEASE_EMPTY", codes)


if __name__ == "__main__":
    unittest.main()
