from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

from tools.l0_mapping_audit import (
    ROOT,
    audit_mapping_text,
    audit_partner,
    load_vocabulary_registry,
)

RKAF = "https://rulespec.org/ns/v1#"
CONFORMANCE_SPEC = ROOT / "spec" / "rkaf-conformance.md"


class L0MappingAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_vocabulary_registry()

    def mapping_markdown(
        self,
        mappings: list[dict[str, Any]],
        *,
        version: str | None = None,
    ) -> str:
        payload = {
            "rulespec_version": version or self.registry.contract_version,
            "mappings": mappings,
        }
        return (
            "```yaml rkaf-l0-mapping\n"
            f"{yaml.safe_dump(payload, sort_keys=False).rstrip()}\n"
            "```\n"
        )

    @staticmethod
    def stage_mapping() -> dict[str, Any]:
        return {
            "table": "proceedings",
            "column": "stage",
            "subject_type": f"{RKAF}Proceeding",
            "term": f"{RKAF}proceedingStage",
            "direction": "forward",
            "value_kind": "vocab",
            "enum_map": {
                "proposed": f"{RKAF}proceedingProposed",
                "final": f"{RKAF}proceedingFinal",
            },
        }

    def test_valid_mapping_checks_domain_kind_enum_and_identifier_sample(self) -> None:
        identifier = {
            "table": "regulatory_agenda_items",
            "column": "rin",
            "subject_type": f"{RKAF}RegulatoryAgendaItem",
            "term": f"{RKAF}hasAgendaItemIdentifier",
            "direction": "forward",
            "value_kind": "iri",
            "transform": {
                "template": "urn:rkaf:us:rin:{rin}",
                "identifier_scheme": f"{RKAF}us-rin",
            },
            "samples": [
                {
                    "input": {"rin": "2060-AV16"},
                    "output": "urn:rkaf:us:rin:2060-AV16",
                }
            ],
        }
        result = audit_mapping_text(
            self.mapping_markdown([self.stage_mapping(), identifier]),
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())
        self.assertEqual(result.blocks, 1)
        self.assertEqual(result.entries, 2)
        self.assertEqual(result.versions, {self.registry.contract_version})

    def test_artifact_identifier_accepts_declared_scheme(self) -> None:
        mapping = {
            "table": "documents",
            "column": "document_id",
            "subject_type": f"{RKAF}Artifact",
            "term": f"{RKAF}hasArtifactIdentifier",
            "direction": "forward",
            "value_kind": "iri",
            "transform": {
                "template": "https://www.regulations.gov/document/{document_id}",
                "identifier_scheme": f"{RKAF}urn-persistent",
            },
            "samples": [
                {
                    "input": {"document_id": "EPA-HQ-OAR-2021-0317-0001"},
                    "output": (
                        "https://www.regulations.gov/document/"
                        "EPA-HQ-OAR-2021-0317-0001"
                    ),
                }
            ],
        }
        result = audit_mapping_text(
            self.mapping_markdown([mapping]),
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())

    def test_same_column_may_project_distinct_predicates(self) -> None:
        artifact_identity = {
            "table": "documents",
            "column": "document_id",
            "subject_type": f"{RKAF}Artifact",
            "term": f"{RKAF}hasArtifactIdentifier",
            "direction": "forward",
            "value_kind": "iri",
            "transform": {
                "template": "https://www.regulations.gov/document/{document_id}",
                "identifier_scheme": f"{RKAF}urn-persistent",
            },
            "samples": [
                {
                    "input": {"document_id": "EPA-HQ-OAR-2021-0317-0001"},
                    "output": (
                        "https://www.regulations.gov/document/"
                        "EPA-HQ-OAR-2021-0317-0001"
                    ),
                }
            ],
        }
        regulatory_identity = {
            **artifact_identity,
            "term": f"{RKAF}hasRegulatoryIdentifier",
            "transform": {
                "template": "urn:rkaf:us:regsgov:{document_id}",
                "identifier_scheme": f"{RKAF}us-regsgov",
            },
            "samples": [
                {
                    "input": {"document_id": "EPA-HQ-OAR-2021-0317-0001"},
                    "output": "urn:rkaf:us:regsgov:EPA-HQ-OAR-2021-0317-0001",
                }
            ],
        }
        result = audit_mapping_text(
            self.mapping_markdown([artifact_identity, regulatory_identity]),
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())

        duplicate = audit_mapping_text(
            self.mapping_markdown([artifact_identity, artifact_identity]),
            registry=self.registry,
        )
        self.assertTrue(any("duplicate mapping" in issue for issue in duplicate.issues))

    def test_source_membership_declares_evidence_qualified_projection(self) -> None:
        mapping = {
            "table": "documents",
            "column": "fr_doc_num",
            "subject_type": f"{RKAF}Artifact",
            "term": "http://purl.org/dc/terms/isFormatOf",
            "direction": "forward",
            "object_type": f"{RKAF}Artifact",
            "value_kind": "iri",
            "source_membership": {
                "table": "federal_register",
                "column": "document_number",
            },
            "transform": {
                "template": "https://www.federalregister.gov/d/{fr_doc_num}",
            },
            "samples": [
                {
                    "input": {"fr_doc_num": "2024-00366"},
                    "output": "https://www.federalregister.gov/d/2024-00366",
                }
            ],
        }
        result = audit_mapping_text(
            self.mapping_markdown([mapping]),
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())

        mapping["source_membership"] = {
            "table": "federal_register",
            "column": "",
            "unexpected": "value",
        }
        result = audit_mapping_text(
            self.mapping_markdown([mapping]),
            registry=self.registry,
        )
        self.assertTrue(
            any(
                "source_membership has unknown keys" in issue
                for issue in result.issues
            )
        )
        self.assertTrue(
            any(
                "source_membership column MUST be a non-empty string" in issue
                for issue in result.issues
            )
        )

    def test_inverse_relation_declares_domain_and_range(self) -> None:
        inverse = {
            "table": "proceedings",
            "column": "fr_document_numbers_json",
            "subject_type": f"{RKAF}Proceeding",
            "term": f"{RKAF}publishedInProceeding",
            "direction": "inverse",
            "object_type": f"{RKAF}Artifact",
            "value_kind": "iri",
            "collection": "json-list",
            "transform": {
                "template": "urn:spicy-regs:artifact:frdoc:{value}",
            },
            "samples": [
                {
                    "input": {
                        "fr_document_numbers_json": '["2024-00366", "2024-00411"]'
                    },
                    "output": [
                        "urn:spicy-regs:artifact:frdoc:2024-00366",
                        "urn:spicy-regs:artifact:frdoc:2024-00411",
                    ],
                }
            ],
        }
        result = audit_mapping_text(
            self.mapping_markdown([inverse]),
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())

        inverse["direction"] = "forward"
        result = audit_mapping_text(
            self.mapping_markdown([inverse]),
            registry=self.registry,
        )
        self.assertTrue(any("mapping domain" in issue for issue in result.issues))
        self.assertTrue(any("mapping range" in issue for issue in result.issues))

    def test_transform_sample_must_execute_exactly(self) -> None:
        mapping = {
            "table": "proceedings",
            "column": "docket_id",
            "subject_type": f"{RKAF}Proceeding",
            "term": f"{RKAF}hasDocket",
            "direction": "forward",
            "object_type": f"{RKAF}Artifact",
            "value_kind": "iri",
            "transform": {"template": "urn:spicy-regs:docket:{docket_id}"},
            "samples": [
                {
                    "input": {"docket_id": "EPA-HQ-OAR-2021-0317"},
                    "output": "urn:wrong",
                }
            ],
        }
        result = audit_mapping_text(
            self.mapping_markdown([mapping]),
            registry=self.registry,
        )
        self.assertTrue(any("transform produced" in issue for issue in result.issues))

    def test_multiple_mapping_blocks_are_composed(self) -> None:
        text = self.mapping_markdown([self.stage_mapping()])
        text += "\n" + self.mapping_markdown(
            [
                {
                    "table": "comment_periods",
                    "column": "proceeding_id",
                    "subject_type": f"{RKAF}CommentPeriod",
                    "term": f"{RKAF}commentPeriodFor",
                    "direction": "forward",
                    "object_type": f"{RKAF}Proceeding",
                    "value_kind": "iri",
                    "transform": {
                        "template": "urn:spicy-regs:proceeding:{proceeding_id}"
                    },
                    "samples": [
                        {
                            "input": {"proceeding_id": "p-123"},
                            "output": "urn:spicy-regs:proceeding:p-123",
                        }
                    ],
                }
            ]
        )
        result = audit_mapping_text(text, registry=self.registry)
        self.assertEqual(result.issues, ())
        self.assertEqual(result.blocks, 2)

    def test_unknown_term_and_compact_term_fail(self) -> None:
        unknown = self.stage_mapping()
        unknown["term"] = f"{RKAF}notRegistered"
        compact = self.stage_mapping()
        compact["column"] = "compact"
        compact["term"] = "rkaf:proceedingStage"
        result = audit_mapping_text(
            self.mapping_markdown([unknown, compact]),
            registry=self.registry,
        )
        self.assertTrue(
            any("unregistered vocabulary term" in issue for issue in result.issues)
        )
        self.assertTrue(any("full HTTP(S) IRI" in issue for issue in result.issues))

    def test_enum_target_must_belong_to_mapped_term(self) -> None:
        mapping = self.stage_mapping()
        mapping["enum_map"] = {"proposed": f"{RKAF}us-cfr"}
        result = audit_mapping_text(
            self.mapping_markdown([mapping]),
            registry=self.registry,
        )
        self.assertTrue(any("not valid for term" in issue for issue in result.issues))

    def test_enum_map_declares_discipline_for_an_id_coerced_closed_enum(self) -> None:
        """`rkaf:decision` is a closed set registered with `@type: @id`.

        Restricting `enum_map` to `value_kind: vocab` left every such term with
        no way to declare closed-enum discipline: a transform's output is
        checked for IRI SHAPE and never for membership, so a typo in the
        template produced an unregistered decision the audit accepted.
        """
        decision = {
            "table": "attestations",
            "column": "decision",
            "subject_type": f"{RKAF}Attestation",
            "term": f"{RKAF}decision",
            "direction": "forward",
            "value_kind": "iri",
            "enum_map": {
                "approved": f"{RKAF}approved",
                "rejected": f"{RKAF}rejected",
            },
        }
        result = audit_mapping_text(
            self.mapping_markdown([decision]),
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())

        decision["enum_map"] = {"approved": f"{RKAF}assignmentPrimary"}
        result = audit_mapping_text(
            self.mapping_markdown([decision]),
            registry=self.registry,
        )
        self.assertTrue(any("not valid for term" in issue for issue in result.issues))

    def test_enum_map_stays_closed_to_untyped_and_open_terms(self) -> None:
        literal_term = {
            "table": "attestations",
            "column": "attestation_scope",
            "subject_type": f"{RKAF}Attestation",
            "term": f"{RKAF}attestationScope",
            "direction": "forward",
            "value_kind": "literal",
            "enum_map": {"whole-record": f"{RKAF}approved"},
        }
        result = audit_mapping_text(
            self.mapping_markdown([literal_term]),
            registry=self.registry,
        )
        self.assertTrue(
            any("enum_map requires value_kind" in issue for issue in result.issues)
        )
        self.assertTrue(
            any(
                "enum_map is only valid for a closed-enum term" in issue
                for issue in result.issues
            )
        )

        open_iri_term = {
            "table": "attestations",
            "column": "attestor_id",
            "subject_type": f"{RKAF}Attestation",
            "term": f"{RKAF}attestor",
            "direction": "forward",
            "value_kind": "iri",
            "enum_map": {"reviewer-14": "urn:example:actor:reviewer-14"},
        }
        result = audit_mapping_text(
            self.mapping_markdown([open_iri_term]),
            registry=self.registry,
        )
        self.assertTrue(
            any(
                "enum_map is only valid for a closed-enum term" in issue
                for issue in result.issues
            )
        )

    @staticmethod
    def carrier_local_evidence_mapping() -> dict[str, Any]:
        return {
            "table": "concept_assignments",
            "columns": [
                "artifact_urn_encoded",
                "start_codepoint",
                "end_codepoint",
                "text_sha256",
            ],
            "subject_type": f"{RKAF}ConceptAssignment",
            "term": f"{RKAF}assignmentEvidence",
            "direction": "forward",
            "object_type": f"{RKAF}SourceFragment",
            "value_kind": "iri",
            "transform": {
                "template": (
                    "urn:rkaf:fragment:{artifact_urn_encoded}:"
                    "{start_codepoint}:{end_codepoint}:sha256-{text_sha256}"
                ),
                "identifier_scheme": f"{RKAF}carrier-local-fragment",
            },
            "samples": [
                {
                    "input": {
                        "artifact_urn_encoded": "urn%3Aspicy-regs%3Aartifact%3A9f2c4b",
                        "start_codepoint": 118,
                        "end_codepoint": 214,
                        "text_sha256": "2" * 64,
                    },
                    "output": (
                        "urn:rkaf:fragment:urn%3Aspicy-regs%3Aartifact%3A9f2c4b"
                        ":118:214:sha256-" + "2" * 64
                    ),
                }
            ],
        }

    def test_carrier_local_evidence_mints_a_fragment_without_a_fragments_table(
        self,
    ) -> None:
        """A carrier with an artifact id, two offsets, and a region digest can
        claim `rkaf:assignmentEvidence` without publishing a fragments table.

        The class range still holds — `object_type` is declared and checked —
        because the URN DENOTES the fragment its components describe.
        """
        result = audit_mapping_text(
            self.mapping_markdown([self.carrier_local_evidence_mapping()]),
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())
        self.assertEqual(result.terms, {f"{RKAF}assignmentEvidence"})

    def test_evidence_mapping_must_declare_its_identity_scheme(self) -> None:
        """Both registered identity forms are absolute IRIs, so the mapping —
        not the value — is what says which grammar the producer is claiming."""
        undeclared = self.carrier_local_evidence_mapping()
        undeclared["transform"] = {
            "template": undeclared["transform"]["template"],
        }
        result = audit_mapping_text(
            self.mapping_markdown([undeclared]),
            registry=self.registry,
        )
        self.assertTrue(
            any("requires a full-IRI identifier_scheme" in issue for issue in result.issues)
        )

        wrong_scheme = self.carrier_local_evidence_mapping()
        wrong_scheme["transform"] = {
            **wrong_scheme["transform"],
            "identifier_scheme": f"{RKAF}us-cfr",
        }
        result = audit_mapping_text(
            self.mapping_markdown([wrong_scheme]),
            registry=self.registry,
        )
        self.assertTrue(
            any("is not valid for" in issue for issue in result.issues)
        )

    def test_evidence_mapping_still_carries_the_source_fragment_range(self) -> None:
        no_range = self.carrier_local_evidence_mapping()
        del no_range["object_type"]
        result = audit_mapping_text(
            self.mapping_markdown([no_range]),
            registry=self.registry,
        )
        self.assertTrue(
            any(
                f"{RKAF}assignmentEvidence requires object_type" in issue
                for issue in result.issues
            )
        )

    def test_the_normative_conformance_examples_are_executable(self) -> None:
        """Every `rkaf-l0-mapping` block in the conformance spec is audited.

        The tabular attestation pattern (§0.1) is normative, so its worked
        mapping has to be executable rather than illustrative: a term, domain,
        range, value kind, or enum target that drifts out of the contract fails
        here instead of shipping as prose a consumer would copy.
        """
        result = audit_mapping_text(
            CONFORMANCE_SPEC.read_text(),
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())
        self.assertGreaterEqual(result.blocks, 2)
        self.assertIn(f"{RKAF}decision", result.terms)
        self.assertIn(f"{RKAF}targets", result.terms)

    def test_mapping_version_must_match_current_contract(self) -> None:
        result = audit_mapping_text(
            self.mapping_markdown([self.stage_mapping()], version=f"sha256:{'0' * 64}"),
            registry=self.registry,
        )
        self.assertTrue(any("does not match the current contract" in issue for issue in result.issues))

    def write_partner(
        self,
        root: Path,
        *,
        mappings: list[dict[str, Any]],
        terms_used: list[str],
        **overrides: Any,
    ) -> Path:
        (root / "ontology.md").write_text(self.mapping_markdown(mappings))
        document: dict[str, Any] = {
            "declared_levels": ["L0"],
            "rulespec_version": self.registry.contract_version,
            "test_corpus_version": "fixture-v1",
            "carrier_mapping": "ontology.md",
            "terms_used": terms_used,
            "results": {"L0": "pass"},
        }
        document.update(overrides)
        partner = root / "partner.yaml"
        partner.write_text(yaml.safe_dump(document, sort_keys=False))
        return partner

    def test_partner_terms_used_must_match_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partner = self.write_partner(
                root,
                mappings=[self.stage_mapping()],
                terms_used=[f"{RKAF}hasArtifactIdentifier"],
            )
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(any("missing mapped terms" in issue for issue in result.issues))
            self.assertTrue(any("unmapped terms" in issue for issue in result.issues))

    def test_valid_partner_self_certification_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partner = self.write_partner(
                root,
                mappings=[self.stage_mapping()],
                terms_used=[f"{RKAF}proceedingStage"],
            )
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.issues, ())

    def test_declared_carve_outs_are_checked_against_the_mapping(self) -> None:
        """`excluded_terms` and `excluded_tables` make narrowing diffable.

        Both are optional, and a declaration that omits them behaves exactly as
        it did before — see the backward-compatibility test below.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partner = self.write_partner(
                root,
                mappings=[self.stage_mapping()],
                terms_used=[f"{RKAF}proceedingStage"],
                excluded_terms=[
                    f"{RKAF}assignmentEvidence",
                    f"{RKAF}hasDocketIdentifier",
                ],
                excluded_tables=["comment_periods", "attestations"],
            )
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.issues, ())
            self.assertEqual(result.tables, {"proceedings"})

    def test_a_carve_out_may_not_name_something_the_mapping_claims(self) -> None:
        """In and out at once is the incoherence the key exists to catch."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partner = self.write_partner(
                root,
                mappings=[self.stage_mapping()],
                terms_used=[f"{RKAF}proceedingStage"],
                excluded_terms=[f"{RKAF}proceedingStage"],
                excluded_tables=["proceedings"],
            )
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(
                any(
                    "excluded_terms MUST NOT name mapped terms" in issue
                    for issue in result.issues
                )
            )
            self.assertTrue(
                any(
                    "excluded_tables MUST NOT name mapped tables" in issue
                    for issue in result.issues
                )
            )

    def test_a_carve_out_may_only_name_registered_terms(self) -> None:
        """A carve-out naming a predicate the contract never had reads as
        coverage of something Rulespec does not define."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partner = self.write_partner(
                root,
                mappings=[self.stage_mapping()],
                terms_used=[f"{RKAF}proceedingStage"],
                excluded_terms=[f"{RKAF}notRegistered"],
            )
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(
                any(
                    "excluded_terms entries MUST be registered contract terms"
                    in issue
                    for issue in result.issues
                )
            )

    def test_a_carve_out_must_be_a_non_empty_duplicate_free_list(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partner = self.write_partner(
                root,
                mappings=[self.stage_mapping()],
                terms_used=[f"{RKAF}proceedingStage"],
                excluded_terms=[],
                excluded_tables=["comment_periods", "comment_periods"],
            )
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(
                any(
                    "excluded_terms MUST be a non-empty list when present" in issue
                    for issue in result.issues
                )
            )
            self.assertTrue(
                any(
                    "excluded_tables MUST NOT contain duplicates" in issue
                    for issue in result.issues
                )
            )

    def test_a_declaration_without_carve_outs_is_unchanged(self) -> None:
        """Backward compatibility, stated as a test rather than assumed.

        Absence means the implementation said nothing about what it left out.
        It is NOT read as the complement of `terms_used`, so no existing
        declaration acquires a claim it never made.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partner = self.write_partner(
                root,
                mappings=[self.stage_mapping()],
                terms_used=[f"{RKAF}proceedingStage"],
            )
            document = yaml.safe_load(partner.read_text())
            self.assertNotIn("excluded_terms", document)
            self.assertNotIn("excluded_tables", document)
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.issues, ())

    def test_partner_cannot_mix_levels_or_claim_adoption_depth(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            partner = self.write_partner(
                root,
                mappings=[self.stage_mapping()],
                terms_used=[f"{RKAF}proceedingStage"],
                declared_levels=["L0", "L1"],
                adoption_depth="D1",
            )
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(any("MUST NOT claim L1" in issue for issue in result.issues))
            self.assertTrue(any("MUST omit adoption_depth" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
