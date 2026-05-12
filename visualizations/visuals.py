"""
JSP Benchmark Visualization Suite
===================================
Generates 6 publication-quality plots from benchmark_results.csv.

Usage:
    python visualize_benchmark.py                          # reads results/benchmark_results.csv
    python visualize_benchmark.py path/to/your/file.csv   # custom path

Output (saved to results/plots/):
    1. gap_boxplot.png          — Optimality gap distribution per algorithm
    2. runtime_vs_gap.png       — Quality vs speed scatter (Pareto frontier)
    3. scaling_jobs.png         — How gap% scales with problem size
    4. family_heatmap.png       — Per-instance-family performance heatmap
    5. cpsat_status.png         — CP-SAT OPTIMAL vs FEASIBLE breakdown
    6. win_rate.png             — Win rate per algorithm across all instances
"""

import sys
import os
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")   # non-interactive backend — works without a display
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────
CSV_PATH    = sys.argv[1] if len(sys.argv) > 1 else "results/benchmark_results.csv"
OUTPUT_DIR  = Path("results/plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Colour palette — one per algorithm, consistent across all plots
ALG_ORDER  = ["MWKR", "GA", "Tabu", "CP-SAT"]
ALG_COLORS = {
    "MWKR":   "#8B8680",
    "GA":     "#7B6FD4",
    "Tabu":   "#1A9E75",
    "CP-SAT": "#2E7FD4",
}

plt.rcParams.update({
    "font.family":      "DejaVu Sans",
    "font.size":        11,
    "axes.spines.top":  False,
    "axes.spines.right":False,
    "axes.grid":        True,
    "grid.alpha":       0.3,
    "grid.linestyle":   "--",
    "figure.dpi":       150,
    "savefig.dpi":      150,
    "savefig.bbox":     "tight",
})

# ── Load data ─────────────────────────────────────────────────────────────
print(f"Loading {CSV_PATH} ...")
df = pd.read_csv(CSV_PATH)
df["optimality_gap_pct"] = pd.to_numeric(df["optimality_gap_pct"], errors="coerce")
df["runtime_s"]          = pd.to_numeric(df["runtime_s"],          errors="coerce")
df["makespan"]           = pd.to_numeric(df["makespan"],            errors="coerce")
df["num_jobs"]           = pd.to_numeric(df["num_jobs"],            errors="coerce")
df["num_machines"]       = pd.to_numeric(df["num_machines"],        errors="coerce")

# Extract instance family prefix (e.g. "ta01" → "ta")
df["family"] = df["instance"].str.extract(r"^([a-zA-Z]+)")

# For gap analysis, clamp negatives to 0 (they are artefacts of stale BKS,
# not genuine results — see Category B in the analysis)
df["gap_clamped"] = df["optimality_gap_pct"].clip(lower=0)

print(f"  {len(df)} rows | {df['instance'].nunique()} instances | "
      f"algorithms: {sorted(df['algorithm'].unique())}")

# ── Helper ────────────────────────────────────────────────────────────────
def save(fig, name):
    path = OUTPUT_DIR / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  Saved → {path}")


# ══════════════════════════════════════════════════════════════════════════
# Plot 1 — Optimality Gap Distribution (box + strip)
# ══════════════════════════════════════════════════════════════════════════
print("\n[1/6] Optimality gap boxplot ...")

fig, ax = plt.subplots(figsize=(9, 6))

data_by_alg = [df[df["algorithm"] == a]["gap_clamped"].dropna().values
               for a in ALG_ORDER]

bp = ax.boxplot(
    data_by_alg,
    patch_artist=True,
    widths=0.45,
    medianprops=dict(color="white", linewidth=2.5),
    whiskerprops=dict(linewidth=1.2),
    capprops=dict(linewidth=1.2),
    flierprops=dict(marker="o", markersize=3, alpha=0.4),
)

for patch, alg in zip(bp["boxes"], ALG_ORDER):
    patch.set_facecolor(ALG_COLORS[alg])
    patch.set_alpha(0.85)
for flier, alg in zip(bp["fliers"], ALG_ORDER):
    flier.set(markerfacecolor=ALG_COLORS[alg], markeredgecolor="none")

# Overlay individual points (jittered)
for i, (alg, vals) in enumerate(zip(ALG_ORDER, data_by_alg), 1):
    jitter = np.random.default_rng(42).uniform(-0.18, 0.18, size=len(vals))
    ax.scatter(i + jitter, vals, s=12, alpha=0.25,
               color=ALG_COLORS[alg], zorder=3, linewidths=0)

ax.set_xticks(range(1, len(ALG_ORDER) + 1))
ax.set_xticklabels(ALG_ORDER, fontsize=12)
ax.set_ylabel("Optimality Gap (%)", fontsize=12)
ax.set_title("Optimality Gap Distribution by Algorithm\n"
             "(lower is better — 0% = matches best known solution)",
             fontsize=13, fontweight="bold", pad=14)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))

# Annotate median values
for i, (alg, vals) in enumerate(zip(ALG_ORDER, data_by_alg), 1):
    med = np.median(vals)
    ax.text(i, med + 1.5, f"{med:.1f}%", ha="center", va="bottom",
            fontsize=9, fontweight="bold", color=ALG_COLORS[alg])

save(fig, "gap_boxplot.png")


# ══════════════════════════════════════════════════════════════════════════
# Plot 2 — Quality vs Speed scatter (log runtime axis)
# ══════════════════════════════════════════════════════════════════════════
print("[2/6] Quality vs speed scatter ...")

# Per-instance average gap and median runtime per algorithm
agg = (df.groupby(["algorithm", "instance"])
         .agg(gap=("gap_clamped", "mean"), rt=("runtime_s", "median"))
         .reset_index())
summary = (agg.groupby("algorithm")
              .agg(avg_gap=("gap", "mean"), med_rt=("rt", "median"),
                   q25_gap=("gap", lambda x: x.quantile(0.25)),
                   q75_gap=("gap", lambda x: x.quantile(0.75)))
              .reset_index())

fig, ax = plt.subplots(figsize=(9, 6))

for _, row in summary.iterrows():
    alg = row["algorithm"]
    ax.scatter(row["med_rt"], row["avg_gap"],
               s=220, color=ALG_COLORS[alg], zorder=5,
               edgecolors="white", linewidths=1.5, label=alg)
    # Error bar for gap IQR
    ax.errorbar(row["med_rt"], row["avg_gap"],
                yerr=[[row["avg_gap"] - row["q25_gap"]],
                      [row["q75_gap"] - row["avg_gap"]]],
                fmt="none", color=ALG_COLORS[alg], alpha=0.5,
                capsize=5, linewidth=1.5)
    ax.annotate(f"  {alg}", (row["med_rt"], row["avg_gap"]),
                fontsize=11, fontweight="bold", color=ALG_COLORS[alg],
                va="center")

ax.set_xscale("log")
ax.set_xlabel("Median Runtime (seconds, log scale)", fontsize=12)
ax.set_ylabel("Average Optimality Gap (%)", fontsize=12)
ax.set_title("Quality vs Speed Trade-off\n"
             "(error bars show IQR of gap across instances)",
             fontsize=13, fontweight="bold", pad=14)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
ax.xaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f"{x:.0f}s" if x >= 1 else f"{x:.3f}s"))

# Annotate the Pareto region
ax.annotate("← faster & better",
            xy=(0.15, 0.08), xycoords="axes fraction",
            fontsize=9, color="gray", style="italic")

save(fig, "runtime_vs_gap.png")


# ══════════════════════════════════════════════════════════════════════════
# Plot 3 — Scaling: gap% vs num_jobs per algorithm
# ══════════════════════════════════════════════════════════════════════════
print("[3/6] Scaling with problem size ...")

scale = (df.groupby(["algorithm", "num_jobs"])["gap_clamped"]
           .mean().reset_index()
           .rename(columns={"gap_clamped": "avg_gap"}))

fig, ax = plt.subplots(figsize=(10, 6))

for alg in ALG_ORDER:
    sub = scale[scale["algorithm"] == alg].sort_values("num_jobs")
    ax.plot(sub["num_jobs"], sub["avg_gap"],
            color=ALG_COLORS[alg], linewidth=2.5,
            marker="o", markersize=7, label=alg)
    # Annotate last point
    last = sub.iloc[-1]
    ax.annotate(f"{alg}  {last['avg_gap']:.1f}%",
                (last["num_jobs"], last["avg_gap"]),
                xytext=(6, 0), textcoords="offset points",
                fontsize=9, color=ALG_COLORS[alg], va="center")

ax.set_xlabel("Number of Jobs", fontsize=12)
ax.set_ylabel("Average Optimality Gap (%)", fontsize=12)
ax.set_title("Algorithm Scalability: How Gap% Grows with Problem Size",
             fontsize=13, fontweight="bold", pad=14)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))
ax.set_xticks(sorted(df["num_jobs"].dropna().unique()))
ax.legend(loc="upper left", framealpha=0.9, fontsize=10)

save(fig, "scaling_jobs.png")


# ══════════════════════════════════════════════════════════════════════════
# Plot 4 — Per-family heatmap of average gap%
# ══════════════════════════════════════════════════════════════════════════
print("[4/6] Family heatmap ...")

heat = (df.groupby(["family", "algorithm"])["gap_clamped"]
          .mean().unstack("algorithm")
          .reindex(columns=ALG_ORDER))

# Order families by CP-SAT gap (hardest first)
heat = heat.sort_values("CP-SAT", ascending=False)

fig, ax = plt.subplots(figsize=(9, 7))

im = ax.imshow(heat.values, cmap="RdYlGn_r", aspect="auto",
               vmin=0, vmax=heat.values.max())

ax.set_xticks(range(len(ALG_ORDER)))
ax.set_xticklabels(ALG_ORDER, fontsize=12, fontweight="bold")
ax.set_yticks(range(len(heat.index)))
ax.set_yticklabels(heat.index.str.upper(), fontsize=11)
ax.set_title("Average Optimality Gap (%) by Instance Family\n"
             "(darker red = worse; green = closer to optimum)",
             fontsize=13, fontweight="bold", pad=14)

# Annotate each cell
for i in range(len(heat.index)):
    for j in range(len(ALG_ORDER)):
        val = heat.values[i, j]
        if not np.isnan(val):
            text_color = "white" if val > heat.values.max() * 0.6 else "black"
            ax.text(j, i, f"{val:.1f}%", ha="center", va="center",
                    fontsize=9, color=text_color, fontweight="bold")

cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.04)
cbar.set_label("Avg Gap (%)", fontsize=10)
cbar.ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.0f%%"))

ax.grid(False)
save(fig, "family_heatmap.png")


# ══════════════════════════════════════════════════════════════════════════
# Plot 5 — CP-SAT status breakdown by instance family
# ══════════════════════════════════════════════════════════════════════════
print("[5/6] CP-SAT status breakdown ...")

cpsat_df = df[df["algorithm"] == "CP-SAT"].copy()
status_counts = (cpsat_df.groupby(["family", "status"])
                          .size().unstack("status").fillna(0))

# Ensure both columns exist
for col in ["OPTIMAL", "FEASIBLE"]:
    if col not in status_counts.columns:
        status_counts[col] = 0

status_counts = status_counts[["OPTIMAL", "FEASIBLE"]]
status_counts = status_counts.sort_values("OPTIMAL", ascending=True)

fig, ax = plt.subplots(figsize=(9, 6))

y = np.arange(len(status_counts))
h = 0.45
ax.barh(y, status_counts["OPTIMAL"], height=h,
        color="#2E7FD4", label="OPTIMAL (proven)", alpha=0.9)
ax.barh(y, status_counts["FEASIBLE"], height=h,
        left=status_counts["OPTIMAL"],
        color="#F4A623", label="FEASIBLE (60s timeout)", alpha=0.9)

# Annotate with percentages
totals = status_counts.sum(axis=1)
for i, (opt, tot) in enumerate(zip(status_counts["OPTIMAL"], totals)):
    pct = opt / tot * 100 if tot > 0 else 0
    ax.text(tot + 0.3, i, f"{pct:.0f}% optimal", va="center",
            fontsize=9, color="#2E7FD4")

ax.set_yticks(y)
ax.set_yticklabels(status_counts.index.str.upper(), fontsize=11)
ax.set_xlabel("Number of Instances", fontsize=12)
ax.set_title("CP-SAT Solve Status by Instance Family\n"
             "(OPTIMAL = proven best; FEASIBLE = hit 60s time limit)",
             fontsize=13, fontweight="bold", pad=14)
ax.legend(loc="lower right", fontsize=10, framealpha=0.9)
ax.grid(axis="y", alpha=0)

save(fig, "cpsat_status.png")


# ══════════════════════════════════════════════════════════════════════════
# Plot 6 — Win rate: which algorithm gets best makespan per instance
# ══════════════════════════════════════════════════════════════════════════
print("[6/6] Win rate chart ...")

# For each instance, find which algorithm has the lowest makespan
best_idx = df.groupby("instance")["makespan"].idxmin()
winners  = df.loc[best_idx, "algorithm"].value_counts().reindex(ALG_ORDER, fill_value=0)

total = winners.sum()
fig, ax = plt.subplots(figsize=(8, 5))

bars = ax.bar(ALG_ORDER, winners.values,
              color=[ALG_COLORS[a] for a in ALG_ORDER],
              width=0.55, edgecolor="white", linewidth=1.2, alpha=0.9)

for bar, alg, count in zip(bars, ALG_ORDER, winners.values):
    pct = count / total * 100
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 1.5,
            f"{count}\n({pct:.1f}%)",
            ha="center", va="bottom", fontsize=11,
            fontweight="bold", color=ALG_COLORS[alg])

ax.set_ylabel("Number of Instances Won", fontsize=12)
ax.set_title(f"Win Rate: Best Makespan Across {total} Instances\n"
             "(which algorithm produces the lowest makespan per instance)",
             fontsize=13, fontweight="bold", pad=14)
ax.set_ylim(0, winners.max() * 1.2)
ax.tick_params(axis="x", labelsize=12)

save(fig, "win_rate.png")


# ── Summary ───────────────────────────────────────────────────────────────
print(f"\nAll 6 plots saved to:  {OUTPUT_DIR.resolve()}/")
print("\nFiles generated:")
for f in sorted(OUTPUT_DIR.glob("*.png")):
    size_kb = f.stat().st_size / 1024
    print(f"  {f.name:<30} {size_kb:.0f} KB")