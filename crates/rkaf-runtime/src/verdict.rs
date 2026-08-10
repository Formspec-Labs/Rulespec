//! Verdict — the unified output type returned by every contract module.
//!
//! Every contract emits a `serde_json::Value` whose shape matches the
//! per-contract format spec in `spec/rkaf-behavior.md` §7. The runtime
//! compares this value deep-equally against the fixture's
//! `rkaf:expectedOutput`; the harness then decides pass/fail.

use serde_json::Value;

/// A single contract's computed output, alongside any diagnostic notes the
/// contract module wants to surface.
#[derive(Debug, Clone)]
pub struct Verdict {
    /// JSON value matching one of the §7 output shapes.
    pub output: Value,
    /// Optional free-form rationale (mirrors the v0.1 §5.2
    /// `effectiveUsageEligibilityRationale` discipline).
    pub rationale: Option<String>,
}

impl Verdict {
    pub fn new(output: Value) -> Self {
        Self {
            output,
            rationale: None,
        }
    }
}
