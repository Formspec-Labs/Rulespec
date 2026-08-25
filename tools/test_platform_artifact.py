"""Focused conformance tests for the shared platform artifact protocol."""

from __future__ import annotations

import gc
import io
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import tracemalloc
import unittest
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

import jsonschema
from rulespec_conformance.contract import resources

from tools.constraints_compile import (
    parse_cue_file,
    target_json_schema,
    target_rust,
    target_typescript,
)
from tools.platform_artifact import (
    FORMAT,
    FORMAT_VERSION,
    ROOT_OBJECT_KEY,
    SOURCE_CATALOG_ITEM_SCHEMA_ID,
    ArtifactInput,
    ArtifactPin,
    ArtifactVerificationError,
    CanonicalSetDigester,
    CompositionSpec,
    DerivationSpec,
    LocalFileStateIndex,
    LocalMemberSource,
    MemberDescriptor,
    MemberManifestReference,
    MemberNotFoundError,
    MemberSource,
    MemberSourceError,
    SourceCatalogSpec,
    admit_artifact,
    build_artifact_root,
    canonical_json_bytes,
    describe_member,
    describe_member_from_receipt,
    expected_artifact_digest,
    expected_logical_id,
    iter_member_descriptors,
    parse_canonical_json,
    sha256_digest,
    source_catalog_item_schema_bytes,
    stamp_root,
    verify_artifact,
    write_member_manifest,
)


class MemoryMemberSource:
    """Small injected test double for storage-independent verification."""

    def __init__(self, files: dict[str, bytes], *, chunk_size: int | None = None) -> None:
        self.files = dict(files)
        self.chunk_size = chunk_size

    def keys(self) -> Sequence[str]:
        return tuple(self.files)

    @contextmanager
    def open(self, object_key: str) -> Iterator[io.BytesIO]:
        if object_key not in self.files:
            raise MemberNotFoundError(object_key)
        stream: io.BytesIO
        if self.chunk_size is None:
            stream = io.BytesIO(self.files[object_key])
        else:
            stream = ChunkedBytesIO(self.files[object_key], self.chunk_size)
        try:
            yield stream
        finally:
            stream.close()


class SqliteBlobMemberSource:
    """Streaming object-store fixture backed by SQLite BLOB handles."""

    def __init__(self, path: Path) -> None:
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            "CREATE TABLE objects (id INTEGER PRIMARY KEY, object_key TEXT UNIQUE, payload BLOB)"
        )

    def put(self, object_key: str, payload: bytes) -> None:
        self.connection.execute(
            "INSERT INTO objects (object_key, payload) VALUES (?, ?)",
            (object_key, payload),
        )

    def keys(self) -> Iterator[str]:
        for row in self.connection.execute("SELECT object_key FROM objects ORDER BY object_key"):
            yield str(row[0])

    @contextmanager
    def open(self, object_key: str) -> Iterator[object]:
        row = self.connection.execute(
            "SELECT id FROM objects WHERE object_key = ?",
            (object_key,),
        ).fetchone()
        if row is None:
            raise MemberNotFoundError(object_key)
        blob = self.connection.blobopen("objects", "payload", int(row[0]), readonly=True)
        try:
            yield blob
        finally:
            blob.close()

    def close(self) -> None:
        self.connection.close()


class PackagedSchemaTests(unittest.TestCase):
    def test_source_catalog_item_schema_has_one_public_identity(self) -> None:
        schema = json.loads(source_catalog_item_schema_bytes())

        self.assertEqual(schema["$id"], SOURCE_CATALOG_ITEM_SCHEMA_ID)
        self.assertIn("sourceItemId", schema["required"])


class PackagedFixtureCorpusTests(unittest.TestCase):
    def test_common_structural_corpus_returns_every_declared_code(self) -> None:
        corpus = resources.platform_artifact_fixture_corpus()
        observed: dict[str, str] = {}
        for case in corpus["cases"]:
            name = case["name"]
            fixture = Path(str(resources.platform_artifact_fixture(name)))
            observed[name] = verify_artifact(LocalMemberSource(fixture)).code

        self.assertEqual(
            observed,
            {case["name"]: case["expectedCode"] for case in corpus["cases"]},
        )
        self.assertTrue(
            {
                "invalid.root-syntax",
                "invalid.identity",
                "invalid.path",
                "invalid.manifest",
                "invalid.membership-missing",
                "invalid.membership-extra",
                "invalid.member-digest",
                "invalid.schema",
                "invalid.statistics",
            }
            <= set(observed.values())
        )


class CanonicalSetDigesterTests(unittest.TestCase):
    def test_stream_matches_canonical_sorted_set_bytes(self) -> None:
        digester = CanonicalSetDigester()
        for value in ("alpha", "bravo", "charlie"):
            digester.add(value)

        self.assertEqual(digester.finish(), sha256_digest(["alpha", "bravo", "charlie"]))
        self.assertEqual(digester.finish(), sha256_digest(["alpha", "bravo", "charlie"]))

    def test_refuses_unsorted_or_repeated_values(self) -> None:
        for values in (("bravo", "alpha"), ("alpha", "alpha")):
            digester = CanonicalSetDigester()
            digester.add(values[0])
            with self.subTest(values=values), self.assertRaisesRegex(ValueError, "sorted and distinct"):
                digester.add(values[1])

    def test_invalid_value_does_not_mutate_the_digest(self) -> None:
        digester = CanonicalSetDigester()
        with self.assertRaises(ArtifactVerificationError):
            digester.add("\ud800")
        digester.add("alpha")

        self.assertEqual(digester.finish(), sha256_digest(["alpha"]))


class ChunkedBytesIO(io.BytesIO):
    def __init__(self, value: bytes, chunk_size: int) -> None:
        super().__init__(value)
        self.chunk_size = chunk_size

    def read(self, size: int = -1) -> bytes:
        selected = self.chunk_size if size < 0 else min(size, self.chunk_size)
        return super().read(selected)


def descriptor(
    object_key: str,
    payload: bytes,
    *,
    records: int = 1,
    role: str = "records",
) -> MemberDescriptor:
    return MemberDescriptor(
        object_key=object_key,
        role=role,
        media_type="application/json",
        byte_size=len(payload),
        sha256=sha256_digest(payload),
        record_count=records,
        schema_id="https://example.test/schemas/records-v1",
    )


def artifact_files(
    *,
    payloads: dict[str, bytes] | None = None,
    partitions: tuple[tuple[str, tuple[str, ...]], ...] | None = None,
    inputs: tuple[ArtifactInput, ...] = (),
    roles: Mapping[str, str] | None = None,
) -> dict[str, bytes]:
    selected_payloads = payloads or {
        "payload/a.json": b'{"id":"a"}',
        "payload/b.json": b'{"id":"b"}',
    }
    selected_partitions = partitions or (
        ("east", ("payload/b.json",)),
        ("west", ("payload/a.json",)),
    )
    references: list[MemberManifestReference] = []
    files = dict(selected_payloads)
    members_by_key = {
        key: descriptor(key, payload, role=(roles or {}).get(key, "records"))
        for key, payload in selected_payloads.items()
    }
    for scope_id, keys in selected_partitions:
        object_key = f"manifests/{scope_id}.json"
        reference, raw = MemberManifestReference.for_members(
            scope_kind="partition",
            scope_id=scope_id,
            object_key=object_key,
            members=tuple(members_by_key[key] for key in keys),
        )
        references.append(reference)
        files[object_key] = raw
    references.sort(key=lambda item: (item.scope_kind, item.scope_id, item.object_key))
    root = stamp_root(
        {
            "counts": {
                "manifestCount": len(references),
                "memberCount": len(selected_payloads),
                "totalMemberByteSize": sum(map(len, selected_payloads.values())),
                "totalRecordCount": len(selected_payloads),
            },
            "coverage": {
                "accountedInputCount": len(selected_payloads),
                "complete": True,
                "unaccountedInputCount": 0,
            },
            "format": FORMAT,
            "formatVersion": FORMAT_VERSION,
            "inputs": [item.as_dict() for item in inputs],
            "kind": "source-catalog",
            "memberManifests": [item.as_dict() for item in references],
            "spec": {
                "catalogId": "urn:example:catalog",
                "requestedUniverseSetDigest": "sha256:" + "3" * 64,
                "selectedSourceSetDigest": "sha256:" + "4" * 64,
                "selectionPolicyDigest": "sha256:" + "5" * 64,
                "selectionPolicyId": "urn:example:selection-policy",
                "selectionPolicyVersion": "1",
                "sourceSystemId": "urn:example:source-system",
                "sourceSystemVersion": "1",
            },
        }
    )
    files[ROOT_OBJECT_KEY] = canonical_json_bytes(root)
    return files


def replace_root(files: dict[str, bytes], change: object) -> dict[str, bytes]:
    updated = dict(files)
    root = parse_canonical_json(updated[ROOT_OBJECT_KEY])
    assert isinstance(root, dict)
    change(root)
    updated[ROOT_OBJECT_KEY] = canonical_json_bytes(root)
    return updated


class CanonicalJsonTests(unittest.TestCase):
    def test_utf16_key_order_matches_rfc_8785(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"\ue000": 1, "\U00010000": 2}),
            b'{"\xf0\x90\x80\x80":2,"\xee\x80\x80":1}',
        )

    def test_float_duplicate_bom_and_noncanonical_bytes_are_refused(self) -> None:
        for raw in (
            b'{"a":1.5}',
            b'{"a":1,"a":2}',
            b'\xef\xbb\xbf{"a":1}',
            b'{"b":2,"a":1}',
        ):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    parse_canonical_json(raw)


class GeneratedShapeTests(unittest.TestCase):
    def test_platform_cue_generates_closed_plain_json(self) -> None:
        source = Path(__file__).parents[1] / "constraints/platform/platform-artifact.cue"
        document = parse_cue_file(source)
        schema = json.loads(target_json_schema(document))
        definitions = schema["$defs"]
        for name in (
            "PlatformSourceCatalogArtifact",
            "PlatformDerivationArtifact",
            "PlatformCompositionArtifact",
        ):
            self.assertIs(definitions[name]["additionalProperties"], False)
            self.assertEqual(definitions[name]["properties"]["inputs"]["type"], "array")
            self.assertTrue(definitions[name]["properties"]["inputs"]["uniqueItems"])
        counts = definitions["PlatformArtifactCounts"]["properties"]
        self.assertEqual(counts["manifestCount"]["type"], "integer")
        self.assertEqual(counts["manifestCount"]["maximum"], (1 << 53) - 1)
        rust = target_rust(document, source_file=source)
        self.assertIn("#[serde(deny_unknown_fields)]", rust)
        self.assertIn("pub manifest_count: i64", rust)
        self.assertNotIn("pub manifest_count: f64", rust)
        self.assertNotIn("pub extra:", rust)
        self.assertNotIn("pub id: Option<String>", rust)
        typescript = target_typescript(document, source_file=source)
        self.assertIn('errs.push("inputs: duplicate items")', typescript)
        self.assertIn('errs.push("expectedOutputRoles: duplicate items")', typescript)
        self.assertIn('errs.push("totalOrderKey: duplicate items")', typescript)
        self.assertIn('errs.push("format: must equal spicy-artifact")', typescript)
        self.assertIn('errs.push("complete: must equal True")', typescript)
        self.assertIn("validatePlatformCompositionInput(value)", typescript)
        self.assertIn('errs.push("manifestCount: must be a safe integer")', typescript)
        self.assertIn("canonicalJsonKey(item)", typescript)
        self.assertNotIn("JSON.stringify(item)", typescript)
        self.assertIn(
            "Plain data carriers only; admit bytes with rulespec_conformance.platform_artifact.",
            rust,
        )
        self.assertIn("pub id: String", rust)
        self.assertNotIn("pub id_2: String", rust)

    @unittest.skipUnless(shutil.which("node"), "Node.js is required to execute generated TypeScript")
    def test_platform_typescript_validator_handles_object_order_and_single_list_errors(self) -> None:
        source = Path(__file__).parents[1] / "constraints/platform/platform-artifact.cue"
        typescript = target_typescript(parse_cue_file(source), source_file=source)
        digest = "sha256:" + "1" * 64
        root = build_artifact_root(
            spec=CompositionSpec(
                "urn:example:merge",
                "1",
                digest,
                ("score", "logical-id"),
            ),
            inputs=(ArtifactInput("member", "urn:example:source", digest),),
            manifests=(),
            accounted_input_count=1,
        )
        executable = typescript + "\n" + f"""
const valid: any = {json.dumps(root)};
const first = {{role: "member", logicalId: "urn:example:source", artifactDigest: "{digest}"}};
const second = {{artifactDigest: "{digest}", logicalId: "urn:example:source", role: "member"}};
const duplicate: any = structuredClone(valid);
duplicate.inputs = [first, second];
const duplicateErrors = validatePlatformCompositionArtifact(duplicate);
if (JSON.stringify(duplicateErrors) !== JSON.stringify(["inputs: duplicate items"])) {{
  throw new Error(`unexpected duplicate diagnostics: ${{JSON.stringify(duplicateErrors)}}`);
}}
const wrongList: any = structuredClone(valid);
wrongList.memberManifests = {{}};
const listErrors = validatePlatformCompositionArtifact(wrongList);
if (listErrors.filter((item) => item === "memberManifests: must be an array").length !== 1) {{
  throw new Error(`duplicate list diagnostics: ${{JSON.stringify(listErrors)}}`);
}}
if (listErrors.some((item) => item.includes("< 0 items"))) {{
  throw new Error(`impossible cardinality diagnostic: ${{JSON.stringify(listErrors)}}`);
}}
"""
        with tempfile.TemporaryDirectory() as directory:
            program = Path(directory) / "platform-artifact.ts"
            program.write_text(executable, encoding="utf-8")
            completed = subprocess.run(
                ["node", "--experimental-strip-types", str(program)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_generated_schema_validates_the_root_directly(self) -> None:
        source = Path(__file__).parents[1] / "constraints/platform/platform-artifact.cue"
        schema = json.loads(target_json_schema(parse_cue_file(source)))
        root = parse_canonical_json(artifact_files()[ROOT_OBJECT_KEY])
        jsonschema.Draft202012Validator(schema).validate(root)
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate({})

        derivation = dict(root)
        derivation.update(
            {
                "inputs": [],
                "kind": "derivation",
                "spec": {
                    "expectedOutputRoles": ["records"],
                    "parametersDigest": "sha256:" + "1" * 64,
                    "partitioningDigest": "sha256:" + "2" * 64,
                    "partitioningId": "urn:example:partitioning",
                    "policyDigest": "sha256:" + "3" * 64,
                    "policyId": "urn:example:policy",
                    "policyVersion": "1",
                    "processorDigest": "sha256:" + "4" * 64,
                    "processorId": "urn:example:processor",
                    "processorVersion": "1",
                },
            }
        )
        composition = dict(root)
        composition.update(
            {
                "inputs": [
                    {
                        "artifactDigest": "sha256:" + "5" * 64,
                        "logicalId": "urn:example:member",
                        "role": "source",
                    }
                ],
                "kind": "composition",
                "spec": {
                    "mergePolicyDigest": "sha256:" + "6" * 64,
                    "mergePolicyId": "urn:example:merge-policy",
                    "mergePolicyVersion": "1",
                    "totalOrderKey": ["score", "subject"],
                },
            }
        )
        incomplete = json.loads(json.dumps(root))
        incomplete["coverage"] = {
            "accountedInputCount": 1,
            "complete": False,
            "unaccountedInputCount": 1,
        }
        bad_role = json.loads(json.dumps(derivation))
        bad_role["inputs"] = [
            {
                "artifactDigest": "sha256:" + "7" * 64,
                "logicalId": "urn:example:source",
                "role": "source",
            }
        ]
        bad_role["spec"]["expectedOutputRoles"] = ["Bad Role"]
        validator = jsonschema.Draft202012Validator(schema)
        for invalid in (derivation, composition, incomplete, bad_role):
            with self.subTest(kind=invalid["kind"]):
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(invalid)


class IdentityTests(unittest.TestCase):
    def test_physical_input_pin_does_not_change_logical_identity(self) -> None:
        first_input = ArtifactInput("source", "urn:example:source", "sha256:" + "1" * 64)
        second_input = ArtifactInput("source", "urn:example:source", "sha256:" + "2" * 64)
        first = artifact_files(inputs=(first_input,))
        second = artifact_files(inputs=(second_input,))
        first_root = parse_canonical_json(first[ROOT_OBJECT_KEY])
        second_root = parse_canonical_json(second[ROOT_OBJECT_KEY])
        self.assertEqual(first_root["logicalId"], second_root["logicalId"])
        self.assertNotEqual(first_root["artifactDigest"], second_root["artifactDigest"])

    def test_logical_input_change_moves_both_identities(self) -> None:
        first = artifact_files(
            inputs=(ArtifactInput("source", "urn:example:first", "sha256:" + "1" * 64),)
        )
        second = artifact_files(
            inputs=(ArtifactInput("source", "urn:example:second", "sha256:" + "1" * 64),)
        )
        first_root = parse_canonical_json(first[ROOT_OBJECT_KEY])
        second_root = parse_canonical_json(second[ROOT_OBJECT_KEY])
        self.assertNotEqual(first_root["logicalId"], second_root["logicalId"])
        self.assertNotEqual(first_root["artifactDigest"], second_root["artifactDigest"])

    def test_derivation_role_order_is_canonicalized_before_identity(self) -> None:
        member = descriptor("payload/one.json", b"{}")
        manifest, _ = MemberManifestReference.for_members(
            scope_kind="global",
            scope_id="all",
            object_key="manifests/all.json",
            members=(member,),
        )
        fields = {
            "processor_id": "urn:example:processor",
            "processor_version": "1",
            "processor_digest": "sha256:" + "1" * 64,
            "policy_id": "urn:example:policy",
            "policy_version": "1",
            "policy_digest": "sha256:" + "2" * 64,
            "parameters_digest": "sha256:" + "3" * 64,
            "partitioning_id": "urn:example:partitioning",
            "partitioning_digest": "sha256:" + "4" * 64,
        }
        source = ArtifactInput("source", "urn:example:source", "sha256:" + "5" * 64)
        first = build_artifact_root(
            spec=DerivationSpec(**fields, expected_output_roles=("records", "metrics")),
            inputs=(source,),
            manifests=(manifest,),
            accounted_input_count=1,
        )
        second = build_artifact_root(
            spec=DerivationSpec(**fields, expected_output_roles=("metrics", "records")),
            inputs=(source,),
            manifests=(manifest,),
            accounted_input_count=1,
        )
        self.assertEqual(first, second)

        noncanonical = json.loads(json.dumps(first))
        noncanonical["spec"]["expectedOutputRoles"] = ["records", "metrics"]
        noncanonical["logicalId"] = expected_logical_id(noncanonical)
        noncanonical["artifactDigest"] = expected_artifact_digest(noncanonical)
        self.assertEqual(
            verify_artifact(
                MemoryMemberSource({ROOT_OBJECT_KEY: canonical_json_bytes(noncanonical)})
            ).code,
            "invalid.schema",
        )


class StructuralVerificationTests(unittest.TestCase):
    def test_producer_helpers_use_the_same_injected_member_source_and_identity(self) -> None:
        payload = b'{"id":"one"}'
        source = MemoryMemberSource({"payload/one.json": payload}, chunk_size=2)
        member = describe_member(
            source,
            object_key="payload/one.json",
            role="records",
            media_type="application/json",
            record_count=1,
        )
        reference, manifest_raw = MemberManifestReference.for_members(
            scope_kind="global",
            scope_id="all",
            object_key="manifests/all.json",
            members=(member,),
        )
        root = build_artifact_root(
            spec=SourceCatalogSpec(
                catalog_id="urn:example:catalog",
                requested_universe_set_digest="sha256:" + "3" * 64,
                selected_source_set_digest="sha256:" + "4" * 64,
                selection_policy_digest="sha256:" + "5" * 64,
                selection_policy_id="urn:example:selection-policy",
                selection_policy_version="1",
                source_system_id="urn:example:source-system",
                source_system_version="1",
            ),
            inputs=(),
            manifests=(reference,),
            accounted_input_count=1,
        )
        files = {
            "artifact.json": canonical_json_bytes(root),
            "manifests/all.json": manifest_raw,
            "payload/one.json": payload,
        }
        result = verify_artifact(MemoryMemberSource(files, chunk_size=2))
        self.assertEqual(result.code, "valid")
        self.assertEqual(root["counts"]["totalMemberByteSize"], len(payload))

    def test_partitioned_artifact_verifies_through_injected_and_local_storage(self) -> None:
        files = artifact_files()
        memory_result = verify_artifact(MemoryMemberSource(files, chunk_size=3))
        self.assertEqual(memory_result.code, "valid")
        self.assertIsNotNone(memory_result.artifact)
        self.assertEqual(memory_result.artifact.member_count, 2)
        self.assertEqual(
            [member.object_key for member in iter_member_descriptors(
                memory_result.artifact,
                MemoryMemberSource(files, chunk_size=3),
            )],
            ["payload/b.json", "payload/a.json"],
        )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, raw in files.items():
                path = root / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            self.assertEqual(verify_artifact(LocalMemberSource(root)).code, "valid")

    def test_local_admission_returns_payload_states_from_the_digest_pass(self) -> None:
        files = artifact_files()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, raw in files.items():
                path = root / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)

            artifact = admit_artifact(LocalMemberSource(root))

            self.assertEqual(
                set(artifact.local_member_states or ()),
                {"payload/a.json", "payload/b.json"},
            )
            state = (artifact.local_member_states or {})["payload/a.json"]
            self.assertEqual(state.size, len(files["payload/a.json"]))
            self.assertEqual(state.inode, (root / "payload/a.json").stat().st_ino)
            payload = root / "payload/a.json"
            payload.rename(root / "payload/a.original")
            payload.write_bytes(b"replacement")
            self.assertNotEqual(state.inode, payload.stat().st_ino)

        memory = admit_artifact(MemoryMemberSource(files))
        self.assertIsNone(memory.local_member_states)

    def test_local_digest_refuses_path_component_replacement_during_read(self) -> None:
        class ReplaceAtEof:
            def __init__(self, stream: object, replace_path: Callable[[], None]) -> None:
                self.stream = stream
                self.replace_path = replace_path
                self.replaced = False

            def read(self, size: int = -1) -> bytes:
                value = self.stream.read(size)  # type: ignore[attr-defined]
                if not value and not self.replaced:
                    self.replace_path()
                    self.replaced = True
                return value

            def fileno(self) -> int:
                return self.stream.fileno()  # type: ignore[attr-defined,no-any-return]

        class ReplacingSource(LocalMemberSource):
            def __init__(self, root: Path, replace_path: Callable[[], None]) -> None:
                super().__init__(root)
                self.replace_path = replace_path

            @contextmanager
            def open(self, object_key: str) -> Iterator[object]:
                with super().open(object_key) as stream:
                    if object_key == "payload/a.json":
                        yield ReplaceAtEof(stream, self.replace_path)
                    else:
                        yield stream

        files = artifact_files()
        for case in ("leaf", "directory"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                for key, raw in files.items():
                    path = root / key
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(raw)

                def replace_leaf() -> None:
                    path = root / "payload/a.json"
                    path.rename(root / "payload/a.original")
                    path.write_bytes(b"corrupt replacement")

                def replace_directory() -> None:
                    payload = root / "payload"
                    payload.rename(root / "payload.original")
                    payload.mkdir()
                    (payload / "a.json").write_bytes(b"corrupt replacement")
                    (payload / "b.json").write_bytes(files["payload/b.json"])

                replacement = replace_leaf if case == "leaf" else replace_directory
                with self.assertRaises(ArtifactVerificationError) as raised:
                    admit_artifact(ReplacingSource(root, replacement))
                self.assertEqual(raised.exception.issue.code, "invalid.member-digest")

    def test_local_source_streams_a_wide_directory_and_rejects_undeclared_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, raw in artifact_files().items():
                path = root / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            wide = root / "wide"
            wide.mkdir()
            for index in range(2_000):
                (wide / f"{index:05d}.json").touch()
            self.assertEqual(
                verify_artifact(LocalMemberSource(root)).code,
                "invalid.membership-extra",
            )

    def test_local_source_keeps_operational_errors_out_of_artifact_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, raw in artifact_files().items():
                path = root / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            source = LocalMemberSource(root)
            with mock.patch(
                "rulespec_conformance.platform_artifact.os.scandir",
                side_effect=PermissionError("listing denied"),
            ):
                with self.assertRaises(MemberSourceError):
                    verify_artifact(source)

            real_open = os.open

            def deny_root_member(
                path: object,
                flags: int,
                mode: int = 0o777,
                *,
                dir_fd: int | None = None,
            ) -> int:
                if path == ROOT_OBJECT_KEY:
                    raise PermissionError("read denied")
                return real_open(path, flags, mode, dir_fd=dir_fd)

            with mock.patch(
                "rulespec_conformance.platform_artifact.os.open",
                side_effect=deny_root_member,
            ):
                with self.assertRaises(MemberSourceError):
                    verify_artifact(source)

    def test_local_source_refuses_a_link_at_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, raw in artifact_files().items():
                path = root / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            payload = root / "payload/a.json"
            payload.unlink()
            payload.symlink_to(root / "payload/b.json")
            self.assertEqual(
                verify_artifact(LocalMemberSource(root)).code,
                "invalid.path",
            )

    def test_local_source_refuses_root_and_intermediate_links(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            real_root = parent / "real"
            real_root.mkdir()
            root_link = parent / "root-link"
            root_link.symlink_to(real_root, target_is_directory=True)
            with self.assertRaises(ArtifactVerificationError) as raised:
                LocalMemberSource(root_link)
            self.assertEqual(raised.exception.issue.code, "invalid.path")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key, raw in artifact_files().items():
                path = root / key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            payload = root / "payload"
            real_payload = root / "real-payload"
            payload.rename(real_payload)
            payload.symlink_to(real_payload, target_is_directory=True)
            self.assertEqual(
                verify_artifact(LocalMemberSource(root)).code,
                "invalid.path",
            )

    def test_local_source_fails_closed_without_no_follow_support(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.object(os, "O_NOFOLLOW", 0):
                with self.assertRaises(MemberSourceError, msg="no-follow"):
                    LocalMemberSource(Path(directory))

    def test_local_source_detects_root_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory)
            root = parent / "artifact"
            root.mkdir()
            source = LocalMemberSource(root)
            root.rename(parent / "original")
            root.mkdir()
            with self.assertRaises(MemberSourceError, msg="changed"):
                tuple(source.keys())

    def test_external_pin_is_checked(self) -> None:
        result = verify_artifact(
            MemoryMemberSource(artifact_files()),
            expected_pin=ArtifactPin("urn:example:wrong", "sha256:" + "0" * 64),
        )
        self.assertEqual(result.code, "invalid.identity")

    def test_missing_root_and_manifest_return_structural_results(self) -> None:
        files = artifact_files()
        del files[ROOT_OBJECT_KEY]
        self.assertEqual(
            verify_artifact(MemoryMemberSource(files)).code,
            "invalid.membership-missing",
        )
        files = artifact_files()
        del files["manifests/east.json"]
        self.assertEqual(
            verify_artifact(MemoryMemberSource(files)).code,
            "invalid.membership-missing",
        )

    def test_operational_source_failure_remains_distinct_from_invalid_bytes(self) -> None:
        class FailingSource(MemoryMemberSource):
            def keys(self) -> Sequence[str]:
                raise MemberSourceError("object store unavailable")

        with self.assertRaises(MemberSourceError):
            verify_artifact(FailingSource(artifact_files()))

    def test_missing_extra_and_corrupt_members_are_refused(self) -> None:
        cases: list[tuple[str, dict[str, bytes], str]] = []
        missing = artifact_files()
        del missing["payload/a.json"]
        cases.append(("missing", missing, "invalid.membership-missing"))
        extra = artifact_files()
        extra["extra.json"] = b"{}"
        cases.append(("extra", extra, "invalid.membership-extra"))
        corrupt = artifact_files()
        corrupt["payload/a.json"] = b"changed"
        cases.append(("corrupt", corrupt, "invalid.member-digest"))
        for name, files, expected in cases:
            with self.subTest(case=name):
                self.assertEqual(verify_artifact(MemoryMemberSource(files)).code, expected)

    def test_root_is_closed_and_cannot_inline_members(self) -> None:
        files = replace_root(
            artifact_files(),
            lambda root: root.__setitem__("members", []),
        )
        self.assertEqual(verify_artifact(MemoryMemberSource(files)).code, "invalid.schema")

    def test_manifest_digest_noncanonical_bytes_and_duplicate_ownership_are_refused(self) -> None:
        corrupt = artifact_files()
        corrupt["manifests/east.json"] += b"\n"
        self.assertEqual(
            verify_artifact(MemoryMemberSource(corrupt)).code,
            "invalid.manifest",
        )

        duplicated = artifact_files(
            partitions=(
                ("east", ("payload/a.json",)),
                ("west", ("payload/a.json", "payload/b.json")),
            )
        )
        self.assertEqual(
            verify_artifact(MemoryMemberSource(duplicated)).code,
            "invalid.manifest",
        )

    def test_declared_manifest_bound_is_enforced_before_full_materialization(self) -> None:
        files = artifact_files()
        result = verify_artifact(MemoryMemberSource(files, chunk_size=2), manifest_byte_limit=8)
        self.assertEqual(result.code, "invalid.limit")

    def test_large_manifest_writer_spools_a_sorted_iterator(self) -> None:
        members = (
            describe_member_from_receipt(
                object_key=f"payload/{index:05d}.json",
                role="records",
                media_type="application/json",
                byte_size=10,
                sha256="sha256:" + f"{index:064x}",
                record_count=1,
            )
            for index in range(1_000)
        )
        output = io.BytesIO()
        reference = write_member_manifest(
            output,
            scope_kind="partition",
            scope_id="bulk",
            object_key="manifests/bulk.json",
            members=members,
            spool_bytes=128,
        )
        self.assertEqual(reference.member_count, 1_000)
        self.assertEqual(reference.byte_size, len(output.getvalue()))

    def test_large_multipart_fixture_is_bounded_through_local_and_blob_sources(self) -> None:
        recipe = resources.platform_artifact_fixture_corpus()["largeMultipart"]
        partition_count = recipe["partitionCount"]
        members_per_partition = recipe["membersPerPartition"]
        payload_bytes = recipe["payloadBytes"]
        total_members = partition_count * members_per_partition

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            local_root = base / "local"
            local_root.mkdir()
            blob_source = SqliteBlobMemberSource(base / "objects.sqlite3")
            references: list[MemberManifestReference] = []

            def put(object_key: str, payload: bytes) -> None:
                path = local_root / object_key
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(payload)
                blob_source.put(object_key, payload)

            for partition in range(partition_count):
                members: list[MemberDescriptor] = []
                for ordinal in range(members_per_partition):
                    object_key = f"payload/{partition:04d}/{ordinal:04d}.bin"
                    prefix = f"{partition:04d}/{ordinal:04d}|".encode()
                    payload = (prefix + b"x" * payload_bytes)[:payload_bytes]
                    put(object_key, payload)
                    members.append(
                        describe_member_from_receipt(
                            object_key=object_key,
                            role="records",
                            media_type="application/octet-stream",
                            byte_size=len(payload),
                            sha256=sha256_digest(payload),
                            record_count=1,
                        )
                    )
                manifest_bytes = io.BytesIO()
                reference = write_member_manifest(
                    manifest_bytes,
                    scope_kind="partition",
                    scope_id=f"{partition:04d}",
                    object_key=f"manifests/{partition:04d}.json",
                    members=members,
                    spool_bytes=128,
                )
                references.append(reference)
                put(reference.object_key, manifest_bytes.getvalue())

            root = build_artifact_root(
                spec=SourceCatalogSpec(
                    catalog_id="urn:example:large-catalog",
                    requested_universe_set_digest="sha256:" + "1" * 64,
                    selected_source_set_digest="sha256:" + "2" * 64,
                    selection_policy_digest="sha256:" + "3" * 64,
                    selection_policy_id="urn:example:selection-policy",
                    selection_policy_version="1",
                    source_system_id="urn:example:source-system",
                    source_system_version="1",
                ),
                inputs=(),
                manifests=references,
                accounted_input_count=total_members,
            )
            root_bytes = canonical_json_bytes(root)
            self.assertLessEqual(len(root_bytes), 1024 * 1024)
            put(ROOT_OBJECT_KEY, root_bytes)
            blob_source.connection.commit()

            peaks: list[int] = []
            pins: list[ArtifactPin] = []
            for source in (LocalMemberSource(local_root), blob_source):
                gc.collect()
                tracemalloc.start()
                artifact = admit_artifact(source, scratch_directory=base / "scratch")
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                peaks.append(peak)
                pins.append(artifact.pin)
                self.assertEqual(artifact.member_count, total_members)
                if isinstance(artifact.local_member_states, LocalFileStateIndex):
                    self.assertEqual(len(artifact.local_member_states), total_members)
                    artifact.local_member_states.close()

            blob_source.close()
            self.assertEqual(pins[0], pins[1])
            self.assertLess(max(peaks), 8 * 1024 * 1024)
            self.assertEqual(tuple((base / "scratch").iterdir()), ())

    def test_explicit_scratch_index_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            self.assertEqual(
                verify_artifact(
                    MemoryMemberSource(artifact_files()),
                    scratch_directory=scratch,
                ).code,
                "valid",
            )
            self.assertEqual(tuple(scratch.iterdir()), ())

    def test_explicit_scratch_index_is_removed_after_connect_or_close_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            with mock.patch(
                "rulespec_conformance.platform_artifact.sqlite3.connect",
                side_effect=OSError("connect failed"),
            ):
                with self.assertRaises(OSError, msg="connect failed"):
                    verify_artifact(
                        MemoryMemberSource(artifact_files()),
                        scratch_directory=scratch,
                    )
            self.assertEqual(tuple(scratch.iterdir()), ())

        real_connect = sqlite3.connect

        class CloseFailure:
            def __init__(self, connection: sqlite3.Connection) -> None:
                self._connection = connection

            def __getattr__(self, name: str) -> object:
                return getattr(self._connection, name)

            def close(self) -> None:
                self._connection.close()
                raise OSError("close failed")

        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            with mock.patch(
                "rulespec_conformance.platform_artifact.sqlite3.connect",
                side_effect=lambda path: CloseFailure(real_connect(path)),
            ):
                with self.assertRaises(OSError, msg="close failed"):
                    verify_artifact(
                        MemoryMemberSource(artifact_files()),
                        scratch_directory=scratch,
                    )
            self.assertEqual(tuple(scratch.iterdir()), ())

    def test_member_source_is_the_only_storage_dependency(self) -> None:
        self.assertTrue(isinstance(MemoryMemberSource(artifact_files()), MemberSource))

    def test_semantic_check_is_injected_through_the_same_entry_point(self) -> None:
        observed: list[str] = []

        def check(artifact: object, source: MemberSource) -> None:
            observed.extend(source.keys())

        result = verify_artifact(MemoryMemberSource(artifact_files()), semantic_verifier=check)
        self.assertEqual(result.code, "valid")
        self.assertIn(ROOT_OBJECT_KEY, observed)

    def test_incomplete_coverage_is_refused(self) -> None:
        files = replace_root(
            artifact_files(),
            lambda root: root["coverage"].update(
                {"complete": False, "unaccountedInputCount": 1}
            ),
        )
        root = parse_canonical_json(files[ROOT_OBJECT_KEY])
        root["artifactDigest"] = expected_artifact_digest(root)
        files[ROOT_OBJECT_KEY] = canonical_json_bytes(root)
        self.assertEqual(verify_artifact(MemoryMemberSource(files)).code, "invalid.statistics")


class KindTests(unittest.TestCase):
    def test_derivation_enforces_declared_roles_and_semantic_identity(self) -> None:
        files = artifact_files(
            inputs=(ArtifactInput("source", "urn:example:source", "sha256:" + "1" * 64),)
        )
        root = parse_canonical_json(files[ROOT_OBJECT_KEY])
        root.update(
            {
                "kind": "derivation",
                "spec": {
                    "expectedOutputRoles": ["records"],
                    "parametersDigest": "sha256:" + "2" * 64,
                    "partitioningDigest": "sha256:" + "3" * 64,
                    "partitioningId": "urn:example:partitioning",
                    "policyDigest": "sha256:" + "4" * 64,
                    "policyId": "urn:example:policy",
                    "policyVersion": "1",
                    "processorDigest": "sha256:" + "5" * 64,
                    "processorId": "urn:example:processor",
                    "processorVersion": "1",
                },
            }
        )
        root.pop("logicalId")
        root.pop("artifactDigest")
        files[ROOT_OBJECT_KEY] = canonical_json_bytes(stamp_root(root))
        self.assertEqual(verify_artifact(MemoryMemberSource(files)).code, "valid")

        changed = replace_root(
            files,
            lambda value: value["spec"].update({"expectedOutputRoles": ["missing"]}),
        )
        changed_root = parse_canonical_json(changed[ROOT_OBJECT_KEY])
        changed_root.pop("logicalId")
        changed_root.pop("artifactDigest")
        changed[ROOT_OBJECT_KEY] = canonical_json_bytes(stamp_root(changed_root))
        self.assertEqual(verify_artifact(MemoryMemberSource(changed)).code, "invalid.schema")

        unexpected = artifact_files(
            inputs=(ArtifactInput("source", "urn:example:source", "sha256:" + "1" * 64),),
            roles={"payload/b.json": "undeclared"},
        )
        unexpected_root = parse_canonical_json(unexpected[ROOT_OBJECT_KEY])
        unexpected_root["kind"] = "derivation"
        unexpected_root["spec"] = root["spec"]
        unexpected_root.pop("logicalId")
        unexpected_root.pop("artifactDigest")
        unexpected[ROOT_OBJECT_KEY] = canonical_json_bytes(stamp_root(unexpected_root))
        self.assertEqual(verify_artifact(MemoryMemberSource(unexpected)).code, "invalid.schema")

    def test_reference_only_composition_needs_no_dummy_manifest(self) -> None:
        root = build_artifact_root(
            spec=CompositionSpec(
                merge_policy_digest="sha256:" + "1" * 64,
                merge_policy_id="urn:example:merge-policy",
                merge_policy_version="1",
                total_order_key=("score", "catalog", "subject"),
            ),
            inputs=(
                ArtifactInput(
                    "member",
                    "urn:spicy:artifact:derivation:" + "a" * 64,
                    "sha256:" + "2" * 64,
                ),
            ),
            manifests=(),
            accounted_input_count=1,
        )
        result = verify_artifact(
            MemoryMemberSource({ROOT_OBJECT_KEY: canonical_json_bytes(root)})
        )
        self.assertEqual(result.code, "valid")
        self.assertEqual(result.artifact.member_count, 0)


if __name__ == "__main__":
    unittest.main()
