from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

import yaml

from tools.l0_mapping_audit import (
    audit_mapping_text,
    audit_partner,
    load_vocabulary_registry,
)

RKAF = "https://rulespec.org/ns/v1#"


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
                "proposed": f"{RKAF}proposed",
                "final": f"{RKAF}final",
            },
        }

    def test_valid_mapping_checks_domain_kind_enum_and_identifier_sample(self) -> None:
        identifier = {
            "table": "proceedings",
            "column": "rin",
            "subject_type": f"{RKAF}Proceeding",
            "term": f"{RKAF}hasProceedingIdentifier",
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
