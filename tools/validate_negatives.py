#!/usr/bin/env python3
"""Negative-fixture validator. Asserts each named fixture FAILS SHACL validation
on the v0.2 shape set (i.e., yields ≥1 violation). Used by Layer 2 conformance.

Exit codes:
  0  every negative fixture produced ≥1 violation as expected
  1  one or more negative fixtures unexpectedly PASSED
  2  setup error
"""
import sys
from pathlib import Path

import rdflib
from pyshacl import validate

ROOT = Path(__file__).resolve().parent.parent
SHAPES = [
    # v0.2 shape files. v0.1 was wholesale-superseded (spec §11) and lives under
    # archive/v0.1/; this gate never loads it.
    "shapes/rkaf-shapes-core-v0.2.ttl",
    "shapes/rkaf-shapes-warrant-v0.2.ttl",
    "shapes/rkaf-shapes-confidence-v0.2.ttl",
    "shapes/rkaf-shapes-accessscope-v0.2.ttl",
    "shapes/rkaf-shapes-studio-promotions-v0.2.ttl",
    "shapes/rkaf-shapes-conceptregistry-v0.2.ttl",
]
NEGATIVES = [
    "fixtures/v0.2/evidencebinding-missing-negative.jsonld",
    "fixtures/v0.2/confidencerecord-score-theater-negative.jsonld",
    "fixtures/v0.2/accessscope-leak-negative.jsonld",
    "fixtures/v0.2/ailineage-missing-approver-negative.jsonld",
]


def main() -> int:
    shapes_g = rdflib.Graph()
    for s in SHAPES:
        shapes_g.parse(str(ROOT / s), format="turtle")
    print(f"loaded {len(shapes_g)} triples across {len(SHAPES)} shape files")
    failed = 0
    for fx in NEGATIVES:
        data = rdflib.Graph()
        data.parse(str(ROOT / fx), format="json-ld")
        conforms, _, _ = validate(
            data_graph=data,
            shacl_graph=shapes_g,
            inference="rdfs",
            advanced=True,
            meta_shacl=False,
        )
        status = "FAIL-AS-EXPECTED" if not conforms else "UNEXPECTED-PASS"
        print(f"  [{status}] {fx}")
        if conforms:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
