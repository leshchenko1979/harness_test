# ADR 0004: Gategrid Phase 3 — evaluators, RunArtifact.error, contrib

**Status:** accepted (2026-05-24)

## Context

Phase 2 used interim `gate_check` on `@case`. Phase 3 introduces user-owned `@evaluator` plugins, moves pass/fail to gate evaluators, and seeds `gategrid.contrib` for file-edit benchmarks ahead of OpenCrabs spike C.

## Decisions

| Topic | Decision |
| ----- | -------- |
| Evaluators | `@evaluator(role="gate"\|"metric", canonical=…)`; return `EvaluatorOutcome`; discovery under `eval_root/evaluators/` (mirror `cases/`) |
| Evaluator ids | Optional `id`; default function name; `GATEGRID_EVALUATOR_ID_QUALIFY=name\|module`; fail on collisions |
| Pass rule | Attempt passes iff adapter returns without exception, `RunArtifact.error` is unset, and **all** `gate` evaluators pass |
| `RunArtifact.error` | Non-null → attempt fails; artifact still stored for debugging |
| `gate_check` | **Removed** from `@case` — no legacy support |
| No gate evaluators | Adapter success alone passes (migration); smoke example ships `echo_contains_case` |
| Metric evaluators | `role="metric"`; never flip `CellResult.passed`; `EvaluatorOutcome.metrics` merged with optional `{evaluator_id}.` prefix |
| Global registry | All discovered `gate` evaluators run on every cell; contrib gates no-op when prerequisites missing |
| Reports | `AttemptRecord.evaluator_results`; JSON schemas updated with `error` + `evaluator_results` |
| `gategrid.contrib` | Optional reference package in install; `file_edit` (sandbox + `file_content_match_impl`); `llm_judge` ABC stub |
| Contrib registration | `file_edit` registers builtin gate `file_content_match` via `register_builtin_evaluator` on import; other contrib evaluators still need user `evaluators/` wrappers |
| Builtin cases | `register_builtin_case` / `register_builtin_case_set` in core (mirror evaluators); shipped hashline batteries in `contrib/file_edit/bundled/` |
| Profile contract | Core `ProfileConfig` is `runtime_adapter` + `data` only; file-edit LLM keys (`system_prompt`, `tools`) live under `data` — see ADR 0005 |
| 3.4 deferral | **Superseded by batteries (ADR 0005)** — file-edit adapter + baseline tools ship in contrib; OpenCrabs stays user `evals/tooling/` |

## `file_content_match` contract

- **Expected:** `FileEditCase.expected_output` from `CaseRecord.data` (via `FileEditCase.from_record`).
- **Actual:** `RunContext.scratchpad["actual_content"]` (adapter sets before session teardown).
- **Skip:** case without `file_edit` tag → gate returns `True` (no-op).
- **Pass display:** gate pass with only `pass: true` (after stripping optional `artifact` key) → `artifact.evaluators[id]` is bool `true`, not `{"pass": true}`.

## Consequences

- Spike C ports OpenCrabs runtime; `file_content_match` is a builtin gate (no `evals/evaluators/` shim).
- Matrix YAML evaluator registry (ADOPT-009) remains future work.
- Phase 4 MCP path unchanged.

## Amended (2026-05-25) — slim artifact + evaluator display

| Topic | Decision |
| ----- | -------- |
| `RunArtifact` | `messages`, `metrics`, `evaluators`, `error` only — **no** `files`, `final_text`, `tool_calls` |
| Compare | File-edit gates read **expected** from `CaseRecord.data`; **actual** from `RunContext.scratchpad["actual_content"]` (adapter sets before session teardown) |
| Gate `dict` return | `pass` (required for dict), optional `artifact` (substitutes whole `RunArtifact`), `message`, `detail` — pass-only → bool `true` on `artifact.evaluators[id]`; failures stay as dict |
| Metric evaluators | Outcomes merge into `cell.metrics` only (via `_merge_metric_outcome`); never written to `artifact.evaluators` |
| Reports | Drop `AttemptRecord.evaluator_results`; gate outcomes on `artifact.evaluators` only |
| Pydantic enrich (Option A) | `enrich_artifact_from_run` in `integrations.pydantic_ai` — **not** a core evaluator; adapters populate `artifact.messages` (merged tool call+return), `artifact.metrics`, and `artifact.tools_called` (name → count) before gates run |
| Adapter metrics | `artifact.metrics` from enrich and/or evaluator patches; no `primary_file` |
| Evaluator patches | Deep-merge into artifact; duplicate metric keys or second `messages` writer → `ArtifactMergeError` |

## See also

- [v1-implementation-checklist.md](../roadmap/v1-implementation-checklist.md) Phase 3
- [0003-gategrid-phase2-executor.md](0003-gategrid-phase2-executor.md)
