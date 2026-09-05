"""The projection's fixture documents pass this repository's own conformance gate.

rulespec-projection promises "gate-valid RKAF JSON-LD". Its own suite proves
byte parity with the producer it was moved from, which is not the same claim:
the producer's gate was a sibling checkout at some earlier version. This test
closes the loop where the gate lives. Every fixture document the package's
parity suite pins is written beside the JSON-LD context and run through
``rulespec_conformance.ci_validate.validate_one`` against the current shapes,
including the release-digest recomputation the L3 validators apply.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rulespec_conformance import ci_validate  # noqa: E402

FIXTURES = ROOT / "packages" / "rulespec-projection" / "tests" / "fixtures"
CONTEXT = ROOT / "context" / "rkaf-context.jsonld"
DOCUMENTS = (
    "federal_register_document.json",
    "federal_register_document_no_tables.json",
    "unified_agenda_observation.json",
    "model_layer.json",
)


class ProjectionConformanceTests(unittest.TestCase):
    def test_every_fixture_document_conforms(self) -> None:
        shapes = ci_validate.shacl_shape_paths()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(CONTEXT, root / "rkaf-context.jsonld")
            for name in DOCUMENTS:
                with self.subTest(fixture=name):
                    fixture = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
                    document = fixture["result"]["document"]
                    self.assertEqual(document["@context"], "./rkaf-context.jsonld")
                    path = root / f"{Path(name).stem}.jsonld"
                    path.write_text(json.dumps(document, ensure_ascii=False) + "\n", encoding="utf-8")
                    report = ci_validate.validate_one(path, shapes)
                    self.assertNotIn("error", report, report)
                    self.assertGreater(report["triples"], 0)
                    self.assertTrue(
                        report["conforms"],
                        json.dumps(report["violations_detail"], indent=1, ensure_ascii=False),
                    )


if __name__ == "__main__":
    unittest.main()
