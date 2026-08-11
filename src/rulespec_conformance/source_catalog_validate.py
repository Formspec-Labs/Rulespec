#!/usr/bin/env python3
"""Rulespec SourceCatalogRelease v1 candidate gate.

Re-derives the candidate bundle digest from the bytes it pins and replays the
whole sealed fixture corpus, reporting the first diagnostic for each case. It
reads only packaged data, so an installed wheel with no checkout in reach
proves the candidate on its own.

This is a SECOND console script rather than a step inside
`rulespec-ci-validate`, and the reason is identity, not convenience. The sealed
M2 `RulespecCoreRelease` (`release-records/fixtures/rulespec-core-release-m2.json`)
pins `ci_validate.py`'s exact bytes in `validator_artifacts`, and its
content-derived `release_id` is in turn pinned by the vendored document
release, the atlas membership stub, and every extrapolation fixture. Folding
this gate into that file would make the M2 artifact's identity move whenever
SourceCatalogRelease work lands — coupling two independently digested release
surfaces that the candidate design exists to keep apart.

Usage:
  rulespec-source-catalog-validate [--json]
  python3 tools/source_catalog_validate.py [--json]   # in-checkout shim

Exit codes:
  0  the bundle digest re-derives and every sealed case returns its named verdict
  1  a digest, a seal, or a verdict differs
  2  setup error (packaged data or a required export is missing)

A missing export or a missing data file exits 2. It must never become a skip:
converting this to `pytest.skip(allow_module_level=True)` or to a caught
`ImportError` restores exactly the defect the gate exists to catch.
"""

from __future__ import annotations

import argparse
import json
import sys

from rulespec_conformance import source_catalog_release

# The SourceCatalogRelease surface a consumer is entitled to import from an
# installed wheel. Listed here rather than read off `__all__`, so deleting a
# symbol AND its `__all__` entry still turns this run red.
REQUIRED_EXPORTS = (
    "CANDIDATE_MANIFEST",
    "CODE_PRECEDENCE",
    "CORPUS_FILE",
    "DIAGNOSTIC_CODES",
    "FIXTURE_ROOT",
    "FORMAT",
    "FORMAT_VERSION",
    "MEMBER_MANIFEST_SCHEMA",
    "RELEASE_ID_PREFIX",
    "ROOT_SCHEMA",
    "SCHEMA_IDS",
    "SELECTION_DISPOSITIONS",
    "SOURCE_ITEMS_SCHEMA",
    "VerificationIssue",
    "VerificationResult",
    "bundle_release_id",
    "candidate_bundle_errors",
    "canonical_sha256",
    "derive_counts",
    "derive_coverage",
    "expected_release_id",
    "source_set_digest",
    "stamp_root",
    "tree_digest",
    "verify_corpus",
    "verify_source_catalog_release",
)

REQUIRED_DATA = (
    "ROOT_SCHEMA",
    "MEMBER_MANIFEST_SCHEMA",
    "SOURCE_ITEMS_SCHEMA",
    "CORPUS_FILE",
    "CANDIDATE_MANIFEST",
)


def die(message: str, code: int = 2) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(code)


def check_exports() -> None:
    missing = [
        name for name in REQUIRED_EXPORTS if not hasattr(source_catalog_release, name)
    ]
    if missing:
        die(
            "rulespec_conformance.source_catalog_release is missing required "
            f"exports: {', '.join(missing)}"
        )
    print(f"  exports: {len(REQUIRED_EXPORTS)} required names present")


def check_data() -> None:
    for name in REQUIRED_DATA:
        path = getattr(source_catalog_release, name)
        if not path.is_file():
            die(f"SourceCatalogRelease data missing from the distribution: {path}")
    print(f"  data:    {source_catalog_release.CANDIDATE_MANIFEST.parent}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rulespec SourceCatalogRelease v1 candidate gate"
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    print("Rulespec SourceCatalogRelease v1 candidate gate")
    print("=" * 60)

    print("\n[1/3] Distribution check")
    check_exports()
    check_data()

    print("\n[2/3] Candidate bundle digest")
    failed = False
    digest_errors = source_catalog_release.candidate_bundle_errors()
    if digest_errors:
        failed = True
        print("  [FAIL] the manifest does not re-derive from the bytes it pins")
        for message in digest_errors[:10]:
            print(f"           {message}")
    else:
        print(f"  [PASS] {source_catalog_release.bundle_release_id()}")

    print("\n[3/3] Sealed conformance corpus")
    rows = source_catalog_release.verify_corpus()
    for row in rows:
        problems = []
        if not row["sealed"]:
            problems.append("sealed tree digest differs")
        if row["observedCode"] != row["expectedCode"]:
            problems.append(
                f"expected {row['expectedCode']}, observed {row['observedCode']}"
            )
        if row["observedPath"] != row["expectedPath"]:
            problems.append(
                f"expected path {row['expectedPath']}, observed {row['observedPath']}"
            )
        if problems:
            failed = True
            print(f"  [FAIL] {row['name']}: {'; '.join(problems)}")
            for issue in row["issues"][:3]:
                print(f"           {issue}")
        else:
            print(f"  [PASS] {row['name']}: {row['observedCode']}")

    exercised = {row["expectedCode"] for row in rows} - {"valid"}
    unexercised = sorted(set(source_catalog_release.DIAGNOSTIC_CODES) - exercised)
    if unexercised:
        failed = True
        print(f"  [FAIL] diagnostic codes with no sealed fixture: {unexercised}")

    print("\nSummary")
    print(f"  Cases:       {len(rows)}")
    print(f"  Codes:       {len(exercised)}/{len(source_catalog_release.DIAGNOSTIC_CODES)}")
    print(f"  Result:      {'FAIL' if failed else 'PASS'}")

    if args.json:
        print("\n--- JSON ---")
        print(
            json.dumps(
                {
                    "result": "FAIL" if failed else "PASS",
                    "bundleReleaseId": source_catalog_release.bundle_release_id(),
                    "digestErrors": digest_errors,
                    "cases": rows,
                },
                indent=2,
            )
        )

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
