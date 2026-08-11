"""Conformance tests for the SourceCatalogRelease v1 boundary."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import jsonschema
import rfc8785

from tools.build_source_catalog_release_fixtures import (
    CANDIDATE_VERSION,
    SOURCE_ITEMS,
    VALID_BUNDLE,
    build_candidate_manifest,
    build_corpus,
)
from tools.source_catalog_release import (
    CANDIDATE_MANIFEST,
    CODE_PRECEDENCE,
    CORPUS_FILE,
    DIAGNOSTIC_CODES,
    SCHEMA_FILES,
    SCHEMA_IDS,
    SELECTION_DISPOSITIONS,
    bundle_release_id,
    candidate_bundle_errors,
    canonical_json_bytes,
    canonical_sha256,
    derive_counts,
    derive_coverage,
    expected_release_id,
    load_strict_canonical_json,
    source_set_digest,
    tree_digest,
    verify_source_catalog_release,
)


class SchemaSetTests(unittest.TestCase):
    def test_every_schema_is_a_valid_closed_draft_2020_12_document(self) -> None:
        for role, path in SCHEMA_FILES.items():
            with self.subTest(schema=role):
                schema = json.loads(path.read_text(encoding="utf-8"))
                jsonschema.Draft202012Validator.check_schema(schema)
                self.assertIs(schema["additionalProperties"], False)
                self.assertEqual(schema["$id"], SCHEMA_IDS[role])

    def test_the_disposition_enum_is_exactly_the_five_contract_values(self) -> None:
        schema = json.loads(SCHEMA_FILES["source-items"].read_text(encoding="utf-8"))
        declared = schema["$defs"]["selectionDisposition"]["properties"]["disposition"][
            "enum"
        ]
        self.assertEqual(sorted(declared), sorted(SELECTION_DISPOSITIONS))
        self.assertEqual(
            schema["$defs"]["selectionDisposition"]["required"], ["disposition"]
        )

    def test_a_second_disposition_is_structurally_unrepresentable(self) -> None:
        """The disposition is an object property, not a row in a table.

        A table admits zero rows and two rows and needs a rule against each.
        Modeling it as one required object closes both without a rule.
        """

        schema = json.loads(SCHEMA_FILES["source-items"].read_text(encoding="utf-8"))
        selection = schema["properties"]["selection"]
        self.assertEqual(selection, {"$ref": "#/$defs/selectionDisposition"})
        self.assertEqual(
            schema["$defs"]["selectionDisposition"]["type"], "object"
        )

    def test_a_selected_item_must_carry_the_complete_normalized_field_set(self) -> None:
        schema = json.loads(SCHEMA_FILES["source-items"].read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        selected = json.loads(json.dumps(SOURCE_ITEMS[0]))
        self.assertEqual(list(validator.iter_errors(selected)), [])
        selected["normalizedMetadata"] = None
        self.assertTrue(list(validator.iter_errors(selected)))
        # The same null is legal on the item the source could not describe.
        failed = json.loads(json.dumps(SOURCE_ITEMS[-1]))
        self.assertEqual(failed["selection"]["disposition"], "failed")
        self.assertIsNone(failed["normalizedMetadata"])
        self.assertEqual(list(validator.iter_errors(failed)), [])

    def test_every_normalized_mvp_field_is_declared_and_required(self) -> None:
        schema = json.loads(SCHEMA_FILES["source-items"].read_text(encoding="utf-8"))
        normalized = schema["$defs"]["normalizedMetadata"]
        self.assertEqual(
            sorted(normalized["required"]),
            [
                "agencies",
                "commentCloseDate",
                "docketIds",
                "documentType",
                "language",
                "lastUpdatedDate",
                "publicationDate",
                "regulationIdentifierNumbers",
                "sourceUrl",
                "title",
            ],
        )
        self.assertEqual(
            sorted(normalized["properties"]), sorted(normalized["required"])
        )
        self.assertIs(normalized["additionalProperties"], False)


class CanonicalBytesTests(unittest.TestCase):
    def test_the_stdlib_encoder_agrees_with_rfc_8785_on_the_safe_domain(self) -> None:
        """The wheel ships no canonicalizer; this is why it does not need one."""

        for path in (CORPUS_FILE, CANDIDATE_MANIFEST, VALID_BUNDLE / "release.json"):
            with self.subTest(document=path.name):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(canonical_json_bytes(value), rfc8785.dumps(value))
        self.assertEqual(
            canonical_sha256({"z": [3, True, None], "a": "é"}),
            hashlib.sha256(rfc8785.dumps({"z": [3, True, None], "a": "é"})).hexdigest(),
        )

    def test_the_loader_rejects_duplicate_float_bom_and_noncanonical_bytes(self) -> None:
        cases = {
            "duplicate": b'{"a":1,"a":2}',
            "float": b'{"a":1.5}',
            "bom": b"\xef\xbb\xbf{\"a\":1}",
            "noncanonical": b'{"b":2, "a":1}\n',
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, raw in cases.items():
                with self.subTest(case=name):
                    path = Path(directory) / f"{name}.json"
                    path.write_bytes(raw)
                    with self.assertRaises((ValueError, json.JSONDecodeError)):
                        load_strict_canonical_json(path)

    def test_a_set_digest_ignores_order_and_repetition(self) -> None:
        self.assertEqual(source_set_digest(["b", "a"]), source_set_digest(["a", "b"]))
        self.assertEqual(
            source_set_digest(["a", "a", "b"]), source_set_digest(["a", "b"])
        )
        self.assertNotEqual(source_set_digest(["a"]), source_set_digest(["a", "b"]))


class DiagnosticOrderTests(unittest.TestCase):
    def test_the_precedence_list_is_a_total_order_over_the_declared_codes(self) -> None:
        self.assertEqual(len(set(DIAGNOSTIC_CODES)), len(DIAGNOSTIC_CODES))
        self.assertEqual(sorted(CODE_PRECEDENCE.values()), list(range(len(DIAGNOSTIC_CODES))))

    def test_an_unsafe_path_outranks_every_membership_claim_about_it(self) -> None:
        """The one deliberate departure from the ExtrapolationRelease v2 order."""

        self.assertLess(
            CODE_PRECEDENCE["invalid.path"],
            CODE_PRECEDENCE["invalid.membership-missing"],
        )
        self.assertLess(
            CODE_PRECEDENCE["invalid.path"],
            CODE_PRECEDENCE["invalid.membership-extra"],
        )


class SealedCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))

    def test_the_valid_fixture_verifies_and_names_itself_by_content(self) -> None:
        result = verify_source_catalog_release(VALID_BUNDLE)
        self.assertEqual(result.code, "valid", "\n".join(map(str, result.issues)))
        root = json.loads((VALID_BUNDLE / "release.json").read_text(encoding="utf-8"))
        self.assertEqual(result.release_id, expected_release_id(root))

    def test_an_annotation_does_not_rename_a_release(self) -> None:
        root = json.loads((VALID_BUNDLE / "release.json").read_text(encoding="utf-8"))
        original = root["releaseId"]
        root["annotations"]["operatorNote"] = "identity-neutral"
        self.assertEqual(expected_release_id(root), original)

    def test_the_valid_fixture_exercises_all_five_dispositions(self) -> None:
        items = json.loads(
            (VALID_BUNDLE / "data" / "source-items.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            {item["selection"]["disposition"] for item in items},
            set(SELECTION_DISPOSITIONS),
        )
        counts = derive_counts(items, member_count=4, total_member_byte_size=0)
        self.assertEqual(counts["discoveredCount"], len(items))
        self.assertEqual(derive_coverage(items)["unaccountedCount"], 0)

    def test_every_sealed_case_returns_its_named_first_diagnostic(self) -> None:
        for case in self.corpus["cases"]:
            with self.subTest(case=case["name"]):
                bundle = CORPUS_FILE.parent / case["bundle"]
                self.assertEqual(tree_digest(bundle), case["treeSha256"])
                result = verify_source_catalog_release(bundle)
                detail = "\n".join(map(str, result.issues))
                self.assertEqual(result.code, case["expectedCode"], detail)
                self.assertEqual(result.path, case["expectedPath"], detail)

    def test_every_declared_diagnostic_code_has_a_sealed_fixture(self) -> None:
        """A code with no fixture is a claim, not a gate."""

        exercised = {case["expectedCode"] for case in self.corpus["cases"]} - {"valid"}
        self.assertEqual(exercised, set(DIAGNOSTIC_CODES))

    def test_each_invalid_case_departs_from_the_valid_bundle(self) -> None:
        valid = tree_digest(VALID_BUNDLE)
        digests = {case["name"]: case["treeSha256"] for case in self.corpus["cases"]}
        self.assertEqual(digests.pop("valid"), valid)
        for name, digest in digests.items():
            with self.subTest(case=name):
                self.assertNotEqual(digest, valid)
        self.assertEqual(len(set(digests.values())), len(digests))

    def test_the_sealed_bytes_match_a_clean_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory) / "source-catalog-release-v1"
            scratch.mkdir()
            cases = build_corpus(scratch)
            self.assertEqual(
                canonical_json_bytes({"cases": cases}), CORPUS_FILE.read_bytes()
            )
            self.assertEqual(
                canonical_json_bytes(build_candidate_manifest(cases)),
                CANDIDATE_MANIFEST.read_bytes(),
            )


class CandidateBundleTests(unittest.TestCase):
    def test_the_manifest_recomputes_from_the_bytes_it_pins(self) -> None:
        self.assertEqual(candidate_bundle_errors(), [])

    def test_the_manifest_is_a_closed_rulespec_core_release(self) -> None:
        schema = json.loads(
            (
                CANDIDATE_MANIFEST.parent / "schemas" / "rulespec-core-release.schema.json"
            ).read_text(encoding="utf-8")
        )
        record = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(schema).validate(record)
        self.assertEqual(record["release_status"], "candidate")
        self.assertEqual(record["version"], CANDIDATE_VERSION)
        self.assertEqual(
            record["release_id"],
            "urn:rulespec:core:" + record["release_digest"].removeprefix("sha256:"),
        )

    def test_the_manifest_pins_every_schema_the_validator_and_every_fixture(self) -> None:
        record = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
        corpus = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(entry["name"] for entry in record["schema_artifacts"]),
            sorted(
                path.relative_to(Path(__file__).resolve().parents[1]).as_posix()
                for path in SCHEMA_FILES.values()
            ),
        )
        self.assertEqual(
            len(record["conformance_fixture_artifacts"]), len(corpus["cases"])
        )
        self.assertEqual(
            [entry["artifact_digest"] for entry in record["conformance_fixture_artifacts"]],
            ["sha256:" + case["treeSha256"] for case in corpus["cases"]],
        )

    def test_the_manifest_pins_both_validator_modules(self) -> None:
        record = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(
            sorted(entry["name"] for entry in record["validator_artifacts"]),
            [
                "src/rulespec_conformance/source_catalog_release.py",
                "src/rulespec_conformance/source_catalog_validate.py",
            ],
        )

    def test_a_changed_fixture_byte_breaks_the_bundle_digest(self) -> None:
        """Immutability is checked, not asserted: any edit starts a new candidate."""

        record = json.loads(CANDIDATE_MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(bundle_release_id(), record["release_id"])
        mutated = json.loads(json.dumps(record))
        mutated["conformance_fixture_artifacts"][0]["artifact_digest"] = (
            "sha256:" + "0" * 64
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.json"
            path.write_bytes(canonical_json_bytes(mutated))
            errors = candidate_bundle_errors(path)
        self.assertTrue(any("expected sha256:" + "0" * 64 in e for e in errors))
        self.assertTrue(any(e.startswith("release_digest:") for e in errors))


class InstalledPackageGateTests(unittest.TestCase):
    """The gate the installed wheel runs. It must fail red, never skip."""

    def test_every_required_export_exists_today(self) -> None:
        import tools.source_catalog_release as module
        from tools.source_catalog_validate import REQUIRED_DATA, REQUIRED_EXPORTS

        missing = [name for name in REQUIRED_EXPORTS if not hasattr(module, name)]
        self.assertEqual(missing, [])
        for name in REQUIRED_DATA:
            with self.subTest(data=name):
                self.assertTrue(getattr(module, name).is_file())

    def test_the_required_export_list_covers_the_public_surface(self) -> None:
        """A name a consumer may import but the gate does not check is untested."""

        import tools.source_catalog_release as module
        from tools.source_catalog_validate import REQUIRED_EXPORTS

        unchecked = set(module.__all__) - set(REQUIRED_EXPORTS)
        self.assertEqual(
            unchecked,
            {
                # Byte-level helpers a consumer may use but whose absence the
                # corpus replay would already report.
                "BUNDLE_TREE_MEDIA_TYPE",
                "SCHEMA_FILES",
                "VALIDATOR_MEDIA_TYPE",
                "canonical_json_bytes",
                "file_sha256",
                "load_strict_canonical_json",
                "write_canonical_json",
            },
        )

    def test_removing_an_export_is_detected(self) -> None:
        from tools.source_catalog_validate import REQUIRED_EXPORTS, check_exports

        class Stripped:
            pass

        stripped = Stripped()
        for name in REQUIRED_EXPORTS[1:]:
            setattr(stripped, name, object())
        import tools.source_catalog_validate as gate

        original = gate.source_catalog_release
        gate.source_catalog_release = stripped
        try:
            with self.assertRaises(SystemExit) as caught:
                check_exports()
        finally:
            gate.source_catalog_release = original
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
