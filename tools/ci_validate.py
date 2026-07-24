#!/usr/bin/env python3
"""Rulespec CI validation gate (conformance).

Validates the positive-fixture set against the SHACL shape suite.
v0.1 was wholesale-superseded (master plan §1; source spec §11) and lives
under `archive/v0.1/` — it is not loaded by this gate.

Usage:
  python3 ci_validate.py [--repo-root <path>] [--json] [fixture.jsonld ...]

  With positional fixtures, validates only those files (e.g. a Studio workspace.jsonld).
  With no positional args, validates the standard positive-fixture set.

Exit codes:
  0  all invariants pass
  1  validation failed (one or more fixtures has violations)
  2  setup error (missing files, wrong pyshacl version, parse failure)
"""

import argparse
import json
import sys
from pathlib import Path

from conformance_lib import ROOT, fixture_name, positive_fixture_paths, shacl_shape_paths

MIN_PYSHACL = (0, 31, 0)


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

    if not hasattr(report_graph, "subjects"):
        return {
            "error": f"SHACL engine rejected the shape graph: {report_graph}",
            "triples": len(data_graph),
            "violations": -1,
        }

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
    parser.add_argument("--repo-root", default=".", help="deprecated; discovery is relative to this script")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "fixtures",
        nargs="*",
        type=Path,
        help="Additional JSON-LD files to validate (if omitted, use positive-fixture set)",
    )
    args = parser.parse_args()

    _ = args.repo_root
    repo_root = ROOT
    shapes_paths = shacl_shape_paths()
    fixture_paths = [Path(p).resolve() for p in args.fixtures] if args.fixtures else positive_fixture_paths()

    print("Rulespec CI validation gate")
    print("=" * 60)

    print("\n[1/3] Environment check")
    check_pyshacl_version()
    for sp in shapes_paths:
        if not sp.exists():
            die(f"Shapes file missing: {sp}")
        print(f"  shapes:  {sp.relative_to(repo_root)}")
    if not fixture_paths:
        die("No positive fixtures discovered")

    print("\n[2/3] Per-fixture validation")
    results = {}
    failed = False
    for fixture_path in fixture_paths:
        try:
            slug = fixture_name(fixture_path).removesuffix(".jsonld")
        except ValueError:
            slug = fixture_path.stem
        if not fixture_path.exists():
            die(f"Fixture missing: {fixture_path}")
        result = validate_one(fixture_path, shapes_paths)
        results[slug] = result

        if "error" in result:
            print(f"  [FAIL] {slug}: {result['error']}")
            failed = True
            continue

        if result["violations"] != 0:
            print(f"  [FAIL] {slug}: {result['violations']} violations, {result['triples']} triples")
            for v in result["violations_detail"][:5]:
                print(f"           {v['constraint'].split('#')[-1]}: {v['message']}")
            failed = True
        else:
            print(f"  [PASS] {slug}: 0 violations, {result['triples']} triples")

    print("\n[3/3] Summary")
    total_triples = sum(r.get("triples", 0) for r in results.values())
    total_violations = sum(r.get("violations", 0) for r in results.values())
    print(f"  Shapes:     {len(shapes_paths)} files")
    print(f"  Fixtures:   {len(results)}")
    print(f"  Triples:    {total_triples}")
    print(f"  Violations: {total_violations}")
    print(f"  Result:     {'FAIL' if failed else 'PASS'}")

    if args.json:
        print("\n--- JSON ---")
        print(json.dumps({
            "result": "FAIL" if failed else "PASS",
            "fixtures": results,
        }, indent=2))

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
