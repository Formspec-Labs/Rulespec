//! Stale transition — spec/rkaf-behavior.md §5.
//!
//! Helper logic shared by bridge rule #5 and downstream queries. Decides
//! whether an Assertion should be in `staleForCurrentUse` given a
//! LifecycleEvent that affects it and the consumer's
//! `supportedAutomaticMigrations`.

use serde_json::Value;

use crate::graph::Graph;

/// True iff `lifecycle_event` declares a `safeAutomaticMigration` that the
/// consumer supports — in which case the affected assertion is exempt from
/// the stale transition.
pub fn has_supported_migration(
    lifecycle_event: &Value,
    consumer_registration: &Value,
) -> bool {
    let Some(declared) = lifecycle_event
        .get("rkaf:safeAutomaticMigration")
        .and_then(Value::as_str)
    else {
        return false;
    };
    consumer_registration
        .get("rkaf:supportedAutomaticMigrations")
        .and_then(Value::as_array)
        .map(|arr| arr.iter().filter_map(Value::as_str).any(|m| m == declared))
        .unwrap_or(false)
}

/// True iff the given assertion `@id` appears in `lifecycle_event.appliesTo`.
pub fn event_affects(lifecycle_event: &Value, assertion_id: &str) -> bool {
    match lifecycle_event.get("rkaf:appliesTo") {
        Some(Value::Array(arr)) => arr.iter().any(|v| v.as_str() == Some(assertion_id)),
        Some(Value::String(s)) => s == assertion_id,
        _ => false,
    }
}

/// Determine whether the assertion should be `staleForCurrentUse` given the
/// graph's lifecycle events and the resolved consumer registration. The
/// caller passes the consumer explicitly so the multi-BCR case is handled
/// at one site (the dispatcher), not silently inside this helper.
pub fn should_be_stale(
    assertion_id: &str,
    consumer: Option<&Value>,
    graph: &Graph,
) -> bool {
    for event in graph.nodes_by_type("rkaf:LifecycleEvent") {
        if !event_affects(event, assertion_id) {
            continue;
        }
        if let Some(reg) = consumer {
            if has_supported_migration(event, reg) {
                continue; // skip — consumer can auto-migrate
            }
        }
        return true;
    }
    false
}
