# agent-eval-matrix — LLM agent eval harness

**User-facing pitch and quick start:** [README.md](README.md) (framework-first; bundled `experiments/` content is examples only).

## Purpose

Matrix evals over **cases** (YAML) × **tool sets** (YAML) × **models** (YAML). Matrices under `experiments/matrices/` declare the runnable cross-product; tool sets hold `system_prompt` + `tools:` paths; each `.py` under `tooling/` exports one tool function.

## Run locally

**Setup (once, or when lock/deps change):** `uv sync --extra dev` — creates/reuses `.venv` from `uv.lock`. **Never** run `python3 -m venv`; re-sync only when `uv.lock` or `pyproject.toml` changes.

```bash
uv sync --extra dev
# Demo (no API key): mocked model, 1×1 matrix
uv run python -m agent_eval_matrix.matrix run --demo
uv run python -m agent_eval_matrix.matrix run   # default: demo.yaml

# Real evals (.env: MINIMAX_API_KEY)
uv run python -m agent_eval_matrix.matrix run --matrix experiments/matrices/ci.yaml
uv run python -m agent_eval_matrix.matrix run --matrix experiments/matrices/full.yaml
uv run python -m agent_eval_matrix.evals run --case add_docstring --tool-set baseline
uv run python -m agent_eval_matrix.matrix run --variant strict/verbose/minimax-m2.7
```

After `source .venv/bin/activate`, omit the `uv run` prefix.

## Layout

- `experiments/tool_sets/` — agent prompts + tool path lists (YAML only bundling)
- `experiments/case_sets/` — named case lists
- `experiments/models/` — model presets (`provider`, `model_name`, `api_key_env`, …)
- `experiments/matrices/` — runnable matrix definitions (`tool_sets`, `models`, `cases`/`case_sets`)
- `experiments/cases/` — case content (one YAML per case)
- `experiments/tooling/reference/` — thin wrappers over `agent_eval_matrix.tools` (one tool per file)
- `experiments/tooling/opencrabs/` — OpenCrabs-style tools (one tool per file)
- `src/agent_eval_matrix/` — loader, sandbox, matrices resolver, matrix CLI

## Tooling rules

- **No** `SYSTEM_PROMPT`, `TOOLS`, or `register(agent)` bundles in `.py` files.
- **Reference tools**: `tooling/reference/*.py` → `agent_eval_matrix.tools`.
- **OpenCrabs tools**: `tooling/opencrabs/*.py`; composed via `tool_sets/opencrabs_original.yaml`.

## Paths

- Models should use **workspace-relative** paths (`app.py`).
- `agent_eval_matrix.sandbox` canonicalizes macOS `/private/var` vs `/var` and accepts absolutes inside the workspace.

## Models

- Presets in `experiments/models/*.yaml` (registry key = filename stem).
- Matrix `models` lists preset stems (e.g. `minimax-m2.7`).
- Providers: `openai` (default install), `anthropic`, `google` (optional extras in pyproject.toml).
- Per-preset env overrides: `{PREFIX}_MODEL`, `{PREFIX}_BASE_URL` where prefix is derived from `api_key_env` (e.g. `MINIMAX_API_KEY` → `MINIMAX_MODEL`).

## Hashline hypothesis matrix

Isolated OpenCrabs variants (H1 doc fix, H2 fuzzy `str_replace`, H3 empty-hash collisions) vs `opencrabs_original` and `baseline`:

```bash
uv run python -m agent_eval_matrix.matrix run --matrix experiments/matrices/hashline_hypotheses.yaml
```

**10 cases** (4 small + 6 large ~100–150 lines): indent traps, ambiguous replace, hash collisions, docstring insert, rename — **50 matrix runs** (5 variants × 10 cases).

Pass/fail is still **file content match** only; `print_summary` adds hypothesis deltas, H4 pass rates by `language:python` / `language:yaml`, and `size:large` vs small buckets.

**Report for OpenCrabs upstream:** [docs/hashline_hypothesis_report.md](docs/hashline_hypothesis_report.md) (prose), [docs/hashline_hypothesis_report.ipynb](docs/hashline_hypothesis_report.ipynb) (charts). Index: [docs/README.md](docs/README.md). Regenerate figures: `uv sync --extra report` then `uv run python docs/_build_report_viz.py`.

## Run metrics (comparison only; pass/fail = file match)

- **turns** — `RunUsage.requests` from `agent.run()` (LLM rounds, not `tool_calls`)
- **tokens_spent** — sum of canonical `RunUsage` token fields + `details` (not `total_tokens`)
- **tool_failures** — sum of `metrics` keys ending in `_failures` from reference tools
- **duration_ms** — pydantic-evals `task_duration` on the report row
- Raw span/tool counters remain in `CaseResult.metrics` for debugging

## Observability

- Default: stdout + `reports/*.json`
- Logfire: `LOGFIRE_TOKEN`, `send_to_logfire='if-token-present'`
- `--trace` → `reports/traces/*.jsonl`
