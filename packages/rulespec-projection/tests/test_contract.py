"""Contract behaviors the producer's own tests enforced, carried at the same names.

These are the promises a consumer checks with a hash, restated from spicy-regs
``tests/test_docpipeline_rkaf_projection.py`` at ``8d9e7a2`` without the
Parquet, DuckDB, RefSpec, and provider machinery those tests ran through. Each
one asserts a property of the contract (an abort, a refusal, a grammar), not an
equality between the port and itself; byte parity with the producer lives in
``test_parity.py``.
"""

from __future__ import annotations

import dataclasses
import json
import re
import unittest
from collections.abc import Mapping
from pathlib import Path

import rulespec_projection as rp

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@dataclasses.dataclass(frozen=True)
class Artifact:
    artifact_id: str
    content_sha256: str
    subject_id: str
    profile_id: str
    raw_fields: Mapping[str, str]
    field_sha256: Mapping[str, str]


def fixture_artifact() -> tuple[Artifact, dict, dict]:
    fixture = json.loads((FIXTURES / "federal_register_document.json").read_text(encoding="utf-8"))
    return Artifact(**fixture["artifact"]), fixture["row"], fixture


def settings(**override: object) -> rp.ProjectionSettings:
    fields: dict = dict(
        corpus_dir=Path("corpus"),
        tables_dir=Path("tables"),
        rulespec_version="0.0.0-test",
        rulespec_constraint_digest="sha256:" + "a" * 64,
        rulespec_source_revision=None,
        asserted_at="2026-07-28T00:00:00Z",
    )
    fields.update(override)
    return rp.ProjectionSettings(**fields)


class SettingsTests(unittest.TestCase):
    def test_projection_settings_require_an_honest_rulespec_reference(self) -> None:
        with self.assertRaises(rp.ProjectionError):
            settings(rulespec_version="latest")
        with self.assertRaises(rp.ProjectionError):
            settings(rulespec_constraint_digest="a" * 64)
        with self.assertRaises(rp.ProjectionError):
            settings(rulespec_source_revision="main")
        self.assertIsNone(settings().rulespec_source_revision)
        self.assertEqual(settings(rulespec_source_revision="f" * 40).rulespec_source_revision, "f" * 40)


class FragmentTests(unittest.TestCase):
    def test_the_minted_urn_satisfies_the_core_4_2_grammar(self) -> None:
        urn = rp.fragment_urn("https://www.federalregister.gov/d/2026-00001", 10, 20, "0" * 64)
        self.assertRegex(urn, rp.FRAGMENT_URN_PATTERN)
        self.assertIn("https%3A%2F%2Fwww.federalregister.gov%2Fd%2F2026-00001", urn)

    def test_offsets_outside_the_stored_field_abort(self) -> None:
        artifact, _, _ = fixture_artifact()
        for start, end in ((5, 4), (-1, 3), (0, 10**6)):
            with self.subTest(start=start, end=end), self.assertRaises(rp.OffsetVerificationError):
                rp.verify_fragment(
                    artifact, key="k", source_field="federal_register.body_html", start=start, end=end, artifact_iri="urn:x"
                )

    def test_a_drifted_offset_aborts_instead_of_being_repaired(self) -> None:
        artifact, _, _ = fixture_artifact()
        text = artifact.raw_fields["federal_register.body_html"]
        start = text.index("poultry slaughter")
        with self.assertRaises(rp.OffsetVerificationError):
            rp.verify_fragment(
                artifact,
                key="k",
                source_field="federal_register.body_html",
                start=start,
                end=start + len("poultry slaughter") + 1,
                artifact_iri="urn:x",
                expected_text="poultry slaughter",
            )

    def test_the_fragment_digest_is_recomputed_not_carried(self) -> None:
        artifact, _, _ = fixture_artifact()
        text = artifact.raw_fields["federal_register.body_html"]
        start = text.index("poultry slaughter")
        fragment = rp.verify_fragment(
            artifact,
            key="k",
            source_field="federal_register.body_html",
            start=start,
            end=start + len("poultry slaughter"),
            artifact_iri="urn:x",
        )
        self.assertEqual(fragment.text_sha256, rp.text_digest("poultry slaughter"))
        self.assertTrue(fragment.urn.endswith(f"sha256-{fragment.text_sha256}"))

    def test_a_citation_with_two_occurrences_is_not_grounded(self) -> None:
        artifact, _, _ = fixture_artifact()
        self.assertIsNone(
            rp.ground_literal(
                artifact,
                key="k",
                source_field="federal_register.body_html",
                artifact_iri="urn:x",
                surface_forms=("inspection",),
            )
        )


class AssemblyTests(unittest.TestCase):
    def test_a_deterministic_assertion_that_cannot_name_its_activity_aborts(self) -> None:
        artifact, row, fixture = fixture_artifact()
        tables = rp.InMemoryTables(fixture["tables"])
        facts = rp.federal_register_facts(artifact, row, tables=tables, partner=settings().partner)
        orphaned = dataclasses.replace(facts, activities=())
        with self.assertRaises(rp.ProjectionError):
            rp.assemble(artifact, orphaned, settings=settings(), model_layer=None)

    def test_an_absent_evidence_field_refuses_rather_than_guessing(self) -> None:
        artifact, row, fixture = fixture_artifact()
        tables = rp.InMemoryTables(fixture["tables"])
        facts = rp.federal_register_facts(artifact, row, tables=tables, partner=settings().partner)
        with self.assertRaises(rp.ProjectionError):
            rp.assemble(artifact, dataclasses.replace(facts, evidence_field="federal_register.nope"), settings=settings())

    def test_every_emitted_fragment_urn_is_reachable_from_the_stored_text(self) -> None:
        artifact, row, fixture = fixture_artifact()
        tables = rp.InMemoryTables(fixture["tables"])
        facts = rp.federal_register_facts(artifact, row, tables=tables, partner=settings().partner)
        result = rp.assemble(artifact, facts, settings=settings())
        text = artifact.raw_fields[facts.evidence_field]
        urns = [node["@id"] for node in result.document["@graph"] if node.get("@type") == "rkaf:SourceFragment"]
        self.assertTrue(urns)
        for urn in urns:
            match = re.fullmatch(r"urn:rkaf:fragment:(?P<artifact>.+):(?P<start>\d+):(?P<end>\d+):sha256-(?P<digest>[0-9a-f]{64})", urn)
            assert match is not None, urn
            start, end = int(match["start"]), int(match["end"])
            self.assertEqual(rp.text_digest(text[start:end]), match["digest"])
            self.assertEqual(match["artifact"], rp.encode_for_uri(facts.artifact_iri))

    def test_a_docket_only_the_document_claims_is_never_minted(self) -> None:
        artifact, row, fixture = fixture_artifact()
        tables = rp.InMemoryTables({name: rows for name, rows in fixture["tables"].items() if name != "dockets"})
        facts = rp.federal_register_facts(artifact, row, tables=tables, partner=settings().partner)
        docket_ids = {node["@id"] for node in facts.extra_nodes if node.get("@type") == "rkaf:Docket"}
        self.assertNotIn("urn:rkaf:us:regsgov:TEST-2026-0002", docket_ids)
        self.assertTrue(any("TEST-2026-0002" in note for note in facts.notes))

    def test_the_model_attests_production_and_never_approval(self) -> None:
        self.assertEqual(rp.MODEL_ATTESTATION_DECISION, rp.DECISION_ENDORSED_FOR_REVIEW)
        self.assertNotEqual(rp.MODEL_ATTESTATION_DECISION, "rkaf:approved")

    def test_two_runs_of_the_deterministic_layer_agree_byte_for_byte(self) -> None:
        artifact, row, fixture = fixture_artifact()
        tables = rp.InMemoryTables(fixture["tables"])
        first = rp.assemble(artifact, rp.federal_register_facts(artifact, row, tables=tables, partner="urn:p"), settings=settings(partner="urn:p"))
        second = rp.assemble(artifact, rp.federal_register_facts(artifact, row, tables=tables, partner="urn:p"), settings=settings(partner="urn:p"))
        self.assertEqual(
            json.dumps(first.document, sort_keys=True) + json.dumps(first.run_record, sort_keys=True),
            json.dumps(second.document, sort_keys=True) + json.dumps(second.run_record, sort_keys=True),
        )


class TableSourceTests(unittest.TestCase):
    def test_in_memory_tables_apply_the_projection_cleaning_on_both_sides(self) -> None:
        tables = rp.InMemoryTables({"t": [{"a": " x ", "b": None}, {"a": "None", "b": "1"}, {"a": "x", "b": "nan"}]})
        self.assertEqual(len(tables.rows("t", a="x")), 2)
        self.assertEqual(len(tables.rows("t", b="")), 2)
        self.assertEqual(len(tables.rows("t", a="", b="1")), 1)
        self.assertEqual(tables.rows("missing"), [])


if __name__ == "__main__":
    unittest.main()
