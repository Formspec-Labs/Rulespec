# Rulespec v0.1 archive

> **Status:** archived. Frozen at v0.1.1. v0.2 is the greenfield successor and replaces v0.1 wholesale (per master plan §1, source spec §11).

This directory preserves the v0.1 line in tree for historical reference. **Nothing here is loaded by CI or by any active tool.** v0.1 files retain their original filenames; the only change is the path prefix.

## Layout

```
archive/v0.1/
├── spec/
│   ├── rkaf-core-v0.1.md
│   └── rkaf-concept-registry-v0.1.2.md
├── shapes/
│   ├── rkaf-shapes-core-v0.1.ttl
│   ├── rkaf-shapes-conceptregistry-v0.1.ttl
│   ├── rkaf-shapes-lifecycle-v0.1.ttl
│   └── rkaf-shapes-justification-v0.1.ttl
├── context/
│   └── rkaf-context-v0.1.jsonld
├── fixtures/
│   ├── mapping-v0.1.jsonld
│   ├── statutory-authority-v0.1.jsonld
│   └── registry-failure-conflict-v0.1.jsonld
└── v0.1.1-release-manifest.md
```

## Why archive instead of delete

History matters for downstream readers comparing the v0.1 → v0.2 supersession. Git history alone is not enough — the v0.1.1 release manifest, the original SHACL shapes, and the v0.1 fixtures are referenced from CHANGELOG entries and from the v0.2 spec's §11 (Compatibility). Keeping them at stable paths under `archive/v0.1/` preserves those references without polluting the active tree.

## What replaces what

| v0.1 artifact | v0.2 successor |
|---|---|
| `spec/rkaf-core-v0.1.md` | `spec/rkaf-core-v0.2.md` + `spec/rkaf-vocabulary-v0.2.md` |
| `spec/rkaf-concept-registry-v0.1.2.md` | `spec/rkaf-concept-registry-v0.2.md` |
| `shapes/rkaf-shapes-core-v0.1.ttl` (+ siblings) | `shapes/rkaf-shapes-core-v0.2.ttl` (umbrella) + 5 modular v0.2 shape files |
| `context/rkaf-context-v0.1.jsonld` | `context/rkaf-context-v0.2.jsonld` |
| `fixtures/*-v0.1.jsonld` (3 files at repo root) | `fixtures/v0.2/*.jsonld` (20+ files) |

No mechanical migration path is provided. Per master plan §1: "Where v0.2 contradicts v0.1.x, v0.2 wins. Replace, don't bridge."
