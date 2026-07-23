from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.constraints_compile import (
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


if __name__ == "__main__":
    unittest.main()
