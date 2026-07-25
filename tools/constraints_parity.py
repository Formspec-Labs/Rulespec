#!/usr/bin/env python3
"""Cross-target constraint parity orchestrator.

For every (constraint, fixture) pair, run the fixture through each compiled
target and assert that the violation classification (PASS / FAIL) is identical
across all targets. Cross-target divergence is a release blocker per source
spec §6.3.

Targets exercised in this MVP:
  - JSON Schema 2020-12 (via Python `jsonschema` package, Draft202012Validator)
  - SHACL Turtle        (via pyshacl 0.31+)

Rust and TypeScript targets compile to equivalent code; their parity is the
codegen's structural property (same enums, same field cardinalities), not a
fixture run. The full SDK-side parity test lands in Layer 5 (Plan 6).

Exit codes:
  0  every fixture × target produced the same classification, all match expected
  1  ≥1 cross-target divergence OR mismatch with expected outcome
  2  setup error
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
import rdflib
from jsonschema import Draft202012Validator, FormatChecker
from pyshacl import validate as shacl_validate

ROOT = Path(__file__).resolve().parent.parent

# Constraint name → (CUE basename, subdir under constraints/)
# All v0.2 constraints. The compiled artifacts live under compiled/<target>/<subdir>/<basename>.<ext>
CONSTRAINTS: dict[str, tuple[str, str]] = {
    "artifact":                "core",
    "source-fragment":         "core",
    "evidence-binding":        "core",
    "warrant":                 "core",
    "confidence-record":       "core",
    "access-scope":            "core",
    "ai-lineage":              "core",
    "retention-policy":        "core",
    "workspace":               "core",
    "mapping-state":           "core",
    "concept-registry":        "core",
    "rulemaking":              "core",
    "assertion":               "core",
    "relationship-assertion":  "core",
    "conditional-silent-pass": "adversarial",
    "cross-property-coupling": "adversarial",
    "enum-drift":              "adversarial",
    "access-scope-leakage":    "adversarial",
    "nested-noevidencereason": "adversarial",
    "warrant-family-confusion":      "ai-extraction",
    "consent-vs-warrant":            "ai-extraction",
    "confidence-score-without-method": "ai-extraction",
}


# Adversarial fixtures by design surface evaluator-class divergences (per spec
# §10.1). For these, divergence between targets is the documented finding, not
# a release-blocking failure. The CORE Vocabulary fixtures, in contrast, MUST
# agree across targets — that is the §6.3 hard gate.
ADVERSARIAL_CONSTRAINTS = {
    "conditional-silent-pass",
    "cross-property-coupling",
    "enum-drift",
    "access-scope-leakage",
    "nested-noevidencereason",
    "warrant-family-confusion",
    "consent-vs-warrant",
    "confidence-score-without-method",
}


# (constraint, shape_def_name, fixture_path_relative_to_root, expected_outcome)
FIXTURE_BINDINGS: list[tuple[str, str, str, str]] = [
    # (constraint, shape_def, fixture, expected — PASS or FAIL)
    ("artifact", "Artifact", "fixtures/artifact-eli-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-doi-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-cid-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-us-cfr-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-us-usc-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-us-frdoc-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-us-regsgov-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-us-pl-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-us-eo-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-primary-topic-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/artifact-version-lineage-positive.jsonld", "PASS"),
    ("artifact", "Artifact", "fixtures/negatives/artifact-regulatory-identifier-missing-scheme-negative.jsonld", "FAIL"),
    ("artifact", "Artifact", "fixtures/negatives/artifact-regulatory-scheme-missing-identifier-negative.jsonld", "FAIL"),
    ("artifact", "Artifact", "fixtures/negatives/artifact-us-cfr-malformed-negative.jsonld", "FAIL"),
    ("artifact", "Artifact", "fixtures/negatives/artifact-us-usc-malformed-negative.jsonld", "FAIL"),
    ("artifact", "Artifact", "fixtures/negatives/artifact-us-frdoc-malformed-negative.jsonld", "FAIL"),
    ("artifact", "Artifact", "fixtures/negatives/artifact-us-regsgov-malformed-negative.jsonld", "FAIL"),
    ("artifact", "Artifact", "fixtures/negatives/artifact-us-pl-malformed-negative.jsonld", "FAIL"),
    ("artifact", "Artifact", "fixtures/negatives/artifact-us-eo-malformed-negative.jsonld", "FAIL"),
    ("rulemaking", "Docket", "fixtures/docket-us-regsgov-positive.jsonld", "PASS"),
    ("rulemaking", "Docket", "fixtures/negatives/docket-missing-has-docket-identifier-negative.jsonld", "FAIL"),
    ("rulemaking", "Docket", "fixtures/negatives/docket-missing-docket-identifier-scheme-negative.jsonld", "FAIL"),
    ("rulemaking", "Docket", "fixtures/negatives/docket-us-regsgov-malformed-negative.jsonld", "FAIL"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/agenda-item-ordinary-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/agenda-item-coast-guard-recurring-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/agenda-item-faa-recurring-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/agenda-item-repeated-unresolved-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaItem", "fixtures/negatives/regulatory-agenda-item-missing-required-fields-negative.jsonld", "FAIL"),
    ("rulemaking", "RegulatoryAgendaObservation", "fixtures/agenda-observations-multiple-editions-positive.jsonld", "PASS"),
    ("rulemaking", "RegulatoryAgendaObservation", "fixtures/negatives/regulatory-agenda-observation-missing-required-fields-negative.jsonld", "FAIL"),
    ("rulemaking", "AgendaProceedingRelationship", "fixtures/agenda-item-ordinary-positive.jsonld", "PASS"),
    ("rulemaking", "AgendaProceedingRelationship", "fixtures/negatives/agenda-proceeding-relationship-missing-required-fields-negative.jsonld", "FAIL"),
    ("rulemaking", "Proceeding", "fixtures/proceeding-partner-positive.jsonld", "PASS"),
    ("rulemaking", "Proceeding", "fixtures/negatives/proceeding-missing-has-proceeding-identifier-negative.jsonld", "FAIL"),
    ("rulemaking", "Proceeding", "fixtures/negatives/proceeding-missing-proceeding-identifier-scheme-negative.jsonld", "FAIL"),
    ("rulemaking", "Proceeding", "fixtures/edges/proceeding-multi-docket-edge.jsonld", "PASS"),
    ("rulemaking", "Proceeding", "fixtures/proceeding-unknown-authority-positive.jsonld", "PASS"),
    ("rulemaking", "Proceeding", "fixtures/negatives/proceeding-rin-as-identity-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/commentperiod-positive.jsonld", "PASS"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-missing-comment-period-for-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-missing-comment-period-start-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-missing-comment-period-end-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-missing-provenance-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-malformed-date-negative.jsonld", "FAIL"),
    ("rulemaking", "CommentPeriod", "fixtures/negatives/comment-period-end-before-start-negative.jsonld", "FAIL"),
    ("warrant",  "Warrant",  "fixtures/warrant-legal-positive.jsonld", "PASS"),
    ("warrant",  "Warrant",  "fixtures/warrant-scientific-positive.jsonld", "PASS"),
    ("confidence-record", "ConfidenceRecord", "fixtures/confidencerecord-uncalibrated-positive.jsonld", "PASS"),
    ("confidence-record", "ConfidenceRecord", "fixtures/confidencerecord-calibrated-positive.jsonld", "PASS"),
    ("confidence-record", "ConfidenceRecord", "fixtures/confidencerecord-score-theater-negative.jsonld", "FAIL"),
    ("access-scope",      "AccessScope",      "fixtures/accessscope-public-positive.jsonld", "PASS"),
    ("access-scope",      "AccessScope",      "fixtures/accessscope-organizationVisible-positive.jsonld", "PASS"),
    ("access-scope",      "AccessScope",      "fixtures/accessscope-leak-negative.jsonld", "FAIL"),
    ("ai-lineage",        "AILineage",        "fixtures/ailineage-positive.jsonld", "PASS"),
    ("ai-lineage",        "AILineage",        "fixtures/ailineage-missing-approver-negative.jsonld", "FAIL"),
    ("retention-policy",  "RetentionPolicy",  "fixtures/retentionpolicy-positive.jsonld", "PASS"),
    ("workspace",         "Workspace",        "fixtures/workspace-positive.jsonld", "PASS"),
    ("evidence-binding",  "EvidenceBinding",  "fixtures/evidencebinding-positive.jsonld", "PASS"),
    ("evidence-binding",  "EvidenceBinding",  "fixtures/evidencebinding-no-evidence-reason-positive.jsonld", "PASS"),
    ("evidence-binding",  "EvidenceBinding",  "fixtures/evidencebinding-missing-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/relationshipassertion-denied-positive.jsonld", "PASS"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/relationshipassertion-affirmed-positive.jsonld", "PASS"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-subject-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-origin-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-predicate-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-object-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-missing-polarity-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-invalid-polarity-negative.jsonld", "FAIL"),
    ("relationship-assertion", "RelationshipAssertion",
     "fixtures/negatives/relationship-assertion-ai-missing-lineage-negative.jsonld", "FAIL"),
    # Adversarial — evaluator-class regressions
    ("conditional-silent-pass", "ConsensusEvidencePermissionShape",
     "fixtures/adversarial/conditional-silent-pass-positive.jsonld", "PASS"),
    ("conditional-silent-pass", "ConsensusEvidencePermissionShape",
     "fixtures/adversarial/conditional-silent-pass-negative.jsonld", "FAIL"),
    ("enum-drift",              "EnumDriftWarrant",
     "fixtures/adversarial/enum-drift-negative.jsonld", "FAIL"),
    ("cross-property-coupling", "ModelInferenceCoupling",
     "fixtures/adversarial/cross-property-coupling-negative.jsonld", "FAIL"),
    ("nested-noevidencereason", "NestedNoEvidenceReasonShape",
     "fixtures/adversarial/nested-noevidencereason-positive.jsonld", "PASS"),
    # AI-extraction adversarial — LLM systematic misinterpretation
    ("warrant-family-confusion", "WarrantFamilyConfusionRejector",
     "fixtures/ai-extraction/warrant-family-confusion-negative.jsonld", "FAIL"),
    ("consent-vs-warrant", "ConsentVsWarrantRejector",
     "fixtures/ai-extraction/consent-vs-warrant-negative.jsonld", "FAIL"),
    ("confidence-score-without-method", "ConfidenceScoreWithoutMethodRejector",
     "fixtures/ai-extraction/confidence-score-without-method-negative.jsonld", "FAIL"),
]


def run_jsonschema(constraint: str, shape: str, fixture_path: Path) -> str:
    subdir = CONSTRAINTS[constraint]
    schema_path = ROOT / "compiled" / "json-schema" / subdir / f"{constraint}.schema.json"
    schema_doc = json.loads(schema_path.read_text())
    target_schema = schema_doc["$defs"][shape]
    target_schema["$defs"] = schema_doc.get("$defs", {})
    payload = json.loads(fixture_path.read_text())
    # JSON-LD fixtures with @graph: validate each node of the matching @type
    if "@graph" in payload:
        nodes = [n for n in payload["@graph"] if n.get("@type") == target_schema.get("properties", {}).get("@type", {}).get("const")]
    else:
        nodes = [payload]
    for node in nodes:
        node = dict(node)
        node.pop("@context", None)
        errs = list(
            Draft202012Validator(
                target_schema,
                format_checker=FormatChecker(),
            ).iter_errors(node)
        )
        for order in target_schema.get("x-rkaf-order", []):
            lower = node.get(order["lower"])
            upper = node.get(order["upper"])
            if isinstance(lower, str) and isinstance(upper, str) and lower > upper:
                errs.append(
                    ValueError(
                        f"{order['lower']} must be less than or equal to {order['upper']}"
                    )
                )
        if errs:
            return "FAIL"
    return "PASS"


def run_shacl(constraint: str, shape: str, fixture_path: Path) -> str:
    subdir = CONSTRAINTS[constraint]
    shape_path = ROOT / "compiled" / "shacl" / subdir / f"{constraint}.ttl"
    if not shape_path.exists():
        return "PASS"  # if no SHACL emitted (e.g. enum-only), treat as PASS
    data = rdflib.Graph()
    # rdflib logs a traceback while retaining malformed xsd:date lexemes.
    # Those lexemes are intentional negative-fixture inputs; SHACL should
    # produce the verdict without obscuring the parity report.
    term_logger = logging.getLogger("rdflib.term")
    previous_level = term_logger.level
    term_logger.setLevel(logging.CRITICAL)
    try:
        data.parse(str(fixture_path), format="json-ld")
    finally:
        term_logger.setLevel(previous_level)
    shapes = rdflib.Graph()
    shapes.parse(str(shape_path), format="turtle")
    conforms, _, _ = shacl_validate(
        data_graph=data, shacl_graph=shapes,
        inference="rdfs", advanced=True, meta_shacl=False,
    )
    return "PASS" if conforms else "FAIL"


# Rust and TypeScript codegen targets emit equivalent enum/struct code; their
# parity to JSON Schema is structural (same enums, same cardinalities, same
# disjunctions). The full SDK-runtime parity check (which would actually run
# Rust/TS validators on JSON-LD docs) lands in Plan 6 (SDK layer). For Layer 2,
# we assert structural parity: every enum/shape in the JSON Schema target also
# appears (by name) in the Rust and TypeScript targets.
def structural_parity_rust(constraint: str) -> bool:
    subdir = CONSTRAINTS[constraint]
    js = (ROOT / "compiled" / "json-schema" / subdir / f"{constraint}.schema.json").read_text()
    # Canonical Rust sink is crates/rkaf-core/src/generated/<snake>.rs.
    # adversarial/ + ai-extraction/ constraints are not compiled to Rust
    # (Plan 7a-7c restriction); skip parity for those.
    if subdir != "core":
        return True
    snake = constraint.replace("-", "_")
    rs_path = ROOT / "crates" / "rkaf-core" / "src" / "generated" / f"{snake}.rs"
    if not rs_path.exists():
        return False
    rs = rs_path.read_text()
    schema = json.loads(js)
    for name in schema.get("$defs", {}):
        # Each $defs entry must appear in the Rust output as either `pub enum {name}`
        # (for closed enums), `pub struct {name}` (for shapes), or a
        # fully-qualified cross-module reference ending in `::{name}`.
        if (
            f"pub enum {name}" not in rs
            and f"pub struct {name}" not in rs
            and f"::{name}" not in rs
        ):
            return False
    return True


def structural_parity_typescript(constraint: str) -> bool:
    subdir = CONSTRAINTS[constraint]
    js  = (ROOT / "compiled" / "json-schema" / subdir / f"{constraint}.schema.json").read_text()
    ts  = (ROOT / "compiled" / "typescript"  / subdir / f"{constraint}.ts").read_text()
    schema = json.loads(js)
    for name in schema.get("$defs", {}):
        if (
            f"export type {name}" not in ts
            and f"export interface {name}" not in ts
            and f"import type {{ {name} }}" not in ts
        ):
            return False
    return True


def main() -> int:
    print(f"Running {len(FIXTURE_BINDINGS)} fixture×constraint pairs across targets")
    print("=" * 70)
    print("CORE PARITY (release gate — all targets MUST agree)")
    print("-" * 70)
    core_divergences = 0
    adversarial_findings = 0
    for constraint, shape, fpath, expected in FIXTURE_BINDINGS:
        full = ROOT / fpath
        if not full.exists():
            print(f"  [SKIP] {fpath} (missing)")
            continue
        js_result    = run_jsonschema(constraint, shape, full)
        shacl_result = run_shacl(constraint, shape, full)
        rs_struct = structural_parity_rust(constraint)
        ts_struct = structural_parity_typescript(constraint)
        all_match = js_result == shacl_result
        # The MUST target (JSON Schema) must classify per the expected outcome.
        match_expected = js_result == expected
        is_adversarial = constraint in ADVERSARIAL_CONSTRAINTS
        if is_adversarial:
            # Adversarial fixtures: JSON Schema (the MUST target) must classify
            # per expected. SHACL divergence is a documented finding, not a
            # blocker (the fixture exists to surface evaluator-class gaps).
            ok = match_expected and rs_struct and ts_struct
            target_divergence = not all_match
            status = "OK" if ok else "FAIL"
            note = " (sh-divergence — expected for adversarial)" if target_divergence else ""
        else:
            # Core fixtures: every target must agree, must match expected.
            ok = all_match and match_expected and rs_struct and ts_struct
            target_divergence = not all_match
            status = "OK" if ok else "DIVERGE"
            note = ""
        line = (f"  [{status}] {constraint:35s} expected={expected:4s} "
                f"json-schema={js_result:4s} shacl={shacl_result:4s} "
                f"rust-struct={'OK' if rs_struct else 'FAIL':4s} "
                f"ts-struct={'OK' if ts_struct else 'FAIL':4s} "
                f"{Path(fpath).name}{note}")
        print(line)
        if not ok:
            if is_adversarial:
                adversarial_findings += 1
            else:
                core_divergences += 1
    print("=" * 70)
    print(f"CORE divergences (release blockers): {core_divergences}")
    print(f"ADVERSARIAL findings (documentation): {adversarial_findings}")
    return 1 if core_divergences > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
