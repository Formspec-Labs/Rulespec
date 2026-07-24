from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.constraints_compile import (
    _scan_reference_class_registry,
    parse_cue_file,
    target_json_schema,
    target_shacl,
    target_typescript,
)


class ConstraintCompilerTests(unittest.TestCase):
    def test_patterns_dates_and_order_project_from_aliased_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "interval.cue"
            source.write_text(
                """
package rkaf

import "time"

#Interval: I={
    "@type": "rkaf:Interval"
    "rkaf:links": [...(string & =~"^[A-Za-z][A-Za-z0-9+.-]*:.+$")]
    "rkaf:scheme"?: string
    "rkaf:start": time.Format("2006-01-02")
    "rkaf:end": time.Format("2006-01-02")
    if I["rkaf:scheme"] != _|_ {
        "rkaf:identifier": string
    }
    if I["rkaf:start"] > I["rkaf:end"] {
        _|_
    }
}
"""
            )

            document = parse_cue_file(source)
            schema = json.loads(target_json_schema(document))
            interval = schema["$defs"]["Interval"]

            link_schema = interval["properties"]["rkaf:links"]
            self.assertEqual(
                link_schema["anyOf"][1]["items"]["pattern"],
                "^[A-Za-z][A-Za-z0-9+.-]*:.+$",
            )
            self.assertEqual(
                interval["properties"]["rkaf:start"]["format"],
                "date",
            )
            self.assertEqual(
                interval["properties"]["rkaf:start"]["pattern"],
                r"^\d{4}-\d{2}-\d{2}$",
            )
            self.assertEqual(
                interval["x-rkaf-order"],
                [{"lower": "rkaf:start", "upper": "rkaf:end"}],
            )
            self.assertIn(
                {
                    "if": {"required": ["rkaf:scheme"]},
                    "then": {
                        "properties": {
                            "rkaf:identifier": {"type": "string"}
                        },
                        "required": ["rkaf:identifier"],
                    },
                },
                interval["allOf"],
            )

            shacl = target_shacl(document)
            self.assertIn(
                "@prefix prov: <http://www.w3.org/ns/prov#> .",
                shacl,
            )
            self.assertIn('sh:pattern "^[A-Za-z][A-Za-z0-9+.-]*:.+$"', shacl)
            self.assertIn("sh:datatype xsd:date", shacl)
            self.assertIn(
                "sh:lessThanOrEquals rkaf:end",
                shacl,
            )
            self.assertIn("sh:path rkaf:scheme ; sh:minCount 1", shacl)
            self.assertIn("sh:path rkaf:scheme ; sh:maxCount 1", shacl)
            self.assertIn("sh:path rkaf:identifier ; sh:minCount 1", shacl)

            typescript = target_typescript(document)
            self.assertIn("function isRkafDate", typescript)
            self.assertIn('!isRkafDate(v["rkaf:start"])', typescript)
            self.assertIn(
                'const condition1 = record["rkaf:scheme"] !== undefined',
                typescript,
            )
            self.assertIn(
                'rkaf:identifier: required by rkaf:scheme',
                typescript,
            )

    def test_reference_ranges_project_to_shacl_classes(self) -> None:
        root = Path(__file__).resolve().parent.parent
        source = root / "constraints" / "core" / "rulemaking.cue"
        document = parse_cue_file(source)
        ranges = _scan_reference_class_registry(source)
        shacl = target_shacl(document, reference_classes=ranges)
        self.assertRegex(
            shacl,
            r"sh:path rkaf:hasDocket ;[^\n]*sh:class rkaf:Docket",
        )
        self.assertRegex(
            shacl,
            r"sh:path rkaf:commentPeriodFor ;[^\n]*sh:class rkaf:Proceeding",
        )
        self.assertIn("@prefix dcat: <http://www.w3.org/ns/dcat#> .", shacl)
        self.assertIn("@prefix foaf: <http://xmlns.com/foaf/0.1/> .", shacl)

    def test_forbidden_pattern_projects_to_all_shape_validators(self) -> None:
        root = Path(__file__).resolve().parent.parent
        source = root / "constraints" / "core" / "rulemaking.cue"
        document = parse_cue_file(source)
        agenda_identifier_scheme = next(
            enum for enum in document.enums
            if enum.name == "AgendaItemIdentifierScheme"
        )
        self.assertEqual(agenda_identifier_scheme.values, ["rkaf:us-rin"])

        schema = json.loads(target_json_schema(document))
        identifier = schema["$defs"]["Proceeding"]["properties"][
            "rkaf:hasProceedingIdentifier"
        ]
        self.assertEqual(
            identifier["not"]["pattern"],
            r"^urn:rkaf:us:(rin|regsgov):",
        )

        shacl = target_shacl(document)
        self.assertIn(
            'sh:not [ sh:pattern "^urn:rkaf:us:(rin|regsgov):" ; ]',
            shacl,
        )

        typescript = target_typescript(document)
        self.assertIn(
            'rkaf:hasProceedingIdentifier: forbidden pattern match',
            typescript,
        )

    def test_optional_nonempty_list_is_absent_or_nonempty(self) -> None:
        root = Path(__file__).resolve().parent.parent
        source = root / "constraints" / "core" / "rulemaking.cue"
        document = parse_cue_file(source)
        schema = json.loads(target_json_schema(document))
        proceeding = schema["$defs"]["Proceeding"]
        has_authority = proceeding["properties"]["rkaf:hasAuthority"]

        self.assertNotIn("rkaf:hasAuthority", proceeding["required"])
        self.assertEqual(has_authority["anyOf"][1]["minItems"], 1)

        shacl = target_shacl(document)
        has_authority_line = next(
            line for line in shacl.splitlines()
            if "sh:path rkaf:hasAuthority" in line
        )
        self.assertNotIn("sh:minCount", has_authority_line)


if __name__ == "__main__":
    unittest.main()
