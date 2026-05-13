#!/usr/bin/env python3
"""Rulespec CI validation gate (multi-mode).

Supports three conformance modes via --mode flag:

  --mode core      Rulespec v0.1-rc1 baseline (Core shapes only, v0.1-rc1 fixtures)
                   Expected: 1,183 triples, 0 violations
  --mode batch2    Rulespec Core + ConceptRegistry (Batch 2, v0.2 fixtures)
                   Expected: 1,184 triples, 0 violations
  --mode batch3    Rulespec Core + ConceptRegistry + Lifecycle (Batch 3 fixtures)
                   Expected: 1,186 triples, 0 violations  ← DEFAULT

Each mode loads a specific shape set and validates the matching fixture set.
Triple counts differ between modes because each shape batch may surface
fixture additions (e.g., usageCeiling on case-4 in Batch 2, retainsAssertion
on inline PIT in Batch 3).

Usage:
  python3 ci_validate.py [--mode core|batch2|batch3] [--repo-root <path>]

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

MODES = {
    "core": {
        "label": "RKAF v0.1-rc1 Core",
        "shapes": ["shapes/rkaf-shapes-core-v0.1.ttl"],
        "expected": {
            "local-operational-v0.2":           {"triples": (340, 370)},
            "mapping-v0.1":                     {"triples": (310, 330)},
            "statutory-authority-v0.1":         {"triples": (285, 315)},
            "registry-failure-conflict-v0.1":   {"triples": (215, 240)},
        },
        "expected_total_triples_label": "1,183 (v0.1-rc1 frozen fixtures, Core-only conformance)",
    },
    "batch2": {
        "label": "RKAF Core + ConceptRegistry (Batch 2)",
        "shapes": [
            "shapes/rkaf-shapes-core-v0.1.ttl",
            "shapes/rkaf-shapes-conceptregistry-v0.1.ttl",
        ],
        "expected": {
            "local-operational-v0.2":           {"triples": (340, 370)},
            "mapping-v0.1":                     {"triples": (310, 330)},
            "statutory-authority-v0.1":         {"triples": (285, 315)},
            "registry-failure-conflict-v0.1":   {"triples": (215, 240)},
        },
        "expected_total_triples_label": "1,184 (Batch 2 fixtures, Core+ConceptRegistry conformance)",
    },

    "batch4": {
        "label": "RKAF Core + ConceptRegistry + Lifecycle + Justification (Batch 4)",
        "shapes": [
            "shapes/rkaf-shapes-core-v0.1.ttl",
            "shapes/rkaf-shapes-conceptregistry-v0.1.ttl",
            "shapes/rkaf-shapes-lifecycle-v0.1.ttl",
            "shapes/rkaf-shapes-justification-v0.1.ttl",
        ],
        "expected": {
            "local-operational-v0.2":           {"triples": (340, 370)},
            "mapping-v0.1":                     {"triples": (310, 330)},
            "statutory-authority-v0.1":         {"triples": (285, 315)},
            "registry-failure-conflict-v0.1":   {"triples": (215, 240)},
        },
        "expected_total_triples_label": "1,206 (Batch 4 fixtures, Core+ConceptRegistry+Lifecycle+Justification conformance, includes Pattern C shape patches and 6 fixture defect fixes)",
    },
    "batch3": {
        "label": "RKAF Core + ConceptRegistry + Lifecycle (Batch 3)",
        "shapes": [
            "shapes/rkaf-shapes-core-v0.1.ttl",
            "shapes/rkaf-shapes-conceptregistry-v0.1.ttl",
            "shapes/rkaf-shapes-lifecycle-v0.1.ttl",
        ],
        "expected": {
            "local-operational-v0.2":           {"triples": (340, 370)},
            "mapping-v0.1":                     {"triples": (310, 330)},
            "statutory-authority-v0.1":         {"triples": (285, 315)},
            "registry-failure-conflict-v0.1":   {"triples": (215, 240)},
        },
        "expected_total_triples_label": "1,186 (Batch 3 fixtures, Core+ConceptRegistry+Lifecycle conformance)",
    },

    "v02": {
        "label": "Rulespec Vocabulary v0.2 (full positive-fixture set)",
        # v0.2 is greenfield supersession of v0.1 (spec/rkaf-core-v0.2.md §11).
        # v0.1 shapes are NOT loaded here — they target the same classes with
        # v0.1 property names that v0.2 has replaced (e.g., v0.1 EvidenceBindingShape).
        "shapes": [
            "shapes/rkaf-shapes-core-v0.2.ttl",
            "shapes/rkaf-shapes-warrant-v0.2.ttl",
            "shapes/rkaf-shapes-confidence-v0.2.ttl",
            "shapes/rkaf-shapes-accessscope-v0.2.ttl",
            "shapes/rkaf-shapes-studio-promotions-v0.2.ttl",
            "shapes/rkaf-shapes-conceptregistry-v0.2.ttl",
        ],
        "expected": {
            "v0.2/artifact-eli-positive":                       {"triples": (1, 50)},
            "v0.2/artifact-doi-positive":                       {"triples": (1, 50)},
            "v0.2/artifact-cid-positive":                       {"triples": (1, 50)},
            "v0.2/sourcefragment-oa-textquote-positive":        {"triples": (1, 50)},
            "v0.2/sourcefragment-oa-xpath-positive":            {"triples": (1, 50)},
            "v0.2/sourcefragment-aknt-eid-positive":            {"triples": (1, 50)},
            "v0.2/sourcefragment-uslm-section-positive":        {"triples": (1, 50)},
            "v0.2/evidencebinding-positive":                    {"triples": (1, 50)},
            "v0.2/evidencebinding-no-evidence-reason-positive": {"triples": (1, 50)},
            "v0.2/warrant-legal-positive":                      {"triples": (1, 50)},
            "v0.2/warrant-scientific-positive":                 {"triples": (1, 50)},
            "v0.2/warrant-cross-family-transition-positive":    {"triples": (1, 50)},
            "v0.2/confidencerecord-uncalibrated-positive":      {"triples": (1, 50)},
            "v0.2/confidencerecord-calibrated-positive":        {"triples": (1, 50)},
            "v0.2/accessscope-public-positive":                 {"triples": (1, 50)},
            "v0.2/accessscope-organizationVisible-positive":    {"triples": (1, 50)},
            "v0.2/ailineage-positive":                          {"triples": (1, 50)},
            "v0.2/retentionpolicy-positive":                    {"triples": (1, 50)},
            "v0.2/mappingstate-positive":                       {"triples": (1, 50)},
            "v0.2/workspace-positive":                          {"triples": (1, 50)},
        },
        "expected_total_triples_label": "v0.2 positive fixtures (loose initial triple ranges)",
    },
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
    parser = argparse.ArgumentParser(description="Rulespec multi-mode CI validation gate")
    parser.add_argument("--mode", choices=list(MODES.keys()), default="batch4",
                        help="Conformance mode (default: batch3)")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    mode_config = MODES[args.mode]
    repo_root = Path(args.repo_root).resolve()
    shapes_paths = [repo_root / p for p in mode_config["shapes"]]
    fixtures_dir = repo_root / FIXTURES_DIR

    print(f"Rulespec CI validation gate — mode: {args.mode}")
    print(f"  {mode_config['label']}")
    print("=" * 60)

    print("\n[1/3] Environment check")
    check_pyshacl_version()
    for sp in shapes_paths:
        if not sp.exists():
            die(f"Shapes file missing: {sp}")
        print(f"  shapes:  {sp.relative_to(repo_root)}")
    if not fixtures_dir.is_dir():
        die(f"Fixtures dir missing: {fixtures_dir}")
    print(f"  expected total: {mode_config['expected_total_triples_label']}")

    print("\n[2/3] Per-fixture validation")
    results = {}
    failed = False
    drift_warnings = []

    for slug, expected in mode_config["expected"].items():
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
    print(f"  Mode:       {args.mode} ({mode_config['label']})")
    print(f"  Shapes:     {len(mode_config['shapes'])} files")
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
            "mode": args.mode,
            "label": mode_config["label"],
            "pass": not failed,
            "total_triples": total_triples,
            "total_violations": total_violations,
            "fixtures": {k: {"triples": v.get("triples"), "violations": v.get("violations")} for k, v in results.items()},
        }, indent=2))

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
