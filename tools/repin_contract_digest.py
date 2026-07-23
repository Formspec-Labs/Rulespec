#!/usr/bin/env python3
"""Re-pin embedded L0 contract digests to the current CUE/context/range digest.

The normative example in spec/rkaf-conformance.md and the us-rulemaking corpus
manifest embed the live contract digest that tools/l0_mapping_audit.py
verifies. Any change to the constraint sources moves the digest, which
previously required a hand-edited follow-up commit. compile_all.sh runs this
tool so the pins move with the contract in the same change.

Only literal `sha256:<64 hex>` values are rewritten; documentation
placeholders such as `sha256:<current L0 contract digest>` are untouched.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from l0_mapping_audit import ROOT, load_vocabulary_registry  # noqa: E402

PINNED_FILES = [
    ROOT / "spec" / "rkaf-conformance.md",
    ROOT / "reference-corpora" / "us-rulemaking" / "v0.2" / "manifest.dcat.jsonld",
]

DIGEST = re.compile(r"sha256:[0-9a-f]{64}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any pinned digest is stale instead of rewriting it",
    )
    args = parser.parse_args()

    current = load_vocabulary_registry().contract_version
    stale = 0
    for path in PINNED_FILES:
        text = path.read_text()
        updated, count = DIGEST.subn(current, text)
        if count == 0:
            print(f"[FAIL] {path}: no pinned sha256 digest found")
            return 1
        if updated == text:
            continue
        stale += 1
        if args.check:
            print(f"[STALE] {path}: pinned digest does not match {current}")
        else:
            path.write_text(updated)
            print(f"[REPIN] {path}: pinned {current}")

    if args.check and stale:
        return 1
    if not stale:
        print(f"[OK] all pins current at {current}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
