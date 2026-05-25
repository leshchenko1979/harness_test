# Gategrid example eval tree

Minimal layout for `gategrid validate` and `gategrid run` (Phase 2+).

```bash
gategrid validate --matrix examples/gategrid/matrices/smoke.yaml
gategrid run --matrix examples/gategrid/matrices/smoke.yaml
# Case ids default to @case function names (see stderr qualify= line)
```

## Smoke (no API key)

```bash
uv sync --extra dev
uv run gategrid validate --matrix matrices/smoke.yaml --root .
uv run gategrid run --matrix matrices/smoke.yaml --root .
```

## MCP gate (mock — CI / offline)

Uses `PydanticAiMcpAdapter` with `provider: mock` (no subprocess MCP server).

```bash
uv sync --extra dev --extra pydantic-ai --extra mcp
uv run gategrid validate --matrix matrices/mcp-gate-mock.yaml --root .
uv run gategrid run --matrix matrices/mcp-gate-mock.yaml --root .
```

## MCP gate (live — LLM + stdio server)

You own side effects: the profile spawns `server/calc_server.py` as a subprocess. Gategrid does not start docker, databases, or production Telegram sessions.

```bash
uv sync --extra dev --extra pydantic-ai --extra mcp
export OPENAI_API_KEY=...
uv run gategrid validate --matrix matrices/mcp-gate.yaml --root .
uv run gategrid run --matrix matrices/mcp-gate.yaml --root .
```

Profile MCP config lives under **`data`** (see `profiles/mcp-candidate.yaml`):

- `data.mcp` — `transport: stdio`, `command`, `args` (paths relative to eval root)
- `data.env_pass_through` — env **names** only; values from the process environment

Optional remote transport: `transport: streamable_http` + `url` (see `gategrid.contrib.mcp.McpProfileConfig`).

## Layout

- `matrices/` — matrix YAML (`profiles`, `models`, `cases` / `case_sets`)
- `profiles/` — profile YAML (`runtime_adapter`; optional `data` for adapter-specific keys)
- `models/` — model presets
- `case_sets/` — named lists of **case ids**
- `cases/` — Python package with **`@case`** handlers (not legacy `EditCase` YAML)
- `evaluators/` — Python package with **`@evaluator`** (`gate` / `metric` tags)
- `adapters/` — example `RuntimeAdapter` implementations
- `server/` — minimal stdio MCP server for the MCP example

Set `GATEGRID_EVAL_ROOT` to this directory when invoking from the repo root.
