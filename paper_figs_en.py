"""CVAA 2026 paper — English versions of fig1/fig3/fig4 (no CJK chars).
All labels English, fonts DejaVu Sans (matplotlib default, embedded in PDF).
Output dir: <repo>/cvaa_figs_en/
"""
import os
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# Font: ASCII-safe. DejaVu Sans is matplotlib's default; force explicit so
# downstream viewers don't substitute a CJK fallback.
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["axes.unicode_minus"] = False

# 仓库根目录锚点：输出与数据均相对仓库解析（开源可复现）
HERE = Path(__file__).resolve().parent
OUT = str(HERE / "cvaa_figs_en")
os.makedirs(OUT, exist_ok=True)

# ============================================================ fig1 EN
def fig1_pipeline_en():
    """System pipeline — English labels.
    Widen canvas so the 'Semantic repair' callout does not overlap the
    adjacent process boxes.
    """
    fig, ax = plt.subplots(figsize=(7.2, 2.6))
    ax.set_xlim(0, 125)
    ax.set_ylim(-1, 32)
    ax.axis("off")

    # x-position, label, kind, fill-color
    boxes = [
        (1,   "PDF\nscore",       "input", "#FCE4D6"),
        (18,  "300 DPI\nrender",  "proc",  "#DDEBF7"),
        (35,  "Page\nPNG",        "input", "#FCE4D6"),
        (52,  "HOMR\nOMR",        "proc",  "#DDEBF7"),
        (69,  "Music\nXML",       "input", "#FCE4D6"),
        (88,  "Feature\ndetect",  "proc",  "#E2EFDA"),
        (108, "Report\nMD/JSON",  "out",   "#EDEDED"),
    ]

    def draw(box, fontsize=13):
        x, label, kind, fc = box
        w = 13
        if kind == "out":
            w = 14
            x = 108
        bb = FancyBboxPatch(
            (x, 14), w, 11, boxstyle="round,pad=0.6",
            fc=fc, ec="#4472C4" if kind == "proc" else "#7F7F7F",
            lw=1.4, zorder=2,
        )
        ax.add_patch(bb)
        ax.text(x + w / 2, 19.5, label, ha="center", va="center",
                fontsize=fontsize, zorder=3)
        return x + w

    for b in boxes:
        draw(b)

    # Semantic-repair module (highlighted) — placed BELOW the main row so
    # it does not overlap any process box. Two thin arrows route MusicXML
    # down into the repair module and back up to the feature-detection
    # box, making the data flow explicit.
    bb = FancyBboxPatch(
        (62.0, 1.5), 33.0, 9, boxstyle="round,pad=0.6",
        fc="#FFF2CC", ec="#BF8F00", lw=2.0, ls="--", zorder=3,
    )
    ax.add_patch(bb)
    ax.text(78.5, 7.7, "Semantic repair",
            ha="center", va="center",
            fontsize=13, fontweight="bold", color="#7F6000", zorder=4)
    ax.text(78.5, 4.0,
            "Cross-hand part re-assignment    "
            "Hand split    "
            "Chord-top correction",
            ha="center", va="center", fontsize=10, color="#7F6000", zorder=4)

    # Arrows
    def arrow(x1, x2, y=19.5, color="#404040"):
        a = FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>",
                            mutation_scale=13, lw=1.3, color=color, zorder=1)
        ax.add_patch(a)

    arrow(14.0, 18.0)   # PDF -> 300 DPI
    arrow(31.0, 35.0)   # 300 DPI -> PNG
    arrow(48.0, 52.0)   # PNG -> HOMR
    arrow(65.0, 69.0)   # HOMR -> MusicXML
    arrow(95.0, 108.0)  # Feature detection -> report

    # Down/up arrows between MusicXML and the repair module
    arrow_dn = FancyArrowPatch((76.0, 14.0), (76.0, 10.5), arrowstyle="-|>",
                               mutation_scale=13, lw=1.3, color="#404040",
                               zorder=1)
    ax.add_patch(arrow_dn)
    arrow_up = FancyArrowPatch((82.0, 10.5), (82.0, 14.0), arrowstyle="-|>",
                               mutation_scale=13, lw=1.3, color="#404040",
                               zorder=1)
    ax.add_patch(arrow_up)

    # Bypass arrow (ablation path: skip repair) — drawn as a red curve
    # above MusicXML pointing into feature detection
    a = FancyArrowPatch((82.0, 25.0), (95.0, 25.0), arrowstyle="-|>",
                        mutation_scale=11, lw=1.1, color="#C00000",
                        ls=(0, (4, 3)), zorder=1,
                        connectionstyle="arc3,rad=-0.18")
    ax.add_patch(a)
    ax.text(88.5, 28.5, "Pre-repair: skip repair (ablation path)",
            fontsize=10, color="#C00000", ha="center")

    plt.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_pipeline_en.png"),
                dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("fig1_pipeline_en.png OK")


# ============================================================ fig3 EN
def fig3_ablation_en():
    pieces = ["etude7", "etude8", "etude9", "etude10"]
    human = [0, 23, 15, 63]
    pre   = [29, 27, 33, 63]   # pre-repair (cross-hand + arpeggio, chord bug)
    post  = [6, 1, 18, 34]     # post-repair (+ chord-top correction)

    x = list(range(len(pieces)))
    w = 0.26
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    b1 = ax.bar([i - w for i in x], human, w, label="Human (gold standard)",
                color="#A9A9A9")
    b2 = ax.bar(list(x), pre, w,
                label="Pre-repair (chord bug)",
                color="#C00000")
    b3 = ax.bar([i + w for i in x], post, w,
                label="Post-repair (+ chord-top fix)",
                color="#2E75B6")

    for bars in (b1, b2, b3):
        for r in bars:
            h = r.get_height()
            if h > 0:
                ax.annotate(f"{int(h)}",
                            (r.get_x() + r.get_width() / 2, h),
                            textcoords="offset points", xytext=(0, 2),
                            ha="center", fontsize=9.5)

    grades = ["Grade 7", "Grade 8", "Grade 9", "Grade 10"]
    ax.set_xticks(x)
    ax.set_xticklabels([f"{p}\n({g})" for p, g in zip(pieces, grades)],
                       fontsize=10.5)
    ax.set_ylabel("Stretched-grip hit count (measures)", fontsize=11)
    ax.set_ylim(0, 72)
    ax.legend(fontsize=9.5, loc="upper left")
    ax.set_title("Effect of semantic repair on stretched grips",
                 fontsize=11.5, pad=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, "fig3_ablation_en.png"),
                dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("fig3_ablation_en.png OK")


# ============================================================ fig4 EN
def fig4_difficulty_trend_en():
    import json

    grades = list(range(1, 11))
    scores = []
    for i in grades:
        p = str(HERE / 'data' / 'reports' / f'etude{i:02d}' / 'report.json')
        d = json.load(open(p, encoding="utf-8"))
        scores.append(d["scores"][0].get("difficulty_score", 0.0))

    fig, ax = plt.subplots(figsize=(5.0, 3.5), dpi=200)
    ax.plot(grades, scores, "o-", color="#C0392B", lw=2.2, ms=7,
            markeredgecolor="white", markeredgewidth=1.2)
    for x, y in zip(grades, scores):
        ax.annotate(f"{y:g}", (x, y), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=9.5, color="#333333")

    ax.set_xlabel("Graded examination level", fontsize=11)
    ax.set_ylabel("Difficulty-weighted total D", fontsize=11)
    ax.set_xticks(grades)
    ax.set_xticklabels([f"G{g}" for g in grades], fontsize=10)
    ax.grid(axis="y", ls="--", alpha=0.4)
    ax.set_title("Difficulty vs. graded level ($\\rho$ = 0.988)",
                 fontsize=11.5, pad=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    out = os.path.join(OUT, "fig4_difficulty_en.png")
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor="white")
    print("fig4_difficulty_en.png OK")


if __name__ == "__main__":
    fig1_pipeline_en()
    fig3_ablation_en()
    fig4_difficulty_trend_en()
    print("DONE ->", OUT)
