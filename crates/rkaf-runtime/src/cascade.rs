//! CascadeClosureV1 — spec/rkaf-behavior.md §2.
//!
//! Inverse-edge BFS over the 10 cascade-edge predicates from a seed `@id`.
//! The seed itself is included in `affectedSet`. Trigger edges
//! (`supersedesAssertion`, `supersedesWorkProduct`, `LifecycleEvent.appliesTo`)
//! identify the seed but are NOT traversed by the closure.

use serde_json::{json, Value};

use crate::{errors::RuntimeError, graph::Graph, verdict::Verdict};

/// The cascade-edge predicates traversed BACKWARD by the closure.
/// Per spec/rkaf-behavior.md §2.1 — these are the "dependency" edges; the
/// trigger edges (supersedesAssertion etc.) are out of scope here.
///
/// The 5 SKOS mapping edges (exactMatch / closeMatch / broadMatch /
/// narrowMatch / relatedMatch) propagate concept-lifecycle cascades
/// (§2.1 row C10): when a concept is superseded, every mapping pointing
/// at it transitively pulls in dependents.
const CASCADE_EDGES: &[&str] = &[
    "rkaf:derivedFromFragment",
    "rkaf:justifiedByAssertion",
    "rkaf:hasAuthority",
    "rkaf:derivesAuthorityFrom",
    "rkaf:implements",
    "rkaf:requiresEvidenceType",
    "rkaf:collectsEvidenceType",
    "rkaf:operationallyDependsOn",
    "rkaf:targetAssertion", // LocalAdoption → Assertion
    "rkaf:assertsObject",   // concept-typed assertions
    // §2.1 C10: 5 SKOS mapping edges for concept-lifecycle cascade.
    "skos:exactMatch",
    "skos:closeMatch",
    "skos:broadMatch",
    "skos:narrowMatch",
    "skos:relatedMatch",
    // ConceptMapping.sourceConcept / targetConcept point AT concepts;
    // inverse from a concept reaches its mappings.
    "rkaf:sourceConcept",
    "rkaf:targetConcept",
];

pub fn evaluate(test_case: &Value, graph: &Graph) -> Result<Verdict, RuntimeError> {
    let seed = test_case
        .get("rkaf:cascadeSeed")
        .and_then(Value::as_str)
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase(
                "CascadeClosureV1 fixture missing rkaf:cascadeSeed".into(),
            )
        })?;

    // Per spec §2.2: closure is scoped to active/adopted state. v0.2
    // interprets "active" as `consumerLifecycleState ∉ {retired,
    // staleForCurrentUse}`. Stale + retired nodes are EXCLUDED from
    // visitation. `as_of` from the test case is informational today —
    // the lifecycle state is the source of truth.
    let affected = closure(seed, graph);

    let mut affected_vec: Vec<Value> = affected.into_iter().map(Value::String).collect();
    affected_vec.sort_by(|a, b| a.as_str().unwrap_or("").cmp(b.as_str().unwrap_or("")));

    Ok(Verdict::new(json!({
        "affectedSet": affected_vec,
        "algorithm": "rkaf:CascadeClosureV1"
    })))
}

/// The closure algorithm itself. Public for unit testing.
pub fn closure(seed: &str, graph: &Graph) -> Vec<String> {
    use std::collections::HashSet;
    use std::collections::VecDeque;

    let mut visited: HashSet<String> = HashSet::new();
    visited.insert(seed.to_string());
    let mut queue: VecDeque<String> = VecDeque::new();
    queue.push_back(seed.to_string());

    while let Some(current) = queue.pop_front() {
        for predicate in CASCADE_EDGES {
            for incoming in graph.incoming(&current, predicate) {
                if !is_active(incoming) {
                    continue;
                }
                if let Some(id) = incoming.get("@id").and_then(Value::as_str) {
                    if visited.insert(id.to_string()) {
                        queue.push_back(id.to_string());
                    }
                }
            }
        }
    }

    visited.into_iter().collect()
}

/// Per spec §2.2 active filter. v0.2 interpretation: a node is active if
/// its `consumerLifecycleState` (when present) is NOT in the terminal /
/// stale set. Nodes without lifecycle state are treated as active by
/// default.
fn is_active(node: &Value) -> bool {
    match node.get("rkaf:consumerLifecycleState").and_then(Value::as_str) {
        None => true,
        Some(s) => !matches!(s, "rkaf:staleForCurrentUse" | "rkaf:retired" | "rkaf:withdrawn"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn supersession_fanout_reaches_work_products_not_superseder() {
        let payload = json!({
            "@graph": [
                {"@id": "A", "@type": "rkaf:Assertion"},
                {"@id": "B", "@type": "rkaf:Assertion", "rkaf:supersedesAssertion": "A"},
                {"@id": "W1", "@type": "rkaf:GeneratedWorkProduct", "rkaf:justifiedByAssertion": "A"},
                {"@id": "W2", "@type": "rkaf:GeneratedWorkProduct", "rkaf:justifiedByAssertion": "A"}
            ]
        });
        let g = Graph::from_payload(&payload).unwrap();
        let mut affected = closure("A", &g);
        affected.sort();
        assert_eq!(affected, vec!["A", "W1", "W2"]);
    }

    #[test]
    fn cycle_safe_via_visited_set() {
        let payload = json!({
            "@graph": [
                {"@id": "X", "@type": "rkaf:Assertion", "rkaf:operationallyDependsOn": "X"}
            ]
        });
        let g = Graph::from_payload(&payload).unwrap();
        let affected = closure("X", &g);
        assert_eq!(affected, vec!["X".to_string()]);
    }
}
