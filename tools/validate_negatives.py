#!/usr/bin/env python3
"""Negative-fixture validator.

Asserts every negative fixture is rejected by the combined authored-JSON and
RDF graph conformance path. Some source rules (language-map keys, explicit
typed-notation objects, and strict array form) are intentionally lost during
JSON-LD expansion and therefore cannot be reconstructed by SHACL. Those
fixtures must fail their compiled JSON Schema before RDF processing; graph
rules continue to fail SHACL. A negative passes this gate only if at least one
of those two normative layers rejects it.

Exit codes:
  0  every negative fixture produced ≥1 violation as expected
  1  one or more negative fixtures unexpectedly PASSED
  2  setup error
"""
import sys
import json
from pathlib import Path

import rdflib
from jsonschema import Draft202012Validator, FormatChecker
from pyshacl import validate

from conformance_lib import (
    fixture_name,
    iter_nodes,
    negative_fixture_paths,
    schema_bindings,
    shacl_shape_paths,
    violates_not_equal,
    violates_order,
)
from reference_release_digest import release_digest_errors

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    shapes_g = rdflib.Graph()
    shapes = shacl_shape_paths()
    for s in shapes:
        shapes_g.parse(str(s), format="turtle")
    bindings = schema_bindings()
    negatives = negative_fixture_paths()
    print(f"loaded {len(shapes_g)} triples across {len(shapes)} shape files")
    failed = 0
    for path in negatives:
        rel = fixture_name(path)
        payload = json.loads(path.read_text())
        source_rejected = False
        for node in iter_nodes(payload):
            binding = bindings.get(node.get("@type"))
            if binding is None:
                continue
            schema_doc = json.loads(binding.schema_path.read_text())
            target_schema = dict(schema_doc["$defs"][binding.class_name])
            target_schema["$defs"] = schema_doc.get("$defs", {})
            authored = dict(node)
            authored.pop("@context", None)
            errors = list(
                Draft202012Validator(
                    target_schema,
                    format_checker=FormatChecker(),
                ).iter_errors(authored)
            )
            extension_rejected = any(
                violates_order(
                    authored.get(order["lower"]),
                    authored.get(order["upper"]),
                )
                for order in target_schema.get("x-rkaf-order", [])
            ) or any(
                violates_not_equal(
                    authored.get(constraint["left"]),
                    authored.get(constraint["right"]),
                )
                for constraint in target_schema.get(
                    "x-rkaf-not-equal", []
                )
            )
            if errors or extension_rejected:
                source_rejected = True
                break

        data = rdflib.Graph()
        graph_rejected = False
        # If source syntax already failed, RDF expansion is not a normative
        # recovery mechanism. Still evaluate parseable graphs for diagnostic
        # coverage, but treat JSON-LD parse failure as graph rejection.
        try:
            data.parse(str(path), format="json-ld")
        except Exception:
            graph_rejected = True
        else:
            conforms, _, _ = validate(
                data_graph=data,
                shacl_graph=shapes_g,
                inference="rdfs",
                advanced=True,
                meta_shacl=False,
            )
            graph_rejected = (
                not conforms or bool(release_digest_errors(data))
            )

        rejected = source_rejected or graph_rejected
        status = "FAIL-AS-EXPECTED" if rejected else "UNEXPECTED-PASS"
        layers = (
            f"source={'FAIL' if source_rejected else 'PASS'} "
            f"graph={'FAIL' if graph_rejected else 'PASS'}"
        )
        print(f"  [{status}] fixtures/{rel} ({layers})")
        if not rejected:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
