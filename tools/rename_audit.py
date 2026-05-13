#!/usr/bin/env python3
"""Rulespec rename audit.

Walks the repo and reports every occurrence of:
  - `pkaf:` prefix (JSON-LD, Turtle, code)
  - `PKAF` brand token (markdown, comments)
  - `https://w3id.org/pkaf/` IRI namespace
  - `urn:pkaf:` URN scheme
  - filenames matching `pkaf-*` or `pkaf_*` or `*pkaf*`

Exit codes:
  0 — clean (no occurrences)
  1 — occurrences found (printed, grouped by class)
  2 — setup error
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ordered: most specific patterns first so multi-class lines attribute correctly
PATTERNS = [
    ("iri-w3id",      re.compile(r"https://w3id\.org/pkaf/")),
    ("urn-pkaf",      re.compile(r"urn:pkaf:")),
    ("prefix-pkaf",   re.compile(r"\bpkaf:")),
    ("brand-PKAF",    re.compile(r"\bPKAF\b")),
    ("brand-pkaf",    re.compile(r"\bpkaf\b(?!:)")),  # bare "pkaf" not followed by colon
]

# directories never audited
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "target", "thoughts"}
# file extensions audited
EXTS = {".md", ".py", ".rs", ".ts", ".js", ".mjs", ".json", ".jsonld",
        ".ttl", ".yaml", ".yml", ".toml", ".sh", ".cue"}

def walk(root: Path):
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if not p.is_file():
            continue
        if p.suffix not in EXTS and p.name not in {"Makefile", "VERSION"}:
            continue
        yield p

def audit(root: Path):
    findings = {name: [] for name, _ in PATTERNS}
    name_findings = []
    for path in walk(root):
        rel = path.relative_to(root)
        # filename match
        if "pkaf" in path.name.lower():
            name_findings.append(str(rel))
        # content match
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, PermissionError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for name, pat in PATTERNS:
                if pat.search(line):
                    findings[name].append((str(rel), lineno, line.rstrip()))
                    break  # attribute to first matching class only
    return findings, name_findings

def main():
    findings, name_findings = audit(ROOT)
    total = sum(len(v) for v in findings.values()) + len(name_findings)
    print(f"Rulespec rename audit — root: {ROOT}")
    print(f"Total findings: {total}")
    print(f"  Filename matches: {len(name_findings)}")
    for name, hits in findings.items():
        print(f"  {name}: {len(hits)}")
    if total == 0:
        print("CLEAN")
        return 0
    print("\n--- Filename matches ---")
    for f in sorted(name_findings):
        print(f"  {f}")
    for name, hits in findings.items():
        if not hits:
            continue
        print(f"\n--- {name} ({len(hits)}) ---")
        for path, lineno, line in hits[:50]:
            print(f"  {path}:{lineno}: {line[:160]}")
        if len(hits) > 50:
            print(f"  ... {len(hits) - 50} more")
    return 1

if __name__ == "__main__":
    sys.exit(main())
