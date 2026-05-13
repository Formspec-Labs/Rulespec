# Formspec → Universal Data-Contract Framework — Implementation-Side Proposal

| | |
|---|---|
| **Date** | 2026-05-13 |
| **Companion (strategic / spec)** | `PKAF/thoughts/specs/2026-05-12-pkaf-as-public-schema-interop-framework.md` |
| **Status** | Draft proposal — engineering scoping only. Reversible. Pre-1.0. |
| **Posture** | Greenfield-first. No migration shims. Form profile preserved as default; everything else is profile-gated. |
| **Audience** | Stack owner; formspec-stack maintainers. |

## Abstract

Formspec is structurally a **data-contract framework** — Definition / Bind / Shape / FEL / option sets / ontology binding / mappings / BridgeValidationResult / `@instance()` are domain-neutral. The form / UI assumptions are scoped bias, not architecture. This proposal grows Formspec implementation along seven axes so it natively expresses Rulespec (and any future non-form domain) — IRI-aware paths, entity-level disjunction, registry-backed cross-document references, constraint-null policy, relevance modes, an explicit profile system, and multi-target codegen. **Rulespec primitives do not bend.** Formspec accommodates.

Engineering scope is substantial but contained — one new fel-core path mode, one new evaluator config struct, one new `formspec-codegen` crate, one new `formspec-resolver` crate, profile-gated branches in three existing evaluator phases, and retirement of the just-shipped CUE compiler in `PKAF/tools/`. Total estimated effort: ~6,500–8,500 LOC across Rust + ~1,500–2,000 LOC TS + ~300 LOC Python, plus deletes. Critical path runs ~3 weeks single-threaded; ~1.5 weeks with parallelism.

The form profile remains the default. `formspec-engine`, `formspec-studio`, `case-portal`, `formspec-webcomponent` continue working unchanged.

## 1. Current implementation map

The Formspec runtime is **logic-in-Rust, surfaced via WASM and Python** — TypeScript is glue. (Confirmed: `formspec/CLAUDE.md` "Logic ownership: Rust/WASM first".)

### 1.1 Rust workspace — `formspec/crates/`

| Crate | Role | LOC (src) |
|---|---|---|
| `fel-core` (sibling, `formspec-stack/fel-core/`) | FEL grammar, AST, evaluator, `Environment` trait, types | ~12k |
| `formspec-core` | Assembler, definition-items walker, schema validator, FEL analysis, option sets, registry client | ~15k |
| `formspec-eval` | 4-phase batch evaluator (rebuild → recalculate → revalidate → NRB) | ~10k |
| `formspec-lint` | Static lint rules | ~6k |
| `formspec-changeset` | Definition diff/migration | ~3k |
| `formspec-wasm` | WASM bindings (`evaluateDefinition`, `evalFEL`, etc.) | ~5k |
| `formspec-py` | PyO3 bindings | ~3k |
| `formspec-signature-*`, `formspec-canonical`, `formspec-cross-stack-fixture-harness` | Adjacent | varies |

### 1.2 Pipeline shape — `formspec-eval`

`evaluate_definition_full_with_instances_and_context` (`formspec/crates/formspec-eval/src/pipeline.rs:102`) is the single entry; six thin wrappers above it (`pipeline.rs:17–99`). Pipeline:

1. **Rebuild** — `rebuild::rebuild_item_tree` (`formspec/crates/formspec-eval/src/rebuild/item_tree.rs`), `seed_initial_values`, `expand_repeat_instances`, `apply_wildcard_binds`.
2. **Recalculate** — `recalculate::recalculate` (`formspec/crates/formspec-eval/src/recalculate/mod.rs:1–460`): relevance/required/readonly/variables/calculate.
3. **Revalidate** — `revalidate::revalidate` (`formspec/crates/formspec-eval/src/revalidate/mod.rs:1–623`): required, type, constraint, shapes, extensions.
4. **NRB** — `nrb::apply_nrb` (`formspec/crates/formspec-eval/src/nrb.rs`).

Cross-cutting:

- **Path resolution** — `convert::resolve_value_by_path` (`formspec/crates/formspec-eval/src/convert.rs:8–45`). Dotted + `rows[N]` bracket-index. **No IRI awareness, no JSON-LD `@id` / `@type`, no graph traversal.**
- **Wildcard paths** — `to_wildcard_path` + `strip_indices` (`formspec/crates/formspec-eval/src/types/paths.rs:53–86`). Form-tree-shaped.
- **FEL `@instance('name')`** — set per evaluation via `EvalContext.instances: HashMap<String, Value>` (`formspec/crates/formspec-eval/src/recalculate/mod.rs:44`, `formspec/crates/formspec-eval/src/revalidate/env.rs:65`). Eagerly materialized; resolver is `HashMap::get`. Sized for ~5–10 named instances.

### 1.3 FEL environment seam — `fel-core/src/evaluator/core.rs:25–76`

The `Environment` trait is the **profile injection point already**. 13 methods: `resolve_field`, `resolve_context`, `mip_*`, `repeat_*`, `current_date/datetime`, `locale`, `runtime_meta`. `FormspecEnvironment` (`fel-core/src/environment.rs:69–87`) is the concrete impl: `HashMap<String, Value>` field data, `HashMap<String, Value>` instances, MIP states, repeat context. **This is where graph-profile resolution plugs in cleanly.**

### 1.4 Shape composition — `formspec/crates/formspec-eval/src/revalidate/shapes.rs`

Already supports `and` / `or` / `not` / `xone` (line `:351`). `xone` (`shapes.rs:350–369`) is exactly the SHACL-shape primitive Rulespec needs for `Assertion = withEvidence | withoutEvidence` at the entity level — **but it's a Shape, not a Definition primitive.** Today a Definition is a tree of Items with binds; entity-level disjunction has no Definition-side surface.

### 1.5 Constraint null policy — current behavior

`formspec/crates/formspec-eval/src/revalidate/items.rs:173–225`: "A constraint that cannot be evaluated due to null inputs is not considered violated." Hardcoded `pass`. Compare with Rulespec evidence-binding semantics (`PKAF/constraints/core/evidence-binding.cue`) — a conditional branch that is *silently absent* (rather than null-input) must FAIL, not pass. **This is a per-Definition / per-Shape policy switch, not a flip.**

### 1.6 Relevance (NRB) — current behavior

`formspec/crates/formspec-eval/src/revalidate/items.rs:37–39`: non-relevant items skip validation entirely. Same for shapes (`shapes.rs:43–47`). Form-shaped: branches the user can't see don't validate. Graph-shaped: every node in the graph validates regardless of UI visibility. **Two modes.**

### 1.7 Schemas → TS types pipeline

`formspec/packages/formspec-types/scripts/generate-types.mjs` runs `json-schema-to-typescript` over `formspec/schemas/*.schema.json` into `formspec/packages/formspec-types/src/generated/`. **One-way, one-target.** No Rust struct emission, no validator emission, no SHACL emission, no OpenAPI emission. The schemas themselves are hand-authored JSON Schema 2020-12.

### 1.8 Just-shipped CUE compiler — `PKAF/tools/constraints_compile.py`

850 LOC Python compiler. Source: `PKAF/constraints/{core,adversarial,ai-extraction}/*.cue`. Targets: JSON Schema / Rust / TypeScript / SHACL / CUE / Rego. Hand-rolls a partial CUE-pattern parser (`PKAF/tools/constraints_compile.py:36`: *"This is NOT a full CUE parser — it handles the regular patterns Rulespec uses."*). Outputs in `PKAF/compiled/{json-schema,rust,typescript,shacl,rego,cue}/`. Built specifically because Formspec couldn't express what Rulespec needed. **This is the artifact that retires when Formspec generalizes.**

## 2. The decision under evaluation

**Two languages, one framework.** FEL (expression) + Formspec (schema/contract). Forms, Rulespec, WOS step definitions, Trellis evidence-packet shapes, future domains — all profiles of one Definition language.

Cost: the seven gap items. Benefit: collapse a parallel toolchain (the CUE compiler), one mental model across the stack, one validator/codegen surface, one set of conformance tests, one extension point for partners.

## 3. Implementation changes per gap item

### 3.1 IRI-aware paths

**Today.** `$field.subfield` and `rows[N].field`. Parser: `formspec/crates/formspec-eval/src/convert.rs:48–61`, `fel-core/src/evaluator/core.rs` `Environment::resolve_field`.

**Needed.** First-class `@id`, `@type`, `rkaf:warrant` references. A JSON-LD-style path mode where segments may be CURIEs or IRIs and resolution walks a triple-graph, not an object tree.

**Where it changes.**

- `fel-core/src/lexer.rs` — accept `:` inside identifier segments under graph mode. Today, lexer treats `rkaf:warrant` as `rkaf` `:` `warrant`. Add a `PathMode::{ObjectTree, IriGraph}` enum at the lexer config level.
- `fel-core/src/ast.rs` — `FieldPath` already represents segments as `Vec<String>`. No AST change needed beyond allowing colons in segments. Path-mode flag lives on the parser context, not in AST nodes.
- `fel-core/src/parser.rs` — add CURIE recognition under graph mode (`prefix:local-name` as a single segment).
- `fel-core/src/evaluator/core.rs` — `Environment::resolve_field` already takes `&[String]`. Impl-level change only.
- `fel-core/src/environment.rs` — new alternate impl `GraphEnvironment` that resolves segments against an in-memory triple store (or a host-provided resolver — see §3.6).
- `formspec/crates/formspec-eval/src/convert.rs` — `resolve_value_by_path` becomes profile-aware: dotted + bracket-index for form profile; CURIE-aware traversal for graph profile.

**Public API change.** New `formspec_eval::PathMode` enum on `EvalContext`. Default `PathMode::ObjectTree`. Graph profile sets `PathMode::IriGraph`.

**LOC estimate.** ~400 Rust (lexer 60, parser 80, new env 200, convert 60) + ~80 fel-core tests + ~120 formspec-eval tests.

### 3.2 Entity-level disjunction as a Definition primitive

**Today.** Disjunction is a shape primitive (`xone`, `shapes.rs:350–369`). Definitions are Item trees; entity-level branching is expressed via per-field constraints and shape rules, never at the structural level.

**Needed.** A Definition node that says "this entity is one of these N variants" — the Rulespec `EvidenceBinding = withEvidence | withoutEvidence` pattern (`PKAF/constraints/core/evidence-binding.cue`).

**Two options:**

**(a) Promote `xone` from Shape to Item.** Add an `Item::Variant { variants: Vec<Item> }` node alongside the existing `Item::Field`, `Item::Group`, `Item::Repeat`. Rebuild walks variants and picks one based on a discriminator FEL expression. **Cost**: touches `rebuild/item_tree.rs` (~80 LOC), `recalculate/mod.rs` (~60 LOC for variant-active-only relevance), `revalidate/items.rs` (~40 LOC for variant gating), schema `definition.schema.json` (~30 LOC, new `variant` discriminator), TS types regen.

**(b) Disjunction-as-Shape, but wired into Definition structure via `targetVariant`.** Keep `xone`, add a Shape-mode flag that makes the *failing* branch suppress its bind-level validations (so the matching branch's binds validate, the other branch's don't). **Cost**: lower — ~60 LOC in `revalidate/`. **Drawback**: still a Shape, not a structural primitive. Codegen (§3.7) has to reconstruct entity variance from shape rules — exactly the painful reverse-engineering the CUE compiler had to do.

**Recommendation: (a).** Variant as a first-class Item kind. Worth the ~210 LOC because codegen drops out cleanly — a variant Item maps directly to a Rust `enum`, a TS discriminated union, a JSON Schema `oneOf`, a SHACL `sh:xone`. No reconstruction.

**LOC estimate.** ~250 Rust + ~100 schema + ~80 tests + ~50 TS types regen verification = ~480.

### 3.3 Graph-style cross-document references at scale

**Today.** `@instance('name')` eagerly materializes via `EvalContext.instances: HashMap<String, Value>` (`formspec/crates/formspec-eval/src/recalculate/mod.rs:44`). Sized for ~5–10 named secondary instances per Definition (locale tables, registry slices, posture declarations). Resolver is `HashMap::get`. **No lazy resolution, no IRI dereference, no caching, no LRU.**

**Needed.** Rulespec assertions reference Warrants (~10² per workspace), Source Fragments (~10³), Concepts (~10⁴). Eager materialization is wrong — most refs are never followed during a single evaluation. Needs a **resolver trait** the host supplies.

**Where it changes.**

- New crate **`formspec-resolver`** (~600 LOC). Exposes:

  ```rust
  pub trait InstanceResolver {
      fn resolve(&self, iri: &str) -> Option<Value>;
      fn resolve_batch(&self, iris: &[&str]) -> HashMap<String, Value>;
  }

  pub struct EagerHashMapResolver(HashMap<String, Value>);  // form profile default
  pub struct LruIriResolver<F> { fetch: F, cache: ... }     // graph profile
  pub struct CompositeResolver(Vec<Box<dyn InstanceResolver>>);  // chain
  ```

- `fel-core/src/environment.rs:69–87` — `FormspecEnvironment.instances: HashMap<...>` becomes `Box<dyn InstanceResolver>`. Form profile keeps the HashMap-backed impl; graph profile gets `LruIriResolver`. The existing `set_instance` API stays for the eager case; new `set_resolver` for graph.
- `fel-core/src/environment.rs:309–322` — `resolve_context("instance", Some(name), tail)` calls `self.instances.resolve(name)` instead of `self.instances.get(name)`. **Behavior change is invisible to FEL.**
- `formspec/crates/formspec-eval/src/recalculate/mod.rs:40–50` — accept `Box<dyn InstanceResolver>` alongside `HashMap`. Adapter wraps HashMap into eager resolver.

**Public API change.** New `formspec_eval::EvalContext::resolver: Option<Box<dyn InstanceResolver>>`. When present, supersedes `instances`. When absent, `instances` wraps into `EagerHashMapResolver`.

**LOC estimate.** ~600 (new crate) + ~80 fel-core changes + ~60 formspec-eval wiring + ~150 tests = ~890.

### 3.4 Constraint null-policy mode

**Today.** Hardcoded `pass` (`formspec/crates/formspec-eval/src/revalidate/items.rs:173–176`).

**Needed.** Per-Definition default + per-Bind / per-Shape override:

```jsonc
{ "$formspec": "1.0", "constraintNullPolicy": "fail", ... }
```

Or at the bind:

```jsonc
{ "path": "...", "constraint": "...", "constraintNullPolicy": "fail" }
```

**Where it changes.**

- `formspec/crates/formspec-eval/src/types/modes.rs` — new `ConstraintNullPolicy::{Pass, Fail}` enum. Same shape as `NrbMode`.
- `formspec/crates/formspec-eval/src/types/item_tree.rs` (`ItemInfo`) — new field `constraint_null_policy: Option<ConstraintNullPolicy>`.
- `formspec/crates/formspec-eval/src/rebuild/item_tree.rs` — read the policy from bind JSON when building items; inherit definition-level default when absent.
- `formspec/crates/formspec-eval/src/revalidate/items.rs:173–176` — gate the existing pass-on-null on `policy == Pass`. When `policy == Fail`, emit `CONSTRAINT_NULL_FAILED` validation result with `severity: error`.
- Same treatment in `revalidate/shapes.rs` for shape constraints.
- `formspec/schemas/definition.schema.json` — add top-level `constraintNullPolicy` (enum: `pass | fail`, default `pass`) + nested override at `binds[*].constraintNullPolicy`, `shapes[*].constraintNullPolicy`.

**LOC estimate.** ~120 Rust + ~50 schema + ~150 tests = ~320.

### 3.5 Relevance suppression mode

**Today.** Non-relevant items skip validation: `formspec/crates/formspec-eval/src/revalidate/items.rs:37–39`, `shapes.rs:43–47`. NRB modes (`Remove | Empty | Keep`) live in `types/modes.rs:1–24`.

**Needed.** `RelevanceMode::{Form, Graph}` orthogonal to NRB. In `Form` mode (default), non-relevant suppresses validation (today's behavior). In `Graph` mode, every node validates regardless of relevance — relevance still affects NRB output shaping but not validation gating.

**Where it changes.**

- `formspec/crates/formspec-eval/src/types/modes.rs` — new `RelevanceMode` enum.
- `formspec/crates/formspec-eval/src/types/evaluation.rs:55–66` (`EvalContext`) — new field `relevance_mode: RelevanceMode` (default `Form`).
- `formspec/crates/formspec-eval/src/revalidate/items.rs:36–39` — gate the relevance-skip on `relevance_mode == Form`.
- `formspec/crates/formspec-eval/src/revalidate/shapes.rs:43–47` — same.
- `formspec/schemas/definition.schema.json` — `relevanceMode` enum at top level (default `form`).

**LOC estimate.** ~80 Rust + ~30 schema + ~100 tests = ~210.

### 3.6 Profile system

**Today.** Implicit. Every code path assumes form shape: `rebuild_item_tree` expects `items` array; `convert::resolve_value_by_path` expects dotted/bracket paths; `EvalContext.instances` is a flat HashMap; relevance suppresses validation; constraint-null passes.

**Needed.** Explicit profile declaration. Profile selects defaults for the four mode switches (§3.1, §3.4, §3.5, §3.3) and selects which Definition AST shape is valid.

**Mechanism — opinionated.** Profile is a **closed enum** + a **config struct**:

```rust
// formspec/crates/formspec-eval/src/types/profile.rs (new)
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Profile {
    /// UI-driven intake. Default. Item tree, dotted paths, form-NRB, pass-on-null-constraint.
    Form,
    /// JSON-LD / IRI-graph contracts. Rulespec is the canonical consumer.
    Graph,
}

pub struct ProfileConfig {
    pub profile: Profile,
    pub path_mode: PathMode,                       // ObjectTree | IriGraph
    pub relevance_mode: RelevanceMode,             // Form | Graph
    pub constraint_null_policy: ConstraintNullPolicy,  // Pass | Fail
    pub resolver: Option<Box<dyn InstanceResolver>>,
}

impl ProfileConfig {
    pub fn form() -> Self { /* today's defaults */ }
    pub fn graph() -> Self { /* IRI paths, graph relevance, fail-on-null, registry resolver */ }
}
```

`EvalContext` gets a new field `pub profile_config: ProfileConfig` (default `ProfileConfig::form()`). **No new evaluator entry point required** — every `evaluate_definition_*` wrapper takes `&EvalContext`, and `ProfileConfig` rides inside it. Form-profile callers (formspec-engine, formspec-studio, case-portal) pass `EvalContext::default()` and get today's behavior verbatim.

At the Definition document level, `profile: "form" | "graph"` is an optional top-level key. When present, the assembler (`formspec-core/src/assembler.rs`) materializes a `ProfileConfig` matching that profile and threads it through.

**Why this shape, not a trait.** A trait-based "Profile" would force the entire evaluator pipeline to be generic-bounded — costly compile-time and code-complexity tax for two implementations. Closed enum + config struct is cheaper, more readable, and the closed-taxonomy posture (`.claude/user_profile.md`) calls for it.

**LOC estimate.** ~250 Rust (new module + EvalContext wiring) + ~80 schema (top-level `profile` key on Definition) + ~150 wiring across rebuild/recalculate/revalidate to honor `profile_config` = ~480.

### 3.7 Multi-target codegen

**Today.** Formspec has **multi-runtime evaluation parity** (Rust + WASM + Python all run the same evaluator). It does *not* have **codegen of types and validators in target languages**. The only schema → code path is `formspec/packages/formspec-types/scripts/generate-types.mjs` (one-shot JSON Schema → TypeScript via `json-schema-to-typescript`).

**Needed.** Definition AST → emitters for {Rust struct + validator, TypeScript types + validator, JSON Schema, SHACL shapes, OpenAPI fragment}. The CUE compiler we just shipped (`PKAF/tools/constraints_compile.py`, 850 LOC) does this for *Rulespec specifically*. Formspec generalization makes it general.

**New crate: `formspec-codegen`.** ~2,500 LOC.

```
formspec/crates/formspec-codegen/
├── src/
│   ├── lib.rs              # public API: codegen(definition, target) → String
│   ├── ast.rs              # internal Definition AST (already exists informally in formspec-core; consolidate here)
│   ├── emit/
│   │   ├── rust.rs         # struct, enum (variants), validator fn per type
│   │   ├── typescript.rs   # interface, discriminated union, Zod validator
│   │   ├── json_schema.rs  # JSON Schema 2020-12 (replaces hand-authored schemas/)
│   │   ├── shacl.rs        # Turtle node shapes (Pattern A from CUE compiler is a good base)
│   │   └── openapi.rs      # OpenAPI 3.1 fragment
│   └── tests/
```

**Reuse strategy from the CUE compiler.** The CUE compiler's emitters (`PKAF/tools/constraints_compile.py:200–800`) handle exactly the four hard cases: closed enums, conditional branches, disjunctions, list cardinality. Port those emitter functions one-for-one into `formspec-codegen`, but driven by Formspec Definition AST instead of the partial CUE parse. The CUE compiler's *parser* throws away (it was the workaround); the *emitters* are reusable patterns. Estimated savings: ~300 LOC of design work.

**Public API.**

```rust
pub fn emit(definition: &Definition, target: Target) -> Result<String, CodegenError>;
pub enum Target { Rust, TypeScript, JsonSchema, Shacl, OpenApi }
```

CLI binary `formspec-codegen` wraps it: `formspec-codegen --definition assertion.json --target rust --out lib.rs`.

**Wired into.** `formspec-wasm` exposes `emitDefinitionAs(definition, target)` for tooling consumers. `formspec-py` exposes `emit_definition(definition, target)` for Python pipelines. The hand-authored schemas in `formspec/schemas/*.schema.json` become *generated artifacts* — their AST source is a meta-Definition in `formspec/schemas/source/*.json`. (Bootstrapping order: ship codegen first, port one schema to source-form as a proof, then port the rest in a follow-up.)

**LOC estimate.** ~2,500 (new crate) + ~200 wasm/py wiring + ~400 tests = ~3,100. **Largest single line item in the proposal.**

## 4. Profile mechanism in code — recap

See §3.6. Closed enum + config struct, threaded through `EvalContext`, with a top-level `profile` key on the Definition document that the assembler reads. Form is default; graph is opt-in. No trait gymnastics; no generic explosion.

## 5. Codegen pipeline

Detailed in §3.7. Summary: new crate `formspec-codegen`, five emitters, ported emitter patterns from the CUE compiler. Schemas-as-generated-artifacts is a follow-up bootstrap step, not part of the core proposal.

## 6. Cross-document reference scaling

Detailed in §3.3. `InstanceResolver` trait, three impls (`EagerHashMapResolver`, `LruIriResolver`, `CompositeResolver`), profile chooses which the evaluator builds. FEL surface (`@instance('name')`) doesn't change — only the resolver mechanics. Caching is the resolver's problem, not the evaluator's.

## 7. Testing strategy

### 7.1 Form-profile preservation (regression safety)

**Baseline.** Run the full Formspec test suite at HEAD (`make test`). Capture failure count = 0.

**Profile default check.** After each gap-item change, re-run `make test` with no fixture changes. **Form profile must remain bit-identical** — same JSON outputs from `evaluate_definition_*`, same validation result codes, same NRB behavior, same shape pass/fail counts. The CI gate is "diff vs. captured baseline = empty."

**Consumer check.** After all gap items land, run:

- `formspec-studio` Playwright E2E (`formspec-studio/packages/formspec-studio/tests/e2e/playwright/`) — must pass unchanged.
- `formspec-engine` Vitest suite — same.
- `case-portal` smoke test — same.
- `formspec-site` build — same.

Any divergence = the form-profile defaults drifted; fix before merging.

### 7.2 Graph-profile correctness (Rulespec as canonical fixture)

**Canonical test corpus.** `PKAF/constraints/core/*.cue` → port each to Formspec Definition form (one Definition per Vocabulary entity: Assertion, EvidenceBinding, Warrant, SourceFragment, etc.). Place in `formspec/crates/formspec-eval/tests/graph_profile/rulespec/`.

**Round-trip checks.**

1. Hand-authored Definition (graph profile) evaluates a Rulespec instance to the same result a SHACL validator would produce against the v0.1 hand-authored shapes (`PKAF/shapes/`).
2. `formspec-codegen --target shacl` over the same Definition produces SHACL Turtle that validates the same instance with the same result.
3. `formspec-codegen --target rust` over the same Definition produces a Rust validator that returns the same `ValidationResult` set as the evaluator does in graph mode.
4. `formspec-codegen --target json-schema` over the same Definition produces JSON Schema that validates the same instance the same way Ajv would today.

If all four agree on `PKAF/fixtures/`, the graph profile is wired correctly and codegen is faithful.

### 7.3 Cross-profile regression

`formspec/crates/formspec-cross-stack-fixture-harness` (already exists) gets a new fixture family — same Definition document, two profile flags, expected divergence documented. Catches accidental profile-leak (form-only code path activated under graph mode, or vice versa).

## 8. Rust workspace changes

`formspec/Cargo.toml`:

```toml
[workspace]
members = [
    "crates/formspec-changeset",
    "crates/formspec-core",
    "crates/formspec-codegen",       # NEW (§3.7)
    "crates/formspec-cross-stack-fixture-harness",
    "crates/formspec-eval",
    "crates/formspec-lint",
    "crates/formspec-py",
    "crates/formspec-resolver",      # NEW (§3.3)
    "crates/formspec-signature-adapter-ring",
    "crates/formspec-signature-cose",
    "crates/formspec-signature-port",
    "crates/formspec-wasm",
]
```

**New dependency edges:**

- `formspec-resolver` depends on `fel-core` (uses `Value`).
- `formspec-eval` depends on `formspec-resolver` (resolver trait in `EvalContext`).
- `formspec-codegen` depends on `formspec-core` (Definition AST + JSON model).
- `formspec-wasm` and `formspec-py` add optional dependency on `formspec-codegen` (behind a `codegen` feature flag — keeps WASM payload size unchanged for engine consumers who don't need it).

**No renames.** Every existing crate keeps its name and identity.

## 9. npm workspace changes

`formspec/package.json` workspaces unchanged. Inside `formspec/packages/`:

- `formspec-types/` — extend `scripts/generate-types.mjs` to read from `formspec-codegen` (WASM call) instead of `json-schema-to-typescript`. ~80 LOC change. Output identical for `Form` profile (regression-checked); new generated files for graph-profile Definitions when authored.
- `formspec-engine/`, `formspec-webcomponent/`, `formspec-react/`, `formspec-adapters/`, `formspec-layout/`, `formspec-assist/` — **zero changes**. Form profile is default; they never see graph code.
- `formspec-core/` (npm package, not the Rust crate) — exports a new `Profile` enum + types from `@formspec-org/types` for tooling consumers that need to author graph-profile Definitions.

LOC: ~150 TS.

## 10. Python extension changes

`formspec/crates/formspec-py/src/lib.rs:33–42` — pyfunction registration. Add:

- `evaluate_definition_graph(definition, data, instances_resolver_callback)` — graph-profile entry. `instances_resolver_callback` is a Python callable the resolver invokes for lazy IRI dereference. ~120 LOC including the callback bridge.
- `emit_definition(definition, target: str) -> str` — codegen surface. ~60 LOC.

`formspec/src/formspec/` (Python pure-side) — no changes for form profile. Adds `formspec.graph` submodule (~150 LOC) exposing the resolver-callback pattern and a few helpers for IRI-graph workflows.

LOC: ~330 Python+Rust.

## 11. Stack-topology implications

**Build order (`formspec-stack/Makefile`).** No change. `fel-core → formspec → ...`.

**Cross-stack dependency edges.** `Rulespec` (`PKAF/`, future `rulespec/` submodule) becomes a *consumer* of Formspec. Today it has zero formspec dependency. Post-generalization, Rulespec ships a `vocabulary/*.definition.json` set authored in graph-profile Formspec, plus its CUE constraint source (retained as informative companion, not source-of-truth — see §12). Rulespec's Rust SDK (when authored) depends on `formspec-eval` + `formspec-resolver`.

**Workspec / WOS, Trellis.** Same opportunity, not in scope of this proposal. Once Formspec generalization lands, a follow-up can replace hand-authored schemas for WOS step definitions and Trellis envelope shapes with graph-profile Definitions. **Not committed here.** That follow-up is reviewed on its own merits, post-Rulespec-proof.

**The 9 submodules at `formspec-stack/`.** No new submodule from this proposal. The Rust workspace gains two crates inside the existing `formspec/` submodule.

## 12. Migration of the just-shipped CUE work

**Retirement plan — 4 steps, sequential.**

1. **Generalization lands.** All seven gap items merged. `formspec-codegen` produces JSON Schema + Rust + TS + SHACL from a Definition.
2. **Port Rulespec Vocabulary to Definitions.** For each `PKAF/constraints/core/*.cue`, author a Formspec graph-profile Definition (`PKAF/vocabulary/*.definition.json` or, post-Rulespec-extraction, `rulespec/vocabulary/*.definition.json`). Same closed enums, same disjunctions, same conditional branches — expressed in Definition syntax via the Variant primitive (§3.2), constraint-null-policy (§3.4), and `xone` shape composition.
3. **Codegen parity gate.** Run `formspec-codegen` against each ported Definition. Diff against the existing `PKAF/compiled/*` outputs. Where bytes match exactly, the Definition is faithful. Where they differ, decide: is the diff cosmetic (whitespace, ordering — accept) or semantic (Definition is incomplete — fix the Definition, not the codegen)? Block on no-semantic-diff.
4. **Retire CUE.**
   - Delete `PKAF/tools/constraints_compile.py` (850 LOC).
   - Delete `PKAF/tools/constraints_parity.py`.
   - Delete `PKAF/tools/install-cue.sh`.
   - Delete `PKAF/cue/` (already absent in current tree — confirmed).
   - Delete `PKAF/constraints/` once Definitions are the source-of-truth, **OR** keep `PKAF/constraints/` as informative companion documentation, marked non-normative in a `CONSTRAINTS-README.md`. Owner choice. Recommendation: delete; CUE was an interim authoring carrier, not a value-add for Rulespec users. The Definition source-of-truth is more LLM-tractable and aligns with the federation-thesis posture.
   - Delete `PKAF/compiled/` — regenerated on demand from `formspec-codegen`.

**Reversibility.** CUE compiler is 850 LOC; can be restored from git history in minutes if generalization stalls. Greenfield posture.

## 13. Engineering scope summary

| Gap | Surface | LOC |
|---|---|---|
| §3.1 IRI paths | fel-core lexer/parser/env + formspec-eval convert | ~600 |
| §3.2 Variant primitive | rebuild + revalidate + schema + tests | ~480 |
| §3.3 Resolver trait + new crate | `formspec-resolver` + wiring | ~890 |
| §3.4 Constraint null policy | items.rs + shapes.rs + schema + tests | ~320 |
| §3.5 Relevance mode | EvalContext + items.rs + shapes.rs + schema + tests | ~210 |
| §3.6 Profile system | new module + EvalContext + assembler + schema | ~480 |
| §3.7 Codegen (largest) | `formspec-codegen` crate + 5 emitters + tests | ~3,100 |
| Python bindings | formspec-py + formspec.graph | ~330 |
| TS wiring | formspec-types generator + new exports | ~150 |
| Cross-profile fixtures | fixture-harness + rulespec port | ~400 |
| Retirement deletes | CUE compiler + ancillary | **−1,200** (net delete) |
| **Total adds** |  | **~6,960** |
| **Net (adds − deletes)** |  | **~5,760** |

(Confidence band: ±25% — codegen is the biggest unknown; could be 2,000 or 4,000 depending on how many of the CUE emitters port cleanly.)

### 13.1 Critical path (single-threaded estimate)

```
PathMode + IRI paths (§3.1)       [3 days, single-threaded — touches fel-core grammar]
        ↓
Profile system (§3.6)              [1 day — wires PathMode, others into EvalContext]
        ↓
Constraint null + Relevance mode  [2 days — tightly coupled, single PR]
(§3.4 + §3.5)
        ↓
Resolver trait + crate (§3.3)      [3 days — new crate, plus wiring]
        ↓
Variant primitive (§3.2)           [2 days — touches all 4 phases]
        ↓
Codegen crate (§3.7)               [6–8 days — five emitters, largest piece]
        ↓
Rulespec port + codegen parity     [3 days — fixture-driven]
        ↓
CUE retirement (§12)               [0.5 day — deletes + CI]
```

**~20–22 working days single-threaded. ~12–14 days with one parallelizable agent on codegen while another lands §3.1–§3.6.**

### 13.2 Parallelism

After §3.1 and §3.6 land (the foundation), the remaining gap items are independent:

- §3.2 (Variant) is independent of §3.3 (Resolver).
- §3.4 / §3.5 are tiny and can be a single PR.
- §3.7 (Codegen) can be started in parallel with §3.2 once the Definition AST is settled — codegen reads AST, doesn't modify it.

Three lanes work simultaneously: structural-additions (3.2), resolver (3.3), codegen (3.7).

## 14. Risks — honest

1. **Codegen scope creep.** ~3,100 LOC is the most optimistic estimate for five emitters. If SHACL emission turns out to need a richer intermediate representation than current Definition AST provides (the CUE compiler hit this — Pattern C compilation is non-obvious), add ~1,000 LOC. Mitigation: ship JSON Schema + Rust + TS first (the three with cleanest emit semantics); SHACL and OpenAPI as a follow-up if needed. Rulespec's day-one codegen need is SHACL — so it's actually on the critical path. Plan for the worst case; budget +30% on §3.7.
2. **Graph-profile resolver performance.** Lazy IRI dereference at 10⁴ refs through a callback-into-Python (or HTTP fetch in production) is potentially slow. Mitigation: `LruIriResolver` ships with reasonable defaults (10k-entry LRU), and a batch-resolve API the host can pre-warm. Not a correctness issue, only a hot-path concern; address with benchmarks before claiming production-ready graph profile.
3. **Form profile drift.** A subtle wiring error in §3.6 could change form-profile output even when callers pass `EvalContext::default()`. Mitigation: §7.1 baseline diff gate. CI enforces zero-diff against captured baselines. If the diff is nonzero, the PR is blocked. This is non-negotiable.
4. **Schema bootstrap circularity.** Once `formspec/schemas/*.schema.json` are generated from meta-Definitions in `formspec/schemas/source/*.json`, there's a chicken-and-egg: the meta-Definitions are themselves Formspec Definitions, so they need the type for `Definition` to exist. Mitigation: hand-author the first meta-Definition (Definition itself) bootstrap-style; all other schemas generate from it.
5. **Rulespec authoring ergonomics.** Authoring Rulespec Vocabulary in graph-profile Formspec JSON is verbose vs. CUE. Mitigation: this is fine — the Vocabulary is small (~12 entities), authored once, mostly read by codegen and AI tooling, not hand-edited by partners. Verbosity is the LLM-tractability bet (§1.5 of the strategic spec).
6. **Variant primitive interaction with repeat groups.** A Variant inside a Repeat (e.g., a list of Assertions where each is either evidence-bound or no-evidence-reason) is a real Rulespec pattern. The rebuild phase has to handle Variant-inside-Repeat expansion correctly. ~80 LOC of edge-case logic; covered in §3.2 estimate. Risk: another ~80 LOC if nested Variants surface unforeseen tree-walk issues.
7. **The Formspec spec authoring contract** (`formspec/CLAUDE.md` §"Spec authoring contract") requires schema → spec → codegen artifacts stay in lockstep. Generalization adds five new top-level Definition keys (`profile`, `constraintNullPolicy`, `relevanceMode`, plus bind-level overrides). Each must be spec-authored, BLUF'd, LLM-md regen'd. ~1 day of spec work, not yet in LOC estimate.

## 15. Structural blockers — answer

**No hard blockers found.** Three things looked like they might be, on inspection turned out tractable:

1. **The `Environment` trait already exists** (`fel-core/src/evaluator/core.rs:25`). Graph-profile is a new impl, not a parallel evaluator. **Clean seam.** The biggest win of the trace.
2. **Shape composition already supports `xone`** (`revalidate/shapes.rs:351`). Variant promotion (§3.2) is *additive* — `xone` at the Shape level keeps working, Variant at the Item level is a new Definition primitive. No conflict.
3. **`EvalContext` is already the carrier** for evaluation-time configuration (`types/evaluation.rs:54–66`). Profile config rides inside it. No new entry point, no fork in the public API.

The four real costs are: §3.1 (lexer/parser change, biggest *risk*), §3.7 (codegen crate, biggest *LOC*), the CUE retirement (smallest individual cost but most visible delete), and the spec authoring tax (real but not load-bearing on the engineering critical path).

**Net answer.** Universal-data-contract framing is feasible at ~6k LOC net add, ~3 weeks single-threaded, ~1.5 weeks parallel. The implementation surfaces line up. Nothing in current Formspec architecture forecloses it.

## 16. Recommendation

Ship it. The owner-economic frame (priority = `(Importance + User Value) × Future Tech Debt`) is unambiguous here:

- **Importance**: removes a parallel toolchain (CUE compiler), collapses two languages back to "FEL + Formspec", reuses one validator/codegen pipeline for forms, Rulespec, and future profiles.
- **User Value**: Rulespec partners (federation thesis, strategic spec §1.3) get Formspec-grade tooling, an LLM-tractable authoring surface, multi-target codegen out of the box. Form consumers (`formspec-studio`, `case-portal`, etc.) see zero change.
- **Future Tech Debt**: the alternative — keep the CUE compiler as the Rulespec source-of-truth, and let it accumulate emitters and partial-parser hacks — has compound debt. Every new target language, every new constraint pattern, every Rulespec-vs-Formspec inconsistency. Generalization caps that.

The economics favor the maximalist one-shot. ~6k LOC across ~3 weeks, against retiring 850 LOC of Python that would otherwise stay forever, plus opening Formspec to every non-form domain on the stack roadmap. Do it once, do it right, do it now.

---

**Next step (single deliverable to unblock):** owner-side review of §3.6 (profile mechanism) and §3.7 (codegen scope). Both are the load-bearing design decisions; everything else is mechanical. If the profile shape (closed enum + `ProfileConfig` riding inside `EvalContext`) and the codegen crate shape (single emit fn, five targets, ported emitter patterns) are accepted, the rest is execution.
