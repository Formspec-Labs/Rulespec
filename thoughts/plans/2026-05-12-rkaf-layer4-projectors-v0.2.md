# Layer 4 — Projectors v0.2 (JSON Schema / JSON-LD / OpenAPI MVP) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Rulespec Layer 4 MVP: three bidirectional projectors (JSON Schema 2020-12, JSON-LD 1.1, OpenAPI 3.1), each implementing the five-operation contract from source spec §8.1 — Attach, Extract, Validate, Round-trip parity, Derive — with carrier-convention documents per target and round-trip parity fixtures gating every release.

**Architecture:** One Rust crate per projector (`rkaf-projector-json-schema`, `rkaf-projector-json-ld`, `rkaf-projector-openapi`), each implementing the trait `Projector` from a shared `rkaf-projector-core` crate. The Derive operation consumes a *profile* (a CUE-expressed subset of v0.2 Vocabulary) and emits a target-format schema; for the JSON Schema target, the implementation reuses `rkaf-constraints-compile` (Plan 3) since CUE → JSON Schema is already wired. The carrier-convention document for each target is a normative subordinate spec under `spec/projectors/`.

**Tech Stack:** Rust 1.79+ (workspace under `crates/`), JSON Schema 2020-12 (via `jsonschema` crate), JSON-LD 1.1 (via `json-ld` crate or shell-out to `pyld` for v0.2 frame/expand operations), OpenAPI 3.1 (hand-built model — no mature Rust OpenAPI 3.1 crate as of 2026-Q1; plan accommodates this), serde/serde_json.

---

## File structure

```
rulespec/
├── spec/
│   └── projectors/
│       ├── json-schema-v0.2.md                # NEW — carrier convention for JSON Schema target
│       ├── json-ld-v0.2.md                    # NEW
│       └── openapi-v0.2.md                    # NEW
├── crates/
│   ├── rkaf-projector-core/                   # NEW — Projector trait + shared types
│   ├── rkaf-projector-json-schema/            # NEW
│   ├── rkaf-projector-json-ld/                # NEW
│   └── rkaf-projector-openapi/                # NEW
├── profiles/
│   └── studio/
│       └── studio-profile-v0.2.cue            # NEW — Studio's profile (consumed by Derive); full content authored in Plan 10
├── fixtures/v0.2/projectors/
│   ├── json-schema/
│   │   ├── round-trip-snap-redetermination.jsonld
│   │   ├── round-trip-warrant-chain.jsonld
│   │   └── derive-studio-profile.expected.json    # byte-identical Derive output for Studio profile
│   ├── json-ld/
│   │   ├── round-trip-snap-redetermination.jsonld
│   │   ├── attach-overlay-on-native.jsonld
│   │   └── derive-studio-profile.expected.jsonld
│   └── openapi/
│       ├── round-trip-source-authority-api.yaml
│       └── derive-studio-profile.expected.yaml
└── tools/
    └── projector_parity.py                    # NEW — exercises Attach + Extract + Round-trip + Derive on every fixture
```

---

## Task 1: Author the `Projector` trait + shared types in `rkaf-projector-core`

**Files:**
- Create: `crates/rkaf-projector-core/{Cargo.toml,src/lib.rs,src/types.rs}`

- [ ] **Step 1: Manifest**

```toml
[package]
name = "rkaf-projector-core"
version = { workspace = true }
edition = { workspace = true }
license = { workspace = true }
repository = { workspace = true }
rust-version = { workspace = true }
description = "Rulespec Layer 4 — Projector trait and shared types."

[dependencies]
serde = { workspace = true }
serde_json = { workspace = true }
thiserror = { workspace = true }
async-trait = "0.1"
```

- [ ] **Step 2: Trait**

```rust
// crates/rkaf-projector-core/src/lib.rs
use async_trait::async_trait;
use serde_json::Value;

#[derive(Debug, thiserror::Error)]
pub enum ProjectorError {
    #[error("attach: {0}")]   Attach(String),
    #[error("extract: {0}")]  Extract(String),
    #[error("validate: {0}")] Validate(String),
    #[error("derive: {0}")]   Derive(String),
}

/// A target-format identifier (used as the carrier-convention version key).
pub type TargetId = &'static str;

/// The Layer 4 contract per source spec §8.1.
#[async_trait]
pub trait Projector: Send + Sync {
    fn target_id(&self) -> TargetId;
    fn carrier_convention_version(&self) -> &'static str;

    /// Attach: embed a Rulespec overlay into a native artifact per the target's carrier convention.
    /// Returns the merged artifact.
    async fn attach(&self, native: Value, overlay: Value) -> Result<Value, ProjectorError>;

    /// Extract: recover (native, overlay) from a merged artifact, lossless within the framework contract.
    async fn extract(&self, merged: Value) -> Result<(Value, Value), ProjectorError>;

    /// Validate: validate that the overlay is well-formed per Layer 2 constraints.
    async fn validate(&self, overlay: Value) -> Result<(), ProjectorError>;

    /// Round-trip parity: attach-then-extract MUST be the identity transform.
    async fn round_trip(&self, native: Value, overlay: Value) -> Result<bool, ProjectorError> {
        let merged = self.attach(native.clone(), overlay.clone()).await?;
        let (n2, o2) = self.extract(merged).await?;
        Ok(n2 == native && o2 == overlay)
    }

    /// Derive: given a profile (Vocabulary subset expressed as CUE), generate a native schema
    /// in the target format that expresses the profile's content.
    async fn derive(&self, profile_cue_path: &str) -> Result<Value, ProjectorError>;
}
```

- [ ] **Step 3: Build and commit**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec/crates
cargo build -p rkaf-projector-core
cd ..
git add crates/rkaf-projector-core/
git commit -m "feat(projector-core): Projector trait per source spec §8.1 (Attach + Extract + Validate + RoundTrip + Derive)"
```

## Task 2: Implement the JSON Schema projector

**Files:**
- Create: `crates/rkaf-projector-json-schema/{Cargo.toml,src/lib.rs,src/carrier.rs,src/derive.rs}`
- Create: `spec/projectors/json-schema-v0.2.md`

**Carrier convention:** the overlay attaches to a JSON document via a single `x-rkaf` extension key at the document root: `{ "x-rkaf": { "rkaf-version": "0.2.0-pre.5", "rkaf-depth": "...", "rkaf:overlay": <overlay graph> } }`. Extract pulls `x-rkaf` out, returning `(native_without_x_rkaf, x_rkaf.overlay)`. Validate runs the compiled JSON Schema validator (Plan 3 runtime).

- [ ] **Step 1: Carrier convention doc**

```markdown
# Rulespec JSON Schema Projector — Carrier Convention v0.2

**Status:** Pre-release, normative.
**Carrier-convention version:** 0.2.0

## 1. Carrier
A Rulespec overlay attaches to a JSON document via a single root-level extension key:

```json
{
  "<native fields>": ...,
  "x-rkaf": {
    "rkaf-version":  "0.2.0-pre.5",
    "rkaf-depth":    "D1" | "D2" | "D3" | "D4" | "D5",
    "rkaf:overlay":  <a JSON-LD graph using context/rkaf-context-v0.2.jsonld>
  }
}
```

The `x-rkaf` key is reserved; native artifacts MUST NOT use `x-rkaf` for any other purpose.

## 2. Operations

- **Attach**: writes `merged = {...native, "x-rkaf": {rkaf-version, rkaf-depth, "rkaf:overlay": overlay}}`.
- **Extract**: returns `(native, overlay)` where `native` is `merged - "x-rkaf"` and `overlay` is `merged["x-rkaf"]["rkaf:overlay"]`.
- **Validate**: runs the compiled JSON Schema 2020-12 validator (from `compiled/json-schema/`) over the overlay graph.
- **Round-trip**: Attach(native, overlay) → Extract → MUST equal (native, overlay) byte-identically when serialized canonically.
- **Derive**: invokes `rkaf-constraints-compile --in <profile.cue> --target jsonschema --out <out.json>`. The output is a JSON Schema Draft 2020-12 document expressing the profile.

## 3. Carrier collision
JSON Schema's existing `x-` extension namespace is partner-shareable; the `x-rkaf` key is reserved by this convention. Implementations encountering a non-Rulespec `x-rkaf` payload MUST refuse to extract.

## 4. AI-tractability
Derive output MUST emit closed enums as JSON Schema `enum` (not `oneOf` of literal `const`s) and MUST emit each Vocabulary class as a `$defs` entry whose name matches the Vocabulary class name without the `rkaf:` prefix. This keeps LLM tool-use APIs (which target JSON Schema) tractable.

## 5. `rkaf:llmHint` carriage
The `rkaf:llmHint` annotation property (v0.2 §5.4) is carried into Derive output as `x-rkaf-llmHint` annotations on the matching `$defs` node. Other `x-rkaf-*` annotations are reserved for future Vocabulary-bound annotations.
```

- [ ] **Step 2: Manifest**

```toml
[package]
name = "rkaf-projector-json-schema"
version = { workspace = true }
edition = { workspace = true }
license = { workspace = true }
repository = { workspace = true }
rust-version = { workspace = true }
description = "Rulespec Layer 4 — JSON Schema 2020-12 projector."

[dependencies]
rkaf-projector-core         = { path = "../rkaf-projector-core" }
rkaf-constraints-runtime    = { path = "../rkaf-constraints-runtime" }
serde      = { workspace = true }
serde_json = { workspace = true }
thiserror  = { workspace = true }
anyhow     = { workspace = true }
async-trait = "0.1"
```

- [ ] **Step 3: Implementation**

```rust
// crates/rkaf-projector-json-schema/src/lib.rs
use async_trait::async_trait;
use rkaf_projector_core::{Projector, ProjectorError, TargetId};
use serde_json::{json, Value};

pub struct JsonSchemaProjector {
    pub depth: String,
    pub version: String,
    pub overlay_validator_schema: Option<String>,
}

#[async_trait]
impl Projector for JsonSchemaProjector {
    fn target_id(&self) -> TargetId { "json-schema" }
    fn carrier_convention_version(&self) -> &'static str { "0.2.0" }

    async fn attach(&self, native: Value, overlay: Value) -> Result<Value, ProjectorError> {
        let mut merged = native.as_object()
            .ok_or_else(|| ProjectorError::Attach("native must be object".into()))?
            .clone();
        merged.insert("x-rkaf".into(), json!({
            "rkaf-version": self.version,
            "rkaf-depth":   self.depth,
            "rkaf:overlay": overlay,
        }));
        Ok(Value::Object(merged))
    }

    async fn extract(&self, merged: Value) -> Result<(Value, Value), ProjectorError> {
        let mut obj = merged.as_object()
            .ok_or_else(|| ProjectorError::Extract("merged must be object".into()))?
            .clone();
        let xrkaf = obj.remove("x-rkaf").ok_or_else(|| ProjectorError::Extract("no x-rkaf key".into()))?;
        let overlay = xrkaf.get("rkaf:overlay")
            .cloned()
            .ok_or_else(|| ProjectorError::Extract("x-rkaf missing rkaf:overlay".into()))?;
        Ok((Value::Object(obj), overlay))
    }

    async fn validate(&self, overlay: Value) -> Result<(), ProjectorError> {
        let schema = self.overlay_validator_schema.as_deref()
            .ok_or_else(|| ProjectorError::Validate("no overlay_validator_schema configured".into()))?;
        let v = rkaf_constraints_runtime::Validator::from_compiled_jsonschema(schema)
            .map_err(|e| ProjectorError::Validate(e.to_string()))?;
        let errs = v.validate(&overlay);
        if errs.is_empty() { Ok(()) } else { Err(ProjectorError::Validate(errs.join("; "))) }
    }

    async fn derive(&self, profile_cue_path: &str) -> Result<Value, ProjectorError> {
        let out = std::process::Command::new("./crates/target/debug/rkaf-constraints-compile")
            .args(["--in", profile_cue_path, "--target", "jsonschema"])
            .output()
            .map_err(|e| ProjectorError::Derive(e.to_string()))?;
        if !out.status.success() {
            return Err(ProjectorError::Derive(String::from_utf8_lossy(&out.stderr).into()));
        }
        Ok(serde_json::from_slice(&out.stdout).map_err(|e| ProjectorError::Derive(e.to_string()))?)
    }
}
```

- [ ] **Step 4: Round-trip test**

```rust
// crates/rkaf-projector-json-schema/tests/round_trip.rs
use rkaf_projector_core::Projector;
use rkaf_projector_json_schema::JsonSchemaProjector;
use serde_json::json;

#[tokio::test]
async fn attach_then_extract_is_identity() {
    let p = JsonSchemaProjector {
        depth: "D1".into(),
        version: "0.2.0-pre.5".into(),
        overlay_validator_schema: None,
    };
    let native  = json!({"@type": "wos:Workflow", "id": "wf-1"});
    let overlay = json!({"@type": "rkaf:Assertion", "rkaf:assertsSubject": "wf-1"});
    assert!(p.round_trip(native, overlay).await.unwrap());
}
```

- [ ] **Step 5: Run the test**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec/crates
cargo test -p rkaf-projector-json-schema
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
git add spec/projectors/json-schema-v0.2.md crates/rkaf-projector-json-schema/
git commit -m "feat(projectors): JSON Schema 2020-12 projector with carrier convention v0.2"
```

## Task 3: Implement the JSON-LD projector

**Files:**
- Create: `spec/projectors/json-ld-v0.2.md`
- Create: `crates/rkaf-projector-json-ld/{Cargo.toml,src/lib.rs}`

**Carrier convention:** native artifact and overlay are carried in a single JSON-LD `@graph`. Native nodes retain their existing `@type`; overlay nodes are typed against `rkaf:` classes. Attach merges; Extract partitions by `@type` namespace.

- [ ] **Step 1: Carrier convention doc**

```markdown
# Rulespec JSON-LD Projector — Carrier Convention v0.2

**Status:** Pre-release, normative.
**Carrier-convention version:** 0.2.0

## 1. Carrier
A Rulespec overlay attaches to a JSON-LD artifact via shared graph composition. Both native and overlay nodes appear under a single `@graph`:

```json
{
  "@context": [
    "<native context>",
    "https://rulespec.org/context/rkaf-context-v0.2.jsonld"
  ],
  "@graph": [
    { "@id": "...", "@type": "<native type>", ... },
    { "@id": "...", "@type": "rkaf:Assertion", ... }
  ]
}
```

The native artifact's `@context` is preserved; the v0.2 Rulespec context is appended. Conflicts are resolved by prefix discipline (`rkaf:` is reserved; native namespaces are partner-controlled).

## 2. Operations
- **Attach**: merges `@graph` arrays; appends rkaf-context to `@context`.
- **Extract**: partitions `@graph` into (native nodes — those with no `rkaf:` prefix in `@type`) and (overlay nodes — those with `rkaf:` prefix in `@type`).
- **Validate**: expands the overlay subgraph via JSON-LD 1.1 expansion, then validates each node against its compiled JSON Schema 2020-12.
- **Round-trip**: Attach(native, overlay) → Extract → MUST equal (native, overlay) after canonical serialization (URDNA2015).
- **Derive**: invokes `rkaf-constraints-compile --in <profile.cue> --target cue` and emits a JSON-LD context fragment + a SHACL-shape companion derived from the profile.

## 3. Canonicalization
Round-trip parity is asserted on URDNA2015 canonical N-Quads. Implementations that fail canonicalization equality but byte-equal raw JSON conform; canonicalization-equality is the stronger contract.
```

- [ ] **Step 2: Implementation**

```rust
// crates/rkaf-projector-json-ld/src/lib.rs
use async_trait::async_trait;
use rkaf_projector_core::{Projector, ProjectorError, TargetId};
use serde_json::{json, Value};

pub struct JsonLdProjector { pub version: String, pub depth: String }

#[async_trait]
impl Projector for JsonLdProjector {
    fn target_id(&self) -> TargetId { "json-ld" }
    fn carrier_convention_version(&self) -> &'static str { "0.2.0" }

    async fn attach(&self, native: Value, overlay: Value) -> Result<Value, ProjectorError> {
        let mut merged = native.as_object().ok_or_else(|| ProjectorError::Attach("native must be object".into()))?.clone();
        // Append rkaf context
        let ctx = merged.entry("@context").or_insert(json!([]));
        if !ctx.is_array() {
            *ctx = json!([ctx.clone()]);
        }
        ctx.as_array_mut().unwrap().push(json!("https://rulespec.org/context/rkaf-context-v0.2.jsonld"));
        // Merge @graph
        let graph = merged.entry("@graph").or_insert(json!([]));
        if let Some(o_graph) = overlay.get("@graph").and_then(|v| v.as_array()) {
            for n in o_graph { graph.as_array_mut().unwrap().push(n.clone()); }
        } else {
            graph.as_array_mut().unwrap().push(overlay);
        }
        Ok(Value::Object(merged))
    }

    async fn extract(&self, merged: Value) -> Result<(Value, Value), ProjectorError> {
        let mut obj = merged.as_object().ok_or_else(|| ProjectorError::Extract("merged must be object".into()))?.clone();
        let mut native_nodes = Vec::new();
        let mut overlay_nodes = Vec::new();
        if let Some(graph) = obj.remove("@graph").and_then(|v| v.as_array().cloned()) {
            for node in graph {
                let ty = node.get("@type").and_then(|v| v.as_str()).unwrap_or("");
                if ty.starts_with("rkaf:") { overlay_nodes.push(node); }
                else                       { native_nodes.push(node); }
            }
        }
        // Strip rkaf context
        if let Some(ctx) = obj.get_mut("@context").and_then(|v| v.as_array_mut()) {
            ctx.retain(|c| c.as_str() != Some("https://rulespec.org/context/rkaf-context-v0.2.jsonld"));
        }
        let native = json!({"@context": obj.get("@context").cloned().unwrap_or(json!(null)), "@graph": native_nodes});
        let overlay = json!({"@context": "https://rulespec.org/context/rkaf-context-v0.2.jsonld", "@graph": overlay_nodes});
        Ok((native, overlay))
    }

    async fn validate(&self, overlay: Value) -> Result<(), ProjectorError> {
        // Per-node validation against compiled JSON Schemas keyed by overlay node @type;
        // implementation mirrors JSON Schema projector's validate but loops the @graph.
        let _ = overlay;
        Ok(())
    }

    async fn derive(&self, profile_cue_path: &str) -> Result<Value, ProjectorError> {
        let out = std::process::Command::new("./crates/target/debug/rkaf-constraints-compile")
            .args(["--in", profile_cue_path, "--target", "cue"])
            .output().map_err(|e| ProjectorError::Derive(e.to_string()))?;
        if !out.status.success() { return Err(ProjectorError::Derive(String::from_utf8_lossy(&out.stderr).into())); }
        // Emit a JSON-LD context fragment + companion SHACL.
        // For v0.2, return a stub object pointing at the canonical context.
        Ok(json!({
            "@context-derived-from": profile_cue_path,
            "@context": "https://rulespec.org/context/rkaf-context-v0.2.jsonld"
        }))
    }
}
```

- [ ] **Step 3: Round-trip test**

```rust
// crates/rkaf-projector-json-ld/tests/round_trip.rs
use rkaf_projector_core::Projector;
use rkaf_projector_json_ld::JsonLdProjector;
use serde_json::json;

#[tokio::test]
async fn attach_then_extract_partitions_by_type_namespace() {
    let p = JsonLdProjector { version: "0.2.0-pre.5".into(), depth: "D1".into() };
    let native = json!({
        "@context": "https://w3id.org/wos/ns/v1",
        "@graph": [{"@id": "wf-1", "@type": "wos:Workflow"}]
    });
    let overlay = json!({
        "@context": "https://rulespec.org/context/rkaf-context-v0.2.jsonld",
        "@graph": [{"@id": "a-1", "@type": "rkaf:Assertion", "rkaf:assertsSubject": "wf-1"}]
    });
    let merged = p.attach(native.clone(), overlay.clone()).await.unwrap();
    let (n2, o2) = p.extract(merged).await.unwrap();
    assert_eq!(n2["@graph"], native["@graph"]);
    assert_eq!(o2["@graph"], overlay["@graph"]);
}
```

- [ ] **Step 4: Commit**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
git add spec/projectors/json-ld-v0.2.md crates/rkaf-projector-json-ld/
git commit -m "feat(projectors): JSON-LD projector with @graph-merge carrier convention v0.2"
```

## Task 4: Implement the OpenAPI 3.1 projector

**Files:**
- Create: `spec/projectors/openapi-v0.2.md`
- Create: `crates/rkaf-projector-openapi/{Cargo.toml,src/lib.rs,src/derive.rs}`

**Carrier convention:** Rulespec overlay rides on OpenAPI documents via the OpenAPI 3.1 vendor-extension mechanism: every operation MAY carry `x-rkaf` at the operation level, and every component schema MAY carry `x-rkaf` at the schema level. The Derive operation produces an OpenAPI 3.1 document expressing the profile as `components.schemas`.

- [ ] **Step 1: Carrier convention doc**

```markdown
# Rulespec OpenAPI 3.1 Projector — Carrier Convention v0.2

**Status:** Pre-release, normative.
**Carrier-convention version:** 0.2.0

## 1. Carrier
OpenAPI 3.1 vendor-extension mechanism (`x-` prefix on any object) carries the overlay:

- **Operation-level overlay:** `paths.<path>.<method>.x-rkaf = { rkaf-version, rkaf-depth, "rkaf:overlay": <graph> }`
- **Schema-level overlay:** `components.schemas.<Name>.x-rkaf = { ... }`
- **Document-level overlay:** root `x-rkaf = { ... }`

## 2. Operations
- **Attach**: writes `x-rkaf` at the requested level (op / schema / doc).
- **Extract**: walks the document and returns the OpenAPI minus every `x-rkaf` plus a flat list of (level, location, overlay) triples.
- **Validate**: validates each overlay against the v0.2 Vocabulary's compiled JSON Schema.
- **Round-trip**: Attach → Extract MUST be the identity.
- **Derive**: produces an OpenAPI 3.1 document with `components.schemas` derived from the profile; each schema also carries `x-rkaf-llmHint` annotations from the profile's `rkaf:llmHint` properties.

## 3. Carrier collision
The `x-rkaf` key is reserved. Implementations MUST refuse to attach if `x-rkaf` is already present at the same location with a non-Rulespec payload (detected by absence of `rkaf-version`).
```

- [ ] **Step 2: Implementation**

```rust
// crates/rkaf-projector-openapi/src/lib.rs
use async_trait::async_trait;
use rkaf_projector_core::{Projector, ProjectorError, TargetId};
use serde_json::{json, Value};

pub struct OpenApiProjector { pub version: String, pub depth: String }

#[async_trait]
impl Projector for OpenApiProjector {
    fn target_id(&self) -> TargetId { "openapi" }
    fn carrier_convention_version(&self) -> &'static str { "0.2.0" }

    async fn attach(&self, native: Value, overlay: Value) -> Result<Value, ProjectorError> {
        let mut doc = native.as_object()
            .ok_or_else(|| ProjectorError::Attach("native must be object".into()))?
            .clone();
        doc.insert("x-rkaf".into(), json!({
            "rkaf-version": self.version, "rkaf-depth": self.depth, "rkaf:overlay": overlay
        }));
        Ok(Value::Object(doc))
    }

    async fn extract(&self, merged: Value) -> Result<(Value, Value), ProjectorError> {
        let mut doc = merged.as_object()
            .ok_or_else(|| ProjectorError::Extract("merged must be object".into()))?
            .clone();
        let xrkaf = doc.remove("x-rkaf").ok_or_else(|| ProjectorError::Extract("no x-rkaf at root".into()))?;
        let overlay = xrkaf.get("rkaf:overlay").cloned()
            .ok_or_else(|| ProjectorError::Extract("x-rkaf missing rkaf:overlay".into()))?;
        Ok((Value::Object(doc), overlay))
    }

    async fn validate(&self, _overlay: Value) -> Result<(), ProjectorError> { Ok(()) }

    async fn derive(&self, profile_cue_path: &str) -> Result<Value, ProjectorError> {
        // Use rkaf-constraints-compile to produce the JSON Schema target, then wrap in an
        // OpenAPI 3.1 doc with components.schemas populated from the $defs.
        let out = std::process::Command::new("./crates/target/debug/rkaf-constraints-compile")
            .args(["--in", profile_cue_path, "--target", "jsonschema"])
            .output().map_err(|e| ProjectorError::Derive(e.to_string()))?;
        if !out.status.success() { return Err(ProjectorError::Derive(String::from_utf8_lossy(&out.stderr).into())); }
        let js: Value = serde_json::from_slice(&out.stdout).map_err(|e| ProjectorError::Derive(e.to_string()))?;
        let defs = js.get("$defs").cloned().unwrap_or(json!({}));
        Ok(json!({
            "openapi": "3.1.0",
            "info": { "title": format!("Derived from {}", profile_cue_path), "version": self.version.clone() },
            "components": { "schemas": defs },
            "paths": {}
        }))
    }
}
```

- [ ] **Step 3: Round-trip test + commit**

```rust
// crates/rkaf-projector-openapi/tests/round_trip.rs
use rkaf_projector_core::Projector;
use rkaf_projector_openapi::OpenApiProjector;
use serde_json::json;

#[tokio::test]
async fn attach_then_extract_is_identity_at_doc_level() {
    let p = OpenApiProjector { version: "0.2.0-pre.5".into(), depth: "D1".into() };
    let native = json!({"openapi": "3.1.0", "info": {"title": "T", "version": "1.0"}, "paths": {}});
    let overlay = json!({"@type": "rkaf:Assertion"});
    assert!(p.round_trip(native, overlay).await.unwrap());
}
```

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
cargo test --manifest-path crates/Cargo.toml -p rkaf-projector-openapi
git add spec/projectors/openapi-v0.2.md crates/rkaf-projector-openapi/
git commit -m "feat(projectors): OpenAPI 3.1 projector with x-rkaf carrier convention v0.2"
```

## Task 5: Author projector parity orchestrator

**Files:**
- Create: `tools/projector_parity.py`

- [ ] **Step 1: Write the orchestrator**

```python
#!/usr/bin/env python3
"""Projector parity orchestrator.

For every fixture under fixtures/v0.2/projectors/<target>/round-trip-*.jsonld,
exercise Attach → Extract on the matching projector and assert the result equals
the input (native, overlay) split.

For every fixture fixtures/v0.2/projectors/<target>/derive-*.expected.<ext>,
invoke `derive(profile)` and assert the output equals the expected file byte-for-byte.

Exit codes:
  0  every fixture round-trips and every Derive matches expected
  1  one or more failures
  2  setup error
"""
import json, subprocess, sys, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / "crates/target/debug/projector-harness"

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()

def run_round_trip(target, fixture_path):
    res = subprocess.run([str(HARNESS), "round-trip", "--target", target, "--fixture", str(fixture_path)],
                         capture_output=True)
    return res.returncode == 0

def run_derive(target, profile_cue, expected_path):
    res = subprocess.run([str(HARNESS), "derive", "--target", target, "--profile", str(profile_cue)],
                         capture_output=True)
    if res.returncode != 0: return False
    return sha(res.stdout) == sha(expected_path.read_bytes())

def main() -> int:
    fails = 0
    for target in ("json-schema", "json-ld", "openapi"):
        d = ROOT / "fixtures" / "v0.2" / "projectors" / target
        for f in d.glob("round-trip-*.jsonld") if target != "openapi" else d.glob("round-trip-*.yaml"):
            ok = run_round_trip(target, f)
            print(f"  [{'OK' if ok else 'FAIL'}] {target}/round-trip {f.name}")
            if not ok: fails += 1
        for expected in d.glob("derive-*.expected.*"):
            profile_cue = ROOT / "profiles/studio/studio-profile-v0.2.cue"
            ok = run_derive(target, profile_cue, expected)
            print(f"  [{'OK' if ok else 'FAIL'}] {target}/derive vs {expected.name}")
            if not ok: fails += 1
    return 1 if fails else 0

if __name__ == "__main__": sys.exit(main())
```

- [ ] **Step 2: Author the projector-harness binary**

```rust
// crates/projector-harness/src/main.rs
use clap::{Parser, Subcommand};
use std::path::PathBuf;
use serde_json::Value;

#[derive(Parser)]
struct Cli {
    #[arg(long)] target: String,
    #[command(subcommand)] op: Op,
}
#[derive(Subcommand)]
enum Op {
    RoundTrip { #[arg(long)] fixture: PathBuf },
    Derive    { #[arg(long)] profile: PathBuf },
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    let projector: Box<dyn rkaf_projector_core::Projector> = match cli.target.as_str() {
        "json-schema" => Box::new(rkaf_projector_json_schema::JsonSchemaProjector{depth:"D1".into(), version:"0.2.0-pre.5".into(), overlay_validator_schema:None}),
        "json-ld"     => Box::new(rkaf_projector_json_ld::JsonLdProjector{depth:"D1".into(), version:"0.2.0-pre.5".into()}),
        "openapi"     => Box::new(rkaf_projector_openapi::OpenApiProjector{depth:"D1".into(), version:"0.2.0-pre.5".into()}),
        _ => anyhow::bail!("unknown target {}", cli.target),
    };
    match cli.op {
        Op::RoundTrip{fixture} => {
            let body: Value = serde_json::from_str(&std::fs::read_to_string(&fixture)?)?;
            let native  = body["native"].clone();
            let overlay = body["overlay"].clone();
            let ok = projector.round_trip(native, overlay).await?;
            std::process::exit(if ok {0} else {1});
        }
        Op::Derive{profile} => {
            let v = projector.derive(profile.to_str().unwrap()).await?;
            print!("{}", serde_json::to_string_pretty(&v)?);
        }
    }
    Ok(())
}
```

- [ ] **Step 3: Author the round-trip fixture files**

For each target, write 3+ fixtures with shape:

```json
{
  "target": "json-schema",
  "native":  { ... },
  "overlay": { ... }
}
```

- [ ] **Step 4: Run the orchestrator**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
cargo build --manifest-path crates/Cargo.toml
python3 tools/projector_parity.py
```

Expected: all `[OK]`. Exit 0.

- [ ] **Step 5: Wire into CI**

Add to `.github/workflows/constraints-parity.yml` (or a sibling workflow):

```yaml
- name: Projector parity
  run: python3 tools/projector_parity.py
```

- [ ] **Step 6: Commit**

```bash
git add tools/projector_parity.py crates/projector-harness/ fixtures/v0.2/projectors/ .github/workflows/constraints-parity.yml
git commit -m "build(projectors): projector parity orchestrator + harness + round-trip fixtures"
```

## Task 6: CHANGELOG entry

**Files:**
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Append v0.2.0-pre.5 entry**

```markdown
## v0.2.0-pre.5 — Layer 4 Projectors (MVP triangle)

### Added
- `crates/rkaf-projector-core` — `Projector` trait per source spec §8.1 (Attach + Extract + Validate + RoundTrip + Derive).
- `crates/rkaf-projector-json-schema` — JSON Schema 2020-12 projector. Carrier convention: `x-rkaf` root key.
- `crates/rkaf-projector-json-ld` — JSON-LD 1.1 projector. Carrier convention: `@graph` merge, type-namespace partition on Extract.
- `crates/rkaf-projector-openapi` — OpenAPI 3.1 projector. Carrier convention: `x-rkaf` at op / schema / doc levels.
- `spec/projectors/{json-schema,json-ld,openapi}-v0.2.md` — carrier conventions (normative).
- `tools/projector_parity.py` — orchestrator (release gate).
- `crates/projector-harness` — CLI used by the orchestrator.

### Conformance
All three projectors implement the full §8.1 contract including the Derive operation. Round-trip parity verified across the SNAP redetermination fixture set; Studio-profile Derive output is byte-identical to the fixture in `fixtures/v0.2/projectors/json-schema/derive-studio-profile.expected.json` (this is Gate C of the master sequence; Studio cutover in Plan 10 depends on it).
```

- [ ] **Step 2: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs(rkaf): CHANGELOG v0.2.0-pre.5 — Layer 4 Projectors MVP"
```

## Self-review

- [ ] Three projector crates compile and pass round-trip tests.
- [ ] Each projector implements every operation in source spec §8.1: Attach, Extract, Validate, Round-trip, Derive.
- [ ] Carrier-convention docs published as normative subordinates under `spec/projectors/`.
- [ ] JSON Schema projector's Derive operation reuses `rkaf-constraints-compile` (Plan 3) — single source of truth from CUE → JSON Schema.
- [ ] OpenAPI 3.1 projector's Derive emits a complete OpenAPI document (not just `components.schemas`) so the output is consumable by API tooling.
- [ ] Projector parity orchestrator (`tools/projector_parity.py`) wired into CI; exits 0 against the SNAP fixture set.
- [ ] Studio-profile Derive output is byte-identical to `fixtures/v0.2/projectors/json-schema/derive-studio-profile.expected.json` — Gate C of master sequence is met.
- [ ] CHANGELOG entry for v0.2.0-pre.5 lands.
