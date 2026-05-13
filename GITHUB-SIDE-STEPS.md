# GitHub-side cutover steps (Plan 1 deferred to owner)

The local filesystem rename is complete. The following operations require GitHub credentials and the `formspec` GitHub org; they are not safe to execute from an autonomous agent.

Execute these from `/Users/mikewolfd/Work/formspec-stack/` (parent stack repo).

## 1. Create the public `formspec/rulespec` repo

Requires: `gh` CLI authenticated; `formspec` org exists (create it first if needed).

```bash
gh repo create formspec/rulespec \
  --public \
  --description "Rulespec (RKAF) — Knowledge Assertion Framework: vendor-neutral federation substrate for evidence-grounded structured claims" \
  --homepage "https://rulespec.org" \
  --license "Apache-2.0"
```

## 2. Extract the renamed PKAF tree as the seed of the new repo

The renamed tree lives in this repo's `PKAF/` directory with full git history. Use `git subtree split` to extract it cleanly.

```bash
cd /Users/mikewolfd/Work/formspec-stack
git subtree split --prefix=PKAF -b rulespec-extract
git push https://github.com/formspec/rulespec.git rulespec-extract:main
```

## 3. Add `rulespec` as a submodule and remove in-tree `PKAF/`

```bash
cd /Users/mikewolfd/Work/formspec-stack
git submodule add https://github.com/formspec/rulespec.git rulespec
ls rulespec/spec/   # should list rkaf-core-v0.1.md, rkaf-concept-registry-v0.1.2.md, README.md
git rm -rf PKAF/
```

## 4. Update `formspec-stack/CLAUDE.md`

Insert this row into the layer table (alphabetical position between Formspec and Trellis/WOS or wherever fits the existing order):

```markdown
| Rulespec | [`rulespec/`](rulespec/) | public | Rulespec (RKAF) — vendor-neutral federation substrate for evidence-grounded structured claims; spec, JSON-LD context, SHACL shapes, conformance fixtures, SDKs. |
```

Update the topological build-order line: insert `rulespec` after `trellis`. The current order:

```
fel-core → formspec → work-spec → trellis → workspec-server → policy-studio → formspec-studio → case-portal
```

Becomes:

```
fel-core → formspec → work-spec → trellis → rulespec → workspec-server → policy-studio → formspec-studio → case-portal
```

(Or place `rulespec` in parallel with `trellis` if Rulespec sits alongside Trellis as substrate.)

## 5. Commit the cutover

```bash
git add .gitmodules rulespec CLAUDE.md
git commit -m "chore(stack): replace in-tree PKAF/ with formspec/rulespec submodule"
```

## 6. Run the in-submodule audit + SHACL validator

```bash
cd /Users/mikewolfd/Work/formspec-stack/rulespec
python3 tools/rename_audit.py        # expect: CLEAN
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python3 tools/ci_validate.py --mode batch4   # expect: Result: PASS, 1206 triples
```

## 7. Sweep formspec-stack for stale PKAF references

```bash
cd /Users/mikewolfd/Work/formspec-stack
grep -rn "PKAF/" --include='*.md' --include='*.toml' --include='*.json' --include='*.mjs' --include='Makefile' . | grep -v "rulespec/" | grep -v "^Binary"
```

Edit any active references in Makefile / scripts/ / .claude-plugin/ to point at `rulespec/`. Historical thoughts/ artifacts may legitimately retain `PKAF` as the prior name; they are timestamped records.

## State at handoff

- Local commits applied to `PKAF/` (now ready for extraction):
  - `1428aae build(tools): add rkaf rename audit script`
  - `e22bc25 refactor(rkaf): rename pkaf-* artifact filenames to rkaf-*`
  - `df29b16 refactor(rkaf): rewrite JSON-LD contexts to rkaf prefix and rulespec.org IRI namespace`
  - `3189522 refactor(rkaf): rewrite SHACL shapes to rkaf prefix, rulespec.org IRIs, and rkaf-bridge contract`
  - `5d1be8c refactor(rkaf): rewrite JSON-LD fixtures to rkaf prefix`
  - `c05723b refactor(rkaf): rebrand ci_validate.py and point at rkaf-shapes-* files`
  - `cd796cb docs(rkaf): rebrand spec body PKAF→Rulespec / pkaf:→rkaf:`
  - `a9e0b52 docs(rkaf): rebrand README/CHANGELOG/CONTRIBUTING/reports/narratives/shape comments`
  - `f5f3fb1 docs(thoughts): add Rulespec v0.2 spec and 12-plan execution series`
  - `1892beb chore(rkaf): bump VERSION to 0.2.0-pre.1`

- `python3 tools/rename_audit.py` → CLEAN (0 findings).
- `.venv/bin/python3 tools/ci_validate.py --mode batch4` → `Result: PASS`, 1,206 triples, 0 violations (byte-identical SHACL graph behavior vs v0.1.1).
- `VERSION` is `0.2.0-pre.1`.
- `CHANGELOG.md` carries the rename note.
