# -*- coding: utf-8 -*-
"""CVAA 论文图表生成脚本。
输出到 D:\githubmusic\论文写作\cvaa_figs\：
  fig1_pipeline.png       系统管线图（含语义修复模块）
  fig2_handsplit.png      etude7 M1：双手拆分诊断前后对比（谱例）
  fig3_ablation.png       伸张把位修复消融：4 曲命中对比
  fig4_difficulty.png     难度加权总分随考级等级趋势
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from music21 import converter

from scoreflow.analysis.hand_split import split_score

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
plt.rcParams["axes.unicode_minus"] = False

OUT = r"D:\githubmusic\论文写作\cvaa_figs"
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- 图 1 管线
def fig1_pipeline():
    fig, ax = plt.subplots(figsize=(9.2, 2.9))
    ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")

    boxes = [
        (1,  "PDF 乐谱",            "input",   "#FCE4D6"),
        (18, "300 DPI\n逐页渲染",     "proc",    "#DDEBF7"),
        (35, "页面图像\n(PNG)",       "input",   "#FCE4D6"),
        (52, "HOMR OMR\n识别",       "proc",    "#DDEBF7"),
        (69, "MusicXML",             "input",   "#FCE4D6"),
        (86, "特征检测\n滑动窗口",    "proc",    "#E2EFDA"),
        (96, "统计报告\nMD/JSON/XLSX","out",    "#EDEDED"),
    ]
    def draw(box, fontsize=9):
        x, label, kind, fc = box
        w = 12
        if kind == "out":
            w = 10; x = 96
        bb = FancyBboxPatch((x, 8), w, 14, boxstyle="round,pad=0.6",
                            fc=fc, ec="#4472C4" if kind == "proc" else "#7F7F7F",
                            lw=1.4, zorder=2)
        ax.add_patch(bb)
        ax.text(x + w/2, 15, label, ha="center", va="center", fontsize=fontsize, zorder=3)
        return x + w
    for b in boxes:
        draw(b)

    # 语义修复模块（高亮，夹在 MusicXML 与特征检测之间）
    bb = FancyBboxPatch((82.2, 2.5), 13.5, 25, boxstyle="round,pad=0.6",
                        fc="#FFF2CC", ec="#BF8F00", lw=2.2, ls="--", zorder=3)
    ax.add_patch(bb)
    ax.text(89, 22.2, "语义修复", ha="center", va="center", fontsize=9.5,
            fontweight="bold", color="#7F6000", zorder=4)
    ax.text(89, 8.2, "交叉手声部\n重分配\n双手拆分\n和弦最高音\n修正", ha="center", va="center",
            fontsize=7.2, color="#7F6000", zorder=4)

    # 箭头
    def arrow(x1, x2, y=15, color="#404040"):
        a = FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>", mutation_scale=13,
                            lw=1.3, color=color, zorder=1)
        ax.add_patch(a)
    arrow(13.0, 18.0); arrow(30.0, 35.0); arrow(47.0, 52.0)
    arrow(64.0, 68.4); arrow(81.0, 82.2); arrow(95.7, 96.0)

    # 绕行箭头（MusicXML 直接进特征检测的备选路径）
    a = FancyArrowPatch((81.0, 20.5), (86.0, 20.5), arrowstyle="-|>",
                        mutation_scale=11, lw=1.1, color="#C00000", ls=(0, (4, 3)), zorder=1)
    ax.add_patch(a)
    ax.text(75.5, 24.0, "修复前：跳过语义修复（直接统计）", fontsize=6.8,
            color="#C00000", ha="center")

    ax.text(50, 2.0, "图 1  系统管线：OMR 输出 MusicXML 后，经语义修复（交叉手声部重分配 + 双手拆分 + 和弦最高音修正）"
                     "再进入特征检测", fontsize=8, ha="center", color="#404040")
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_pipeline.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig1_pipeline.png OK")


# ---------------------------------------------------------------- 图 2 双手拆分谱例
def fig2_handsplit():
    """etude7 第 1 小节：OMR 合并声部 vs 双手拆分后的 RH/LH 轮廓。"""
    score = converter.parse(r"D:\HOMR\output\etude07\pages\page_001.musicxml")

    # (a) 拆分前：从 part 0 按 chord_top 取出的"合并声部"轮廓
    part0 = score.parts[0]
    m1_pre = part0.measure(1)
    pre_seq = []
    for el in m1_pre.recurse().notes:
        if hasattr(el, "notes"):
            pre_seq.append(max(el.notes, key=lambda n: n.pitch.midi))
        else:
            pre_seq.append(el)
    pre_seq.sort(key=lambda n: n.offset)
    pre_x = list(range(1, len(pre_seq) + 1))
    pre_y = [n.pitch.midi for n in pre_seq]
    pre_names = [n.pitch.nameWithOctave for n in pre_seq]

    # (b) 拆分后：RH / LH 两条轮廓
    split, _ = split_score(score, threshold=16)
    rh_part, lh_part = split.parts[0], split.parts[1]
    rh_m1 = rh_part.measure(1)
    lh_m1 = lh_part.measure(1)
    rh_seq = sorted(list(rh_m1.recurse().notes), key=lambda n: n.offset)
    lh_seq = sorted(list(lh_m1.recurse().notes), key=lambda n: n.offset)
    rh_x = list(range(1, len(rh_seq) + 1))
    lh_x = list(range(1, len(lh_seq) + 1))
    rh_y = [n.pitch.midi for n in rh_seq]
    lh_y = [n.pitch.midi for n in lh_seq]
    rh_names = [n.pitch.nameWithOctave for n in rh_seq]
    lh_names = [n.pitch.nameWithOctave for n in lh_seq]

    fig, axes = plt.subplots(2, 1, figsize=(9.2, 5.6), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1], "hspace": 0.42})

    # (a) 拆分前
    ax = axes[0]
    ax.plot(pre_x, pre_y, "-o", color="#C00000", lw=1.4, ms=4, alpha=0.9)
    for xi, yi, nm in zip(pre_x, pre_y, pre_names):
        ax.annotate(nm, (xi, yi), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=7.5, color="#C00000")
    ax.set_ylim(35, 96)
    ax.set_yticks(range(36, 96, 12))
    ax.set_ylabel("MIDI", fontsize=9)
    ax.set_title("(a) 拆分前：OMR 将跨谱表琶音合并为单一声部，\n"
                 "按最高音取轮廓得到 D4→A6 的单一线条，暗示单手跨越近 3 个八度",
                 fontsize=9.5, loc="left", color="#C00000")

    # (b) 拆分后
    ax = axes[1]
    ax.plot(rh_x, rh_y, "-o", color="#C00000", lw=1.4, ms=4, alpha=0.9, label="右手")
    ax.plot(lh_x, lh_y, "-s", color="#2E75B6", lw=1.4, ms=4, alpha=0.9, label="左手")
    # 标注若干关键点避免拥挤
    for xi, yi, nm in zip(rh_x, rh_y, rh_names):
        if xi % 4 == 1 or xi == len(rh_x):
            ax.annotate(nm, (xi, yi), textcoords="offset points", xytext=(0, 7),
                        ha="center", fontsize=7, color="#C00000")
    for xi, yi, nm in zip(lh_x, lh_y, lh_names):
        if xi % 4 == 1 or xi == len(lh_x):
            ax.annotate(nm, (xi, yi), textcoords="offset points", xytext=(0, -12),
                        ha="center", fontsize=7, color="#2E75B6")
    ax.set_ylim(35, 96)
    ax.set_yticks(range(36, 96, 12))
    ax.set_ylabel("MIDI", fontsize=9)
    ax.set_xlabel("音符序号（同一小节内按时间顺序）", fontsize=9)
    ax.legend(fontsize=9, loc="upper right")
    ax.set_title("(b) 拆分后：经 10 度诊断，重建右手（红）F#3→A6 与左手（蓝）D2→F#5 两条平滑平行琶音线",
                 fontsize=9.5, loc="left", color="#333333")

    fig.suptitle("谱例 1  etude7 第 1 小节：跨谱表琶音的双手拆分诊断",
                 fontsize=10.5, y=0.995, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(OUT, "fig2_handsplit.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig2_handsplit.png OK")


# ---------------------------------------------------------------- 图 3 消融
def fig3_ablation():
    pieces = ["etude7", "etude8", "etude9", "etude10"]
    human = [0, 23, 15, 63]
    pre   = [29, 27, 33, 63]   # 修复前（交叉手+琶音，chord bug）
    post  = [6, 1, 18, 34]     # 修复后（+chord 最高音修正）

    x = range(len(pieces))
    w = 0.26
    fig, ax = plt.subplots(figsize=(8.6, 3.9))
    b1 = ax.bar([i-w for i in x], human, w, label="人工标注（金标准）", color="#A9A9A9")
    b2 = ax.bar([i for i in x], pre, w, label="修复前（chord bug）", color="#C00000")
    b3 = ax.bar([i+w for i in x], post, w, label="修复后（+最高音修正）", color="#2E75B6")

    for bars in (b1, b2, b3):
        for r in bars:
            h = r.get_height()
            if h > 0:
                ax.annotate(f"{int(h)}", (r.get_x()+r.get_width()/2, h),
                            textcoords="offset points", xytext=(0, 2),
                            ha="center", fontsize=8)

    ax.set_xticks(list(x))
    ax.set_xticklabels([f"etude{p[-1]}\n({['7级','8级','9级','10级'][i]})" for i, p in enumerate(pieces)], fontsize=9)
    ax.set_ylabel("伸张把位命中小节数", fontsize=9.5)
    ax.set_ylim(0, 72)
    ax.legend(fontsize=9, loc="upper left")
    ax.set_title("图 3  把位语义修复对伸张把位特征的影响：etude7 误报 29→6（逼近人工 0），\n"
                 "但琶音感知对 etude8/10 的真实伸张把位存在过度豁免（见 4.4 讨论）",
                 fontsize=10, loc="left")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, "fig3_ablation.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig3_ablation.png OK")


# ---------------------------------------------------------------- 图 4 难度趋势
def fig4_difficulty_trend():
    """图 4：难度加权总分随考级等级的趋势（含 Spearman ρ）"""
    import json

    grades = list(range(1, 11))
    scores = []
    for i in grades:
        p = rf"D:/HOMR/output_grades/etude{i:02d}/reports/report.json"
        d = json.load(open(p, encoding="utf-8"))
        scores.append(d["scores"][0].get("difficulty_score", 0.0))

    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=200)
    ax.plot(grades, scores, "o-", color="#C0392B", lw=2.2, ms=7,
            markeredgecolor="white", markeredgewidth=1.2)
    for x, y in zip(grades, scores):
        ax.annotate(f"{y:g}", (x, y), textcoords="offset points",
                    xytext=(0, 9), ha="center", fontsize=9, color="#333333")

    ax.set_xlabel("考级等级", fontsize=12)
    ax.set_ylabel("难度加权总分 D", fontsize=12)
    ax.set_xticks(grades)
    ax.set_xticklabels([f"{g} 级" for g in grades], fontsize=10)
    ax.grid(axis="y", ls="--", alpha=0.4)
    ax.set_title("难度加权总分随考级等级的变化（Spearman ρ = 0.988）",
                 fontsize=12, pad=12)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    out = r"D:/githubmusic/论文写作/cvaa_figs/fig4_difficulty.png"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.savefig(out, dpi=200)
    print("fig4_difficulty.png OK")


if __name__ == "__main__":
    fig1_pipeline()
    fig2_handsplit()
    fig3_ablation()
    fig4_difficulty_trend()
    print("DONE ->", OUT)
