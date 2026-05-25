# ADR 0006: Gategrid Phase 4 — MCP path

**Status:** accepted (2026-05-25)

## Context

Phase 4 delivers a credible **LLM-mediated MCP** eval story for v1 competitive parity (vs mcp-eval / promptfoo MCP). Core must not own MCP transport, docker, or protocol-level tests.

## Decisions

| Topic | Decision |
| ----- | -------- |
| Config location | `profile.data.mcp` + optional `profile.data.env_pass_through` (names only); core `ProfileConfig` unchanged |
| `contrib/mcp` | Integration-agnostic: `McpProfileConfig`, `mcp_from_profile`, `resolve_env_pass_through`; **no** agent loop; **no** import of `mcp` or `integrations.pydantic_ai` at module load |
| `integrations/pydantic_ai/mcp_servers` | Optional Path A: `mcp_toolset_from_data` → `MCPServerStdio` / `MCPServerStreamableHTTP`; requires `gategrid[pydantic-ai,mcp]` |
| Extras | `[mcp]` pins `mcp>=1.12.4`; pydantic-ai MCP toolsets need both extras |
| Example | `examples/gategrid/` — stdio `server/calc_server.py`, `mcp-gate.yaml` (live), `mcp-gate-mock.yaml` (CI) |
| Stdio cwd | Adapter passes `cwd=eval_root` so relative server paths resolve |
| Global gates | `mcp_tooling_ok` no-ops without `mcp` case tag; `echo_contains_case` no-ops when `profile_id != demo` |
| Remote transport | One factory: `streamable_http` (SSE deferred) |
| Non-goals | Direct MCP `tools/list` / `call_tool` in core pytest; `stdio_session_from_config` in contrib until Spike A |

## Path A vs Path B

| Path | Install | Wiring |
| ---- | ------- | ------ |
| **A** (example) | `gategrid[pydantic-ai,mcp]` | `contrib/mcp` + `mcp_toolset_from_data` + `run_agent(toolsets=…)` |
| **B** (Spike A, custom) | `gategrid[mcp]` or other client | `mcp_from_profile` + own loop → `RunArtifact` |

## Consequences

- Spike A (fast-mcp-telegram) can reuse `contrib/mcp` without pydantic-ai.
- Phase 5 adds CI matrices and baseline workflows for MCP gate lanes.
