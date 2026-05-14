//! Runtime error types.

use serde_json::Value;

#[derive(Debug, thiserror::Error)]
pub enum RuntimeError {
    #[error("parse: {0}")]
    Parse(String),

    #[error("missing node: no node with @id={0} in input graph")]
    MissingNode(String),

    #[error("unsupported behaviorContract: {0}")]
    UnsupportedContract(String),

    #[error("contract internal failure: {0}")]
    ContractInternal(String),

    #[error("output mismatch: expected {expected}, got {actual}")]
    OutputMismatch { expected: Value, actual: Value },

    #[error("malformed BehaviorTestCase: {0}")]
    MalformedTestCase(String),

    #[error("semver: {0}")]
    Semver(#[from] semver::Error),
}

impl RuntimeError {
    /// IRI tag identifying this error variant for fixture-level
    /// `rkaf:expectedRuntimeError` assertions and `rkaf-behavior-validate`
    /// CLI diagnostics. Centralized so the variant → IRI mapping has a
    /// single source of truth; previously duplicated between
    /// `crates/rkaf-runtime/tests/behavior_fixtures.rs` and
    /// `crates/rkaf-runtime-cli/src/main.rs`.
    ///
    /// The IRI strings are normative — fixtures bind to them. Pinned by
    /// `runtime_error_iri_tag_mapping` below; adding a variant requires
    /// extending both the match here and the test.
    pub fn iri_tag(&self) -> &'static str {
        match self {
            RuntimeError::Parse(_) => "rkaf:ParseError",
            RuntimeError::MissingNode(_) => "rkaf:MissingNode",
            RuntimeError::UnsupportedContract(_) => "rkaf:UnsupportedContract",
            RuntimeError::ContractInternal(_) => "rkaf:ContractInternal",
            RuntimeError::OutputMismatch { .. } => "rkaf:OutputMismatch",
            RuntimeError::MalformedTestCase(_) => "rkaf:MalformedTestCase",
            RuntimeError::Semver(_) => "rkaf:SemverError",
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn runtime_error_iri_tag_mapping() {
        // Pin the variant → IRI mapping. Fixtures bind to these strings;
        // any rename is a breaking change to the fixture contract.
        assert_eq!(
            RuntimeError::Parse("x".into()).iri_tag(),
            "rkaf:ParseError"
        );
        assert_eq!(
            RuntimeError::MissingNode("x".into()).iri_tag(),
            "rkaf:MissingNode"
        );
        assert_eq!(
            RuntimeError::UnsupportedContract("x".into()).iri_tag(),
            "rkaf:UnsupportedContract"
        );
        assert_eq!(
            RuntimeError::ContractInternal("x".into()).iri_tag(),
            "rkaf:ContractInternal"
        );
        assert_eq!(
            RuntimeError::OutputMismatch {
                expected: json!(null),
                actual: json!(null)
            }
            .iri_tag(),
            "rkaf:OutputMismatch"
        );
        assert_eq!(
            RuntimeError::MalformedTestCase("x".into()).iri_tag(),
            "rkaf:MalformedTestCase"
        );
        // Semver doesn't construct directly from a literal; use From.
        let semver_err: RuntimeError = "not-a-semver".parse::<semver::Version>().unwrap_err().into();
        assert_eq!(semver_err.iri_tag(), "rkaf:SemverError");
    }
}
