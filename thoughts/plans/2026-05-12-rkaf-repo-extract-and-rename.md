# Repo Extract + Brand/IRI Rename Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract `formspec-stack/PKAF/` into a public `formspec/rulespec` GitHub repository, submodule it back into formspec-stack as `rulespec/`, and complete the PKAF→Rulespec brand rename across every implementation artifact (file paths, IRIs, prefixes, JSON-LD context, SHACL shapes, Python tools, fixtures, reports).

**Architecture:** One-shot rename. No symlink shims, no compatibility re-exports. The current `PKAF/` tree becomes the seed of the public repo; brand-name strings change in place; the result is committed and tagged before extraction. After extraction, formspec-stack adds the new repo as a submodule at `rulespec/` and removes the in-tree `PKAF/`.

**Tech Stack:** git, git submodules, GitHub CLI (`gh`), `rg` for the rename audit, Python 3 (existing `tools/ci_validate.py`), `pyshacl` for SHACL parity check.

---

## File structure

**New repository: `formspec/rulespec` (public, GitHub).** Seeded from `PKAF/` with brand-renamed contents:

```
rulespec/
├── README.md                           # rewritten (covered in plan 11)
├── LICENSE                             # unchanged
├── LICENSE-CODE                        # unchanged
├── LICENSE-SPEC                        # unchanged
├── CONTRIBUTING.md                     # rebranded prose
├── CHANGELOG.md                        # appended with rename entry; new initial v0.2 section in plan 11
├── VERSION                             # bumped to "0.2.0-pre.1"
├── v0.1.1-release-manifest.md          # archived under reports/, renamed to reports/v0.1.1-release-manifest.md (already there) — top-level copy removed
├── spec/
│   ├── rkaf-core-v0.1.md               # renamed from pkaf-core-v0.1.md (frontmatter + body brand-renamed)
│   ├── rkaf-concept-registry-v0.1.2.md # renamed from pkaf-concept-registry-v0.1.2.md
│   └── README.md                       # rebranded
├── context/
│   ├── rkaf-context-v0.1.jsonld        # renamed; @context entries rewritten
│   ├── rkaf-context-v0.2.jsonld        # renamed; @context entries rewritten
│   └── README.md                       # rebranded
├── shapes/
│   ├── rkaf-shapes-core-v0.1.ttl       # renamed; rkaf: prefix declared; pkaf: removed
│   ├── rkaf-shapes-conceptregistry-v0.1.ttl
│   ├── rkaf-shapes-lifecycle-v0.1.ttl
│   ├── rkaf-shapes-justification-v0.1.ttl
│   └── README.md                       # rebranded
├── fixtures/
│   ├── context.jsonld                  # @context references updated
│   ├── local-operational-v0.2.jsonld   # pkaf: → rkaf: in JSON-LD payload
│   ├── mapping-v0.1.jsonld
│   ├── statutory-authority-v0.1.jsonld
│   ├── registry-failure-conflict-v0.1.jsonld
│   ├── narratives/                     # markdown brand-renamed
│   └── README.md                       # rebranded
├── tools/
│   ├── ci_validate.py                  # MODES keys, prints, paths updated; class:`PKAF` strings → `RKAF`/`Rulespec`
│   ├── rename_audit.py                 # NEW — created in this plan; greps for residual pkaf:/PKAF strings
│   └── README.md                       # rebranded
├── reports/
│   ├── batch1-shapes.md
│   ├── batch1.1-patches.md
│   ├── batch2-validation-report.md
│   ├── batch3-validation-report.md
│   ├── batch4-validation-report.md
│   ├── v0.1-rc1-manifest.md
│   ├── v0.1.1-release-manifest.md      # historical; brand-rename inline references in prose
│   └── README.md
├── thoughts/
│   ├── specs/
│   │   └── 2026-05-12-pkaf-as-public-schema-interop-framework.md   # filename retained (historical artifact); body uses Rulespec branding already
│   └── plans/
│       └── 2026-05-12-rkaf-*.md        # this plan set
└── requirements.txt                    # unchanged
```

**formspec-stack/** changes:

- `formspec-stack/.gitmodules` — adds `rulespec` entry pointing to new public repo URL.
- `formspec-stack/rulespec/` — submodule placeholder (populated after `git submodule add`).
- `formspec-stack/PKAF/` — removed in same parent commit that adds `rulespec/`.
- `formspec-stack/CLAUDE.md` — table row updated: PKAF row replaced with Rulespec row pointing at `rulespec/`.
- `formspec-stack/Makefile` — if PKAF targets exist (verify in Task 1), rename to `rulespec`.
- `formspec-stack/scripts/generate-filemap.mjs` — if it scans `PKAF/`, update path.

---

## Task 1: Audit current PKAF→Rulespec rename surface

**Files:**
- Create: `/Users/mikewolfd/Work/formspec-stack/PKAF/tools/rename_audit.py`

- [ ] **Step 1: Write the audit script (deterministic enumeration of every renamed surface)**

```python
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
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "target"}
# file extensions audited
EXTS = {".md", ".py", ".rs", ".ts", ".js", ".mjs", ".json", ".jsonld",
        ".ttl", ".yaml", ".yml", ".toml", ".sh"}

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
```

- [ ] **Step 2: Run the audit on the current PKAF tree to capture the baseline**

Run: `python3 /Users/mikewolfd/Work/formspec-stack/PKAF/tools/rename_audit.py | tee /tmp/rkaf-rename-baseline.txt`

Expected: Exit 1 with hundreds of findings. Capture the output as the baseline; the rename is complete when the audit exits 0.

- [ ] **Step 3: Commit the audit script**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
git add tools/rename_audit.py
git commit -m "build(tools): add rkaf rename audit script"
```

## Task 2: Rename in-tree filenames (spec, context, shapes)

**Files:**
- Rename: `PKAF/spec/pkaf-core-v0.1.md` → `PKAF/spec/rkaf-core-v0.1.md`
- Rename: `PKAF/spec/pkaf-concept-registry-v0.1.2.md` → `PKAF/spec/rkaf-concept-registry-v0.1.2.md`
- Rename: `PKAF/context/pkaf-context-v0.1.jsonld` → `PKAF/context/rkaf-context-v0.1.jsonld`
- Rename: `PKAF/context/pkaf-context-v0.2.jsonld` → `PKAF/context/rkaf-context-v0.2.jsonld`
- Rename: `PKAF/shapes/pkaf-shapes-core-v0.1.ttl` → `PKAF/shapes/rkaf-shapes-core-v0.1.ttl`
- Rename: `PKAF/shapes/pkaf-shapes-conceptregistry-v0.1.ttl` → `PKAF/shapes/rkaf-shapes-conceptregistry-v0.1.ttl`
- Rename: `PKAF/shapes/pkaf-shapes-lifecycle-v0.1.ttl` → `PKAF/shapes/rkaf-shapes-lifecycle-v0.1.ttl`
- Rename: `PKAF/shapes/pkaf-shapes-justification-v0.1.ttl` → `PKAF/shapes/rkaf-shapes-justification-v0.1.ttl`

- [ ] **Step 1: Rename via `git mv` (preserves history)**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
git mv spec/pkaf-core-v0.1.md spec/rkaf-core-v0.1.md
git mv spec/pkaf-concept-registry-v0.1.2.md spec/rkaf-concept-registry-v0.1.2.md
git mv context/pkaf-context-v0.1.jsonld context/rkaf-context-v0.1.jsonld
git mv context/pkaf-context-v0.2.jsonld context/rkaf-context-v0.2.jsonld
git mv shapes/pkaf-shapes-core-v0.1.ttl shapes/rkaf-shapes-core-v0.1.ttl
git mv shapes/pkaf-shapes-conceptregistry-v0.1.ttl shapes/rkaf-shapes-conceptregistry-v0.1.ttl
git mv shapes/pkaf-shapes-lifecycle-v0.1.ttl shapes/rkaf-shapes-lifecycle-v0.1.ttl
git mv shapes/pkaf-shapes-justification-v0.1.ttl shapes/rkaf-shapes-justification-v0.1.ttl
```

- [ ] **Step 2: Verify the renames landed**

Run: `git status`
Expected: 8 renames listed under "renamed:" lines. No unstaged changes in those files (yet — content edit comes in Task 3).

- [ ] **Step 3: Commit the renames as a separate commit (history-preserving)**

```bash
git commit -m "refactor(rkaf): rename pkaf-* artifact filenames to rkaf-*"
```

## Task 3: Rewrite IRI namespace and prefix in JSON-LD context (v0.2)

**Files:**
- Modify: `PKAF/context/rkaf-context-v0.2.jsonld` (every `pkaf:` key → `rkaf:`; `https://w3id.org/pkaf/ns/v1#` → `https://rulespec.org/ns/v1#`)

- [ ] **Step 1: Write a failing audit assertion**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
python3 -c "
import json
ctx = json.load(open('context/rkaf-context-v0.2.jsonld'))['@context']
assert 'rkaf' in ctx and ctx['rkaf'] == 'https://rulespec.org/ns/v1#', f\"got {ctx.get('rkaf')!r}\"
assert 'pkaf' not in ctx, 'pkaf prefix must not remain'
"
```

Expected: AssertionError on the first assertion (`rkaf` key not yet present).

- [ ] **Step 2: Apply the rewrite**

Use `sed` only because the JSON-LD context is a flat key-value map; for the spec/SHACL files (Task 4+) a code-aware rewrite is required.

```bash
sed -i.bak \
  -e 's|"pkaf":|"rkaf":|g' \
  -e 's|"pkaf:|"rkaf:|g' \
  -e 's|https://w3id.org/pkaf/|https://rulespec.org/|g' \
  context/rkaf-context-v0.2.jsonld
rm context/rkaf-context-v0.2.jsonld.bak
```

- [ ] **Step 3: Re-run the assertion**

Same command as Step 1.
Expected: No assertion error; exit 0.

- [ ] **Step 4: Apply the same rewrite to v0.1 context**

```bash
sed -i.bak \
  -e 's|"pkaf":|"rkaf":|g' \
  -e 's|"pkaf:|"rkaf:|g' \
  -e 's|https://w3id.org/pkaf/|https://rulespec.org/|g' \
  context/rkaf-context-v0.1.jsonld
rm context/rkaf-context-v0.1.jsonld.bak
```

- [ ] **Step 5: Validate JSON-LD parses**

```bash
python3 -c "
import json
for p in ['context/rkaf-context-v0.1.jsonld', 'context/rkaf-context-v0.2.jsonld']:
    json.load(open(p))
    print(f'{p}: parses OK')
"
```

Expected: Both files print `parses OK`.

- [ ] **Step 6: Commit**

```bash
git add context/
git commit -m "refactor(rkaf): rewrite JSON-LD contexts to rkaf prefix and rulespec.org IRI namespace"
```

## Task 4: Rewrite SHACL shape files (Turtle prefixes + IRIs)

**Files:**
- Modify: `PKAF/shapes/rkaf-shapes-core-v0.1.ttl`
- Modify: `PKAF/shapes/rkaf-shapes-conceptregistry-v0.1.ttl`
- Modify: `PKAF/shapes/rkaf-shapes-lifecycle-v0.1.ttl`
- Modify: `PKAF/shapes/rkaf-shapes-justification-v0.1.ttl`

- [ ] **Step 1: Confirm pyshacl can parse the files (baseline)**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
python3 -c "
import rdflib
for f in ['shapes/rkaf-shapes-core-v0.1.ttl','shapes/rkaf-shapes-conceptregistry-v0.1.ttl','shapes/rkaf-shapes-lifecycle-v0.1.ttl','shapes/rkaf-shapes-justification-v0.1.ttl']:
    g = rdflib.Graph(); g.parse(f, format='turtle'); print(f, len(g), 'triples')
"
```

Expected: Each file prints triple count, no exceptions.

- [ ] **Step 2: Rewrite the prefix declarations and IRIs**

```bash
for f in shapes/rkaf-shapes-*.ttl; do
  sed -i.bak \
    -e 's|@prefix pkaf:|@prefix rkaf:|g' \
    -e 's|<https://w3id.org/pkaf/|<https://rulespec.org/|g' \
    -e 's|pkaf:|rkaf:|g' \
    "$f"
  rm "${f}.bak"
done
```

- [ ] **Step 3: Re-parse to verify integrity**

Same parse loop as Step 1.
Expected: Same triple counts (parser sees the same graph; only prefix labels and IRI host changed).

- [ ] **Step 4: Commit**

```bash
git add shapes/
git commit -m "refactor(rkaf): rewrite SHACL shapes to rkaf prefix and rulespec.org IRI namespace"
```

## Task 5: Rewrite fixtures (JSON-LD payloads)

**Files:**
- Modify: every file in `PKAF/fixtures/*.jsonld`

- [ ] **Step 1: Write a failing parse-and-validate assertion**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
python3 -c "
import json
for p in ['fixtures/context.jsonld','fixtures/local-operational-v0.2.jsonld','fixtures/mapping-v0.1.jsonld','fixtures/statutory-authority-v0.1.jsonld','fixtures/registry-failure-conflict-v0.1.jsonld']:
    txt = open(p).read()
    assert 'pkaf:' not in txt, f'pkaf: still present in {p}'
    assert 'rkaf:' in txt, f'rkaf: not yet present in {p}'
"
```

Expected: AssertionError on first fixture (`pkaf:` still present).

- [ ] **Step 2: Rewrite all fixtures**

```bash
for f in fixtures/*.jsonld; do
  sed -i.bak \
    -e 's|"pkaf":|"rkaf":|g' \
    -e 's|"pkaf:|"rkaf:|g' \
    -e 's|https://w3id.org/pkaf/|https://rulespec.org/|g' \
    "$f"
  rm "${f}.bak"
done
```

- [ ] **Step 3: Verify each fixture still parses as JSON**

```bash
python3 -c "
import json
for p in ['fixtures/context.jsonld','fixtures/local-operational-v0.2.jsonld','fixtures/mapping-v0.1.jsonld','fixtures/statutory-authority-v0.1.jsonld','fixtures/registry-failure-conflict-v0.1.jsonld']:
    json.load(open(p)); print(p, 'OK')
"
```

Expected: Each fixture prints `OK`.

- [ ] **Step 4: Commit**

```bash
git add fixtures/
git commit -m "refactor(rkaf): rewrite JSON-LD fixtures to rkaf prefix"
```

## Task 6: Rewrite the Python validator (`tools/ci_validate.py`)

**Files:**
- Modify: `PKAF/tools/ci_validate.py` — every `PKAF` brand string → `Rulespec`/`RKAF`; every `pkaf-shapes-*.ttl` path → `rkaf-shapes-*.ttl`

- [ ] **Step 1: Write a failing assertion**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
grep -c 'rkaf-shapes' tools/ci_validate.py
```

Expected: `0` (no occurrences yet).

- [ ] **Step 2: Apply the rewrite**

Use the Edit tool, not sed, because this is code:

Replace every occurrence in `tools/ci_validate.py`:
- `"shapes/pkaf-shapes-core-v0.1.ttl"` → `"shapes/rkaf-shapes-core-v0.1.ttl"`
- `"shapes/pkaf-shapes-conceptregistry-v0.1.ttl"` → `"shapes/rkaf-shapes-conceptregistry-v0.1.ttl"`
- `"shapes/pkaf-shapes-lifecycle-v0.1.ttl"` → `"shapes/rkaf-shapes-lifecycle-v0.1.ttl"`
- `"shapes/pkaf-shapes-justification-v0.1.ttl"` → `"shapes/rkaf-shapes-justification-v0.1.ttl"`
- Module docstring: `"""PKAF CI validation gate (multi-mode)."""` → `"""Rulespec CI validation gate (multi-mode)."""`
- Mode label strings: `"PKAF v0.1-rc1 Core"` → `"RKAF v0.1-rc1 Core"` (and similarly for batch2/batch3/batch4 labels)
- `print(f"PKAF CI validation gate — mode: {args.mode}")` → `print(f"Rulespec CI validation gate — mode: {args.mode}")`
- `parser = argparse.ArgumentParser(description="PKAF multi-mode CI validation gate")` → `parser = argparse.ArgumentParser(description="Rulespec multi-mode CI validation gate")`

- [ ] **Step 3: Verify the validator still runs**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
python3 tools/ci_validate.py --mode batch4
```

Expected: Output begins with `Rulespec CI validation gate — mode: batch4` and ends with `Result: PASS`. Exit 0. Triple counts unchanged from the v0.1.1 baseline (the rename does not change the SHACL graph).

- [ ] **Step 4: Commit**

```bash
git add tools/ci_validate.py
git commit -m "refactor(rkaf): rebrand ci_validate.py and point at rkaf-shapes-* files"
```

## Task 7: Rewrite spec body brand tokens (`spec/rkaf-core-v0.1.md`, `spec/rkaf-concept-registry-v0.1.2.md`)

**Files:**
- Modify: `PKAF/spec/rkaf-core-v0.1.md`
- Modify: `PKAF/spec/rkaf-concept-registry-v0.1.2.md`

These are normative spec text. Brand-rename inline; do not change semantics.

- [ ] **Step 1: Apply scoped sed to in-prose tokens**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
for f in spec/rkaf-core-v0.1.md spec/rkaf-concept-registry-v0.1.2.md; do
  sed -i.bak \
    -e 's|`pkaf:|`rkaf:|g' \
    -e 's|`pkaf-|`rkaf-|g' \
    -e 's|https://w3id.org/pkaf/|https://rulespec.org/|g' \
    -e 's|\bPKAF\b|Rulespec|g' \
    -e 's|\bpkaf\b|rkaf|g' \
    "$f"
  rm "${f}.bak"
done
```

- [ ] **Step 2: Verify the spec body cleanly references the renamed shapes/context**

```bash
grep -n "pkaf" spec/rkaf-core-v0.1.md spec/rkaf-concept-registry-v0.1.2.md
```

Expected: No output (zero matches).

- [ ] **Step 3: Commit**

```bash
git add spec/
git commit -m "docs(rkaf): rebrand spec body PKAF→Rulespec / pkaf:→rkaf:"
```

## Task 8: Rewrite reports/, narratives/, READMEs, CONTRIBUTING.md, CHANGELOG.md

**Files:**
- Modify: `PKAF/reports/*.md` (historical batch reports + manifests)
- Modify: `PKAF/fixtures/narratives/*.md`
- Modify: `PKAF/{spec,context,shapes,fixtures,tools,reports}/README.md`
- Modify: `PKAF/CONTRIBUTING.md`
- Modify: `PKAF/CHANGELOG.md`
- Modify: `PKAF/README.md`

- [ ] **Step 1: Bulk rebrand in markdown**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
find reports fixtures/narratives spec context shapes tools \
     CONTRIBUTING.md CHANGELOG.md README.md \
  -name '*.md' -type f | while read f; do
  sed -i.bak \
    -e 's|`pkaf:|`rkaf:|g' \
    -e 's|`pkaf-|`rkaf-|g' \
    -e 's|pkaf-shapes-|rkaf-shapes-|g' \
    -e 's|pkaf-context-|rkaf-context-|g' \
    -e 's|pkaf-core-|rkaf-core-|g' \
    -e 's|pkaf-concept-registry-|rkaf-concept-registry-|g' \
    -e 's|https://w3id.org/pkaf/|https://rulespec.org/|g' \
    -e 's|\bPKAF\b|Rulespec|g' \
    "$f"
  rm "${f}.bak"
done
```

- [ ] **Step 2: Append a CHANGELOG entry for the rename**

Edit `PKAF/CHANGELOG.md`. Insert at the top (under any existing pre-release section header):

```markdown
## v0.2.0-pre.1 — Brand rename: PKAF → Rulespec

- The framework is renamed to **Rulespec** (acronym **RKAF**, "Rulespec Knowledge Assertion Framework").
- Vocabulary prefix `pkaf:` is renamed to `rkaf:` everywhere in shapes, JSON-LD contexts, fixtures, and spec bodies.
- IRI namespace `https://w3id.org/pkaf/` is renamed to `https://rulespec.org/`.
- All `pkaf-*` artifact filenames are renamed to `rkaf-*` (`spec/pkaf-core-v0.1.md` → `spec/rkaf-core-v0.1.md` etc.).
- This is a wholesale rename. There is no compatibility shim and no `pkaf:` prefix is supported in v0.2 or later.
```

- [ ] **Step 3: Run the rename audit**

```bash
python3 tools/rename_audit.py
```

Expected: Exit 0 (CLEAN). If not, the printed findings tell you where residual `pkaf:` / `PKAF` strings remain — fix in place and rerun until clean.

- [ ] **Step 4: Commit**

```bash
git add reports/ fixtures/narratives/ spec/README.md context/README.md shapes/README.md fixtures/README.md tools/README.md reports/README.md CONTRIBUTING.md CHANGELOG.md README.md
git commit -m "docs(rkaf): rebrand README/CHANGELOG/CONTRIBUTING/reports/narratives"
```

## Task 9: Bump VERSION

**Files:**
- Modify: `PKAF/VERSION`

- [ ] **Step 1: Set the version**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
echo "0.2.0-pre.1" > VERSION
```

- [ ] **Step 2: Commit**

```bash
git add VERSION
git commit -m "chore(rkaf): bump VERSION to 0.2.0-pre.1"
```

## Task 10: Final pre-extraction validation

**Files:**
- (no edits) verify the renamed tree is internally consistent

- [ ] **Step 1: Run the rename audit once more**

```bash
cd /Users/mikewolfd/Work/formspec-stack/PKAF
python3 tools/rename_audit.py
```

Expected: Exit 0 (CLEAN).

- [ ] **Step 2: Run the SHACL validator end-to-end**

```bash
python3 tools/ci_validate.py --mode batch4
```

Expected: `Result: PASS`. Total triples ~1206 (matches v0.1.1 baseline; the rename touches labels, not graph structure).

- [ ] **Step 3: Verify no broken intra-repo references**

```bash
grep -rn "shapes/pkaf-" .  || echo "no stale shape refs"
grep -rn "context/pkaf-" . || echo "no stale context refs"
grep -rn "spec/pkaf-"    . || echo "no stale spec refs"
```

Expected: All three print `no stale * refs`.

## Task 11: Create the public `formspec/rulespec` repo on GitHub

- [ ] **Step 1: Create the empty public repo via gh**

```bash
gh repo create formspec/rulespec \
  --public \
  --description "Rulespec (RKAF) — Knowledge Assertion Framework: vendor-neutral federation substrate for evidence-grounded structured claims" \
  --homepage "https://rulespec.org" \
  --license "Apache-2.0" \
  --confirm
```

Expected: `gh` prints the new repo URL `https://github.com/formspec/rulespec`.

- [ ] **Step 2: Stop here if `formspec` org doesn't yet exist or you lack rights**

If the gh command errors with `not found` for the `formspec` org, that organization needs to be created (out of scope for this plan; the owner handles GitHub org creation). Resume Task 11 once the org exists.

## Task 12: Push the renamed PKAF tree as the seed of the new repo

- [ ] **Step 1: Make a fresh clone of the PKAF subtree as a standalone repo**

The existing PKAF git history is part of formspec-stack; extract it cleanly using `git subtree split`.

```bash
cd /Users/mikewolfd/Work/formspec-stack
git subtree split --prefix=PKAF -b rulespec-extract
```

Expected: A new local branch `rulespec-extract` with the PKAF subtree's full history (all commits up through the rename commits in Tasks 2-9).

- [ ] **Step 2: Push that branch as `main` to the new repo**

```bash
git push https://github.com/formspec/rulespec.git rulespec-extract:main
```

Expected: Push succeeds.

- [ ] **Step 3: Verify on GitHub**

```bash
gh repo view formspec/rulespec --web
```

Expected: GitHub opens the repo; default branch is `main`; `spec/rkaf-core-v0.1.md` appears in the file tree.

## Task 13: Add `rulespec` as a submodule in formspec-stack; remove `PKAF/`

**Files:**
- Modify: `formspec-stack/.gitmodules`
- Create: `formspec-stack/rulespec/` (submodule)
- Delete: `formspec-stack/PKAF/`
- Modify: `formspec-stack/CLAUDE.md` (table row)

- [ ] **Step 1: Add the submodule**

```bash
cd /Users/mikewolfd/Work/formspec-stack
git submodule add https://github.com/formspec/rulespec.git rulespec
```

Expected: `.gitmodules` gains a `[submodule "rulespec"]` section; `rulespec/` directory populated with the renamed tree.

- [ ] **Step 2: Verify the submodule mirrors the renamed content**

```bash
ls rulespec/spec/
```

Expected: Lists `rkaf-core-v0.1.md`, `rkaf-concept-registry-v0.1.2.md`, `README.md`.

- [ ] **Step 3: Remove the in-tree `PKAF/` directory (the source has been extracted)**

```bash
git rm -rf PKAF/
```

Expected: All PKAF files staged for deletion.

- [ ] **Step 4: Update `CLAUDE.md` table row**

Edit `/Users/mikewolfd/Work/formspec-stack/CLAUDE.md`. Find the row referencing PKAF (if present in the layer table) and replace with:

```markdown
| Rulespec | [`rulespec/`](rulespec/) | public | Rulespec (RKAF) — vendor-neutral federation substrate for evidence-grounded structured claims; spec, JSON-LD context, SHACL shapes, conformance fixtures, SDKs. |
```

If no PKAF row exists (PKAF was in-tree without a CLAUDE.md table entry), insert this row in alphabetical order alongside the other public layers.

Update the topological build-order line: insert `rulespec` after `trellis` (Rulespec sits alongside Trellis as substrate).

- [ ] **Step 5: Commit the submodule add + PKAF removal + CLAUDE.md update as one atomic commit**

```bash
git add .gitmodules rulespec CLAUDE.md
git commit -m "chore(stack): replace in-tree PKAF/ with formspec/rulespec submodule"
```

## Task 14: Final cross-repo audit

- [ ] **Step 1: Audit formspec-stack for stale PKAF references**

```bash
cd /Users/mikewolfd/Work/formspec-stack
grep -rn "PKAF/" --include='*.md' --include='*.toml' --include='*.json' --include='*.mjs' --include='Makefile' . | grep -v "rulespec/" | grep -v "^Binary"
```

Expected: No output, OR only historical references in `thoughts/` (which are timestamped artifacts and may legitimately mention PKAF as the prior name). If non-historical references remain in active code (Makefile, scripts/, .claude-plugin/), edit them in place to point at `rulespec/`.

- [ ] **Step 2: Run the in-submodule audit**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 tools/rename_audit.py
```

Expected: Exit 0 (CLEAN).

- [ ] **Step 3: Run the SHACL validator from inside the submodule**

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 tools/ci_validate.py --mode batch4
```

Expected: `Result: PASS`.

- [ ] **Step 4: Commit any formspec-stack-side cleanups**

```bash
cd /Users/mikewolfd/Work/formspec-stack
git add -A
git commit -m "chore(stack): clean residual PKAF references after rulespec submodule cutover" || echo "nothing to clean"
```

## Self-review

- [ ] Every renamed filename is reachable; the SHACL validator passes inside the submodule with the new file paths.
- [ ] The rename audit script exits 0 inside `rulespec/` (no `pkaf:`/`PKAF`/`https://w3id.org/pkaf/`/`urn:pkaf:` strings remain in code-reachable surface — historical `thoughts/` artifacts retain original names).
- [ ] `formspec-stack` no longer has a `PKAF/` directory; `rulespec/` is a registered submodule pointing at `https://github.com/formspec/rulespec.git`.
- [ ] `formspec-stack/CLAUDE.md` lists Rulespec in the layer table.
- [ ] `formspec/rulespec` GitHub repo exists, public, with the renamed tree as `main`.
- [ ] `VERSION` reads `0.2.0-pre.1`; `CHANGELOG.md` has the rename entry.
- [ ] No broken refs across the seam: `grep -rn 'shapes/pkaf-\|context/pkaf-\|spec/pkaf-' rulespec/` → empty.
