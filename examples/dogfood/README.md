# Dogfood integrations

Gategrid spikes on repos used to validate the framework before broader release.

**Checklist:** [docs/roadmap/v1-implementation-checklist.md](../../docs/roadmap/v1-implementation-checklist.md#dogfooding-spikes) · **Diary:** [docs/roadmap/dogfood-notes.md](../../docs/roadmap/dogfood-notes.md)

## Order

1. **[opencrabs](https://github.com/leshchenko1979/opencrabs)** — hashline matrix on Gategrid (**done** in this repo under [`evals/`](../../evals/))
2. **[ai-antispam](https://github.com/leshchenko1979/ai-antispam)** — after Phase 2–3
3. **[fast-mcp-telegram](https://github.com/leshchenko1979/fast-mcp-telegram)** — after Phase 4–5 MCP path

| # | Repo | Gate matrix | Status |
| - | ---- | ----------- | ------ |
| 1 | opencrabs (in-repo) | `evals/matrices/hashline-gate.yaml` | Spike C complete |
| 2 | ai-antispam | `evals/matrices/spam-gate.yaml` (planned) | Not started |
| 3 | fast-mcp-telegram | `evals/matrices/telegram-mcp-gate.yaml` (planned) | Not started |

## OpenCrabs (this repo)

```bash
uv sync --extra dev --extra pydantic-ai
gategrid run --matrix evals/matrices/hashline-gate.yaml --root evals
gategrid baseline update --from-report .gategrid/reports/<latest>.json --profile opencrabs_original
gategrid gate --report .gategrid/reports/<latest>.json --profile opencrabs_original
```

Background: [docs/hashline_hypothesis_report.md](../../docs/hashline_hypothesis_report.md).

## Target layout (each external repo)

```text
evals/
  cases/
  matrices/
  profiles/
  models/
.gategrid/
  baselines/
  reports/
```
