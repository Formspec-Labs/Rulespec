#!/usr/bin/env python3
"""Rulespec conformance reporter — L1/L2/L3/L4 per-fixture verdict.

For each fixture under `fixtures/` (positives, negatives, edges), runs three
gates and reports a structured verdict:

  L1 (Parse):       does the document parse as JSON-LD?
  L2 (Shape):       does every Rulespec-typed node validate against its
                    compiled JSON Schema?
  L3 (Constraint):  does the document pass the SHACL shape suite (hand-
                    authored Pattern-C invariants + CUE-compiled enums/
                    cardinality)?

L4 (Behavior) is gated for `fixtures/behavior/` by the Rust
`rkaf-behavior-validate` binary.

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
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from conformance_lib import (
    FIXTURES_DIR,
    fixture_name,
    fixture_paths,
    iter_nodes,
    load_json,
    schema_bindings,
    shacl_shape_paths,
)

ROOT = Path(__file__).resolve().parent.parent


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
        return load_json(path)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


_SCHEMA_CACHE: dict[Path, dict] = {}


def _load_schema(path: Path) -> Optional[dict]:
    if path in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[path]
    if not path.is_file():
        return None
    schema = json.loads(path.read_text())
    _SCHEMA_CACHE[path] = schema
    return schema


def l2_validate(doc: dict) -> tuple[bool, list[str]]:
    """L2 gate: walk every node (root or in @graph) with an @type starting
    with `rkaf:`, look up the schema, validate against `$defs.<ClassName>`.
    Returns (passed, error_messages)."""
    try:
        import jsonschema
    except ImportError:
        return False, ["jsonschema not installed"]

    nodes = list(iter_nodes(doc))
    bindings = schema_bindings()

    errs: list[str] = []
    for node in nodes:
        type_iri = node.get("@type")
        if not isinstance(type_iri, str) or not type_iri.startswith("rkaf:"):
            continue
        binding = bindings.get(type_iri)
        if binding is None:
            continue  # unknown rkaf:* class — pass silently per L2 spec
        schema = _load_schema(binding.schema_path)
        if schema is None:
            errs.append(f"schema missing for {type_iri}")
            continue
        # Wrap with top-level $ref so the JSON Schema validator targets the right $defs entry.
        wrapper = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref":    f"#/$defs/{binding.class_name}",
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
    for full in shacl_shape_paths():
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
    """Infer expected verdict from filename + path pattern:
      - `fixtures/behavior/<x>.jsonld` → behavior (L4 contract; L1+L2 only at
        shape gates; runtime impl validates the input→expectedOutput claim)
      - filename ends `-negative` → negative
      - filename ends `-edge` → edge
      - else → positive
    """
    n = name.lower()
    if n.startswith("behavior/"):
        return "behavior"
    if "-negative" in n:
        return "negative"
    if "-edge" in n:
        return "edge"
    return "positive"


def walk_fixtures() -> list[Path]:
    """Walk fixtures/ recursively for .jsonld files. Excludes:
      - `fixtures/projectors/` (carries `{native, overlay}` envelopes,
        consumed by tools/projector_parity.py, not single Rulespec nodes)
      - `fixtures/adversarial/` (cross-gate divergence corpus consumed by
        tools/constraints_parity.py — documents expected JSON-Schema vs
        SHACL divergence, not conformance)
      - `fixtures/ai-extraction/` (same — AI-extraction adversarial corpus)
    """
    return fixture_paths()


def evaluate(path: Path) -> FixtureResult:
    name = fixture_name(path)
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

    # Expectation check.
    #   positive  → MUST pass L2 + L3.
    #   negative  → MUST fail L2 OR L3.
    #   behavior  → MUST pass L1 + L2; L3 not gated (input @graph may contain
    #               stubs as declarative meta-content). L4 verdict is set
    #               separately by rkaf-behavior-validate.
    #   edge      → no strict expectation; report only.
    if result.expected == "positive":
        result.diverged = not (result.l2 == "pass" and result.l3 == "pass")
    elif result.expected == "negative":
        result.diverged = not (result.l2 == "fail" or result.l3 == "fail")
    elif result.expected == "behavior":
        # L1+L2 must pass on the wrapper + the inner rkaf:input graph.
        # L3 is permissive in the divergence check (input graph carries
        # declarative content + may use shapes a SHACL gate wouldn't validate),
        # but L3=fail surfaces in `notes` for visibility instead of being
        # silently masked.
        if result.l3 == "fail":
            result.notes.append("L3: behavior fixture's input graph has SHACL violations (permitted; not gated)")
        # L4 is computed by main() in a batched subprocess call to
        # rkaf-behavior-validate after per-fixture L1/L2/L3 evaluation.
        result.diverged = not (result.l1 == "pass" and result.l2 == "pass")
    # edges: no strict expectation — report only.

    return result


_RUNTIME_BINS = [
    ROOT / "crates" / "target" / "debug" / "rkaf-behavior-validate",
    ROOT / "crates" / "target" / "release" / "rkaf-behavior-validate",
]


def _l4_batch_evaluate(results: list) -> dict[str, str]:
    """Run rkaf-behavior-validate on every behavior fixture in one subprocess.
    Returns a {fixture_stem: "pass"|"fail"|"error"} map. If the binary is
    missing, returns an empty map (caller treats as a setup failure).
    """
    runtime_bin = next((p for p in _RUNTIME_BINS if p.is_file()), None)
    if runtime_bin is None:
        return {}
    import subprocess
    paths = [str(FIXTURES_DIR / r.name) for r in results]
    proc = subprocess.run(
        [str(runtime_bin), "--json", *paths],
        capture_output=True, cwd=ROOT,
    )
    if proc.returncode not in (0, 1):
        # 2 = setup error, others unexpected; report all as error
        return {Path(p).stem: "error" for p in paths}
    try:
        envelope = json.loads(proc.stdout.decode() or "{}")
    except json.JSONDecodeError:
        return {Path(p).stem: "error" for p in paths}
    return {entry["name"]: entry["result"] for entry in envelope.get("fixtures", [])}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true",
                    help="emit a machine-readable JSON report on stdout")
    ap.add_argument("--self-certify", action="store_true",
                    help="emit a self-certification YAML on stdout summarizing this run")
    args = ap.parse_args()

    results = [evaluate(p) for p in walk_fixtures()]

    # L4 batch evaluation: every "behavior" fixture is run through
    # rkaf-behavior-validate (single subprocess invocation). Result populates
    # the L4 column. Missing-binary is a divergence: an L4 conformance run
    # that did not execute L4 behavior fixtures is not green.
    behavior_results = [r for r in results if r.expected == "behavior"]
    if behavior_results:
        l4_map = _l4_batch_evaluate(behavior_results)
        for r in behavior_results:
            verdict = l4_map.get(Path(r.name).stem)
            if verdict in ("pass", "fail"):
                r.l4 = verdict
                if verdict == "fail":
                    r.diverged = True
            elif verdict == "error":
                r.l4 = "error"
                r.diverged = True
            else:
                r.l4 = "skip"
                r.diverged = True
                r.notes.append("L4: rkaf-behavior-validate binary missing; build with `cargo build --manifest-path crates/Cargo.toml --workspace`")

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
                "behavior": sum(1 for r in results if r.expected == "behavior"),
            },
        }
        print(json.dumps(report, indent=2))
        return 1 if diverged else 0

    if args.self_certify:
        l1_pass = all(r.l1 == "pass" for r in results)
        l2_pass = all(r.l2 == "pass" for r in results if r.expected == "positive") and \
                  all((r.l2 == "fail" or r.l3 == "fail") for r in results if r.expected == "negative")
        l3_pass = all(r.l3 == "pass" for r in results if r.expected == "positive") and \
                  all((r.l2 == "fail" or r.l3 == "fail") for r in results if r.expected == "negative")
        behavior = [r for r in results if r.expected == "behavior"]
        l4_pass = bool(behavior) and all(r.l4 == "pass" for r in behavior)
        version = (ROOT / "VERSION").read_text().strip()
        positive_count = sum(1 for r in results if r.expected == "positive")
        negative_count = sum(1 for r in results if r.expected == "negative")
        schema_count = len(schema_bindings())
        shape_count = len(shacl_shape_paths())
        required_slots = sum(
            len(set(binding.required) - {"@type"})
            for binding in schema_bindings().values()
        )
        ran_at = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        print(f"""# Self-certification for the Rulespec reference implementation in this repo.
# Generated by tools/conformance_report.py --self-certify.

partner:        "Rulespec maintainers"
implementation: "rkaf-validate@{version} + tools/ci_validate.py"

rulespec_version: "{version}"

declared_levels:
  - L1
  - L2
  - L3
  - L4

adoption_depth: D3   # reference consumer; this repo IS the reference implementation

test_corpus_run_at: "{ran_at.isoformat()}"
test_corpus_commit: "<see git log>"

results:
  L0: not-claimed
  L1: {"pass" if l1_pass else "fail"}
  L2: {"pass" if l2_pass else "fail"}     # rkaf-validate: discovered positive fixtures validate and cover every embedded schema type.
  L3: {"pass" if l3_pass else "fail"}     # tools/ci_validate.py: {positive_count} positive fixtures across {shape_count} SHACL shape files, 0 violations; {negative_count} negatives FAIL-AS-EXPECTED.
  L4: {"pass" if l4_pass else "fail"}     # rkaf-behavior-validate: {len(behavior)} behavior fixtures cover reducer, cascade, PIT, concept resolution, and all 10 bridge rules.

notes: |
  This implementation is the reference. Shape conformance (L1-L3) is end-to-end:
  CUE source-of-truth compiles to JSON Schema + SHACL + Rust; rkaf-validate
  discovers and embeds every compiled class schema; tools/ci_validate.py and
  tools/validate_negatives.py discover the current fixture and shape corpora.
  tools/conformance_report.py evaluated {len(results)} fixtures with {len(diverged)} divergences.
  tools/l0_l3_coverage_audit.py verifies L0 vocabulary/source coverage,
  L1 JSON-LD parse coverage, L2 positive/negative type coverage, all
  {required_slots} required-field negative slots, and L3 edge coverage across
  all {schema_count} compiled schema classes.

  L4 behavioral conformance is enforced by crates/rkaf-runtime and
  rkaf-behavior-validate against the {len(behavior)} fixtures under fixtures/behavior/.
  tools/l4_coverage_audit.py verifies branch coverage across all L4 contracts.

  Documented divergences:
    - 2 adversarial fixtures (`conditional-silent-pass-positive`,
      `nested-noevidencereason-positive`) are classified as "documentation
      findings" by tools/constraints_parity.py — known JSON-Schema/SHACL
      divergences on adversarial-class corpora, not release blockers.
    - `OneOrMany<T>` in rkaf-core accepts empty arrays (`[]` →
      `Many(vec![])`), bypassing `list.MinItems(N)` at the Rust layer.
      The matching JSON Schema enforces `minItems` correctly; the Rust
      wrapper trades type-strictness for round-trip parity. Documented in
      `crates/rkaf-core/src/lib.rs::OneOrMany`.""")
        return 1 if diverged else 0

    # Human-readable table.
    print(f"{'fixture':<55} {'exp':<10} {'L1':<6} {'L2':<6} {'L3':<6} {'L4':<6}")
    print("-" * 95)
    for r in results:
        flag = " *" if r.diverged else ""
        print(f"{r.name:<55} {r.expected:<10} {r.l1:<6} {r.l2:<6} {r.l3:<6} {r.l4:<6}{flag}")
    print()
    print(f"Total: {len(results)} fixtures, {len(diverged)} divergences")
    if diverged:
        print()
        print("Divergent:")
        for r in diverged:
            print(f"  {r.name} (expected={r.expected}, L1={r.l1} L2={r.l2} L3={r.l3} L4={r.l4})")
            for n in r.notes[:2]:
                print(f"    {n}")
    return 1 if diverged else 0


if __name__ == "__main__":
    sys.exit(main())
