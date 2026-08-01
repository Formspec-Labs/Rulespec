"""Drive the reader over RefSpec's vendored atlas conformance corpus.

`release-records/fixtures/upstream/refspec-atlas-conformance/` holds a
byte-for-byte copy of the corpus RefSpec publishes at
`bindings/atlas/1.0/fixtures/`. Rulespec pins and validates that copy; it does
not own its contents. `CORPUS_DIGEST` is the noted digest of the vendored
`corpus.json`, and every case in that file carries the digests of the two
distribution files it selects, so a silently edited fixture fails here before
it can weaken a verdict.

Refresh the copy from a RefSpec checkout with:

    python3 tools/vendor_refspec_atlas_conformance.py /path/to/RefSpec
"""

from __future__ import annotations

import json
import re
import unittest
from typing import Any

from tools.refspec_atlas import AtlasIntegrityError, RefSpecVocabularyAtlas
from tools.rulespec_release import content_digest
from tools.vendor_refspec_atlas_conformance import (
    CASE_FILES,
    SCHEMA_VERSION as CORPUS_SCHEMA_VERSION,
    VENDORED_ROOT as CORPUS_ROOT,
)

CORPUS_PATH = CORPUS_ROOT / "corpus.json"
CORPUS_DIGEST = (
    "sha256:16468566593c73def688e35c5c1086b39bb6f76d1b3a981f57ba2fba86ed2e13"
)

# The exact published case set. A corpus that drops a case, renames one, or
# flips a verdict must fail this module rather than quietly shrink the gate.
PUBLISHED_CASES = {
    "minimal-valid-distribution": True,
    "analysis-membership-must-match-release-facts": False,
    "search-only-eligibility-has-exact-cardinality": False,
    "search-only-requires-exactly-two-machines": False,
    "search-only-requires-distinct-provider-models": False,
    "implementation-paths-are-unique": False,
    "nquads-lines-are-canonical": False,
}

# Cases this reader deliberately does not reject, with the reason. Empty today:
# every published invalid case fails closed. A case listed here is an explicit,
# documented strictness delta, not an oversight.
STRICTNESS_DELTAS: dict[str, str] = {}


def load_corpus() -> list[dict[str, Any]]:
    """Return the vendored corpus cases after checking the noted digest."""

    payload = CORPUS_PATH.read_bytes()
    if content_digest(payload) != CORPUS_DIGEST:
        raise AssertionError(
            "vendored corpus.json differs from the noted digest; re-vendor it"
        )
    corpus = json.loads(payload.decode("utf-8"))
    return list(corpus["cases"])


def _open(case: dict[str, Any]) -> RefSpecVocabularyAtlas:
    return RefSpecVocabularyAtlas.open(
        CORPUS_ROOT / case["directory"],
        expected_manifest_digest=case["manifestDigest"],
        expected_output_digest=case["outputDigest"],
    )


class VendoredCorpusIntegrityTests(unittest.TestCase):
    """The vendored copy must still be the corpus RefSpec published."""

    def setUp(self) -> None:
        self.cases = load_corpus()

    def test_corpus_declares_the_supported_schema_version(self) -> None:
        corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        self.assertEqual(corpus["schemaVersion"], CORPUS_SCHEMA_VERSION)

    def test_vendored_case_set_matches_the_published_case_set(self) -> None:
        self.assertEqual(
            {case["id"]: bool(case["valid"]) for case in self.cases},
            PUBLISHED_CASES,
        )

    def test_every_vendored_file_matches_its_noted_digest(self) -> None:
        for case in self.cases:
            directory = CORPUS_ROOT / case["directory"]
            expected = (case["manifestDigest"], case["outputDigest"])
            for name, digest in zip(CASE_FILES, expected, strict=True):
                with self.subTest(case=case["id"], file=name):
                    self.assertEqual(
                        content_digest((directory / name).read_bytes()), digest
                    )

    def test_no_vendored_case_directory_is_unreferenced(self) -> None:
        referenced = {
            (CORPUS_ROOT / case["directory"]).resolve() for case in self.cases
        }
        observed = {
            path.parent.resolve() for path in CORPUS_ROOT.rglob("atlas-manifest.json")
        }
        self.assertEqual(observed, referenced)


class RefSpecAtlasConformanceTests(unittest.TestCase):
    """Every published case drives `RefSpecVocabularyAtlas.open` offline."""

    def setUp(self) -> None:
        self.cases = load_corpus()

    def test_valid_cases_open(self) -> None:
        valid = [case for case in self.cases if case["valid"]]
        self.assertTrue(valid)
        for case in valid:
            with self.subTest(case=case["id"]):
                atlas = _open(case)
                self.assertEqual(atlas.manifest_digest, case["manifestDigest"])
                self.assertEqual(atlas.output_digest, case["outputDigest"])
                self.assertEqual(
                    atlas.pin()["distribution_digest"], atlas.output_digest
                )

    def test_invalid_cases_fail_closed(self) -> None:
        invalid = [
            case
            for case in self.cases
            if not case["valid"] and case["id"] not in STRICTNESS_DELTAS
        ]
        self.assertTrue(invalid)
        for case in invalid:
            with self.subTest(case=case["id"]):
                with self.assertRaisesRegex(
                    AtlasIntegrityError, re.escape(case["errorContains"])
                ):
                    _open(case)

    def test_documented_strictness_deltas_still_hold(self) -> None:
        for case in self.cases:
            if case["id"] not in STRICTNESS_DELTAS:
                continue
            with self.subTest(case=case["id"]):
                # Asserting the accepting behavior on purpose: this reader does
                # not own the check, and the delta is documented above.
                _open(case)


class SearchOnlyMappingBoundaryTests(unittest.TestCase):
    """Named regressions for the three checks the corpus exposed as missing."""

    def _case(self, case_id: str) -> dict[str, Any]:
        for case in load_corpus():
            if case["id"] == case_id:
                return case
        raise AssertionError(f"corpus is missing case {case_id}")

    def test_mapping_eligibility_has_exact_cardinality(self) -> None:
        with self.assertRaisesRegex(AtlasIntegrityError, "mapping eligibility"):
            _open(self._case("search-only-eligibility-has-exact-cardinality"))

    def test_search_only_mapping_requires_exactly_two_machines(self) -> None:
        with self.assertRaisesRegex(
            AtlasIntegrityError, "exactly two machine validations"
        ):
            _open(self._case("search-only-requires-exactly-two-machines"))

    def test_search_only_mapping_requires_distinct_provider_models(self) -> None:
        with self.assertRaisesRegex(
            AtlasIntegrityError, "validations are not independent"
        ):
            _open(self._case("search-only-requires-distinct-provider-models"))


if __name__ == "__main__":
    unittest.main()
