//! `rkaf-validate <file>` — validate a Rulespec v0.2 JSON-LD document against
//! the embedded JSON Schema gate.
//!
//! Exit codes:
//!   0  document validates cleanly (or carries only types outside the v0.2 vocabulary)
//!   1  one or more violations
//!   2  setup error (file not found, JSON parse failed, validator init failed)
//!
//! With `--json`, the report is a machine-readable structured object on stdout
//! (an empty errors array on success).

use clap::Parser;
use rkaf_validate::{ValidationError, Validator};
use std::path::PathBuf;
use std::process::ExitCode;

#[derive(Parser)]
#[command(
    name = "rkaf-validate",
    version = env!("CARGO_PKG_VERSION"),
    about = "Validate a Rulespec v0.2 JSON-LD document against the embedded JSON Schema gate.",
    long_about = "\
Validates a Rulespec v0.2 JSON-LD document (or @graph envelope of documents)
against the embedded JSON Schema 2020-12 gate covering Assertion, Warrant,
EvidenceBinding, ConfidenceRecord, AccessScope, AILineage, Artifact, and
SourceFragment classes.

This CLI exercises the JSON Schema target only. Full v0.2 conformance also
requires the SHACL gate (`tools/ci_validate.py` in the rulespec repo).
"
)]
struct Cli {
    /// Path to the JSON-LD document to validate.
    file: PathBuf,
    /// Emit a machine-readable JSON report on stdout (empty errors array on success).
    #[arg(long)]
    json: bool,
}

#[derive(serde::Serialize)]
struct JsonReport<'a> {
    result: &'a str,
    file: &'a str,
    errors: &'a [ValidationError],
}

fn main() -> ExitCode {
    let cli = Cli::parse();
    let file_display = cli.file.display().to_string();

    let bytes = match std::fs::read(&cli.file) {
        Ok(b) => b,
        Err(e) => {
            eprintln!("rkaf-validate: read {file_display}: {e}");
            return ExitCode::from(2);
        }
    };

    let doc: serde_json::Value = match serde_json::from_slice(&bytes) {
        Ok(v) => v,
        Err(e) => {
            eprintln!("rkaf-validate: parse JSON {file_display}: {e}");
            return ExitCode::from(2);
        }
    };

    let validator = Validator::new();
    let outcome = validator.validate_document(&doc);

    if cli.json {
        let errors_vec: Vec<ValidationError> = outcome.clone().err().unwrap_or_default();
        let report = JsonReport {
            result: if outcome.is_ok() { "PASS" } else { "FAIL" },
            file: &file_display,
            errors: &errors_vec,
        };
        println!("{}", serde_json::to_string_pretty(&report).unwrap());
        return if outcome.is_ok() {
            ExitCode::SUCCESS
        } else {
            ExitCode::from(1)
        };
    }

    match outcome {
        Ok(()) => {
            println!("rkaf-validate: {file_display} PASS");
            ExitCode::SUCCESS
        }
        Err(errors) => {
            eprintln!("rkaf-validate: {file_display} FAIL ({} violation(s))", errors.len());
            for e in &errors {
                eprintln!("  [{}] {} — {}", e.type_iri, e.pointer, e.message);
            }
            ExitCode::from(1)
        }
    }
}
