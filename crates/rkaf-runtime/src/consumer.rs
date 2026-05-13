//! Consumer-selection helper.
//!
//! Several behavior contracts (stale transition, reducer step 5, PIT anchor
//! check, bridge rules 4 and 9) read "the consumer's" capabilities from a
//! `rkaf:BridgeConsumerRegistration` node. v0.2 has a single-consumer
//! assumption — if a graph carries more than one BCR, the test case MUST
//! disambiguate via `rkaf:evaluationConsumer` carrying the BCR's `@id`.
//!
//! This helper is the single source of truth for "which BCR applies."

use serde_json::Value;

use crate::{errors::RuntimeError, graph::Graph};

/// Select the BridgeConsumerRegistration to read capabilities from.
///
/// Resolution:
/// - 0 BCRs in the graph → `Ok(None)` (contracts treat as "no consumer
///   capabilities declared"; e.g., reducer step 5 applies no cap).
/// - 1 BCR → `Ok(Some(&bcr))` unambiguously.
/// - 2+ BCRs → require `test_case.rkaf:evaluationConsumer == bcr.@id`;
///   pick that one. If no such field, error.
pub fn select_consumer<'a>(
    test_case: &Value,
    graph: &'a Graph<'a>,
) -> Result<Option<&'a Value>, RuntimeError> {
    let bcrs: Vec<&Value> = graph.nodes_by_type("rkaf:BridgeConsumerRegistration").collect();
    match bcrs.len() {
        0 => Ok(None),
        1 => Ok(Some(bcrs[0])),
        _ => {
            let explicit = test_case
                .get("rkaf:evaluationConsumer")
                .and_then(Value::as_str);
            let Some(target_id) = explicit else {
                return Err(RuntimeError::MalformedTestCase(format!(
                    "graph carries {} BridgeConsumerRegistration nodes; the BehaviorTestCase MUST set rkaf:evaluationConsumer to the @id of the BCR to use",
                    bcrs.len()
                )));
            };
            bcrs.into_iter()
                .find(|b| b.get("@id").and_then(Value::as_str) == Some(target_id))
                .map(Some)
                .ok_or_else(|| {
                    RuntimeError::MalformedTestCase(format!(
                        "rkaf:evaluationConsumer={target_id} does not resolve to a BCR in the graph"
                    ))
                })
        }
    }
}
