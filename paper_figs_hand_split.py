# -*- coding: utf-8 -*-
"""双手拆分诊断报告生成器。

为论文生成 etude07 的 hand_split 诊断对比图：
- 修复前：OMR 输出将双手音符混为和弦，取 top note 后形成跨八度伪音程
- 修复后：按 onset 最大间隙拆分为 RH/LH 两轨，各自形成平滑琶音线
"""

from pathlib import Path
from music21 import converter
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def generate_hand_split_diagram(xml_path: Path, output_path: Path, dpi: int = 150):
    """生成双手拆分诊断对比图。"""
    score = converter.parse(str(xml_path))
    
    # 获取第一个 part 的第一个小节（最具代表性的双手琶音）
    p = score.parts[0]
    m = p.getElementsByClass('Measure')[0]
    notes = list(m.recurse().notes)
    
    # 提取 top note 序列（修复前的行为）
    top_notes = []
    for el in notes:
        if hasattr(el, 'notes'):
            top = max(el.notes, key=lambda n: n.pitch.midi)
            top_notes.append(top)
        else:
            top_notes.append(el)
    
    # 双手拆分
    from scoreflow.analysis import hand_split
    new_score, ops = hand_split.split_score(score, threshold=16)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 9))
    
    # ---- (a) 修复前：混轨 ----
    ax1 = axes[0]
    xs = list(range(len(top_notes)))
    ys = [n.pitch.midi for n in top_notes]
    ax1.plot(xs, ys, 'r-o', linewidth=2.5, markersize=7, label='混轨 (取和弦最高音)')
    
    # 标注音名
    for i, n in enumerate(top_notes):
        ax1.annotate(n.pitch.nameWithOctave, 
                    (xs[i], ys[i]), 
                    textcoords='offset points', 
                    xytext=(0, 12), 
                    ha='center', 
                    fontsize=9,
                    fontweight='bold')
    
    ax1.set_title('(a) 修复前：OMR 输出混轨（双手音符被归入同一条声部）', 
                  fontsize=13, fontweight='bold', pad=10)
    ax1.set_ylabel('MIDI 音高编号', fontsize=11)
    ax1.legend(loc='upper left', fontsize=10)
    ax1.grid(True, alpha=0.3, linestyle='--')
    ax1.set_xlim(-0.5, len(top_notes) - 0.5)
    
    # ---- (b) 修复后：拆分为 RH/LH ----
    ax2 = axes[1]
    colors = {'Right Hand': '#d62728', 'Left Hand': '#1f77b4'}  # 红/蓝
    labels = {'Right Hand': '右手 (RH)', 'Left Hand': '左手 (LH)'}
    
    for part in new_score.parts:
        pname = part.partName
        for m in part.getElementsByClass('Measure')[:1]:
            ns = list(m.recurse().notes)
            xs = list(range(len(ns)))
            ys = [n.pitch.midi for n in ns]
            ax2.plot(xs, ys, 'o-', 
                    color=colors.get(pname, 'gray'), 
                    linewidth=2.5, 
                    markersize=7, 
                    label=labels.get(pname, pname))
            
            # 标注音名
            for i, n in enumerate(ns):
                ax2.annotate(n.pitch.nameWithOctave, 
                            (xs[i], ys[i]), 
                            textcoords='offset points', 
                            xytext=(0, 12), 
                            ha='center', 
                            fontsize=9,
                            fontweight='bold')
    
    ax2.set_title('(b) 修复后：双手拆分诊断（按 onset 最大音程间隙分离）', 
                  fontsize=13, fontweight='bold', pad=10)
    ax2.set_xlabel('音符序号（按时间顺序）', fontsize=11)
    ax2.set_ylabel('MIDI 音高编号', fontsize=11)
    ax2.legend(loc='upper left', fontsize=10)
    ax2.grid(True, alpha=0.3, linestyle='--')
    
    # 添加诊断说明文本框
    diag_text = (
        "诊断规则：当合并声部跨度 ≥ 16 半音（十度）时触发拆分\n"
        "拆分策略：按每个 onset 上的最大音程间隙分为高音组/低音组"
    )
    ax2.text(0.98, 0.02, diag_text, 
             transform=ax2.transAxes,
             fontsize=9,
             verticalalignment='bottom',
             horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi, bbox_inches='tight')
    print(f"Saved: {output_path}")
    return output_path


if __name__ == "__main__":
    HERE = Path(__file__).resolve().parent  # 仓库根目录
    xml_path = HERE / 'data' / 'etude07' / 'page_001.musicxml'
    output_path = HERE / 'cvaa_figs' / 'fig5_hand_split_diagnosis.png'
    generate_hand_split_diagram(xml_path, output_path, dpi=200)
