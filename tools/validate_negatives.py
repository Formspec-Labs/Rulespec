#!/usr/bin/env python3
"""Negative-fixture validator. Asserts every negative fixture FAILS SHACL validation
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

from conformance_lib import fixture_name, negative_fixture_paths, shacl_shape_paths

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    shapes_g = rdflib.Graph()
    shapes = shacl_shape_paths()
    for s in shapes:
        shapes_g.parse(str(s), format="turtle")
    negatives = negative_fixture_paths()
    print(f"loaded {len(shapes_g)} triples across {len(shapes)} shape files")
    failed = 0
    for path in negatives:
        rel = fixture_name(path)
        data = rdflib.Graph()
        data.parse(str(path), format="json-ld")
        conforms, _, _ = validate(
            data_graph=data,
            shacl_graph=shapes_g,
            inference="rdfs",
            advanced=True,
            meta_shacl=False,
        )
        status = "FAIL-AS-EXPECTED" if not conforms else "UNEXPECTED-PASS"
        print(f"  [{status}] fixtures/{rel}")
        if conforms:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
