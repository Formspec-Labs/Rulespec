#!/usr/bin/env python3
"""Compare two installed artifact-wheel encoders against the shared corpus."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "packages" / "rulespec-artifacts" / "tests" / "canonical_corpus_runner.py"
CORPUS = ROOT / "platform-fixtures" / "canonical-json" / "corpus.json"


def _environment_python(root: Path) -> Path:
    return root / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _evaluate(wheel: Path, root: Path) -> dict[str, object]:
    venv.EnvBuilder(with_pip=True, clear=True).create(root)
    python = _environment_python(root)
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            "--quiet",
            str(wheel.resolve()),
        ],
        check=True,
    )
    completed = subprocess.run(
        [str(python), str(RUNNER), "--corpus", str(CORPUS), "--json"],
        check=True,
        cwd=root,
        text=True,
        capture_output=True,
    )
    value = json.loads(completed.stdout)
    if not isinstance(value, dict):
        raise TypeError("corpus runner did not return a JSON object")
    return value


def _behavior(report: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in report.items() if key != "packageVersion"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-wheel", type=Path, required=True)
    parser.add_argument("--candidate-wheel", type=Path, required=True)
    args = parser.parse_args()
    for wheel in (args.previous_wheel, args.candidate_wheel):
        if not wheel.is_file():
            parser.error(f"wheel does not exist: {wheel}")

    with tempfile.TemporaryDirectory(prefix="rulespec-encoder-compare-") as directory:
        root = Path(directory)
        previous = _evaluate(args.previous_wheel, root / "previous")
        candidate = _evaluate(args.candidate_wheel, root / "candidate")

    previous_version = previous.get("packageVersion")
    candidate_version = candidate.get("packageVersion")
    if previous_version == candidate_version:
        print(
            "previous and candidate wheels have the same rulespec-artifacts version",
            file=sys.stderr,
        )
        return 1
    if _behavior(previous) != _behavior(candidate):
        print("canonical encoder behavior changed; use a new format major", file=sys.stderr)
        return 1
    total = sum(
        len(candidate[key])
        for key in ("encodeAccepted", "encodeRejected", "parseRejected")
    )
    print(
        f"canonical encoder behavior preserved from {previous_version} to "
        f"{candidate_version} across {total} cases"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
