#!/usr/bin/env python3
"""Audit lower-layer conformance coverage.

The verdict gates prove pass/fail behavior. This audit proves the L0-L3 surface
is broad enough: vocabulary rows still bind to source/fixtures, every normal
conformance fixture is JSON-LD parseable, every compiled schema class has
positive, negative, and edge coverage, and every required field has a negative
fixture.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import rdflib

from conformance_lib import (
    classify_fixture,
    fixture_name,
    fixture_paths,
    iter_nodes,
    load_json,
    schema_bindings,
)
from vocab_audit import (
    FIXTURE_DIR,
    TERM_DOC,
    constraint_sources,
    cue_coverage_check,
    parse_required_fixtures,
)


def node_types(node: dict[str, Any]) -> set[str]:
    value = node.get("@type")
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {v for v in value if isinstance(v, str)}
    return set()


def fixture_type_coverage(paths: list[Path]) -> dict[str, set[str]]:
    coverage: dict[str, set[str]] = defaultdict(set)
    bindings = schema_bindings()
    for path in paths:
        kind = classify_fixture(fixture_name(path))
        doc = load_json(path)
        if doc is None:
            continue
        for node in iter_nodes(doc):
            coverage[kind].update(t for t in node_types(node) if t in bindings)
    return coverage


def missing_required_field_coverage(paths: list[Path]) -> list[tuple[str, str]]:
    bindings = schema_bindings()
    required_by_type = {
        type_iri: set(binding.required) - {"@type"}
        for type_iri, binding in bindings.items()
    }
    covered: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        doc = load_json(path)
        if doc is None:
            continue
        for node in iter_nodes(doc):
            for type_iri in node_types(node):
                required = required_by_type.get(type_iri)
                if not required:
                    continue
                covered[type_iri].update(required - set(node.keys()))

    missing: list[tuple[str, str]] = []
    for type_iri, required in required_by_type.items():
        for field in sorted(required - covered[type_iri]):
            missing.append((type_iri, field))
    return missing


def jsonld_parse_failures(paths: list[Path]) -> list[tuple[str, str]]:
    failures: list[tuple[str, str]] = []
    for path in paths:
        graph = rdflib.Graph()
        try:
            graph.parse(str(path), format="json-ld")
        except Exception as exc:  # noqa: BLE001 - print concrete parser failure.
            failures.append((fixture_name(path), str(exc)))
    return failures


def l0_vocab_coverage() -> tuple[list[str], int, int, int, int]:
    issues: list[str] = []
    vocab_text = TERM_DOC.read_text()
    required = parse_required_fixtures(vocab_text)
    present = {path.stem for path in FIXTURE_DIR.rglob("*.jsonld")}
    cue_count = len(constraint_sources())
    missing_fixtures = sorted(required - present)
    missing_terms = cue_coverage_check(vocab_text)

    for name in missing_fixtures:
        issues.append(f"L0 vocabulary fixture missing: {name}.jsonld")
    for label, terms in missing_terms:
        choices = ", ".join(sorted(f"rkaf:{term}" for term in terms))
        issues.append(f"L0 CUE primitive missing vocabulary terms: {label} -> {choices}")

    return (
        issues,
        len(required) - len(missing_fixtures),
        len(required),
        cue_count - len(missing_terms),
        cue_count,
    )


def main() -> int:
    paths = fixture_paths()
    bindings = schema_bindings()
    type_set = set(bindings)
    coverage = fixture_type_coverage(paths)
    negative_paths = [
        path for path in paths if classify_fixture(fixture_name(path)) == "negative"
    ]

    issues: list[str] = []

    l0_issues, l0_fixtures_covered, l0_fixture_count, l0_cue_covered, l0_cue_count = (
        l0_vocab_coverage()
    )
    issues.extend(l0_issues)

    parse_failures = jsonld_parse_failures(paths)
    if parse_failures:
        for name, message in parse_failures:
            issues.append(f"L1 JSON-LD parse failed for {name}: {message}")

    for kind in ("positive", "negative", "edge"):
        missing = sorted(type_set - coverage[kind])
        if missing:
            issues.append(
                f"{kind} fixture type coverage missing {len(missing)} classes: {missing}"
            )

    required_missing = missing_required_field_coverage(negative_paths)
    if required_missing:
        issues.append(
            "required-field negative coverage missing: "
            + ", ".join(f"{type_iri}.{field}" for type_iri, field in required_missing)
        )

    required_slots = sum(
        len(set(binding.required) - {"@type"}) for binding in bindings.values()
    )
    covered_required_slots = required_slots - len(required_missing)

    print("L0-L3 coverage audit")
    print(f"  normal fixtures: {len(paths)}")
    print(f"  schema classes: {len(bindings)}")
    print(f"  L0 vocabulary fixtures: {l0_fixtures_covered}/{l0_fixture_count}")
    print(f"  L0 CUE primitive terms: {l0_cue_covered}/{l0_cue_count}")
    print(f"  L1 JSON-LD parse: {len(paths) - len(parse_failures)}/{len(paths)}")
    print(f"  L2 positive type coverage: {len(coverage['positive'])}/{len(bindings)}")
    print(f"  L2 negative type coverage: {len(coverage['negative'])}/{len(bindings)}")
    print(f"  L2 required-field negatives: {covered_required_slots}/{required_slots}")
    print(f"  L3 edge type coverage: {len(coverage['edge'])}/{len(bindings)}")

    if issues:
        print()
        print("Missing L0-L3 coverage:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
