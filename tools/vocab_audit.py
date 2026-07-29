#!/usr/bin/env python3
"""Vocab audit — fails the build if vocabulary and CUE source diverge.

Two checks:
  (1) Fixture-presence: every fixture name listed in the
      spec's `Required fixtures` column exists under fixtures/.
  (2) CUE↔vocab coverage: every class term emitted by a compiled CUE schema is
      mentioned in spec/rkaf-vocabulary.md as `rkaf:<Term>`. Enum/property-only
      CUE files use a small fallback term map.

Exit codes:
  0  fixtures + CUE coverage both clean
  1  fixtures missing OR CUE primitives un-declared
  2  parse error (table malformed)
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TERM_DOC = ROOT / "spec" / "rkaf-vocabulary.md"
FIXTURE_DIR = ROOT / "fixtures"
CUE_DIR = ROOT / "constraints" / "core"
ANALYSIS_CUE_DIR = ROOT / "constraints" / "analysis"
PROFILES_CUE_DIR = ROOT / "constraints" / "profiles"
COMPILED_JSON_SCHEMA_DIR = ROOT / "compiled" / "json-schema" / "core"
COMPILED_ANALYSIS_JSON_SCHEMA_DIR = ROOT / "compiled" / "json-schema" / "analysis"
COMPILED_PROFILE_JSON_SCHEMA_ROOT = ROOT / "compiled" / "json-schema" / "profiles"

# Enum/property-only schemas do not emit concrete JSON-LD @type constants.
CUE_TERM_FALLBACKS: dict[str, set[str]] = {
    "trust-and-safety": {"hasTrustZone", "hasSafetyLabel"},
    "usage-eligibility": {"usageEligibility"},
}


def _kebab_to_titlecase(name: str) -> str:
    return "".join(part[:1].upper() + part[1:] for part in name.split("-"))


def constraint_sources() -> list[tuple[str, Path, Path]]:
    """(label, cue path, compiled JSON Schema path) for every codified source.

    The kernel, the document-analysis module, and every domain profile. Terms
    from the latter two are still Rulespec vocabulary — they just live in their
    own section of `spec/rkaf-vocabulary.md` rather than the
    universal-primitives table. Leaving either tree out of this walk would let a
    class ship with no vocabulary row and no required fixture, which is the one
    thing this audit exists to prevent.
    """
    sources: list[tuple[str, Path, Path]] = [
        (
            f"constraints/core/{cue.name}",
            cue,
            COMPILED_JSON_SCHEMA_DIR / f"{cue.stem}.schema.json",
        )
        for cue in sorted(CUE_DIR.glob("*.cue"))
    ]
    if ANALYSIS_CUE_DIR.is_dir():
        sources.extend(
            (
                f"constraints/analysis/{cue.name}",
                cue,
                COMPILED_ANALYSIS_JSON_SCHEMA_DIR / f"{cue.stem}.schema.json",
            )
            for cue in sorted(ANALYSIS_CUE_DIR.glob("*.cue"))
        )
    if PROFILES_CUE_DIR.is_dir():
        for cue in sorted(PROFILES_CUE_DIR.glob("*/*.cue")):
            profile = cue.parent.name
            sources.append(
                (
                    f"constraints/profiles/{profile}/{cue.name}",
                    cue,
                    COMPILED_PROFILE_JSON_SCHEMA_ROOT
                    / profile
                    / f"{cue.stem}.schema.json",
                )
            )
    return sources


def _schema_type_terms(schema_path: Path) -> set[str]:
    if not schema_path.is_file():
        return set()
    import json

    doc = json.loads(schema_path.read_text())
    terms: set[str] = set()
    for class_schema in doc.get("$defs", {}).values():
        if not isinstance(class_schema, dict):
            continue
        type_iri = (
            class_schema.get("properties", {})
            .get("@type", {})
            .get("const")
        )
        if isinstance(type_iri, str) and type_iri.startswith("rkaf:"):
            terms.add(type_iri.removeprefix("rkaf:"))
    return terms


def cue_primitives_expected_terms() -> dict[str, set[str]]:
    """For each CUE file, return every vocab term suffix it must cover."""
    out: dict[str, set[str]] = {}
    for label, cue, schema_path in constraint_sources():
        stem = cue.stem
        schema_terms = _schema_type_terms(schema_path)
        if schema_terms:
            out[label] = schema_terms
        elif stem in CUE_TERM_FALLBACKS:
            out[label] = CUE_TERM_FALLBACKS[stem]
        else:
            out[label] = {_kebab_to_titlecase(stem)}
    return out

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
    """Parse the vocab spec's term-reference tables and return the union of
    fixture names declared across §5 and §6.

    Recognizes two table headers:
      §5 (the 7-cell layout):
        `| Term | IRI | Kind | Domain | Range | Cardinality | Required fixtures |`
        — fixtures live in the LAST cell, comma-or-space-separated.
      §6 (the 4-cell codified-terms layout):
        `| Term | CUE | Fixture | Purpose |`
        — the single fixture lives in cell index 2 (`Fixture`).
    """
    required: set[str] = set()
    in_table = False
    table_fixture_col: int | None = None   # which cell holds the fixture name
    for line in text.splitlines():
        if line.startswith("| Term "):
            in_table = True
            # Header signature determines column layout.
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 7 and "Required fixtures" in cells[-1]:
                # §5 layout — fixtures in the last cell.
                table_fixture_col = len(cells) - 1
            elif "Fixture" in cells:
                # §6 layout — single fixture column.
                table_fixture_col = cells.index("Fixture")
            else:
                table_fixture_col = None
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            in_table = False
            table_fixture_col = None
            continue
        if table_fixture_col is None:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or cells[0].startswith("-"):  # separator row
            continue
        if table_fixture_col >= len(cells):
            continue
        cell = cells[table_fixture_col]
        for token in re.split(r"[,\s`]+", cell):
            token = token.strip().rstrip(".jsonld").rstrip(".")
            if not token:
                continue
            if token in IGNORE_TOKENS:
                continue
            if "-" not in token:
                continue
            if not FIXTURE_NAME.fullmatch(token):
                continue
            required.add(token)
    return required


def cue_coverage_check(vocab_text: str) -> list[tuple[str, set[str]]]:
    """Return (cue source label, missing_terms) for uncovered CUE terms."""
    missing: list[tuple[str, set[str]]] = []
    for label, terms in cue_primitives_expected_terms().items():
        missing_terms = {t for t in terms if not re.search(rf"\brkaf:{t}\b", vocab_text)}
        if missing_terms:
            missing.append((label, missing_terms))
    return missing


def main() -> int:
    if not TERM_DOC.exists():
        print(f"ERROR: term reference {TERM_DOC} missing", file=sys.stderr)
        return 2
    vocab_text = TERM_DOC.read_text()
    required = parse_required_fixtures(vocab_text)
    if not FIXTURE_DIR.is_dir():
        print(f"ERROR: fixture dir {FIXTURE_DIR} missing", file=sys.stderr)
        return 2
    if not CUE_DIR.is_dir():
        print(f"ERROR: CUE source dir {CUE_DIR} missing", file=sys.stderr)
        return 2
    if not COMPILED_JSON_SCHEMA_DIR.is_dir():
        print(f"ERROR: compiled JSON Schema dir {COMPILED_JSON_SCHEMA_DIR} missing", file=sys.stderr)
        return 2

    # Required-fixture names are logical corpus identifiers, not a promise
    # that every case lives at the fixture root. Edge and negative regression
    # cases intentionally live in named subdirectories, so discover the whole
    # corpus just as the conformance and validation gates do.
    present = {p.stem for p in FIXTURE_DIR.rglob("*.jsonld")}
    missing_fixtures = sorted(required - present)
    extra = sorted(present - required)
    missing_terms = cue_coverage_check(vocab_text)
    primitive_count = len(constraint_sources())

    print(
        f"vocab audit — fixtures required: {len(required)} present: {len(present)} | "
        f"CUE primitives: {primitive_count} covered: "
        f"{primitive_count - len(missing_terms)}"
    )
    if missing_fixtures:
        print(f"\nMISSING FIXTURES ({len(missing_fixtures)}):")
        for m in missing_fixtures:
            print(f"  {m}.jsonld")
    if missing_terms:
        print(f"\nCUE PRIMITIVES MISSING FROM spec/rkaf-vocabulary.md ({len(missing_terms)}):")
        for label, terms in missing_terms:
            choices = ", ".join(sorted(f"rkaf:{t}" for t in terms))
            print(f"  {label} missing: {choices}")
    if extra:
        # Compact form — count only by default; full list only when small.
        if len(extra) <= 5:
            print(f"\nEXTRA fixtures ({len(extra)}):")
            for x in extra:
                print(f"  {x}.jsonld")
        else:
            print(f"\nEXTRA fixtures: {len(extra)} (not in required list; informational; pass `--list-extras` to enumerate)")
        if "--list-extras" in sys.argv:
            for x in extra:
                print(f"  {x}.jsonld")
    fail = bool(missing_fixtures) or bool(missing_terms)
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
