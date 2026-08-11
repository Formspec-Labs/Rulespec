# Rulespec — Policy Knowledge Assertion Framework.
#
# Standalone repo: Rust workspace under crates/ + Python tooling under tools/.
# This Makefile is the single entry point the stack-level fan-out calls into.

CARGO         = cargo
# rdfcanon 1.0.0 requires Python 3.12. uv resolves that interpreter and the
# pinned requirements for the default local gate; callers may still override
# PYTHON on the make command line.
# `--no-project` is load-bearing: without it `uv run` builds the
# rulespec-conformance wheel before every command, and that build force-includes
# the generated `compiled/` tree — so on a fresh clone `make compile` would
# depend on its own output. Tooling reads src/ through the tools/ shims instead.
PYTHON        = uv run --no-project --python 3.12 --with-requirements requirements.txt python
CARGO_MANIFEST = --manifest-path crates/Cargo.toml
# Pinned by tools/install-cue.sh into .tools/cue (gitignored; not required for
# targets other than cue-vet). Run tools/install-cue.sh once to populate it.
CUE           = .tools/cue

.PHONY: all help build build-runtime-cli test test-rust test-shapes test-reference-corpora test-audits test-conformance test-package clean compile cue-vet

# Scratch venv for test-package. Outside the tree so the packaged validator is
# exercised with no checkout in reach.
PACKAGE_CHECK_DIR = $(shell printf '%s' "$${TMPDIR:-/tmp}")rulespec-package-check

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
	@echo "  make test-package       — build the wheel and run it outside the checkout"
	@echo "  make cue-vet            — validate CUE source syntax (requires tools/install-cue.sh)"
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

test: test-rust test-shapes test-audits test-conformance test-package

# The distribution's claim is that a consumer needs no checkout. Only building
# the wheel and running it from an empty environment outside the repository can
# falsify it: a data directory left out of `force-include`, or a `compiled/`
# tree that was never generated, fails here and in no other target.
#
# Both console scripts run. The second one proves the SourceCatalogRelease v1
# candidate from the installed package — required exports, bundle digest, and
# every sealed fixture verdict. Deleting an export or a packaged data file must
# turn this red; it must never be softened into a skip.
test-package:
	rm -rf dist "$(PACKAGE_CHECK_DIR)"
	uv build --wheel
	uv venv --python 3.12 "$(PACKAGE_CHECK_DIR)"
	VIRTUAL_ENV="$(PACKAGE_CHECK_DIR)" uv pip install --quiet dist/*.whl
	cd "$(PACKAGE_CHECK_DIR)" && ./bin/rulespec-ci-validate
	cd "$(PACKAGE_CHECK_DIR)" && ./bin/rulespec-source-catalog-validate
	cd "$(PACKAGE_CHECK_DIR)" && ./bin/rulespec-document-validate
	rm -rf "$(PACKAGE_CHECK_DIR)"

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
	$(PYTHON) -m unittest tools.test_constraints_compile tools.test_l0_mapping_audit tools.test_semantic_carriers tools.test_reference_release_digest tools.test_rulespec_releases tools.test_extrapolation_release_v2 tools.test_atlas_membership_stub tools.test_source_catalog_release tools.test_document_release -v
	$(PYTHON) tools/build_source_catalog_release_fixtures.py --check
	$(PYTHON) tools/build_document_release_fixtures.py --check
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
# `cue-vet` validates CUE source syntax with the CUE compiler proper before
# tools/constraints_compile.py (a bespoke, non-CUE-aware parser) projects it
# to other targets. Split into two invocations because `cue vet` unifies every
# file passed together into one instance: the `rkaf` package (core, analysis,
# adversarial, ai-extraction, profiles/<profile>/*.cue) and the standalone
# `semantics` package (the L0 range registries, one per kernel/analysis/
# profile directory) are separate packages and cannot be vetted in one call.
cue-vet:
	$(CUE) vet constraints/core/*.cue constraints/analysis/*.cue constraints/adversarial/*.cue constraints/ai-extraction/*.cue constraints/profiles/*/*.cue
	$(CUE) vet constraints/semantics/*.cue constraints/analysis/*/*.cue constraints/profiles/*/*/*.cue

# `compile` drives every primitive through every target via the single
# canonical wrapper. Writes Rust to crates/rkaf-core/src/generated/ (tracked);
# other targets to compiled/<target>/<sub>/ (gitignored).

compile:
	PYTHON="$(PYTHON)" tools/compile_all.sh

# ─── Clean ─────────────────────────────────────────────────────────────

clean:
	$(CARGO) clean $(CARGO_MANIFEST)
