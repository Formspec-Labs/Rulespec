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
    p.push("../../fixtures/v0.2");
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

#[test]
fn cli_fails_negative_fixture_with_diagnostic() {
    let out = Command::new(bin())
        .arg(fixture("ailineage-missing-approver-negative"))
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&out.stderr);
    assert!(stderr.contains("FAIL"), "stderr did not mention FAIL: {stderr}");
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
        .arg(fixture("ailineage-missing-approver-negative"))
        .output()
        .unwrap();
    assert_eq!(out.status.code(), Some(1));
    let stdout = String::from_utf8_lossy(&out.stdout);
    let parsed: serde_json::Value = serde_json::from_str(&stdout).unwrap();
    assert_eq!(parsed["result"], "FAIL");
    assert!(parsed["errors"].as_array().unwrap().len() >= 1);
}
