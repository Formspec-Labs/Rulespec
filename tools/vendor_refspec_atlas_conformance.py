"""Vendor RefSpec's atlas conformance corpus as byte-exact copies.

RefSpec owns `bindings/atlas/1.0/fixtures/`. Rulespec keeps a copy under
`release-records/fixtures/upstream/refspec-atlas-conformance/` so
`tools/test_refspec_atlas_conformance.py` can drive the reader offline. This
script is the only supported way to refresh that copy: it verifies every source
file against the digest `corpus.json` notes, copies the bytes unchanged, and
prints the corpus digest to record in the test module.

    python3 tools/vendor_refspec_atlas_conformance.py /path/to/RefSpec
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

try:
    from rulespec_release import content_digest
except ModuleNotFoundError:  # imported as a tools package
    from tools.rulespec_release import content_digest

ROOT = Path(__file__).resolve().parents[1]
VENDORED_ROOT = ROOT / "release-records/fixtures/upstream/refspec-atlas-conformance"
PUBLISHED_SUBPATH = Path("bindings/atlas/1.0/fixtures")
CASE_FILES = ("atlas-manifest.json", "atlas.nq")
SCHEMA_VERSION = "refspec-vocabulary-atlas-conformance-corpus/v1"


def _source_fixtures(source: Path) -> Path:
    """Accept either a RefSpec checkout root or the fixtures directory."""

    if (source / "corpus.json").is_file():
        return source
    candidate = source / PUBLISHED_SUBPATH
    if (candidate / "corpus.json").is_file():
        return candidate
    raise SystemExit(f"no atlas conformance corpus under {source}")


def vendor(source: Path) -> str:
    """Copy the published corpus verbatim and return its content digest."""

    fixtures = _source_fixtures(source.resolve(strict=True))
    corpus_bytes = (fixtures / "corpus.json").read_bytes()
    corpus = json.loads(corpus_bytes.decode("utf-8"))
    declared = corpus.get("schemaVersion")
    if declared != SCHEMA_VERSION:
        raise SystemExit(f"unsupported corpus schemaVersion: {declared}")

    for case in corpus["cases"]:
        directory = fixtures / case["directory"]
        for name, expected in zip(
            CASE_FILES, (case["manifestDigest"], case["outputDigest"]), strict=True
        ):
            if content_digest((directory / name).read_bytes()) != expected:
                raise SystemExit(
                    f"published case {case['id']} file {name} differs from corpus.json"
                )

    if VENDORED_ROOT.exists():
        shutil.rmtree(VENDORED_ROOT)
    VENDORED_ROOT.mkdir(parents=True)
    (VENDORED_ROOT / "corpus.json").write_bytes(corpus_bytes)
    for case in corpus["cases"]:
        source_case = fixtures / case["directory"]
        target = VENDORED_ROOT / case["directory"]
        target.mkdir(parents=True)
        for name in CASE_FILES:
            (target / name).write_bytes((source_case / name).read_bytes())
    return content_digest(corpus_bytes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        type=Path,
        help="RefSpec checkout root, or its bindings/atlas/1.0/fixtures directory",
    )
    args = parser.parse_args()
    digest = vendor(args.source)
    print(f"vendored {VENDORED_ROOT.relative_to(ROOT)}")
    print(f"set CORPUS_DIGEST in tools/test_refspec_atlas_conformance.py to {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
