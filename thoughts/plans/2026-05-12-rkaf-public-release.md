# Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Rulespec v0.2.0-pre publicly: a polished `README.md` + getting-started, the `rkaf-validate <file>` CLI, SDKs published to crates.io / npm / PyPI under matching versions, the public `CHANGELOG.md` initialized as a single coherent release narrative, and a release manifest spanning all seven layers.

**Architecture:** Three publish flows kicked off from one orchestrator script (`tools/release.sh`). Each flow tags + publishes its registry artifact. Versions are pinned to a single git tag. The CLI tool is a thin wrapper around the `rkaf` Rust SDK from Plan 6 with a single subcommand `validate`. The README walks zero-to-passing-validation in under 10 minutes.

**Tech Stack:** GitHub releases (`gh release create`), `cargo publish` (Rust), `npm publish` (TypeScript), `maturin publish` (Python), GitHub Actions for CI release pipeline.

---

## File structure

```
rulespec/
├── README.md                                     # REWRITTEN — landing page
├── docs/
│   ├── getting-started.md                        # NEW — zero-to-validation walkthrough
│   ├── concepts.md                               # NEW — three-axis claim model + adoption depth + conformance levels
│   └── release-manifest-v0.2.md                  # NEW — single document spanning all seven layers + corpora + bindings + Studio
├── crates/
│   └── rkaf-validate/                            # NEW — CLI binary
│       ├── Cargo.toml
│       └── src/main.rs
├── tools/
│   ├── release.sh                                # NEW — orchestrates the three publish flows
│   └── verify-public-release.sh                  # NEW — post-publish smoke test (installs from each registry, runs `rkaf-validate`)
├── .github/workflows/
│   ├── release.yml                               # NEW — tag-driven publish
│   └── verify-release.yml                        # NEW — runs verify-public-release.sh
└── CHANGELOG.md                                  # CONSOLIDATED — flatten the v0.2.0-pre.{1..10} entries from Plans 1-10 into one v0.2.0 release section
```

---

## Task 1: Author `rkaf-validate` CLI

**Files:**
- Create: `crates/rkaf-validate/{Cargo.toml,src/main.rs}`

- [ ] **Step 1: Manifest**

```toml
[package]
name = "rkaf-validate"
version = { workspace = true }
edition = { workspace = true }
license = { workspace = true }
repository = { workspace = true }
rust-version = { workspace = true }
description = "Rulespec (RKAF) validator CLI — validates a JSON-LD file against the v0.2 vocabulary."

[[bin]]
name = "rkaf-validate"
path = "src/main.rs"

[dependencies]
rkaf       = { path = "../rkaf" }
clap       = { workspace = true }
serde      = { workspace = true }
serde_json = { workspace = true }
anyhow     = { workspace = true }
tokio      = { version = "1", features = ["full"] }
```

- [ ] **Step 2: CLI**

```rust
// crates/rkaf-validate/src/main.rs
use clap::Parser;
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "rkaf-validate", version,
          about = "Validate a JSON-LD file against the Rulespec v0.2 vocabulary.\n\
                   Auto-detects which compiled schema to use by inspecting @type.")]
struct Cli {
    /// Path to the JSON-LD file to validate.
    fixture: PathBuf,
    /// Override the compiled-schema directory (default: bundled schemas).
    #[arg(long, default_value = "compiled/json-schema")]
    schema_dir: PathBuf,
    /// Print errors as JSON instead of plain text.
    #[arg(long)]
    json: bool,
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    let body = std::fs::read_to_string(&cli.fixture)?;
    let doc: serde_json::Value = serde_json::from_str(&body)?;
    let ty = doc.get("@type").and_then(|v| v.as_str())
        .or_else(|| doc.pointer("/@graph/0/@type").and_then(|v| v.as_str()))
        .ok_or_else(|| anyhow::anyhow!("input has no @type at root or first @graph entry"))?;
    let schema_name = ty.strip_prefix("rkaf:").map(class_to_filename)
        .ok_or_else(|| anyhow::anyhow!("@type {ty} is not in the rkaf: namespace"))?;
    let schema_path = cli.schema_dir.join(&schema_name);
    let schema_text = std::fs::read_to_string(&schema_path)?;
    let result = rkaf::parse_and_validate(&body, &schema_text).await?;
    if cli.json {
        println!("{}", serde_json::to_string_pretty(&result)?);
    } else if result.valid {
        println!("OK: {} validates against rkaf:{ty}", cli.fixture.display());
    } else {
        eprintln!("FAIL: {} did not validate:", cli.fixture.display());
        for e in &result.errors { eprintln!("  - {e}"); }
    }
    std::process::exit(if result.valid {0} else {1})
}

fn class_to_filename(class: &str) -> String {
    let mut out = String::with_capacity(class.len());
    for (i, c) in class.chars().enumerate() {
        if i > 0 && c.is_uppercase() { out.push('-'); }
        out.push(c.to_ascii_lowercase());
    }
    out
}
```

- [ ] **Step 3: Build + smoke test**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
cargo build --release --manifest-path crates/Cargo.toml -p rkaf-validate
./crates/target/release/rkaf-validate fixtures/v0.2/artifact-eli-positive.jsonld
./crates/target/release/rkaf-validate fixtures/v0.2/evidencebinding-missing-negative.jsonld
echo "exit code from negative: $?"
```

Expected: First call prints `OK: ... validates against rkaf:Artifact`, exits 0. Second call prints `FAIL` lines and exits 1.

- [ ] **Step 4: Commit**

```bash
git add crates/rkaf-validate/
git commit -m "feat(cli): rkaf-validate <file> — single-shot JSON-LD validator over the v0.2 vocabulary"
```

## Task 2: Author `README.md`

**Files:**
- Modify: `README.md` (full rewrite)

- [ ] **Step 1: Write the README**

```markdown
# Rulespec (RKAF)

**Public federation substrate for evidence-grounded structured claims.**

Rulespec is a vendor-neutral framework for systems that need to make, transport, validate, or act on **structured claims with provable evidence**. Policy is one use case; scientific reproducibility, journalism citation, contracting transparency, audit trails, and AI training-data provenance are siblings.

The framework is **seven layers** — Vocabulary, Constraints, Registries, Projectors, SDKs, Conformance, Reference Corpora — bound by a versioned contract. Cryptographic anchoring is dependency-inverted (bindings depend on Rulespec). AI tooling is treated as a substrate accelerator, not a decision-making authority.

## Quick start

Install the CLI and validate a fixture in under three minutes:

```bash
# Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cargo install rkaf-validate

# Validate a sample assertion
rkaf-validate https://rulespec.org/fixtures/v0.2/warrant-legal-positive.jsonld
# → OK: ... validates against rkaf:Warrant
```

For more depth: [`docs/getting-started.md`](docs/getting-started.md).

## SDKs

| Language | Package | Install |
|---|---|---|
| Rust | [`rkaf`](https://crates.io/crates/rkaf) | `cargo add rkaf` |
| TypeScript | [`@rulespec/sdk`](https://www.npmjs.com/package/@rulespec/sdk) | `npm install @rulespec/sdk` |
| Python | [`rulespec`](https://pypi.org/project/rulespec/) (import `rkaf`) | `pip install rulespec` |

All three SDKs implement the full Rulespec contract — Vocabulary, Constraints, Registries, Projectors — and pass the same conformance suite ([`fixtures/v0.2/sdk-conformance.index.json`](fixtures/v0.2/sdk-conformance.index.json)).

## What this is

Rulespec is **not** a rules engine, **not** rules-as-code, **not** an execution language. It is a data ontology and federation substrate for claims and the metadata that grounds them. Engines, compilers, retrieval systems, and execution layers MAY consume Rulespec but are not part of it.

The framework's job is to make the universal primitives — assertion, artifact, source fragment, evidence binding, warrant (with legal authority as one specialization), eligibility, applicability, access scope, lifecycle, supersession, concept, adoption, justification, attestation, confidence record, bridge — interoperable across heterogeneous tools and services without consolidating around any single vendor's stack.

## How partners join

Six adoption depths (D0 Cite → D5 Sole). Open enrollment; no application process; declare a depth + a conformance level (L1 Validate → L4 Federation), file a disclosure with the [Bridge Contract Registry](spec/registries/bridge-contract-v0.2.md), and you're a partner.

The first reference consumer is [WOS Studio (Authoring)](https://github.com/formspec/policy-studio) at depth D3 (Derive). Studio's 19 native schemas are generated from the [Rulespec Vocabulary](spec/rkaf-core-v0.2.md) via the [Layer 4 JSON Schema projector](spec/projectors/json-schema-v0.2.md).

## Specs and schemas

- **Core vocabulary v0.2:** [`spec/rkaf-core-v0.2.md`](spec/rkaf-core-v0.2.md)
- **Concept registry v0.2:** [`spec/rkaf-concept-registry-v0.2.md`](spec/rkaf-concept-registry-v0.2.md)
- **Anchoring contract v0.2:** [`spec/anchoring/contract-v0.2.md`](spec/anchoring/contract-v0.2.md)
- **Registry specs:** [`spec/registries/`](spec/registries/)
- **Projector carrier conventions:** [`spec/projectors/`](spec/projectors/)
- **Conformance suite:** [`conformance/v0.2/`](conformance/v0.2/)
- **Reference corpora:** [`reference-corpora/`](reference-corpora/)

## Composition with existing ontologies

Rulespec composes deliberately with the existing public-ontology ecosystem. **Do not reinvent.** See [§9 of the core spec](spec/rkaf-core-v0.2.md#9-public-ontology-imports-and-alignments).

| Mode | Examples |
|---|---|
| **Import** | PROV-O, OA (Web Annotation), SKOS, JSON-LD, SHACL, RDF/RDFS/XSD |
| **Align** | ELI / ELI-DL / ELI-I, RRMV, Akoma Ntoso, USLM, LegalRuleML, ECO/SEPIO, Nanopublications, ODRL, DPV, DCTERMS, CiTO, Schema.org/Legislation, DCAT/VoID |
| **Project** | JSON Schema 2020-12, JSON-LD, OpenAPI 3.1 (MVP); FHIR, NIEM, GraphQL, Protobuf, Avro, Iceberg, Cedar/Rego (when partners need them) |

## Status and versioning

Pre-release. Breaking changes signaled via [`CHANGELOG.md`](CHANGELOG.md). Single version axis (`rkaf/0.x`) until structural stability supports the post-1.0 split.

## License

Spec content: [`LICENSE-SPEC`](LICENSE-SPEC) (CC-BY-4.0).
Code: [`LICENSE-CODE`](LICENSE-CODE) (Apache-2.0).
Reference corpora: per-corpus license (CC-BY-4.0 for the corpora shipped in v0.2).

## Contributing

[`CONTRIBUTING.md`](CONTRIBUTING.md). RFC process per [§13 of the core spec](spec/rkaf-core-v0.2.md). External contributor PRs reviewed and merged on technical merit, not institutional affiliation.

## Editorial team

[`CODEOWNERS`](CODEOWNERS). The framework currently operates under formspec-stack maintainership; governance shell migration follows adoption signal (per spec §13.3).
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(rkaf): public README for v0.2 release"
```

## Task 3: Author `docs/getting-started.md`

**Files:**
- Create: `docs/getting-started.md`
- Create: `docs/concepts.md`

- [ ] **Step 1: Getting started — zero to passing validation in under 10 minutes**

```markdown
# Getting Started — Rulespec v0.2

This walkthrough takes you from zero to a passing local validation in under ten minutes.

## 1. Install

Pick a language. The SDKs are at API parity.

```bash
# Rust (recommended for substrate work)
cargo install rkaf-validate
cargo add rkaf

# TypeScript
npm install @rulespec/sdk

# Python (import name "rkaf")
pip install rulespec
```

## 2. Fetch a sample fixture

```bash
curl -sO https://rulespec.org/fixtures/v0.2/warrant-legal-positive.jsonld
```

Open it. You'll see a JSON-LD document expressing a legal-warrant chain: an assertion grounded by source fragments inside an Artifact identified by an ELI URI, supported by a Warrant of kind `rkaf:statutory` in the legal warrant family.

## 3. Validate it

```bash
rkaf-validate warrant-legal-positive.jsonld
# → OK: warrant-legal-positive.jsonld validates against rkaf:Warrant
```

## 4. Break it on purpose

```bash
sed -i 's/rkaf:statutory/rkaf:consent/' warrant-legal-positive.jsonld
rkaf-validate warrant-legal-positive.jsonld
# → FAIL: warrant-legal-positive.jsonld did not validate:
# →   - /rkaf:warrantKind: "rkaf:consent" is not one of the closed-enum values …
```

`rkaf:consent` is not in the v0.2 closed `warrantKind` enum. The validator caught it. This is the "AI as substrate accelerator" guarantee in action — closed enums mean LLMs producing structured output have unambiguous targets, and the validator surfaces every drift.

## 5. Author your own assertion

Use the Rust SDK:

```rust
use rkaf::Validator;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let schema = std::fs::read_to_string("compiled/json-schema/warrant")?;
    let v = Validator::from_compiled_jsonschema(&schema)?;
    let payload = serde_json::json!({
        "@type": "rkaf:Warrant",
        "rkaf:warrantKind":   "rkaf:methodological",
        "rkaf:warrantFamily": "rkaf:scientific"
    });
    let errs = v.validate(&payload);
    println!("errs: {errs:?}");
    Ok(())
}
```

Same operation in TypeScript:

```typescript
import {parseAndValidate} from "@rulespec/sdk";
import {readFileSync} from "node:fs";

const schema  = readFileSync("compiled/json-schema/warrant", "utf8");
const payload = JSON.stringify({
  "@type": "rkaf:Warrant",
  "rkaf:warrantKind":   "rkaf:methodological",
  "rkaf:warrantFamily": "rkaf:scientific",
});
console.log(parseAndValidate(payload, schema));
```

Same in Python:

```python
import rkaf, json
schema  = open("compiled/json-schema/warrant").read()
payload = json.dumps({
  "@type": "rkaf:Warrant",
  "rkaf:warrantKind":   "rkaf:methodological",
  "rkaf:warrantFamily": "rkaf:scientific",
})
print(rkaf.parse_and_validate(payload, schema))
```

## 6. Next steps

- Walk the [three-axis claim model](concepts.md#three-axis-claim-model) — Truth, Social, Consumer.
- Pick an [adoption depth](concepts.md#adoption-depths) (D1 → D5).
- Read the [conformance levels](concepts.md#conformance-levels) (L1 → L4).
- Browse the [reference corpora](../reference-corpora/) — SNAP redetermination (US benefits policy) + scientific reproducibility (10 DOI papers).
- Inspect the [Studio depth-D3 cutover](../profiles/studio/) — the first reference consumer at deep adoption.
```

- [ ] **Step 2: Concepts**

`docs/concepts.md` — copy the relevant normative excerpts from `spec/rkaf-core-v0.2.md` §§1.6 (three-axis claim model), 4.5 (adoption depth gradient), 10.2 (conformance levels). Keep the depth and length appropriate for an introductory overview; link out to the spec for normative content.

- [ ] **Step 3: Commit**

```bash
git add docs/getting-started.md docs/concepts.md
git commit -m "docs(rkaf): getting-started walkthrough + concepts overview"
```

## Task 4: Author `docs/release-manifest-v0.2.md`

**Files:**
- Create: `docs/release-manifest-v0.2.md`

A single document enumerating what shipped across all seven layers + the brand rename + repo extraction + Trellis binding + Studio cutover.

- [ ] **Step 1: Write the manifest**

```markdown
# Rulespec v0.2.0-pre Release Manifest

**Released:** 2026-05-12 (pre-release; CHANGELOG-driven; no semver compatibility yet).

## Brand and infrastructure
- Renamed PKAF → Rulespec / `pkaf:` → `rkaf:` / `https://w3id.org/pkaf/...` → `https://rulespec.org/...` per [Plan 1](../thoughts/plans/2026-05-12-rkaf-repo-extract-and-rename.md).
- Extracted to public `formspec/rulespec` repo; submoduled into `formspec-stack/`.
- VERSION pinned to `0.2.0-pre`; CHANGELOG initialized.

## Layer 1 — Vocabulary
- `spec/rkaf-core-v0.2.md` — normative core (supersedes v0.1.x wholesale; no migration).
- New first-class primitives: Artifact, SourceFragment, EvidenceBinding, Warrant (with Authority preserved as legal-family specialization), ConfidenceRecord, AccessScope, AILineage, MappingState, RetentionPolicy, Workspace, RegistryDisagreement.
- Six warrant families: legal, scientific, editorial, cryptographic, social, source-class.
- §9 ontology composition: imports PROV-O, OA, SKOS, JSON-LD, SHACL, RDF/RDFS/XSD; aligns ELI/ELI-DL/ELI-I, RRMV, Akoma Ntoso, USLM, LegalRuleML, ECO/SEPIO, ODRL, DPV, DCTERMS, CiTO, Nanopublications, Schema.org/Legislation, DCAT/VoID.

## Layer 2 — Constraints
- CUE selected as constraint source language (ADR `docs/adr/2026-05-12-rkaf-constraint-source-cue.md`).
- Multi-target compilation pipeline: JSON Schema 2020-12, Rust, TypeScript (MUST); SHACL Pattern C, CUE, Rego (MAY).
- ≥5 adversarial fixtures (Appendix-C class regressions); ≥3 AI-extraction adversarial fixtures (LLM systematic-misinterpretation patterns).

## Layer 3 — Registries + Federation
- Three normative registries (Source Authority, Concept, Bridge Contract).
- Federation protocol: pull / push / mirror / trust / disagreement.
- Reference instances ship as `docker compose up -d`.

## Layer 4 — Projectors
- JSON Schema 2020-12 / JSON-LD 1.1 / OpenAPI 3.1 — MVP triangle.
- All bidirectional with the Derive operation.
- Carrier conventions published as normative subordinates.

## Layer 5 — SDKs
- Rust (`rkaf`), TypeScript (`@rulespec/sdk`), Python (`rulespec` dist, `rkaf` import).
- API parity asserted by the shared `fixtures/v0.2/sdk-conformance.index.json`.
- Cross-SDK divergence detector (`tools/sdk_parity.py`) gates every release.

## Layer 6 — Conformance
- §10.1 coverage targets met: every Vocabulary class with positive + negative + edge fixtures; every constraint with positive + negative; every projector with round-trip + Derive; every registry-resolution path; ≥5 adversarial; ≥3 AI-extraction adversarial; cascade closure (CascadeClosureV1) and usageEligibility reducer fixtures for L3.
- `rkaf-conformance --level {L1,L2,L3,L4}` exits 0 against the local reference stack.

## Layer 7 — Reference Corpora
- **SNAP redetermination** (US federal benefits policy) — first Reference Corpus, formalized from the Studio SNAP slice. L3 + D3 declared.
- **Scientific Reproducibility** (10 DOI-identified papers, ECO-aligned warrants) — non-policy corpus per master-sequence directive. L2 + D1 declared.
- Both corpora ship with DCAT metadata + tagging methodology + source provenance + CC-BY-4.0 license.

## Anchoring contract
- §7 of `spec/rkaf-core-v0.2.md` defines the abstract contract; subordinate `spec/anchoring/contract-v0.2.md`.
- Reference binding (`urn:rkaf:anchor:trellis/1`) lives in the Trellis repo (`trellis/spec/rkaf-binding.md` + `trellis/crates/trellis-rkaf`). Trellis depends on Rulespec; Rulespec does not name Trellis.

## Studio reference-consumer cutover
- Studio profile published at `rulespec/profiles/studio/studio-profile-v0.2.cue`.
- Studio's 19 native schemas regenerated as outputs of the Layer 4 JSON Schema Derive operation.
- Compiler rewired; **byte-identical SNAP-slice output** verified by `policy-studio/crates/wos-studio-compiler/tests/snap_byte_identical.rs`.
- Studio declares L3 + D3 in `rulespec/conformance/partners/policy-studio.yaml`.

## SDK publication
- Rust: `crates.io/rkaf` and `crates.io/rkaf-validate` at v0.2.0-pre.
- TypeScript: `@rulespec/sdk` at v0.2.0-pre.
- Python: `rulespec` at v0.2.0-pre on PyPI (import name `rkaf`).

## Out of scope (post-launch)
- Partner recruitment beyond Studio (per source spec §16 Phase 7).
- Governance shell migration (per source spec §13.3 — moves on adoption signal).
- Subsequent projector targets beyond the MVP triangle (FHIR, NIEM, GraphQL, Protobuf, Avro, Iceberg, Cedar/Rego — available when partners need them).
- Subsequent reference corpora (journalism citation, contracting transparency via OCDS, AI training-data provenance).
```

- [ ] **Step 2: Commit**

```bash
git add docs/release-manifest-v0.2.md
git commit -m "docs(rkaf): release manifest v0.2 spanning all seven layers + anchoring + Studio cutover"
```

## Task 5: Consolidate the CHANGELOG

**Files:**
- Modify: `CHANGELOG.md`

The CHANGELOG currently has v0.2.0-pre.{1..10} entries from Plans 1-10. Flatten them into one v0.2.0-pre release section so external readers see one coherent narrative, not ten incremental commits.

- [ ] **Step 1: Rewrite**

```markdown
# Rulespec CHANGELOG

## v0.2.0-pre — Public release

**The first public Rulespec release. Pre-release; CHANGELOG-driven; no semver yet.**

### Brand and repo
- Renamed PKAF → Rulespec; `pkaf:` → `rkaf:`; `https://w3id.org/pkaf/...` → `https://rulespec.org/...`.
- Repository extracted to public `formspec/rulespec`; submoduled into `formspec-stack/`.

### Layer 1 — Vocabulary v0.2
- `spec/rkaf-core-v0.2.md` (normative; supersedes v0.1.x wholesale).
- `spec/rkaf-concept-registry-v0.2.md`.
- New first-class primitives: Artifact, SourceFragment, EvidenceBinding, Warrant (universal grounding), ConfidenceRecord, AccessScope, AILineage, MappingState, RetentionPolicy, Workspace, RegistryDisagreement.
- Public ontology composition: imports PROV-O, OA, SKOS, JSON-LD, SHACL, RDF/RDFS/XSD; aligns ELI/ELI-DL/ELI-I, RRMV, Akoma Ntoso, USLM, LegalRuleML, ECO/SEPIO, ODRL, DPV, DCTERMS, CiTO, Nanopublications, Schema.org/Legislation, DCAT/VoID.

### Layer 2 — Constraints v0.2
- CUE source language. JSON Schema 2020-12, Rust, TypeScript MUST; SHACL Pattern C, CUE, Rego MAY.
- ≥5 adversarial fixtures + ≥3 AI-extraction adversarial fixtures.

### Layer 3 — Registries + Federation
- Three normative registries (Source Authority, Concept, Bridge Contract).
- Federation protocol: pull / push / mirror / trust / disagreement.
- Reference instances via `docker compose`.

### Layer 4 — Projectors v0.2
- JSON Schema 2020-12 / JSON-LD 1.1 / OpenAPI 3.1 MVP triangle, all bidirectional with Derive.

### Layer 5 — SDKs v0.2
- Rust `rkaf`, TypeScript `@rulespec/sdk`, Python `rulespec` (import `rkaf`).
- API parity asserted by `fixtures/v0.2/sdk-conformance.index.json`.

### Layer 6 — Conformance
- §10.1 coverage met. `rkaf-conformance --level {L1,L2,L3,L4}` runner.
- Self-certification template + partner howto.

### Layer 7 — Reference Corpora
- SNAP redetermination (L3 + D3) — formalized from Studio's SNAP slice.
- Scientific reproducibility (L2 + D1) — 10 DOI-identified papers with ECO-aligned warrants.

### Anchoring contract (abstract)
- `spec/rkaf-core-v0.2.md` §7 + `spec/anchoring/contract-v0.2.md`.
- Reference binding (`urn:rkaf:anchor:trellis/1`) lives in the Trellis repo.

### Reference consumer cutover
- WOS Studio (Authoring) is the first reference consumer at depth D3 + level L3.
- Studio's 19 native schemas regenerated from the Studio profile via Layer 4 Derive.
- Byte-identical SNAP-slice output verified across the cutover.

### Tooling
- `rkaf-validate <file>` CLI (cargo install rkaf-validate).
- `rkaf-conformance` runner.
- Constraint compiler (`rkaf-constraints-compile`), runtime (`rkaf-constraints-runtime`).
- Three reference registry servers + federation crate.

### Compatibility
None with v0.1.x. Wholesale supersession. No migration shim.
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(rkaf): consolidate v0.2.0-pre CHANGELOG into one release section"
```

## Task 6: Author `tools/release.sh`

**Files:**
- Create: `tools/release.sh`

- [ ] **Step 1: Orchestrator**

```bash
#!/usr/bin/env bash
# Rulespec v0.2 release orchestrator. Tags + publishes:
#   - crates.io: rkaf, rkaf-validate, rkaf-constraints-compile, rkaf-constraints-runtime,
#                rkaf-projector-{core,json-schema,json-ld,openapi},
#                rkaf-registry-{core,client}, rkaf-federation, rkaf-conformance
#   - npm:       @rulespec/sdk
#   - PyPI:      rulespec
#   - GitHub:    release with the release-manifest as body and SHACL+CUE+JSONSchema artifacts attached
set -euo pipefail
VERSION="${1:?usage: tools/release.sh <version, e.g. 0.2.0-pre>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> 1/6 Verify all release gates pass"
.tools/cue version
cargo build --release --manifest-path crates/Cargo.toml
python3 tools/constraints_parity.py
python3 tools/projector_parity.py
python3 tools/sdk_parity.py
./crates/target/release/rkaf-conformance --level L1 --report /tmp/L1.json
./crates/target/release/rkaf-conformance --level L2 --report /tmp/L2.json
./crates/target/release/rkaf-conformance --level L3 --report /tmp/L3.json
./crates/target/release/rkaf-conformance --level L4 --report /tmp/L4.json
python3 tools/corpus_validate.py reference-corpora/snap-redetermination/v0.2
python3 tools/corpus_validate.py reference-corpora/scientific-reproducibility/v0.2

echo "==> 2/6 Tag the repo"
git tag -a "v$VERSION" -m "Rulespec v$VERSION"
git push origin "v$VERSION"

echo "==> 3/6 Publish Rust crates (in dep order)"
for c in rkaf-constraints-compile rkaf-constraints-runtime \
         rkaf-projector-core rkaf-projector-json-schema rkaf-projector-json-ld rkaf-projector-openapi \
         rkaf-registry-core rkaf-registry-client rkaf-federation \
         rkaf rkaf-conformance rkaf-validate; do
  cargo publish --manifest-path "crates/$c/Cargo.toml"
done

echo "==> 4/6 Publish npm package"
( cd sdks/typescript && npm publish --access public )

echo "==> 5/6 Publish Python package"
( cd sdks/python && maturin publish --manifest-path ../../crates/rkaf-py/Cargo.toml )

echo "==> 6/6 GitHub release"
gh release create "v$VERSION" \
  --title "Rulespec v$VERSION" \
  --notes-file docs/release-manifest-v0.2.md \
  /tmp/L1.json /tmp/L2.json /tmp/L3.json /tmp/L4.json
echo "DONE"
```

- [ ] **Step 2: Make executable + smoke test (dry run, do not actually publish)**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
chmod +x tools/release.sh
./tools/release.sh --dry-run 0.2.0-pre || echo "dry-run not yet supported; see Task 7 for the dry-run flag"
```

- [ ] **Step 3: Commit**

```bash
git add tools/release.sh
git commit -m "build(rkaf): release orchestrator script (gates + publish flows)"
```

## Task 7: Author `tools/verify-public-release.sh`

**Files:**
- Create: `tools/verify-public-release.sh`

- [ ] **Step 1: Verifier**

```bash
#!/usr/bin/env bash
# Post-publish verification. Installs each SDK from its public registry into a
# clean container/venv and runs `rkaf-validate` on a sample fixture.
set -euo pipefail
VERSION="${1:?usage: tools/verify-public-release.sh <version>}"

echo "==> Rust"
cargo install --version "$VERSION" rkaf-validate
rkaf-validate https://rulespec.org/fixtures/v0.2/warrant-legal-positive.jsonld

echo "==> TypeScript"
mkdir -p /tmp/rkaf-verify-ts && cd /tmp/rkaf-verify-ts
npm init -y >/dev/null
npm install "@rulespec/sdk@$VERSION"
node --eval 'import("@rulespec/sdk").then(({parseAndValidate}) => console.log(typeof parseAndValidate))'

echo "==> Python"
python3 -m venv /tmp/rkaf-verify-py
. /tmp/rkaf-verify-py/bin/activate
pip install "rulespec==$VERSION"
python3 -c "import rkaf; print(dir(rkaf))"

echo "ALL VERIFIED"
```

- [ ] **Step 2: Commit**

```bash
git add tools/verify-public-release.sh
git commit -m "build(rkaf): post-publish verifier (installs from each registry, smoke-tests)"
```

## Task 8: CI release pipeline

**Files:**
- Create: `.github/workflows/release.yml`
- Create: `.github/workflows/verify-release.yml`

- [ ] **Step 1: Tag-driven release workflow**

```yaml
# .github/workflows/release.yml
name: release
on:
  push:
    tags: ['v*']
permissions: { contents: write }
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { submodules: recursive, fetch-depth: 0 }
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - uses: actions/setup-node@v4
        with: { node-version: '22', registry-url: 'https://registry.npmjs.org' }
      - uses: dtolnay/rust-toolchain@stable
      - run: ./tools/install-cue.sh
      - run: pip install pyshacl rdflib pyld jsonschema maturin
      - run: ./tools/release.sh ${GITHUB_REF_NAME#v}
        env:
          CARGO_REGISTRY_TOKEN: ${{ secrets.CARGO_REGISTRY_TOKEN }}
          NODE_AUTH_TOKEN:      ${{ secrets.NPM_TOKEN }}
          MATURIN_PYPI_TOKEN:   ${{ secrets.PYPI_TOKEN }}
          GH_TOKEN:             ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: Post-release verifier workflow**

```yaml
# .github/workflows/verify-release.yml
name: verify-release
on:
  release: { types: [published] }
jobs:
  verify:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: ./tools/verify-public-release.sh ${{ github.event.release.tag_name }}
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml .github/workflows/verify-release.yml
git commit -m "ci(rkaf): tag-driven release + post-release verification workflows"
```

## Task 9: Final pre-release sanity sweep

- [ ] **Step 1: Re-run every gate**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 tools/rename_audit.py                       # CLEAN
python3 tools/vocab_audit.py                        # all required fixtures present
python3 tools/ci_validate.py --mode v02             # PASS
python3 tools/validate_negatives.py                 # all FAIL-AS-EXPECTED
python3 tools/constraints_parity.py                 # zero divergences
python3 tools/projector_parity.py                   # all OK
python3 tools/sdk_parity.py                         # all PARITY
./crates/target/release/rkaf-conformance --level L1 --report /tmp/L1.json
./crates/target/release/rkaf-conformance --level L2 --report /tmp/L2.json
./crates/target/release/rkaf-conformance --level L3 --report /tmp/L3.json
./crates/target/release/rkaf-conformance --level L4 --report /tmp/L4.json
python3 tools/corpus_validate.py reference-corpora/snap-redetermination/v0.2
python3 tools/corpus_validate.py reference-corpora/scientific-reproducibility/v0.2
python3 tools/corpus_eco_align.py
python3 tools/federation_test.py
( cd ../trellis && cargo test -p trellis-rkaf )
( cd ../policy-studio && cargo test -p wos-studio-compiler --test snap_byte_identical )
```

Expected: every command exits 0.

- [ ] **Step 2: Cut the tag and trigger the release pipeline**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
git tag -a v0.2.0-pre -m "Rulespec v0.2.0-pre — public release"
git push origin v0.2.0-pre
```

- [ ] **Step 3: Watch the CI release pipeline**

```bash
gh run watch --repo formspec/rulespec
```

Expected: `release.yml` succeeds (publishes to crates.io / npm / PyPI / GitHub release). `verify-release.yml` then succeeds on both ubuntu and macOS runners.

## Task 10: Bump submodule pointers in formspec-stack to the released tag

- [ ] **Step 1: Bump rulespec submodule to v0.2.0-pre**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
git checkout v0.2.0-pre
cd /Users/mikewolfd/Work/formspec-stack
git add rulespec
git commit -m "chore(submodules): bump rulespec to v0.2.0-pre (public release)"
```

## Self-review

- [ ] `rkaf-validate <file>` CLI exists, builds clean, and exits 0 on a passing fixture / 1 on a failing fixture.
- [ ] `README.md` walks zero-to-validation in under 10 minutes; lists install commands for all three SDKs.
- [ ] `docs/getting-started.md` and `docs/concepts.md` exist.
- [ ] `docs/release-manifest-v0.2.md` spans all seven layers + anchoring + Studio cutover.
- [ ] `CHANGELOG.md` consolidated to one v0.2.0-pre release section (not ten incremental v0.2.0-pre.{1..10} entries).
- [ ] `tools/release.sh` runs every gate then publishes Rust + npm + PyPI + GitHub release.
- [ ] `tools/verify-public-release.sh` installs each SDK from its public registry and smoke-tests.
- [ ] `.github/workflows/release.yml` is tag-driven; secrets configured (CARGO_REGISTRY_TOKEN, NPM_TOKEN, PYPI_TOKEN).
- [ ] `.github/workflows/verify-release.yml` runs on `release.published` for ubuntu + macOS.
- [ ] Every gate passes locally before tag push (Task 9 step 1).
- [ ] formspec-stack submodule pointer bumped to v0.2.0-pre.
- [ ] Public release artifacts: crates.io packages live, npm package live, PyPI package live, GitHub release with attached conformance reports + release manifest as body.
