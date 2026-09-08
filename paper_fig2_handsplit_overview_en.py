# -*- coding: utf-8 -*-
"""CVAA 2026 论文「全景对比图」英文版（fig2_handsplit_overview_en.png）。

IEEE 要求图片内不得含中文字符，故本脚本输出纯英文版全景图：
  左面板 ── Baseline (no repair)：模拟 D2 缺陷（取 chord.notes[-1]），
            跨谱表琶音被合并为单声部，取末位音后形成剧烈起伏红线。
  右面板 ── After repair：和弦 MIDI 最高音修正 + 双手拆分，红/蓝双轨平稳琶音。

数据源与 paper_fig2_handsplit_overview.py 完全一致（etude07 第 1 小节
OMR 原始 musicxml + Sibelius 分轨真值）。
"""

import os
from pathlib import Path
import matplotlib

matplotlib.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys

# 仓库根目录锚点：数据与输出均相对仓库解析（开源可复现）
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from music21 import converter
from scoreflow.analysis import hand_split

# ---- 数据 ----
XML_INPUT = str(HERE / 'data' / 'etude07' / 'page_001.musicxml')

# (左) 零修复：模拟 D2 缺陷「取 chords[-1]」+ 不调 hand_split
score = converter.parse(XML_INPUT)
p0 = score.parts[0]
m0 = p0.getElementsByClass('Measure')[0]
notes0 = list(m0.recurse().notes)
ys_raw = []
for el in notes0:
    if hasattr(el, 'notes'):
        ys_raw.append(el.notes[-1].pitch.midi)  # bug: last element may be lowest
    else:
        ys_raw.append(el.pitch.midi)

# (右) 修复后：按 MIDI 最高音 + hand_split
new_score, ops = hand_split.split_score(score, threshold=16)
sys_right, sys_left = [], []
for part in new_score.parts:
    pname = part.partName
    for m in part.getElementsByClass('Measure')[:1]:
        ns = list(m.recurse().notes)
        ys = [n.pitch.midi for n in ns]
        if 'Right' in pname or '右手' in pname:
            sys_right = ys
        else:
            sys_left = ys


def _range(seq):
    return (max(seq) - min(seq)) if seq else 0


span_raw = _range(ys_raw)
span_r = _range(sys_right)
span_l = _range(sys_left)

# ---- 画图（2 行 1 列：单栏 3.4in 打印后字号仍 >=7pt）----
fig, axes = plt.subplots(2, 1, figsize=(5.6, 5.2), dpi=300)
fig.suptitle(
    'Measure 1 of Etude No. 7: hand-split repair',
    fontsize=13, fontweight='bold', y=0.985,
)

PITCH = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def m2n(m):
    return f'{PITCH[m % 12]}{m // 12 - 1}'


all_ys = ys_raw + sys_right + sys_left
y_min, y_max = min(all_ys) - 2, max(all_ys) + 2

# ===== 左面板：零修复 =====
ax = axes[0]
x = list(range(len(ys_raw)))
ax.plot(x, ys_raw, color='#A32D2D', lw=2.4, marker='o',
        mfc='#A32D2D', mec='#A32D2D', ms=6,
        label='Baseline OMR (chord.notes[-1], pre-fix bug)')

# 人手单手 8 度舒适阈值灰带
hand_limit_low = min(ys_raw) - 5
hand_limit_high = min(ys_raw) + 12  # 8 度 + 余量
ax.axhspan(hand_limit_low, hand_limit_high, color='#9E9E9E', alpha=0.10,
           label='One-hand 8ve comfort band (12 semitones)')
ax.axhline(y=hand_limit_low, color='#9E9E9E', ls='--', lw=0.7, alpha=0.55)
ax.axhline(y=hand_limit_high, color='#9E9E9E', ls='--', lw=0.7, alpha=0.55)

# 标注超过人手极限的点
for xi, yi in zip(x, ys_raw):
    if yi > hand_limit_high:
        ax.plot(xi, yi, marker='o', mfc='none', mec='#791F1F', mew=1.6, ms=11)
# 标注每个音名
for xi, yi in zip(x, ys_raw):
    ax.annotate(m2n(yi), (xi, yi), textcoords='offset points',
                xytext=(0, 7), ha='center', fontsize=9.5, color='#791F1F')

ax.set_title(f'(a) Baseline (chord.notes[-1], pre-repair)\n'
             f'span {span_raw} semitones (\u22482.6 oct): beyond one hand',
             fontsize=11, loc='left', color='#791F1F', pad=6)
ax.set_xlim(-0.6, len(x) - 0.4)
ax.set_ylim(y_min, y_max)
ax.set_xlabel('Note index', fontsize=11)
ax.set_ylabel('MIDI pitch', fontsize=11)
ax.legend(loc='lower right', fontsize=9.5, frameon=True)
ax.grid(alpha=0.3, ls=':')

# ===== 右面板：修复后 =====
ax = axes[1]
x2 = list(range(len(sys_right)))
ax.plot(x2, sys_right, color='#A32D2D', lw=2.0, marker='o', mfc='#A32D2D',
        mec='#A32D2D', ms=5, label='Right hand (system, repaired)')
ax.plot(x2, sys_left, color='#185FA5', lw=2.0, marker='s', mfc='#185FA5',
        mec='#185FA5', ms=5, label='Left hand (system, repaired)')

# 真值叠加
try:
    import xml.etree.ElementTree as ET
    def extract_gt(xml_path):
        z = ET.parse(xml_path).getroot()
        out = []
        for m in z.iter('measure'):
            for n in m.findall('note'):
                p = n.find('pitch')
                if p is None:
                    continue
                step = p.find('step').text
                aelt = p.find('alter')
                alter = int(aelt.text) if aelt is not None else 0
                octv = int(p.find('octave').text)
                base = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[step]
                out.append((octv + 1) * 12 + base + alter)
        return out
    gt_r = extract_gt(str(HERE / 'data' / 'etude07' / 'righthand.musicxml'))[:len(sys_right)]
    gt_l = extract_gt(str(HERE / 'data' / 'etude07' / 'lefthand.musicxml'))[:len(sys_left)]
    ax.plot(range(len(gt_r)), gt_r, color='#791F1F', ls='--', lw=0.8, alpha=0.45,
            label='Right hand (Sibelius GT)')
    ax.plot(range(len(gt_l)), gt_l, color='#0C447C', ls=':', lw=0.8, alpha=0.45,
            label='Left hand (Sibelius GT)')
except Exception as e:
    print('GT skipped:', e)

# 标注关键点
for xi, yi in zip([0, len(sys_right) // 2, len(sys_right) - 1],
                  [sys_right[0], sys_right[len(sys_right) // 2], sys_right[-1]]):
    ax.annotate(m2n(yi), (xi, yi), textcoords='offset points',
                xytext=(0, 7), ha='center', fontsize=9.5, color='#791F1F')
for xi, yi in zip([0, len(sys_left) // 2, len(sys_left) - 1],
                  [sys_left[0], sys_left[len(sys_left) // 2], sys_left[-1]]):
    ax.annotate(m2n(yi), (xi, yi), textcoords='offset points',
                xytext=(0, -10), ha='center', fontsize=9.5, color='#0C447C')

ax.set_title(f'(b) After repair (chord-top + hand split)\n'
             f'RH span {span_r} / LH span {span_l} semitones, within one hand',
             fontsize=11, loc='left', color='#0C447C', pad=6)
ax.set_xlim(-0.6, max(len(sys_right), len(sys_left)) - 0.4)
ax.set_xlabel('Note index', fontsize=11)
ax.legend(loc='lower right', fontsize=9.5, frameon=True)
ax.grid(alpha=0.3, ls=':')

plt.tight_layout(rect=[0, 0, 1, 0.92])
os.makedirs(HERE / 'cvaa_figs', exist_ok=True)
OUT_PNG = str(HERE / 'cvaa_figs' / 'fig2_handsplit_overview_en.png')
plt.savefig(OUT_PNG, bbox_inches="tight", facecolor="white", dpi=300)
print('saved', OUT_PNG)
print(f'span  raw={span_raw}  right={span_r}  left={span_l}')
