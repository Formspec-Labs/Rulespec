//! Rulespec Layer 1 — typed Vocabulary primitives.
//!
//! Each primitive maps 1:1 to a `rkaf:` class declared in the Rulespec v0.2
//! Vocabulary. Structs round-trip with the canonical JSON-LD wire format via
//! serde; closed-enum properties are typed Rust enums whose serde
//! representations are the canonical `rkaf:` IRIs.
//!
//! This crate intentionally does **no validation**. Constructing a struct that
//! violates a Layer 2 constraint is allowed — validation lives in
//! `rkaf-validate`. Round-trip parity (`from_value(to_value(x)) == x`) is the
//! only invariant this crate guarantees.

pub mod access_scope;
pub mod ai_lineage;
pub mod artifact;
pub mod assertion;
pub mod confidence;
pub mod evidence;
pub mod source_fragment;
pub mod warrant;

pub use access_scope::{AccessScope, AccessScopeKind, RegulatoryClass};
pub use ai_lineage::AiLineage;
pub use artifact::{Artifact, ArtifactIdentifierScheme};
pub use assertion::{Assertion, AssertionOrigin};
pub use confidence::{
    CalibrationStatus, ConfidenceMethod, ConfidenceRecord, ScoreCategorical,
};
pub use evidence::{EvidenceBinding, NoEvidenceReason};
pub use source_fragment::{SelectorKind, SourceFragment};
pub use warrant::{Warrant, WarrantFamily, WarrantKind};

/// Canonical Rulespec v0.2 JSON-LD context URL.
pub const RKAF_CONTEXT: &str =
    "https://rulespec.org/context/rkaf-context.jsonld";
