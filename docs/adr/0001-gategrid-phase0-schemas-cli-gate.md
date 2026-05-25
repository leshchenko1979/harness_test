# ADR 0001: Gategrid Phase 0 — schemas, CLI, gate (executor deferred)

**Status:** accepted (2026-05-24)

## Context

Gategrid replaces the coupled `agent-eval-matrix` harness with a pytest-shaped, git-native regression gate. Phase 0 must freeze on-disk contracts before rewriting execution.

## Decisions

| Topic | Decision |
| ----- | -------- |
| Package | `src/gategrid/` from day one; `schemas/v1/*.schema.json` + `examples/` |
| Schema version | `schema_version: 1` only; **no** reader for legacy `MatrixReport` / `reports/*.json` |
| Baseline files | **Per profile:** `.gategrid/baselines/<profile_id>.json` — no `last.json` |
| Cell key | `(case_id, profile_id, model_id)` |
| `RunArtifact` | `messages[]`, `tool_calls[]`, `files` (bytes as base64 in JSON), `metrics` |
| Aggregates | `pass_rate`, `tokens_spent_mean`, `turns_mean` (+ means for tool_failures, duration in schema) |
| Fingerprint | `matrix_name` + sorted `profile_ids` + sorted `case_ids` |
| Matrix YAML | `profiles` (not `tool_sets` in new configs) |
| Home dir | `GATEGRID_HOME` or `.gategrid/` — **no** `.agent-eval-matrix` alias |
| Phase 0 scope | Models, schemas, **`gategrid gate`**, **`gategrid baseline update`**, **`gategrid run` stub** |
| Executor | **Phase 2** — `gategrid/executor.py` documents `CellExecutor` responsibilities |

## Executor (Phase 2 — not in Phase 0)

`CellExecutor` will:

1. Load `MatrixConfig` and resolve case ids (Python `@case` registry in Phase 2).
2. Expand the grid `cases × profiles × models`.
3. Apply `run.sample` (seeded) for PR-sized runs.
4. For each cell, call `RuntimeAdapter.execute()` → `RunArtifact`.
5. Run user `@evaluator` hooks; **`gate`** tag must pass on ≥1 attempt (`run.max_retries`).
6. Build `MatrixReport` with `overall`, `fingerprint`, `sampling`, flake fields.
7. Write `.gategrid/reports/<timestamp>_matrix.json`.

Phase 0 validates gate/baseline logic against hand-written or test-generated reports.

## CLI (Phase 0)

```bash
gategrid run --matrix path.yaml      # exits 2 + explanation until Phase 2
gategrid gate [--report] [--baseline] [--matrix] [--profile]
gategrid baseline update --from-report PATH --profile ID
```

## Consequences

- Legacy `agent_eval_matrix` harness removed after Spike C; use `gategrid run` only.
- Dogfood spikes use fixture reports until Phase 2 connects live runs.
- JSON Schema files are checked in; tests assert they match Pydantic `model_json_schema()`.

## Amended (2026-05-25) — agnostic aggregates + gate metric dicts

| Topic | Decision |
| ----- | -------- |
| `RunArtifact` | `messages`, `metrics`, `evaluators`, `error` only (see ADR 0004 amend) |
| `ReportOverall` / `BaselineOverall` | `pass_rate`, `duration_ms_mean`, `cell_count`, `metrics: dict[str, float]` — no typed `turns_mean` / `tokens_spent_mean` |
| Gate bounds | `metric_mean_min`, `metric_mean_max`, `metric_mean_min_delta`, `metric_mean_max_delta` (per-key dicts); `pass_rate_*` stay first-class |
| Cell reporting | No top-level `CellResult.turns` / `tokens_spent` / `tool_failures` — values in `cell.metrics` only |

## See also

- [v1-implementation-checklist.md](../roadmap/v1-implementation-checklist.md)
- [architecture-vision.md](../roadmap/architecture-vision.md)
