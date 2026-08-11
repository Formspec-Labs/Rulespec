#!/usr/bin/env python3
"""Deterministic builder for the sealed SourceCatalogRelease v1 fixture corpus.

One valid bundle, then one invalid bundle per rule. Each invalid bundle is the
valid bundle copied and mutated in exactly one way, with every downstream
digest, count, and identity restamped, so the case violates the rule it is
named for and nothing else. `corpus.json` seals each bundle by tree digest and
records the diagnostic the verifier must report first.

The output is byte-reproducible: no clock, no filesystem order, no random
value enters a fixture.

Usage:
  python3 tools/build_source_catalog_release_fixtures.py            # rebuild
  python3 tools/build_source_catalog_release_fixtures.py --check    # drift gate
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rulespec_conformance.source_catalog_release import (  # noqa: E402
    CANDIDATE_MANIFEST,
    CORPUS_FILE,
    FIXTURE_ROOT,
    FORMAT,
    FORMAT_VERSION,
    SCHEMA_FILES,
    SCHEMA_IDS,
    canonical_json_bytes,
    canonical_sha256,
    derive_counts,
    derive_coverage,
    file_sha256,
    source_set_digest,
    stamp_root,
    tree_digest,
    write_canonical_json,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
VALID_BUNDLE = FIXTURE_ROOT / "valid"
INVALID_ROOT = FIXTURE_ROOT / "invalid"

CATALOG_ID = "urn:spicy-regs:source-catalog:us-federal-register"
PUBLISHED_AT = "2026-08-11T00:00:00Z"
CANDIDATE_VERSION = "1.0.0-candidate.1"

SOURCE_ITEMS: list[dict[str, Any]] = [
    {
        "candidateRenditions": [
            {
                "expectedByteSize": 184320,
                "expectedSha256": "sha256:"
                + "3f1c2b8d4e5a6f70819293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8",
                "locator": "https://www.govinfo.gov/content/pkg/FR-2026-02-13/html/2026-03227.htm",
                "mediaType": "text/html",
                "renditionId": "2026-03227.html",
            },
            {
                "expectedByteSize": None,
                "expectedSha256": None,
                "locator": "https://www.govinfo.gov/content/pkg/FR-2026-02-13/pdf/2026-03227.pdf",
                "mediaType": "application/pdf",
                "renditionId": "2026-03227.pdf",
            },
        ],
        "documentId": "FR-2026-03227",
        "normalizedMetadata": {
            "agencies": [
                {
                    "agencyId": "food-safety-and-inspection-service",
                    "agencyName": "Food Safety and Inspection Service",
                }
            ],
            "commentCloseDate": None,
            "docketIds": ["FSIS-2022-0027"],
            "documentType": "Rule",
            "language": "en",
            "lastUpdatedDate": "2026-02-14",
            "publicationDate": "2026-02-13",
            "regulationIdentifierNumbers": ["0583-AD86"],
            "sourceUrl": "https://www.federalregister.gov/documents/2026/02/13/2026-03227",
            "title": "Salmonella Framework for Raw Poultry Products",
        },
        "selection": {"disposition": "selected"},
        "sourceIssuedVersion": "2026-02-14T09:12:00Z",
        "sourceNativeMetadata": {
            "document_number": "2026-03227",
            "page_length": 34,
            "start_page": 7926,
            "type": "Rule",
            "volume": 91,
        },
        "sourceItemId": "federalregister.gov/2026-03227",
        "sourceObservations": [
            {"observationKey": "significant", "observationValue": "true"},
            {"observationKey": "start_page", "observationValue": "7926"},
        ],
        "sourceObservedTopics": [
            {
                "label": "Meat and poultry products",
                "observedTopicId": "meat-and-poultry-products",
                "observedTopicScheme": "federalregister.gov/topics",
            },
            {
                "label": "Food safety",
                "observedTopicId": "food-safety",
                "observedTopicScheme": "federalregister.gov/topics",
            },
        ],
    },
    {
        "candidateRenditions": [
            {
                "expectedByteSize": None,
                "expectedSha256": None,
                "locator": "https://www.govinfo.gov/content/pkg/FR-2026-03-04/html/2026-04188.htm",
                "mediaType": "text/html",
                "renditionId": "2026-04188.html",
            }
        ],
        "documentId": "FR-2026-04188",
        "normalizedMetadata": {
            "agencies": [
                {
                    "agencyId": "environmental-protection-agency",
                    "agencyName": "Environmental Protection Agency",
                }
            ],
            "commentCloseDate": "2026-05-04",
            "docketIds": ["EPA-HQ-OAR-2025-0411", "EPA-R03-OAR-2025-0022"],
            "documentType": "Proposed Rule",
            "language": "en",
            "lastUpdatedDate": None,
            "publicationDate": "2026-03-04",
            "regulationIdentifierNumbers": ["2060-AW12"],
            "sourceUrl": "https://www.federalregister.gov/documents/2026/03/04/2026-04188",
            "title": "Air Plan Approval; Pennsylvania; Regional Haze Progress Report",
        },
        "selection": {"disposition": "selected"},
        "sourceIssuedVersion": "2026-03-04T06:00:00Z",
        "sourceNativeMetadata": {
            "comments_close_on": "2026-05-04",
            "document_number": "2026-04188",
            "type": "Proposed Rule",
            "volume": 91,
        },
        "sourceItemId": "federalregister.gov/2026-04188",
        "sourceObservations": [
            {"observationKey": "comment_url", "observationValue": "https://www.regulations.gov/commenton/EPA-R03-OAR-2025-0022-0001"}
        ],
        "sourceObservedTopics": [
            {
                "label": "Air pollution control",
                "observedTopicId": "air-pollution-control",
                "observedTopicScheme": "federalregister.gov/topics",
            }
        ],
    },
    {
        "candidateRenditions": [
            {
                "expectedByteSize": None,
                "expectedSha256": None,
                "locator": "https://www.govinfo.gov/content/pkg/FR-2026-03-09/html/2026-04401.htm",
                "mediaType": "text/html",
                "renditionId": "2026-04401.html",
            }
        ],
        "documentId": "FR-2026-04401",
        "normalizedMetadata": {
            "agencies": [
                {"agencyId": "commerce-department", "agencyName": "Department of Commerce"}
            ],
            "commentCloseDate": None,
            "docketIds": [],
            "documentType": "Notice",
            "language": "en",
            "lastUpdatedDate": None,
            "publicationDate": "2026-03-09",
            "regulationIdentifierNumbers": [],
            "sourceUrl": "https://www.federalregister.gov/documents/2026/03/09/2026-04401",
            "title": "Notice of Public Meeting of the Census Scientific Advisory Committee",
        },
        "selection": {
            "disposition": "excluded",
            "reason": "The selection policy admits Rule and Proposed Rule only; this is a Notice.",
            "reasonCode": "policy.document-type-out-of-scope",
        },
        "sourceIssuedVersion": "2026-03-09T06:00:00Z",
        "sourceNativeMetadata": {
            "document_number": "2026-04401",
            "type": "Notice",
            "volume": 91,
        },
        "sourceItemId": "federalregister.gov/2026-04401",
        "sourceObservations": [],
        "sourceObservedTopics": [],
    },
    {
        "candidateRenditions": [],
        "documentId": "FR-2026-04555",
        "normalizedMetadata": {
            "agencies": [
                {
                    "agencyId": "federal-aviation-administration",
                    "agencyName": "Federal Aviation Administration",
                }
            ],
            "commentCloseDate": None,
            "docketIds": ["FAA-2025-1188"],
            "documentType": "Proposed Rule",
            "language": "en",
            "lastUpdatedDate": "2026-03-18",
            "publicationDate": "2026-03-12",
            "regulationIdentifierNumbers": ["2120-AL77"],
            "sourceUrl": "https://www.federalregister.gov/documents/2026/03/12/2026-04555",
            "title": "Airworthiness Directives; Various Transport Category Airplanes",
        },
        "selection": {
            "disposition": "deleted",
            "reason": "The source withdrew the document after publication and serves a tombstone.",
            "reasonCode": "source.withdrawn-after-publication",
        },
        "sourceIssuedVersion": "2026-03-18T14:31:00Z",
        "sourceNativeMetadata": {
            "document_number": "2026-04555",
            "type": "Proposed Rule",
            "volume": 91,
            "withdrawn": True,
        },
        "sourceItemId": "federalregister.gov/2026-04555",
        "sourceObservations": [
            {"observationKey": "withdrawal_notice", "observationValue": "2026-04901"}
        ],
        "sourceObservedTopics": [],
    },
    {
        "candidateRenditions": [
            {
                "expectedByteSize": None,
                "expectedSha256": None,
                "locator": "https://www.govinfo.gov/content/pkg/FR-2026-03-20/html/2026-05010.htm",
                "mediaType": "text/html",
                "renditionId": "2026-05010.html",
            }
        ],
        "documentId": "FR-2026-05010",
        "normalizedMetadata": {
            "agencies": [
                {
                    "agencyId": "securities-and-exchange-commission",
                    "agencyName": "Securities and Exchange Commission",
                }
            ],
            "commentCloseDate": "2026-05-20",
            "docketIds": ["SEC-2026-0044"],
            "documentType": "Proposed Rule",
            "language": "en",
            "lastUpdatedDate": None,
            "publicationDate": "2026-03-20",
            "regulationIdentifierNumbers": ["3235-AN19"],
            "sourceUrl": "https://www.federalregister.gov/documents/2026/03/20/2026-05010",
            "title": "Order Competition Rule; Reopening of Comment Period",
        },
        "selection": {
            "disposition": "unavailable",
            "reason": "Every candidate rendition returned HTTP 403 for the whole discovery window.",
            "reasonCode": "source.rendition-forbidden",
        },
        "sourceIssuedVersion": "2026-03-20T06:00:00Z",
        "sourceNativeMetadata": {
            "document_number": "2026-05010",
            "type": "Proposed Rule",
            "volume": 91,
        },
        "sourceItemId": "federalregister.gov/2026-05010",
        "sourceObservations": [],
        "sourceObservedTopics": [],
    },
    {
        "candidateRenditions": [],
        "documentId": "FR-2026-05233",
        "normalizedMetadata": None,
        "selection": {
            "disposition": "failed",
            "reason": "The source metadata record could not be parsed; no normalized view exists.",
            "reasonCode": "source.metadata-unparsable",
        },
        "sourceIssuedVersion": "2026-03-25T06:00:00Z",
        "sourceNativeMetadata": {
            "document_number": "2026-05233",
            "raw": "<!DOCTYPE html><html><body>502 Bad Gateway</body></html>",
        },
        "sourceItemId": "federalregister.gov/2026-05233",
        "sourceObservations": [],
        "sourceObservedTopics": [],
    },
]

SELECTION_POLICY = {
    "policyId": "urn:spicy-regs:selection-policy:federal-register-rules-and-proposed-rules",
    "policySha256": canonical_sha256(
        {
            "documentTypes": ["Proposed Rule", "Rule"],
            "publicationWindow": {"from": "2026-02-01", "to": "2026-03-31"},
        }
    ),
    "policyVersion": "1.0",
}
SOURCE_SYSTEM = {
    "sourceSystemId": "https://www.federalregister.gov/api/v1",
    "sourceSystemVersion": "v1",
}


def _schema_object_key(role: str) -> str:
    return f"schemas/{SCHEMA_FILES[role].name}"


def _member(
    bundle: Path, object_key: str, *, role: str, record_count: int | None, schema_id: str
) -> dict[str, Any]:
    path = bundle / object_key
    return {
        "byteSize": path.stat().st_size,
        "mediaType": "application/schema+json"
        if role == "schema"
        else "application/json",
        "objectKey": object_key,
        "recordCount": record_count,
        "role": role,
        "schemaId": schema_id,
        "sha256": file_sha256(path),
    }


def _restamp(bundle: Path, items: list[dict[str, Any]]) -> None:
    """Rewrite every derived value in a bundle from its current member bytes.

    Called after every mutation so an invalid fixture differs from the valid
    one in exactly the rule it targets.
    """

    (bundle / "data").mkdir(parents=True, exist_ok=True)
    write_canonical_json(bundle / "data" / "source-items.json", items)

    members = [
        _member(
            bundle,
            "data/source-items.json",
            role="source-items",
            record_count=len(items),
            schema_id=SCHEMA_IDS["source-items"],
        )
    ]
    for role in sorted(SCHEMA_FILES):
        members.append(
            _member(
                bundle,
                _schema_object_key(role),
                role="schema",
                record_count=None,
                schema_id=SCHEMA_IDS[role],
            )
        )
    members.sort(key=lambda member: member["objectKey"])

    manifest = {
        "counts": {
            "memberCount": len(members),
            "totalByteSize": sum(member["byteSize"] for member in members),
            "totalRecordCount": sum(member["recordCount"] or 0 for member in members),
        },
        "format": "spicy-artifact-member-manifest",
        "formatVersion": "1.0",
        "manifestId": "global:global",
        "members": members,
        "scope": {"id": "global", "kind": "global"},
    }
    manifest_key = "manifests/global.json"
    write_canonical_json(bundle / manifest_key, manifest)

    schemas = sorted(
        (
            {
                "roles": [role],
                "schemaId": SCHEMA_IDS[role],
                "schemaSha256": file_sha256(bundle / _schema_object_key(role)),
            }
            for role in SCHEMA_FILES
        ),
        key=lambda descriptor: descriptor["schemaId"],
    )
    universe_ids = [item["sourceItemId"] for item in items]
    selected_ids = [
        item["sourceItemId"]
        for item in items
        if item.get("selection", {}).get("disposition") == "selected"
    ]
    content = {
        "catalogId": CATALOG_ID,
        # No `publishedAt` here. It is a fact about the act of publishing, so
        # it rides in the identity-excluded annotations envelope below.
        "counts": derive_counts(
            items,
            member_count=len(members),
            total_member_byte_size=sum(member["byteSize"] for member in members),
        ),
        "coverage": derive_coverage(items),
        "globalManifest": {
            "byteSize": (bundle / manifest_key).stat().st_size,
            "manifestId": "global:global",
            "objectKey": manifest_key,
            "scopeId": "global",
            "scopeKind": "global",
            "sha256": file_sha256(bundle / manifest_key),
        },
        "requestedUniverseSetDigest": source_set_digest(universe_ids),
        "schemaSet": {
            "schemaSetId": f"urn:spicy:schema-set:v1:{canonical_sha256(schemas)}",
            "schemas": schemas,
        },
        "selectedSourceSetDigest": source_set_digest(selected_ids),
        "selectionPolicy": SELECTION_POLICY,
        "sourceSystem": SOURCE_SYSTEM,
    }
    root = {
        "annotations": {
            "buildRunId": "source-catalog-release-v1-conformance-fixture",
            "publishedAt": PUBLISHED_AT,
            "releaseStatus": "fixture",
        },
        "content": content,
        "format": FORMAT,
        "formatVersion": FORMAT_VERSION,
    }
    write_canonical_json(bundle / "release.json", stamp_root(root))


def build_valid_bundle(bundle: Path) -> None:
    """Materialize the sealed valid bundle at ``bundle``."""

    if bundle.exists():
        shutil.rmtree(bundle)
    (bundle / "schemas").mkdir(parents=True)
    for role, path in SCHEMA_FILES.items():
        shutil.copyfile(path, bundle / _schema_object_key(role))
    _restamp(bundle, json.loads(json.dumps(SOURCE_ITEMS)))


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _items(bundle: Path) -> list[dict[str, Any]]:
    return _load(bundle / "data" / "source-items.json")


def _index_of(items: list[dict[str, Any]], disposition: str) -> int:
    for index, item in enumerate(items):
        if item["selection"]["disposition"] == disposition:
            return index
    raise AssertionError(f"fixture has no {disposition} item")


def build_corpus(fixture_root: Path = FIXTURE_ROOT) -> list[dict[str, Any]]:
    """Rebuild every bundle and return the sealed corpus rows."""

    valid = fixture_root / "valid"
    invalid_root = fixture_root / "invalid"
    build_valid_bundle(valid)
    if invalid_root.exists():
        shutil.rmtree(invalid_root)
    invalid_root.mkdir(parents=True)

    cases: list[dict[str, Any]] = [
        {
            "bundle": "valid",
            "expectedCode": "valid",
            "expectedPath": None,
            "name": "valid",
            "treeSha256": tree_digest(valid),
        }
    ]

    def copy_case(name: str) -> Path:
        target = invalid_root / name
        shutil.copytree(valid, target)
        return target

    def record(name: str, code: str, path: str | None, bundle: Path) -> None:
        cases.append(
            {
                "bundle": f"invalid/{name}",
                "expectedCode": code,
                "expectedPath": path,
                "name": name,
                "treeSha256": tree_digest(bundle),
            }
        )

    # A root whose bytes are not canonical is unreadable before it is unjudged.
    bundle = copy_case("noncanonical-root")
    (bundle / "release.json").write_bytes(
        (bundle / "release.json").read_bytes() + b"\n"
    )
    record(
        "noncanonical-root",
        "invalid.root-syntax",
        "release.json",
        bundle,
    )

    bundle = copy_case("unknown-version")
    root = _load(bundle / "release.json")
    root["formatVersion"] = "1.1"
    write_canonical_json(bundle / "release.json", stamp_root(root))
    record("unknown-version", "invalid.format", "release.json", bundle)

    bundle = copy_case("wrong-identity")
    root = _load(bundle / "release.json")
    root["releaseId"] = "urn:spicy-regs:source-catalog-release:v1:" + "0" * 64
    write_canonical_json(bundle / "release.json", root)
    record("wrong-identity", "invalid.identity", "release.json/releaseId", bundle)

    bundle = copy_case("unsafe-path")
    manifest = _load(bundle / "manifests" / "global.json")
    for member in manifest["members"]:
        if member["role"] == "source-items":
            member["objectKey"] = "../escaped-source-items.json"
    manifest["members"].sort(key=lambda member: member["objectKey"])
    write_canonical_json(bundle / "manifests" / "global.json", manifest)
    root = _load(bundle / "release.json")
    root["content"]["globalManifest"]["byteSize"] = (
        bundle / "manifests" / "global.json"
    ).stat().st_size
    root["content"]["globalManifest"]["sha256"] = file_sha256(
        bundle / "manifests" / "global.json"
    )
    write_canonical_json(bundle / "release.json", stamp_root(root))
    record(
        "unsafe-path",
        "invalid.path",
        "manifests/global.json/members/0/objectKey",
        bundle,
    )

    bundle = copy_case("missing-member")
    (bundle / "data" / "source-items.json").unlink()
    record(
        "missing-member",
        "invalid.membership-missing",
        "data/source-items.json",
        bundle,
    )

    bundle = copy_case("extra-member")
    (bundle / "undeclared.json").write_bytes(b"{}")
    record("extra-member", "invalid.membership-extra", "undeclared.json", bundle)

    bundle = copy_case("member-digest")
    # Same JSON value, different bytes: only the declared digest can catch it.
    (bundle / "data" / "source-items.json").write_bytes(
        (bundle / "data" / "source-items.json").read_bytes() + b" "
    )
    record("member-digest", "invalid.member-digest", "data/source-items.json", bundle)

    bundle = copy_case("missing-disposition")
    items = _items(bundle)
    index = _index_of(items, "excluded")
    del items[index]["selection"]["disposition"]
    _restamp(bundle, items)
    record(
        "missing-disposition",
        "invalid.schema",
        f"data/source-items.json/{index}/selection",
        bundle,
    )

    bundle = copy_case("unknown-disposition")
    items = _items(bundle)
    index = _index_of(items, "excluded")
    items[index]["selection"]["disposition"] = "skipped"
    _restamp(bundle, items)
    record(
        "unknown-disposition",
        "invalid.schema",
        f"data/source-items.json/{index}/selection/disposition",
        bundle,
    )

    bundle = copy_case("missing-reason")
    items = _items(bundle)
    index = _index_of(items, "unavailable")
    del items[index]["selection"]["reason"]
    _restamp(bundle, items)
    record(
        "missing-reason",
        "invalid.disposition",
        f"data/source-items.json/{index}/selection/reason",
        bundle,
    )

    bundle = copy_case("duplicate-source-item")
    items = _items(bundle)
    index = _index_of(items, "deleted")
    items[index]["sourceItemId"] = items[0]["sourceItemId"]
    _restamp(bundle, items)
    record(
        "duplicate-source-item",
        "invalid.duplicate-identity",
        f"data/source-items.json/{index}/sourceItemId",
        bundle,
    )

    bundle = copy_case("set-digest-mismatch")
    root = _load(bundle / "release.json")
    root["content"]["selectedSourceSetDigest"] = "sha256:" + "0" * 64
    write_canonical_json(bundle / "release.json", stamp_root(root))
    record(
        "set-digest-mismatch",
        "invalid.set-digest",
        "release.json/content/selectedSourceSetDigest",
        bundle,
    )

    bundle = copy_case("selected-without-rendition")
    items = _items(bundle)
    index = _index_of(items, "selected")
    items[index]["candidateRenditions"] = []
    _restamp(bundle, items)
    record(
        "selected-without-rendition",
        "invalid.rendition",
        f"data/source-items.json/{index}/candidateRenditions",
        bundle,
    )

    bundle = copy_case("refspec-concept-topic")
    items = _items(bundle)
    index = _index_of(items, "selected")
    items[index]["sourceObservedTopics"][0]["observedTopicId"] = (
        "urn:ref:concept:federal-register-thesaurus:meat-and-poultry-products"
    )
    _restamp(bundle, items)
    record(
        "refspec-concept-topic",
        "invalid.topic-scope",
        f"data/source-items.json/{index}/sourceObservedTopics/0/observedTopicId",
        bundle,
    )

    bundle = copy_case("counts-mismatch")
    root = _load(bundle / "release.json")
    root["content"]["counts"]["selectedCount"] += 1
    write_canonical_json(bundle / "release.json", stamp_root(root))
    record("counts-mismatch", "invalid.counts", "release.json/content/counts", bundle)

    bundle = copy_case("coverage-mismatch")
    root = _load(bundle / "release.json")
    root["content"]["coverage"]["selectedWithCandidateRenditionCount"] += 1
    write_canonical_json(bundle / "release.json", stamp_root(root))
    record(
        "coverage-mismatch",
        "invalid.coverage",
        "release.json/content/coverage",
        bundle,
    )

    return cases


def build_candidate_manifest(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Bind the schemas, the validator, and every sealed fixture under one digest.

    The record is a `RulespecCoreRelease` (`spec/rulespec-releases.md` §2), so
    the bundle digest is minted, checked, and revoked by the machinery this
    repository already has rather than by a second publication pipeline. Its
    `release_id` IS the candidate's immutable name.
    """

    def artifact(path: Path, media_type: str) -> dict[str, Any]:
        return {
            "artifact_digest": "sha256:" + file_sha256(path),
            "media_type": media_type,
            "name": path.relative_to(REPO_ROOT).as_posix(),
        }

    schema_artifacts = sorted(
        (
            artifact(path, "application/schema+json")
            for path in SCHEMA_FILES.values()
        ),
        key=lambda entry: entry["name"],
    )
    validator_artifacts = [
        artifact(REPO_ROOT / "src" / "rulespec_conformance" / name, "text/x-python")
        for name in ("source_catalog_release.py", "source_catalog_validate.py")
    ]
    fixture_artifacts = [
        {
            "artifact_digest": "sha256:" + case["treeSha256"],
            "media_type": "application/vnd.spicy.bundle-tree+json",
            "name": f"release-records/fixtures/source-catalog-release-v1/{case['bundle']}",
        }
        for case in cases
    ]
    record = {
        "conformance_fixture_artifacts": fixture_artifacts,
        "record_type": "RulespecCoreRelease",
        "release_status": "candidate",
        "schema_artifacts": schema_artifacts,
        "validator_artifacts": validator_artifacts,
        "version": CANDIDATE_VERSION,
    }
    digest = "sha256:" + canonical_sha256(record)
    record["release_digest"] = digest
    record["release_id"] = f"urn:rulespec:core:{digest.removeprefix('sha256:')}"
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild into a scratch tree and fail on any drift",
    )
    args = parser.parse_args(argv)

    if args.check:
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory) / "source-catalog-release-v1"
            scratch.mkdir()
            cases = build_corpus(scratch)
            rebuilt = {
                "corpus": canonical_json_bytes({"cases": cases}),
                "candidate": canonical_json_bytes(build_candidate_manifest(cases)),
            }
        committed = {
            "corpus": CORPUS_FILE.read_bytes(),
            "candidate": CANDIDATE_MANIFEST.read_bytes(),
        }
        drift = [name for name in rebuilt if rebuilt[name] != committed.get(name)]
        if drift:
            print(f"DRIFT: {', '.join(sorted(drift))} differ from a clean rebuild")
            return 1
        print("source-catalog-release-v1 fixtures match a clean rebuild")
        return 0

    cases = build_corpus()
    write_canonical_json(CORPUS_FILE, {"cases": cases})
    write_canonical_json(CANDIDATE_MANIFEST, build_candidate_manifest(cases))
    print(f"wrote {len(cases)} sealed cases to {CORPUS_FILE}")
    print(f"bundle digest {json.loads(CANDIDATE_MANIFEST.read_text())['release_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
