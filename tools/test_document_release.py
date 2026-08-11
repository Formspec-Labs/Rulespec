"""Conformance tests for the DocumentRelease v2 boundary."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema
import rfc8785

from tools.build_document_release_fixtures import (
    CANDIDATE_VERSION,
    SOURCE_CATALOG_FIXTURE,
    VALID_BUNDLE,
    build_candidate_manifest,
    build_corpus,
)
from tools.document_release import (
    CANDIDATE_MANIFEST,
    CATALOG_DISPOSITIONS,
    CODE_PRECEDENCE,
    CORPUS_FILE,
    DIAGNOSTIC_CODES,
    FORMAT,
    FORMAT_VERSION,
    RELEASE_ID_PREFIX,
    SCHEMA_FILES,
    SCHEMA_IDS,
    bundle_release_id,
    candidate_bundle_errors,
    derive_coverage,
    expected_release_id,
    mapping_digest,
    verify_document_release,
)
from tools.source_catalog_release import canonical_json_bytes, tree_digest


def _valid_root() -> dict:
    return json.loads((VALID_BUNDLE / "release.json").read_text(encoding="utf-8"))


def _member(name: str) -> list:
    return json.loads((VALID_BUNDLE / "data" / name).read_text(encoding="utf-8"))


class SchemaSetTests(unittest.TestCase):
    def test_every_schema_is_a_valid_closed_draft_2020_12_document(self) -> None:
        for role, path in SCHEMA_FILES.items():
            with self.subTest(schema=role):
                schema = json.loads(path.read_text(encoding="utf-8"))
                jsonschema.Draft202012Validator.check_schema(schema)
                self.assertIs(schema["additionalProperties"], False)
                self.assertEqual(schema["$id"], SCHEMA_IDS[role])

    def test_the_catalog_disposition_enum_projects_all_five_catalog_values(self) -> None:
        schema = json.loads(SCHEMA_FILES["source-dispositions"].read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(schema["properties"]["catalogDisposition"]["enum"]),
            sorted(CATALOG_DISPOSITIONS),
        )

    def test_a_selected_item_must_carry_a_document_and_a_non_selected_must_not(self) -> None:
        """The bijection is structural: a processing failure cannot become a silent exclusion."""

        schema = json.loads(SCHEMA_FILES["source-dispositions"].read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        base = {
            "sourceItemId": "s1",
            "documentId": "d1",
            "sourceIssuedVersion": "v1",
            "processingFailures": [],
        }
        self.assertEqual(
            list(validator.iter_errors({**base, "catalogDisposition": "selected", "documentVersionId": "d1@v1"})),
            [],
        )
        self.assertTrue(
            list(validator.iter_errors({**base, "catalogDisposition": "selected", "documentVersionId": None}))
        )
        self.assertTrue(
            list(
                validator.iter_errors(
                    {**base, "catalogDisposition": "excluded", "documentVersionId": "d1@v1"}
                )
            )
        )

    def test_a_search_segment_always_names_a_structural_parent(self) -> None:
        schema = json.loads(SCHEMA_FILES["search-segments"].read_text(encoding="utf-8"))
        parent = schema["properties"]["structuralParentId"]
        self.assertEqual(parent["type"], "string")
        self.assertNotIn("oneOf", parent)
        self.assertTrue(list(jsonschema.Draft202012Validator(parent).iter_errors(None)))
        self.assertIn("structuralParentId", schema["required"])
        self.assertIn("headingPath", schema["required"])
        self.assertIn("evidence", schema["required"])


class SharedProtocolTests(unittest.TestCase):
    def test_both_validators_share_one_path_safety_implementation(self) -> None:
        """A second copy could drift in behaviour while both looked maintained."""

        import tools.document_release as document
        import tools.source_catalog_release as catalog

        self.assertIs(document.safe_object_key, catalog._safe_object_key)
        self.assertIs(document.member_path, catalog._member_path)
        self.assertIs(document.tree_digest, catalog.tree_digest)

    def test_the_source_catalog_candidate_is_undisturbed(self) -> None:
        """Importing from a sealed module must not re-mint its candidate."""

        from tools.source_catalog_release import candidate_bundle_errors as catalog_errors

        self.assertEqual(catalog_errors(), [])

    def test_the_canonical_encoder_agrees_with_rfc_8785(self) -> None:
        for path in (CORPUS_FILE, CANDIDATE_MANIFEST, VALID_BUNDLE / "release.json"):
            with self.subTest(document=path.name):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(canonical_json_bytes(value), rfc8785.dumps(value))


class IdentityTests(unittest.TestCase):
    def test_the_version_does_not_collide_with_docspec_live_format(self) -> None:
        """`docspec-document-release` 1.1 is a different, internal shape."""

        root = _valid_root()
        self.assertEqual(root["format"], FORMAT)
        self.assertEqual(root["formatVersion"], FORMAT_VERSION)
        self.assertNotEqual(root["formatVersion"], "1.1")
        self.assertTrue(root["releaseId"].startswith(RELEASE_ID_PREFIX))
        self.assertTrue(RELEASE_ID_PREFIX.startswith("urn:docspec:"))

    def test_no_document_in_this_candidate_carries_the_retired_urn_spelling(self) -> None:
        for path in (*SCHEMA_FILES.values(), CORPUS_FILE, CANDIDATE_MANIFEST):
            with self.subTest(document=path.name):
                self.assertNotIn("urn:spicyregs:", path.read_text(encoding="utf-8"))

    def test_publishing_the_same_corpus_later_does_not_change_identity(self) -> None:
        root = _valid_root()
        self.assertNotIn("publishedAt", root["content"])
        self.assertIn("publishedAt", root["annotations"])
        republished = json.loads(json.dumps(root))
        republished["annotations"]["publishedAt"] = "2027-01-01T00:00:00Z"
        self.assertEqual(expected_release_id(republished), root["releaseId"])

    def test_identity_binds_the_format_token_and_version(self) -> None:
        """DocSpec's live identity digests content alone; this one cannot collide."""

        root = _valid_root()
        reshaped = json.loads(json.dumps(root))
        reshaped["formatVersion"] = "2.1"
        self.assertNotEqual(expected_release_id(reshaped), root["releaseId"])

    def test_no_capture_record_carries_a_wall_clock(self) -> None:
        """A capture time inside a content-derived identity is the createdAt trap."""

        for document in _member("documents.json"):
            with self.subTest(document=document["documentVersionId"]):
                self.assertNotIn("acquiredAt", document["capture"])
                self.assertNotIn("capturedAt", document["capture"])


class SealedCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))

    def test_the_valid_fixture_verifies_and_names_itself_by_content(self) -> None:
        result = verify_document_release(VALID_BUNDLE)
        self.assertEqual(result.code, "valid", "\n".join(map(str, result.issues)))
        self.assertEqual(result.release_id, expected_release_id(_valid_root()))

    def test_every_sealed_case_returns_its_named_first_diagnostic(self) -> None:
        for case in self.corpus["cases"]:
            with self.subTest(case=case["name"]):
                bundle = CORPUS_FILE.parent / case["bundle"]
                self.assertEqual(tree_digest(bundle), case["treeSha256"])
                result = verify_document_release(bundle)
                detail = "\n".join(map(str, result.issues))
                self.assertEqual(result.code, case["expectedCode"], detail)
                self.assertEqual(result.path, case["expectedPath"], detail)

    def test_every_declared_diagnostic_code_has_a_sealed_fixture(self) -> None:
        exercised = {case["expectedCode"] for case in self.corpus["cases"]} - {"valid"}
        self.assertEqual(exercised, set(DIAGNOSTIC_CODES))

    def test_the_precedence_list_is_a_total_order(self) -> None:
        self.assertEqual(len(set(DIAGNOSTIC_CODES)), len(DIAGNOSTIC_CODES))
        self.assertEqual(sorted(CODE_PRECEDENCE.values()), list(range(len(DIAGNOSTIC_CODES))))
        # Structure outranks segments: a segment cannot be judged against a
        # parent whose own range is already known to be wrong.
        self.assertLess(CODE_PRECEDENCE["invalid.structure"], CODE_PRECEDENCE["invalid.segment"])
        self.assertLess(
            CODE_PRECEDENCE["invalid.representation"], CODE_PRECEDENCE["invalid.structure"]
        )
        self.assertLess(CODE_PRECEDENCE["invalid.capture"], CODE_PRECEDENCE["invalid.representation"])

    def test_the_sealed_bytes_match_a_clean_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory) / "document-release-v2"
            scratch.mkdir()
            cases = build_corpus(scratch)
            self.assertEqual(canonical_json_bytes({"cases": cases}), CORPUS_FILE.read_bytes())
            self.assertEqual(
                canonical_json_bytes(build_candidate_manifest(cases)),
                CANDIDATE_MANIFEST.read_bytes(),
            )


class CorpusContentTests(unittest.TestCase):
    def test_the_release_projects_every_member_of_the_requested_universe(self) -> None:
        """Corpus membership and exclusion coverage come from this release alone."""

        catalog_items = json.loads(
            (SOURCE_CATALOG_FIXTURE / "data" / "source-items.json").read_text(encoding="utf-8")
        )
        rows = _member("source-dispositions.json")
        self.assertEqual(
            [row["sourceItemId"] for row in rows],
            [item["sourceItemId"] for item in catalog_items],
        )
        self.assertEqual(
            {row["catalogDisposition"] for row in rows}, set(CATALOG_DISPOSITIONS)
        )

    def test_the_root_pins_the_exact_source_catalog_release(self) -> None:
        catalog_root = json.loads(
            (SOURCE_CATALOG_FIXTURE / "release.json").read_text(encoding="utf-8")
        )
        pin = _valid_root()["content"]["sourceCatalog"]
        self.assertEqual(pin["releaseId"], catalog_root["releaseId"])
        self.assertEqual(
            pin["selectedSourceSetDigest"],
            catalog_root["content"]["selectedSourceSetDigest"],
        )
        self.assertEqual(
            pin["requestedUniverseSetDigest"],
            catalog_root["content"]["requestedUniverseSetDigest"],
        )

    def test_the_join_is_one_to_one_and_sealed(self) -> None:
        root = _valid_root()["content"]
        documents = _member("documents.json")
        pairs = [[d["sourceItemId"], d["documentVersionId"]] for d in documents]
        self.assertEqual(root["sourceDocumentMappingDigest"], mapping_digest(pairs))
        self.assertEqual(root["joinReceipt"]["mappingDigest"], mapping_digest(pairs))
        self.assertEqual(len({p[0] for p in pairs}), len(pairs))
        self.assertEqual(len({p[1] for p in pairs}), len(pairs))

    def test_visible_text_is_fully_tiled_by_segments_and_exclusions(self) -> None:
        documents = _member("documents.json")
        segments = _member("search-segments.json")
        coverage = derive_coverage(_member("source-dispositions.json"), documents, segments)
        self.assertEqual(
            coverage["segmentedByteTotal"] + coverage["excludedByteTotal"],
            coverage["representationByteTotal"],
        )
        self.assertEqual(coverage["unaccountedCount"], 0)
        self.assertEqual(coverage["documentsWithSegmentCount"], len(documents))

    def test_markup_is_not_search_text(self) -> None:
        """The representation is extracted visible text; the rendition is markup."""

        for document in _member("documents.json"):
            with self.subTest(document=document["documentVersionId"]):
                representation = (VALID_BUNDLE / document["representation"]["objectKey"]).read_bytes()
                rendition = (VALID_BUNDLE / document["capture"]["objectKey"]).read_bytes()
                self.assertNotIn(b"<", representation)
                self.assertIn(b"<html>", rendition)
                self.assertNotEqual(representation, rendition)

    def test_every_segment_reverses_to_exact_captured_evidence(self) -> None:
        documents = {d["documentVersionId"]: d for d in _member("documents.json")}
        for segment in _member("search-segments.json"):
            with self.subTest(segment=segment["segmentId"]):
                document = documents[segment["documentVersionId"]]
                representation = (VALID_BUNDLE / document["representation"]["objectKey"]).read_bytes()
                rendition = (VALID_BUNDLE / document["capture"]["objectKey"]).read_bytes()
                text = representation[
                    segment["representationStart"] : segment["representationEnd"]
                ]
                evidence = rendition[segment["evidence"]["start"] : segment["evidence"]["end"]]
                self.assertEqual(segment["evidence"]["renditionSha256"], document["capture"]["sha256"])
                # The representation adds the newline the markup expressed as a
                # tag boundary; the evidence is otherwise the same exact bytes.
                self.assertEqual(text.rstrip(b"\n"), evidence)


class CandidateBundleTests(unittest.TestCase):
    def test_the_manifest_recomputes_from_the_bytes_it_pins(self) -> None:
        self.assertEqual(candidate_bundle_errors(), [])

    def test_the_manifest_is_a_closed_rulespec_core_release(self) -> None:
        schema = json.loads(
            (CANDIDATE_MANIFEST.parent / "schemas" / "rulespec-core-release.schema.json").read_text(
                encoding="utf-8"
            )
        )
        record = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(record)
        self.assertEqual(record["release_status"], "candidate")
        self.assertEqual(record["version"], CANDIDATE_VERSION)
        self.assertEqual(bundle_release_id(), record["release_id"])

    def test_the_manifest_pins_six_schemas_two_validators_and_every_fixture(self) -> None:
        record = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
        corpus = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(len(record["schema_artifacts"]), 6)
        self.assertEqual(
            sorted(entry["name"] for entry in record["validator_artifacts"]),
            [
                "src/rulespec_conformance/document_release.py",
                "src/rulespec_conformance/document_validate.py",
            ],
        )
        self.assertEqual(len(record["conformance_fixture_artifacts"]), len(corpus["cases"]))

    def test_the_two_candidates_are_separately_named(self) -> None:
        from tools.source_catalog_release import bundle_release_id as catalog_bundle_id

        self.assertNotEqual(bundle_release_id(), catalog_bundle_id())


class InstalledPackageGateTests(unittest.TestCase):
    def test_every_required_export_exists_today(self) -> None:
        import tools.document_release as module
        from tools.document_validate import REQUIRED_DATA, REQUIRED_EXPORTS

        self.assertEqual([n for n in REQUIRED_EXPORTS if not hasattr(module, n)], [])
        for name in REQUIRED_DATA:
            with self.subTest(data=name):
                self.assertTrue(getattr(module, name).is_file())

    def test_removing_an_export_is_detected(self) -> None:
        import tools.document_validate as gate
        from tools.document_validate import REQUIRED_EXPORTS, check_exports

        class Stripped:
            pass

        stripped = Stripped()
        for name in REQUIRED_EXPORTS[1:]:
            setattr(stripped, name, object())
        original = gate.document_release
        gate.document_release = stripped
        try:
            with self.assertRaises(SystemExit) as caught:
                check_exports()
        finally:
            gate.document_release = original
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
