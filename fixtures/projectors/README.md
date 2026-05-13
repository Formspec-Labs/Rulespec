# Projector parity fixtures (Layer 4)

Fixtures consumed by `tools/projector_parity.py` via the `projector-harness` CLI.

## Round-trip fixtures

Each `round-trip-*.{jsonld,yaml}` file is a 2-key envelope:

```json
{
  "native":  <native artifact in the target's wire format>,
  "overlay": <Rulespec overlay graph>
}
```

The orchestrator invokes:

```
projector-harness --target <t> round-trip --fixture <file>
```

which runs Attach → Extract and exits 0 iff the recovered `(native, overlay)` pair equals the input.

## Carrier conventions

The matching carrier convention for every target lives under `spec/projectors/`.
