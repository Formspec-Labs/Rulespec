"""ReferenceResourceRelease digest conformance vectors."""

from __future__ import annotations

import copy
import unittest
from pathlib import Path

from rdflib import DCAT, PROV, Graph, Literal, URIRef

from tools.ci_validate import validate_one
from tools.conformance_lib import shacl_shape_paths
from tools.reference_release_digest import (
    DCAT_VERSION,
    RKAF,
    canonical_preimage,
    compute_digest,
    release_digest_errors,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "reference-resource-release-digest-positive.jsonld"
WRONG_DIGEST_FIXTURE = (
    ROOT
    / "fixtures"
    / "negatives"
    / "reference-resource-release-wrong-digest-negative.jsonld"
)
BLANK_NODE_RELEASE_FIXTURE = (
    ROOT
    / "fixtures"
    / "negatives"
    / "reference-resource-release-blank-node-negative.jsonld"
)
RELEASE = URIRef("urn:rkaf:fixture:release:digest-vector")


class ReferenceResourceReleaseDigestTests(unittest.TestCase):
    def graph(self) -> Graph:
        graph = Graph()
        graph.parse(FIXTURE, format="json-ld")
        return graph

    def test_normative_vector_matches_declared_digest(self) -> None:
        graph = self.graph()
        declared = str(next(graph.objects(RELEASE, RKAF.referenceReleaseDigest)))
        self.assertEqual(
            declared,
            "sha256:999bb800008a7d517d4f0269304358d79a10925f21d13ea9376b0eee1feda431",
        )
        self.assertEqual(compute_digest(graph, RELEASE), declared)
        preimage = canonical_preimage(graph, RELEASE)
        self.assertEqual(preimage, "".join(sorted(preimage.splitlines(True))))

    def test_member_change_invalidates_the_digest(self) -> None:
        graph = self.graph()
        declared = str(next(graph.objects(RELEASE, RKAF.referenceReleaseDigest)))
        changed = copy.deepcopy(graph)
        changed.add(
            (
                RELEASE,
                PROV.hadMember,
                URIRef("urn:rkaf:fixture:concept:added-after-release"),
            )
        )
        self.assertNotEqual(compute_digest(changed, RELEASE), declared)

    def test_distribution_digest_change_invalidates_the_release_digest(self) -> None:
        graph = self.graph()
        declared = str(next(graph.objects(RELEASE, RKAF.referenceReleaseDigest)))
        distribution = next(graph.objects(RELEASE, DCAT.distribution))
        changed = copy.deepcopy(graph)
        changed.remove((distribution, RKAF.hasContentDigest, None))
        from rdflib import Literal

        changed.add(
            (
                distribution,
                RKAF.hasContentDigest,
                Literal("sha256:" + "f" * 64),
            )
        )
        self.assertNotEqual(compute_digest(changed, RELEASE), declared)

    def test_rdfc_control_characters_use_canonical_escapes(self) -> None:
        graph = self.graph()
        graph.remove((RELEASE, DCAT_VERSION, None))
        graph.add(
            (
                RELEASE,
                DCAT_VERSION,
                Literal("a\b\t\n\f\r\u0001\u007f"),
            )
        )
        preimage = canonical_preimage(graph, RELEASE)
        self.assertIn(
            '"a\\b\\t\\n\\f\\r\\u0001\\u007F"',
            preimage,
        )
        self.assertNotIn("\b", preimage)
        self.assertNotIn("\u0001", preimage)
        self.assertNotIn("\u007f", preimage)

    def test_xsd_string_uses_the_rdfc_simple_literal_spelling(self) -> None:
        preimage = canonical_preimage(self.graph(), RELEASE)
        self.assertIn('"application/ld+json" .', preimage)
        self.assertNotIn(
            '"application/ld+json"^^'
            "<http://www.w3.org/2001/XMLSchema#string>",
            preimage,
        )

    def test_well_formed_wrong_digest_fails_the_production_hook(self) -> None:
        graph = Graph()
        graph.parse(WRONG_DIGEST_FIXTURE, format="json-ld")
        errors = release_digest_errors(graph)
        self.assertEqual(len(errors), 1)
        self.assertIn("does not match RDFC-1.0 manifest digest", errors[0])

        result = validate_one(WRONG_DIGEST_FIXTURE, shacl_shape_paths())
        self.assertFalse(result["conforms"])
        self.assertTrue(
            any(
                detail["constraint"]
                == "ReferenceResourceReleaseDigestConstraint"
                for detail in result["violations_detail"]
            )
        )

    def test_blank_node_release_cannot_bypass_the_production_hook(self) -> None:
        graph = Graph()
        graph.parse(BLANK_NODE_RELEASE_FIXTURE, format="json-ld")
        errors = release_digest_errors(graph)
        self.assertEqual(len(errors), 1)
        self.assertIn("must be named by an IRI", errors[0])

        result = validate_one(BLANK_NODE_RELEASE_FIXTURE, shacl_shape_paths())
        self.assertFalse(result["conforms"])
        self.assertTrue(
            any(
                detail["constraint"]
                == "ReferenceResourceReleaseDigestConstraint"
                for detail in result["violations_detail"]
            )
        )


if __name__ == "__main__":
    unittest.main()
