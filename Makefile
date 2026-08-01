# Rulespec — Policy Knowledge Assertion Framework.
#
# Standalone repo: Rust workspace under crates/ + Python tooling under tools/.
# This Makefile is the single entry point the stack-level fan-out calls into.

CARGO         = cargo
# rdfcanon 1.0.0 requires Python 3.12. uv resolves that interpreter and the
# pinned requirements for the default local gate; callers may still override
# PYTHON on the make command line.
PYTHON        = uv run --python 3.12 --with-requirements requirements.txt python
CARGO_MANIFEST = --manifest-path crates/Cargo.toml

.PHONY: all help build build-runtime-cli test test-rust test-shapes test-reference-corpora test-audits test-conformance clean compile

all: build

help:
	@echo "Rulespec Makefile"
	@echo ""
	@echo "  make build              — cargo build --workspace + release CLI"
	@echo "  make test               — full gate sweep (rust + shapes + audits + L0-L4 conformance)"
	@echo "  make test-rust          — cargo test --workspace (unit + integration)"
	@echo "  make test-shapes        — parse + JSON-Schema + SHACL + negative fixtures"
	@echo "  make test-reference-corpora — validate shipped reference-corpus JSON-LD"
	@echo "  make test-audits        — vocab, coverage, rename, constraints-parity, projector-parity, version-sync, semantic carriers"
	@echo "  make test-conformance   — L1-L4 report plus L0 carrier-mapping audit"
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

test-shapes: test-reference-corpora
	$(PYTHON) tools/ci_validate.py
	$(PYTHON) tools/validate_negatives.py

test-reference-corpora:
	$(CARGO) build $(CARGO_MANIFEST) -p rkaf-validate-cli
	@for file in reference-corpora/us-rulemaking/v0.2/data/*.jsonld; do \
		crates/target/debug/rkaf-validate "$$file"; \
	done
	$(PYTHON) tools/ci_validate.py reference-corpora/us-rulemaking/v0.2/data/*.jsonld

test-audits:
	$(CARGO) build $(CARGO_MANIFEST) -p projector-harness
	$(PYTHON) tools/vocab_audit.py
	$(PYTHON) -m unittest tools.test_constraints_compile tools.test_l0_mapping_audit tools.test_semantic_carriers tools.test_reference_release_digest tools.test_rulespec_releases tools.test_refspec_atlas tools.test_refspec_atlas_conformance tools.test_refspec_atlas_cross_repository -v
	$(PYTHON) tools/l0_mapping_audit.py
	$(PYTHON) tools/l0_l3_coverage_audit.py
	$(PYTHON) tools/rename_audit.py
	$(PYTHON) tools/l4_coverage_audit.py
	$(PYTHON) tools/constraints_parity.py
	$(PYTHON) tools/projector_parity.py
	$(PYTHON) tools/version_sync.py --check
	$(PYTHON) tools/codegen_drift_audit.py

test-conformance: build-runtime-cli
	$(PYTHON) tools/conformance_report.py

# ─── Codegen ───────────────────────────────────────────────────────────
#
# `compile` drives every primitive through every target via the single
# canonical wrapper. Writes Rust to crates/rkaf-core/src/generated/ (tracked);
# other targets to compiled/<target>/<sub>/ (gitignored).

compile:
	PYTHON="$(PYTHON)" tools/compile_all.sh

# ─── Clean ─────────────────────────────────────────────────────────────

clean:
	$(CARGO) clean $(CARGO_MANIFEST)
