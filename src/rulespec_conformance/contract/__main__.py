"""`python -m rulespec_conformance.contract` — the contract, proved installed.

`make test-package` runs this from a scratch venv outside the repository, next
to the three console scripts. The claim it falsifies is narrow and the only one
that matters here: everything this package exports is reachable with no
checkout in reach. A data directory left out of `pyproject.toml`'s
force-include table, a generated module that was never regenerated, or an enum
constant that has drifted from the schema shipped beside it fails here and in
no other target.

Exit codes:
  0  every export resolved and agreed with the packaged data
  1  at least one did not — each failure is printed
"""

from __future__ import annotations

import sys

from . import VERSION, enums, resources, terms
from ._term import RKAF_NAMESPACE

# Terms from five different declaring sources, so a scan that lost one source
# fails here rather than shrinking quietly: a class and a property from the
# CUE, a lattice member, a kebab-case enum member, and an L4 wire property
# whose only carriers are `spec/rkaf-behavior.md` and the Rust runtime.
SAMPLE_TERMS = (
    "Artifact",
    "hasContentDigest",
    "officialUse",
    "us_cfr",
    "behaviorContract",
)

# Not a term, and never was: `rkaf:assignedConcept` is a concept-assignment
# field Rulespec retired, held at `sh:maxCount 0` in `shapes/rkaf-shapes-core.ttl`.
RETIRED_TERM = "assignedConcept"


def _compiled_schema_location(cue_relpath: str) -> tuple[str, str]:
    """`constraints/core/artifact.cue` → (`core`, `artifact`)."""
    parts = cue_relpath.split("/")
    return "/".join(parts[1:-1]), parts[-1].removesuffix(".cue")


def main() -> int:
    """Run every check, reporting a missing packaged file as a failure line."""
    try:
        return _check()
    except FileNotFoundError as error:
        print(f"rulespec contract: 1 failure(s)\n  FAIL {error}")
        return 1


def _check() -> int:
    failures: list[str] = []

    if not VERSION:
        failures.append("VERSION is empty")

    context = resources.context()
    declared = context.get("@context", {}).get("rkaf")
    if declared != RKAF_NAMESPACE:
        failures.append(f"context declares rkaf as {declared!r}, not {RKAF_NAMESPACE!r}")

    families = ["core", "analysis", "adversarial", "ai-extraction"]
    # Profiles are discovered, not listed: a profile added upstream should
    # widen this count without anyone remembering to edit it here.
    profiles = resources.resource("compiled/json-schema/profiles")
    if profiles.is_dir():
        families += sorted(f"profiles/{entry.name}" for entry in profiles.iterdir())
    schema_count = sum(len(resources.json_schema_names(f)) for f in families)
    shacl_count = sum(len(resources.shacl_names(f)) for f in families)
    shape_names = resources.shape_names()
    if not schema_count:
        failures.append("no compiled JSON Schemas are packaged")
    if not shacl_count:
        failures.append("no compiled SHACL is packaged")
    if not shape_names:
        failures.append("no hand-authored shapes are packaged")
    for name in shape_names:
        if "sh:" not in resources.shapes(name):
            failures.append(f"shapes/{name}.ttl carries no SHACL")

    # The constants against the schemas shipped beside them. Both are
    # projections of the same CUE, so disagreement means one of the two was
    # built from a different tree.
    compared = 0
    for cue_name, values in enums.ENUMS.items():
        family, stem = _compiled_schema_location(enums.ENUM_SOURCES[cue_name])
        try:
            schema = resources.json_schema(stem, family=family)
        except FileNotFoundError:
            failures.append(f"#{cue_name}: compiled/json-schema/{family}/{stem} missing")
            continue
        packaged = schema.get("$defs", {}).get(cue_name, {}).get("enum")
        if packaged is None:
            continue
        compared += 1
        if tuple(packaged) != values:
            failures.append(
                f"#{cue_name}: constant {values} != packaged schema {tuple(packaged)}"
            )
    if not compared:
        failures.append("no enum could be compared against a packaged schema")

    if not terms.TERMS:
        failures.append("the term registry is empty")
    for sample in SAMPLE_TERMS:
        try:
            getattr(terms, sample)
        except AttributeError:
            failures.append(f"terms.{sample} is missing from the registry")
    try:
        getattr(terms, RETIRED_TERM)
    except AttributeError:
        pass
    else:
        failures.append(f"terms.{RETIRED_TERM} resolved; a retired term must not")

    unregistered = sorted(
        value
        for values in enums.ENUMS.values()
        for value in values
        if value.startswith("rkaf:") and value not in terms.TERMS
    )
    if unregistered:
        failures.append(f"enum members missing from the registry: {unregistered}")

    if failures:
        print(f"rulespec contract {VERSION}: {len(failures)} failure(s)")
        for failure in failures:
            print(f"  FAIL {failure}")
        return 1

    print(f"rulespec contract {VERSION} — data root {resources.DATA_ROOT}")
    print(f"  {schema_count} compiled JSON Schemas, {shacl_count} compiled SHACL files")
    print(f"  {len(shape_names)} hand-authored shape files, 1 JSON-LD context")
    print(f"  {len(enums.ENUMS)} closed enums ({compared} confirmed against the schemas)")
    print(f"  {len(terms.TERMS)} rkaf terms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
