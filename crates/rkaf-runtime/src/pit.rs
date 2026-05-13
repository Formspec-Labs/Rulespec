//! PointInTimeException — spec/rkaf-behavior.md §4.

use serde_json::Value;

use crate::{errors::RuntimeError, graph::Graph, verdict::Verdict};

pub fn evaluate(_test_case: &Value, graph: &Graph) -> Result<Verdict, RuntimeError> {
    // Locate the Assertion, PIT exception, and consumer registration.
    let assertion = graph
        .nodes_by_type("rkaf:Assertion")
        .next()
        .ok_or_else(|| RuntimeError::MalformedTestCase("PIT fixture missing Assertion".into()))?;
    let assertion_id = assertion
        .get("@id")
        .and_then(Value::as_str)
        .ok_or_else(|| RuntimeError::MalformedTestCase("Assertion has no @id".into()))?
        .to_string();

    let exception = graph
        .nodes_by_type("rkaf:PointInTimeException")
        .next()
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase("PIT fixture missing PointInTimeException".into())
        })?;

    let registration = graph
        .nodes_by_type("rkaf:BridgeConsumerRegistration")
        .next()
        .ok_or_else(|| {
            RuntimeError::MalformedTestCase("PIT fixture missing BridgeConsumerRegistration".into())
        })?;

    let retains = exception
        .get("rkaf:retainsAssertion")
        .and_then(Value::as_str);
    let anchor = exception
        .get("rkaf:evaluationAnchor")
        .and_then(Value::as_str)
        .unwrap_or("");

    let supported_anchors: Vec<&str> = registration
        .get("rkaf:supportedEvaluationAnchors")
        .and_then(Value::as_array)
        .map(|arr| arr.iter().filter_map(Value::as_str).collect())
        .unwrap_or_default();

    // Spec §4: if the anchor is not supported, the consumer MUST refuse
    // (not silently degrade). Return an error-shaped verdict.
    let retains_this = retains == Some(assertion_id.as_str());
    if retains_this && !supported_anchors.contains(&anchor) {
        return Ok(Verdict::new(serde_json::json!({
            "errorClass": "rkaf:UnsupportedEvaluationAnchor",
            "rationale": format!("PIT anchor {anchor} not in consumer's supportedEvaluationAnchors"),
        })));
    }

    let pit_applies = retains_this && supported_anchors.contains(&anchor);

    let lifecycle_state = assertion
        .get("rkaf:consumerLifecycleState")
        .and_then(Value::as_str)
        .unwrap_or("rkaf:operational");

    // Anchor name = strip "rkaf:" prefix per spec §7 example shape.
    let anchor_name = anchor.strip_prefix("rkaf:").unwrap_or(anchor);
    let key_for_anchor = format!("{assertion_id}.effectiveStateForAnchor:{anchor_name}");
    let key_for_current = format!("{assertion_id}.effectiveStateForCurrentUse");

    let mut output = serde_json::Map::new();
    if pit_applies {
        output.insert(key_for_anchor, Value::String("rkaf:retainedForPointInTime".into()));
    } else {
        output.insert(key_for_anchor, Value::String(lifecycle_state.into()));
    }
    output.insert(key_for_current, Value::String(lifecycle_state.into()));

    Ok(Verdict::new(Value::Object(output)))
}
