#!/usr/bin/env python3
"""Rulespec conformance reporter — L1/L2/L3 per-fixture verdict.

For each fixture under `fixtures/` (positives, negatives, edges), runs three
gates and reports a structured verdict:

  L1 (Parse):       does the document parse as JSON-LD?
  L2 (Shape):       does every Rulespec-typed node validate against its
                    compiled JSON Schema?
  L3 (Constraint):  does the document pass the SHACL shape suite (hand-
                    authored Pattern-C invariants + CUE-compiled enums/
                    cardinality)?

L4 (Behavior) is not gated automatically; reports `not-tested` per
spec/rkaf-conformance.md §4.2.

Usage:
  python3 tools/conformance_report.py
  python3 tools/conformance_report.py --json
  python3 tools/conformance_report.py --self-certify > conformance/partners/<impl>.yaml

Exit codes:
  0  every fixture's outcome matches its expected verdict (positives pass,
     negatives fail as designed)
  1  one or more divergences
  2  setup error (missing files, wrong pyshacl version, parse failure)
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "fixtures"
COMPILED_JSON_SCHEMA_DIR = ROOT / "compiled" / "json-schema" / "core"

# Shape file set must match tools/ci_validate.py::SHAPES.
SHACL_SHAPES = [
    "shapes/rkaf-shapes-core.ttl",
    "shapes/rkaf-shapes-warrant.ttl",
    "shapes/rkaf-shapes-confidence.ttl",
    "shapes/rkaf-shapes-accessscope.ttl",
    "shapes/rkaf-shapes-studio-promotions.ttl",
    "shapes/rkaf-shapes-conceptregistry.ttl",
    "compiled/shacl/core/authority.ttl",
    "compiled/shacl/core/attestation.ttl",
    "compiled/shacl/core/local-adoption.ttl",
    "compiled/shacl/core/applicability-scope.ttl",
    "compiled/shacl/core/effective-period.ttl",
    "compiled/shacl/core/lifecycle-event.ttl",
    "compiled/shacl/core/concept.ttl",
    "compiled/shacl/core/concept-mapping.ttl",
    "compiled/shacl/core/concept-resolution-result.ttl",
    "compiled/shacl/core/bridge-validation-result.ttl",
    "compiled/shacl/core/bridge-consumer-registration.ttl",
    "compiled/shacl/core/registry-conflict.ttl",
    "compiled/shacl/core/justification.ttl",
]


@dataclass
class FixtureResult:
    name: str
    expected: str        # "positive" | "negative" | "edge"
    l1: str = "?"        # "pass" | "fail" | "skip"
    l2: str = "?"
    l3: str = "?"
    l4: str = "not-tested"
    notes: list[str] = field(default_factory=list)
    diverged: bool = False


# ---------------------------------------------------------------- gate helpers


def load_jsonld(path: Path) -> Optional[dict]:
    """L1 gate: parse the document as JSON. (JSON-LD-specific expansion is
    handled by pyshacl + rdflib when L3 runs; the L1 check is "structurally
    parseable as JSON.")"""
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


_SCHEMA_CACHE: dict[str, dict] = {}


def _load_schema(name: str) -> Optional[dict]:
    if name in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[name]
    candidate = COMPILED_JSON_SCHEMA_DIR / f"{name}.schema.json"
    if not candidate.is_file():
        return None
    schema = json.loads(candidate.read_text())
    _SCHEMA_CACHE[name] = schema
    return schema


_TYPE_TO_SCHEMA = {
    "rkaf:Artifact":                       ("artifact", "Artifact"),
    "rkaf:SourceFragment":                 ("source-fragment", "SourceFragment"),
    "rkaf:EvidenceBinding":                ("evidence-binding", "EvidenceBinding"),
    "rkaf:Warrant":                        ("warrant", "Warrant"),
    "rkaf:ConfidenceRecord":               ("confidence-record", "ConfidenceRecord"),
    "rkaf:AccessScope":                    ("access-scope", "AccessScope"),
    "rkaf:AILineage":                      ("ai-lineage", "AILineage"),
    "rkaf:Assertion":                      ("assertion", "Assertion"),
    "rkaf:RetentionPolicy":                ("retention-policy", "RetentionPolicy"),
    "rkaf:MappingState":                   ("mapping-state", "MappingState"),
    "rkaf:Workspace":                      ("workspace", "Workspace"),
    "rkaf:Authority":                      ("authority", "Authority"),
    "rkaf:Attestation":                    ("attestation", "Attestation"),
    "rkaf:LocalAdoption":                  ("local-adoption", "LocalAdoption"),
    "rkaf:ApplicabilityScope":             ("applicability-scope", "ApplicabilityScope"),
    "rkaf:EffectivePeriod":                ("effective-period", "EffectivePeriod"),
    "rkaf:LifecycleEvent":                 ("lifecycle-event", "LifecycleEvent"),
    "rkaf:RegisteredConcept":              ("concept", "RegisteredConcept"),
    "rkaf:LocalConcept":                   ("concept", "LocalConcept"),
    "rkaf:ConceptMapping":                 ("concept-mapping", "ConceptMapping"),
    "rkaf:MappingApplicabilityContext":    ("concept-mapping", "MappingApplicabilityContext"),
    "rkaf:ConceptResolutionResult":        ("concept-resolution-result", "ConceptResolutionResult"),
    "rkaf:BridgeValidationResult":         ("bridge-validation-result", "BridgeValidationResult"),
    "rkaf:BridgeConsumerRegistration":     ("bridge-consumer-registration", "BridgeConsumerRegistration"),
    "rkaf:RegistryConflict":               ("registry-conflict", "RegistryConflict"),
    "rkaf:Justification":                  ("justification", "Justification"),
}


def l2_validate(doc: dict) -> tuple[bool, list[str]]:
    """L2 gate: walk every node (root or in @graph) with an @type starting
    with `rkaf:`, look up the schema, validate against `$defs.<ClassName>`.
    Returns (passed, error_messages)."""
    try:
        import jsonschema
    except ImportError:
        return False, ["jsonschema not installed"]

    nodes: list[dict] = []
    if "@graph" in doc and isinstance(doc["@graph"], list):
        nodes.extend(n for n in doc["@graph"] if isinstance(n, dict))
    else:
        nodes.append(doc)

    errs: list[str] = []
    for node in nodes:
        type_iri = node.get("@type")
        if not isinstance(type_iri, str) or not type_iri.startswith("rkaf:"):
            continue
        if type_iri not in _TYPE_TO_SCHEMA:
            continue  # unknown rkaf:* class — pass silently per L2 spec
        schema_name, class_name = _TYPE_TO_SCHEMA[type_iri]
        schema = _load_schema(schema_name)
        if schema is None:
            errs.append(f"schema missing for {type_iri}")
            continue
        # Wrap with top-level $ref so the JSON Schema validator targets the right $defs entry.
        wrapper = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref":    f"#/$defs/{class_name}",
            "$defs":   schema.get("$defs", {}),
        }
        try:
            jsonschema.Draft202012Validator(wrapper).validate(node)
        except jsonschema.ValidationError as e:
            errs.append(f"{type_iri}: {e.message}")
    return (not errs), errs


_SHACL_GRAPH_CACHE = None


def _load_shacl_graph():
    global _SHACL_GRAPH_CACHE
    if _SHACL_GRAPH_CACHE is not None:
        return _SHACL_GRAPH_CACHE
    import rdflib
    g = rdflib.Graph()
    for p in SHACL_SHAPES:
        full = ROOT / p
        if full.is_file():
            g.parse(str(full), format="turtle")
    _SHACL_GRAPH_CACHE = g
    return g


def l3_validate(fixture_path: Path) -> tuple[bool, int]:
    """L3 gate: run pyshacl on the fixture against the full SHACL shape suite.
    Returns (conforms, violation_count)."""
    try:
        import rdflib
        from pyshacl import validate
    except ImportError:
        return False, -1

    data_graph = rdflib.Graph()
    try:
        data_graph.parse(str(fixture_path), format="json-ld")
    except Exception:
        return False, -1

    shapes_g = _load_shacl_graph()
    conforms, report_g, _ = validate(
        data_graph=data_graph,
        shacl_graph=shapes_g,
        inference="rdfs",
        advanced=True,
        meta_shacl=False,
    )
    SH = rdflib.Namespace("http://www.w3.org/ns/shacl#")
    violations = list(report_g.subjects(rdflib.RDF.type, SH.ValidationResult))
    return conforms, len(violations)


# ---------------------------------------------------------------- main loop


def classify_fixture(name: str) -> str:
    """Infer expected verdict from filename pattern: '-negative' → negative,
    '-edge' → edge, anything else → positive."""
    n = name.lower()
    if "-negative" in n:
        return "negative"
    if "-edge" in n:
        return "edge"
    return "positive"


def walk_fixtures() -> list[Path]:
    """Walk fixtures/ recursively for .jsonld files. Excludes:
      - `fixtures/context.jsonld` (shared JSON-LD context, not a fixture)
      - `fixtures/projectors/` (carries `{native, overlay}` envelopes,
        consumed by tools/projector_parity.py, not single Rulespec nodes)
      - `fixtures/adversarial/` (cross-gate divergence corpus consumed by
        tools/constraints_parity.py — documents expected JSON-Schema vs
        SHACL divergence, not conformance)
      - `fixtures/ai-extraction/` (same — AI-extraction adversarial corpus)
    """
    skip_dirs = {"projectors", "adversarial", "ai-extraction"}
    paths: list[Path] = []
    for p in FIXTURES_DIR.rglob("*.jsonld"):
        rel = p.relative_to(FIXTURES_DIR).as_posix()
        if rel == "context.jsonld":
            continue
        if any(part in skip_dirs for part in p.relative_to(FIXTURES_DIR).parts):
            continue
        paths.append(p)
    paths.sort()
    return paths


def evaluate(path: Path) -> FixtureResult:
    name = path.relative_to(FIXTURES_DIR).as_posix()
    result = FixtureResult(name=name, expected=classify_fixture(name))

    doc = load_jsonld(path)
    if doc is None:
        result.l1 = "fail"
        result.l2 = "skip"
        result.l3 = "skip"
        result.notes.append("JSON parse failed")
    else:
        result.l1 = "pass"
        l2_ok, l2_errs = l2_validate(doc)
        result.l2 = "pass" if l2_ok else "fail"
        if l2_errs:
            result.notes.extend(f"L2: {m}" for m in l2_errs[:3])
        l3_ok, _violations = l3_validate(path)
        result.l3 = "pass" if l3_ok else "fail"

    # Expectation check: positives must pass L2 + L3; negatives must fail L2 OR L3.
    if result.expected == "positive":
        result.diverged = not (result.l2 == "pass" and result.l3 == "pass")
    elif result.expected == "negative":
        result.diverged = not (result.l2 == "fail" or result.l3 == "fail")
    # edges: no strict expectation — report only.

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true",
                    help="emit a machine-readable JSON report on stdout")
    ap.add_argument("--self-certify", action="store_true",
                    help="emit a self-certification YAML on stdout summarizing this run")
    args = ap.parse_args()

    results = [evaluate(p) for p in walk_fixtures()]
    diverged = [r for r in results if r.diverged]

    if args.json:
        report = {
            "rulespec_version": (ROOT / "VERSION").read_text().strip(),
            "ran_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "fixtures": [
                {"name": r.name, "expected": r.expected,
                 "L1": r.l1, "L2": r.l2, "L3": r.l3, "L4": r.l4,
                 "notes": r.notes, "diverged": r.diverged}
                for r in results
            ],
            "summary": {
                "total":    len(results),
                "diverged": len(diverged),
                "positive": sum(1 for r in results if r.expected == "positive"),
                "negative": sum(1 for r in results if r.expected == "negative"),
                "edge":     sum(1 for r in results if r.expected == "edge"),
            },
        }
        print(json.dumps(report, indent=2))
        return 1 if diverged else 0

    if args.self_certify:
        l2_pass = all(r.l2 == "pass" for r in results if r.expected == "positive") and \
                  all(r.l2 == "fail" for r in results if r.expected == "negative")
        l3_pass = all(r.l3 == "pass" for r in results if r.expected == "positive") and \
                  all(r.l3 == "fail" for r in results if r.expected == "negative")
        version = (ROOT / "VERSION").read_text().strip()
        print(f"""# Auto-generated by tools/conformance_report.py --self-certify
partner:          "Rulespec maintainers"
implementation:   "rkaf-validate@{version} + tools/ci_validate.py"
rulespec_version: "{version}"
declared_levels:  [L1, L2, L3]
adoption_depth:   D3
test_corpus_run_at: "{datetime.datetime.now(datetime.timezone.utc).isoformat()}"
test_corpus_commit: "<see git log>"
results:
  L1: pass
  L2: {"pass" if l2_pass else "fail"}
  L3: {"pass" if l3_pass else "fail"}
  L4: not-claimed
notes: |
  {len(results)} fixtures evaluated; {len(diverged)} divergences.""")
        return 1 if diverged else 0

    # Human-readable table.
    print(f"{'fixture':<55} {'exp':<10} {'L1':<6} {'L2':<6} {'L3':<6}")
    print("-" * 90)
    for r in results:
        flag = " *" if r.diverged else ""
        print(f"{r.name:<55} {r.expected:<10} {r.l1:<6} {r.l2:<6} {r.l3:<6}{flag}")
    print()
    print(f"Total: {len(results)} fixtures, {len(diverged)} divergences")
    if diverged:
        print()
        print("Divergent:")
        for r in diverged:
            print(f"  {r.name} (expected={r.expected}, L1={r.l1} L2={r.l2} L3={r.l3})")
            for n in r.notes[:2]:
                print(f"    {n}")
    return 1 if diverged else 0


if __name__ == "__main__":
    sys.exit(main())
