"""Conformance tests for the partitioned ExtrapolationRelease v2 boundary."""

from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

import jsonschema

from tools.build_extrapolation_release_v2_fixtures import (
    FIXTURE_CARRIAGE_POLICY,
    FIXTURE_ROOT,
    UPSTREAM_DOCUMENT_RELEASE,
    VALID_BUNDLE,
    _tree_digest,
    build_valid_bundle,
    fixture_only_carriage_records,
)
from tools.build_rulespec_release_fixtures import open_vendored_atlas
from tools.extrapolation_release_v2 import (
    ROLE_SCHEMA_FILES,
    ROOT_SCHEMA,
    TABLE_SCHEMA_ROOT,
    canonical_sha256,
    load_strict_canonical_json,
    load_document_release_view,
    verify_extrapolation_release_v2,
)


class ExtrapolationReleaseV2SchemaTests(unittest.TestCase):
    def test_two_canonical_encoders_produce_the_same_safe_domain_digest(self) -> None:
        value = {"z": [3, True, None], "a": "é", "content": {"version": "2.0"}}
        reference = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        self.assertEqual(
            canonical_sha256(value),
            hashlib.sha256(reference).hexdigest(),
        )

    def test_manifest_loader_rejects_duplicate_float_bom_and_noncanonical_json(
        self,
    ) -> None:
        cases = {
            "duplicate": b'{"a":1,"a":2}',
            "float": b'{"a":1.5}',
            "bom": b'\xef\xbb\xbf{"a":1}',
            "noncanonical": b'{"b":2, "a":1}\n',
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, raw in cases.items():
                with self.subTest(case=name):
                    path = Path(directory) / f"{name}.json"
                    path.write_bytes(raw)
                    with self.assertRaises((ValueError, json.JSONDecodeError)):
                        load_strict_canonical_json(path)

    def test_root_and_row_schemas_are_valid_and_closed(self) -> None:
        paths = [
            ROOT_SCHEMA,
            *(TABLE_SCHEMA_ROOT / filename for filename in ROLE_SCHEMA_FILES.values()),
        ]
        for path in paths:
            with self.subTest(schema=path.name):
                schema = json.loads(path.read_text(encoding="utf-8"))
                jsonschema.Draft202012Validator.check_schema(schema)
                self.assertFalse(schema["additionalProperties"])
        root_schema = json.loads(ROOT_SCHEMA.read_text(encoding="utf-8"))
        schema_set = root_schema["$defs"]["schemaSet"]["properties"]["schemas"]
        self.assertEqual(schema_set["minItems"], 6)
        self.assertEqual(schema_set["maxItems"], 6)

    def test_assignment_confidence_is_optional_diagnostic_data(self) -> None:
        schema = json.loads(
            (TABLE_SCHEMA_ROOT / ROLE_SCHEMA_FILES["assignments"]).read_text(
                encoding="utf-8"
            )
        )
        confidence = schema["properties"]["confidence"]
        self.assertEqual(confidence["type"], ["number", "null"])
        self.assertNotIn("minimum", confidence)
        self.assertNotIn("maximum", confidence)
        root_schema = json.loads(ROOT_SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            set(root_schema["$defs"]["assignmentPolicy"]["properties"]),
            {
                "policyId",
                "policySha256",
                "emissionPolicyId",
                "candidateMethodId",
                "qualificationProtocolId",
            },
        )


@unittest.skipUnless(VALID_BUNDLE.exists(), "v2 fixture has not been generated")
class ExtrapolationReleaseV2FixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document_release = load_document_release_view(UPSTREAM_DOCUMENT_RELEASE)
        cls.atlas = open_vendored_atlas()

    def test_valid_fixture_verifies_without_a_sibling_worktree(self) -> None:
        result = verify_extrapolation_release_v2(
            VALID_BUNDLE,
            document_release=self.document_release,
            atlas=self.atlas,
        )
        self.assertEqual(result.code, "valid", "\n".join(map(str, result.issues)))
        self.assertTrue(result.release_id.startswith("urn:rulespec:extrapolation:v2:"))

    def test_fixture_reconciles_all_four_assignment_dispositions(self) -> None:
        import pyarrow.parquet as pq

        rows = []
        for path in sorted(
            VALID_BUNDLE.glob("data/partition-*/assignment-dispositions.parquet")
        ):
            rows.extend(pq.read_table(path).to_pylist())
        self.assertEqual(
            {row["disposition"] for row in rows},
            {"assigned", "abstained", "excluded", "failed"},
        )
        self.assertEqual(
            {row["document_id"] for row in rows},
            set(self.document_release.active_documents),
        )

    def test_annotations_do_not_change_release_identity(self) -> None:
        root = json.loads((VALID_BUNDLE / "release.json").read_text(encoding="utf-8"))
        original_id = root["releaseId"]
        root["annotations"]["operatorNote"] = "identity-neutral fixture annotation"
        expected = "urn:rulespec:extrapolation:v2:" + canonical_sha256(
            {
                "format": root["format"],
                "formatVersion": root["formatVersion"],
                "content": root["content"],
            }
        )
        self.assertEqual(expected, original_id)

    def test_checked_fixture_matches_the_deterministic_builder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "release"
            build_valid_bundle(target, UPSTREAM_DOCUMENT_RELEASE)
            self.assertEqual(_tree_digest(target), _tree_digest(VALID_BUNDLE))

    def test_sealed_negative_corpus_returns_the_named_first_code(self) -> None:
        corpus = json.loads((FIXTURE_ROOT / "corpus.json").read_text(encoding="utf-8"))
        for case in corpus["cases"]:
            with self.subTest(case=case["name"]):
                bundle = FIXTURE_ROOT / case["bundle"]
                self.assertEqual(_tree_digest(bundle), case["treeSha256"])
                result = verify_extrapolation_release_v2(
                    bundle,
                    document_release=self.document_release,
                    atlas=self.atlas,
                )
                self.assertEqual(
                    result.code,
                    case["expectedCode"],
                    "\n".join(map(str, result.issues)),
                )

    def test_input_document_release_copy_is_complete_and_digest_pinned(self) -> None:
        root = json.loads((VALID_BUNDLE / "release.json").read_text(encoding="utf-8"))
        self.assertEqual(
            root["content"]["input_releases"]["document_release"],
            self.document_release.v1_pin,
        )
        self.assertEqual(len(self.document_release.active_documents), 4)


class FixtureCarriageBoundaryTests(unittest.TestCase):
    def test_carriage_helper_refuses_every_nonfixture_status(self) -> None:
        for status in ("candidate", "published", "", "Fixture"):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, "fixture"):
                    fixture_only_carriage_records(
                        release_status=status,
                        document_release_id="",
                        document_version_id="",
                        passage_id="",
                        passage_text="",
                    )

    def test_fixture_policy_names_upstream_passage_carriage(self) -> None:
        self.assertEqual(
            FIXTURE_CARRIAGE_POLICY,
            "spicyregs-passage-carriage-fixture-v1",
        )


if __name__ == "__main__":
    unittest.main()
