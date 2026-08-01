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
# Domain profiles under constraints/profiles/<profile>/ compile to portable
# targets under a `profiles/<profile>` sub-path, e.g.
#   compiled/json-schema/profiles/us-rulemaking/rulemaking.schema.json
#   crates/rkaf-core/src/generated/profiles/us_rulemaking/rulemaking.rs
# The sub-path keeps the dependency direction legible: a profile may compose a
# kernel shape, never the reverse.
#
# The RefSpec open-label profile belongs to the independently released Rulespec
# Extrapolator boundary. It still compiles to portable schema targets, but it is
# intentionally excluded from the generated `rkaf-core` Rust crate.
#
# The document-analysis module under constraints/analysis/ compiles the same
# way, under an `analysis` sub-path:
#   compiled/json-schema/analysis/relation-finding.schema.json
#   crates/rkaf-core/src/generated/analysis/relation_finding.rs
# It is NOT a profile: it declares generic, jurisdiction-free contracts that a
# profile may depend on. The dependency direction is kernel <- analysis <-
# profiles; the kernel never depends on either.
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
    elif [[ "$src" == constraints/analysis/* ]]; then sub="analysis"
    elif [[ "$src" == constraints/adversarial/* ]]; then sub="adversarial"
    elif [[ "$src" == constraints/ai-extraction/* ]]; then sub="ai-extraction"
    elif [[ "$src" == constraints/profiles/*/*.cue ]]; then
        sub="profiles/$(basename "$(dirname "$src")")"
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
            # core/ primitives, analysis/ contracts, and profiles/ overlays
            # feed into the Rust workspace. adversarial/ and ai-extraction/ are
            # CUE-only.
            case "$sub" in
                core)        outdir="crates/rkaf-core/src/generated" ;;
                analysis)    outdir="crates/rkaf-core/src/generated/analysis" ;;
                profiles/refspec) return 0 ;;
                profiles/*)  outdir="crates/rkaf-core/src/generated/profiles/$(snake_case "${sub#profiles/}")" ;;
                *)           return 0 ;;
            esac
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
        constraints/analysis/*.cue
        constraints/adversarial/*.cue
        constraints/ai-extraction/*.cue
        constraints/profiles/*/*.cue
    )
    local targets=(json-schema typescript shacl cue rego rust)

    # Remove output from compilers that predate the Core/Extrapolator split.
    # `profiles/refspec` no longer has a valid Rust sink in `rkaf-core`.
    rm -f crates/rkaf-core/src/generated/profiles/refspec/open_label.rs

    for src in "${sources[@]}"; do
        for t in "${targets[@]}"; do
            compile_one "$src" "$t"
        done
    done

    # Keep the embedded L0 contract digests (conformance example, corpus
    # manifest) pinned to the contract that was just compiled.
    $PYTHON tools/repin_contract_digest.py
}

main "$@"
