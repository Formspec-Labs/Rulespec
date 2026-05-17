"""Tests for ``studio_schemas_derive_manifest`` (run from the Rulespec root)."""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

RULESPEC_ROOT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent


def _load_module():
    path = TOOLS / "studio_schemas_derive_manifest.py"
    spec = importlib.util.spec_from_file_location("studio_schemas_derive_manifest", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["studio_schemas_derive_manifest"] = mod
    spec.loader.exec_module(mod)
    return mod


ssd = _load_module()


class TestStudioSchemasDeriveManifest(unittest.TestCase):
    def test_sha256sums_lines_sorted_by_output_path(self) -> None:
        """Line order in ``SHA256SUMS`` matches ``sorted(output paths)`` from ``compute_derived``."""
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "schema-source" / "api").mkdir(parents=True)
            (root / "schema-source" / "api" / "z.schema.json").write_text(
                "{}", encoding="utf-8"
            )
            (root / "schema-source" / "a.schema.json").write_text("{}", encoding="utf-8")
            man = {
                "version": 1,
                "outputs": [
                    {
                        "path": "api/z.schema.json",
                        "provenance": "curated",
                        "source": "schema-source/api/z.schema.json",
                        "rationale": "test",
                    },
                    {
                        "path": "a.schema.json",
                        "provenance": "curated",
                        "source": "schema-source/a.schema.json",
                        "rationale": "test",
                    },
                ],
            }
            (root / "schemas-derive-manifest.json").write_text(
                json.dumps(man), encoding="utf-8"
            )
            _, sums = ssd.compute_derived(root)
            lines = [ln for ln in sums.strip().split("\n") if ln]
            self.assertEqual(len(lines), 2)
            # sorted: "a.schema.json" < "api/z.schema.json"
            self.assertTrue(lines[0].endswith("./a.schema.json"), lines[0])
            self.assertTrue(lines[1].endswith("./api/z.schema.json"), lines[1])

    def test_duplicate_manifest_path_errors(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "schema-source").mkdir()
            (root / "schema-source" / "a.schema.json").write_text("{}", encoding="utf-8")
            man = {
                "version": 1,
                "outputs": [
                    {
                        "path": "a.schema.json",
                        "provenance": "curated",
                        "source": "schema-source/a.schema.json",
                        "rationale": "test",
                    },
                    {
                        "path": "a.schema.json",
                        "provenance": "curated",
                        "source": "schema-source/a.schema.json",
                        "rationale": "test",
                    },
                ],
            }
            (root / "schemas-derive-manifest.json").write_text(
                json.dumps(man), encoding="utf-8"
            )
            with self.assertRaises(ValueError) as ctx:
                ssd.compute_derived(root)
            self.assertIn("duplicate", str(ctx.exception).lower())

    def test_fragment_merge_not_implemented(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "schema-source").mkdir()
            (root / "schema-source" / "a.schema.json").write_text("{}", encoding="utf-8")
            man = {
                "version": 1,
                "outputs": [
                    {
                        "path": "a.schema.json",
                        "provenance": "fragment_merge",
                        "source": "schema-source/a.schema.json",
                    },
                ],
            }
            (root / "schemas-derive-manifest.json").write_text(
                json.dumps(man), encoding="utf-8"
            )
            with self.assertRaises(NotImplementedError):
                ssd.compute_derived(root)

    def test_passthrough_requires_rationale(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "schema-source").mkdir()
            (root / "schema-source" / "a.schema.json").write_text("{}", encoding="utf-8")
            man = {
                "version": 1,
                "outputs": [
                    {
                        "path": "a.schema.json",
                        "provenance": "passthrough_explicit",
                        "source": "schema-source/a.schema.json",
                    },
                ],
            }
            (root / "schemas-derive-manifest.json").write_text(
                json.dumps(man), encoding="utf-8"
            )
            with self.assertRaises(ValueError) as ctx:
                ssd.compute_derived(root)
            self.assertIn("rationale", str(ctx.exception).lower())

    def test_stack_sibling_policy_studio_profile(self) -> None:
        profile = RULESPEC_ROOT.parent / "policy-studio" / "profiles" / "studio"
        if not (profile / "schemas-derive-manifest.json").is_file():
            self.skipTest("policy-studio sibling checkout not present")
        files, sums = ssd.compute_derived(profile)
        self.assertEqual(len(files), 24)
        self.assertEqual(len(sums.strip().split("\n")), 24)
        # Byte-stable vs committed tree
        derived = profile / "schemas-derived"
        if not derived.is_dir():
            self.skipTest("schemas-derived not checked in")
        for rel, content in files.items():
            self.assertEqual((derived / rel).read_bytes(), content, rel)


if __name__ == "__main__":
    unittest.main()
