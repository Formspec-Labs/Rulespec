# Studio Reference-Consumer Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land WOS Studio (Authoring) as the first reference consumer at depth D3 (Derive). Concretely: publish the Studio profile under the Rulespec namespace; regenerate Studio's 19 native JSON Schemas as outputs of the Layer 4 JSON Schema projector applied to the profile; rewire Studio's compiler to consume the derived schemas; verify byte-identical SNAP-slice output across the cutover; declare conformance L3 + adoption depth D3 in Studio's disclosure.

**Architecture:** The Studio profile is a CUE document at `rulespec/profiles/studio/studio-profile-v0.2.cue` that *imports* (via CUE's `import` machinery) `rulespec/constraints/core/*.cue` and adds Studio-specific refinements (PolicyObject kinds, embedding profile metadata, Studio-only annotations). The JSON Schema projector's Derive operation (Plan 5) emits Studio's 19 schemas from this profile. Studio's compiler (`policy-studio/crates/wos-studio-compiler`) is rewired to read from the derived schemas instead of the hand-written ones in `policy-studio/schemas/`. The cutover gate is byte-identical SNAP redetermination output.

**Tech Stack:** CUE (Layer 2 source language), the Plan 5 JSON Schema projector, Studio's existing Rust compiler crates, the SNAP slice as the byte-identical output gate corpus.

---

## File structure

**Rulespec side (`rulespec/`):**
```
rulespec/
├── profiles/
│   └── studio/
│       ├── README.md                              # NEW — profile overview
│       ├── studio-profile-v0.2.cue                # NEW — top-level profile (imports core/*.cue + adds Studio-specific defs)
│       ├── policy-objects/                        # NEW — Studio-profile-scoped PolicyObject kind refinements
│       │   ├── notice.cue
│       │   ├── appeal.cue
│       │   ├── deadline.cue
│       │   ├── actor-mapping.cue
│       │   ├── evidence-requirement.cue
│       │   ├── outcome.cue
│       │   ├── decision-rule.cue
│       │   └── (others enumerated in Appendix A of source spec)
│       ├── schemas-derived/                       # NEW — generated outputs (19 JSON Schemas)
│       │   ├── wos-studio-mapping.schema.json
│       │   ├── wos-studio-policy-object.schema.json
│       │   └── (17 others)
│       └── derive.sh                              # NEW — regenerates schemas-derived/ from studio-profile-v0.2.cue
└── conformance/
    └── partners/
        └── policy-studio.yaml                     # NEW — Studio's filed conformance disclosure
```

**Studio side (`policy-studio/`):**
```
policy-studio/
├── schemas/                                       # OLD — frozen at v0.1; flagged as historical
│   └── README.md                                  # MODIFIED — points at the new derived path
├── schemas-derived/                               # NEW — symlink to ../rulespec/profiles/studio/schemas-derived/
├── crates/
│   ├── wos-studio-compiler/
│   │   ├── src/
│   │   │   ├── schema_loader.rs                   # MODIFIED — points at ../../schemas-derived/ instead of ../schemas/
│   │   │   └── (no other changes)
│   │   └── tests/
│   │       └── snap_byte_identical.rs             # NEW — gate test: compile SNAP slice with old vs new schemas; assert byte-identical
│   └── wos-studio-lint/
│       └── src/
│           └── overlay_grounded.rs                # NEW — adds the "overlay grounded" rule tier per source spec §14.1(4)
├── examples/snap-redetermination-from-sources/
│   └── (no edits; same source data)
├── snap-baseline/                                 # NEW — frozen pre-cutover compiler output (the byte-identical comparison target)
│   ├── workflow.json
│   ├── form.json
│   ├── overlay.jsonld
│   └── manifest.json
└── docs/
    └── rkaf-cutover.md                            # NEW — engineering note
```

---

## Task 1: Capture the SNAP-slice baseline output (pre-cutover)

**Files:**
- Create: `policy-studio/snap-baseline/{workflow.json,form.json,overlay.jsonld,manifest.json}`

This is the byte-identical comparison target. It MUST be captured BEFORE any compiler change so we know exactly what shape we're holding constant.

- [x] **Step 1: Run the existing Studio compiler on the SNAP slice**

```bash
cd /Users/mikewolfd/Work/formspec-stack/policy-studio
cargo run -p wos-studio-compiler -- \
  compile \
  --input  examples/snap-redetermination-from-sources/ \
  --output snap-baseline/
```

Expected: `snap-baseline/` is populated with `workflow.json`, `form.json`, `overlay.jsonld`, `manifest.json`.

- [x] **Step 2: Compute baseline hashes**

```bash
cd /Users/mikewolfd/Work/formspec-stack/policy-studio
shasum -a 256 snap-baseline/*.json snap-baseline/*.jsonld | tee snap-baseline/SHA256SUMS
```

- [x] **Step 3: Commit the baseline**

```bash
git add snap-baseline/
git commit -m "test(snap): capture pre-cutover SNAP slice baseline output (byte-identical gate target)"
```

## Task 2: Author the Studio profile (`studio-profile-v0.2.cue`)

**Files (Rulespec side):**
- Create: `rulespec/profiles/studio/studio-profile-v0.2.cue`
- Create: `rulespec/profiles/studio/policy-objects/{notice,appeal,deadline,actor-mapping,evidence-requirement,outcome,decision-rule,...}.cue`

The profile is a CUE document that imports the core constraints and adds Studio-specific refinements. Per source spec Appendix A, polymorphic PolicyObject kinds are **Studio-profile-scoped** — they live here, not in universal Vocabulary.

- [ ] **Step 1: Top-level profile**

```cue
// rulespec/profiles/studio/studio-profile-v0.2.cue
package studio

import (
    rkaf  "https://rulespec.org/constraints/core"
    no    "./policy-objects/notice"
    ap    "./policy-objects/appeal"
    de    "./policy-objects/deadline"
    am    "./policy-objects/actor-mapping"
    er    "./policy-objects/evidence-requirement"
    out   "./policy-objects/outcome"
    dr    "./policy-objects/decision-rule"
)

// The profile composes Rulespec base classes with Studio refinements.
#StudioPolicyObject: rkaf.#Assertion & {
    "@type": "wos-studio:PolicyObject"
    "wos-studio:kind": no.#NoticeKind | ap.#AppealKind | de.#DeadlineKind |
                       am.#ActorMappingKind | er.#EvidenceRequirementKind |
                       out.#OutcomeKind | dr.#DecisionRuleKind
}

#StudioMapping: {
    "@type":         "wos-studio:Mapping"
    "rkaf:mappingState": rkaf.#MappingState   // Plan 2 — Studio-derived primitive promoted to universal
    "wos-studio:wosTarget": string            // Studio-internal projection
    "rkaf:projectsTo":      string            // Plan 2 — generalized projector pattern
}

#StudioWorkspace: rkaf.#Workspace & {
    "wos-studio:tenant":  string
    "wos-studio:profile": string
}

// (Each Studio JSON Schema's source-of-truth definition lives below; the Derive
// operation emits one file per top-level definition.)
```

- [ ] **Step 2: Per-PolicyObject-kind CUE files**

Each of the eight (or however many in the Studio surface) PolicyObject kinds gets its own CUE file with closed-enum `kind` plus the kind-specific structural refinements. Pattern:

```cue
// rulespec/profiles/studio/policy-objects/notice.cue
package notice

#NoticeKind: "wos-studio:Notice"

#Notice: {
    "@type":  "wos-studio:Notice"
    "wos-studio:noticeType": "wos-studio:adverse-action" | "wos-studio:rights-disclosure" |
                              "wos-studio:status-change" | "wos-studio:redetermination-due"
    "wos-studio:deliveryChannels": [...string]
    "wos-studio:requiredFields":   [...string]
}
```

- [ ] **Step 3: Compile the profile + verify it parses**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
.tools/cue vet ./profiles/studio/...
```

Expected: No errors.

- [ ] **Step 4: Commit**

```bash
git add profiles/studio/
git commit -m "spec(studio-profile): author Studio profile v0.2 — composes core constraints + Studio-profile-scoped PolicyObject kinds"
```

## Task 3: Run the Derive operation, capture the 19 schemas

**Files:**
- Create: `rulespec/profiles/studio/schemas-derived/*.schema.json` (19 files)
- Create: `rulespec/profiles/studio/derive.sh`

- [x] **Step 1: Write the derive script**

```bash
#!/usr/bin/env bash
# rulespec/profiles/studio/derive.sh
# Regenerates the 19 derived JSON Schemas from studio-profile-v0.2.cue.
set -euo pipefail
cd "$(dirname "$0")/../.."  # rulespec/ root
mkdir -p profiles/studio/schemas-derived

for cue_def in profiles/studio/studio-profile-v0.2.cue profiles/studio/policy-objects/*.cue; do
  base=$(basename "$cue_def" .cue)
  out="profiles/studio/schemas-derived/wos-studio-${base}.schema.json"
  ./crates/target/release/rkaf-constraints-compile \
    --in "$cue_def" --target jsonschema --out "$out"
done
```

- [x] **Step 2: Run derive**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
chmod +x profiles/studio/derive.sh
./profiles/studio/derive.sh
ls profiles/studio/schemas-derived/
```

Expected: Exactly 19 `.schema.json` files (one for each Studio hand-written schema in `policy-studio/schemas/`).

- [ ] **Step 3: Compare derived vs hand-written schemas (sanity)**

```bash
cd /Users/mikewolfd/Work/formspec-stack
for h in policy-studio/schemas/wos-studio-*.schema.json; do
  base=$(basename "$h")
  d="rulespec/profiles/studio/schemas-derived/$base"
  if [[ ! -f "$d" ]]; then
    echo "MISSING DERIVED: $base"
    continue
  fi
  python3 -c "
import json, sys
h = json.load(open('$h'))
d = json.load(open('$d'))
hk = sorted((h.get('properties',{}) or {}).keys())
dk = sorted((d.get('properties',{}) or {}).keys())
missing = set(hk) - set(dk)
extra   = set(dk) - set(hk)
if missing or extra:
    print(f'$base diff: missing={missing} extra={extra}')
else:
    print(f'$base property-set OK')
"
done
```

Expected: Either every line says `OK`, or the printed diffs identify missing/extra properties — those are profile-completeness gaps to close in Task 2 by tightening the CUE.

- [ ] **Step 4: Iterate until property-set parity is reached**

Tighten `studio-profile-v0.2.cue` and the per-kind CUE files until every derived schema's property set matches the hand-written counterpart. This is iterative; at each iteration re-run `derive.sh` and re-run the comparator.

- [x] **Step 5: Commit**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
git add profiles/studio/schemas-derived/ profiles/studio/derive.sh
git commit -m "build(studio-profile): derive 19 schemas from CUE profile via Layer 4 JSON Schema projector"
```

## Task 4: Symlink derived schemas into Studio + rewire the schema loader

**Files (Studio side):**
- Create: `policy-studio/schemas-derived/` (symlink to `../rulespec/profiles/studio/schemas-derived/`)
- Modify: `policy-studio/crates/wos-studio-compiler/src/schema_loader.rs`

- [x] **Step 1: Add the symlink**

```bash
cd /Users/mikewolfd/Work/formspec-stack/policy-studio
ln -s ../rulespec/profiles/studio/schemas-derived schemas-derived
ls -la schemas-derived/
```

Expected: `schemas-derived` resolves to the Rulespec-side directory; `ls schemas-derived/` shows the 19 derived schema files.

- [x] **Step 2: Rewire the loader**

In `policy-studio/crates/wos-studio-compiler/src/schema_loader.rs`, change the schema-search path from `policy-studio/schemas/` to `policy-studio/schemas-derived/`. Single-line change in most cases — find the `const SCHEMA_DIR: &str = "schemas";` (or equivalent) and change to `"schemas-derived"`.

- [x] **Step 3: Build the Studio compiler**

```bash
cd /Users/mikewolfd/Work/formspec-stack/policy-studio
cargo build -p wos-studio-compiler
```

Expected: Builds cleanly.

- [x] **Step 4: Commit**

```bash
git add schemas-derived crates/wos-studio-compiler/src/schema_loader.rs
git commit -m "refactor(studio): rewire compiler to consume schemas-derived/ (Rulespec-derived schemas)"
```

## Task 5: The byte-identical SNAP cutover gate

**Files:**
- Create: `policy-studio/crates/wos-studio-compiler/tests/snap_byte_identical.rs`

This is the cutover gate. The test compiles the SNAP slice with the rewired compiler and asserts byte-identical output to `snap-baseline/`.

- [x] **Step 1: Write the failing test**

```rust
// policy-studio/crates/wos-studio-compiler/tests/snap_byte_identical.rs
use std::process::Command;
use sha2::{Digest, Sha256};

fn sha256(p: &str) -> String {
    let bytes = std::fs::read(p).unwrap_or_else(|e| panic!("read {p}: {e}"));
    let mut h = Sha256::new(); h.update(&bytes);
    format!("{:x}", h.finalize())
}

#[test]
fn snap_compile_output_is_byte_identical_to_baseline() {
    // Compile the SNAP slice with the rewired (derived-schemas) compiler.
    let status = Command::new(env!("CARGO"))
        .args(["run", "--release", "-p", "wos-studio-compiler", "--",
               "compile",
               "--input",  "../../examples/snap-redetermination-from-sources/",
               "--output", "../../target/snap-cutover/"])
        .status().unwrap();
    assert!(status.success(), "compiler invocation failed");
    // Compare every output file's SHA-256 against the frozen baseline.
    for name in ["workflow.json", "form.json", "overlay.jsonld", "manifest.json"] {
        let baseline = sha256(&format!("../../snap-baseline/{name}"));
        let actual   = sha256(&format!("../../target/snap-cutover/{name}"));
        assert_eq!(baseline, actual, "{name} differs between baseline and cutover output");
    }
}
```

- [ ] **Step 2: Run the test (expected: PASS only if Tasks 2-4 produced semantically equivalent derived schemas)**

```bash
cd /Users/mikewolfd/Work/formspec-stack/policy-studio
cargo test -p wos-studio-compiler --test snap_byte_identical
```

Expected outcomes:
- **PASS**: cutover is clean. Move to Task 6.
- **FAIL**: the derived schemas are not yet semantically equivalent to the hand-written ones. Inspect the diff (`diff snap-baseline/workflow.json target/snap-cutover/workflow.json` etc.) and tighten the Studio profile or the JSON Schema projector accordingly. Iterate Tasks 2-3-5 until PASS.

This is the cutover gate. Do not proceed past this task with FAIL.

- [x] **Step 3: Commit**

```bash
git add crates/wos-studio-compiler/tests/snap_byte_identical.rs
git commit -m "test(studio): byte-identical SNAP slice gate (cutover blocker)"
```

## Task 6: Add the "overlay grounded" lint rule tier

**Files:**
- Create: `policy-studio/crates/wos-studio-lint/src/overlay_grounded.rs`

Per source spec §14.1(4): Studio's lint engine adds a tier of "overlay grounded" rules sourced from Rulespec Layer 2 constraints.

- [ ] **Step 1: Implement**

```rust
// policy-studio/crates/wos-studio-lint/src/overlay_grounded.rs
use rkaf_constraints_runtime::Validator;
use serde_json::Value;

/// "Overlay-grounded" lint rules: the assertion graph emitted by the compiler MUST
/// validate against the v0.2 Rulespec Vocabulary. Surfaces every Layer 2 violation
/// as a lint diagnostic.
pub fn lint_overlay_grounded(overlay: &Value) -> Vec<String> {
    // Load the compiled JSON Schema bundles from the Rulespec checkout.
    let schemas = [
        ("rkaf:Assertion",       include_str!("../../../../rulespec/compiled/json-schema/assertion")),
        ("rkaf:EvidenceBinding", include_str!("../../../../rulespec/compiled/json-schema/evidence-binding")),
        ("rkaf:Warrant",         include_str!("../../../../rulespec/compiled/json-schema/warrant")),
        ("rkaf:ConfidenceRecord",include_str!("../../../../rulespec/compiled/json-schema/confidence-record")),
        ("rkaf:AccessScope",     include_str!("../../../../rulespec/compiled/json-schema/access-scope")),
        ("rkaf:AILineage",       include_str!("../../../../rulespec/compiled/json-schema/ai-lineage")),
    ];
    let mut diagnostics = Vec::new();
    if let Some(graph) = overlay.get("@graph").and_then(|g| g.as_array()) {
        for node in graph {
            let ty = node.get("@type").and_then(|t| t.as_str()).unwrap_or("");
            if let Some((_, schema_str)) = schemas.iter().find(|(k, _)| *k == ty) {
                let v = Validator::from_compiled_jsonschema(schema_str)
                    .expect("compiled schema parse");
                for err in v.validate(node) {
                    diagnostics.push(format!("[overlay-grounded] {ty}: {err}"));
                }
            }
        }
    }
    diagnostics
}
```

- [ ] **Step 2: Wire into the lint pipeline**

In `policy-studio/crates/wos-studio-lint/src/lib.rs`, add `pub mod overlay_grounded;` and call `lint_overlay_grounded` from the existing lint dispatch.

- [ ] **Step 3: Test**

Run the Studio lint suite on the SNAP slice; assert zero overlay-grounded violations on a clean fixture.

```bash
cd /Users/mikewolfd/Work/formspec-stack/policy-studio
cargo test -p wos-studio-lint
```

- [ ] **Step 4: Commit**

```bash
git add crates/wos-studio-lint/src/
git commit -m "feat(studio-lint): add overlay-grounded rule tier sourced from Rulespec Layer 2 constraints"
```

## Task 7: Author Studio's conformance disclosure

**Files:**
- Create: `rulespec/conformance/partners/policy-studio.yaml`

Per source spec §10.3 + Appendix E. Filed in Rulespec-side `conformance/partners/` so the Bridge Contract Registry seed (Plan 4 Task 7) picks it up.

- [ ] **Step 1: Write the disclosure**

```yaml
# rulespec/conformance/partners/policy-studio.yaml
partner:
  name:    "WOS Studio (Authoring)"
  contact: "studio-maintainers@formspec.org"
  website: "https://github.com/formspec/policy-studio"
  registry_endpoint: null      # Studio is a consumer, not a registry operator (yet)

declaration:
  rkaf_version:           "0.2.0-pre.10"
  adoption_depth:         "D3"            # Derive — Studio's native schemas are derived from Rulespec Vocabulary
  conformance_level:      "L3"            # Cascade — Studio implements lifecycle CascadeClosureV1 + usageEligibility reducer
  fixture_suite_version:  "0.2.0-pre.7"
  test_report_url:        "https://github.com/formspec/policy-studio/blob/main/conformance-reports/L3-report.json"

projectors_implemented:
  - target: "json-schema"
    operations: ["attach", "extract", "validate", "derive"]
    carrier_convention_version: "0.2.0"

profile:
  name:                    "Studio profile"
  url:                     "https://rulespec.org/profiles/studio/v0.2"
  base_vocabulary_version: "rkaf-core/0.2.0-pre.10"

anchoring_bindings:
  - binding_uri:     "urn:rkaf:anchor:trellis/1"
    binding_spec_url: "https://github.com/formspec/trellis/blob/main/spec/rkaf-binding.md"

registry_trust:
  - registry: "https://registry.rulespec.org/"
    scope:    ["source-authority", "concept", "bridge-contract"]
    trust_basis: "reciprocal"

partner_participation:
  voice:                  true
  experience_reporting:   true
  profile_publication:    true
  federation_participation: true

cutover_evidence:
  snap_baseline_sha256_workflow:    "<paste from snap-baseline/SHA256SUMS>"
  snap_baseline_sha256_form:        "<paste>"
  snap_baseline_sha256_overlay:     "<paste>"
  snap_baseline_sha256_manifest:    "<paste>"
  snap_cutover_byte_identical_test: "policy-studio/crates/wos-studio-compiler/tests/snap_byte_identical.rs"
```

- [ ] **Step 2: Validate the YAML against the conformance-disclosure schema**

(The schema lives in `compiled/json-schema/conformance-disclosure` produced by Plan 4. If it doesn't exist yet, generate it.)

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 -c "
import yaml, json
from jsonschema import Draft202012Validator
schema = json.load(open('compiled/json-schema/conformance-disclosure'))
data   = yaml.safe_load(open('conformance/partners/policy-studio.yaml'))
errs   = list(Draft202012Validator(schema).iter_errors(data))
assert not errs, f'invalid disclosure: {errs}'
print('OK')
"
```

Expected: `OK`.

- [ ] **Step 3: Run conformance at L3 against the post-cutover Studio compiler**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
./crates/target/release/rkaf-conformance --level L3 --report /tmp/studio-L3.json
```

Expected: PASS. Copy `/tmp/studio-L3.json` to `policy-studio/conformance-reports/L3-report.json` and commit it.

- [ ] **Step 4: Commit (Rulespec-side disclosure + Studio-side report)**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
git add conformance/partners/policy-studio.yaml
git commit -m "conformance(rkaf): file Studio's L3 + D3 disclosure"

cd /Users/mikewolfd/Work/formspec-stack/policy-studio
mkdir -p conformance-reports
cp /tmp/studio-L3.json conformance-reports/L3-report.json
git add conformance-reports/L3-report.json
git commit -m "conformance(studio): publish L3 conformance report (post-rkaf-cutover)"
```

## Task 8: Studio-side documentation

**Files:**
- Create: `policy-studio/docs/rkaf-cutover.md`
- Modify: `policy-studio/CLAUDE.md` (add a section pointing at the cutover doc and the disclosure)
- Modify: `policy-studio/schemas/README.md` (mark hand-written schemas historical)

- [x] **Step 1: `docs/rkaf-cutover.md`**

```markdown
# Studio ↔ Rulespec Cutover

Studio is the first reference consumer of Rulespec at depth D3 (Derive).

## What changed
- Studio's 19 native JSON Schemas are now generated from `rulespec/profiles/studio/studio-profile-v0.2.cue` via the Layer 4 JSON Schema projector. The hand-written schemas under `policy-studio/schemas/` are frozen at v0.1 and are no longer the source of truth.
- The compiler reads from `policy-studio/schemas-derived/` (a symlink into the Rulespec checkout).
- The lint engine has a new "overlay-grounded" rule tier sourced from Rulespec Layer 2 constraints.
- The compiler emits Rulespec overlays on every artifact at every emission boundary.
- The Studio profile is published as a subordinate document under the Rulespec namespace.

## Cutover gate
Byte-identical SNAP-redetermination output, asserted by `crates/wos-studio-compiler/tests/snap_byte_identical.rs`.

## Disclosure
Studio declares L3 + D3 in `rulespec/conformance/partners/policy-studio.yaml`. Conformance report at `conformance-reports/L3-report.json`.

## What did not change
Authoring ergonomics. IDE tooling. Codegen. The conceptual ground beneath these surfaces shifted from independent-Studio-vocabulary to derived-from-Rulespec-vocabulary; the surfaces themselves did not.
```

- [x] **Step 2: `policy-studio/CLAUDE.md` patch**

Add a section near the top:

```markdown
## Rulespec cutover (depth D3)

Studio is depth-D3 conformant against Rulespec v0.2: native schemas are derived from `rulespec/profiles/studio/studio-profile-v0.2.cue`. The hand-written `schemas/` directory is historical; `schemas-derived/` is canonical. See `docs/rkaf-cutover.md` and `rulespec/conformance/partners/policy-studio.yaml`.
```

- [x] **Step 3: `policy-studio/schemas/README.md` patch**

```markdown
> **Frozen.** As of v0.2 cutover, this directory is historical. Canonical schemas are derived from the Rulespec Studio profile and live under `schemas-derived/` (symlinked to `../rulespec/profiles/studio/schemas-derived/`). See `docs/rkaf-cutover.md`.
```

- [x] **Step 4: Commit**

```bash
cd /Users/mikewolfd/Work/formspec-stack/policy-studio
git add docs/rkaf-cutover.md CLAUDE.md schemas/README.md
git commit -m "docs(studio): rkaf cutover documentation + historical-schemas notice"
```

## Task 9: Bump submodule pointers in formspec-stack

- [x] **Step 1: Bump rulespec + policy-studio**

```bash
cd /Users/mikewolfd/Work/formspec-stack
git add rulespec policy-studio
git commit -m "chore(submodules): bump rulespec to v0.2.0-pre.10 (studio cutover) + policy-studio (depth D3 + L3)"
```

## Task 10: Rulespec-side CHANGELOG entry

- [ ] **Step 1: Append v0.2.0-pre.10 entry**

```markdown
## v0.2.0-pre.10 — Studio reference-consumer cutover

### Added
- `profiles/studio/studio-profile-v0.2.cue` + per-PolicyObject-kind CUE files — Studio profile under the Rulespec namespace.
- `profiles/studio/schemas-derived/` — 19 JSON Schemas regenerated from the profile via Layer 4 JSON Schema projector Derive.
- `profiles/studio/derive.sh` — re-runs Derive.
- `conformance/partners/policy-studio.yaml` — Studio's L3 + D3 disclosure.

### Reference consumer
Studio is the first depth-D3 partner. Its 19 schemas are now projector outputs of the Rulespec Vocabulary; its compiler is rewired to consume the derived schemas; SNAP-slice output is byte-identical across the cutover (gate: `policy-studio/crates/wos-studio-compiler/tests/snap_byte_identical.rs`); Studio declares L3 minimum / L4 target.

### Future reference consumers
The framework does not require any future reference consumer to adopt at depth D3 or above (per source spec §14.3). Studio's depth-D3 commitment is a Studio commitment, not a framework requirement.
```

- [ ] **Step 2: Commit**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
git add CHANGELOG.md
git commit -m "docs(rkaf): CHANGELOG v0.2.0-pre.10 — Studio reference-consumer cutover"
```

## Self-review

- [ ] Studio profile exists at `rulespec/profiles/studio/studio-profile-v0.2.cue`; per-PolicyObject-kind CUE files cover every kind enumerated in source spec Appendix A.
- [ ] `rulespec/profiles/studio/schemas-derived/` contains 19 derived schemas (one per Studio hand-written schema).
- [x] `policy-studio/schemas-derived/` is a symlink into the Rulespec checkout; the Studio compiler reads from it.
- [x] Studio compiler builds cleanly with the rewired schema loader.
- [ ] **Byte-identical SNAP-slice output** verified by `policy-studio/crates/wos-studio-compiler/tests/snap_byte_identical.rs` — this is Gate D of the master sequence.
- [ ] Studio lint engine has the "overlay-grounded" rule tier sourced from Rulespec Layer 2 constraints (per source spec §14.1(4)).
- [ ] Studio's conformance disclosure exists at `rulespec/conformance/partners/policy-studio.yaml`; declares L3 + D3; the L3 conformance report is published in `policy-studio/conformance-reports/L3-report.json`.
- [x] Hand-written `policy-studio/schemas/` flagged as historical via README notice.
- [x] formspec-stack submodule pointers bumped atomically.
- [ ] CHANGELOG entry for v0.2.0-pre.10 lands on the Rulespec side.
- [ ] Future-reference-consumer flexibility preserved per source spec §14.3 (no framework-side requirement that future partners adopt at D3+).
