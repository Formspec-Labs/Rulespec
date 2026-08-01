"""Fail-closed tests for Rulespec's RefSpec atlas reader."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from rdflib import Dataset, Literal, URIRef
from rdflib.namespace import PROV, RDF, SKOS

from tools.refspec_atlas import (
    ATLAS,
    ATLAS_FORMAT,
    RKAF,
    AtlasIntegrityError,
    RefSpecVocabularyAtlas,
)
from tools.rulespec_release import (
    canonical_digest,
    canonical_json_bytes,
    content_digest,
)

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64
MANAGED_INPUT = {
    "role": "ManagedReleaseView",
    "manifestDigest": DIGEST_A,
    "publicationReleaseId": "urn:test:publication:one",
    "rulespecGraph": {"id": "urn:test:rulespec-graph:one", "digest": DIGEST_B},
}
CORE_INPUT = {
    "role": "RulespecCoreRelease",
    "fileDigest": DIGEST_C,
    "releaseId": "urn:rulespec:core:" + "a" * 64,
    "releaseDigest": DIGEST_A,
}
CROSSWALK_INPUT = {
    "role": "CrosswalkBundle",
    "id": "urn:test:crosswalk:one",
    "digest": DIGEST_B,
    "fileDigest": DIGEST_C,
    "mediaType": "application/vnd.refspec.vocabulary-atlas-crosswalk+json",
}
IMPLEMENTATION = {
    "id": "urn:ref:implementation:vocabulary-atlas:1.0",
    "version": "1.0",
    "sourceModules": [
        {"path": path, "digest": DIGEST_A}
        for path in (
            "refspec/atlas/__init__.py",
            "refspec/atlas/model.py",
            "refspec/atlas/queries.py",
            "refspec/binding.py",
            "refspec/generated_rulespec_dependency.py",
            "refspec/managed_release.py",
            "refspec/release_graph.py",
            "refspec/storage.py",
            "refspec/vocabulary.py",
        )
    ],
    "runtime": {
        "jsonschemaVersion": "4.26.0",
        "pyarrowVersion": "23.0.0",
        "pythonRequirement": ">=3.10",
        "pythonVersion": "3.12.0",
        "rdflibVersion": "7.6.0",
    },
}
POLICIES = {
    "releaseFacts": "copiedManagedReleaseFactsOnly",
    "analysis": "replaceableMachineAnalysis",
    "labelEquality": "clusterOnly",
    "mappingEligibility": "twoIndependentMachinesSearchOnly",
    "humanFeedback": "appendOnlyNonAuthorizing",
}
SOURCE_MEMBER = URIRef("urn:test:concept:source")
TARGET_MEMBER = URIRef("urn:test:concept:target")
SOURCE_RELEASE = URIRef("urn:test:release:source")
TARGET_RELEASE = URIRef("urn:test:release:target")


def _canonical_nquads(dataset: Dataset) -> bytes:
    serialized = dataset.serialize(format="nquads")
    text = serialized.decode("utf-8") if isinstance(serialized, bytes) else serialized
    lines = sorted(line for line in text.splitlines() if line.strip())
    return ("\n".join(lines) + "\n").encode("utf-8")


def _manifest_selection(root: Path) -> dict[str, Any]:
    manifest_bytes = (root / "atlas-manifest.json").read_bytes()
    return {
        "manifest_digest": content_digest(manifest_bytes),
        "output_digest": content_digest((root / "atlas.nq").read_bytes()),
    }


def _write_atlas(
    root: Path,
    *,
    implementation: dict[str, Any] | None = None,
    omit_authoritative_membership: bool = False,
) -> dict[str, Any]:
    selected_implementation = implementation or IMPLEMENTATION
    inputs = [dict(MANAGED_INPUT), dict(CORE_INPUT), dict(CROSSWALK_INPUT)]
    generation_digest = canonical_digest(
        {
            "format": ATLAS_FORMAT,
            "inputs": inputs,
            "implementation": selected_implementation,
            "policies": POLICIES,
        }
    )
    asset_id = "urn:ref:vocabulary-atlas:" + generation_digest.removeprefix("sha256:")
    release_graph_id = asset_id + ":release-facts"
    analysis_graph_id = asset_id + ":analysis"
    dataset = Dataset(default_union=False)
    release_graph = dataset.graph(URIRef(release_graph_id))
    analysis = dataset.graph(URIRef(analysis_graph_id))

    for release, member, digest in (
        (SOURCE_RELEASE, SOURCE_MEMBER, DIGEST_A),
        (TARGET_RELEASE, TARGET_MEMBER, DIGEST_B),
    ):
        release_graph.add((release, RDF.type, RKAF.ReferenceResourceRelease))
        release_graph.add((release, RKAF.referenceReleaseDigest, Literal(digest)))
        if not (omit_authoritative_membership and member == SOURCE_MEMBER):
            release_graph.add((release, PROV.hadMember, member))
        release_graph.add((member, RDF.type, SKOS.Concept))
        analysis.add((member, ATLAS.memberOfRelease, release))

    payload = _canonical_nquads(dataset)
    root.mkdir()
    (root / "atlas.nq").write_bytes(payload)
    manifest: dict[str, Any] = {
        "id": asset_id,
        "type": "urn:ref:type:VocabularyAtlasManifest",
        "schemaVersion": "1.0",
        "format": ATLAS_FORMAT,
        "generationDigest": generation_digest,
        "inputs": inputs,
        "implementation": selected_implementation,
        "policies": POLICIES,
        "graphs": [
            {
                "role": "releaseFacts",
                "id": release_graph_id,
                "quadCount": len(release_graph),
            },
            {"role": "analysis", "id": analysis_graph_id, "quadCount": len(analysis)},
        ],
        "output": {
            "path": "atlas.nq",
            "mediaType": "application/n-quads",
            "digest": content_digest(payload),
            "byteLength": len(payload),
            "quadCount": len(release_graph) + len(analysis),
        },
        "counts": {
            "managedReleases": 1,
            "releaseFacts": len(release_graph),
            "analysisFacts": len(analysis),
            "labelClusters": 0,
            "mappingCandidates": 0,
            "searchOnlyMappings": 0,
            "machineValidations": 0,
            "feedback": 0,
        },
    }
    manifest["canonicalPayloadDigest"] = canonical_digest(manifest)
    (root / "atlas-manifest.json").write_bytes(canonical_json_bytes(manifest) + b"\n")
    return _manifest_selection(root)


def _open(root: Path, selection: dict[str, Any]) -> RefSpecVocabularyAtlas:
    return RefSpecVocabularyAtlas.open(
        root,
        expected_manifest_digest=selection["manifest_digest"],
        expected_output_digest=selection["output_digest"],
    )


class RefSpecVocabularyAtlasTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "atlas"
        self.selection = _write_atlas(self.root)

    def test_reads_exact_reference_release_membership(self) -> None:
        atlas = _open(self.root, self.selection)

        self.assertEqual(
            atlas.pin(),
            {
                "asset_id": atlas.asset_id,
                "manifest_digest": self.selection["manifest_digest"],
                "distribution_digest": self.selection["output_digest"],
            },
        )
        self.assertEqual(
            atlas.rulespec_core_pin().release_id,
            CORE_INPUT["releaseId"],
        )
        self.assertEqual(
            atlas.require_member(
                member_id=str(SOURCE_MEMBER), release_id=str(SOURCE_RELEASE)
            ).release_id,
            str(SOURCE_RELEASE),
        )
        with self.assertRaisesRegex(AtlasIntegrityError, "does not contain member"):
            atlas.require_member(
                member_id="urn:test:concept:missing",
                release_id=str(SOURCE_RELEASE),
            )

    def test_accepts_declared_producer_neutral_implementation_provenance(
        self,
    ) -> None:
        alternate = {
            "id": "urn:test:alternate-atlas-builder",
            "version": "42",
            "sourceModules": [{"path": "publisher/atlas.py", "digest": DIGEST_B}],
            "runtime": {"engineVersion": "alternate-1"},
        }
        alternate_root = Path(self.temporary.name) / "alternate-atlas"
        selection = _write_atlas(alternate_root, implementation=alternate)
        self.assertEqual(
            _open(alternate_root, selection).manifest["implementation"], alternate
        )

    def test_rejects_distribution_tampering(self) -> None:
        (self.root / "atlas.nq").write_bytes(
            (self.root / "atlas.nq").read_bytes() + b"# changed\n"
        )
        with self.assertRaisesRegex(AtlasIntegrityError, "bytes differ"):
            _open(self.root, self.selection)

    def test_analysis_membership_must_match_authoritative_release_facts(
        self,
    ) -> None:
        root = Path(self.temporary.name) / "wrong-membership"
        selection = _write_atlas(root, omit_authoritative_membership=True)
        with self.assertRaisesRegex(AtlasIntegrityError, "authoritative release facts"):
            _open(root, selection)

    def test_recomputes_generation_identity_from_exact_inputs(self) -> None:
        manifest_path = self.root / "atlas-manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["implementation"]["sourceModules"][0]["digest"] = DIGEST_C
        manifest.pop("canonicalPayloadDigest")
        manifest["canonicalPayloadDigest"] = canonical_digest(manifest)
        manifest_path.write_bytes(canonical_json_bytes(manifest) + b"\n")
        selection = _manifest_selection(self.root)

        with self.assertRaisesRegex(AtlasIntegrityError, "generationDigest differs"):
            _open(self.root, selection)


if __name__ == "__main__":
    unittest.main()
