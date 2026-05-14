#!/usr/bin/env python3
"""Audit Layer 4 behavior-fixture coverage.

This is not a verdict runner. `rkaf-behavior-validate` proves that each
fixture's expected output matches the runtime. This audit proves that the
fixture corpus actually names every L4 branch the conformance claim depends on.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
BEHAVIOR_DIR = ROOT / "fixtures" / "behavior"

LATTICE = [
    "rkaf:notEligible",
    "rkaf:searchOnly",
    "rkaf:reviewQueueOnly",
    "rkaf:draftGenerationAllowed",
    "rkaf:localOperationalUse",
    "rkaf:publicationAllowed",
    "rkaf:officialUse",
]

CONTRACTS = {
    "rkaf:UsageEligibilityReducer",
    "rkaf:CascadeClosureV1",
    "rkaf:BridgeContractRule",
    "rkaf:PointInTimeException",
    "rkaf:ConceptResolutionWithConflict",
}

CASCADE_EDGES = {
    "rkaf:derivedFromFragment",
    "rkaf:justifiedByAssertion",
    "rkaf:hasAuthority",
    "rkaf:derivesAuthorityFrom",
    "rkaf:implements",
    "rkaf:requiresEvidenceType",
    "rkaf:collectsEvidenceType",
    "rkaf:operationallyDependsOn",
    "rkaf:targetAssertion",
    "rkaf:assertsObject",
    "skos:exactMatch",
    "skos:closeMatch",
    "skos:broadMatch",
    "skos:narrowMatch",
    "skos:relatedMatch",
    "rkaf:sourceConcept",
    "rkaf:targetConcept",
}

REDUCER_BRANCHES = {
    "baseline_workspace",
    "applicability_gate",
    "local_adoption_broadens",
    "capability_cap_narrows",
    "stale_narrows",
    "stale_honored_pit",
}

PIT_BRANCHES = {
    "supported_anchor_retains",
    "unsupported_anchor_refuses",
}

CONCEPT_RESULTS = {
    "rkaf:unresolved",
    "rkaf:resolved",
    "rkaf:conflict",
}

CONCEPT_SEVERITIES = {
    "rkaf:informational",
    "rkaf:operationalConflict",
    "rkaf:publicationBlocking",
    "rkaf:authorityCritical",
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def graph_nodes(doc: dict[str, Any]) -> list[dict[str, Any]]:
    graph = doc.get("rkaf:input", {}).get("@graph", [])
    return [n for n in graph if isinstance(n, dict)]


def node_types(node: dict[str, Any]) -> set[str]:
    value = node.get("@type")
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {v for v in value if isinstance(v, str)}
    return set()


def nodes_by_type(doc: dict[str, Any], type_iri: str) -> list[dict[str, Any]]:
    return [n for n in graph_nodes(doc) if type_iri in node_types(n)]


def node_by_id(doc: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for node in graph_nodes(doc):
        if node.get("@id") == node_id:
            return node
    return None


def values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, str)]
    return []


def rank(level: str) -> int:
    try:
        return LATTICE.index(level)
    except ValueError:
        return -1


def output_levels(expected: dict[str, Any]) -> list[str]:
    if isinstance(expected.get("effectiveUsageEligibility"), str):
        return [expected["effectiveUsageEligibility"]]
    by_scope = expected.get("byScope")
    if isinstance(by_scope, dict):
        return [v for v in by_scope.values() if isinstance(v, str)]
    return []


def string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(string_values(item))
        return out
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(string_values(item))
        return out
    return []


def supported_anchors(doc: dict[str, Any]) -> set[str]:
    anchors: set[str] = set()
    for reg in nodes_by_type(doc, "rkaf:BridgeConsumerRegistration"):
        anchors.update(values(reg.get("rkaf:supportedEvaluationAnchors")))
    return anchors


def has_supported_pit(doc: dict[str, Any], assertion_id: str) -> bool:
    supported = supported_anchors(doc)
    for pit in nodes_by_type(doc, "rkaf:PointInTimeException"):
        if pit.get("rkaf:retainsAssertion") == assertion_id:
            anchor = pit.get("rkaf:evaluationAnchor")
            if isinstance(anchor, str) and anchor in supported:
                return True
    return False


def collect_reducer_branch(doc: dict[str, Any], branches: set[str]) -> None:
    subject_id = doc.get("rkaf:subjectAssertion")
    if not isinstance(subject_id, str):
        return
    assertion = node_by_id(doc, subject_id)
    if assertion is None:
        return

    expected = doc.get("rkaf:expectedOutput", {})
    levels = output_levels(expected)
    baseline = assertion.get("rkaf:usageEligibility", "rkaf:notEligible")
    is_stale = assertion.get("rkaf:consumerLifecycleState") == "rkaf:staleForCurrentUse"

    if (
        "rkaf:evaluationScopes" not in doc
        and expected.get("effectiveUsageEligibility") == baseline
        and not is_stale
        and not nodes_by_type(doc, "rkaf:LocalAdoption")
        and not nodes_by_type(doc, "rkaf:BridgeConsumerRegistration")
    ):
        branches.add("baseline_workspace")

    if assertion.get("rkaf:hasApplicability") and "rkaf:notEligible" in levels:
        branches.add("applicability_gate")

    if is_stale and "rkaf:notEligible" in levels and not has_supported_pit(doc, subject_id):
        branches.add("stale_narrows")

    if is_stale and has_supported_pit(doc, subject_id) and baseline in levels:
        branches.add("stale_honored_pit")

    for level in levels:
        if rank(level) > rank(baseline):
            for adoption in nodes_by_type(doc, "rkaf:LocalAdoption"):
                if adoption.get("rkaf:targetAssertion") == subject_id:
                    branches.add("local_adoption_broadens")

        if rank(level) < rank(baseline):
            for reg in nodes_by_type(doc, "rkaf:BridgeConsumerRegistration"):
                cap = reg.get("rkaf:capabilityCap")
                if isinstance(cap, str) and level == cap:
                    branches.add("capability_cap_narrows")


def collect_cascade_edges(doc: dict[str, Any], edges: set[str]) -> None:
    seed = doc.get("rkaf:cascadeSeed")
    expected = doc.get("rkaf:expectedOutput", {})
    affected = set(values(expected.get("affectedSet")))
    if not isinstance(seed, str):
        return
    for node in graph_nodes(doc):
        node_id = node.get("@id")
        if not isinstance(node_id, str) or node_id not in affected:
            continue
        for predicate in CASCADE_EDGES:
            if seed in values(node.get(predicate)):
                edges.add(predicate)


def collect_bridge_rule(
    doc: dict[str, Any],
    by_rule: dict[int, set[str]],
    extras: set[str],
) -> None:
    rule = doc.get("rkaf:contractRuleNumber")
    expected = doc.get("rkaf:expectedOutput", {})
    result = expected.get("bridgeValidationResult")
    if isinstance(rule, int) and isinstance(result, str):
        by_rule[rule].add(result)

    if rule != 5 or result != "rkaf:accepted":
        return

    migrations: set[str] = set()
    for reg in nodes_by_type(doc, "rkaf:BridgeConsumerRegistration"):
        migrations.update(values(reg.get("rkaf:supportedAutomaticMigrations")))
    for event in nodes_by_type(doc, "rkaf:LifecycleEvent"):
        migration = event.get("rkaf:safeAutomaticMigration")
        if isinstance(migration, str) and migration in migrations:
            extras.add("rule5_safe_automatic_migration")


def collect_pit_branch(doc: dict[str, Any], branches: set[str]) -> None:
    expected = doc.get("rkaf:expectedOutput", {})
    if expected.get("errorClass") == "rkaf:UnsupportedEvaluationAnchor":
        branches.add("unsupported_anchor_refuses")
    if "rkaf:retainedForPointInTime" in string_values(expected):
        branches.add("supported_anchor_retains")


def collect_concept_branch(
    doc: dict[str, Any],
    results: set[str],
    severities: set[str],
) -> None:
    expected = doc.get("rkaf:expectedOutput", {})
    result = expected.get("resolutionResult")
    if isinstance(result, str):
        results.add(result)
    conflict = expected.get("registryConflict")
    if isinstance(conflict, dict):
        severity = conflict.get("severity")
        if isinstance(severity, str):
            severities.add(severity)


def main() -> int:
    docs = [(p, load(p)) for p in sorted(BEHAVIOR_DIR.glob("*.jsonld"))]
    issues: list[str] = []
    contracts: set[str] = set()
    bridge_by_rule: dict[int, set[str]] = defaultdict(set)
    bridge_extras: set[str] = set()
    reducer_branches: set[str] = set()
    pit_branches: set[str] = set()
    concept_results: set[str] = set()
    concept_severities: set[str] = set()
    cascade_edges: set[str] = set()
    cascade_as_of = False

    for path, doc in docs:
        if doc.get("@type") != "rkaf:BehaviorTestCase":
            issues.append(f"{path.name}: @type is not rkaf:BehaviorTestCase")
            continue
        contract = doc.get("rkaf:behaviorContract")
        if not isinstance(contract, str):
            issues.append(f"{path.name}: missing rkaf:behaviorContract")
            continue
        contracts.add(contract)

        if contract == "rkaf:BridgeContractRule":
            collect_bridge_rule(doc, bridge_by_rule, bridge_extras)
        elif contract == "rkaf:UsageEligibilityReducer":
            collect_reducer_branch(doc, reducer_branches)
        elif contract == "rkaf:CascadeClosureV1":
            collect_cascade_edges(doc, cascade_edges)
            cascade_as_of = cascade_as_of or isinstance(doc.get("rkaf:cascadeAsOf"), str)
        elif contract == "rkaf:PointInTimeException":
            collect_pit_branch(doc, pit_branches)
        elif contract == "rkaf:ConceptResolutionWithConflict":
            collect_concept_branch(doc, concept_results, concept_severities)

    missing_contracts = CONTRACTS - contracts
    if missing_contracts:
        issues.append(f"missing behavior contracts: {sorted(missing_contracts)}")

    for rule in range(1, 11):
        seen = bridge_by_rule.get(rule, set())
        if "rkaf:accepted" not in seen:
            issues.append(f"bridge rule {rule}: missing accepted fixture")
        if "rkaf:rejected" not in seen:
            issues.append(f"bridge rule {rule}: missing rejected fixture")
    if "rule5_safe_automatic_migration" not in bridge_extras:
        issues.append("bridge rule 5: missing safeAutomaticMigration exemption fixture")

    missing_reducer = REDUCER_BRANCHES - reducer_branches
    if missing_reducer:
        issues.append(f"reducer branches missing: {sorted(missing_reducer)}")

    missing_pit = PIT_BRANCHES - pit_branches
    if missing_pit:
        issues.append(f"PIT branches missing: {sorted(missing_pit)}")

    missing_results = CONCEPT_RESULTS - concept_results
    if missing_results:
        issues.append(f"concept resolution outcomes missing: {sorted(missing_results)}")

    missing_severities = CONCEPT_SEVERITIES - concept_severities
    if missing_severities:
        issues.append(f"concept conflict severities missing: {sorted(missing_severities)}")

    missing_cascade_edges = CASCADE_EDGES - cascade_edges
    if missing_cascade_edges:
        issues.append(f"cascade predicates missing: {sorted(missing_cascade_edges)}")
    if not cascade_as_of:
        issues.append("cascade: missing rkaf:cascadeAsOf fixture")

    print("L4 coverage audit")
    print(f"  behavior fixtures: {len(docs)}")
    print(f"  contracts: {len(contracts)}/{len(CONTRACTS)}")
    print(f"  bridge rules: {len(bridge_by_rule)}/10 plus safeAutomaticMigration")
    print(f"  reducer branches: {len(reducer_branches)}/{len(REDUCER_BRANCHES)}")
    print(f"  PIT branches: {len(pit_branches)}/{len(PIT_BRANCHES)}")
    print(
        "  concept outcomes/severities: "
        f"{len(concept_results)}/{len(CONCEPT_RESULTS)} + "
        f"{len(concept_severities)}/{len(CONCEPT_SEVERITIES)}"
    )
    print(f"  cascade predicates: {len(cascade_edges)}/{len(CASCADE_EDGES)}")

    if issues:
        print()
        print("Missing L4 coverage:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
