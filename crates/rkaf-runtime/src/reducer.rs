//! UsageEligibility reducer — spec/rkaf-behavior.md §1.

use serde_json::{json, Value};

use crate::{errors::RuntimeError, graph::Graph, verdict::Verdict};

/// The 7-level UsageEligibility lattice, ordered low → high.
const LATTICE: &[&str] = &[
    "rkaf:notEligible",
    "rkaf:searchOnly",
    "rkaf:reviewQueueOnly",
    "rkaf:draftGenerationAllowed",
    "rkaf:localOperationalUse",
    "rkaf:publicationAllowed",
    "rkaf:officialUse",
];

fn rank(level: &str) -> Option<usize> {
    LATTICE.iter().position(|&l| l == level)
}

fn max_on_lattice(a: &str, b: &str) -> String {
    let ra = rank(a).unwrap_or(0);
    let rb = rank(b).unwrap_or(0);
    LATTICE[ra.max(rb)].to_string()
}

fn min_on_lattice(a: &str, b: &str) -> String {
    let ra = rank(a).unwrap_or(LATTICE.len() - 1);
    let rb = rank(b).unwrap_or(LATTICE.len() - 1);
    LATTICE[ra.min(rb)].to_string()
}

pub fn evaluate(test_case: &Value, graph: &Graph) -> Result<Verdict, RuntimeError> {
    // Locate the Assertion under evaluation. By convention, fixtures carry it
    // as the first rkaf:Assertion node in the input @graph.
    let assertion = graph
        .nodes_by_type("rkaf:Assertion")
        .next()
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase(
                "UsageEligibilityReducer fixture missing an rkaf:Assertion in input".into(),
            )
        })?;
    let assertion_id = assertion
        .get("@id")
        .and_then(Value::as_str)
        .ok_or_else(|| RuntimeError::MalformedTestCase("Assertion has no @id".into()))?
        .to_string();

    let baseline = assertion
        .get("rkaf:usageEligibility")
        .and_then(Value::as_str)
        .unwrap_or("rkaf:notEligible")
        .to_string();

    let is_stale = assertion.get("rkaf:consumerLifecycleState").and_then(Value::as_str)
        == Some("rkaf:staleForCurrentUse");

    // Determine evaluation scopes.
    // Behavior fixtures MAY carry rkaf:evaluationScopes; otherwise derive from
    // LocalAdoptions targeting the assertion.
    let mut scopes: Vec<String> = Vec::new();
    if let Some(arr) = test_case.get("rkaf:evaluationScopes").and_then(Value::as_array) {
        for v in arr {
            if let Some(s) = v.as_str() {
                scopes.push(s.into());
            }
        }
    } else {
        // Default: every LocalAdoption.adoptionScope targeting this assertion,
        // plus an out-of-scope sentinel for comparison. The
        // local-broadens-in-scope fixture expects both an in-scope and
        // an out-of-scope reading; we synthesize them from the fixture.
        for la in graph.nodes_by_type("rkaf:LocalAdoption") {
            if la.get("rkaf:targetAssertion").and_then(Value::as_str) == Some(&assertion_id) {
                if let Some(s) = la.get("rkaf:adoptionScope").and_then(Value::as_str) {
                    if !scopes.contains(&s.to_string()) {
                        scopes.push(s.to_string());
                    }
                }
            }
        }
        // For multi-scope reasoning the fixture must declare scopes
        // explicitly; we don't synthesize the "other scope" — too magical.
    }

    // No scopes declared → workspace-wide reduction (no LocalAdoption).
    if scopes.is_empty() {
        let level = reduce_for_scope(&assertion_id, &baseline, is_stale, None, graph);
        return Ok(Verdict::new(json!({
            "effectiveUsageEligibility": level,
            "rationale": if is_stale {
                "lifecycle status (staleForCurrentUse) wins over baseline"
            } else {
                "baseline applied; no LocalAdoption broadening (workspace-wide reduction)"
            },
        })));
    }

    let mut by_scope = serde_json::Map::new();
    for scope in scopes {
        let level = reduce_for_scope(&assertion_id, &baseline, is_stale, Some(&scope), graph);
        by_scope.insert(scope, Value::String(level));
    }
    Ok(Verdict::new(json!({ "byScope": Value::Object(by_scope) })))
}

fn reduce_for_scope(
    assertion_id: &str,
    baseline: &str,
    is_stale: bool,
    scope: Option<&str>,
    graph: &Graph,
) -> String {
    let lifecycle_floor: String = if is_stale {
        // No PIT-honored exceptions modeled yet here (would be added by
        // composing the PIT contract). Per §1.3 invariant 4.
        "rkaf:notEligible".to_string()
    } else {
        baseline.to_string()
    };

    // Step 4 — LocalAdoption broadening (only in-scope).
    let mut effective = lifecycle_floor;
    if let Some(scope_iri) = scope {
        for la in graph.nodes_by_type("rkaf:LocalAdoption") {
            if la.get("rkaf:targetAssertion").and_then(Value::as_str) == Some(assertion_id)
                && la.get("rkaf:adoptionScope").and_then(Value::as_str) == Some(scope_iri)
                && la.get("rkaf:adoptionStatus").and_then(Value::as_str) == Some("rkaf:active")
            {
                if let Some(eligibility) = la
                    .get("rkaf:usageEligibility")
                    .and_then(Value::as_str)
                {
                    effective = max_on_lattice(&effective, eligibility);
                }
            }
        }
    }

    // Step 5 — consumer capability cap. The reducer reads it from the first
    // BridgeConsumerRegistration in the graph if present. Absent → no cap.
    if let Some(reg) = graph.nodes_by_type("rkaf:BridgeConsumerRegistration").next() {
        if let Some(cap) = reg.get("rkaf:capabilityCap").and_then(Value::as_str) {
            effective = min_on_lattice(&effective, cap);
        }
    }

    effective
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lattice_ordering() {
        assert!(rank("rkaf:officialUse") > rank("rkaf:publicationAllowed"));
        assert!(rank("rkaf:notEligible") < rank("rkaf:searchOnly"));
        assert_eq!(max_on_lattice("rkaf:officialUse", "rkaf:searchOnly"), "rkaf:officialUse");
        assert_eq!(min_on_lattice("rkaf:officialUse", "rkaf:searchOnly"), "rkaf:searchOnly");
    }
}
