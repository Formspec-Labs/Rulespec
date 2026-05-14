//! Temporal-bounds helpers shared across L4 contracts.
//!
//! Plan 7e.1 — extracted from `bridge.rs::rule_8` so any contract that needs
//! "is this Attestation in force at time T?" can call the same canonical
//! function and stay in lock-step. Strictness posture mirrors
//! `cascade::is_active`: dangling `rkaf:hasEffectivePeriod` IRIs and
//! malformed `xsd:dateTime` literals propagate as `MalformedTestCase`
//! rather than silently passing.

use chrono::{DateTime, FixedOffset};
use serde_json::Value;

use crate::{errors::RuntimeError, graph::Graph};

/// True iff `attestation` is effective at `time`, per Plan 7d semantics:
///   * `rkaf:revokedAt` is absent OR strictly after `time`, AND
///   * `rkaf:hasEffectivePeriod` is absent OR its EffectivePeriod contains
///     `time` (start ≤ time ≤ end, where each endpoint defaults to ±∞).
///
/// Errors:
///   * `MalformedTestCase` if `revokedAt`, `effectivePeriodStart`, or
///     `effectivePeriodEnd` is not parseable RFC-3339.
///   * `MalformedTestCase` if `hasEffectivePeriod` is set but the referenced
///     EffectivePeriod node is not in the graph.
pub fn effective_at(
    attestation: &Value,
    time: &DateTime<FixedOffset>,
    graph: &Graph,
) -> Result<bool, RuntimeError> {
    let att_id = attestation
        .get("@id")
        .and_then(Value::as_str)
        .unwrap_or("<unknown>");
    // revokedAt — if present and <= time, attestation is no longer effective.
    if let Some(raw) = attestation.get("rkaf:revokedAt").and_then(Value::as_str) {
        let revoked = DateTime::parse_from_rfc3339(raw).map_err(|e| {
            RuntimeError::MalformedTestCase(format!(
                "Attestation {att_id} rkaf:revokedAt value {raw:?} is not valid RFC-3339: {e}"
            ))
        })?;
        if revoked <= *time {
            return Ok(false);
        }
    }
    // hasEffectivePeriod — if present, the period MUST contain time.
    let Some(period_iri) = attestation
        .get("rkaf:hasEffectivePeriod")
        .and_then(Value::as_str)
    else {
        return Ok(true);
    };
    let Some(period) = graph.find(period_iri) else {
        return Err(RuntimeError::MalformedTestCase(format!(
            "Attestation {att_id} declares rkaf:hasEffectivePeriod {period_iri:?} but no such EffectivePeriod node exists in the graph"
        )));
    };
    let parse_field = |field: &str, raw: &str| -> Result<DateTime<FixedOffset>, RuntimeError> {
        DateTime::parse_from_rfc3339(raw).map_err(|e| {
            RuntimeError::MalformedTestCase(format!(
                "Attestation {att_id} EffectivePeriod.{field} value {raw:?} is not valid RFC-3339: {e}"
            ))
        })
    };
    if let Some(s) = period
        .get("rkaf:effectivePeriodStart")
        .and_then(Value::as_str)
    {
        let start = parse_field("effectivePeriodStart", s)?;
        if *time < start {
            return Ok(false);
        }
    }
    if let Some(e) = period
        .get("rkaf:effectivePeriodEnd")
        .and_then(Value::as_str)
    {
        let end = parse_field("effectivePeriodEnd", e)?;
        if *time > end {
            return Ok(false);
        }
    }
    Ok(true)
}

/// All `rkaf:Attestation` nodes in `graph` effective at `time`, per
/// [`effective_at`]. Errors propagate from the first malformed/dangling
/// node encountered — strict, not best-effort — matching
/// `cascade::is_active` posture.
pub fn effective_attestations_at<'a>(
    graph: &'a Graph,
    time: &DateTime<FixedOffset>,
) -> Result<Vec<&'a Value>, RuntimeError> {
    let mut out = Vec::new();
    for att in graph.nodes_by_type("rkaf:Attestation") {
        if effective_at(att, time, graph)? {
            out.push(att);
        }
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn parse(s: &str) -> DateTime<FixedOffset> {
        DateTime::parse_from_rfc3339(s).expect("parse rfc3339")
    }

    #[test]
    fn effective_at_no_constraints_returns_true() {
        let att = json!({"@id": "a", "@type": "rkaf:Attestation"});
        let payload = json!({"@graph": [att.clone()]});
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        assert!(effective_at(&att, &t, &g).unwrap());
    }

    #[test]
    fn effective_at_revoked_before_time_is_false() {
        let att = json!({
            "@id": "a",
            "@type": "rkaf:Attestation",
            "rkaf:revokedAt": "2026-03-01T00:00:00Z"
        });
        let payload = json!({"@graph": [att.clone()]});
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        assert!(!effective_at(&att, &t, &g).unwrap());
    }

    #[test]
    fn effective_at_revoked_after_time_is_true() {
        let att = json!({
            "@id": "a",
            "@type": "rkaf:Attestation",
            "rkaf:revokedAt": "2026-09-01T00:00:00Z"
        });
        let payload = json!({"@graph": [att.clone()]});
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        assert!(effective_at(&att, &t, &g).unwrap());
    }

    #[test]
    fn effective_at_period_contains_time() {
        let att = json!({
            "@id": "a",
            "@type": "rkaf:Attestation",
            "rkaf:hasEffectivePeriod": "ep1"
        });
        let ep = json!({
            "@id": "ep1",
            "@type": "rkaf:EffectivePeriod",
            "rkaf:effectivePeriodStart": "2026-01-01T00:00:00Z",
            "rkaf:effectivePeriodEnd": "2026-12-31T23:59:59Z"
        });
        let payload = json!({"@graph": [att.clone(), ep]});
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        assert!(effective_at(&att, &t, &g).unwrap());
    }

    #[test]
    fn effective_at_period_excludes_time() {
        let att = json!({
            "@id": "a",
            "@type": "rkaf:Attestation",
            "rkaf:hasEffectivePeriod": "ep1"
        });
        let ep = json!({
            "@id": "ep1",
            "@type": "rkaf:EffectivePeriod",
            "rkaf:effectivePeriodStart": "2024-01-01T00:00:00Z",
            "rkaf:effectivePeriodEnd": "2024-12-31T23:59:59Z"
        });
        let payload = json!({"@graph": [att.clone(), ep]});
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        assert!(!effective_at(&att, &t, &g).unwrap());
    }

    #[test]
    fn effective_at_dangling_period_iri_errors_loudly() {
        let att = json!({
            "@id": "a",
            "@type": "rkaf:Attestation",
            "rkaf:hasEffectivePeriod": "ep-missing"
        });
        let payload = json!({"@graph": [att.clone()]});
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        match effective_at(&att, &t, &g).unwrap_err() {
            RuntimeError::MalformedTestCase(msg) => {
                assert!(
                    msg.contains("ep-missing") && msg.contains("hasEffectivePeriod"),
                    "expected dangling-IRI error, got: {msg}"
                );
            }
            other => panic!("unexpected error: {other:?}"),
        }
    }

    #[test]
    fn effective_at_malformed_revoked_at_errors_loudly() {
        let att = json!({
            "@id": "a",
            "@type": "rkaf:Attestation",
            "rkaf:revokedAt": "not-a-date"
        });
        let payload = json!({"@graph": [att.clone()]});
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        match effective_at(&att, &t, &g).unwrap_err() {
            RuntimeError::MalformedTestCase(msg) => {
                assert!(msg.contains("revokedAt"), "msg={msg}");
            }
            other => panic!("unexpected error: {other:?}"),
        }
    }

    #[test]
    fn effective_attestations_at_empty_graph_returns_empty() {
        let payload = json!({"@graph": []});
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        assert!(effective_attestations_at(&g, &t).unwrap().is_empty());
    }

    #[test]
    fn effective_attestations_at_mix_returns_only_effective() {
        let payload = json!({
            "@graph": [
                // Effective: no constraints.
                {"@id": "att-active", "@type": "rkaf:Attestation"},
                // Revoked before time: NOT effective.
                {
                    "@id": "att-revoked",
                    "@type": "rkaf:Attestation",
                    "rkaf:revokedAt": "2026-03-01T00:00:00Z"
                },
                // Out of period: NOT effective.
                {
                    "@id": "att-out-of-period",
                    "@type": "rkaf:Attestation",
                    "rkaf:hasEffectivePeriod": "ep-old"
                },
                {
                    "@id": "ep-old",
                    "@type": "rkaf:EffectivePeriod",
                    "rkaf:effectivePeriodStart": "2024-01-01T00:00:00Z",
                    "rkaf:effectivePeriodEnd": "2024-12-31T23:59:59Z"
                },
                // In period: effective.
                {
                    "@id": "att-in-period",
                    "@type": "rkaf:Attestation",
                    "rkaf:hasEffectivePeriod": "ep-current"
                },
                {
                    "@id": "ep-current",
                    "@type": "rkaf:EffectivePeriod",
                    "rkaf:effectivePeriodStart": "2026-01-01T00:00:00Z",
                    "rkaf:effectivePeriodEnd": "2026-12-31T23:59:59Z"
                }
            ]
        });
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        let mut ids: Vec<&str> = effective_attestations_at(&g, &t)
            .unwrap()
            .into_iter()
            .filter_map(|n| n.get("@id").and_then(Value::as_str))
            .collect();
        ids.sort();
        assert_eq!(ids, vec!["att-active", "att-in-period"]);
    }

    #[test]
    fn effective_attestations_at_malformed_propagates() {
        let payload = json!({
            "@graph": [
                {
                    "@id": "att-bad",
                    "@type": "rkaf:Attestation",
                    "rkaf:revokedAt": "not-a-date"
                }
            ]
        });
        let g = Graph::from_payload(&payload).unwrap();
        let t = parse("2026-06-01T00:00:00Z");
        match effective_attestations_at(&g, &t).unwrap_err() {
            RuntimeError::MalformedTestCase(msg) => {
                assert!(msg.contains("revokedAt"), "msg={msg}");
            }
            other => panic!("unexpected error: {other:?}"),
        }
    }
}
