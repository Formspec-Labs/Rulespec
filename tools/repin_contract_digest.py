#!/usr/bin/env python3
"""Re-pin embedded L0 contract digests to the current CUE/context/range digest.

The normative example in spec/rkaf-conformance.md and the us-rulemaking corpus
manifest embed the live contract digest that tools/l0_mapping_audit.py
verifies. Any change to the constraint sources moves the digest, which
previously required a hand-edited follow-up commit. compile_all.sh runs this
tool so the pins move with the contract in the same change.

Only literal `sha256:<64 hex>` values are rewritten; documentation
placeholders such as `sha256:<current L0 contract digest>` are untouched.

THE MANIFEST'S PROV RECORD MOVES WITH ITS PIN. The us-rulemaking manifest
does not just carry a digest; it carries a `prov:Activity` asserting that a
validation run USED that exact digest on a given `dcterms:date`
(reference-corpora/README.md: the manifest "pins the exact content-addressed
contract digest the validation run used"). Rewriting only the digest while
leaving that date behind makes the record lie: a 2026-07-24 activity would
claim it ran against a contract that did not exist until a later date. So
when — and only when — this script actually moves a file's pinned digest, it
also re-stamps that file's validation date and any date-suffixed `@id`s to
today, the day of the re-run that produced the new digest. A no-change run
(the digest already matches) touches nothing, keeping `make compile`
idempotent: re-running it twice in a row must not move the date a second
time. spec/rkaf-conformance.md carries no such dated PROV record, so the
restamp is a no-op there by construction (the patterns below simply do not
match its text).
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from l0_mapping_audit import ROOT, load_vocabulary_registry  # noqa: E402

PINNED_FILES = [
    ROOT / "spec" / "rkaf-conformance.md",
    ROOT / "reference-corpora" / "us-rulemaking" / "v0.2" / "manifest.dcat.jsonld",
]

DIGEST = re.compile(r"sha256:[0-9a-f]{64}")

# The two PROV markers a re-validation date can be read off: a date-suffixed
# `@id` (`...:validation:<date>` / `...:validation-activity:<date>`) and the
# activity's own `dcterms:date` field. Deliberately narrow — `dcterms:issued`
# (the CORPUS's own publication date, unrelated to any one validation run) is
# a different field name and never matches either pattern.
VALIDATION_ID_DATE = re.compile(
    r"(urn:rkaf:corpus:us-rulemaking:validation(?:-activity)?:)\d{4}-\d{2}-\d{2}"
)
VALIDATION_FIELD_DATE = re.compile(r'("dcterms:date":\s*")\d{4}-\d{2}-\d{2}(")')


def _restamp_validation_date(text: str, new_date: str) -> str:
    """Move every embedded re-validation date marker to `new_date`.

    Called only on the digest-change path (see module docstring) — never
    speculatively — so a file with no such markers, or a repin that changed
    nothing, is untouched.
    """
    text = VALIDATION_ID_DATE.sub(lambda m: m.group(1) + new_date, text)
    text = VALIDATION_FIELD_DATE.sub(
        lambda m: m.group(1) + new_date + m.group(2), text
    )
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit 1 if any pinned digest is stale instead of rewriting it",
    )
    args = parser.parse_args()

    current = load_vocabulary_registry().contract_version
    today = date.today().isoformat()
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
            # The digest genuinely moved on this run: the file now describes
            # a re-validation that is actually happening today, so its PROV
            # date markers move with it (see module docstring). A no-change
            # run never reaches this branch, so the date never moves on its
            # own — `make compile` run twice in a row is still idempotent.
            updated = _restamp_validation_date(updated, today)
            path.write_text(updated)
            print(f"[REPIN] {path}: pinned {current}")

    if args.check and stale:
        return 1
    if not stale:
        print(f"[OK] all pins current at {current}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
