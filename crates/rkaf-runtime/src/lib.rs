//! Rulespec Layer 5 behavioral runtime.
//!
//! Implements the 5 behavioral contracts specified in `spec/rkaf-behavior.md`:
//! the UsageEligibility reducer, CascadeClosureV1, the 10 bridge contract
//! rules, PointInTimeException evaluation, and concept resolution with
//! RegistryConflict detection.
//!
//! The entry point is [`Runtime::evaluate`], which consumes a
//! `BehaviorTestCase` (JSON-LD wrapper with `behaviorContract`, `input`, and
//! `expectedOutput` fields) and returns a [`Verdict`] either matching the
//! declared expected output or carrying a diagnostic.
//!
//! This crate is the reference L4 conformance gate. Partner runtimes MUST
//! produce identical outputs on the corpus under `fixtures/behavior/`.

#![forbid(unsafe_code)]

pub mod bridge;
pub mod cascade;
pub mod concept;
pub mod errors;
pub mod graph;
pub mod pit;
pub mod reducer;
pub mod runtime;
pub mod stale;
pub mod verdict;

pub use errors::RuntimeError;
pub use graph::Graph;
pub use runtime::Runtime;
pub use verdict::Verdict;
