# Dogfood spike diary

Personal log for [Gategrid](README-pitch-draft.md) spikes (**order: OpenCrabs → ai-antispam → fast-mcp-telegram**):

1. [opencrabs](https://github.com/leshchenko1979/opencrabs)
2. [ai-antispam](https://github.com/leshchenko1979/ai-antispam)
3. [fast-mcp-telegram](https://github.com/leshchenko1979/fast-mcp-telegram)

Checklist: [v1-implementation-checklist.md#dogfooding-spikes](v1-implementation-checklist.md#dogfooding-spikes) · [Spike → contrib](v1-implementation-checklist.md#spike--contrib)

**Contrib promotion:** For each spike, note what stayed in the repo’s `evals/` vs what was **promoted to `gategrid.contrib`** (and why). Generalizable adapters/evaluators belong in contrib; product fixtures and secrets stay in the repo.

---

## Go / no-go (fill when D.8)

| Criterion | Met? | Notes |
| --------- | ---- | ----- |
| PR-style `gate` trustworthy | | |
| Git baseline simpler than alternatives | | |
| New case under 30 min | | |
| Gate caught real regression | | |

**Decision:** _go / narrow / pause_ — _date_

---

## Spike C — OpenCrabs (1st)

**Layout:** Repo-root [`evals/`](../../evals/) (not under `examples/`).

**Policy:** Gategrid-only for **gated** results (`gategrid run` / `baseline update` / `gate` only). Legacy `experiments/` + `agent_eval_matrix` removed 2026-05 ([teardown L.1–L.4](v1-implementation-checklist.md#legacy-teardown-after-spike-c)).

| Promoted to framework | Stays in `evals/` |
| --------------------- | ----------------- |
| `gategrid.models.env`, `gategrid.integrations.pydantic_ai`, `contrib.file_edit` (sandbox, session, `file_content_match`, **batteries**: hashline cases + baseline tools, `load_file_edit_tools`, profile `data` helpers) | `adapters/file_edit.py`, OpenCrabs tooling + fuzzy stack, opencrabs profiles, matrices |

**Smoke (no API key):** `uv run gategrid run --matrix evals/matrices/hashline-smoke.yaml` with `GATEGRID_EVAL_ROOT=evals` or `--root evals`.

| Date | Command / matrix | Result | Verdict |
| ---- | ---------------- | ------ | ------- |
| 2026-05-24 | `hashline-smoke` (mock) + pytest `test_gategrid_spike_c` | 1/1 pass | smoke OK |
| 2026-05-24 | `hashline-gate` (minimax, 4 cases) | 4/4 pass | [report](../../.gategrid/reports/2026-05-24T194019.9_matrix.json) |
| 2026-05-24 | `baseline update` + `gate` on that report | gate exit 0 | C.3 OK |
| 2026-05-24 | C.4 regression drill (bad report → gate exit 1, good → 0) | PASS / FAIL as expected | C.4 OK |
| 2026-05-24 | Parity: `indent_collision`, `add_docstring_large` vs legacy | both cells: legacy==gategrid `passed` | D.4 parity OK |
| 2026-05-24 | `hashline-bench` (5×10, minimax, ~8.7 min) | 44/50 pass; 2×429 rate limit, 4×`rename_symbol_large` gate fail — [report](../../.gategrid/reports/2026-05-24T195718.2_matrix.json) | C.6 run OK (not all green) |

Notes:

- **Roadmap — 429 handling:** MiniMax returned HTTP 429 on 2/50 `hashline-bench` cells (infra, not eval logic). Tracked as **ADOPT-020** / [Phase 6.8](v1-implementation-checklist.md#phase-6--post-v1-defer) — transport-level retry + backoff at LLM boundary, separate from `run.max_retries`.
- **Contrib candidates:** _e.g. file_edit sandbox/tools, opencrabs tool adapter — promote when API stable_
- Cases/tooling live in repo-root [`evals/`](../../evals/).
- Report / upstream doc: [hashline_hypothesis_report.md](../hashline_hypothesis_report.md) — regenerate from Gategrid reports after C.2.

---

## Spike B — ai-antispam (2nd)

| Date | Command | Result | Verdict |
| ---- | ------- | ------ | ------- |
| | | | |

Notes:

- Fixtures source: `tests/` in ai-antispam
- Deliberate regression experiment (B.7):

---

## Spike A — fast-mcp-telegram (3rd)

| Date | Command | Result | Verdict |
| ---- | ------- | ------ | ------- |
| | | | |

Notes:

- Test account / Saved Messages only for writes
- CI: secrets / workflow_dispatch

---

## Blockers

| Repo | Blocker | Workaround |
| ---- | ------- | ---------- |
