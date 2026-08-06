#!/usr/bin/env python3
"""Generate the book's data charts (rulers, roofline, KV budget bar) as SVG.

Replaces hand-positioned CSS/ASCII diagrams with real plots. Run this
after changing any of the numbers below, then `mdbook build` picks up
the regenerated SVGs automatically (they're static files under src/img/).

    pipeline/.venv/bin/python pipeline/make_charts.py
"""

import numpy as np
import math
import os

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

matplotlib.use("svg")

# --- Palette, lifted directly from theme/custom.css ------------------
PAPER = "#f7f8fa"
INK = "#14181f"
GRATICULE = "#dde2ea"
SIGNAL = "#0b6e75"
FLAG = "#a81e4d"
MUTED = "#5c6675"

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "src", "img")
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 12,
    "text.color": INK,
    "axes.edgecolor": GRATICULE,
    "axes.labelcolor": MUTED,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "svg.fonttype": "path",  # embed glyph outlines: renders identically everywhere
})


def save(fig, name):
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, format="svg", facecolor=PAPER, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print("wrote", os.path.relpath(path))


# --- The ruler: a log-scale strip placing a measurement against the --
# --- candidates it has to beat. -------------------------------------
def ruler(name, points, xlim, caption, figwidth=7.2, figheight=1.7):
    """points: list of (value, value_label, name_label, is_measured)"""
    fig, ax = plt.subplots(figsize=(figwidth, figheight))
    ax.set_xscale("log")
    ax.set_xlim(*xlim)

    # Collision avoidance: if two points sit close together on the log
    # axis, their centered value labels overlap. Stagger the crowded
    # ones onto a taller tick so the text has room.
    log_lo, log_hi = math.log10(xlim[0]), math.log10(xlim[1])
    span = log_hi - log_lo
    order = sorted(range(len(points)), key=lambda i: points[i][0])
    stagger = [False] * len(points)
    for a, b in zip(order, order[1:]):
        if (math.log10(points[b][0]) - math.log10(points[a][0])) / span < 0.11:
            stagger[b] = True

    top_extra = 0.3 if any(stagger) else 0.0
    ax.set_ylim(0, 1 + top_extra)
    ax.axhline(0.32, color=INK, linewidth=1, zorder=1)

    for i, (value, val_label, name_label, is_measured) in enumerate(points):
        color = FLAG if is_measured else INK
        muted = FLAG if is_measured else MUTED
        tick_top = 0.62 if is_measured else 0.48
        if stagger[i]:
            tick_top += top_extra
        lw = 2.2 if is_measured else 1.2
        ax.plot([value, value], [0.32, tick_top], color=color, linewidth=lw, zorder=3,
                 solid_capstyle="butt")
        ax.annotate(val_label, (value, tick_top), xytext=(0, 4), textcoords="offset points",
                    ha="center", va="bottom", fontsize=12.5, fontweight="bold", color=color)
        ax.annotate(name_label, (value, 0.32), xytext=(0, -10), textcoords="offset points",
                    ha="center", va="top", fontsize=10.5, color=muted)

    ax.set_yticks([])
    ax.spines[["left", "right", "top", "bottom"]].set_visible(False)
    ax.xaxis.set_major_locator(mticker.LogLocator(base=10))
    ax.xaxis.set_major_formatter(mticker.NullFormatter())
    ax.xaxis.set_minor_formatter(mticker.NullFormatter())
    ax.tick_params(axis="x", which="both", length=0)
    for v in ax.get_xticks(minor=False):
        if xlim[0] <= v <= xlim[1]:
            ax.axvline(v, color=GRATICULE, linewidth=0.8, zorder=0)

    fig.text(0.01, -0.06, caption, fontsize=10, color=MUTED, ha="left", va="top", wrap=True)
    save(fig, name)


ruler(
    "ruler-01-twenty-five-microseconds.svg",
    points=[
        (25e-6, "25 µs", "measured", True),
        (100e-6, "100 µs", "memcpy", False),
        (500e-6, "500 µs", "NVMe", False),
        (6.7e-3, "6.7 ms", "disk", False),
    ],
    xlim=(2e-6, 2e-2),
    caption="Log scale. The measurement doesn't land between the candidates. It lands to the left of all of them.",
)

ruler(
    "ruler-03-the-barrier.svg",
    points=[
        (4e-9, "4 ns", "floor", False),
        (100e-6, "100 µs", "measured", True),
        (1.7e-3, "1–3 ms", "SATA", False),
        (7.1e-3, "5–10 ms", "disk", False),
    ],
    xlim=(1e-9, 2e-2),
    caption="Log scale. The bandwidth floor sits six orders of magnitude from where the measurement lands.",
)

ruler(
    "ruler-07-the-ridge.svg",
    points=[
        (1, "1 FLOP/B", "measured", True),
        (156, "~156 FLOP/B", "ridge", False),
    ],
    xlim=(0.3, 500),
    caption="Log scale. The workload sits two orders of magnitude left of the ridge, deep in memory-bound territory.",
    figheight=1.6,
)


# --- The roofline: chapter 7 -----------------------------------------
def roofline():
    peak_tflops = 312.0
    bandwidth_tbs = 2.0  # TB/s
    ridge_x = peak_tflops / bandwidth_tbs  # FLOP/byte

    fig, ax = plt.subplots(figsize=(6.6, 5))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.2, 1000)
    ax.set_ylim(0.5, 1000)

    x_mem = [0.2, ridge_x]
    y_mem = [bandwidth_tbs * x for x in x_mem]
    x_comp = [ridge_x, 1000]
    y_comp = [peak_tflops, peak_tflops]

    ax.plot(x_mem, y_mem, color=INK, linewidth=2.2)
    ax.plot(x_comp, y_comp, color=INK, linewidth=2.2)
    ax.axvline(ridge_x, color=GRATICULE, linewidth=1, linestyle=(0, (4, 3)))

    ax.plot([ridge_x], [peak_tflops], marker="o", markersize=6, color=SIGNAL, zorder=4)
    ax.annotate(f"ridge point\n~{ridge_x:.0f} FLOP/byte", (ridge_x, peak_tflops),
                xytext=(8, -6), textcoords="offset points", fontsize=10.5, color=SIGNAL,
                ha="left", va="top")

    our_x, our_y = 1, bandwidth_tbs * 1
    ax.plot([our_x], [our_y], marker="o", markersize=7, color=FLAG, zorder=4)
    ax.annotate("batch 1, this chapter (1 FLOP/byte):\nGPU 99.4% idle", (our_x, our_y),
                xytext=(28, -22), textcoords="offset points", fontsize=10.5, color=FLAG,
                ha="left", va="top",
                arrowprops=dict(arrowstyle="-", color=FLAG, linewidth=0.8,
                                 shrinkA=4, shrinkB=4))

    ax.text(0.97, 0.04, "compute-bound", fontsize=10, color=MUTED, style="italic",
            transform=ax.transAxes, ha="right", va="bottom")
    ax.text(0.03, 0.96, "memory-bound", fontsize=10, color=MUTED, style="italic",
            transform=ax.transAxes, ha="left", va="top")

    ax.set_xlabel("arithmetic intensity (FLOP/byte)")
    ax.set_ylabel("achieved TFLOP/s")
    ax.grid(True, which="major", color=GRATICULE, linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRATICULE)
    ax.tick_params(length=0)

    save(fig, "roofline-07-the-ridge.svg")


roofline()


# --- The KV-cache budget bar: chapter 8 -------------------------------
def kv_budget_bar():
    card_gb = 80
    weights_gb = 14
    kv_gb = 64
    ridge_sequences = 156
    ridge_kv_gb = ridge_sequences * 1  # 1 GB/sequence at 2048 tokens

    fig, ax = plt.subplots(figsize=(7.4, 2.9))

    # Row 1: this card.
    ax.barh(1, weights_gb, color=MUTED, edgecolor=PAPER, height=0.5, label="weights (14 GB)")
    ax.barh(1, kv_gb, left=weights_gb, color=SIGNAL, edgecolor=PAPER, height=0.5,
            label="KV cache")
    ax.annotate("64 GB, 64 sequences", (weights_gb + kv_gb, 1), xytext=(10, 0),
                textcoords="offset points", fontsize=10, color=SIGNAL, ha="left", va="center",
                fontweight="bold")

    # Row 0: what the ridge wants, drawn past the card limit.
    ax.barh(0, weights_gb, color=MUTED, edgecolor=PAPER, height=0.5, alpha=0.55)
    ax.barh(0, ridge_kv_gb, left=weights_gb, color=FLAG, edgecolor=PAPER, height=0.5, alpha=0.9,
            label="KV cache the ridge wants")
    ax.annotate(f"~{ridge_kv_gb:.0f} GB, {ridge_sequences} sequences\n(~{weights_gb + ridge_kv_gb:.0f} GB total, doesn't fit)",
                (weights_gb + ridge_kv_gb, 0), xytext=(10, 0),
                textcoords="offset points", fontsize=10, color=FLAG, ha="left", va="center",
                fontweight="bold")

    ax.axvline(card_gb, color=INK, linewidth=1.6, linestyle=(0, (4, 3)))
    ax.annotate("80 GB card", (card_gb, 1.42), xytext=(0, 2), textcoords="offset points",
                fontsize=10, color=INK, fontweight="bold", ha="center", va="bottom")

    ax.legend(handles=[
        plt.Rectangle((0, 0), 1, 1, color=MUTED, label="weights"),
        plt.Rectangle((0, 0), 1, 1, color=SIGNAL, label="KV cache, this card"),
        plt.Rectangle((0, 0), 1, 1, color=FLAG, label="KV cache the ridge wants"),
    ], loc="center left", frameon=False, fontsize=9.5, bbox_to_anchor=(1.02, 0.5), ncol=1)

    ax.set_yticks([0, 1])
    ax.set_yticklabels(["ridge wants\n(156 seqs)", "this card\n(64 seqs)"], fontsize=10)
    ax.set_xlim(0, weights_gb + ridge_kv_gb + 55)
    ax.set_ylim(-0.35, 1.65)
    ax.set_xlabel("GB")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRATICULE, linewidth=0.8)
    ax.set_axisbelow(True)

    save(fig, "kv-budget-08-kv-cache.svg")


kv_budget_bar()


# --- The survival grid: chapter 2 -------------------------------------
def survival_grid():
    layers = ["userspace buffer", "page cache", "drive write cache", "flash / platter"]
    failures = ["kill -9\n(SIGKILL)", "kernel\npanic", "power\nloss", "power loss\n+ PLP"]
    # True = survives, False = dies. Row order top-to-bottom matches `layers`.
    survives = [
        [False, False, False, False],  # userspace buffer
        [True, False, False, False],   # page cache
        [True, True, False, True],     # drive write cache
        [True, True, True, True],      # flash / platter
    ]

    n_rows, n_cols = len(layers), len(failures)
    fig, ax = plt.subplots(figsize=(6.6, 4.0))

    for r in range(n_rows):
        for c in range(n_cols):
            ok = survives[r][c]
            color = SIGNAL if ok else FLAG
            y = n_rows - 1 - r
            ax.add_patch(plt.Rectangle((c, y), 0.94, 0.86, facecolor=color, alpha=0.16 if ok else 0.14,
                                        edgecolor=color, linewidth=1.3))
            ax.text(c + 0.47, y + 0.43, "✓" if ok else "✗", ha="center", va="center",
                    fontsize=17, color=color, fontweight="bold")

    ax.set_xlim(0, n_cols)
    ax.set_ylim(0, n_rows)
    ax.set_xticks([c + 0.47 for c in range(n_cols)])
    ax.set_xticklabels(failures, fontsize=9.5)
    ax.xaxis.tick_top()
    ax.set_yticks([n_rows - 1 - r + 0.43 for r in range(n_rows)])
    ax.set_yticklabels(layers, fontsize=10.5)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.text(0.5, -0.04,
              "Read each row left to right: the first ✗ is where that failure stops your data.",
              fontsize=10, color=MUTED, ha="center", va="top")

    save(fig, "survival-grid-02-the-ladder.svg")


survival_grid()


# --- Fixed vs. adaptive batching latency: chapter 5 ---------------------
def group_commit_bars():
    scenarios = ["low load\n(10 events/sec)", "high load\n(100,000 events/sec)"]
    fixed_ms = [100_000, 10]       # 100 s, 10 ms, in milliseconds
    adaptive_ms = [0.1, 0.1]       # ~100 µs either way

    x = [0, 1.4]
    width = 0.42
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.set_yscale("log")

    bars_fixed = ax.bar([xi - width / 2 - 0.02 for xi in x], fixed_ms, width=width,
                        color=FLAG, label="fixed count (N=1000)")
    bars_adapt = ax.bar([xi + width / 2 + 0.02 for xi in x], adaptive_ms, width=width,
                        color=SIGNAL, label="adaptive (fsync-triggered)")

    for bars, values in ((bars_fixed, fixed_ms), (bars_adapt, adaptive_ms)):
        for rect, v in zip(bars, values):
            label = f"{v/1000:.0f} s" if v >= 1000 else (f"{v:.0f} ms" if v >= 1 else f"{v*1000:.0f} µs")
            ax.annotate(label, (rect.get_x() + rect.get_width() / 2, v), xytext=(0, 4),
                        textcoords="offset points", ha="center", va="bottom", fontsize=10,
                        fontweight="bold", color=rect.get_facecolor())

    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=10.5)
    ax.set_ylabel("wait to fill a batch (ms, log scale)")
    ax.set_ylim(0.05, 300_000)
    ax.legend(frameon=False, fontsize=9.5, loc="upper center", bbox_to_anchor=(0.5, 1.22), ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(GRATICULE)
    ax.tick_params(length=0)
    ax.grid(axis="y", which="major", color=GRATICULE, linewidth=0.8)
    ax.set_axisbelow(True)

    save(fig, "group-commit-05-group-commit.svg")


group_commit_bars()


# --- Slot occupancy, static vs continuous: chapter 9 -------------------
def occupancy_timelines():
    lengths = [5, 8, 6, 120, 7, 9, 6, 11]
    total = max(lengths)
    fig, (top, bot) = plt.subplots(2, 1, figsize=(7.4, 3.6), sharex=True)

    for i, L in enumerate(lengths):
        top.barh(i, L, color=SIGNAL, edgecolor=PAPER, height=0.72)
        top.barh(i, total - L, left=L, color=GRATICULE, edgecolor=PAPER, height=0.72)
    used = sum(lengths)
    top.set_title(f"static: one batch, runs to its slowest member "
                  f"({used}/{len(lengths) * total} slot-steps used, 18%)",
                  fontsize=10.5, color=INK, loc="left", pad=8)

    # Continuous: each slot refills from a queue of short requests.
    queue = [7, 9, 6, 11, 5, 8, 6, 7, 9, 6, 11, 5, 8, 6, 7, 9, 6, 11, 5, 8]
    qi = 0
    for i, L in enumerate(lengths):
        t = 0
        run = L
        while t < total:
            bit = min(run, total - t)
            bot.barh(i, bit, left=t, color=SIGNAL, edgecolor=PAPER, height=0.72)
            t += bit
            if t >= total:
                break
            run = queue[qi % len(queue)]
            qi += 1
    bot.set_title("continuous: a finished slot is refilled on the next step",
                  fontsize=10.5, color=INK, loc="left", pad=8)

    for ax in (top, bot):
        ax.set_yticks([])
        ax.set_ylim(-0.7, len(lengths) - 0.3)
        ax.set_facecolor(PAPER)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
    bot.set_xlabel("decode steps", fontsize=10)
    fig.patch.set_facecolor(PAPER)
    save(fig, "occupancy-09-the-slot-that-waited.svg")


# --- KV waste under three allocators: chapter 10 -----------------------
def kv_waste_bars():
    budget_mb = 66 * 1024
    schemes = [
        ("contiguous\n(reserve 2048)", 2048 * 0.5, 350 * 0.5),
        ("ideal\n(pay per token)", 350 * 0.5, 350 * 0.5),
        ("paged\n(16-token blocks)", 352 * 0.5, 350 * 0.5),
    ]
    fig, ax = plt.subplots(figsize=(7.4, 3.0))
    for i, (label, held_mb, used_mb) in enumerate(schemes):
        fits = int(budget_mb / held_mb)
        ax.barh(i, held_mb, color=GRATICULE, edgecolor=PAPER, height=0.6)
        ax.barh(i, used_mb, color=SIGNAL, edgecolor=PAPER, height=0.6)
        ax.annotate(f"{fits} sequences fit", (held_mb, i), xytext=(10, 0),
                    textcoords="offset points", fontsize=10.5,
                    color=SIGNAL if i else FLAG, va="center", ha="left",
                    fontweight="bold")
    ax.set_yticks(range(len(schemes)))
    ax.set_yticklabels([s[0] for s in schemes], fontsize=10)
    ax.set_xlabel("MB held per sequence (shaded: reserved but never used)", fontsize=10)
    ax.set_xlim(0, 1250)
    ax.set_facecolor(PAPER)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    fig.patch.set_facecolor(PAPER)
    save(fig, "kv-waste-10-page-table.svg")


# --- Launch overhead against the floor: chapter 11 ---------------------
def launch_overhead_bars():
    floor = 3.13
    rows = [("eager", floor, 4.67), ("CUDA graph", floor, 0.26)]
    fig, ax = plt.subplots(figsize=(7.4, 2.4))
    for i, (label, mem, cpu) in enumerate(rows):
        ax.barh(i, mem, color=SIGNAL, edgecolor=PAPER, height=0.5)
        ax.barh(i, cpu, left=mem, color=FLAG, edgecolor=PAPER, height=0.5)
        ax.annotate(f"{mem + cpu:.2f} ms", (mem + cpu, i), xytext=(10, 0),
                    textcoords="offset points", fontsize=10.5, color=INK,
                    va="center", ha="left", fontweight="bold")
    ax.axvline(floor, color=MUTED, linestyle="--", linewidth=1.1)
    ax.annotate("roofline floor, 3.13 ms", (floor, 1.55), xytext=(4, 0),
                textcoords="offset points", fontsize=9.5, color=MUTED, ha="left")
    ax.barh(-1, 0, color=SIGNAL, label="memory traffic")
    ax.barh(-1, 0, color=FLAG, label="CPU launch overhead")
    ax.legend(loc="lower right", frameon=False, fontsize=9.5)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=10.5)
    ax.set_ylim(-0.6, 1.9)
    ax.set_xlabel("milliseconds per decode token", fontsize=10)
    ax.set_facecolor(PAPER)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    fig.patch.set_facecolor(PAPER)
    save(fig, "launch-overhead-11-below-the-floor.svg")


# --- Speculation on the roofline: chapter 12 ---------------------------
def speculative_roofline():
    peak, bw, ridge = 312.0, 2.0, 156.0
    x = np.logspace(-1, 3.2, 400)
    y = np.minimum(x * bw, peak)

    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    ax.loglog(x, y, color=MUTED, linewidth=1.8)
    ax.axvline(ridge, color=GRATICULE, linewidth=1.2, zorder=0)
    ax.annotate(f"ridge, ~{ridge:.0f} FLOP/byte", (ridge, 3.5), xytext=(8, 0),
                textcoords="offset points", fontsize=9.5, color=MUTED, ha="left")

    for xi, label, colour in ((1, "decode 1 token", SIGNAL),
                              (5, "verify 5 tokens", FLAG)):
        ax.plot([xi], [xi * bw], "o", color=colour, markersize=8, zorder=5)
        ax.annotate(label, (xi, xi * bw), xytext=(0, -20),
                    textcoords="offset points", fontsize=10, color=colour,
                    ha="center", fontweight="bold")

    ax.annotate("both read 14 GB: both cost 7 ms", (2.3, 22),
                fontsize=10, color=INK, ha="center")
    ax.set_xlabel("arithmetic intensity (FLOP/byte)", fontsize=10)
    ax.set_ylabel("achieved TFLOP/s", fontsize=10)
    ax.set_facecolor(PAPER)
    ax.grid(True, which="major", color=GRATICULE, linewidth=0.7)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.patch.set_facecolor(PAPER)
    save(fig, "speculative-12-spending-the-idle.svg")


occupancy_timelines()
kv_waste_bars()
launch_overhead_bars()
speculative_roofline()
