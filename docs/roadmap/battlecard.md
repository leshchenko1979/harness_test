# Battlecard — Gategrid vs promptfoo vs DeepEval

**Audience:** engineering leads, platform/QA, MCP/agent maintainers evaluating CI eval tooling.

**Us:** [Gategrid](README-pitch-draft.md) — matrix runner + **git-native regression gate** for **one profile per CI lane**. Full landscape: [competitive-landscape.md](competitive-landscape.md).

**Last updated:** 2026-05-24

---

## At a glance

| | **Gategrid (planned)** | **promptfoo** | **DeepEval** |
| - | ---------------------- | ------------- | ------------ |
| **One-liner** | pytest + codecov for your agent matrix | Prompt/agent eval + red team CLI | Pytest for LLM metrics |
| **Stars (May 2026)** | pre-launch | ~21.5k | ~15.7k |
| **Language** | Python-first | TypeScript / YAML | Python |
| **Hosted required?** | No | No (cloud optional) | No (Confident AI optional) |
| **Best buyer** | Agent/MCP team gating **their** stack in CI | Prompt/RAG + security teams | App team unit-testing LLM outputs |

---

## When we win

| Situation | Why Gategrid |
| --------- | ------------ |
| PR must fail if **your** agent+MCP stack regresses | `gate` vs **committed** `baselines/<profile>.json`, overall + like-for-like |
| Same cases, **one** production profile on PR and `main` | Gate matrix = 1 profile; benchmark matrix = many (no PR gate) |
| Agent loop already exists (custom, pydantic-ai, etc.) | `RuntimeAdapter` — framework runs grid, not your app |
| No eval SaaS / air-gapped CI | History in git + artifacts only |
| MCP **E2E with LLM** (not protocol fuzzing) | Cases + profile MCP config; user owns side effects |
| Hard floors when PR env ≠ `main` | `gate.limits` + regression in one command |

**Talk track:** “We don’t replace your agent. We run your cases across your matrix and block merge when this profile drops below the last golden run — like codecov, for agents.”

---

## When we lose (be honest)

| Situation | Choose instead |
| --------- | -------------- |
| OWASP / red team / adversarial MCP catalog | **promptfoo** red team |
| Need polished UI and share links day one | **promptfoo view** or **Confident AI** |
| Team already on LangSmith/Braintrust experiments | Stay on platform; we’re a **thin git gate** optional |
| Only RAG retrieval quality, no tools | **Ragas** or DeepEval RAG metrics |
| Public benchmark leaderboard (MMLU, SWE-bench) | **Inspect AI** / DeepEval benchmarks |
| Want hosted regression history without git discipline | **Braintrust** / **LangSmith** |

---

## Feature-by-feature

| Capability | Gategrid | promptfoo | DeepEval |
| ---------- | -------- | --------- | -------- |
| Declarative matrix YAML | ● | ● | ◐ |
| Python `@case` / fixtures | ● | ◐ (JS providers) | ● pytest |
| Custom agent runtime | ● adapter | ◐ | ● bring app |
| Built-in metrics library | ◐ `contrib` | ◐ assertions | ● large |
| Multi-provider model matrix | ● | ● | ◐ |
| CI fail on regression | ● `gate` | ◐ thresholds | ◐ + cloud |
| Baseline in **git** | ● | ○ | ○ |
| Single-profile gate semantics | ● | ○ | ○ |
| Like-for-like on case churn | ● | ◐ | ◐ |
| PR cell sampling | ● | ◐ | ◐ |
| MCP LLM E2E | ● | ● | ◐ |
| MCP security / BOLA plugins | ○ | ● | ◐ |
| Trace / production loop | ◐ local | ◐ | ● w/ Confident AI |

---

## Objection handling

| Objection | Response |
| --------- | -------- |
| “We already use promptfoo.” | Keep promptfoo for prompt sweeps and red team; use Gategrid for **one gated agent profile** and **repo baselines** if YAML+JS doesn’t match your runtime. |
| “DeepEval is pytest.” | DeepEval scores **outputs**; Gategrid orchestrates **cases × profiles × models** and **merge gates** on aggregates. Composable: DeepEval metrics inside our `@evaluator`. |
| “We use LangSmith experiments.” | LangSmith stores baselines in cloud; Gategrid stores golden runs in **`.gategrid/baselines/`** for fork/PR workflows without vendor lock-in. |
| “Too early / no stars.” | Wedge is narrow on purpose; adopt for **one MCP gate matrix** before betting the whole eval program. |
| “LLMs are flaky.” | v1: cell retries + `flaky_suspect`; gate uses aggregates and deltas, not single deterministic runs. |

---

## Proof points to build (v1)

| Demo | Beats |
| ---- | ----- |
| `mcp-gate` matrix: 1 profile, PR sample + `gate`, `main` `baseline update` | promptfoo “pass rate in JSON” scripts |
| Committed `baselines/mcp-candidate.json` + PR `--baseline-from-artifact` | DeepEval-only cloud regression |
| File-edit example ported on `RuntimeAdapter` | “Coupled to pydantic-ai” perception |

Checklist: [v1-implementation-checklist.md](v1-implementation-checklist.md).

---

## Related competitors (not on card)

| Tool | Relation |
| ---- | -------- |
| **pydantic-evals** | Library; we may bridge via `[legacy]` extra |
| **mcp-eval** | Overlapping MCP story; we add matrix + gate |
| **Langfuse / Braintrust** | Observability-first; different buyer |
| **evalgate** (PyPI) | Similar PR-check slogan — avoid brand confusion |

---

## Naming note

Recommended product name: **Gategrid** (`pip install gategrid`). Avoid **evalgate** (taken; same niche). Details: [competitive-landscape.md#product-naming-revisited](competitive-landscape.md#product-naming-revisited).
