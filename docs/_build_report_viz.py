"""Generate hashline report figures and notebook. Run from repo root."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
REPORT_JSON = REPO / "reports/2026-05-23T13-22-35.666225+00-00_local-r_matrix.json"
FIGURES = Path(__file__).resolve().parent / "figures"

VARIANTS = [
    "opencrabs_original",
    "opencrabs_h1_docs",
    "opencrabs_h3_collision",
    "opencrabs_h2_fuzzy",
    "baseline",
]
VARIANT_LABELS = {
    "opencrabs_original": "original toolset",
    "opencrabs_h1_docs": "H1: docs fix",
    "opencrabs_h3_collision": "H3: empty-hash",
    "opencrabs_h2_fuzzy": "H2: fuzzy replace",
    "baseline": "str_replace only",
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
                "tags": r.get("tags", []),
            }
        )
    return pd.DataFrame(rows)


def plot_pass_rate(df: pd.DataFrame) -> None:
    rates = []
    for v in VARIANTS:
        sub = df[df["variant"] == v]
        rates.append(100.0 * sub["passed"].mean())
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#4C72B0"] * len(VARIANTS)
    colors[0] = "#DD8452"
    colors[3] = "#55A868"
    bars = ax.barh(
        [VARIANT_LABELS[v] for v in VARIANTS],
        rates,
        color=colors,
        edgecolor="black",
        linewidth=0.5,
    )
    bars[0].set_edgecolor("black")
    bars[0].set_linewidth(2)
    ax.set_xlim(0, 105)
    ax.set_xlabel("Pass rate (%)")
    ax.set_title("Pass rate by variant (10 cases)")
    ax.axvline(90, color="gray", linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(FIGURES / "pass_rate_by_variant.png", dpi=150)
    plt.close(fig)


def plot_heatmap(df: pd.DataFrame) -> None:
    mat = np.zeros((len(CASE_ORDER), len(VARIANTS)))
    for i, case in enumerate(CASE_ORDER):
        for j, v in enumerate(VARIANTS):
            row = df[(df["variant"] == v) & (df["case_name"] == case)]
            mat[i, j] = 1.0 if (len(row) and row.iloc[0]["passed"]) else 0.0
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(mat, aspect="auto", cmap="RdYlGn", vmin=0, vmax=1)
    ax.set_xticks(range(len(VARIANTS)))
    ax.set_xticklabels([VARIANT_LABELS[v] for v in VARIANTS], rotation=30, ha="right")
    ax.set_yticks(range(len(CASE_ORDER)))
    ax.set_yticklabels(CASE_ORDER, fontsize=8)
    ax.set_title("Pass matrix (green=pass, red=fail)")
    for i in range(len(CASE_ORDER)):
        for j in range(len(VARIANTS)):
            ax.text(
                j, i, "✓" if mat[i, j] else "✗", ha="center", va="center", fontsize=12
            )
    fig.colorbar(im, ax=ax, fraction=0.02)
    fig.tight_layout()
    fig.savefig(FIGURES / "pass_matrix_heatmap.png", dpi=150)
    plt.close(fig)


def plot_efficiency(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    labels = [VARIANT_LABELS[v] for v in VARIANTS]
    turns = [df[df["variant"] == v]["turns"].mean() for v in VARIANTS]
    tokens = [df[df["variant"] == v]["tokens_spent"].mean() for v in VARIANTS]
    x = np.arange(len(VARIANTS))
    axes[0].bar(x, turns, color="#4C72B0")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=30, ha="right")
    axes[0].set_ylabel("Mean turns")
    axes[0].set_title("Mean LLM turns per case")
    axes[1].bar(x, tokens, color="#C44E52")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=30, ha="right")
    axes[1].set_ylabel("Mean tokens spent")
    axes[1].set_title("Mean tokens per case")
    fig.tight_layout()
    fig.savefig(FIGURES / "efficiency_tokens_turns.png", dpi=150)
    plt.close(fig)


def plot_buckets(df: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    def pass_rate(sub: pd.DataFrame) -> list[float]:
        return [
            100.0 * sub[sub["variant"] == v]["passed"].mean()
            if len(sub[sub["variant"] == v])
            else 0
            for v in VARIANTS
        ]

    h4_df = df[df["case_name"].isin(H4_CASES)]
    large = df[df["tags"].apply(lambda t: "size:large" in t)]
    small = df[df["tags"].apply(lambda t: "size:large" not in t)]

    x = np.arange(len(VARIANTS))
    axes[0].bar(x, pass_rate(h4_df), color="#4C72B0")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(
        [VARIANT_LABELS[v] for v in VARIANTS], rotation=30, ha="right"
    )
    axes[0].set_ylabel("Pass rate (%)")
    axes[0].set_title("H4 cases: indented py/yaml traps (n=4)")
    axes[0].set_ylim(0, 105)

    w = 0.35
    axes[1].bar(x - w / 2, pass_rate(large), w, label="large (6)")
    axes[1].bar(x + w / 2, pass_rate(small), w, label="small (4)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(
        [VARIANT_LABELS[v] for v in VARIANTS], rotation=30, ha="right"
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
