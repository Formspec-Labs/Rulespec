# Studio profile (relocated)

The canonical WOS Studio (Authoring) Rulespec profile lives in the
**policy-studio** submodule:

`policy-studio/profiles/studio/`

- `schema-source/`, `studio-profile-v0.2.cue`, `derive.sh`, `schemas-derived/`
- Conformance disclosure: [`../../conformance/partners/policy-studio.yaml`](../../conformance/partners/policy-studio.yaml)

Do not add schema sources here. Regenerate via `policy-studio/profiles/studio/derive.sh`.

## `profile.url` resolution

Partner disclosure [`policy-studio.yaml`](../../conformance/partners/policy-studio.yaml)
sets `profile.url` to `policy-studio/profiles/studio/`. Resolve that path from the
**formspec-stack repository root** (the monorepo parent that contains both `PKAF/`
and `policy-studio/`), not from the `PKAF/` directory alone.
