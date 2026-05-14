//! Bridge contract rules — spec/rkaf-behavior.md §3.
//!
//! Each of the 10 rules is implemented as its own predicate function over
//! the graph + supporting context (consumer registration, attestation
//! contract). The dispatcher reads `contractRuleNumber` from the
//! BehaviorTestCase and routes to the matching function.

use serde_json::{json, Value};
use std::collections::HashSet;

use crate::{
    consumer as consumer_mod, errors::RuntimeError, graph::Graph, reducer, stale, verdict::Verdict,
};

/// Bridge rules are typed verdicts: accepted / acceptedWithWarnings /
/// rejected. The runtime emits the §7 output shape.
fn accepted() -> Verdict {
    Verdict::new(json!({ "bridgeValidationResult": "rkaf:accepted" }))
}

fn rejected(error_class: &str, rationale: &str) -> Verdict {
    Verdict::new(json!({
        "bridgeValidationResult": "rkaf:rejected",
        "errorClass": error_class,
        "rationale": rationale,
    }))
}

pub fn evaluate(test_case: &Value, graph: &Graph) -> Result<Verdict, RuntimeError> {
    let rule_num = test_case
        .get("rkaf:contractRuleNumber")
        .and_then(Value::as_u64)
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase(
                "BridgeContractRule fixture missing rkaf:contractRuleNumber".into(),
            )
        })?;

    let consumer = consumer_mod::select_consumer(test_case, graph)?;

    match rule_num {
        1 => rule_1(graph),
        2 => rule_2(graph, consumer),
        3 => rule_3(graph),
        4 => rule_4(graph),
        5 => rule_5(graph, consumer),
        6 => rule_6(graph),
        7 => rule_7(graph),
        8 => rule_8(graph),
        9 => rule_9(graph, consumer),
        10 => rule_10(graph),
        other => Err(RuntimeError::UnsupportedContract(format!(
            "BridgeContractRule rule_num={other} (must be 1..10)"
        ))),
    }
}

// ── Rule 1 — No Rulespec-backed authority inference outside the 3 predicates ──
fn rule_1(graph: &Graph) -> Result<Verdict, RuntimeError> {
    for assertion in graph.nodes_by_type("rkaf:Assertion") {
        let Some(warrant_id) = assertion.get("rkaf:hasWarrant").and_then(Value::as_str) else {
            continue;
        };
        let Some(warrant) = graph.find(warrant_id) else {
            continue;
        };
        let is_legal_family =
            warrant.get("rkaf:warrantFamily").and_then(Value::as_str) == Some("rkaf:legal");
        if !is_legal_family {
            continue;
        }
        // Legal-family warrant must be backed by hasAuthority OR be the target
        // of a LocalAdoption OR derive authority from a chain.
        let has_authority = assertion.get("rkaf:hasAuthority").is_some();
        let has_chain = warrant.get("rkaf:derivesAuthorityFrom").is_some();
        let has_adoption = graph.nodes_by_type("rkaf:LocalAdoption").any(|la| {
            la.get("rkaf:targetAssertion").and_then(Value::as_str)
                == assertion.get("@id").and_then(Value::as_str)
        });
        if has_authority || has_chain || has_adoption {
            continue;
        }
        return Ok(rejected(
            "rkaf:UnauthorizedLegalInference",
            "Assertion carries a legal-family Warrant but has no hasAuthority chain, derivesAuthorityFrom hop, or LocalAdoption",
        ));
    }
    Ok(accepted())
}

// ── Rule 2 — usageEligibility narrow OK, broaden NOT ──
// Calls the canonical `reducer::reduce_for_scope` (NOT a re-implementation)
// so the two contracts can never silently diverge.
fn rule_2(graph: &Graph, consumer: Option<&Value>) -> Result<Verdict, RuntimeError> {
    for decl in graph.nodes_by_type("rkaf:ConsumerEffectiveDeclaration") {
        let Some(assertion_id) = decl.get("rkaf:forAssertion").and_then(Value::as_str) else {
            continue;
        };
        let Some(declared) = decl.get("rkaf:declaredEffective").and_then(Value::as_str) else {
            continue;
        };
        let Some(assertion) = graph.find(assertion_id) else {
            continue;
        };
        let scope = decl.get("rkaf:declaredScope").and_then(Value::as_str);

        let baseline = assertion
            .get("rkaf:usageEligibility")
            .and_then(Value::as_str)
            .unwrap_or("rkaf:notEligible");
        let is_stale = assertion
            .get("rkaf:consumerLifecycleState")
            .and_then(Value::as_str)
            == Some("rkaf:staleForCurrentUse");

        // Resolve applicability set (mirror reducer::evaluate's logic; one
        // pass through applicability scopes).
        let applicability_iris: Vec<&str> = match assertion.get("rkaf:hasApplicability") {
            Some(Value::String(s)) => vec![s.as_str()],
            Some(Value::Array(arr)) => arr.iter().filter_map(Value::as_str).collect(),
            _ => Vec::new(),
        };
        let mut applicability_set: Vec<&str> = Vec::new();
        for app_iri in &applicability_iris {
            if let Some(app) = graph.find(app_iri) {
                if let Some(arr) = app
                    .get("rkaf:appliesInJurisdiction")
                    .and_then(Value::as_array)
                {
                    for v in arr {
                        if let Some(s) = v.as_str() {
                            applicability_set.push(s);
                        }
                    }
                }
                if applicability_set.is_empty() {
                    applicability_set.push(app_iri);
                }
            }
        }

        let computed = reducer::reduce_for_scope(
            assertion_id,
            baseline,
            is_stale,
            &applicability_set,
            scope,
            consumer,
            graph,
        );

        if rank_above(declared, Some(&computed)) {
            return Ok(rejected(
                "rkaf:UnauthorizedBroadening",
                "ConsumerEffectiveDeclaration.declaredEffective is above the reducer output",
            ));
        }
    }
    Ok(accepted())
}

fn rank_index(level: &str) -> usize {
    let lattice = [
        "rkaf:notEligible",
        "rkaf:searchOnly",
        "rkaf:reviewQueueOnly",
        "rkaf:draftGenerationAllowed",
        "rkaf:localOperationalUse",
        "rkaf:publicationAllowed",
        "rkaf:officialUse",
    ];
    lattice.iter().position(|&x| x == level).unwrap_or(0)
}

fn rank_above(a: &str, b: Option<&str>) -> bool {
    let Some(b) = b else { return false };
    rank_index(a) > rank_index(b)
}

// ── Rule 3 — authorityKind preserved; no substitution ──
fn rule_3(graph: &Graph) -> Result<Verdict, RuntimeError> {
    for bvr in graph.nodes_by_type("rkaf:BridgeValidationResult") {
        let Some(declared_kind) = bvr.get("rkaf:chainTerminusKind").and_then(Value::as_str) else {
            continue; // no claim → no mismatch
        };
        let terminus_id = bvr.get("rkaf:chainTerminus").and_then(Value::as_str);
        let Some(terminus_node) = terminus_id.and_then(|id| graph.find(id)) else {
            return Ok(rejected(
                "rkaf:AuthorityKindSubstitution",
                "BVR.chainTerminus does not resolve to a node in the graph",
            ));
        };
        let actual_kind = terminus_node
            .get("rkaf:authorityKind")
            .and_then(Value::as_str)
            .or_else(|| {
                terminus_node
                    .get("rkaf:warrantKind")
                    .and_then(Value::as_str)
            });
        if actual_kind != Some(declared_kind) {
            return Ok(rejected(
                "rkaf:AuthorityKindSubstitution",
                "BVR.chainTerminusKind does not match the actual terminus's authorityKind/warrantKind",
            ));
        }
    }
    Ok(accepted())
}

// ── Rule 4 — declared EvaluationAnchor support ──
fn rule_4(graph: &Graph) -> Result<Verdict, RuntimeError> {
    let supported: HashSet<&str> = graph
        .nodes_by_type("rkaf:BridgeConsumerRegistration")
        .flat_map(|reg| {
            reg.get("rkaf:supportedEvaluationAnchors")
                .and_then(Value::as_array)
                .map(|arr| arr.iter().filter_map(Value::as_str).collect::<Vec<_>>())
                .unwrap_or_default()
        })
        .collect();
    for pit in graph.nodes_by_type("rkaf:PointInTimeException") {
        let Some(anchor) = pit.get("rkaf:evaluationAnchor").and_then(Value::as_str) else {
            continue;
        };
        if !supported.contains(anchor) {
            return Ok(rejected(
                "rkaf:UnsupportedEvaluationAnchor",
                "PIT carries an evaluationAnchor not in any consumer's supportedEvaluationAnchors",
            ));
        }
    }
    Ok(accepted())
}

// ── Rule 5 — cascade staleForCurrentUse transition ──
fn rule_5(graph: &Graph, consumer: Option<&Value>) -> Result<Verdict, RuntimeError> {
    for assertion in graph.nodes_by_type("rkaf:Assertion") {
        let Some(id) = assertion.get("@id").and_then(Value::as_str) else {
            continue;
        };
        if stale::should_be_stale(id, consumer, graph) {
            let actual_state = assertion
                .get("rkaf:consumerLifecycleState")
                .and_then(Value::as_str);
            if actual_state != Some("rkaf:staleForCurrentUse") {
                return Ok(rejected(
                    "rkaf:MissingStaleTransition",
                    "Assertion is affected by a LifecycleEvent (no safeAutomaticMigration supported) but consumerLifecycleState is not staleForCurrentUse",
                ));
            }
        }
    }
    Ok(accepted())
}

// ── Rule 6 — concept resolution ≠ authority ──
fn rule_6(graph: &Graph) -> Result<Verdict, RuntimeError> {
    let concept_ids: HashSet<&str> = graph
        .nodes_by_type("rkaf:RegisteredConcept")
        .chain(graph.nodes_by_type("rkaf:LocalConcept"))
        .filter_map(|c| c.get("@id").and_then(Value::as_str))
        .collect();
    for bvr in graph.nodes_by_type("rkaf:BridgeValidationResult") {
        let Some(used) = bvr.get("rkaf:usedAsAuthority").and_then(Value::as_array) else {
            continue;
        };
        for v in used {
            if let Some(s) = v.as_str() {
                if concept_ids.contains(s) {
                    return Ok(rejected(
                        "rkaf:ConceptUsedAsAuthority",
                        "BVR.usedAsAuthority cites a Concept node; concept resolution is not authority",
                    ));
                }
            }
        }
    }
    Ok(accepted())
}

// ── Rule 7 — justification chains MUST terminate ──
fn rule_7(graph: &Graph) -> Result<Verdict, RuntimeError> {
    for wp in graph.nodes_by_type("rkaf:GeneratedWorkProduct") {
        let Some(assertion_id) = wp.get("rkaf:justifiedByAssertion").and_then(Value::as_str) else {
            continue;
        };
        if chain_terminates(assertion_id, graph) {
            continue;
        }
        return Ok(rejected(
            "rkaf:UnterminatedJustificationChain",
            "Justification chain does not reach hasAuthority / derivesAuthorityFrom / LocalAdoption",
        ));
    }
    Ok(accepted())
}

fn chain_terminates(assertion_id: &str, graph: &Graph) -> bool {
    let mut visited: HashSet<String> = HashSet::new();
    let mut stack: Vec<String> = vec![assertion_id.into()];
    while let Some(current) = stack.pop() {
        if !visited.insert(current.clone()) {
            continue;
        }
        let Some(node) = graph.find(&current) else {
            continue;
        };
        // Termination conditions:
        if node.get("rkaf:hasAuthority").is_some() {
            return true;
        }
        if node.get("rkaf:derivesAuthorityFrom").is_some() {
            return true;
        }
        // LocalAdoption targeting this node terminates the chain.
        if graph
            .nodes_by_type("rkaf:LocalAdoption")
            .any(|la| la.get("rkaf:targetAssertion").and_then(Value::as_str) == Some(&current))
        {
            return true;
        }
        // Walk inward through Justification → Warrant.
        if let Some(j) = node.get("rkaf:hasJustification").and_then(Value::as_str) {
            stack.push(j.into());
        }
        if let Some(w) = node.get("rkaf:hasWarrant").and_then(Value::as_str) {
            stack.push(w.into());
        }
    }
    false
}

// ── Rule 8 — bridge-emitted attestations for consumer-detected issues ──
fn rule_8(graph: &Graph) -> Result<Verdict, RuntimeError> {
    // For each BVR with detectedIssues, check that every issue kind appearing
    // in some consumer's BridgeIssueAttestationContract.attestedIssueKinds is
    // attested via an Attestation referencing the BVR.
    for bvr in graph.nodes_by_type("rkaf:BridgeValidationResult") {
        let Some(bvr_id) = bvr.get("@id").and_then(Value::as_str) else {
            continue;
        };
        let bvr_consumer = bvr.get("rkaf:consumer").and_then(Value::as_str);
        let detected: Vec<&str> = bvr
            .get("rkaf:detectedIssues")
            .and_then(Value::as_array)
            .map(|arr| arr.iter().filter_map(Value::as_str).collect())
            .unwrap_or_default();
        if detected.is_empty() {
            continue;
        }
        // Find this consumer's attestation contract.
        let contract = graph
            .nodes_by_type("rkaf:BridgeIssueAttestationContract")
            .find(|c| c.get("rkaf:consumer").and_then(Value::as_str) == bvr_consumer);
        let Some(contract) = contract else { continue };
        let attested_kinds: HashSet<&str> = contract
            .get("rkaf:attestedIssueKinds")
            .and_then(Value::as_array)
            .map(|arr| arr.iter().filter_map(Value::as_str).collect())
            .unwrap_or_default();

        for issue in &detected {
            if !attested_kinds.contains(issue) {
                continue; // not under contract — no attestation required
            }
            // Look for any Attestation whose `targets` list contains bvr_id.
            let has_attestation = graph.nodes_by_type("rkaf:Attestation").any(|att| {
                att.get("rkaf:targets")
                    .and_then(Value::as_array)
                    .map(|arr| arr.iter().any(|v| v.as_str() == Some(bvr_id)))
                    .unwrap_or(false)
            });
            if !has_attestation {
                return Ok(rejected(
                    "rkaf:UnattestedConsumerIssue",
                    "BVR surfaces a contracted issue kind but no Attestation references the BVR",
                ));
            }
        }
    }
    Ok(accepted())
}

// ── Rule 9 — bridgeContractVersion declared; unsupported versions refused ──
fn rule_9(graph: &Graph, consumer: Option<&Value>) -> Result<Verdict, RuntimeError> {
    let Some(reg) = consumer else {
        return Ok(accepted());
    };
    let ranges: Vec<&str> = reg
        .get("rkaf:supportsRegistryVersionRange")
        .and_then(Value::as_array)
        .map(|arr| arr.iter().filter_map(Value::as_str).collect())
        .unwrap_or_default();
    for bvr in graph.nodes_by_type("rkaf:BridgeValidationResult") {
        let Some(version) = bvr
            .get("rkaf:bridgeContractVersion")
            .and_then(Value::as_str)
        else {
            continue;
        };
        let parsed = semver::Version::parse(version);
        // BVR carries a bare semver; if it doesn't parse, treat as unsupported.
        let Ok(parsed) = parsed else {
            return Ok(rejected(
                "rkaf:UnsupportedContractVersion",
                "BVR.bridgeContractVersion is not a parseable semver",
            ));
        };
        let mut any_match = false;
        for range in &ranges {
            // Skip slash-prefixed registry tags (consumer-side metadata).
            if range.contains('/') {
                continue;
            }
            if let Ok(req) = semver::VersionReq::parse(range) {
                if req.matches(&parsed) {
                    any_match = true;
                    break;
                }
            }
        }
        if !any_match {
            return Ok(rejected(
                "rkaf:UnsupportedContractVersion",
                "BVR.bridgeContractVersion not matched by any consumer.supportsRegistryVersionRange entry",
            ));
        }
    }
    Ok(accepted())
}

// ── Rule 10 — generated artifacts preserve Rulespec justification metadata ──
// Per spec §3.10: BOTH justifiedByAssertion presence AND the referenced
// assertion's chain terminates per Rule 7.
fn rule_10(graph: &Graph) -> Result<Verdict, RuntimeError> {
    for wp in graph.nodes_by_type("rkaf:GeneratedWorkProduct") {
        let Some(assertion_id) = wp.get("rkaf:justifiedByAssertion").and_then(Value::as_str) else {
            return Ok(rejected(
                "rkaf:MissingJustificationMetadata",
                "GeneratedWorkProduct lacks justifiedByAssertion",
            ));
        };
        if !chain_terminates(assertion_id, graph) {
            return Ok(rejected(
                "rkaf:UnterminatedJustificationChain",
                "GeneratedWorkProduct's justifiedByAssertion has no terminating chain per Rule 7",
            ));
        }
    }
    Ok(accepted())
}

#[cfg(test)]
mod tests {
    // Module tests are in tests/behavior_fixtures.rs — they exercise via the
    // full Runtime::evaluate path, which is the integration contract.
}
