from __future__ import annotations

import contextlib
import errno
import fcntl
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

import canonical_corpus_runner
from rulespec_artifacts import resources
from rulespec_artifacts import __version__ as PACKAGE_VERSION
from rulespec_artifacts import (
    ROOT_OBJECT_KEY,
    ArtifactInput,
    ArtifactVerificationError,
    CompositionRelation,
    DerivationRelation,
    FramedSection,
    ImmutableMemberReceipt,
    KnownLimit,
    LocalBlobSource,
    LocalMemberSource,
    MemberManifestReference,
    MemberNotFoundError,
    MemberSourceError,
    PinnedLocalDirectory,
    Producer,
    admit_artifact,
    build_artifact_root,
    canonical_json_bytes,
    describe_member,
    describe_member_from_receipt,
    framed_section_digest,
    move_child_directory_no_replace,
    parse_canonical_json,
    publish_child_directory_no_replace,
    publish_directory_no_replace,
    schema_bundle_digest,
    sha256_digest,
    validate_composition_relation,
    validate_derivation_relation,
    verify_artifact,
)


class MemorySource:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files

    def keys(self) -> tuple[str, ...]:
        return tuple(self.files)

    @contextlib.contextmanager
    def open(self, key: str):  # type: ignore[no-untyped-def]
        if key not in self.files:
            raise MemberNotFoundError(key)
        yield io.BytesIO(self.files[key])


class ReceiptMemorySource(MemorySource):
    """Test one versioned object store without reading admitted payload bytes."""

    def __init__(
        self,
        files: dict[str, bytes],
        *,
        receipt_overrides: dict[str, ImmutableMemberReceipt] | None = None,
    ) -> None:
        super().__init__(files)
        self.opened: list[str] = []
        self.receipt_overrides = receipt_overrides or {}

    @contextlib.contextmanager
    def open(self, key: str):  # type: ignore[no-untyped-def]
        self.opened.append(key)
        with super().open(key) as stream:
            yield stream

    def receipt(self, object_key: str) -> ImmutableMemberReceipt:
        if object_key not in self.files:
            raise MemberNotFoundError(object_key)
        if object_key in self.receipt_overrides:
            return self.receipt_overrides[object_key]
        payload = self.files[object_key]
        return ImmutableMemberReceipt(
            object_key=object_key,
            byte_size=len(payload),
            sha256=sha256_digest(payload),
            version_id=f"version:{object_key}",
        )


def producer(implementation: str = "1") -> Producer:
    return Producer(
        product="test-product",
        implementation_id=f"git:https://example.test/product@{implementation * 40}",
        verifier_id="urn:test:verifier",
        verifier_version="1.0.0",
        verifier_implementation_id=(
            f"pkg:pypi/rulespec-artifacts@{PACKAGE_VERSION}?checksum=sha256:"
            + "2" * 64
        ),
    )


def artifact_files(
    *, external: bool = False
) -> tuple[dict[str, bytes], dict[str, bytes]]:
    payload = b'{"id":"a"}\n'
    files: dict[str, bytes] = {}
    blobs: dict[str, bytes] = {}
    if external:
        digest = sha256_digest(payload)
        descriptor = describe_member_from_receipt(
            blob_ref=digest,
            role="records",
            media_type="application/jsonl",
            byte_size=len(payload),
            record_count=1,
        )
        blobs[digest] = payload
    else:
        files["records/a.jsonl"] = payload
        descriptor = describe_member(
            MemorySource(files),
            object_key="records/a.jsonl",
            role="records",
            media_type="application/jsonl",
            record_count=1,
        )
    reference, raw_manifest = MemberManifestReference.for_members(
        scope_kind="global",
        scope_id="all",
        object_key="manifests/all.json",
        members=(descriptor,),
    )
    files[reference.object_key] = raw_manifest
    root = build_artifact_root(
        kind="test-artifact",
        spec={"profile": "1"},
        producer=producer(),
        manifests=(reference,),
    )
    files[ROOT_OBJECT_KEY] = canonical_json_bytes(root)
    return files, blobs


class CanonicalTests(unittest.TestCase):
    def test_shared_golden_corpus_covers_encoder_and_parser_boundaries(self) -> None:
        observations = canonical_corpus_runner.evaluate_corpus(
            resources.canonical_json_corpus()
        )
        self.assertEqual(len(observations["encodeAccepted"]), 16)
        self.assertEqual(len(observations["encodeRejected"]), 13)
        self.assertEqual(len(observations["parseRejected"]), 15)

    def test_canonical_json_uses_utf16_order_and_refuses_floats(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"\ue000": 1, "\U00010000": 2}),
            b'{"\xf0\x90\x80\x80":2,"\xee\x80\x80":1}',
        )
        with self.assertRaises(ArtifactVerificationError):
            canonical_json_bytes({"not-exact": 0.5})
        with self.assertRaises(ArtifactVerificationError):
            parse_canonical_json(b'{"b":2,"a":1}')

    def test_framed_section_digest_streams_and_checks_counts(self) -> None:
        records = ({"id": value} for value in ("a", "b"))
        first = framed_section_digest(
            "urn:test:records/1",
            (FramedSection("records", 2, records),),
        )
        second = framed_section_digest(
            "urn:test:records/1",
            (FramedSection("records", 2, ({"id": "a"}, {"id": "b"})),),
        )
        self.assertEqual(first, second)
        with self.assertRaisesRegex(ValueError, "declared 2 records"):
            framed_section_digest(
                "urn:test:records/1",
                (FramedSection("records", 2, ({"id": "a"},)),),
            )

    def test_schema_bundle_ignores_only_ids_and_closes_relative_refs(self) -> None:
        base = {
            "root.json": {
                "$id": "https://one.example/root",
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$ref": "parts/item.json#/$defs/item",
            },
            "parts/item.json": {
                "$id": "https://one.example/item",
                "$defs": {"item": {"type": "string"}},
            },
        }
        changed_ids = json.loads(json.dumps(base))
        changed_ids["root.json"]["$id"] = "https://two.example/root"
        changed_ids["parts/item.json"]["$id"] = "https://two.example/item"
        self.assertEqual(schema_bundle_digest(base), schema_bundle_digest(changed_ids))
        with self.assertRaisesRegex(ValueError, "missing schema"):
            schema_bundle_digest({"root.json": {"$ref": "missing.json"}})


class ArtifactTests(unittest.TestCase):
    def test_optional_relation_helpers_do_not_dispatch_on_product_kind(self) -> None:
        files, _ = artifact_files()
        root = parse_canonical_json(files[ROOT_OBJECT_KEY])
        root_manifest = MemberManifestReference.from_dict(
            root["memberManifests"][0], path="test/reference"
        )
        input_artifact = ArtifactInput(
            "source",
            "urn:test:source:" + "a" * 64,
            "sha256:" + "b" * 64,
        )
        derivation_root = build_artifact_root(
            kind="test-output",
            spec={"profile": "test"},
            producer=producer(),
            inputs=(input_artifact,),
            manifests=(root_manifest,),
        )
        files[ROOT_OBJECT_KEY] = canonical_json_bytes(derivation_root)
        source = MemorySource(files)
        artifact = admit_artifact(source)
        digest = "sha256:" + "c" * 64
        relation = DerivationRelation(
            "urn:test:processor",
            "1",
            digest,
            "urn:test:policy",
            "1",
            digest,
            digest,
            "urn:test:partitioning",
            digest,
            ("records",),
        )
        validate_derivation_relation(artifact, source, relation)

        member_input = ArtifactInput(
            "member",
            artifact.pin.logical_id,
            artifact.pin.artifact_digest,
        )
        composition_root = build_artifact_root(
            kind="test-view",
            spec={"profile": "test"},
            producer=producer(),
            inputs=(member_input,),
        )
        composition_source = MemorySource(
            {ROOT_OBJECT_KEY: canonical_json_bytes(composition_root)}
        )
        composition = admit_artifact(composition_source)
        composition_relation = CompositionRelation(
            "urn:test:merge", "1", digest, ("score", "id")
        )
        validate_composition_relation(composition, composition_relation)

    def test_unknown_product_kind_is_admitted(self) -> None:
        files, _ = artifact_files()
        admitted = admit_artifact(MemorySource(files))
        self.assertEqual(admitted.root["kind"], "test-artifact")
        self.assertEqual(admitted.member_count, 1)

    def test_producer_identity_uses_git_or_published_digest(self) -> None:
        identities = (
            "git:https://example.test/product@" + "1" * 40,
            "git:https://example.test/product@" + "2" * 64,
            "oci://registry.example/product@sha256:" + "3" * 64,
            "https://files.example.test/product.whl#sha256=" + "4" * 64,
            "pkg:pypi/product@1.0.0?checksum=sha256:" + "5" * 64,
        )
        for identity in identities:
            with self.subTest(identity=identity):
                root = build_artifact_root(
                    kind="identity-test",
                    spec={},
                    producer=Producer(
                        "test-product",
                        identity,
                        "urn:test:verifier",
                        "1",
                        identity,
                    ),
                )
                self.assertEqual(root["producer"]["implementationId"], identity)

        for identity in (
            "git:https://example.test/product@" + "6" * 41,
            "urn:test:sha256:not-a-published-digest",
        ):
            with self.subTest(identity=identity), self.assertRaises(
                ArtifactVerificationError
            ):
                build_artifact_root(
                    kind="identity-test",
                    spec={},
                    producer=Producer(
                        "test-product",
                        identity,
                        "urn:test:verifier",
                        "1",
                        identity,
                    ),
                )

    def test_publication_identity_does_not_change_logical_identity(self) -> None:
        first = build_artifact_root(
            kind="test-artifact", spec={"profile": "1"}, producer=producer("1")
        )
        second = build_artifact_root(
            kind="test-artifact", spec={"profile": "1"}, producer=producer("3")
        )
        self.assertEqual(first["logicalId"], second["logicalId"])
        self.assertNotEqual(first["artifactDigest"], second["artifactDigest"])

    def test_inputs_sort_by_role_and_logical_digest(self) -> None:
        first = ArtifactInput("source", "urn:first:" + "b" * 64, "sha256:" + "1" * 64)
        second = ArtifactInput("source", "urn:second:" + "a" * 64, "sha256:" + "2" * 64)
        root = build_artifact_root(
            kind="test-artifact",
            spec={},
            producer=producer(),
            inputs=(first, second),
        )
        self.assertEqual(
            [value["logicalId"] for value in root["inputs"]],
            [second.logical_id, first.logical_id],
        )

    def test_missing_extra_and_changed_members_fail_closed(self) -> None:
        files, _ = artifact_files()
        missing = dict(files)
        missing.pop("records/a.jsonl")
        self.assertEqual(
            verify_artifact(MemorySource(missing)).code, "invalid.membership-missing"
        )
        extra = dict(files, extra=b"x")
        self.assertEqual(
            verify_artifact(MemorySource(extra)).code, "invalid.membership-extra"
        )
        changed = dict(files)
        changed["records/a.jsonl"] = b"changed"
        self.assertEqual(
            verify_artifact(MemorySource(changed)).code, "invalid.member-digest"
        )

    def test_immutable_provider_receipt_avoids_payload_download(self) -> None:
        files, _ = artifact_files()
        source = ReceiptMemorySource(files)

        self.assertEqual(verify_artifact(source).code, "valid")
        self.assertEqual(
            source.opened,
            [ROOT_OBJECT_KEY, "manifests/all.json"],
        )

    def test_immutable_provider_receipt_must_match_exact_member(self) -> None:
        files, _ = artifact_files()
        payload = files["records/a.jsonl"]
        wrong = ImmutableMemberReceipt(
            object_key="records/a.jsonl",
            byte_size=len(payload),
            sha256="sha256:" + "f" * 64,
            version_id="version:wrong-bytes",
        )
        source = ReceiptMemorySource(
            files,
            receipt_overrides={"records/a.jsonl": wrong},
        )

        self.assertEqual(verify_artifact(source).code, "invalid.member-digest")
        self.assertNotIn("records/a.jsonl", source.opened)

    def test_immutable_provider_receipt_refuses_unversioned_object(self) -> None:
        with self.assertRaisesRegex(
            ArtifactVerificationError,
            "non-null immutable provider version",
        ):
            ImmutableMemberReceipt(
                object_key="records/a.jsonl",
                byte_size=1,
                sha256="sha256:" + "f" * 64,
                version_id="null",
            )

    def test_external_blob_uses_injected_digest_source(self) -> None:
        files, blobs = artifact_files(external=True)
        self.assertEqual(
            verify_artifact(MemorySource(files)).code, "invalid.membership-missing"
        )
        self.assertEqual(
            verify_artifact(MemorySource(files), blob_source=MemorySource(blobs)).code,
            "valid",
        )

    def test_known_limit_evidence_must_resolve(self) -> None:
        files, _ = artifact_files()
        manifest = parse_canonical_json(files["manifests/all.json"])
        evidence = manifest["members"][0]["sha256"]
        root = parse_canonical_json(files[ROOT_OBJECT_KEY])
        reference = MemberManifestReference.from_dict(
            root["memberManifests"][0], path="test/reference"
        )
        valid = build_artifact_root(
            kind="test-artifact",
            spec={"profile": "1"},
            producer=producer(),
            manifests=(reference,),
            known_limits=(
                KnownLimit("partial-evidence", "records", "Only one row", (evidence,)),
            ),
        )
        files[ROOT_OBJECT_KEY] = canonical_json_bytes(valid)
        self.assertEqual(verify_artifact(MemorySource(files)).code, "valid")

        invalid = build_artifact_root(
            kind="test-artifact",
            spec={"profile": "1"},
            producer=producer(),
            manifests=(reference,),
            known_limits=(
                KnownLimit(
                    "partial-evidence",
                    "records",
                    "Unknown evidence",
                    ("sha256:" + "f" * 64,),
                ),
            ),
        )
        files[ROOT_OBJECT_KEY] = canonical_json_bytes(invalid)
        self.assertEqual(verify_artifact(MemorySource(files)).code, "invalid.schema")

    def test_local_sources_refuse_symlinked_members(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "real").write_bytes(b"x")
            (root / "link").symlink_to("real")
            with self.assertRaises(ArtifactVerificationError):
                tuple(LocalMemberSource(root).keys())

    def test_local_blob_source_uses_digest_address(self) -> None:
        payload = b"blob"
        digest = sha256_digest(payload)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "sha256" / digest.removeprefix("sha256:")
            target.parent.mkdir()
            target.write_bytes(payload)
            with LocalBlobSource(Path(directory)).open(digest) as stream:
                self.assertEqual(stream.read(), payload)

    def test_local_blob_source_verifies_content_address_on_every_open(self) -> None:
        payload = b"blob"
        digest = sha256_digest(payload)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "sha256" / digest.removeprefix("sha256:")
            target.parent.mkdir()
            target.write_bytes(payload)
            source = LocalBlobSource(Path(directory))

            with source.open(digest) as stream:
                self.assertEqual(stream.read(), payload)

            target.write_bytes(b"evil")
            with self.assertRaises(ArtifactVerificationError) as changed:
                with source.open(digest):
                    pass
            self.assertEqual(changed.exception.issue.code, "invalid.member-digest")

    def test_pinned_local_directory_opens_child_member_and_blob_sources(self) -> None:
        payload = b"blob"
        digest = sha256_digest(payload)
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "distribution"
            artifact = parent / "artifacts" / "child"
            artifact.mkdir(parents=True)
            (artifact / "member.txt").write_bytes(b"member")
            blob = parent / "blobs" / "sha256" / digest.removeprefix("sha256:")
            blob.parent.mkdir(parents=True)
            blob.write_bytes(payload)

            pinned = PinnedLocalDirectory(parent)
            member_source = pinned.member_source("artifacts/child")
            self.assertEqual(set(member_source.keys()), {"member.txt"})
            with member_source.open("member.txt") as stream:
                self.assertEqual(stream.read(), b"member")
            with pinned.blob_source("blobs").open(digest) as stream:
                self.assertEqual(stream.read(), payload)

    def test_pinned_local_directory_rejects_escape_and_linked_child(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "distribution"
            outside = root / "outside"
            parent.mkdir()
            outside.mkdir()
            (parent / "linked").symlink_to(outside, target_is_directory=True)

            pinned = PinnedLocalDirectory(parent)
            with self.assertRaises(ArtifactVerificationError) as escaped:
                pinned.member_source("../outside")
            self.assertEqual(escaped.exception.issue.code, "invalid.path")
            with self.assertRaises(ArtifactVerificationError) as linked:
                pinned.member_source("linked")
            self.assertEqual(linked.exception.issue.code, "invalid.path")

    def test_pinned_local_directory_checks_expected_identity_after_swap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "current"
            replacement = root / "replacement"
            parent.mkdir()
            replacement.mkdir()
            admitted = parent.stat()
            expected_identity = (admitted.st_dev, admitted.st_ino)
            replacement_state = replacement.stat()
            self.assertNotEqual(
                expected_identity,
                (replacement_state.st_dev, replacement_state.st_ino),
            )
            PinnedLocalDirectory(parent, expected_identity=expected_identity)

            parent.rename(root / "original")
            replacement.rename(parent)

            with self.assertRaisesRegex(
                MemberSourceError,
                "does not match its expected device and inode identity",
            ):
                PinnedLocalDirectory(parent, expected_identity=expected_identity)

    def test_pinned_child_sources_reject_parent_replacement(self) -> None:
        payload = b"blob"
        digest = sha256_digest(payload)

        def build_distribution(root: Path) -> None:
            artifact = root / "artifact"
            artifact.mkdir(parents=True)
            (artifact / "member.txt").write_bytes(b"member")
            blob = root / "blobs" / "sha256" / digest.removeprefix("sha256:")
            blob.parent.mkdir(parents=True)
            blob.write_bytes(payload)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "current"
            replacement = root / "replacement"
            build_distribution(parent)
            build_distribution(replacement)
            pinned = PinnedLocalDirectory(parent)
            member_source = pinned.member_source("artifact")
            blob_source = pinned.blob_source("blobs")

            parent.rename(root / "original")
            replacement.rename(parent)

            with self.assertRaisesRegex(MemberSourceError, "parent directory changed"):
                tuple(member_source.keys())
            with self.assertRaisesRegex(MemberSourceError, "parent directory changed"):
                with member_source.open("member.txt"):
                    pass
            with self.assertRaisesRegex(MemberSourceError, "parent directory changed"):
                with blob_source.open(digest):
                    pass

    def test_pinned_child_source_rejects_parent_symlink_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "current"
            replacement = root / "replacement"
            (parent / "artifact").mkdir(parents=True)
            (parent / "artifact" / "member.txt").write_bytes(b"member")
            (replacement / "artifact").mkdir(parents=True)
            (replacement / "artifact" / "member.txt").write_bytes(b"member")
            source = PinnedLocalDirectory(parent).member_source("artifact")

            parent.rename(root / "original")
            parent.symlink_to(replacement, target_is_directory=True)

            with self.assertRaises(ArtifactVerificationError) as linked:
                with source.open("member.txt"):
                    pass
            self.assertEqual(linked.exception.issue.code, "invalid.path")

    def test_local_directory_publication_is_atomic_and_no_replace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "candidate"
            destination = root / "published"
            source.mkdir()
            (source / "member.txt").write_bytes(b"candidate")

            publish_directory_no_replace(source, destination)

            self.assertFalse(source.exists())
            self.assertEqual((destination / "member.txt").read_bytes(), b"candidate")
            self.assertFalse((root / ".published.publish.lock").exists())

            replacement = root / "replacement"
            replacement.mkdir()
            (replacement / "member.txt").write_bytes(b"replacement")
            with self.assertRaises(FileExistsError):
                publish_directory_no_replace(replacement, destination)
            self.assertTrue(replacement.is_dir())
            self.assertEqual((destination / "member.txt").read_bytes(), b"candidate")

    def test_local_directory_publication_refuses_held_lock_then_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "candidate"
            destination = root / "published"
            source.mkdir()
            (source / "member.txt").write_bytes(b"candidate")
            descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError) as held:
                    publish_directory_no_replace(source, destination)
                self.assertEqual(held.exception.errno, errno.EWOULDBLOCK)
                self.assertTrue(source.is_dir())
                self.assertFalse(destination.exists())
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)

            publish_directory_no_replace(source, destination)
            self.assertEqual((destination / "member.txt").read_bytes(), b"candidate")

    def test_pinned_parent_publishes_one_exact_child_without_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_parent = root / "staging"
            destination_parent = root / "artifacts"
            source = source_parent / "candidate"
            source.mkdir(parents=True)
            destination_parent.mkdir()
            (source / "member.txt").write_bytes(b"candidate")
            identity = (source.stat().st_dev, source.stat().st_ino)
            pinned_source = PinnedLocalDirectory(source_parent)
            pinned_destination = PinnedLocalDirectory(destination_parent)

            pinned_source.publish_child_directory_no_replace(
                "candidate",
                pinned_destination,
                "published",
                expected_source_identity=identity,
            )

            self.assertFalse(source.exists())
            self.assertEqual(
                (destination_parent / "published" / "member.txt").read_bytes(),
                b"candidate",
            )
            replacement = source_parent / "replacement"
            replacement.mkdir()
            with self.assertRaises(FileExistsError):
                pinned_source.publish_child_directory_no_replace(
                    "replacement",
                    pinned_destination,
                    "published",
                )

    def test_pinned_parent_moves_cleanup_child_and_checks_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            staging = root / "staging"
            session = staging / "session"
            session.mkdir(parents=True)
            identity = (session.stat().st_dev, session.stat().st_ino)
            pinned = PinnedLocalDirectory(staging)

            pinned.move_child_directory_no_replace(
                "session",
                pinned,
                "tombstone",
                expected_source_identity=identity,
            )

            self.assertFalse(session.exists())
            self.assertTrue((staging / "tombstone").is_dir())
            replacement = staging / "replacement"
            replacement.mkdir()
            with self.assertRaisesRegex(MemberSourceError, "source changed"):
                pinned.move_child_directory_no_replace(
                    "replacement",
                    pinned,
                    "other",
                    expected_source_identity=identity,
                )

    def test_descriptor_relative_child_operations_survive_parent_rename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent = root / "transactions"
            candidate = parent / "candidate"
            cleanup = parent / "cleanup"
            candidate.mkdir(parents=True)
            cleanup.mkdir()
            (candidate / "member.txt").write_bytes(b"candidate")
            candidate_identity = (candidate.stat().st_dev, candidate.stat().st_ino)
            cleanup_identity = (cleanup.stat().st_dev, cleanup.stat().st_ino)
            descriptor = os.open(parent, os.O_RDONLY | os.O_DIRECTORY)
            retained = root / "retained"
            parent.rename(retained)
            parent.symlink_to(root / "outside", target_is_directory=True)
            try:
                publish_child_directory_no_replace(
                    descriptor,
                    descriptor,
                    "candidate",
                    "published",
                    expected_source_identity=candidate_identity,
                )
                move_child_directory_no_replace(
                    descriptor,
                    descriptor,
                    "cleanup",
                    "tombstone",
                    expected_source_identity=cleanup_identity,
                )
            finally:
                os.close(descriptor)

            self.assertEqual(
                (retained / "published" / "member.txt").read_bytes(),
                b"candidate",
            )
            self.assertTrue((retained / "tombstone").is_dir())
            self.assertTrue(parent.is_symlink())


if __name__ == "__main__":
    unittest.main()
