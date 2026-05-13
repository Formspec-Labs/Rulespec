//! Integration test: every fixture in `fixtures/behavior/` runs through
//! `Runtime::evaluate_and_check` and MUST match its declared
//! `rkaf:expectedOutput`. This is the L4 conformance gate.

use rkaf_runtime::{Runtime, RuntimeError};
use serde_json::Value;
use std::fs;
use std::path::PathBuf;

fn behavior_dir() -> PathBuf {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    p.push("../../fixtures/behavior");
    p
}

fn load(name: &str) -> Value {
    let mut p = behavior_dir();
    p.push(format!("{name}.jsonld"));
    let bytes = fs::read(&p).unwrap_or_else(|e| panic!("read {}: {e}", p.display()));
    serde_json::from_slice(&bytes).expect("parse jsonld")
}

fn assert_passes(name: &str) {
    let tc = load(name);
    match Runtime::evaluate_and_check(&tc) {
        Ok(_) => {}
        Err(RuntimeError::OutputMismatch { expected, actual }) => {
            panic!(
                "fixture {name} OutputMismatch:\n  expected: {}\n  actual:   {}",
                serde_json::to_string_pretty(&expected).unwrap(),
                serde_json::to_string_pretty(&actual).unwrap()
            );
        }
        Err(other) => panic!("fixture {name} runtime error: {other}"),
    }
}

// ─── CascadeClosureV1 ───────────────────────────────────────────────────

#[test]
fn cascade_closure_supersession_fanout() {
    assert_passes("cascade-closure-supersession-fanout");
}

// ─── UsageEligibility reducer ──────────────────────────────────────────

#[test]
fn usage_eligibility_reducer_stale_narrows() {
    assert_passes("usage-eligibility-reducer-stale-narrows");
}

#[test]
fn usage_eligibility_reducer_local_broadens_in_scope() {
    assert_passes("usage-eligibility-reducer-local-broadens-in-scope");
}

// ─── PointInTimeException ──────────────────────────────────────────────

#[test]
fn point_in_time_exception_honored() {
    assert_passes("point-in-time-exception-honored");
}

// ─── ConceptResolutionWithConflict ─────────────────────────────────────

#[test]
fn concept_resolution_mapping_conflict() {
    assert_passes("concept-resolution-mapping-conflict");
}

// ─── Bridge contract rules — all 10 ────────────────────────────────────

#[test] fn bridge_rule_1_positive() { assert_passes("bridge-rule-1-legal-with-authority-positive"); }
#[test] fn bridge_rule_1_negative() { assert_passes("bridge-rule-1-legal-without-authority-negative"); }
#[test] fn bridge_rule_2_positive() { assert_passes("bridge-rule-2-declared-equals-reducer-positive"); }
#[test] fn bridge_rule_2_negative() { assert_passes("bridge-rule-2-declared-broadens-without-adoption-negative"); }
#[test] fn bridge_rule_3_positive() { assert_passes("bridge-rule-3-chain-terminus-kind-matches-positive"); }
#[test] fn bridge_rule_3_negative() { assert_passes("bridge-rule-3-chain-terminus-kind-mismatch-negative"); }
#[test] fn bridge_rule_4_positive() { assert_passes("bridge-rule-4-supported-anchor-positive"); }
#[test] fn bridge_rule_4_negative() { assert_passes("bridge-rule-4-unsupported-anchor-negative"); }
#[test] fn bridge_rule_5_positive() { assert_passes("bridge-rule-5-stale-transition-set-positive"); }
#[test] fn bridge_rule_5_negative() { assert_passes("bridge-rule-5-stale-not-transitioned-negative"); }
#[test] fn bridge_rule_6_positive() { assert_passes("bridge-rule-6-no-concept-in-authority-positive"); }
#[test] fn bridge_rule_6_negative() { assert_passes("bridge-rule-6-concept-in-authority-negative"); }
#[test] fn bridge_rule_7_negative() { assert_passes("bridge-rule-7-justification-orphan"); }
#[test] fn bridge_rule_8_positive() { assert_passes("bridge-rule-8-issue-with-attestation-positive"); }
#[test] fn bridge_rule_8_negative() { assert_passes("bridge-rule-8-issue-without-attestation-negative"); }
#[test] fn bridge_rule_9_positive() { assert_passes("bridge-rule-9-version-in-range-positive"); }
#[test] fn bridge_rule_9_negative() { assert_passes("bridge-rule-9-version-out-of-range-negative"); }
#[test] fn bridge_rule_10_positive() { assert_passes("bridge-rule-10-gwp-with-terminating-justification-positive"); }
#[test] fn bridge_rule_10_negative() { assert_passes("bridge-rule-10-gwp-missing-justification-negative"); }
