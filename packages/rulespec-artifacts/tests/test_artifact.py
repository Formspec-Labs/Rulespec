from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

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
    Producer,
    admit_artifact,
    build_artifact_root,
    canonical_json_bytes,
    describe_member,
    describe_member_from_receipt,
    framed_section_digest,
    parse_canonical_json,
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
            "pkg:pypi/rulespec-artifacts@1.0.0?checksum=sha256:" + "2" * 64
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


if __name__ == "__main__":
    unittest.main()
