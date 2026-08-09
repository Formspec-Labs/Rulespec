"""Fail-closed tests for Rulespec's in-repo AtlasMembershipReader stub."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.atlas_membership_stub import (
    STUB_FORMAT,
    AtlasMembershipStubError,
    RulespecAtlasMembershipStub,
    write_stub_atlas,
)

DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
CORE_RELEASE = {
    "release_id": "urn:rulespec:core:" + "c" * 64,
    "release_digest": DIGEST_A,
}
SOURCE_RELEASE = "urn:test:release:source"
TARGET_RELEASE = "urn:test:release:target"
SOURCE_MEMBER = "urn:test:concept:source"
TARGET_MEMBER = "urn:test:concept:target"
RELEASES = [
    {
        "release_id": SOURCE_RELEASE,
        "release_digest": DIGEST_A,
        "members": [SOURCE_MEMBER],
    },
    {
        "release_id": TARGET_RELEASE,
        "release_digest": DIGEST_B,
        "members": [TARGET_MEMBER],
    },
]


def _write(root: Path) -> dict[str, Any]:
    return write_stub_atlas(
        root, rulespec_core_release=CORE_RELEASE, releases=RELEASES
    )


def _open(root: Path, selection: dict[str, Any]) -> RulespecAtlasMembershipStub:
    return RulespecAtlasMembershipStub.open(
        root,
        expected_manifest_digest=selection["manifest_digest"],
        expected_output_digest=selection["output_digest"],
    )


class AtlasMembershipStubTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "atlas"
        self.selection = _write(self.root)

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
        self.assertEqual(atlas.rulespec_core_pin().release_id, CORE_RELEASE["release_id"])
        self.assertEqual(atlas.rulespec_core_pin().release_digest, CORE_RELEASE["release_digest"])
        pin = atlas.require_member(member_id=SOURCE_MEMBER, release_id=SOURCE_RELEASE)
        self.assertEqual(pin.release_id, SOURCE_RELEASE)
        self.assertEqual(pin.release_digest, DIGEST_A)
        with self.assertRaisesRegex(AtlasMembershipStubError, "does not contain member"):
            atlas.require_member(member_id="urn:test:concept:missing", release_id=SOURCE_RELEASE)
        with self.assertRaisesRegex(AtlasMembershipStubError, "does not contain member"):
            # A member that exists, but not in the release it is asserted against.
            atlas.require_member(member_id=SOURCE_MEMBER, release_id=TARGET_RELEASE)

    def test_no_downstream_namespace_or_vocabulary_leaks_in(self) -> None:
        atlas = _open(self.root, self.selection)
        self.assertNotIn("refspec", json.dumps(dict(atlas.manifest)).lower())
        self.assertEqual(atlas.manifest["format"], STUB_FORMAT)

    def test_rejects_manifest_tampering(self) -> None:
        manifest_path = self.root / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["rulespecCoreRelease"]["releaseDigest"] = DIGEST_B
        manifest_path.write_bytes(
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
            + b"\n"
        )
        # Reopening with the *original* selection now fails the manifest-digest
        # check (the bytes changed underneath the pin).
        with self.assertRaisesRegex(AtlasMembershipStubError, "bytes differ"):
            _open(self.root, self.selection)

    def test_rejects_members_tampering_even_with_a_refreshed_manifest_digest(self) -> None:
        # Simulate an attacker who edits members.json and updates the *outer*
        # selection pin to match the new bytes, without redoing the whole
        # atlas: the generationDigest/id inside manifest.json must still not
        # match, because they are computed over the ORIGINAL membersDigest.
        members_path = self.root / "members.json"
        members = json.loads(members_path.read_bytes())
        members["releases"][0]["members"].append("urn:test:concept:injected")
        tampered = (
            json.dumps(members, sort_keys=True, separators=(",", ":")).encode("utf-8")
            + b"\n"
        )
        members_path.write_bytes(tampered)
        from tools.atlas_membership_stub import content_digest  # local import: test-only

        selection = dict(self.selection)
        selection["output_digest"] = content_digest(tampered)
        with self.assertRaisesRegex(
            AtlasMembershipStubError, "membersDigest differs from members.json"
        ):
            _open(self.root, selection)

    def test_recomputes_generation_identity_from_exact_inputs(self) -> None:
        manifest_path = self.root / "manifest.json"
        manifest = json.loads(manifest_path.read_bytes())
        manifest["rulespecCoreRelease"]["releaseId"] = "urn:rulespec:core:" + "d" * 64
        manifest["generationDigest"] = "sha256:" + "0" * 64
        payload = (
            json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
            + b"\n"
        )
        manifest_path.write_bytes(payload)
        from tools.atlas_membership_stub import content_digest  # local import: test-only

        selection = dict(self.selection)
        selection["manifest_digest"] = content_digest(payload)
        with self.assertRaisesRegex(
            AtlasMembershipStubError, "generationDigest differs from its exact inputs"
        ):
            _open(self.root, selection)

    def test_rejects_symlinked_directory(self) -> None:
        link = Path(self.temporary.name) / "atlas-link"
        link.symlink_to(self.root)
        with self.assertRaisesRegex(AtlasMembershipStubError, "must not be a symlink"):
            _open(link, self.selection)

    def test_rejects_a_release_missing_from_the_membership_table(self) -> None:
        atlas = _open(self.root, self.selection)
        with self.assertRaisesRegex(AtlasMembershipStubError, "does not contain member"):
            atlas.require_member(member_id=SOURCE_MEMBER, release_id="urn:test:release:unknown")


if __name__ == "__main__":
    unittest.main()
