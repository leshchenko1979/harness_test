# OpenCrabs file-editing evaluation

Report for **OpenCrabs** developers (upstream was not consulted before this study). Tests hashline protocol changes, **two edit tools → one** fuzzy replace (H2), and comparison to a **simplified reference** tool set (H4; 8 vs 32 total tool parameters).

| Artifact                                                                                              | Description                                      |
| ----------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| [hashline_hypothesis_report.md](hashline_hypothesis_report.md)                                        | Full report — implementers start at §2; metrics §3 |
| [hashline_hypothesis_report.ipynb](hashline_hypothesis_report.ipynb)                                  | Charts                                           |
| `.gategrid/reports/*_matrix.json` | Gategrid bench output (see [hashline_hypothesis_report.md](hashline_hypothesis_report.md)) |

**Report sections:** [§2 Quick reference](hashline_hypothesis_report.md#2-quick-reference-for-implementers) · [§3 Executive summary](hashline_hypothesis_report.md#3-executive-summary)

**Verdicts:** H2 fuzzy replace **supported** (10/10, lower tokens); H3 empty-hash collisions **rejected** (worst efficiency); H1 inconclusive; H4 mixed (equal pass, reference cheaper).

```bash
uv sync --extra report
uv run python docs/_build_report_viz.py
```
