#!/usr/bin/env python3
"""Rulespec CI validation gate (conformance).

Validates the positive-fixture set against the SHACL shape suite.
v0.1 was wholesale-superseded (master plan §1; source spec §11) and lives
under `archive/v0.1/` — it is not loaded by this gate.

Usage:
  python3 ci_validate.py [--repo-root <path>] [--json]

Exit codes:
  0  all invariants pass
  1  validation failed (one or more fixtures has violations)
  2  setup error (missing files, wrong pyshacl version, parse failure)
"""

import argparse
import json
import sys
from pathlib import Path

MIN_PYSHACL = (0, 31, 0)

# Single conformance mode: full positive-fixture set.
SHAPES = [
    "shapes/rkaf-shapes-core.ttl",
    "shapes/rkaf-shapes-warrant.ttl",
    "shapes/rkaf-shapes-confidence.ttl",
    "shapes/rkaf-shapes-accessscope.ttl",
    "shapes/rkaf-shapes-studio-promotions.ttl",
    "shapes/rkaf-shapes-conceptregistry.ttl",
]
EXPECTED = {
    "artifact-eli-positive":                       {"triples": (1, 50)},
    "artifact-doi-positive":                       {"triples": (1, 50)},
    "artifact-cid-positive":                       {"triples": (1, 50)},
    "sourcefragment-oa-textquote-positive":        {"triples": (1, 50)},
    "sourcefragment-oa-xpath-positive":            {"triples": (1, 50)},
    "sourcefragment-aknt-eid-positive":            {"triples": (1, 50)},
    "sourcefragment-uslm-section-positive":        {"triples": (1, 50)},
    "evidencebinding-positive":                    {"triples": (1, 50)},
    "evidencebinding-no-evidence-reason-positive": {"triples": (1, 50)},
    "warrant-legal-positive":                      {"triples": (1, 50)},
    "warrant-scientific-positive":                 {"triples": (1, 50)},
    "warrant-cross-family-transition-positive":    {"triples": (1, 50)},
    "confidencerecord-uncalibrated-positive":      {"triples": (1, 50)},
    "confidencerecord-calibrated-positive":        {"triples": (1, 50)},
    "accessscope-public-positive":                 {"triples": (1, 50)},
    "accessscope-organizationVisible-positive":    {"triples": (1, 50)},
    "ailineage-positive":                          {"triples": (1, 50)},
    "retentionpolicy-positive":                    {"triples": (1, 50)},
    "mappingstate-positive":                       {"triples": (1, 50)},
    "workspace-positive":                          {"triples": (1, 50)},
}

FIXTURES_DIR = "fixtures"


def die(msg, code=2):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def check_pyshacl_version():
    try:
        import pyshacl
    except ImportError:
        die("pyshacl not installed. Install with: pip install pyshacl")
    version_str = getattr(pyshacl, "__version__", "0.0.0")
    parts = tuple(int(p) for p in version_str.split(".")[:3])
    if parts < MIN_PYSHACL:
        die(f"pyshacl {version_str} < required {'.'.join(map(str, MIN_PYSHACL))}")
    print(f"  pyshacl {version_str} OK")


def validate_one(fixture_path, shapes_paths):
    import rdflib
    from pyshacl import validate

    data_graph = rdflib.Graph()
    try:
        data_graph.parse(str(fixture_path), format="json-ld")
    except Exception as e:
        return {"error": f"JSON-LD parse failed: {e}", "triples": 0, "violations": -1}

    shapes_graph = rdflib.Graph()
    for sp in shapes_paths:
        shapes_graph.parse(str(sp), format="turtle")

    conforms, report_graph, _ = validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        inference="rdfs",
        advanced=True,
        meta_shacl=False,
    )

    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    violations = list(report_graph.subjects(rdflib.RDF.type, SH.ValidationResult))

    return {
        "conforms": conforms,
        "triples": len(data_graph),
        "violations": len(violations),
        "violations_detail": [
            {
                "focus": str(report_graph.value(v, SH.focusNode)),
                "path": str(report_graph.value(v, SH.resultPath)) if report_graph.value(v, SH.resultPath) else None,
                "constraint": str(report_graph.value(v, SH.sourceConstraintComponent)),
                "message": str(report_graph.value(v, SH.resultMessage)),
            }
            for v in violations
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Rulespec CI validation gate")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    shapes_paths = [repo_root / p for p in SHAPES]
    fixtures_dir = repo_root / FIXTURES_DIR

    print("Rulespec CI validation gate")
    print("=" * 60)

    print("\n[1/3] Environment check")
    check_pyshacl_version()
    for sp in shapes_paths:
        if not sp.exists():
            die(f"Shapes file missing: {sp}")
        print(f"  shapes:  {sp.relative_to(repo_root)}")
    if not fixtures_dir.is_dir():
        die(f"Fixtures dir missing: {fixtures_dir}")

    print("\n[2/3] Per-fixture validation")
    results = {}
    failed = False
    drift_warnings = []

    for slug, expected in EXPECTED.items():
        fixture_path = fixtures_dir / f"{slug}.jsonld"
        if not fixture_path.exists():
            die(f"Fixture missing: {fixture_path}")
        result = validate_one(fixture_path, shapes_paths)
        results[slug] = result

        if "error" in result:
            print(f"  [FAIL] {slug}: {result['error']}")
            failed = True
            continue

        violation_ok = result["violations"] == 0
        lo, hi = expected["triples"]
        triple_ok = lo <= result["triples"] <= hi

        if not violation_ok:
            print(f"  [FAIL] {slug}: {result['violations']} violations, {result['triples']} triples")
            for v in result["violations_detail"][:5]:
                print(f"           {v['constraint'].split('#')[-1]}: {v['message']}")
            failed = True
        else:
            note = "" if triple_ok else f" (DRIFT: expected {lo}–{hi})"
            print(f"  [PASS] {slug}: 0 violations, {result['triples']} triples{note}")
            if not triple_ok:
                drift_warnings.append((slug, result["triples"], lo, hi))

    print("\n[3/3] Summary")
    total_triples = sum(r.get("triples", 0) for r in results.values())
    total_violations = sum(r.get("violations", 0) for r in results.values())
    print(f"  Shapes:     {len(SHAPES)} files")
    print(f"  Fixtures:   {len(results)}")
    print(f"  Triples:    {total_triples}")
    print(f"  Violations: {total_violations}")
    print(f"  Result:     {'FAIL' if failed else 'PASS'}")

    if drift_warnings:
        print("\nDRIFT WARNINGS (non-fatal):")
        for slug, actual, lo, hi in drift_warnings:
            print(f"  {slug}: {actual} triples outside expected range [{lo}, {hi}]")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps({
            "result": "FAIL" if failed else "PASS",
            "fixtures": results,
        }, indent=2))

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
