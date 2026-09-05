"""Parity with the producer this package was moved from.

Every expectation here is read from ``fixtures/*.json``, which were produced by
running spicy-regs ``docpipeline/rkaf_projection.py`` at ``8d9e7a2`` (see each
file's ``derived_from``). The port never computes its own expected value: the
same inputs go in, and the document, run record, transcript, facts, judgments,
rejections, fragments, and citation IRIs that come out must equal what the
original produced, byte for byte after JSON normalization.
"""

from __future__ import annotations

import dataclasses
import json
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import rulespec_projection as rp
from rulespec_projection import citations, evidence

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def plain(value: Any) -> Any:
    """The same JSON normalization the fixture generator applied."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return plain(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, Path):
        return str(value)
    return value


@dataclasses.dataclass(frozen=True)
class FixtureArtifact:
    """The six attributes :class:`rulespec_projection.SourceArtifact` names."""

    artifact_id: str
    content_sha256: str
    subject_id: str
    profile_id: str
    raw_fields: Mapping[str, str]
    field_sha256: Mapping[str, str]


def artifact_from(fixture: dict[str, Any]) -> FixtureArtifact:
    return FixtureArtifact(**fixture["artifact"])


def settings_from(fixture: dict[str, Any], **override: Any) -> rp.ProjectionSettings:
    fields = dict(fixture["settings"])
    fields["corpus_dir"] = Path(fields["corpus_dir"])
    fields["tables_dir"] = Path(fields["tables_dir"])
    fields.update(override)
    return rp.ProjectionSettings(**fields)


def result_as_plain(result: rp.ProjectionResult) -> dict[str, Any]:
    return {"document": result.document, "run_record": plain(result.run_record), "transcript": result.transcript}


class SourceArtifactContractTests(unittest.TestCase):
    def test_the_fixture_artifact_satisfies_the_declared_protocol(self) -> None:
        artifact = artifact_from(load("federal_register_document.json"))
        self.assertIsInstance(artifact, rp.SourceArtifact)


class FederalRegisterParityTests(unittest.TestCase):
    def assert_projection_matches(self, name: str) -> None:
        fixture = load(name)
        artifact = artifact_from(fixture)
        tables = rp.InMemoryTables(fixture["tables"])
        settings = settings_from(fixture)
        facts = rp.federal_register_facts(artifact, fixture["row"], tables=tables, partner=settings.partner)
        self.assertEqual(plain(facts), fixture["facts"])
        result = rp.assemble(artifact, facts, settings=settings, model_layer=None)
        self.assertEqual(result_as_plain(result), fixture["result"])

    def test_the_document_with_published_tables(self) -> None:
        self.assert_projection_matches("federal_register_document.json")

    def test_the_document_with_no_published_tables(self) -> None:
        self.assert_projection_matches("federal_register_document_no_tables.json")


class UnifiedAgendaParityTests(unittest.TestCase):
    def test_the_observation(self) -> None:
        fixture = load("unified_agenda_observation.json")
        artifact = artifact_from(fixture)
        tables = rp.InMemoryTables(fixture["tables"])
        settings = settings_from(fixture)
        facts = rp.unified_agenda_facts(artifact, fixture["row"], tables=tables, partner=settings.partner)
        self.assertEqual(plain(facts), fixture["facts"])
        result = rp.assemble(artifact, facts, settings=settings, model_layer=None)
        self.assertEqual(result_as_plain(result), fixture["result"])


class ModelLayerParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = load("model_layer.json")
        self.artifact = artifact_from(self.fixture)
        self.vocabulary = {
            key: rp.VocabularyConcept(**value) for key, value in self.fixture["vocabulary_concepts"].items()
        }

    def verify(self, rows: list[dict[str, Any]], **kwargs: Any) -> tuple[list[rp.ConceptJudgment], list[dict[str, Any]]]:
        return rp.verify_candidate_rows(
            self.artifact,
            rows,
            artifact_iri=self.fixture["artifact_iri"],
            evidence_field=self.fixture["evidence_field"],
            **kwargs,
        )

    def test_candidate_rows_verify_to_the_same_judgments_and_rejections(self) -> None:
        judgments, rejections = self.verify(
            self.fixture["candidate_rows"],
            vocabulary_concepts=self.vocabulary,
            allowed_assignment_role_iris=self.fixture["allowed_assignment_role_iris"],
        )
        self.assertEqual(plain(judgments), self.fixture["judgments"])
        self.assertEqual(plain(rejections), self.fixture["rejections"])

    def test_the_compatibility_branch_without_a_vocabulary(self) -> None:
        judgments, rejections = self.verify(self.fixture["bare_candidate_rows"])
        self.assertEqual(plain(judgments), self.fixture["bare_judgments"])
        self.assertEqual(plain(rejections), self.fixture["bare_rejections"])

    def test_the_assembled_document_with_a_model_layer(self) -> None:
        judgments, rejections = self.verify(
            self.fixture["candidate_rows"],
            vocabulary_concepts=self.vocabulary,
            allowed_assignment_role_iris=self.fixture["allowed_assignment_role_iris"],
        )
        fields = dict(self.fixture["model_layer"])
        fields["vocabulary_nodes"] = tuple(fields["vocabulary_nodes"])
        fields["candidate_selection_ledger"] = tuple(fields["candidate_selection_ledger"])
        model_layer = rp.ModelLayer(
            **fields,
            vocabulary_concepts=self.vocabulary,
            judgments=tuple(judgments),
            rejections=tuple(rejections),
        )
        tables = rp.InMemoryTables(self.fixture["tables"])
        settings = settings_from(self.fixture, attestor_id="")
        facts = rp.federal_register_facts(self.artifact, load("federal_register_document.json")["row"], tables=tables, partner=settings.partner)
        result = rp.assemble(self.artifact, facts, settings=settings, model_layer=model_layer)
        self.assertEqual(result_as_plain(result), self.fixture["result"])


class FragmentParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = load("fragments.json")
        self.artifact = artifact_from(self.fixture)

    def test_verify_fragment_cases(self) -> None:
        for case in self.fixture["verify_fragment"]:
            with self.subTest(case=case["name"]):
                try:
                    fragment = rp.verify_fragment(
                        self.artifact, key=case["name"], artifact_iri=self.fixture["artifact_iri"], **case["args"]
                    )
                except rp.OffsetVerificationError as error:
                    self.assertIsNone(case["fragment"])
                    self.assertEqual(str(error), case["error"])
                else:
                    self.assertIsNone(case["error"])
                    self.assertEqual(plain(fragment), case["fragment"])

    def test_ground_literal_cases(self) -> None:
        for case in self.fixture["ground_literal"]:
            with self.subTest(forms=case["surface_forms"]):
                fragment = rp.ground_literal(
                    self.artifact,
                    key="ground",
                    source_field=self.fixture["evidence_field"] if "evidence_field" in self.fixture else "federal_register.body_html",
                    artifact_iri=self.fixture["artifact_iri"],
                    surface_forms=case["surface_forms"],
                )
                self.assertEqual(plain(fragment), case["fragment"])

    def test_encode_for_uri(self) -> None:
        for value, expected in self.fixture["encode_for_uri"].items():
            with self.subTest(value=value):
                self.assertEqual(rp.encode_for_uri(value), expected)

    def test_resolve_exact_evidence_offsets(self) -> None:
        text = self.artifact.raw_fields["federal_register.body_html"]
        for case in self.fixture["resolve_exact_evidence_offsets"]:
            with self.subTest(quote=case["quote"]):
                resolution = evidence.resolve_exact_evidence_offsets(text, case["quote"], None, None)
                self.assertEqual(plain(resolution), case["resolution"])


class CitationParityTests(unittest.TestCase):
    def test_every_recorded_call(self) -> None:
        fixture = load("citations.json")
        for name in (
            "canonical_cfr_iri",
            "canonical_usc_iri",
            "canonical_pl_iri",
            "canonical_rin_iri",
            "canonical_regsgov_iri",
            "docket_reference_as_stated",
            "normalize_docket_reference",
            "federal_register_identifier",
            "parse_cfr_citation",
            "parse_authority_citation",
        ):
            function = getattr(citations, name)
            for case in fixture[name]:
                with self.subTest(function=name, args=case["args"]):
                    try:
                        value = function(*case["args"])
                    except Exception as error:  # noqa: BLE001 - the fixture records the type and message
                        self.assertIsNone(case["value"])
                        self.assertEqual(f"{type(error).__name__}: {error}", case["error"])
                    else:
                        self.assertIsNone(case["error"])
                        self.assertEqual(plain(value), case["value"])


if __name__ == "__main__":
    unittest.main()
