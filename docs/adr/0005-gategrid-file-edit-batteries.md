# ADR 0005: Gategrid file-edit batteries + slim profile contract

**Status:** accepted (2026-05-24)

## Context

Hashline benchmark cases and the reference baseline tool stack lived only under repo `evals/`, forcing every consumer to copy YAML and `tooling/reference/` before running a baseline profile. Core `ProfileConfig` also carried `system_prompt` and `tools` fields that only the pydantic-ai file-edit adapter used.

## Decisions

| Topic | Decision |
| ----- | -------- |
| Batteries location | `gategrid.contrib.file_edit.bundled/` — 10 hashline case YAMLs, `hashline_hypotheses` case set, `tooling/baseline.py` |
| Packaging | `package-data` for `bundled/**/*.yaml` in `pyproject.toml` |
| Registration | `register_builtin_case` / `register_builtin_case_set` in core `cases.py`; bundled YAML via `register_builtin_case_from_yaml` (never `_pending`) |
| Case discovery | Builtins always loaded; optional `eval_root/cases/` merged; duplicate id → `ValueError` |
| Case sets | `eval_root/case_sets/<id>.yaml` wins; else builtin registry (e.g. `hashline_hypotheses`) |
| Profile core | `ProfileConfig`: `name`, `runtime_adapter`, `data: dict` only — no `system_prompt` / `tools` |
| File-edit profile keys | `data.system_prompt`, `data.tools` — interpreted by contrib `profile.py` + adapter |
| Tools | `load_file_edit_tools()` in contrib; `builtin:*` registry + eval-root `.py` via integrations loader |
| LLM tool names | `Tool(callable, name=exposed)` — e.g. `builtin:read_file` → model sees `read_file` (prompt text unchanged) |
| `glob` | `builtin:glob` → exposed name `glob` (implementation `glob_tool`) |
| Duplicate exposed name | Same profile lists `builtin:read_file` and `tooling/read_file.py` → `ValueError` at load |
| Fuzzy replace | Not bundled; `evals/tooling/fuzzy/` for OpenCrabs h2 dogfood |
| Onboarding | `examples/file_edit/` — minimal tree, builtins only |

## Consequences

- `evals/cases/` and `evals/tooling/reference/` removed from dogfood tree; matrices keep same case ids.
- Spike B / MCP adapters can use `profile.data` without file-edit fields on core.
- ADR 0003 discovery row amended for optional `cases/`.

## See also

- [contrib README](../../src/gategrid/contrib/README.md)
- [examples/file_edit](../../examples/file_edit/)
- [0004-gategrid-phase3-evaluators-contrib.md](0004-gategrid-phase3-evaluators-contrib.md)
