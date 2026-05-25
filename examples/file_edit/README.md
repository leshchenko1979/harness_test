# File-edit example (Gategrid batteries)

Minimal eval tree using **builtin** hashline cases and baseline tools shipped in `gategrid.contrib.file_edit.bundled`.

No `cases/` directory is required — case ids like `indent_collision` come from the package. Add `cases/` only when registering your own `@case` handlers (use a **new** id; duplicating a builtin id errors).

## Override rules

| Resource | Override |
|----------|----------|
| Cases | Fork with a new id under `eval_root/cases/` |
| Tools | Swap `builtin:read_file` for `tooling/read_file.py` in profile `data.tools` — do not list both (duplicate exposed name errors at load) |
| Case sets | `eval_root/case_sets/foo.yaml` wins over builtin `hashline_hypotheses` |

Profile file-edit keys live under **`data`** (not on core `ProfileConfig`): `data.system_prompt`, `data.tools` (`builtin:*` or eval-root `.py` paths).

## Run

```bash
uv sync --extra dev --extra pydantic-ai
uv run gategrid validate --matrix matrices/smoke-mock.yaml --root .
uv run gategrid run --matrix matrices/smoke-mock.yaml --root .
```

Set `GATEGRID_EVAL_ROOT` to this directory when invoking from the repo root.
