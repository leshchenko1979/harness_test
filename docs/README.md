# OpenCrabs file-editing evaluation

Report for **OpenCrabs** developers (upstream was not consulted before this study). Tests hashline protocol changes, **two edit tools → one** fuzzy replace (H2), and comparison to a **simplified reference** tool set (H4; 8 vs 32 total tool parameters).

| Artifact | Description |
|----------|-------------|
| [**hashline_hypothesis_report.md**](hashline_hypothesis_report.md) | Full report — **implementers: [§2 Quick reference](hashline_hypothesis_report.md#2-quick-reference-for-implementers)** · metrics: [§3](hashline_hypothesis_report.md#3-executive-summary) |
| [**hashline_hypothesis_report.ipynb**](hashline_hypothesis_report.ipynb) | Charts |
| [Matrix JSON](../reports/2026-05-23T13-22-35.666225+00-00_local-r_matrix.json) | 50 runs |

**Verdicts:** H2 fuzzy replace **supported** (10/10, lower tokens); H3 empty-hash collisions **rejected** (worst efficiency); H1 inconclusive; H4 mixed (equal pass, reference cheaper).

```bash
pip install -e ".[report]"
python docs/_build_report_viz.py
```
