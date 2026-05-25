# Gategrid

**Product:** [Gategrid](docs/roadmap/README-pitch-draft.md) — matrix eval runner with git-native CI gates.

**User-facing pitch:** [README.md](README.md). Roadmap: [docs/roadmap/v1-implementation-checklist.md](docs/roadmap/v1-implementation-checklist.md).

## Setup

```bash
uv sync --extra dev
gategrid --version
gategrid validate --matrix examples/gategrid/matrices/smoke.yaml
gategrid run --matrix examples/gategrid/matrices/smoke.yaml
pytest tests/test_gategrid_phase0.py tests/test_gategrid_phase1.py \
  tests/test_gategrid_phase2.py tests/test_gategrid_phase3.py
```

For hashline / LLM dogfood: `uv sync --extra dev --extra pydantic-ai`.

Artifacts live under `.gategrid/` (`GATEGRID_HOME` overrides). ADRs: [docs/adr/](docs/adr/). **Coding principles:** [CODE.md](CODE.md) — reread before implementation (after plan approval); update after post-impl review ([implementation workflow](.cursor/rules/gategrid-phase-workflow.mdc)).

## In-repo eval tree (`evals/`)

Dogfood layout for OpenCrabs hashline (Spike C). Not part of `pip install gategrid`; use `--root evals` or `GATEGRID_EVAL_ROOT=evals`.

```bash
gategrid validate --matrix evals/matrices/hashline-smoke.yaml --root evals
gategrid run --matrix evals/matrices/hashline-smoke.yaml --root evals
pytest tests/test_gategrid_spike_c.py tests/test_gategrid_file_edit_batteries.py
```

| Path | Role |
| ---- | ---- |
| `evals/matrices/` | Runnable matrices (`hashline-smoke`, `hashline-gate`, `hashline-bench`, …) |
| `evals/profiles/` | `runtime_adapter` + `data.system_prompt` / `data.tools` |
| `evals/models/` | Model presets (`provider`, `model_name`, `api_key_env`, …) |
| `evals/cases/` | `@case` registration + YAML case bodies |
| `evals/tooling/opencrabs/` | OpenCrabs-style tools (one tool per file) |
| `evals/adapters/` | `file_edit` runtime adapter |

**Tooling rules:** No `SYSTEM_PROMPT`, `TOOLS`, or `register(agent)` bundles in `.py` files. Paths in cases are workspace-relative.

## Examples

| Path | Role |
| ---- | ---- |
| `examples/gategrid/` | Minimal Gategrid smoke (mock) |
| `examples/file_edit/` | File-edit contrib sample |

## Hashline hypothesis matrix

5 profile variants × 10 cases (4 small + 6 large). Pass/fail = file content match via `contrib/file_edit`.

```bash
gategrid run --matrix evals/matrices/hashline-bench.yaml --root evals
```

**Report:** [docs/hashline_hypothesis_report.md](docs/hashline_hypothesis_report.md). Regenerate figures: `uv sync --extra report` then `uv run python docs/_build_report_viz.py` (set `GATEGRID_REPORT_JSON` to a `.gategrid/reports/*.json` from a bench run).

## Observability

- Default: stdout + `.gategrid/reports/`
- Logfire: `LOGFIRE_TOKEN`, `send_to_logfire='if-token-present'` on pydantic-ai runs
