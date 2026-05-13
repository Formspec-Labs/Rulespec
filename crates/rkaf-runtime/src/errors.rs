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
