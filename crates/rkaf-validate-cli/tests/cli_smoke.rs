//! End-to-end CLI smoke tests via Cargo's bin target.
//!
//! Runs the `rkaf-validate` binary on a positive fixture (exit 0) and a
//! negative fixture (exit 1). Also exercises `--json` to verify the
//! machine-readable report.

use std::path::PathBuf;
use std::process::Command;

fn bin() -> PathBuf {
    // `env!("CARGO_BIN_EXE_<bin name>")` resolves to the built binary path.
    env!("CARGO_BIN_EXE_rkaf-validate").into()
}

fn fixture(name: &str) -> PathBuf {
    let mut p = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    p.push("../../fixtures");
    p.push(format!("{name}.jsonld"));
    p
}

#[test]
fn cli_passes_positive_fixture() {
    let out = Command::new(bin())
        .arg(fixture("warrant-legal-positive"))
        .output()
        .unwrap();
    assert!(
        out.status.success(),
        "rkaf-validate exited {:?}: stderr={}",
        out.status.code(),
        String::from_utf8_lossy(&out.stderr)
    );
}

// `ailineage-missing-approver-negative` was retired when Core §2.4 made
// `rkaf:humanApprover` optional: an unreviewed model candidate must be
// representable, so a missing approver stopped being a defect. Its
// replacement catches one that is still real — an input-context hash that
// is not a digest.
#[test]
fn cli_fails_negative_fixture_with_diagnostic() {
    let out = Command::new(bin())
        .arg(fixture("ailineage-malformed-input-context-hash-negative"))
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        stderr.contains("FAIL"),
        "stderr did not mention FAIL: {stderr}"
    );
}

// The selector contract has to reach the SHIPPED validator, not only the SHACL
// gate. `oa:TextPositionSelector` is the only class in the repo with a NUMERIC
// `x-rkaf-order`, so until it was registered the numeric branch of
// `violates_order` was unreachable and this binary returned exit 0 on a region
// whose end precedes its start.
#[test]
fn cli_fails_on_an_inverted_position_selector() {
    let out = Command::new(bin())
        .arg(fixture(
            "negatives/text-position-selector-inverted-offsets-negative",
        ))
        .output()
        .unwrap();
    assert_eq!(
        out.status.code(),
        Some(1),
        "stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(
        stderr.contains("oa:start"),
        "diagnostic did not name the inverted pair: {stderr}"
    );
}

// The same registration is what makes a missing coordinate system an L2
// failure. An offset with no declared unit is not a coordinate, and the
// required-property check is the one JSON Schema can make about it.
#[test]
fn cli_fails_on_a_position_selector_with_no_coordinate_system() {
    let out = Command::new(bin())
        .arg(fixture(
            "negatives/text-position-selector-missing-coordinate-system-negative",
        ))
        .output()
        .unwrap();
    assert_eq!(
        out.status.code(),
        Some(1),
        "stderr={}",
        String::from_utf8_lossy(&out.stderr)
    );
}

#[test]
fn cli_json_mode_emits_structured_report() {
    let out = Command::new(bin())
        .arg("--json")
        .arg(fixture("warrant-legal-positive"))
        .output()
        .unwrap();
    assert!(out.status.success());
    let stdout = String::from_utf8_lossy(&out.stdout);
    let parsed: serde_json::Value = serde_json::from_str(&stdout)
        .unwrap_or_else(|e| panic!("CLI --json output should be valid JSON: {e}\n{stdout}"));
    assert_eq!(parsed["result"], "PASS");
    assert_eq!(parsed["errors"].as_array().map(|a| a.len()), Some(0));
}

#[test]
fn cli_json_mode_emits_error_array_on_failure() {
    let out = Command::new(bin())
        .arg("--json")
        .arg(fixture("ailineage-malformed-input-context-hash-negative"))
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    let stdout = String::from_utf8_lossy(&out.stdout);
    let parsed: serde_json::Value = serde_json::from_str(&stdout).unwrap();
    assert_eq!(parsed["result"], "FAIL");
    assert!(parsed["errors"].as_array().unwrap().len() >= 1);
}
