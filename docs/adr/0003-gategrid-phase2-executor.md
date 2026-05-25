# ADR 0003: Gategrid Phase 2 — matrix execution

**Status:** accepted (2026-05-24)

## Context

Phase 0–1 froze schemas, gate/baseline CLI, and config validation. Phase 2 connects live matrix runs without legacy file-edit harness code in core.

## Decisions

| Topic | Decision |
| ----- | -------- |
| Execution | `CellExecutor` in `gategrid/executor.py` — expand full grid, sequential async cells |
| Runtime | `RuntimeAdapter` protocol + `RunContext`; **required** `profile.runtime_adapter` (`module:Class`) |
| Cases | `@case` decorator; optional `id` (default `fn.__name__`), optional `tags` (default `[]`) |
| Case id qualify | `GATEGRID_CASE_ID_QUALIFY`: `name` (default) or `module` (dotted path under `cases` package) |
| Collisions | Duplicate resolved ids → hard error at discovery |
| Discovery | Builtin file-edit cases always loaded; optional `pkgutil.walk_packages` on `eval_root/cases/` when present; eval root prepended on `sys.path`; user id colliding with builtin → error |
| Pass rule (Phase 2, superseded) | **Executor only:** no adapter exception ∧ optional `gate_check` (removed in Phase 3 — use `@evaluator`) |
| Retries | `run.max_retries`; pass if any attempt passes; `flaky_suspect` when attempts disagree |
| Sampling | **Deferred** — report sets `SamplingMeta(sampled=False, planned=executed=N)` |
| Eval root | CLI `--root` > `GATEGRID_EVAL_ROOT` > parent of `matrices/` |
| CLI exit | `run`: 0 all pass, 1 any fail, 2 config/validation |
| Demo adapter | `gategrid.adapters.echo:EchoAdapter` (no LLM) |

## Consequences

- `@evaluator` and `run.sample` remain Phase 3 / 5.
- OpenCrabs spike still needs `contrib/file_edit` (Phase 3.4).
- Matrix YAML references case **ids** produced by discovery (documented on validate/run stderr).

## See also

- [v1-implementation-checklist.md](../roadmap/v1-implementation-checklist.md) Phase 2
- [0001-gategrid-phase0-schemas-cli-gate.md](0001-gategrid-phase0-schemas-cli-gate.md)
