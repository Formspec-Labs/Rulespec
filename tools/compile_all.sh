#!/usr/bin/env bash
# Single canonical driver for the constraint compiler.
#
# Writes every target output to its canonical sink:
#   json-schema   → compiled/json-schema/<sub>/<name>.schema.json
#   typescript    → compiled/typescript/<sub>/<name>.ts
#   shacl         → compiled/shacl/<sub>/<name>.ttl
#   cue           → compiled/cue/<sub>/<name>.cue       (passthrough)
#   rego          → compiled/rego/<sub>/<name>.rego
#   rust          → crates/rkaf-core/src/generated/<snake>.rs   (canonical;
#                   the Rust workspace re-exports from this path. No kebab
#                   copy is produced — see ADR or constraints/README.md.)
#
# Idempotent. Run from Rulespec repo root.
#
# Used by:
#   - `make compile` (Rulespec Makefile)
#   - `make test-audits` (codegen_drift_audit.py invokes this)
#   - .github/workflows/constraints-parity.yml

set -euo pipefail

PYTHON="${PYTHON:-python3}"
COMPILER="$PYTHON tools/constraints_compile.py"

# Map kebab-case primitive name → snake_case Rust module name.
snake_case() { tr '-' '_' <<< "$1"; }

compile_one() {
    local src="$1" target="$2"
    local base sub ext outdir outpath
    base=$(basename "$src" .cue)

    if [[ "$src" == constraints/core/* ]]; then sub="core"
    elif [[ "$src" == constraints/adversarial/* ]]; then sub="adversarial"
    elif [[ "$src" == constraints/ai-extraction/* ]]; then sub="ai-extraction"
    else
        echo "ERROR: unknown constraint subdirectory in $src" >&2
        return 1
    fi

    case "$target" in
        json-schema)
            outdir="compiled/json-schema/$sub"
            outpath="$outdir/$base.schema.json"
            ;;
        typescript)
            outdir="compiled/typescript/$sub"
            outpath="$outdir/$base.ts"
            ;;
        shacl)
            outdir="compiled/shacl/$sub"
            outpath="$outdir/$base.ttl"
            ;;
        cue)
            outdir="compiled/cue/$sub"
            outpath="$outdir/$base.cue"
            ;;
        rego)
            outdir="compiled/rego/$sub"
            outpath="$outdir/$base.rego"
            ;;
        rust)
            # Only core/ primitives feed into the Rust workspace today.
            # adversarial/ and ai-extraction/ are CUE-only.
            if [[ "$sub" != "core" ]]; then return 0; fi
            outdir="crates/rkaf-core/src/generated"
            outpath="$outdir/$(snake_case "$base").rs"
            ;;
        *)
            echo "ERROR: unknown target $target" >&2
            return 1
            ;;
    esac

    mkdir -p "$outdir"
    $COMPILER --in "$src" --target "$target" --out "$outpath"
}

main() {
    local sources=(
        constraints/core/*.cue
        constraints/adversarial/*.cue
        constraints/ai-extraction/*.cue
    )
    local targets=(json-schema typescript shacl cue rego rust)

    for src in "${sources[@]}"; do
        for t in "${targets[@]}"; do
            compile_one "$src" "$t"
        done
    done
}

main "$@"
