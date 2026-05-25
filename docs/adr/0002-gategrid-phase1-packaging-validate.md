# ADR 0002: Gategrid Phase 1 — packaging, validate, clean break

**Status:** accepted (2026-05-24)

## Context

Phase 0 added schemas, `gate`, and `baseline update` under a monorepo still named `agent-eval-matrix` with legacy CLIs and heavy core deps. Phase 1 makes **gategrid** the only installable package surface.

## Decisions

| Topic | Decision |
| ----- | -------- |
| PyPI name | `gategrid` (`version` synced with `gategrid.version.__version__`) |
| Core deps | `pydantic`, `pyyaml`, `python-dotenv` only |
| Extras | `pydantic-ai` (adapter in Phase 2); `dev` = pytest; provider/report extras unchanged; **`mcp` deferred to Phase 4** |
| Scripts | `gategrid` only — **no** `agent-eval-matrix` / `agent-eval` |
| Packages shipped | `gategrid*` only — legacy harness removed after [legacy teardown](../roadmap/v1-implementation-checklist.md#legacy-teardown-after-spike-c) |
| Legacy | **No** `[legacy]` extra, pydantic-evals bridge, or dual report formats |
| Home writer | `ensure_home()` creates `baselines/`, `reports/`, `traces/` under `GATEGRID_HOME` / `.gategrid/`; called from `io.save_json` only |
| Config models | `ProfileConfig`, `ModelConfig`, `CaseSetConfig` via Pydantic `BaseModel` — **no** pydantic-settings in Phase 1 |
| Validate | `gategrid validate --matrix PATH [--root ROOT]` — matrix + referenced profile/model/case_set YAML; eval root defaults to parent of `matrices/` when matrix lives there |
| Matrix axis | `profiles:` only (no `tool_sets` alias in validate) |
| Cases | Matrix lists case **ids** only; no core `cases/*.yaml` (legacy `EditCase` is contrib, not core) |

## CLI (Phase 1)

- `gategrid --version`
- `gategrid validate --matrix …`
- Phase 0 commands unchanged: `run` (stub), `gate`, `baseline update`

## Consequences

- `uv sync --extra dev` runs gategrid tests; legacy harness removed (teardown L.1–L.4).
- Monorepo contributors run legacy harness via editable path only until port completes — not via `pip install gategrid`.

## See also

- [ADR 0001](0001-gategrid-phase0-schemas-cli-gate.md)
- [v1 implementation checklist](../roadmap/v1-implementation-checklist.md)
