# Rulespec Layer 2 — Constraints (CUE source-of-truth)

This directory holds the CUE constraint source for Rulespec Vocabulary v0.2.
CUE is the **source of truth**. JSON Schema, Rust, TypeScript, SHACL, and Rego are **compilation targets** produced by `tools/constraints_compile.py` into `compiled/`.

Selection rationale: see `docs/adr/2026-05-12-rkaf-constraint-source-cue.md`.

## Layout

```
constraints/
├── core/              CUE source for every v0.2 UNIVERSAL vocabulary primitive (§§4-5 of spec).
├── platform/          Closed plain-JSON platform artifact carriers.
├── analysis/          Generic document-analysis contracts above the kernel.
├── semantics/         Kernel L0 range registry (class-valued predicate ranges).
├── profiles/          Domain profiles. Jurisdiction- or family-specific terms.
│   ├── refspec/       Open-label extrapolation profile; portable targets only,
│   │                  excluded from the generated rkaf-core Rust crate.
│   └── us-rulemaking/ US regulatory identity + the rulemaking-process module
│                      (spec/rkaf-rulemaking.md), plus its own semantics/l0-ranges.cue.
├── adversarial/       Evaluator-class adversarial constraints (≥5 per spec §10.1).
└── ai-extraction/     LLM-systematic-misinterpretation adversarial constraints (≥3 per spec §10.1).
```

### Kernel / profile boundary

`profiles/` may compose a kernel shape; `core/` MUST NOT reference anything
under `profiles/`. That direction is audited, not merely documented — see
`KernelProfileBoundaryTests` in `tools/test_constraints_compile.py`, which
fails the build on a profile-shape reference or a US identifier grammar
landing in `core/`.

A profile overlay composes the kernel shape it extends and keeps that shape's
`@type`. `#USRegulatoryArtifact` therefore constrains `rkaf:Artifact`, adding
only optional properties and guarded grammars: conjoining the profile's
NodeShape with the kernel's can only ever add constraints, never relax one. A
consumer that loads only the kernel sees no profile term at all.

Kernel definitions are closed at the CUE layer, so
`#Artifact & {"rkaf:hasRegulatoryIdentifier": "…"}` is `field not allowed`. The
compiled carriers are open by construction (JSON Schema without
`additionalProperties: false`; open-world RDF), so a US-bearing document is
UNCONSTRAINED by the kernel carriers rather than rejected by them, and is
constrained by the profile carriers. `tools/constraints_parity.py` pins both
halves.

### Layered value sets

A profile may contribute VALUES to a kernel property as well as properties to a
kernel class. `rkaf:lifecycleEventKind` is the worked example:

| Layer | Declares | Compiled artifact |
|---|---|---|
| `core/lifecycle-event.cue` | `#LifecycleEventKind` — the eight universal kinds — and a kind property left deliberately OPEN | `compiled/*/core/lifecycle-event.*`: the eight kinds as a named type, no closure on the property |
| `profiles/us-rulemaking/us-lifecycle-event.cue` | `#USProceedingLifecycleEventKind` (twelve `proceeding` kinds), the assembled union `#ComposedLifecycleEventKind`, and `#USLifecycleEvent` composing the kernel shape | `compiled/*/profiles/us-rulemaking/us-lifecycle-event.*`: all 20 values, closed, bound to `rkaf:LifecycleEvent` |

Why the kernel carrier stays open: SHACL is conjunctive and the compiled shapes
are loaded together, so a kernel `sh:in` over ten values would reject every
profile-contributed kind no matter what the overlay says. Openness here means
the same thing it means for the Artifact terms — unconstrained by the kernel,
constrained by the profile — and the composed artifact is the one
`tools/conformance_lib.py` and `crates/rkaf-validate/build.rs` bind to the
class. Ownership is not left to review habit: `LifecycleKindOwnershipTests` in
`tools/test_constraints_compile.py` proves every value in every compiled
artifact has exactly one declaring module, that the kernel's part is exactly
the eight universal kinds, and that the assembled union equals kernel +
sum(profiles).

"Every compiled artifact" is meant literally, and the audit walks each sink in
the shape that sink can express:

| Sink | How the closure appears | Scanned by |
|---|---|---|
| `compiled/json-schema/` | `enum` on the property (possibly via `$ref`) | `_compiled_schema_closures` |
| `compiled/shacl/` | `sh:in` on the property's `sh:property` | `_compiled_shacl_closures` |
| `compiled/typescript/` | property typed by a literal-union alias, not `string` | `_compiled_typescript_closures` |
| `crates/rkaf-core/src/generated/` | field typed by a generated enum, not `String` | `_generated_rust_closures` |
| `compiled/rego/` | a `<definition>_values` list — Rego has NO property types | `_compiled_rego_closures` |

Rego is the reason this table exists rather than a sentence. It is the one
target that cannot express "this property is closed over that set" at all — it
emits value sets and leaves the `deny` rules to the policy author — and it is
also the target no gate loads. When `target_rego` iterated `doc.enums` only, the
assembled 20-value union existed in every other artifact and in none of the
Rego ones, and nothing failed. `test_every_target_carries_the_assembled_closure`
now asserts per-sink, so the next target to lose a union names itself.

Cross-file value sets reach EVERY target: `target_shacl` and `target_rego` take
the same enum registry the json-schema/rust/typescript emitters take, so an
overlay closes a property whose enum a different file declares. Two consequences
worth stating outright:

  * An IRI-valued `sh:in` only matches data whose values arrive as IRIs, so
    every enum-valued term MUST also carry an `@type: @id`/`@vocab` coercion in
    `context/rkaf-context.jsonld`.
  * The registry is built from a SORTED walk and rejects a duplicate
    enum/union name with a `CompileError`. A name that resolved to whichever
    file the walk reached first would make the compiled value sets — and the
    contract digest pinned in `spec/rkaf-conformance.md` — depend on the
    filesystem that built them.

## Targets and obligations (per spec §6.3)

| Target        | Status | Output                                  |
|---------------|--------|-----------------------------------------|
| JSON Schema   | MUST   | `compiled/json-schema/<sub>/<name>.schema.json` (Draft 2020-12) |
| Rust          | MUST for Core and Rust-carried profiles | `crates/rkaf-core/src/generated/<snake>.rs` for `core/` and selected profiles. `profiles/refspec/` belongs to Rulespec Extrapolator and is deliberately excluded from `rkaf-core`. The canonical Rust sink is tracked in git; no parallel `compiled/rust/` copy is produced. |
| TypeScript    | MUST   | `compiled/typescript/<sub>/<name>.ts`   |
| SHACL         | MAY    | `compiled/shacl/<sub>/<name>.ttl` (Pattern C only — no `sh:if`/`sh:then`) |
| Rego          | MAY    | `compiled/rego/<sub>/<name>.rego`       |

`constraints/platform/` is the deliberate exception to the JSON-LD carrier
defaults. It emits closed, array-strict plain JSON to JSON Schema, TypeScript,
and Rust. It has no RDF meaning, so the driver emits no SHACL or Rego for it.

## Build

```bash
# Pin CUE 0.10.0
./tools/install-cue.sh

# Validate CUE source syntax before compiling (make cue-vet also works)
.tools/cue vet constraints/core/*.cue constraints/analysis/*.cue constraints/adversarial/*.cue constraints/ai-extraction/*.cue constraints/profiles/*/*.cue
.tools/cue vet constraints/semantics/*.cue constraints/analysis/*/*.cue constraints/profiles/*/*/*.cue
.tools/cue vet constraints/platform/*.cue

# Compile every constraint to every target
tools/compile_all.sh
```

`compile_all.sh` is the single canonical driver: it maps each source directory
to its compiled sub-path (`core`, `platform`, `analysis`, `adversarial`,
`ai-extraction`, `profiles/<profile>`), writes Rust for Core, platform,
analysis, and Rust-carried
profiles, and re-pins the embedded L0 contract digests. The RefSpec profile
still produces portable JSON Schema, TypeScript, SHACL, and Rego outputs,
but never a generated `rkaf-core` module.

CUE packages are directory-scoped, so a profile that composes a kernel shape is
vetted as one instance with the kernel — which is exactly the dependency it
declares:

```bash
.tools/cue vet ./constraints/core/*.cue ./constraints/profiles/us-rulemaking/*.cue
```

## Parity orchestrator (release gate)

```bash
.venv/bin/python3 tools/constraints_parity.py
```

Asserts that for every (constraint, fixture) pair in the core Vocabulary set,
the JSON Schema and SHACL targets produce the same PASS/FAIL classification,
and the JSON Schema classification matches the expected outcome. Adversarial
fixtures by design surface evaluator-class divergences (per spec §10.1) — those
are reported as "documentation findings" rather than release blockers.

CI gate: `core_divergences > 0` exits non-zero.

## Pattern C lint

```bash
grep -rE 'sh:if|sh:then' compiled/shacl/ && echo FAIL || echo PASS
```

Compiled SHACL output MUST NOT contain `sh:if` or `sh:then` (per source spec
Appendix C). The compiler emits `sh:or` with `sh:not` (Pattern C) only.

## Note on the compiler implementation

`tools/constraints_compile.py` is a Python implementation of the structural
CUE → multi-target compiler. It recognizes the regular CUE patterns Rulespec
uses (closed-string-enums, enum-of-refs unions, shape definitions, conditional
`if "x" == "v" { ... }` blocks, sibling `{...} | {...}` disjunctions, list
constraints with `list.MinItems(N)`). It is not a full CUE parser; the
authoritative CUE syntax check is `.tools/cue vet` (see Build above for the
profile invocation).

The plan envisaged a Rust crate (`rkaf-constraints-compile`); the Python
implementation here is the v0.2-pre.3 working compiler. Per the plan's ADR,
the Rust port is a follow-up under the SDK plan (Plan 6 / Layer 5) once the
SDK consumer surface is known.
