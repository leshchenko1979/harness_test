"""Generate hashline report figures and notebook. Run from repo root."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]


def _resolve_report_json() -> Path:
    if env := os.environ.get("GATEGRID_REPORT_JSON"):
        return Path(env)
    home = Path(os.environ.get("GATEGRID_HOME", REPO / ".gategrid"))
    reports = home / "reports"
    if reports.is_dir():
        candidates = sorted(
            reports.glob("*_matrix.json"), key=lambda p: p.stat().st_mtime
        )
        if candidates:
            return candidates[-1]
    print(
        "Set GATEGRID_REPORT_JSON to a Gategrid matrix report "
        "(e.g. from gategrid run --matrix evals/matrices/hashline-bench.yaml --root evals).",
        file=sys.stderr,
    )
    sys.exit(1)


REPORT_JSON = _resolve_report_json()
FIGURES = Path(__file__).resolve().parent / "figures"

# Hypothesis order: original → H1 → H2 → H3 → H4 reference
VARIANTS = [
    "opencrabs_original",
    "opencrabs_h1_docs",
    "opencrabs_h2_fuzzy",
    "opencrabs_h3_collision",
    "baseline",
]
VARIANT_LABELS = {
    "opencrabs_original": "original OpenCrabs",
    "opencrabs_h1_docs": "H1: docs fix",
    "opencrabs_h2_fuzzy": "H2: fuzzy replace",
    "opencrabs_h3_collision": "H3: empty-hash read",
    "baseline": "H4: simplified reference",
}
H4_CASES = [
    "whitespace_trap",
    "whitespace_trap_yaml",
    "whitespace_trap_py_large",
    "whitespace_trap_yaml_large",
]
CASE_ORDER = [
    "whitespace_trap",
    "whitespace_trap_yaml",
    "ambiguous_replace",
    "indent_collision",
    "whitespace_trap_py_large",
    "whitespace_trap_yaml_large",
    "ambiguous_replace_large",
    "add_docstring_large",
    "rename_symbol_large",
    "indent_collision_large",
]

IDX_ORIGINAL = 0
IDX_H2 = 2


def load_df() -> pd.DataFrame:
    data = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    rows = []
    for r in data["results"]:
        rows.append(
            {
                "variant": r["variant_id"].rsplit("/", 1)[0],
                "case_name": r["case_name"],
                "passed": r["passed"],
                "turns": r.get("turns", 0),
                "tokens_spent": r.get("tokens_spent", 0),
                "tool_failures": r.get("tool_failures", 0),
                "duration_ms": r.get("duration_ms", 0),
                "tags": r.get("tags", []),
            }
        )
    return pd.DataFrame(rows)


def _variant_stats(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for v in VARIANTS:
        sub = df[df["variant"] == v]
        n = len(sub)
        out[v] = {
            "pass_rate": 100.0 * sub["passed"].mean() if n else 0.0,
            "pass_n": int(sub["passed"].sum()),
            "n": n,
            "turns": sub["turns"].mean() if n else 0.0,
            "tokens": sub["tokens_spent"].mean() if n else 0.0,
            "tool_failures": sub["tool_failures"].sum() if n else 0,
            "duration_s": sub["duration_ms"].mean() / 1000.0 if n else 0.0,
        }
    return out


def _bar_labels(ax, bars, labels: list[str]) -> None:
    for bar, label in zip(bars, labels, strict=True):
        ax.text(
            bar.get_width() + 1,
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=9,
        )


def plot_pass_rate(df: pd.DataFrame) -> None:
    stats = _variant_stats(df)
    rates = [stats[v]["pass_rate"] for v in VARIANTS]
    ann = [f"{int(stats[v]['pass_n'])}/{int(stats[v]['n'])}" for v in VARIANTS]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    colors = ["#4C72B0"] * len(VARIANTS)
    colors[IDX_ORIGINAL] = "#DD8452"
    colors[IDX_H2] = "#55A868"
    ylabels = [VARIANT_LABELS[v] for v in VARIANTS]
    bars = ax.barh(ylabels, rates, color=colors, edgecolor="black", linewidth=0.5)
    bars[IDX_ORIGINAL].set_linewidth(2)
    _bar_labels(ax, bars, ann)
    ax.set_xlim(0, 115)
    ax.set_xlabel("Pass rate (%)")
    ax.set_title("Pass rate by variant (10 cases)")
    ax.axvline(90, color="gray", linestyle="--", alpha=0.5, label="9/10")
    fig.tight_layout()
    fig.savefig(FIGURES / "pass_rate_by_variant.png", dpi=150)
    plt.close(fig)


def plot_heatmap(df: pd.DataFrame) -> None:
    mat = np.zeros((len(CASE_ORDER), len(VARIANTS)))
    for i, case in enumerate(CASE_ORDER):
        for j, v in enumerate(VARIANTS):
            row = df[(df["variant"] == v) & (df["case_name"] == case)]
            mat[i, j] = 1.0 if (len(row) and row.iloc[0]["passed"]) else 0.0
    fig, ax = plt.subplots(figsize=(10.5, 8))
    ax.imshow(mat, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
    ax.set_xticks(range(len(VARIANTS)))
    ax.set_xticklabels([VARIANT_LABELS[v] for v in VARIANTS], rotation=25, ha="right")
    ax.set_yticks(range(len(CASE_ORDER)))
    ax.set_yticklabels(CASE_ORDER, fontsize=8)
    ax.set_title("Pass matrix (green=pass, red=fail)")
    for i in range(len(CASE_ORDER)):
        for j in range(len(VARIANTS)):
            ax.text(
                j,
                i,
                "P" if mat[i, j] else "F",
                ha="center",
                va="center",
                fontsize=11,
                fontweight="bold",
                color="white" if mat[i, j] < 0.5 else "black",
            )
    fig.tight_layout()
    fig.savefig(FIGURES / "pass_matrix_heatmap.png", dpi=150)
    plt.close(fig)


def plot_efficiency(df: pd.DataFrame) -> None:
    stats = _variant_stats(df)
    labels = [VARIANT_LABELS[v] for v in VARIANTS]
    x = np.arange(len(VARIANTS))

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    turns = [stats[v]["turns"] for v in VARIANTS]
    tokens = [stats[v]["tokens"] for v in VARIANTS]
    failures = [stats[v]["tool_failures"] for v in VARIANTS]
    duration = [stats[v]["duration_s"] for v in VARIANTS]

    for ax, values, title, ylabel, color in [
        (axes[0, 0], turns, "Mean LLM turns per case", "Mean turns", "#4C72B0"),
        (axes[0, 1], tokens, "Mean tokens per case", "Mean tokens", "#C44E52"),
        (
            axes[1, 0],
            failures,
            "Tool failures (sum, 10 cases)",
            "Sum tool_failures",
            "#8172B2",
        ),
        (axes[1, 1], duration, "Mean task duration", "Mean duration (s)", "#CCB974"),
    ]:
        ax.bar(x, values, color=color)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=28, ha="right", fontsize=8)
        ax.set_ylabel(ylabel)
        ax.set_title(title)

    fig.suptitle("Variant efficiency (comparison metrics)", y=1.02)
    fig.tight_layout()
    fig.savefig(FIGURES / "efficiency_tokens_turns.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_buckets(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    def pass_stats(sub: pd.DataFrame) -> tuple[list[float], list[str]]:
        rates: list[float] = []
        ann: list[str] = []
        for v in VARIANTS:
            vs = sub[sub["variant"] == v]
            n = len(vs)
            k = int(vs["passed"].sum()) if n else 0
            rates.append(100.0 * k / n if n else 0.0)
            ann.append(f"{k}/{n}")
        return rates, ann

    h4_df = df[df["case_name"].isin(H4_CASES)]
    large = df[df["tags"].apply(lambda t: "size:large" in t)]
    small = df[df["tags"].apply(lambda t: "size:large" not in t)]

    x = np.arange(len(VARIANTS))
    h4_rates, h4_ann = pass_stats(h4_df)
    bars0 = axes[0].bar(x, h4_rates, color="#4C72B0")
    for bar, label in zip(bars0, h4_ann, strict=True):
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            label,
            ha="center",
            fontsize=9,
        )
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(
        [VARIANT_LABELS[v] for v in VARIANTS], rotation=28, ha="right", fontsize=8
    )
    axes[0].set_ylabel("Pass rate (%)")
    axes[0].set_title("H4 cases: indented py/yaml traps (n=4 per variant)")
    axes[0].set_ylim(0, 115)

    w = 0.35
    large_rates, _ = pass_stats(large)
    small_rates, _ = pass_stats(small)
    axes[1].bar(x - w / 2, large_rates, w, label="large (6)")
    axes[1].bar(x + w / 2, small_rates, w, label="small (4)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(
        [VARIANT_LABELS[v] for v in VARIANTS], rotation=28, ha="right", fontsize=8
    )
    axes[1].set_ylabel("Pass rate (%)")
    axes[1].set_title("All cases: file size")
    axes[1].legend()
    axes[1].set_ylim(0, 105)

    fig.tight_layout()
    fig.savefig(FIGURES / "h4_cases_and_file_size.png", dpi=150)
    plt.close(fig)
    old = FIGURES / "h4_and_size_buckets.png"
    if old.exists():
        old.unlink()


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    df = load_df()
    plot_pass_rate(df)
    plot_heatmap(df)
    plot_efficiency(df)
    plot_buckets(df)
    print(f"Wrote figures to {FIGURES}")


if __name__ == "__main__":
    main()
