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

.PHONY: all help build build-runtime-cli test test-rust test-shapes test-reference-corpora test-audits test-conformance test-package test-package-artifacts test-package-conformance test-package-projection test-artifact-encoder-compat clean compile cue-vet

# Scratch venvs for installed-wheel checks. Each stays outside the tree so no
# source checkout can satisfy an import. Keeping the artifact-only environment
# separate also proves its dependency closure excludes the graph stack.
ARTIFACT_PACKAGE_CHECK_DIR = $(shell printf '%s' "$${TMPDIR:-/tmp}")rulespec-artifact-package-check
CONFORMANCE_PACKAGE_CHECK_DIR = $(shell printf '%s' "$${TMPDIR:-/tmp}")rulespec-conformance-package-check
PROJECTION_PACKAGE_CHECK_DIR = $(shell printf '%s' "$${TMPDIR:-/tmp}")rulespec-projection-package-check
ARTIFACT_WHEEL_GLOB = dist/artifacts/rulespec_artifacts-*.whl
PROJECTION_WHEEL_GLOB = dist/projection/rulespec_projection-*.whl
PREVIOUS_ARTIFACT_WHEEL ?=

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
	@echo "  make test-package       — run every installed-wheel check outside the checkout"
	@echo "  make test-package-artifacts — prove the artifact-only wheel and dependency closure"
	@echo "  make test-package-conformance — prove the full graph validator wheel"
	@echo "  make test-package-projection — prove the projection wheel and its empty dependency closure"
	@echo "  make test-artifact-encoder-compat PREVIOUS_ARTIFACT_WHEEL=... — compare release encoders"
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

# The artifact wheel and graph validator use separate environments. Installing
# both together cannot prove that an artifact-only consumer avoids RDF/SHACL.
test-package: test-package-conformance test-package-projection

test-package-artifacts:
	rm -rf dist/artifacts "$(ARTIFACT_PACKAGE_CHECK_DIR)"
	uv run --project packages/rulespec-artifacts python -m unittest discover -s packages/rulespec-artifacts/tests -p 'test_*.py'
	uv build --project packages/rulespec-artifacts --wheel --out-dir dist/artifacts
	uv venv --python 3.12 "$(ARTIFACT_PACKAGE_CHECK_DIR)"
	VIRTUAL_ENV="$(ARTIFACT_PACKAGE_CHECK_DIR)" uv pip install --quiet $(ARTIFACT_WHEEL_GLOB)
	cd "$(ARTIFACT_PACKAGE_CHECK_DIR)" && ./bin/python -c 'import importlib.util; import rulespec_artifacts as package; from importlib.metadata import distributions, requires, version; excluded={"rdfcanon", "rdflib", "pyshacl"}; installed={item.metadata["Name"].lower() for item in distributions() if item.metadata["Name"]}; assert version("rulespec-artifacts") == package.__version__; assert not requires("rulespec-artifacts"); assert not installed & excluded; assert all(importlib.util.find_spec(name) is None for name in excluded)'
	cd "$(ARTIFACT_PACKAGE_CHECK_DIR)" && ./bin/python -c 'import rulespec_artifacts as p; from rulespec_artifacts import resources; assert p.FORMAT == "spicy-artifact"; assert resources.platform_artifact_spec(); assert resources.fixture_corpus()["cases"]; assert resources.canonical_json_corpus()["encodeAccepted"]; assert resources.fixture("valid").is_dir()'
	cd "$(ARTIFACT_PACKAGE_CHECK_DIR)" && ./bin/python "$(CURDIR)/packages/rulespec-artifacts/tests/canonical_corpus_runner.py"
	cd "$(ARTIFACT_PACKAGE_CHECK_DIR)" && ./bin/python -c 'from pathlib import Path; from rulespec_artifacts import LocalMemberSource, verify_artifact; from rulespec_artifacts import resources; corpus=resources.fixture_corpus(); observed={case["name"]: verify_artifact(LocalMemberSource(Path(str(resources.fixture(case["name"]))))).code for case in corpus["cases"]}; assert observed == {case["name"]: case["expectedCode"] for case in corpus["cases"]}'
	cd "$(ARTIFACT_PACKAGE_CHECK_DIR)" && ./bin/python -c 'import tempfile; import rulespec_artifacts as package; from pathlib import Path; from rulespec_artifacts import LocalMemberSource, Producer, ROOT_OBJECT_KEY, admit_artifact, build_artifact_root, canonical_json_bytes; temporary=tempfile.TemporaryDirectory(); root=Path(temporary.name); producer=Producer("test-product", "git:https://example.test/product@" + "1" * 40, "urn:test:verifier", "1", f"pkg:pypi/rulespec-artifacts@{package.__version__}?checksum=sha256:" + "2" * 64); artifact=build_artifact_root(kind="unknown-test-kind", spec={"fixture": "1"}, producer=producer); (root / ROOT_OBJECT_KEY).write_bytes(canonical_json_bytes(artifact)); admitted=admit_artifact(LocalMemberSource(root)); assert admitted.root == artifact; temporary.cleanup()'
	rm -rf "$(ARTIFACT_PACKAGE_CHECK_DIR)"

test-package-conformance: test-package-artifacts
	rm -rf dist/conformance "$(CONFORMANCE_PACKAGE_CHECK_DIR)"
	uv build --wheel --out-dir dist/conformance
	uv venv --python 3.12 "$(CONFORMANCE_PACKAGE_CHECK_DIR)"
	VIRTUAL_ENV="$(CONFORMANCE_PACKAGE_CHECK_DIR)" uv pip install --quiet $(ARTIFACT_WHEEL_GLOB) dist/conformance/*.whl
	cd "$(CONFORMANCE_PACKAGE_CHECK_DIR)" && ./bin/rulespec-ci-validate
	cd "$(CONFORMANCE_PACKAGE_CHECK_DIR)" && ./bin/python -m rulespec_conformance.contract
	cd "$(CONFORMANCE_PACKAGE_CHECK_DIR)" && ./bin/python -c 'import importlib.util; from importlib.metadata import entry_points; assert importlib.util.find_spec("rulespec_conformance.source_catalog_release") is None; assert importlib.util.find_spec("rulespec_conformance.document_release") is None; names = {item.name for item in entry_points(group="console_scripts")}; assert "rulespec-source-catalog-validate" not in names; assert "rulespec-document-validate" not in names'
	rm -rf "$(CONFORMANCE_PACKAGE_CHECK_DIR)"

# The projection wheel declares no dependencies and must import none: its price
# was zero new dependencies, so the installed-wheel check proves the closure is
# empty and then runs the package's own suite against the installed copy (the
# parity fixtures were derived from spicy-regs 8d9e7a2, not from this code).
test-package-projection:
	rm -rf dist/projection "$(PROJECTION_PACKAGE_CHECK_DIR)"
	uv run --project packages/rulespec-projection python -m unittest discover -s packages/rulespec-projection/tests -p 'test_*.py'
	uv build --project packages/rulespec-projection --wheel --out-dir dist/projection
	uv venv --python 3.12 "$(PROJECTION_PACKAGE_CHECK_DIR)"
	VIRTUAL_ENV="$(PROJECTION_PACKAGE_CHECK_DIR)" uv pip install --quiet $(PROJECTION_WHEEL_GLOB)
	cd "$(PROJECTION_PACKAGE_CHECK_DIR)" && ./bin/python -c 'import sys; import rulespec_projection as package; from importlib.metadata import distributions, requires, version; assert version("rulespec-projection") == package.__version__; assert not requires("rulespec-projection"); installed={item.metadata["Name"].lower() for item in distributions() if item.metadata["Name"]}; assert installed == {"rulespec-projection"}, installed; loaded=sorted(name for name in sys.modules if name.partition(".")[0] not in sys.stdlib_module_names and not name.startswith(("rulespec_projection", "_"))); assert loaded == [], loaded'
	cd "$(PROJECTION_PACKAGE_CHECK_DIR)" && ./bin/python -m unittest discover -s "$(CURDIR)/packages/rulespec-projection/tests" -p 'test_*.py'
	rm -rf "$(PROJECTION_PACKAGE_CHECK_DIR)"

test-artifact-encoder-compat: test-package-artifacts
	test -n "$(PREVIOUS_ARTIFACT_WHEEL)"
	uv run --no-project --python 3.12 python tools/compare_artifact_encoders.py --previous-wheel "$(PREVIOUS_ARTIFACT_WHEEL)" --candidate-wheel $(ARTIFACT_WHEEL_GLOB)

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
	$(PYTHON) -m unittest tools.test_constraints_compile tools.test_l0_mapping_audit tools.test_semantic_carriers tools.test_reference_release_digest tools.test_rulespec_releases tools.test_extrapolation_release_v2 tools.test_atlas_membership_stub tools.test_platform_artifact tools.test_contract_exports -v
	$(PYTHON) tools/build_platform_artifact_fixtures.py --check
	$(PYTHON) tools/build_contract_exports.py --check
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
	$(CUE) vet constraints/platform/*.cue

# `compile` drives every primitive through every target via the single
# canonical wrapper. Writes Rust to crates/rkaf-core/src/generated/ (tracked);
# other targets to compiled/<target>/<sub>/ (gitignored).

compile:
	PYTHON="$(PYTHON)" tools/compile_all.sh

# ─── Clean ─────────────────────────────────────────────────────────────

clean:
	$(CARGO) clean $(CARGO_MANIFEST)
