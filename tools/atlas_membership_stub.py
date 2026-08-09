"""A minimal, rulespec-native stand-in for ``AtlasMembershipReader``.

``tools/rulespec_release.py`` and ``tools/extrapolation_release_v2.py`` each
declare an ``AtlasMembershipReader`` Protocol: a release may pin an external,
product-owned atlas asset that proves reference-resource membership, and
Rulespec's validators verify that pin against whatever reader a caller
supplies. That interface is legitimate and does not change here.

This module is not a reader for any downstream consumer's wire format,
namespace, or distribution shape. It exists only so this repository's own
tests and fixture builders have something real to hand the validators: a
tiny, self-authored, tamper-evident membership table expressed entirely in
Rulespec's own JSON conventions (the ``canonical_digest`` /
``canonical_json_bytes`` helpers already used throughout
``tools/rulespec_release.py``).

On disk, one stub atlas is a directory with two files:

``manifest.json``
    ``format``, a content-derived ``id``, the pinned ``rulespecCoreRelease``,
    and a digest of ``members.json``, closed by a self-referential
    ``generationDigest`` -- change any field and the id and generation
    digest stop matching, so tampering is caught the same way the rest of
    the release tooling already catches it.

``members.json``
    A small table of ``{releaseId, releaseDigest, members: [...]}`` rows:
    the exact membership facts ``require_member`` proves.

A production release may still pin a real, external atlas asset -- the
Protocol does not change, and a caller is free to construct any object that
satisfies it and pass that in directly. This module is not that atlas; it is
what lets Rulespec test and build fixtures for that seam without vendoring
one.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self

try:
    from rulespec_release import canonical_digest, canonical_json_bytes, content_digest
except ModuleNotFoundError:  # imported as a tools package
    from tools.rulespec_release import (
        canonical_digest,
        canonical_json_bytes,
        content_digest,
    )

STUB_FORMAT = "rulespec-atlas-membership-stub-1.0"

_MANIFEST_FIELDS = {
    "format",
    "id",
    "rulespecCoreRelease",
    "membersDigest",
    "generationDigest",
}
_CORE_PIN_FIELDS = {"releaseId", "releaseDigest"}
_RELEASE_ROW_FIELDS = {"releaseId", "releaseDigest", "members"}


class AtlasMembershipStubError(ValueError):
    """The stub atlas directory does not prove the requested membership."""


@dataclass(frozen=True, slots=True)
class AtlasReleasePin:
    """One exact release identity -- structurally an ``ExactReleaseIdentity``."""

    release_id: str
    release_digest: str


def _mapping(value: object, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AtlasMembershipStubError(f"{label} must be an object")
    return value


def _require_str(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AtlasMembershipStubError(f"{label} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class RulespecAtlasMembershipStub:
    """An in-repo, minimal ``AtlasMembershipReader`` for tests and fixtures."""

    manifest: Mapping[str, Any]
    manifest_digest: str
    members_digest: str
    _releases: Mapping[str, tuple[str, frozenset[str]]]

    @classmethod
    def open(
        cls,
        directory: Path | str,
        *,
        expected_manifest_digest: str,
        expected_output_digest: str,
    ) -> Self:
        """Open one stub atlas selected only by its two external file digests."""

        root = Path(directory)
        if root.is_symlink():
            raise AtlasMembershipStubError(
                "stub atlas directory must not be a symlink"
            )
        try:
            root = root.resolve(strict=True)
        except FileNotFoundError as error:
            raise AtlasMembershipStubError(
                "stub atlas directory does not exist"
            ) from error
        if not root.is_dir():
            raise AtlasMembershipStubError("stub atlas path must be a directory")

        manifest_path = root / "manifest.json"
        members_path = root / "members.json"
        for path in (manifest_path, members_path):
            if path.is_symlink() or not path.is_file():
                raise AtlasMembershipStubError(f"{path.name} must be a regular file")

        manifest_bytes = manifest_path.read_bytes()
        if content_digest(manifest_bytes) != expected_manifest_digest:
            raise AtlasMembershipStubError(
                "stub atlas manifest bytes differ from the external pin"
            )
        members_bytes = members_path.read_bytes()
        members_digest = content_digest(members_bytes)
        if members_digest != expected_output_digest:
            raise AtlasMembershipStubError(
                "stub atlas members bytes differ from the external pin"
            )

        try:
            manifest = json.loads(manifest_bytes)
        except json.JSONDecodeError as error:
            raise AtlasMembershipStubError(
                "manifest.json is not valid JSON"
            ) from error
        if not isinstance(manifest, dict):
            raise AtlasMembershipStubError("manifest.json must contain a JSON object")
        if manifest_bytes != canonical_json_bytes(manifest) + b"\n":
            raise AtlasMembershipStubError("manifest.json bytes are not canonical")
        if set(manifest) != _MANIFEST_FIELDS or manifest.get("format") != STUB_FORMAT:
            raise AtlasMembershipStubError("manifest.json has unsupported fields")
        if manifest.get("membersDigest") != members_digest:
            raise AtlasMembershipStubError(
                "manifest.json membersDigest differs from members.json"
            )
        core_pin = _mapping(
            manifest.get("rulespecCoreRelease"), label="rulespecCoreRelease"
        )
        if set(core_pin) != _CORE_PIN_FIELDS:
            raise AtlasMembershipStubError(
                "rulespecCoreRelease has unsupported fields"
            )
        _require_str(core_pin.get("releaseId"), label="rulespecCoreRelease releaseId")
        _require_str(
            core_pin.get("releaseDigest"), label="rulespecCoreRelease releaseDigest"
        )

        generation_digest = canonical_digest(
            {
                "format": STUB_FORMAT,
                "rulespecCoreRelease": dict(core_pin),
                "membersDigest": members_digest,
            }
        )
        if manifest.get("generationDigest") != generation_digest:
            raise AtlasMembershipStubError(
                "manifest.json generationDigest differs from its exact inputs"
            )
        expected_id = "urn:rulespec:atlas-membership-stub:" + (
            generation_digest.removeprefix("sha256:")
        )
        if manifest.get("id") != expected_id:
            raise AtlasMembershipStubError(
                "manifest.json id does not match its generation digest"
            )

        try:
            members_doc = json.loads(members_bytes)
        except json.JSONDecodeError as error:
            raise AtlasMembershipStubError(
                "members.json is not valid JSON"
            ) from error
        if not isinstance(members_doc, dict):
            raise AtlasMembershipStubError("members.json must contain a JSON object")
        if members_bytes != canonical_json_bytes(members_doc) + b"\n":
            raise AtlasMembershipStubError("members.json bytes are not canonical")
        if set(members_doc) != {"releases"}:
            raise AtlasMembershipStubError("members.json has unsupported fields")
        rows = members_doc["releases"]
        if not isinstance(rows, list) or not rows:
            raise AtlasMembershipStubError(
                "members.json releases must be a non-empty array"
            )
        releases: dict[str, tuple[str, frozenset[str]]] = {}
        for raw_row in rows:
            row = _mapping(raw_row, label="members.json release row")
            if set(row) != _RELEASE_ROW_FIELDS:
                raise AtlasMembershipStubError("release row has unsupported fields")
            release_id = _require_str(
                row.get("releaseId"), label="release row releaseId"
            )
            if release_id in releases:
                raise AtlasMembershipStubError(f"release row repeats {release_id!r}")
            release_digest = _require_str(
                row.get("releaseDigest"), label="release row releaseDigest"
            )
            members = row.get("members")
            if (
                not isinstance(members, list)
                or not members
                or any(
                    not isinstance(member, str) or not member.strip()
                    for member in members
                )
            ):
                raise AtlasMembershipStubError(
                    f"release row {release_id!r} members must be a non-empty "
                    "array of strings"
                )
            if len(set(members)) != len(members):
                raise AtlasMembershipStubError(
                    f"release row {release_id!r} repeats a member"
                )
            releases[release_id] = (release_digest, frozenset(members))

        return cls(
            manifest=manifest,
            manifest_digest=expected_manifest_digest,
            members_digest=members_digest,
            _releases=releases,
        )

    @property
    def asset_id(self) -> str:
        """Return the content-derived stub atlas identifier."""

        return str(self.manifest["id"])

    def pin(self) -> dict[str, str]:
        """Return the exact fields an ExtrapolationRelease should retain."""

        return {
            "asset_id": self.asset_id,
            "manifest_digest": self.manifest_digest,
            "distribution_digest": self.members_digest,
        }

    def rulespec_core_pin(self) -> AtlasReleasePin:
        """Return the one Rulespec Core identity sealed into the manifest."""

        core_pin = self.manifest["rulespecCoreRelease"]
        return AtlasReleasePin(
            release_id=str(core_pin["releaseId"]),
            release_digest=str(core_pin["releaseDigest"]),
        )

    def require_member(self, *, member_id: str, release_id: str) -> AtlasReleasePin:
        """Return the exact release pin or reject an assignment target."""

        entry = self._releases.get(release_id)
        if entry is None or member_id not in entry[1]:
            raise AtlasMembershipStubError(
                f"stub atlas release {release_id} does not contain member "
                f"{member_id}"
            )
        release_digest, _members = entry
        return AtlasReleasePin(release_id=release_id, release_digest=release_digest)


def write_stub_atlas(
    directory: Path,
    *,
    rulespec_core_release: Mapping[str, str],
    releases: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    """Write one canonical stub atlas directory and return its selection pin.

    ``releases`` is a sequence of ``{"release_id", "release_digest",
    "members"}`` rows. Used by the fixture builders and by this module's own
    tests -- never by production code, which only ever receives an
    ``AtlasMembershipReader`` through dependency injection.
    """

    core_pin = {
        "releaseId": _require_str(
            rulespec_core_release.get("release_id"),
            label="rulespec_core_release release_id",
        ),
        "releaseDigest": _require_str(
            rulespec_core_release.get("release_digest"),
            label="rulespec_core_release release_digest",
        ),
    }
    rows = [
        {
            "releaseId": _require_str(
                release.get("release_id"), label="release release_id"
            ),
            "releaseDigest": _require_str(
                release.get("release_digest"), label="release release_digest"
            ),
            "members": [str(member) for member in release["members"]],
        }
        for release in releases
    ]
    members_doc = {"releases": rows}
    members_bytes = canonical_json_bytes(members_doc) + b"\n"
    members_digest = content_digest(members_bytes)
    generation_digest = canonical_digest(
        {
            "format": STUB_FORMAT,
            "rulespecCoreRelease": core_pin,
            "membersDigest": members_digest,
        }
    )
    manifest = {
        "format": STUB_FORMAT,
        "id": "urn:rulespec:atlas-membership-stub:"
        + generation_digest.removeprefix("sha256:"),
        "rulespecCoreRelease": core_pin,
        "membersDigest": members_digest,
        "generationDigest": generation_digest,
    }
    manifest_bytes = canonical_json_bytes(manifest) + b"\n"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_bytes(manifest_bytes)
    (directory / "members.json").write_bytes(members_bytes)
    return {
        "manifest_digest": content_digest(manifest_bytes),
        "output_digest": members_digest,
    }


__all__ = [
    "STUB_FORMAT",
    "AtlasMembershipStubError",
    "AtlasReleasePin",
    "RulespecAtlasMembershipStub",
    "write_stub_atlas",
]
