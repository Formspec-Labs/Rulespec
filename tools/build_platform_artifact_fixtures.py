#!/usr/bin/env python3
"""Build the packaged structural fixture corpus for platform artifacts."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from platform_artifact import (
    ROOT_OBJECT_KEY,
    MemberManifestReference,
    Producer,
    build_artifact_root,
    canonical_json_bytes,
    describe_member_from_receipt,
    expected_artifact_digest,
    parse_canonical_json,
    sha256_digest,
    stamp_root,
)
from rulespec_artifacts import __version__ as ARTIFACT_PACKAGE_VERSION

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "platform-fixtures"


def _valid_files() -> dict[str, bytes]:
    payload_key = "payload/records.json"
    payload = b'[{"id":"one"}]'
    member = describe_member_from_receipt(
        object_key=payload_key,
        role="records",
        media_type="application/json",
        byte_size=len(payload),
        sha256=sha256_digest(payload),
        record_count=1,
        schema_id="https://example.test/schemas/records-v1",
    )
    manifest, manifest_bytes = MemberManifestReference.for_members(
        scope_kind="global",
        scope_id="all",
        object_key="manifests/all.json",
        members=(member,),
    )
    root = build_artifact_root(
        kind="fixture-artifact",
        spec={"profile": "fixture/1"},
        producer=Producer(
            product="fixture-producer",
            implementation_id="git:https://example.test/fixture@" + "1" * 40,
            verifier_id="urn:example:fixture-verifier",
            verifier_version="1.0.0",
            verifier_implementation_id=(
                f"pkg:pypi/rulespec-artifacts@{ARTIFACT_PACKAGE_VERSION}"
                "?checksum=sha256:"
                + "2" * 64
            ),
        ),
        manifests=(manifest,),
    )
    return {
        ROOT_OBJECT_KEY: canonical_json_bytes(root),
        manifest.object_key: manifest_bytes,
        payload_key: payload,
    }


def _root(files: dict[str, bytes]) -> dict[str, object]:
    root = parse_canonical_json(files[ROOT_OBJECT_KEY])
    assert isinstance(root, dict)
    return root


def _with_root(files: dict[str, bytes], root: dict[str, object]) -> dict[str, bytes]:
    result = dict(files)
    result[ROOT_OBJECT_KEY] = canonical_json_bytes(root)
    return result


def _cases() -> dict[str, tuple[str, dict[str, bytes]]]:
    valid = _valid_files()
    cases: dict[str, tuple[str, dict[str, bytes]]] = {"valid": ("valid", valid)}

    noncanonical = dict(valid)
    noncanonical[ROOT_OBJECT_KEY] += b"\n"
    cases["noncanonical-root"] = ("invalid.root-syntax", noncanonical)

    unknown = _root(valid)
    unknown["unexpected"] = True
    cases["unknown-root-field"] = ("invalid.schema", _with_root(valid, unknown))

    wrong_identity = _root(valid)
    wrong_identity["logicalId"] = "urn:spicy:artifact:fixture-artifact:" + "0" * 64
    cases["wrong-identity"] = ("invalid.identity", _with_root(valid, wrong_identity))

    unsafe = _root(valid)
    unsafe["memberManifests"][0]["objectKey"] = "../escape.json"  # type: ignore[index]
    cases["unsafe-path"] = ("invalid.path", _with_root(valid, unsafe))

    invalid_manifest = dict(valid)
    invalid_manifest["manifests/all.json"] += b"\n"
    cases["invalid-manifest"] = ("invalid.manifest", invalid_manifest)

    missing = dict(valid)
    del missing["payload/records.json"]
    cases["missing-member"] = ("invalid.membership-missing", missing)

    extra = dict(valid)
    extra["payload/extra.json"] = b"{}"
    cases["extra-member"] = ("invalid.membership-extra", extra)

    corrupt = dict(valid)
    corrupt["payload/records.json"] = b"corrupt"
    cases["member-digest"] = ("invalid.member-digest", corrupt)

    counts = _root(valid)
    counts.pop("logicalId")
    counts.pop("artifactDigest")
    counts["counts"]["memberCount"] = 2  # type: ignore[index]
    cases["counts"] = ("invalid.statistics", _with_root(valid, stamp_root(counts)))

    mutable_producer = _root(valid)
    mutable_producer["producer"]["implementationId"] = "git:https://example.test/main"  # type: ignore[index]
    mutable_producer["artifactDigest"] = expected_artifact_digest(mutable_producer)
    cases["mutable-producer"] = ("invalid.schema", _with_root(valid, mutable_producer))
    return cases


def _write_tree(destination: Path) -> None:
    cases = _cases()
    corpus = {
        "cases": [
            {"expectedCode": expected, "name": name, "path": f"cases/{name}"}
            for name, (expected, _) in sorted(cases.items())
        ],
        "format": "rulespec-platform-artifact-fixtures",
        "formatVersion": "1.0",
        "largeMultipart": {
            "membersPerPartition": 64,
            "partitionCount": 64,
            "payloadBytes": 256,
        },
    }
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "corpus.json").write_bytes(canonical_json_bytes(corpus))
    golden_path = FIXTURE_ROOT / "canonical-json" / "corpus.json"
    golden_bytes = golden_path.read_bytes()
    golden = parse_canonical_json(golden_bytes)
    if not isinstance(golden, dict) or golden.get("format") != (
        "rulespec-canonical-json-golden-corpus"
    ):
        raise ValueError("canonical-JSON golden corpus has an unknown format")
    output_golden = destination / "canonical-json" / "corpus.json"
    output_golden.parent.mkdir(parents=True, exist_ok=True)
    output_golden.write_bytes(golden_bytes)
    for name, (_, files) in cases.items():
        case_root = destination / "cases" / name
        for object_key, payload in files.items():
            path = case_root / object_key
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)


def _snapshot(root: Path) -> dict[str, bytes]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        generated = Path(directory) / "platform-fixtures"
        _write_tree(generated)
        if args.check:
            if _snapshot(generated) != _snapshot(FIXTURE_ROOT):
                print("platform fixture corpus is stale")
                return 1
            print("platform fixture corpus is current")
            return 0
        if FIXTURE_ROOT.exists():
            shutil.rmtree(FIXTURE_ROOT)
        shutil.copytree(generated, FIXTURE_ROOT)
    print(f"wrote {FIXTURE_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
