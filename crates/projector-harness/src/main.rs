//! Rulespec Layer 4 — projector-harness.
//!
//! CLI used by `tools/projector_parity.py`. Two subcommands:
//!
//!     projector-harness --target <t> round-trip --fixture <path>
//!         Reads a fixture document of shape `{ "native": <doc>, "overlay": <doc> }`
//!         (JSON for json-schema/json-ld; YAML for openapi) and runs Attach → Extract,
//!         exiting 0 on identity, 1 otherwise.
//!
//!     projector-harness --target <t> derive --profile <path>
//!         Invokes `derive(profile)` on the target projector and prints the result
//!         (pretty JSON for json-schema/json-ld, YAML for openapi) to stdout.

use clap::{Parser, Subcommand};
use rkaf_projector_core::Projector;
use serde_json::Value;
use std::path::{Path, PathBuf};

#[derive(Parser)]
struct Cli {
    /// Target projector identifier.
    #[arg(long)]
    target: String,
    #[command(subcommand)]
    op: Op,
}

#[derive(Subcommand)]
enum Op {
    /// Run Attach → Extract on a fixture and assert identity.
    RoundTrip {
        #[arg(long)]
        fixture: PathBuf,
    },
    /// Run `derive(profile)` and print the result.
    Derive {
        #[arg(long)]
        profile: PathBuf,
    },
    /// Validate an overlay through the target projector's shared Layer 2
    /// constraint path.
    Validate {
        #[arg(long)]
        fixture: PathBuf,
    },
}

fn repo_root() -> PathBuf {
    // Harness runs from the Rulespec repo root (the parity orchestrator cd's there).
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn projector_for(target: &str) -> anyhow::Result<Box<dyn Projector>> {
    let root = repo_root();
    match target {
        "json-schema" => Ok(Box::new(
            rkaf_projector_json_schema::JsonSchemaProjector::with_repo_root(&root),
        )),
        "json-ld" => Ok(Box::new(
            rkaf_projector_json_ld::JsonLdProjector::with_repo_root(&root),
        )),
        "openapi" => Ok(Box::new(
            rkaf_projector_openapi::OpenApiProjector::with_repo_root(&root),
        )),
        other => {
            anyhow::bail!("unknown target `{other}` (expected: json-schema | json-ld | openapi)")
        }
    }
}

fn load_fixture(target: &str, path: &Path) -> anyhow::Result<Value> {
    let bytes = std::fs::read(path)?;
    match target {
        "openapi" => Ok(serde_yaml::from_slice(&bytes)?),
        _ => Ok(serde_json::from_slice(&bytes)?),
    }
}

fn print_derive(target: &str, value: &Value) -> anyhow::Result<()> {
    match target {
        "openapi" => print!("{}", serde_yaml::to_string(value)?),
        _ => print!("{}", serde_json::to_string_pretty(value)?),
    }
    Ok(())
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    let projector = projector_for(&cli.target)?;
    match cli.op {
        Op::RoundTrip { fixture } => {
            let body = load_fixture(&cli.target, &fixture)?;
            let native = body
                .get("native")
                .cloned()
                .ok_or_else(|| anyhow::anyhow!("fixture missing `native`"))?;
            let overlay = body
                .get("overlay")
                .cloned()
                .ok_or_else(|| anyhow::anyhow!("fixture missing `overlay`"))?;
            let ok = projector.round_trip(native, overlay).await?;
            std::process::exit(if ok { 0 } else { 1 });
        }
        Op::Derive { profile } => {
            let v = projector.derive(profile.to_str().unwrap()).await?;
            print_derive(&cli.target, &v)?;
        }
        Op::Validate { fixture } => {
            let overlay = load_fixture(&cli.target, &fixture)?;
            projector.validate(overlay).await?;
        }
    }
    Ok(())
}
