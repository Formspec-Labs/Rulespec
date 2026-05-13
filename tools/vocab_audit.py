#!/usr/bin/env python3
"""Vocab audit — fails the build if a v0.2 vocabulary term has zero fixtures.

Parses spec/rkaf-vocabulary-v0.2.md (the term reference tables) and verifies
that every fixture name listed in the `Required fixtures` column exists
under fixtures/v0.2/ as a `<name>.jsonld` file.

Exit codes:
  0  every required fixture present
  1  one or more required fixtures missing
  2  parse error (table malformed)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERM_DOC = ROOT / "spec" / "rkaf-vocabulary-v0.2.md"
FIXTURE_DIR = ROOT / "fixtures" / "v0.2"

# Fixture names look like: lowercase-with-hyphens, possibly mixed case for camelCase enums.
FIXTURE_NAME = re.compile(r"[a-zA-Z][a-zA-Z0-9-]+")

# Tokens that look like fixture names but are documentation prose words to ignore.
IGNORE_TOKENS = {
    "covered", "by", "projector", "fixtures", "Plan", "and",
    "Class", "Property", "closed", "enum", "annotation", "property",
    "carrier", "specialization", "of", "hasWarrant", "AI-touched",
    "REQUIRED", "if", "assertionOrigin", "mapping-bearing", "any",
    "vocabulary", "term",
}


def parse_required_fixtures(text: str) -> set[str]:
    required: set[str] = set()
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Term "):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7:
            continue
        if cells[0].startswith("-"):  # separator row
            continue
        # Last cell: "Required fixtures"
        last_cell = cells[-1]
        for token in re.split(r"[,\s]+", last_cell):
            token = token.strip()
            if not token:
                continue
            if not FIXTURE_NAME.fullmatch(token):
                continue
            if token in IGNORE_TOKENS:
                continue
            # Fixture names always contain a hyphen (positive / negative / kind tag).
            if "-" not in token:
                continue
            required.add(token)
    return required


def main() -> int:
    if not TERM_DOC.exists():
        print(f"ERROR: term reference {TERM_DOC} missing", file=sys.stderr)
        return 2
    required = parse_required_fixtures(TERM_DOC.read_text())
    if not FIXTURE_DIR.is_dir():
        print(f"ERROR: fixture dir {FIXTURE_DIR} missing", file=sys.stderr)
        return 2
    present = {p.stem for p in FIXTURE_DIR.glob("*.jsonld")}
    missing = sorted(required - present)
    extra = sorted(present - required)
    print(f"vocab audit — required: {len(required)} present: {len(present)}")
    if missing:
        print(f"\nMISSING ({len(missing)}):")
        for m in missing:
            print(f"  {m}.jsonld")
    if extra:
        print(f"\nEXTRA fixtures (not declared in term reference; ok if intentional): {len(extra)}")
        for x in extra:
            print(f"  {x}.jsonld")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
