//! Exercise the validator against the v0.2 fixture set.
//!
//! Positive fixtures MUST validate cleanly through the JSON Schema gate, and
//! they MUST cover every compiled schema type embedded by `rkaf-validate`.
//! Negative-fixture fail-as-expected behavior is enforced by the SHACL-side
//! `tools/validate_negatives.py` gate.

use rkaf_validate::Validator;
use serde_json::Value;
use std::collections::BTreeSet;
use std::path::{Path, PathBuf};

fn fixture_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../fixtures")
}

fn fixture(path: &Path) -> Value {
    serde_json::from_slice(
        &std::fs::read(path).unwrap_or_else(|e| panic!("read fixture {}: {e}", path.display())),
    )
    .unwrap_or_else(|e| panic!("parse fixture {}: {e}", path.display()))
}

fn fixture_paths(dir: &Path) -> Vec<PathBuf> {
    let mut paths = Vec::new();
    for entry in
        std::fs::read_dir(dir).unwrap_or_else(|e| panic!("read fixture dir {}: {e}", dir.display()))
    {
        let path = entry.expect("fixture dir entry").path();
        if path.is_dir() {
            paths.extend(fixture_paths(&path));
        } else if path.extension().and_then(|e| e.to_str()) == Some("jsonld") {
            paths.push(path);
        }
    }
    paths.sort();
    paths
}

fn relative_name(path: &Path) -> String {
    path.strip_prefix(fixture_root())
        .expect("fixture path is below fixture root")
        .to_string_lossy()
        .replace('\\', "/")
}

fn expected_kind(path: &Path) -> Option<&'static str> {
    let name = relative_name(path);
    // Cross-gate corpora and L4 behavior fixtures bypass the shape-only
    // validator (each has its own gate). The legacy `context.jsonld`
    // exclusion was removed in `b6c24de` along with the file itself.
    if name.starts_with("behavior/")
        || name.starts_with("edges/")
        || name.starts_with("projectors/")
        || name.starts_with("adversarial/")
        || name.starts_with("ai-extraction/")
    {
        return None;
    }
    if name.contains("-negative") {
        Some("negative")
    } else {
        Some("positive")
    }
}

/// Collect the `@type` IRIs of every dispatchable node in a document.
///
/// The prefix set mirrors `build.rs`: `rkaf:` plus the two OA selector classes
/// Core §4.2 compiles shapes for. Collecting `rkaf:` alone would have made
/// `positive_fixtures_cover_every_embedded_schema_type` fail open the moment
/// those classes were embedded — it would report them uncovered rather than
/// prove a positive fixture exercises them.
///
/// Like the validator itself, this walks the root and `@graph` members only;
/// a selector attached inline inside a fragment is not a covered node.
fn collect_types(value: &Value, types: &mut BTreeSet<String>) {
    if let Some(type_iri) = value.get("@type").and_then(Value::as_str) {
        if type_iri.starts_with("rkaf:") || type_iri.starts_with("oa:") {
            types.insert(type_iri.to_string());
        }
    }
    if let Some(graph) = value.get("@graph").and_then(Value::as_array) {
        for node in graph {
            collect_types(node, types);
        }
    }
}

#[test]
fn every_positive_fixture_validates() {
    let v = Validator::new();
    let mut fails: Vec<(String, Vec<rkaf_validate::ValidationError>)> = Vec::new();
    for path in fixture_paths(&fixture_root())
        .into_iter()
        .filter(|path| expected_kind(path) == Some("positive"))
    {
        let doc = fixture(&path);
        if let Err(errs) = v.validate_document(&doc) {
            fails.push((relative_name(&path), errs));
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
        panic!(
            "{} positive fixtures failed JSON-Schema validation",
            fails.len()
        );
    }
}

#[test]
fn negative_fixtures_load_and_classify() {
    let v = Validator::new();
    for path in fixture_paths(&fixture_root())
        .into_iter()
        .filter(|path| expected_kind(path) == Some("negative"))
    {
        let doc = fixture(&path);
        let result = v.validate_document(&doc);
        let _ = result;
    }
}

#[test]
fn positive_fixtures_cover_every_embedded_schema_type() {
    let v = Validator::new();
    let known: BTreeSet<String> = v.known_type_iris().map(str::to_owned).collect();
    let mut covered = BTreeSet::new();
    for path in fixture_paths(&fixture_root())
        .into_iter()
        .filter(|path| expected_kind(path) == Some("positive"))
    {
        collect_types(&fixture(&path), &mut covered);
    }
    let missing: Vec<_> = known.difference(&covered).cloned().collect();
    assert!(
        missing.is_empty(),
        "positive fixture corpus does not cover embedded schema types: {missing:?}"
    );
}
