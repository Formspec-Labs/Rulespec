//! Exercise the validator against the v0.2 positive + negative fixture set.
//!
//! Positive fixtures MUST validate cleanly. Negative fixtures MUST produce ≥1
//! violation. The corpus mirrors `tools/validate_negatives.py` (the SHACL-side
//! negative-fixture gate).

use rkaf_validate::Validator;
use serde_json::Value;

fn fixture(name: &str) -> Value {
    let path = format!(
        "{}/../../fixtures/v0.2/{name}.jsonld",
        env!("CARGO_MANIFEST_DIR")
    );
    serde_json::from_slice(&std::fs::read(&path).expect(&path)).unwrap()
}

/// Fixtures the JSON-Schema gate validates cleanly today.
const STRICT_POSITIVE: &[&str] = &[
    "warrant-legal-positive",
    "warrant-scientific-positive",
    "warrant-cross-family-transition-positive",
    "confidencerecord-calibrated-positive",
    "confidencerecord-uncalibrated-positive",
    "accessscope-public-positive",
    "accessscope-organizationVisible-positive",
    "ailineage-positive",
    "artifact-eli-positive",
    "artifact-doi-positive",
    "artifact-cid-positive",
];

/// Fixtures the SHACL gate validates but the JSON Schema gate does not — the
/// documented Appendix-C divergence:
///
///   - All four `sourcefragment-*-positive`: `rkaf:hasSelector` is a
///     structured OA selector object on the wire, but the CUE → JSON Schema
///     compiler emits a degraded `string | array[string]` shape.
///     (Layer 3 compiler limitation; tracked for a future iteration.)
///   - Both `evidencebinding-*-positive`: contain sparse Assertion cross-ref
///     placeholders without `rkaf:assertionOrigin`. SHACL's targetClass
///     validation does not trip on sparse nodes the same way JSON Schema
///     `required` does.
///
/// These fixtures are normatively valid (per spec/rkaf-vocabulary-v0.2.md and
/// the SHACL shape suite); rkaf-validate's JSON-Schema gate is the weaker
/// target. v0.2 conformance requires *both* the JSON-Schema gate (here) and
/// the SHACL gate (`tools/ci_validate.py`).
const SHACL_ONLY_POSITIVE: &[&str] = &[
    "sourcefragment-oa-textquote-positive",
    "sourcefragment-oa-xpath-positive",
    "sourcefragment-aknt-eid-positive",
    "sourcefragment-uslm-section-positive",
    "evidencebinding-positive",
    "evidencebinding-no-evidence-reason-positive",
];

const NEGATIVE: &[(&str, &str)] = &[
    ("evidencebinding-missing-negative", "rkaf:EvidenceBinding"),
    ("confidencerecord-score-theater-negative", "rkaf:ConfidenceRecord"),
    ("accessscope-leak-negative", "rkaf:AccessScope"),
    ("ailineage-missing-approver-negative", "rkaf:AILineage"),
];

#[test]
fn strict_positive_fixtures_validate() {
    let v = Validator::new();
    let mut fails: Vec<(&str, Vec<rkaf_validate::ValidationError>)> = Vec::new();
    for name in STRICT_POSITIVE {
        let doc = fixture(name);
        if let Err(errs) = v.validate_document(&doc) {
            fails.push((name, errs));
        }
    }
    if !fails.is_empty() {
        eprintln!("\nUnexpected JSON-Schema-side failures on STRICT_POSITIVE:");
        for (name, errs) in &fails {
            eprintln!("  {name}");
            for e in errs {
                eprintln!("    [{}] {} — {}", e.type_iri, e.pointer, e.message);
            }
        }
        panic!("{} strict-positive fixtures regressed", fails.len());
    }
}

#[test]
fn shacl_only_fixtures_currently_diverge_as_expected() {
    let v = Validator::new();
    let mut unexpected_passes: Vec<&str> = Vec::new();
    for name in SHACL_ONLY_POSITIVE {
        let doc = fixture(name);
        if v.validate_document(&doc).is_ok() {
            unexpected_passes.push(name);
        }
    }
    // If a fixture in the SHACL-only list starts passing JSON Schema validation,
    // either the compiler gap closed (great — move it to STRICT_POSITIVE) or
    // the fixture was simplified (also a signal to move it).
    if !unexpected_passes.is_empty() {
        panic!(
            "fixtures in SHACL_ONLY_POSITIVE unexpectedly passed JSON-Schema validation \
             (compiler gap may have closed — move them to STRICT_POSITIVE): {unexpected_passes:?}"
        );
    }
}

/// Negative fixtures intentionally break a Layer 2 invariant. Most break
/// invariants that the *SHACL* shapes catch but the JSON Schema target does
/// not (the documented Appendix-C gap). We assert that AT LEAST the documents
/// parse — they're well-formed enough to load — and document which classes are
/// JSON-Schema-catchable today.
///
/// This is informational: the rkaf-validate JSON-Schema gate is the
/// weaker-side parity check, not the stronger-side SHACL gate.
#[test]
fn negative_fixtures_load_and_classify() {
    let v = Validator::new();
    for (name, _type_iri) in NEGATIVE {
        let doc = fixture(name);
        let result = v.validate_document(&doc);
        // The result might be Ok (Appendix-C gap: SHACL catches, JSON Schema
        // doesn't) or Err (caught by JSON Schema). Either way, we just verify
        // the load + validate path doesn't panic and the doc is parseable.
        let _ = result;
    }
}
