# Rulespec Layer 2 — Constraints (CUE source-of-truth)

This directory holds the CUE constraint source for Rulespec Vocabulary v0.2.
CUE is the **source of truth**. JSON Schema, Rust, TypeScript, SHACL, CUE-passthrough, and Rego are **compilation targets** produced by `tools/constraints_compile.py` into `compiled/`.

Selection rationale: see `docs/adr/2026-05-12-rkaf-constraint-source-cue.md`.

## Layout

```
constraints/
├── core/              CUE source for every v0.2 vocabulary primitive (§§4-5 of spec).
├── adversarial/       Evaluator-class adversarial constraints (≥5 per spec §10.1).
└── ai-extraction/     LLM-systematic-misinterpretation adversarial constraints (≥3 per spec §10.1).
```

## Targets and obligations (per spec §6.3)

| Target        | Status | Output                                  |
|---------------|--------|-----------------------------------------|
| JSON Schema   | MUST   | `compiled/json-schema/<sub>/<name>.schema.json` (Draft 2020-12) |
| Rust          | MUST   | `crates/rkaf-core/src/generated/<snake>.rs` — canonical sink for the Rust workspace; kebab → snake mapping handled by `tools/compile_all.sh`. **Tracked in git.** No parallel `compiled/rust/` copy is produced. |
| TypeScript    | MUST   | `compiled/typescript/<sub>/<name>.ts`   |
| SHACL         | MAY    | `compiled/shacl/<sub>/<name>.ttl` (Pattern C only — no `sh:if`/`sh:then`) |
| CUE           | MAY    | `compiled/cue/<sub>/<name>.cue` (passthrough) |
| Rego          | MAY    | `compiled/rego/<sub>/<name>.rego`       |

## Build

```bash
# Pin CUE 0.10.0
./tools/install-cue.sh

# Compile every constraint to every target
for f in constraints/core/*.cue constraints/adversarial/*.cue constraints/ai-extraction/*.cue; do
  base=$(basename "$f" .cue)
  if [[ "$f" == constraints/core/* ]]; then sub="core"
  elif [[ "$f" == constraints/adversarial/* ]]; then sub="adversarial"
  else sub="ai-extraction"; fi
  for t in json-schema rust typescript shacl cue rego; do
    python3 tools/constraints_compile.py --in "$f" --target "$t" \
      --out "compiled/$t/$sub/$base.<ext>"
  done
done
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
authoritative CUE syntax check is `.tools/cue vet ./constraints/...`.

The plan envisaged a Rust crate (`rkaf-constraints-compile`); the Python
implementation here is the v0.2-pre.3 working compiler. Per the plan's ADR,
the Rust port is a follow-up under the SDK plan (Plan 6 / Layer 5) once the
SDK consumer surface is known.
