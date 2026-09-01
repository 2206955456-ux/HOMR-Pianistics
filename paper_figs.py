# -*- coding: utf-8 -*-
"""CVAA 论文图表生成脚本。
输出 3 张图到 D:\githubmusic\论文写作\cvaa_figs\：
  fig1_pipeline.png   系统管线图（含语义修复模块）
  fig2_arpeggio.png   etude7 M1 右手：chord 音符排序缺陷修复前后对比（谱例）
  fig3_ablation.png   把位修复消融：4 曲 wide_leap_sum 命中对比
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

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
    def draw(box, color, fontsize=9):
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
        draw(b, None)

    # 语义修复模块（高亮，夹在 MusicXML 与特征检测之间）
    bb = FancyBboxPatch((82.2, 2.5), 13.5, 25, boxstyle="round,pad=0.6",
                        fc="#FFF2CC", ec="#BF8F00", lw=2.2, ls="--", zorder=3)
    ax.add_patch(bb)
    ax.text(89, 22.2, "语义修复", ha="center", va="center", fontsize=9.5,
            fontweight="bold", color="#7F6000", zorder=4)
    ax.text(89, 8.2, "交叉手声部\n重分配\n和弦最高音\n修正", ha="center", va="center",
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

    ax.text(50, 2.0, "图 1  系统管线：OMR 输出 MusicXML 后，经语义修复（交叉手声部重分配 + 和弦最高音修正）"
                     "再进入特征检测", fontsize=8, ha="center", color="#404040")
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, "fig1_pipeline.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig1_pipeline.png OK")

# ---------------------------------------------------------------- 图 2 谱例
def fig2_arpeggio():
    # etude7 page_001 M1 右手：修复前后音符序列（MIDI）
    pre = ["D4","F#4","A4","D5","D4","A5","A4","D5","A6","D5","A4","A5","D4","D5"]
    post = ["D4","F#4","A4","D5","F#5","A5","D6","F#6","A6","F#6","D6","A5","F#5","D5"]
    midi = {"C":0,"C#":1,"D":2,"D#":3,"E":4,"F":5,"F#":6,"G":7,"G#":8,"A":9,"A#":10,"B":11}
    def to_midi(name):
        pc, octv = name[:-1], int(name[-1])
        return (octv+1)*12 + midi[pc]
    pre_m = [to_midi(p) for p in pre]
    post_m = [to_midi(p) for p in post]
    x = list(range(1, len(pre)+1))

    fig, axes = plt.subplots(2, 1, figsize=(9.2, 5.4), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1], "hspace": 0.42})
    colors_pre  = ["#C00000" if i in (4,5,7,8,10,11,12,13) else "#404040" for i in range(len(pre))]
    # 修复前：画折线+散点，标出虚假跳进
    ax = axes[0]
    ax.plot(x, pre_m, "-o", color="#C00000", lw=1.4, ms=4, alpha=0.85)
    # 用红色标注含 >12 半音跳变的相邻段
    for i in range(len(pre_m)-1):
        if abs(pre_m[i+1]-pre_m[i]) > 7:
            ax.plot([x[i], x[i+1]], [pre_m[i], pre_m[i+1]], "-", color="#C00000", lw=2.6, alpha=0.9)
    for xi, mi, nm in zip(x, pre_m, pre):
        ax.annotate(nm, (xi, mi), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=8, color="#C00000", fontweight="bold")
    ax.set_ylim(58, 86)
    ax.set_yticks(range(60, 85, 5))
    ax.set_ylabel("MIDI", fontsize=9)
    ax.set_title("(a) 修复前：取 <chord> 内最后一个音符（el.notes[-1]），\n"
                 "琶音被拆成跨八度伪跳进（红色粗线段），宽跳误报 10 处",
                 fontsize=9.5, loc="left", color="#C00000")

    # 修复后
    ax = axes[1]
    ax.plot(x, post_m, "-o", color="#2E75B6", lw=1.4, ms=4)
    for xi, mi, nm in zip(x, post_m, post):
        ax.annotate(nm, (xi, mi), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=8, color="#2E75B6")
    ax.set_ylim(58, 86)
    ax.set_yticks(range(60, 85, 5))
    ax.set_ylabel("MIDI", fontsize=9)
    ax.set_xlabel("音符序号（同一小节内按时间顺序）", fontsize=9)
    ax.set_title("(b) 修复后：按 MIDI 取和弦最高音（max-by-midi），\n"
                 "恢复平滑琶音轮廓（D 大调分解和弦上行），宽跳命中 0 处",
                 fontsize=9.5, loc="left", color="#2E75B6")

    fig.suptitle("谱例 1  etude7 第 1 小节右手声部：OMR 输出中 <chord> 音符排序缺陷导致的宽跳误报与修复",
                 fontsize=10.5, y=0.995, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(OUT, "fig2_arpeggio.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig2_arpeggio.png OK")

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
    ax.set_ylabel("宽跳（伸张把位）命中小节数", fontsize=9.5)
    ax.set_ylim(0, 72)
    ax.legend(fontsize=9, loc="upper left")
    ax.set_title("图 3  把位语义修复对宽跳特征的影响：etude7 误报 29→6（逼近人工 0），\n"
                 "但琶音感知对 etude8/10 的真宽跳存在过度豁免（见 4.4 讨论）",
                 fontsize=10, loc="left")
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    plt.tight_layout()
    fig.savefig(os.path.join(OUT, "fig3_ablation.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("fig3_ablation.png OK")

if __name__ == "__main__":
    fig1_pipeline()
    fig2_arpeggio()
    fig3_ablation()
    print("DONE ->", OUT)


def fig4_difficulty_trend():
    """图 4：难度加权总分随考级等级的趋势（含 Spearman ρ）"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import json, os

    # 中文字体
    for f in font_manager.fontManager.ttflist:
        if "SimHei" in f.name or "Microsoft YaHei" in f.name:
            plt.rcParams["font.sans-serif"] = [f.name]
            break
    plt.rcParams["axes.unicode_minus"] = False

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
    print("✓", out)


if __name__ == "__main__":
    fig4_difficulty_trend()
