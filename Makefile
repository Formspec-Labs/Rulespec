# Rulespec — Policy Knowledge Assertion Framework.
#
# Standalone repo: Rust workspace under crates/ + Python tooling under tools/.
# This Makefile is the single entry point the stack-level fan-out calls into.

CARGO         = cargo
PYTHON        = python3
CARGO_MANIFEST = --manifest-path crates/Cargo.toml

.PHONY: all help build build-runtime-cli test test-rust test-shapes test-audits test-conformance clean compile

all: build

help:
	@echo "Rulespec Makefile"
	@echo ""
	@echo "  make build              — cargo build --workspace + release CLI"
	@echo "  make test               — full gate sweep (rust + shapes + audits + L1-L5 conformance)"
	@echo "  make test-rust          — cargo test --workspace (unit + integration)"
	@echo "  make test-shapes        — parse + JSON-Schema + SHACL + negative fixtures"
	@echo "  make test-audits        — vocab, rename, constraints-parity, projector-parity, version-sync"
	@echo "  make test-conformance   — L1-L5 conformance report across every fixture"
	@echo "  make compile            — regenerate JSON Schema + Rust + SHACL + TS from CUE"
	@echo "  make clean              — cargo clean"
	@echo ""

# ─── Build ─────────────────────────────────────────────────────────────

build: build-runtime-cli

build-runtime-cli:
	$(CARGO) build $(CARGO_MANIFEST) --workspace
	$(CARGO) build $(CARGO_MANIFEST) -p rkaf-runtime-cli --release

# ─── Test (the gate sweep) ─────────────────────────────────────────────
#
# `test` runs every gate. Each sub-target is independently invocable for
# faster local loops. Conformance depends on the release CLI being built
# (the reporter shells out to it for L4 behavior verdicts).

test: test-rust test-shapes test-audits test-conformance

test-rust:
	$(CARGO) test $(CARGO_MANIFEST) --workspace

test-shapes:
	$(PYTHON) tools/ci_validate.py
	$(PYTHON) tools/validate_negatives.py

test-audits:
	$(PYTHON) tools/vocab_audit.py
	$(PYTHON) tools/rename_audit.py
	$(PYTHON) tools/constraints_parity.py
	$(PYTHON) tools/projector_parity.py
	$(PYTHON) tools/version_sync.py --check

test-conformance: build-runtime-cli
	$(PYTHON) tools/conformance_report.py

# ─── Codegen ───────────────────────────────────────────────────────────

compile:
	$(PYTHON) tools/constraints_compile.py

# ─── Clean ─────────────────────────────────────────────────────────────

clean:
	$(CARGO) clean $(CARGO_MANIFEST)
