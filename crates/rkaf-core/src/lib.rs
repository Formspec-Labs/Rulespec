//! Rulespec Layer 1 — typed Vocabulary primitives.
//!
//! **All types in this crate are code-generated from the CUE source-of-truth
//! under `constraints/core/`.** The generator is `tools/constraints_compile.py
//! --target rust`. Each CUE source file produces one Rust module under
//! `src/generated/`. The same compiler emits JSON Schema, SHACL, and
//! TypeScript targets from the identical AST — so all surfaces stay in lock
//! step.
//!
//! Source pipeline:
//! ```text
//!   constraints/core/<class>.cue
//!     ↓ python3 tools/constraints_compile.py --target rust
//!   crates/rkaf-core/src/generated/<class>.rs
//! ```
//!
//! Round-trip parity (`from_value(to_value(x)) == x`) is the only invariant
//! this crate guarantees. Validation lives in `rkaf-validate`.

#![allow(clippy::all)]

/// Canonical Rulespec JSON-LD context URL.
pub const RKAF_CONTEXT: &str = "https://rulespec.org/context/rkaf-context.jsonld";

/// JSON-LD shorthand: a property value may appear as either a single scalar
/// or an array of scalars on the wire. The compiled JSON Schema reflects this
/// with `anyOf: [scalar, array]`; this wrapper enum mirrors the same
/// permissiveness in Rust.
///
/// **Caveat — empty-array permissiveness.** `OneOrMany<T>` accepts an empty
/// array (`[]` → `Many(vec![])`), which bypasses any `list.MinItems(N)` CUE
/// cardinality declaration at the Rust layer. JSON Schema validation (via
/// `rkaf-validate`) and SHACL validation (via `tools/ci_validate.py`) catch
/// the cardinality violation on their respective gates; the Rust layer
/// trades type-strictness for round-trip parity. Callers needing strict
/// cardinality should validate via `rkaf-validate` after deserializing.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(untagged)]
pub enum OneOrMany<T> {
    One(T),
    Many(Vec<T>),
}

impl<T> OneOrMany<T> {
    /// Iterate over all values regardless of wire form.
    pub fn iter(&self) -> Box<dyn Iterator<Item = &T> + '_> {
        match self {
            Self::One(v) => Box::new(std::iter::once(v)),
            Self::Many(vs) => Box::new(vs.iter()),
        }
    }
}

#[rustfmt::skip]
pub mod generated {
    pub mod access_scope                 { include!("generated/access_scope.rs"); }
    pub mod ai_lineage                   { include!("generated/ai_lineage.rs"); }
    pub mod applicability_scope          { include!("generated/applicability_scope.rs"); }
    pub mod artifact                     { include!("generated/artifact.rs"); }
    pub mod assertion                          { include!("generated/assertion.rs"); }
    pub mod attestation                        { include!("generated/attestation.rs"); }
    pub mod authority                          { include!("generated/authority.rs"); }
    pub mod bridge_consumer_registration       { include!("generated/bridge_consumer_registration.rs"); }
    pub mod bridge_issue_attestation_contract  { include!("generated/bridge_issue_attestation_contract.rs"); }
    pub mod bridge_validation_result           { include!("generated/bridge_validation_result.rs"); }
    pub mod concept                            { include!("generated/concept.rs"); }
    pub mod concept_mapping                    { include!("generated/concept_mapping.rs"); }
    pub mod concept_resolution_result          { include!("generated/concept_resolution_result.rs"); }
    pub mod confidence_record                  { include!("generated/confidence_record.rs"); }
    pub mod consumer_effective_declaration     { include!("generated/consumer_effective_declaration.rs"); }
    pub mod effective_period                   { include!("generated/effective_period.rs"); }
    pub mod evaluation_anchor                  { include!("generated/evaluation_anchor.rs"); }
    pub mod evidence_binding                   { include!("generated/evidence_binding.rs"); }
    pub mod generated_work_product             { include!("generated/generated_work_product.rs"); }
    pub mod justification                      { include!("generated/justification.rs"); }
    pub mod lifecycle_event                    { include!("generated/lifecycle_event.rs"); }
    pub mod local_adoption                     { include!("generated/local_adoption.rs"); }
    pub mod registry_conflict                  { include!("generated/registry_conflict.rs"); }
    pub mod mapping_state                      { include!("generated/mapping_state.rs"); }
    pub mod point_in_time_exception            { include!("generated/point_in_time_exception.rs"); }
    pub mod retention_policy                   { include!("generated/retention_policy.rs"); }
    pub mod revalidation_event                 { include!("generated/revalidation_event.rs"); }
    pub mod source_fragment                    { include!("generated/source_fragment.rs"); }
    pub mod trust_and_safety                   { include!("generated/trust_and_safety.rs"); }
    pub mod usage_eligibility                  { include!("generated/usage_eligibility.rs"); }
    pub mod warrant                            { include!("generated/warrant.rs"); }
    pub mod workspace                          { include!("generated/workspace.rs"); }
}

// Top-level re-exports — every primitive class. Use the `generated::<module>::`
// path if you need the inner enums (WarrantKind, ConfidenceMethod, etc.).
pub use generated::access_scope::AccessScope;
pub use generated::ai_lineage::AILineage;
pub use generated::applicability_scope::ApplicabilityScope;
pub use generated::artifact::Artifact;
pub use generated::assertion::Assertion;
pub use generated::attestation::Attestation;
pub use generated::authority::Authority;
pub use generated::bridge_consumer_registration::BridgeConsumerRegistration;
pub use generated::bridge_issue_attestation_contract::BridgeIssueAttestationContract;
pub use generated::bridge_validation_result::BridgeValidationResult;
pub use generated::concept_mapping::ConceptMapping;
pub use generated::concept_resolution_result::ConceptResolutionResult;
pub use generated::confidence_record::ConfidenceRecord;
pub use generated::consumer_effective_declaration::ConsumerEffectiveDeclaration;
pub use generated::effective_period::EffectivePeriod;
pub use generated::evidence_binding::EvidenceBinding;
pub use generated::generated_work_product::GeneratedWorkProduct;
pub use generated::justification::Justification;
pub use generated::lifecycle_event::LifecycleEvent;
pub use generated::local_adoption::LocalAdoption;
pub use generated::point_in_time_exception::PointInTimeException;
pub use generated::registry_conflict::RegistryConflict;
pub use generated::revalidation_event::{RevalidationClosureEvent, RevalidationEvent};
pub use generated::source_fragment::SourceFragment;
pub use generated::warrant::Warrant;
pub use generated::workspace::Workspace;
