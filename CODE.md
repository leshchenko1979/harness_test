# Gategrid — coding principles

Durable **implementation guardrails** for agents and humans. Not the product spec, phase plan, or command cheatsheets. **Public product overview:** [README.md](README.md).

**Workflow:** Reread before implementing a phase (after plan approval). Read that phase’s [ADR](docs/adr/) for decisions. After post-implementation review, add bullets here only if they’re non-obvious in ADR/code — merge into the sections below, don’t start new “Phase N” blocks.

---

## What belongs here

| Include | Example |
| ------- | ------- |
| Cross-phase invariants easy to violate while coding | adapters don’t score; metrics never fail CI |
| Discovery / executor gotchas | global gate registry; contrib registration on import |
| Test expectations | import-guard tests; subprocess CLI smoke |

| Do **not** include | Put it in |
| ------------------ | --------- |
| Steps 1–6, HIIL, plan gates | [`.cursor/rules/gategrid-phase-workflow.mdc`](.cursor/rules/gategrid-phase-workflow.mdc) |
| Phase scope, exits, checklist rows | [v1-implementation-checklist.md](docs/roadmap/v1-implementation-checklist.md) |
| Decision tables, schema fields | [docs/adr/](docs/adr/) |
| Product layers, clean-break tables | Checklist [Product shape](docs/roadmap/v1-implementation-checklist.md#product-shape-what-ships-where), [Clean break](docs/roadmap/v1-implementation-checklist.md#clean-break-policy-v1--no-legacy-path) |
| Run/setup commands | [CLAUDE.md](CLAUDE.md) |

**Before adding a bullet:** Needed in the first 60 seconds of a future phase? If ADR already states it, link ADR — don’t copy.

---

## Packaging and clean break

- **Install surface = `gategrid` only.** Core deps minimal; optional stacks in extras. No `pydantic-evals` / legacy harness in default install.
- **Ship only `gategrid*`** from `pyproject.toml`. Legacy `agent_eval_matrix` + `experiments/` removed after Spike C ([legacy teardown](docs/roadmap/v1-implementation-checklist.md#legacy-teardown-after-spike-c)).
- **No legacy bridges** in new configs (`[legacy]` extra, `tool_sets`, dual report formats). See checklist [Clean break policy](docs/roadmap/v1-implementation-checklist.md#clean-break-policy-v1--no-legacy-path).
- **File-edit in `contrib`, not core.** `@case` + matrix case ids in core; sandbox / file-match in `gategrid.contrib`. Promote contrib only when generalizable — [contrib README](src/gategrid/contrib/README.md).

## Code style

- **Export public config models** from `gategrid.models` when part of the plugin/YAML contract.
- **Prefer one obvious code path** over single-call helpers — match surrounding module style.

## Paths and on-disk layout

- **Framework artifacts under `.gategrid/`** (`GATEGRID_HOME`). Do not write Gategrid reports to repo-root `reports/`.
- **`ensure_home()` only when writing under the active home** — pass `home=` through `save_json` for custom homes.
- **Eval tree:** `matrices/`, `profiles/`, `models/`, `case_sets/`, optional `cases/`, `evaluators/`; matrix uses `profiles:` not `tool_sets`.

## Config and validation

- **Pydantic `BaseModel` for YAML**; defer `pydantic-settings` until needed.
- **`gategrid validate`** mirrors `run`: same eval-root resolution; case ids resolved via builtin batteries + optional `cases/`; validate `evaluators/` when present (tags, duplicate ids, `GATEGRID_EVALUATOR_ID_QUALIFY`).
- **Core `ProfileConfig`:** only `name`, `runtime_adapter`, opaque `data`. File-edit uses `data.system_prompt` and `data.tools` (contrib helpers) — not top-level profile fields.

## Cases and discovery

- **Case discovery:** builtin file-edit cases always loaded; optional `eval_root/cases/` via `pkgutil` merges with collision errors; put eval root **first** on `sys.path` when switching projects in one process.
- **Case ids:** default function name; `GATEGRID_CASE_ID_QUALIFY=module` for dotted ids; fail on collisions.
- **No `gate_check` on `@case`** — scoring only via `@evaluator`.

## Runtime adapters and executor

- **Adapters return `RunArtifact` only** — no pass/fail in adapters. [ADR 0003](docs/adr/0003-gategrid-phase2-executor.md).
- **`profile.runtime_adapter` required** for `run` — no silent default.
- **`RunArtifact.error` set** → attempt fails (adapter need not raise); artifact still stored. [ADR 0004](docs/adr/0004-gategrid-phase3-evaluators-contrib.md).
- **Pass/fail:** all evaluators with `role="gate"` must return `EvaluatorOutcome(pass_=True)`; if none registered, adapter success (no error) passes.
- **Global gate registry** — every `role="gate"` evaluator runs on **every** cell; contrib gates must **no-op** when prerequisites are absent (e.g. missing `file_edit` tag).
- **`role="metric"` evaluators** never flip `CellResult.passed`; merge via `EvaluatorOutcome.metrics` — prefixed `{evaluator_id}.{key}` unless `@evaluator(canonical=True)` (unprefixed into `cell.metrics`).
- **Pydantic observability (Option A):** not a core evaluator — adapters call `run_agent` + `enrich_artifact_from_run` in `gategrid.integrations.pydantic_ai`; mock via `mock_run_result()`. Core never imports pydantic for evaluator registration. Slim transcript merges each tool-call with its tool-return (one `role: tool` row); `tools_called` is `dict[str, int]` name → invocation count; no `tool_call_count` in `metrics`.
- **`RunArtifact` shape:** `messages`, `metrics`, `evaluators`, `error` only — no `files` / `final_text` / `tool_calls` in matrix JSON ([ADR 0004](docs/adr/0004-gategrid-phase3-evaluators-contrib.md)).
- **Artifact layers:**

  | Layer | Contents |
  | ----- | -------- |
  | `artifact.metrics` | From adapter / pydantic **enrich** + optional evaluator patches (deep-merge; duplicate keys → `ArtifactMergeError`) |
  | `artifact.tools_called` | Pydantic enrich only — per-tool invocation counts; evaluators must not patch |
  | `artifact.evaluators` | **Gates only** — executor writes from `EvaluatorOutcome.pass_` / `message` / `detail`; metrics never stored here |
  | `cell.metrics` | `artifact.metrics` numerics + merged metric-evaluator keys (for aggregates / gate YAML) |
- **Scratchpad:** per-attempt, not serialized; file-edit sets `actual_content` for `file_content_match` only — not usage.
- **Evaluator patches:** must not set `messages` or `evaluators` on `artifact`; gates → metrics run order in `run_evaluators_on_artifact`.
- **Gate failures:** `CellResult.error` = failing gate id; CLI reads `artifact.evaluators[id].message` / `.detail` ([`cli_output.py`](src/gategrid/cli_output.py)).
- **Aggregates / gate:** `compute_overall(cells, mean_keys)` and gate checks use keys from matrix YAML only — core never hardcodes `turns` ([ADR 0001](docs/adr/0001-gategrid-phase0-schemas-cli-gate.md)).
- **Builtin gates:** `import gategrid.contrib.file_edit` registers `file_content_match`; user `evaluators/` must not re-register the same id.

## MCP (Phase 4)

- **Config under `profile.data` only** — `data.mcp` (`transport`, `command`/`args` or `url`); `data.env_pass_through` lists env **names**; values resolved in the adapter, not in core `validate`. [ADR 0006](docs/adr/0006-gategrid-phase4-mcp-path.md).
- **`contrib/mcp`** — `mcp_from_profile`, `resolve_env_pass_through`; integration-agnostic (no `mcp` / pydantic-ai import at contrib load).
- **Pydantic-ai MCP** — `mcp_toolset_from_data` in `integrations/pydantic_ai/mcp_servers`; requires `gategrid[pydantic-ai,mcp]`. Stdio spawn uses `cwd=eval_root`.
- **Shared eval roots:** MCP gates no-op without `mcp` case tag; non-MCP gates (e.g. echo) no-op outside their profile/case — global registry runs all gates on every cell.
- **CI:** `examples/gategrid/matrices/mcp-gate-mock.yaml` for pytest; live `mcp-gate.yaml` is manual README exit.

## Tests

- **Import-guard tests** assert the **installed core** (optional deps not importable), not monorepo `PYTHONPATH` side effects.
- **Phase exit:** `pytest tests/test_gategrid_phase*.py` (through phase 4) + `test_gategrid_cli_output.py` + `test_gategrid_spike_c.py`.
- **CLI smoke in a subprocess** when in-process imports can mask evaluator registration bugs (e.g. duplicate `@evaluator` on contrib + example shim).
