//! Runtime dispatcher.
//!
//! Reads a `BehaviorTestCase` JSON-LD document, identifies its
//! `rkaf:behaviorContract` IRI, and routes evaluation to the matching
//! contract module. Returns a [`Verdict`] whose `output` is deep-equal-
//! comparable against the test case's `rkaf:expectedOutput`.

use serde_json::Value;

use crate::{
    bridge, cascade, concept, errors::RuntimeError, graph::Graph, pit, reducer, verdict::Verdict,
};

/// The top-level entry point for the L4 conformance runtime.
pub struct Runtime;

impl Runtime {
    /// Evaluate a single `BehaviorTestCase`. The runtime is stateless; this
    /// is an associated function for ergonomics.
    pub fn evaluate(test_case: &Value) -> Result<Verdict, RuntimeError> {
        // Verify the wrapper @type.
        match test_case.get("@type").and_then(Value::as_str) {
            Some("rkaf:BehaviorTestCase") => {}
            other => {
                return Err(RuntimeError::MalformedTestCase(format!(
                    "expected @type=rkaf:BehaviorTestCase, got {other:?}"
                )));
            }
        }

        let contract = test_case
            .get("rkaf:behaviorContract")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                RuntimeError::MalformedTestCase("missing rkaf:behaviorContract".into())
            })?;

        let input = test_case
            .get("rkaf:input")
            .ok_or_else(|| RuntimeError::MalformedTestCase("missing rkaf:input".into()))?;
        let graph = Graph::from_payload(input)?;

        match contract {
            "rkaf:CascadeClosureV1" => cascade::evaluate(test_case, &graph),
            "rkaf:UsageEligibilityReducer" => reducer::evaluate(test_case, &graph),
            "rkaf:BridgeContractRule" => bridge::evaluate(test_case, &graph),
            "rkaf:PointInTimeException" => pit::evaluate(test_case, &graph),
            "rkaf:ConceptResolutionWithConflict" => concept::evaluate(test_case, &graph),
            other => Err(RuntimeError::UnsupportedContract(other.into())),
        }
    }

    /// Run `evaluate` and compare its output to the test case's
    /// `rkaf:expectedOutput`. Returns `Ok(verdict)` on match,
    /// `Err(OutputMismatch)` otherwise.
    pub fn evaluate_and_check(test_case: &Value) -> Result<Verdict, RuntimeError> {
        let verdict = Self::evaluate(test_case)?;
        let expected = test_case
            .get("rkaf:expectedOutput")
            .cloned()
            .unwrap_or(Value::Null);
        if deep_equal(&verdict.output, &expected) {
            Ok(verdict)
        } else {
            Err(RuntimeError::OutputMismatch {
                expected,
                actual: verdict.output,
            })
        }
    }
}

/// Deep-equal comparison for JSON values.
///
/// Arrays are compared as **multisets** for the `affectedSet` case
/// (`§2.5` declares the set is unordered). To keep this primitive simple
/// for now, we treat all top-level arrays under `affectedSet` /
/// `conflictingEntries` as order-insensitive; other arrays are order-
/// sensitive. The harness can re-enter with sorted inputs if it wants
/// strict ordering later.
/// Keys EXCLUDED from output equality comparison. Centralized so the rule
/// is discoverable and testable rather than embedded in deep_equal's body.
///
/// Each entry must have a justification in spec/rkaf-behavior.md §7
/// (Expected-output format). Adding a key here changes the contract;
/// `deep_equal_skips_informational_keys` test pins the current set.
const INFORMATIONAL_OUTPUT_KEYS: &[&str] = &[
    "rationale", // §7 — informational only; never gates a verdict.
];

fn is_informational_key(key: &str) -> bool {
    INFORMATIONAL_OUTPUT_KEYS.contains(&key)
}

fn deep_equal(a: &Value, b: &Value) -> bool {
    match (a, b) {
        (Value::Object(am), Value::Object(bm)) => {
            // Per INFORMATIONAL_OUTPUT_KEYS: keys whose presence/absence
            // MUST NOT cause an OutputMismatch. The set is normative;
            // see spec/rkaf-behavior.md §7.
            let skip = is_informational_key;
            let am_keys: std::collections::HashSet<&String> =
                am.keys().filter(|k| !skip(k.as_str())).collect();
            let bm_keys: std::collections::HashSet<&String> =
                bm.keys().filter(|k| !skip(k.as_str())).collect();
            if am_keys != bm_keys {
                return false;
            }
            for k in am_keys {
                let av = am.get(k).unwrap();
                let bv = bm.get(k).unwrap();
                if k == "affectedSet" || k == "conflictingEntries" {
                    if !array_set_equal(av, bv) {
                        return false;
                    }
                } else if !deep_equal(av, bv) {
                    return false;
                }
            }
            true
        }
        (Value::Array(al), Value::Array(bl)) => {
            al.len() == bl.len() && al.iter().zip(bl).all(|(x, y)| deep_equal(x, y))
        }
        _ => a == b,
    }
}

fn array_set_equal(a: &Value, b: &Value) -> bool {
    let (Some(al), Some(bl)) = (a.as_array(), b.as_array()) else {
        return a == b;
    };
    if al.len() != bl.len() {
        return false;
    }
    let mut bl_remaining: Vec<&Value> = bl.iter().collect();
    for x in al {
        if let Some(pos) = bl_remaining.iter().position(|y| deep_equal(x, y)) {
            bl_remaining.swap_remove(pos);
        } else {
            return false;
        }
    }
    bl_remaining.is_empty()
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn malformed_test_case_rejected() {
        let bad = json!({"@type": "rkaf:NotATestCase"});
        let err = Runtime::evaluate(&bad).unwrap_err();
        match err {
            RuntimeError::MalformedTestCase(_) => {}
            other => panic!("unexpected error: {other:?}"),
        }
    }

    #[test]
    fn unsupported_contract_rejected() {
        let bad = json!({
            "@type": "rkaf:BehaviorTestCase",
            "rkaf:behaviorContract": "rkaf:WhateverNotARealContract",
            "rkaf:input": {"@graph": []}
        });
        let err = Runtime::evaluate(&bad).unwrap_err();
        match err {
            RuntimeError::UnsupportedContract(_) => {}
            other => panic!("unexpected error: {other:?}"),
        }
    }

    #[test]
    fn deep_equal_affected_set_is_order_insensitive() {
        let a = json!({"affectedSet": ["A", "W1", "W2"], "algorithm": "x"});
        let b = json!({"affectedSet": ["W2", "A", "W1"], "algorithm": "x"});
        assert!(deep_equal(&a, &b));
    }

    #[test]
    fn deep_equal_non_set_arrays_are_order_sensitive() {
        let a = json!({"chain": ["A", "B"]});
        let b = json!({"chain": ["B", "A"]});
        assert!(!deep_equal(&a, &b));
    }

    #[test]
    fn deep_equal_skips_informational_keys() {
        // Pins the INFORMATIONAL_OUTPUT_KEYS contract. Adding a key here
        // is a spec change — must update spec/rkaf-behavior.md §7 alongside.
        assert_eq!(INFORMATIONAL_OUTPUT_KEYS, &["rationale"]);
        // Behavioral pin: equality holds across presence/absence of any
        // informational key.
        for k in INFORMATIONAL_OUTPUT_KEYS {
            let with = serde_json::json!({"result": "ok", *k: "anything"});
            let without = serde_json::json!({"result": "ok"});
            assert!(
                deep_equal(&with, &without),
                "informational key {k:?} should not gate equality"
            );
        }
    }
}
