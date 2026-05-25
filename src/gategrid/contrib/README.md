# gategrid.contrib

Optional reference implementations grown from dogfood spikes. Core `pip install gategrid` includes this package but does **not** require contrib deps unless you use optional extras.

## When to promote code here

Move from a repo’s `evals/` into contrib when:

- A second project needs the same adapter/evaluator/helper, or
- The pattern is clearly domain-agnostic (sandbox, file match, LLM-judge base).

Keep secrets, product fixtures, and one-off wiring in the user repo.

## File-edit batteries (shipped defaults)

Under `contrib/file_edit/bundled/` (package-data YAML + `tooling/baseline.py`):

| Battery | Ids / registry |
| ------- | -------------- |
| Cases | 10 hashline hypothesis cases (`indent_collision`, …) |
| Case set | `hashline_hypotheses` |
| Tools | `builtin:read_file`, `builtin:str_replace`, `builtin:ls`, `builtin:glob`, `builtin:grep` |

**LLM-visible tool names** stay short (`read_file`, …) via pydantic-ai `Tool(fn, name=…)` — baseline prompt text unchanged.

### Override rules

| Resource | Rule |
| -------- | ---- |
| Case id | User `cases/` with same id as builtin → **error**; fork with a new id |
| Case set | `eval_root/case_sets/foo.yaml` wins; else builtin registry |
| Tools | Swap `builtin:read_file` for `tooling/read_file.py` in `data.tools` — listing both → **duplicate exposed name** error at load |

User eval trees without `cases/` can run matrices that reference builtin ids or `case_sets: [hashline_hypotheses]`. See [examples/file_edit](../../examples/file_edit/).

## Modules

| Module | Purpose |
| ------ | ------- |
| `file_edit` | Sandbox, session, `file_edit_case()`, `register_case_from_yaml()` (eval-root only), `register_builtin_case_from_yaml()` (bundled); `load_file_edit_tools()`; profile helpers; **on import** registers builtin gate `file_content_match` + batteries |
| `llm_judge` | Base class for user-defined LLM judges (no provider calls in core) |

## Not in contrib

| Piece | Location |
| ----- | -------- |
| `ModelConfig` YAML contract | `gategrid.models` (core) |
| `ProfileConfig` core fields | `name`, `runtime_adapter`, `data` only |
| Env overrides (`{PREFIX}_MODEL`, `_BASE_URL`), API key checks | `gategrid.models.env` (core) |
| pydantic-ai `Model` + `run_agent` | `gategrid.integrations.pydantic_ai` — `pip install gategrid[pydantic-ai]` |
| `load_tool_functions` (eval-root `.py` only) | `gategrid.integrations.pydantic_ai.tools` |
| `RuntimeAdapter` wiring | User `evals/adapters/` or `examples/file_edit/adapters/` |
| Product agent tools (OpenCrabs hashline) | User `evals/tooling/opencrabs/` |
| Re-register `file_content_match` in `evaluators/` | **Error** — duplicate id vs builtin |
