//! Rulespec Layer 4 — Projector trait per source spec §8.1.
//!
//! Every projector implements five operations: Attach, Extract, Validate,
//! RoundTrip (default), Derive. Round-trip parity (Attach → Extract is the
//! identity transform) is the release-gating invariant.

use async_trait::async_trait;
use serde_json::Value;

#[derive(Debug, thiserror::Error)]
pub enum ProjectorError {
    #[error("attach: {0}")]
    Attach(String),
    #[error("extract: {0}")]
    Extract(String),
    #[error("validate: {0}")]
    Validate(String),
    #[error("derive: {0}")]
    Derive(String),
}

pub type TargetId = &'static str;

#[async_trait]
pub trait Projector: Send + Sync {
    fn target_id(&self) -> TargetId;
    fn carrier_convention_version(&self) -> &'static str;

    /// Embed a Rulespec overlay into a native artifact per the target's carrier convention.
    async fn attach(&self, native: Value, overlay: Value) -> Result<Value, ProjectorError>;

    /// Recover `(native, overlay)` from a merged artifact, lossless within the contract.
    async fn extract(&self, merged: Value) -> Result<(Value, Value), ProjectorError>;

    /// Validate that the overlay is well-formed per Layer 2 constraints.
    async fn validate(&self, overlay: Value) -> Result<(), ProjectorError>;

    /// Round-trip parity: `attach → extract` MUST be the identity transform.
    async fn round_trip(
        &self,
        native: Value,
        overlay: Value,
    ) -> Result<bool, ProjectorError> {
        let merged = self.attach(native.clone(), overlay.clone()).await?;
        let (n2, o2) = self.extract(merged).await?;
        Ok(n2 == native && o2 == overlay)
    }

    /// Given a profile (Vocabulary subset expressed as CUE), generate a native schema
    /// in the target format that expresses the profile's content.
    async fn derive(&self, profile_cue_path: &str) -> Result<Value, ProjectorError>;
}
