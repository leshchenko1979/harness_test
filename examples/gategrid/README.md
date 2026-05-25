# Gategrid example eval tree

Minimal layout for `gategrid validate` and `gategrid run` (Phase 2+).

```bash
gategrid validate --matrix examples/gategrid/matrices/smoke.yaml
gategrid run --matrix examples/gategrid/matrices/smoke.yaml
# Case ids default to @case function names (see stderr qualify= line)
```

Layout:

- `matrices/` — matrix YAML (`profiles`, `models`, `cases` / `case_sets`)
- `profiles/` — profile YAML (`runtime_adapter`; optional `data` for adapter-specific keys)
- `models/` — model presets
- `case_sets/` — named lists of **case ids**
- `cases/` — Python package with **`@case`** handlers (not legacy `EditCase` YAML)
- `evaluators/` — Python package with **`@evaluator`** (`gate` / `metric` tags)
