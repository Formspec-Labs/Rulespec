from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

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

    def test_valid_mapping_accepts_registered_terms_and_enum_targets(self) -> None:
        result = audit_mapping_text(
            f"""
```yaml rkaf-l0-mapping
- table: proceedings
  column: stage
  term: {RKAF}proceedingStage
  enum_map:
    proposed: {RKAF}proposed
    final: {RKAF}final
- table: proceedings
  column: rin
  term: {RKAF}hasArtifactIdentifier
```
""",
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())
        self.assertEqual(result.blocks, 1)
        self.assertEqual(result.entries, 2)

    def test_multiple_mapping_blocks_are_composed(self) -> None:
        result = audit_mapping_text(
            f"""
```yaml rkaf-l0-mapping
- table: rule_targets
  column: cfr_ref
  term: {RKAF}hasArtifactIdentifier
```

```yaml rkaf-l0-mapping
- table: rule_targets
  column: source
  term: {RKAF}artifactIdentifierScheme
  enum_map:
    cfr: {RKAF}us-cfr
```
""",
            registry=self.registry,
        )
        self.assertEqual(result.issues, ())
        self.assertEqual(result.blocks, 2)

    def test_unknown_term_and_compact_term_fail(self) -> None:
        result = audit_mapping_text(
            f"""
```yaml rkaf-l0-mapping
- table: t
  column: unknown
  term: {RKAF}notRegistered
- table: t
  column: compact
  term: rkaf:proceedingStage
```
""",
            registry=self.registry,
        )
        self.assertTrue(any("unregistered vocabulary term" in issue for issue in result.issues))
        self.assertTrue(any("full HTTP(S) IRI" in issue for issue in result.issues))

    def test_enum_target_must_belong_to_mapped_term(self) -> None:
        result = audit_mapping_text(
            f"""
```yaml rkaf-l0-mapping
- table: proceedings
  column: stage
  term: {RKAF}proceedingStage
  enum_map:
    proposed: {RKAF}us-cfr
```
""",
            registry=self.registry,
        )
        self.assertTrue(any("not valid for term" in issue for issue in result.issues))

    def test_partner_terms_used_must_match_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mapping = root / "ontology.md"
            mapping.write_text(
                f"""
```yaml rkaf-l0-mapping
- table: proceedings
  column: stage
  term: {RKAF}proceedingStage
```
"""
            )
            partner = root / "partner.yaml"
            partner.write_text(
                yaml.safe_dump(
                    {
                        "declared_levels": ["L0"],
                        "carrier_mapping": "ontology.md",
                        "terms_used": [f"{RKAF}hasArtifactIdentifier"],
                        "results": {"L0": "pass"},
                    },
                    sort_keys=False,
                )
            )
            result = audit_partner(
                partner,
                registry=self.registry,
                repo_root=root,
            )
            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(any("missing mapped terms" in issue for issue in result.issues))
            self.assertTrue(any("unmapped terms" in issue for issue in result.issues))

    def test_valid_partner_self_certification_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mapping = root / "ontology.md"
            mapping.write_text(
                f"""
```yaml rkaf-l0-mapping
- table: proceedings
  column: stage
  term: {RKAF}proceedingStage
  enum_map:
    proposed: {RKAF}proposed
```
"""
            )
            partner = root / "partner.yaml"
            partner.write_text(
                yaml.safe_dump(
                    {
                        "declared_levels": ["L0"],
                        "carrier_mapping": "ontology.md",
                        "terms_used": [f"{RKAF}proceedingStage"],
                        "results": {"L0": "pass"},
                    },
                    sort_keys=False,
                )
            )
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result.issues, ())

    def test_partner_cannot_mix_l0_with_jsonld_levels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            mapping = root / "ontology.md"
            mapping.write_text(
                f"""
```yaml rkaf-l0-mapping
- table: proceedings
  column: rin
  term: {RKAF}hasArtifactIdentifier
```
"""
            )
            partner = root / "partner.yaml"
            partner.write_text(
                yaml.safe_dump(
                    {
                        "declared_levels": ["L0", "L1"],
                        "carrier_mapping": "ontology.md",
                        "terms_used": [f"{RKAF}hasArtifactIdentifier"],
                        "results": {"L0": "pass"},
                    },
                    sort_keys=False,
                )
            )
            result = audit_partner(partner, registry=self.registry, repo_root=root)
            self.assertIsNotNone(result)
            assert result is not None
            self.assertTrue(
                any("MUST NOT claim L1" in issue for issue in result.issues)
            )


if __name__ == "__main__":
    unittest.main()
