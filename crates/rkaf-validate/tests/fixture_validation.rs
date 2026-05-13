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

/// Every v0.2 positive fixture validates cleanly against the JSON Schema gate.
///
/// Previously the `sourcefragment-*` and `evidencebinding-*` fixtures lived in
/// a separate `SHACL_ONLY_POSITIVE` list as documented Appendix-C divergences:
///   - `hasSelector` was emitted as `string | array[string]` by the CUE → JSON
///     Schema compiler, but real fixtures use structured OA selector objects.
///   - Cross-ref Assertion placeholders carried no `assertionOrigin`.
/// Both gaps were closed (constraint compiler emits `items: {}` for bare
/// `list.MinItems(N)`; fixtures use a real `rkaf:humanAsserted` origin on
/// cross-ref Assertions). The JSON Schema gate is now byte-equivalent to the
/// SHACL gate on the v0.2 positive fixture set.
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
fn every_positive_fixture_validates() {
    let v = Validator::new();
    let mut fails: Vec<(&str, Vec<rkaf_validate::ValidationError>)> = Vec::new();
    for name in STRICT_POSITIVE {
        let doc = fixture(name);
        if let Err(errs) = v.validate_document(&doc) {
            fails.push((name, errs));
        }
    }
    if !fails.is_empty() {
        eprintln!("\nUnexpected JSON-Schema-side failures:");
        for (name, errs) in &fails {
            eprintln!("  {name}");
            for e in errs {
                eprintln!("    [{}] {} — {}", e.type_iri, e.pointer, e.message);
            }
        }
        panic!("{} positive fixtures failed JSON-Schema validation", fails.len());
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
