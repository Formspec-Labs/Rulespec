"""Build with RefSpec, then read the files in a separate Rulespec process."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.refspec_atlas import AtlasIntegrityError, RefSpecVocabularyAtlas
from tools.test_refspec_atlas_conformance import (
    CASE_FILES,
    CORPUS_ROOT,
    PUBLISHED_CASES,
)

REFSPEC_CHECKOUT = os.environ.get("REFSPEC_CHECKOUT")


@unittest.skipUnless(
    REFSPEC_CHECKOUT,
    "set REFSPEC_CHECKOUT to run the cross-repository RefSpec atlas gate",
)
class RefSpecAtlasCrossRepositoryTests(unittest.TestCase):
    def test_vendored_corpus_still_matches_the_published_corpus(self) -> None:
        """The offline copy is only trustworthy while it is byte-identical."""

        checkout = Path(str(REFSPEC_CHECKOUT)).resolve(strict=True)
        root = checkout / "bindings/atlas/1.0/fixtures"
        self.assertEqual(
            (root / "corpus.json").read_bytes(),
            (CORPUS_ROOT / "corpus.json").read_bytes(),
        )
        corpus = json.loads((root / "corpus.json").read_text(encoding="utf-8"))
        for case in corpus["cases"]:
            for name in CASE_FILES:
                with self.subTest(case=case["id"], file=name):
                    self.assertEqual(
                        (root / case["directory"] / name).read_bytes(),
                        (CORPUS_ROOT / case["directory"] / name).read_bytes(),
                    )

    def test_every_refspec_conformance_case(self) -> None:
        checkout = Path(str(REFSPEC_CHECKOUT)).resolve(strict=True)
        root = checkout / "bindings/atlas/1.0/fixtures"
        corpus = json.loads((root / "corpus.json").read_text(encoding="utf-8"))
        cases = list(corpus["cases"])
        self.assertEqual(
            {case["id"]: bool(case["valid"]) for case in cases}, PUBLISHED_CASES
        )
        for case in cases:
            with self.subTest(case=case["id"]):
                directory = root / case["directory"]
                if case["valid"]:
                    RefSpecVocabularyAtlas.open(
                        directory,
                        expected_manifest_digest=case["manifestDigest"],
                        expected_output_digest=case["outputDigest"],
                    )
                    continue
                with self.assertRaisesRegex(
                    AtlasIntegrityError, re.escape(case["errorContains"])
                ):
                    RefSpecVocabularyAtlas.open(
                        directory,
                        expected_manifest_digest=case["manifestDigest"],
                        expected_output_digest=case["outputDigest"],
                    )

    def test_refspec_output_round_trips_without_importing_refspec(self) -> None:
        checkout = Path(str(REFSPEC_CHECKOUT)).resolve(strict=True)
        producer_python = Path(
            os.environ.get("REFSPEC_PYTHON", checkout / ".venv/bin/python")
        )
        self.assertTrue(
            producer_python.is_file(), f"producer Python is missing: {producer_python}"
        )
        producer = r"""
import importlib.util
import json
import sys
from pathlib import Path

from refspec.atlas import build_vocabulary_atlas

checkout = Path(sys.argv[1])
out = Path(sys.argv[2])
spec = importlib.util.spec_from_file_location(
    "refspec_rulespec_cross_repository_fixture",
    checkout / "tests/test_vocabulary_atlas.py",
)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)

managed = module._real_release(out / "managed-input")
crosswalk_releases = module._two_releases(out / "crosswalk-input")
for name, releases, crosswalk in (
    ("managed", (managed,), None),
    ("crosswalk", crosswalk_releases, module._qualified_bundle()),
):
    core_dir = out / f"{name}-core"
    core_dir.mkdir()
    core = module._core_release(core_dir)
    asset = build_vocabulary_atlas(releases, rulespec_core=core, crosswalk=crosswalk)
    directory = asset.write(out / f"{name}-atlas")
    view = releases[0].verified_view()
    member = next(view.iter_members())
    selection = {
        "manifestDigest": asset.manifest_digest,
        "outputDigest": asset.output_digest,
        "rulespecCore": {
            "release_id": core.release_id,
            "release_digest": core.release_digest,
        },
        "probe": {"releaseId": member.release_iri, "memberId": member.member_iri},
    }
    (out / f"{name}-selection.json").write_text(json.dumps(selection, sort_keys=True))
"""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            subprocess.run(
                (
                    str(producer_python),
                    "-c",
                    producer,
                    str(checkout),
                    str(output),
                ),
                cwd=checkout,
                check=True,
            )

            self.assertFalse(
                any(
                    name == "refspec" or name.startswith("refspec.")
                    for name in sys.modules
                )
            )
            for name in ("managed", "crosswalk"):
                selection = json.loads((output / f"{name}-selection.json").read_text())
                atlas = RefSpecVocabularyAtlas.open(
                    output / f"{name}-atlas",
                    expected_manifest_digest=selection["manifestDigest"],
                    expected_output_digest=selection["outputDigest"],
                )
                core_pin = atlas.rulespec_core_pin()
                self.assertEqual(
                    {
                        "release_id": core_pin.release_id,
                        "release_digest": core_pin.release_digest,
                    },
                    selection["rulespecCore"],
                )
                pin = atlas.require_member(
                    release_id=selection["probe"]["releaseId"],
                    member_id=selection["probe"]["memberId"],
                )
                self.assertEqual(pin.release_id, selection["probe"]["releaseId"])
                self.assertTrue(pin.release_digest.startswith("sha256:"))

            self.assertFalse(
                any(
                    name == "refspec" or name.startswith("refspec.")
                    for name in sys.modules
                )
            )


if __name__ == "__main__":
    unittest.main()
