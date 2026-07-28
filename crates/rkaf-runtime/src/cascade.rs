//! CascadeClosureV1 — spec/rkaf-behavior.md §2.
//!
//! Inverse-edge BFS over the 10 cascade-edge predicates from a seed `@id`.
//! The seed itself is included in `affectedSet`. Trigger edges
//! (`supersedesAssertion`, `supersedesWorkProduct`, `LifecycleEvent.appliesTo`)
//! identify the seed but are NOT traversed by the closure.

use chrono::{DateTime, FixedOffset};
use serde_json::{json, Value};

use crate::{errors::RuntimeError, graph::Graph, verdict::Verdict};

/// Parse an RFC-3339 timestamp into a timezone-aware `DateTime`. We use
/// the timezone-preserving parser (`parse_from_rfc3339`) so semantic
/// comparison works across any RFC-3339 offset spelling, not just
/// `Z`-suffixed UTC.
fn parse_rfc3339(s: &str) -> Result<DateTime<FixedOffset>, chrono::ParseError> {
    DateTime::parse_from_rfc3339(s)
}

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
    // ConceptMapping uses the canonical RelationshipAssertion proposition;
    // inverse from either endpoint reaches the mapping.
    "rkaf:assertsSubject",
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

    // Per spec §2.2: closure is scoped to active/adopted state. Two
    // exclusions apply:
    //   (a) consumerLifecycleState ∈ {staleForCurrentUse, retired,
    //       withdrawn} excludes the node.
    //   (b) If the fixture carries `rkaf:cascadeAsOf` (an xsd:dateTime),
    //       nodes whose attached EffectivePeriod does not contain that
    //       timestamp are excluded too.
    let as_of_raw = test_case.get("rkaf:cascadeAsOf").and_then(Value::as_str);
    let as_of = match as_of_raw {
        Some(s) => Some(parse_rfc3339(s).map_err(|e| {
            RuntimeError::MalformedTestCase(format!(
                "rkaf:cascadeAsOf value {s:?} is not valid RFC-3339: {e}"
            ))
        })?),
        None => None,
    };
    let affected = closure(seed, as_of.as_ref(), graph)?;

    let mut affected_vec: Vec<Value> = affected.into_iter().map(Value::String).collect();
    affected_vec.sort_by(|a, b| a.as_str().unwrap_or("").cmp(b.as_str().unwrap_or("")));

    Ok(Verdict::new(json!({
        "affectedSet": affected_vec,
        "algorithm": "rkaf:CascadeClosureV1"
    })))
}

/// The closure algorithm itself. Public for unit testing.
///
/// Returns `Err` if any node's EffectivePeriod carries an unparseable
/// `xsd:dateTime`; the runtime refuses to silently include or exclude a
/// node whose temporal scope it cannot evaluate.
pub fn closure(
    seed: &str,
    as_of: Option<&DateTime<FixedOffset>>,
    graph: &Graph,
) -> Result<Vec<String>, RuntimeError> {
    use std::collections::HashSet;
    use std::collections::VecDeque;

    let mut visited: HashSet<String> = HashSet::new();
    visited.insert(seed.to_string());
    let mut queue: VecDeque<String> = VecDeque::new();
    queue.push_back(seed.to_string());

    while let Some(current) = queue.pop_front() {
        for predicate in CASCADE_EDGES {
            for incoming in graph.incoming(&current, predicate) {
                if !is_active(incoming, as_of, graph)? {
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

    Ok(visited.into_iter().collect())
}

/// Per spec §2.2 active filter. Two exclusions:
///   (a) `consumerLifecycleState ∈ {staleForCurrentUse, retired,
///       withdrawn}` — terminal / stale.
///   (b) When `as_of` is provided, the node's attached EffectivePeriod
///       (via `rkaf:hasEffectivePeriod` → EffectivePeriod with
///       effectivePeriodStart/effectivePeriodEnd) must contain the
///       `as_of` instant. Comparison is semantic — `as_of`,
///       `effectivePeriodStart`, and `effectivePeriodEnd` are parsed as
///       timezone-aware RFC-3339 and compared as instants, so any valid
///       offset spelling (Z, +00:00, +05:00, …) works without lex
///       foot-guns.
fn is_active(
    node: &Value,
    as_of: Option<&DateTime<FixedOffset>>,
    graph: &Graph,
) -> Result<bool, RuntimeError> {
    // (a) lifecycle-state exclusion
    if let Some(s) = node
        .get("rkaf:consumerLifecycleState")
        .and_then(Value::as_str)
    {
        if matches!(
            s,
            "rkaf:staleForCurrentUse" | "rkaf:retired" | "rkaf:withdrawn"
        ) {
            return Ok(false);
        }
    }
    // (b) effective-period exclusion (only when as_of is set)
    let Some(as_of_ts) = as_of else {
        return Ok(true);
    };
    let Some(period_iri) = node.get("rkaf:hasEffectivePeriod").and_then(Value::as_str) else {
        // No period declared → active by default.
        return Ok(true);
    };
    let node_id = node
        .get("@id")
        .and_then(Value::as_str)
        .unwrap_or("<unknown>");
    // Dangling-IRI exclusion: a node declares a temporal scope but the
    // referenced EffectivePeriod is not in the graph. Mirror the
    // malformed-timestamp branch below — error loudly rather than silently
    // returning Ok(true). Silent acceptance would let typos and missing
    // nodes pass the as_of filter unchecked, which is exactly the
    // strictness gap Plan 7c began closing for timestamp parsing.
    let Some(period) = graph.find(period_iri) else {
        return Err(RuntimeError::MalformedTestCase(format!(
            "node {node_id} declares rkaf:hasEffectivePeriod {period_iri:?} but no such EffectivePeriod node exists in the graph"
        )));
    };
    let parse_field = |field: &str, raw: &str| -> Result<DateTime<FixedOffset>, RuntimeError> {
        parse_rfc3339(raw).map_err(|e| {
            RuntimeError::MalformedTestCase(format!(
                "node {node_id} EffectivePeriod.{field} value {raw:?} is not valid RFC-3339: {e}"
            ))
        })
    };
    if let Some(s) = period
        .get("rkaf:effectivePeriodStart")
        .and_then(Value::as_str)
    {
        let start = parse_field("effectivePeriodStart", s)?;
        if *as_of_ts < start {
            return Ok(false);
        }
    }
    if let Some(e) = period
        .get("rkaf:effectivePeriodEnd")
        .and_then(Value::as_str)
    {
        let end = parse_field("effectivePeriodEnd", e)?;
        if *as_of_ts > end {
            return Ok(false);
        }
    }
    Ok(true)
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
        let mut affected = closure("A", None, &g).unwrap();
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
        let affected = closure("X", None, &g).unwrap();
        assert_eq!(affected, vec!["X".to_string()]);
    }

    #[test]
    fn as_of_semantic_compare_handles_non_z_offsets() {
        // EffectivePeriod uses -05:00; cascadeAsOf uses Z. Lex compare
        // would mis-order these; semantic compare must treat them as
        // equivalent instants.
        let payload = json!({
            "@graph": [
                {"@id": "A", "@type": "rkaf:Assertion"},
                {
                    "@id": "W",
                    "@type": "rkaf:GeneratedWorkProduct",
                    "rkaf:justifiedByAssertion": "A",
                    "rkaf:hasEffectivePeriod": "ep1"
                },
                {
                    "@id": "ep1",
                    "@type": "rkaf:EffectivePeriod",
                    "rkaf:effectivePeriodStart": "2026-01-01T00:00:00-05:00",
                    "rkaf:effectivePeriodEnd": "2026-12-31T23:59:59-05:00"
                }
            ]
        });
        let g = Graph::from_payload(&payload).unwrap();
        // 2026-06-01T05:00:00Z == 2026-06-01T00:00:00-05:00 — inside range.
        let as_of = parse_rfc3339("2026-06-01T05:00:00Z").unwrap();
        let mut affected = closure("A", Some(&as_of), &g).unwrap();
        affected.sort();
        assert_eq!(affected, vec!["A", "W"]);
    }

    #[test]
    fn as_of_outside_period_excludes_node() {
        let payload = json!({
            "@graph": [
                {"@id": "A", "@type": "rkaf:Assertion"},
                {
                    "@id": "W",
                    "@type": "rkaf:GeneratedWorkProduct",
                    "rkaf:justifiedByAssertion": "A",
                    "rkaf:hasEffectivePeriod": "ep1"
                },
                {
                    "@id": "ep1",
                    "@type": "rkaf:EffectivePeriod",
                    "rkaf:effectivePeriodStart": "2024-01-01T00:00:00Z",
                    "rkaf:effectivePeriodEnd": "2024-12-31T23:59:59Z"
                }
            ]
        });
        let g = Graph::from_payload(&payload).unwrap();
        let as_of = parse_rfc3339("2026-06-01T00:00:00Z").unwrap();
        let affected = closure("A", Some(&as_of), &g).unwrap();
        assert_eq!(affected, vec!["A".to_string()]);
    }

    #[test]
    fn malformed_effective_period_errors_loudly() {
        let payload = json!({
            "@graph": [
                {"@id": "A", "@type": "rkaf:Assertion"},
                {
                    "@id": "W",
                    "@type": "rkaf:GeneratedWorkProduct",
                    "rkaf:justifiedByAssertion": "A",
                    "rkaf:hasEffectivePeriod": "ep1"
                },
                {
                    "@id": "ep1",
                    "@type": "rkaf:EffectivePeriod",
                    "rkaf:effectivePeriodStart": "not-a-date"
                }
            ]
        });
        let g = Graph::from_payload(&payload).unwrap();
        let as_of = parse_rfc3339("2026-06-01T00:00:00Z").unwrap();
        let err = closure("A", Some(&as_of), &g).unwrap_err();
        match err {
            RuntimeError::MalformedTestCase(msg) => {
                assert!(msg.contains("effectivePeriodStart"), "msg={msg}");
            }
            other => panic!("unexpected error: {other:?}"),
        }
    }

    #[test]
    fn dangling_effective_period_iri_errors_loudly() {
        // Strictness parity with malformed_effective_period_errors_loudly:
        // a node declaring hasEffectivePeriod that points at a missing
        // node MUST yield MalformedTestCase rather than silently passing
        // the as_of filter. Closes Plan 7c follow-up FINDING 6 (cascade
        // asymmetry).
        let payload = json!({
            "@graph": [
                {"@id": "A", "@type": "rkaf:Assertion"},
                {
                    "@id": "W",
                    "@type": "rkaf:GeneratedWorkProduct",
                    "rkaf:justifiedByAssertion": "A",
                    "rkaf:hasEffectivePeriod": "ep-missing"
                }
                // No EffectivePeriod node with @id "ep-missing" exists.
            ]
        });
        let g = Graph::from_payload(&payload).unwrap();
        let as_of = parse_rfc3339("2026-06-01T00:00:00Z").unwrap();
        let err = closure("A", Some(&as_of), &g).unwrap_err();
        match err {
            RuntimeError::MalformedTestCase(msg) => {
                assert!(
                    msg.contains("ep-missing") && msg.contains("hasEffectivePeriod"),
                    "expected dangling-IRI error, got: {msg}"
                );
            }
            other => panic!("unexpected error: {other:?}"),
        }
    }
}
