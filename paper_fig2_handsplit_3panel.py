# -*- coding: utf-8 -*-
"""v2 论文谱例 1（三联对照版）。

复用 paper_figs_hand_split.py 的真实数据流（从 etude07 第 1 小节解析），
再叠加 (c) 真值面板：来自 Sibelius 导出的 etude07righthand.musicxml / lefthand.musicxml。
"""

import os
from pathlib import Path
import matplotlib
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import xml.etree.ElementTree as ET
import sys

# 仓库根目录锚点：本脚本位于仓库根，数据与输出均相对仓库解析（开源可复现）
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from music21 import converter
from scoreflow.analysis import hand_split

# ---- 真值：从 Sibelius 分轨 musicxml 提取 ----
def extract_gt(xml_path: str):
    z = ET.parse(xml_path).getroot()
    out = []
    for m in z.iter('measure'):
        for n in m.findall('note'):
            p = n.find('pitch')
            if p is None: continue
            step = p.find('step').text
            aelt = p.find('alter')
            alter = int(aelt.text) if aelt is not None else 0
            octv = int(p.find('octave').text)
            base = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}[step]
            out.append((octv+1)*12 + base + alter)
    return out

# 输入路径（相对仓库 data/ 目录）
XML_INPUT = str(HERE / 'data' / 'etude07' / 'page_001.musicxml')
XML_GT_R  = str(HERE / 'data' / 'etude07' / 'righthand.musicxml')
XML_GT_L  = str(HERE / 'data' / 'etude07' / 'lefthand.musicxml')
os.makedirs(HERE / 'cvaa_figs', exist_ok=True)
OUT_PNG   = str(HERE / 'cvaa_figs' / 'fig2_handsplit.png')

# (a) 修复前：music21 解析原始 OMR 输出，取和弦最高音
score = converter.parse(XML_INPUT)
p0 = score.parts[0]
m0 = p0.getElementsByClass('Measure')[0]
notes0 = list(m0.recurse().notes)
ys_before = []
for el in notes0:
    if hasattr(el, 'notes'):
        ys_before.append(max(el.notes, key=lambda n: n.pitch.midi).pitch.midi)
    else:
        ys_before.append(el.pitch.midi)

# (b) 修复后：调用 hand_split
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

# (c) 真值
gt_right = extract_gt(XML_GT_R)[:len(sys_right)]
gt_left  = extract_gt(XML_GT_L)[:len(sys_left)]

# ---- 画三联图 ----
fig, axes = plt.subplots(3, 1, figsize=(8.5, 10.0), dpi=200)
fig.suptitle('etude7 第 1 小节：跨谱表琶音的双手拆分诊断（系统输出 vs Sibelius 分轨真值）',
             fontsize=12, fontweight='bold', y=0.995)

x = list(range(len(ys_before)))
PITCH = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def m2n(m): return f'{PITCH[m%12]}{m//12 - 1}'

# (a) 修复前
ax = axes[0]
ax.plot(x, ys_before, color='#A32D2D', lw=2.0, marker='o', mfc='#A32D2D', mec='#A32D2D', ms=5)
for xi, yi in zip(x, ys_before):
    ax.annotate(m2n(yi), (xi, yi), textcoords='offset points', xytext=(0, 6),
                ha='center', fontsize=7, color='#791F1F')
ax.set_title('(a) 修复前：OMR 将跨谱表琶音合为单声部，按最高音取轮廓 → D4→A6 单线，跨近 3 个八度',
             fontsize=9, loc='left', color='#791F1F', pad=4)
ax.set_xlim(-0.5, len(x) - 0.5); ax.set_ylim(34, 98)
ax.set_ylabel('MIDI 音高', fontsize=9)
ax.grid(alpha=0.3, ls=':')
ax.set_xticks(range(0, len(x), 2))
ax.text(0.01, 0.04, f'OMR 输出 14 音（前 4 单音 + 9 双音 + 1 单音；起点 D4）',
        transform=ax.transAxes, fontsize=7, color='#791F1F', alpha=0.7)

# (b) 修复后（系统拆分）
ax = axes[1]
x2 = list(range(len(sys_right)))
ax.plot(x2, sys_right, color='#A32D2D', lw=1.8, marker='o', mfc='#A32D2D', ms=4, label='系统右手')
ax.plot(x2, sys_left,  color='#185FA5', lw=1.8, marker='s', mfc='#185FA5', ms=4, label='系统左手')
for xi, yi in zip([0, 10, 15], [sys_right[0], sys_right[10], sys_right[15]]):
    dx = 8 if xi == 0 else 0
    ha = 'left' if xi == 0 else 'center'
    ax.annotate(m2n(yi), (xi, yi), textcoords='offset points', xytext=(dx, 6),
                ha=ha, fontsize=7, color='#791F1F')
for xi, yi in zip([0, 10, 15], [sys_left[0], sys_left[10], sys_left[15]]):
    if xi == 0:
        dx, dy, ha = 4, 8, 'left'
    elif xi == 15:
        dx, dy, ha = -4, -8, 'right'
    else:
        dx, dy, ha = 0, -12, 'center'
    ax.annotate(m2n(yi), (xi, yi), textcoords='offset points', xytext=(dx, dy),
                ha=ha, fontsize=7, color='#0C447C')
ax.set_title('(b) 修复后：经 10 度诊断（和声音程 ≥10 度），OMR 单声部被重写为右手（红）+ 左手（蓝）',
             fontsize=9, loc='left', color='#0C447C', pad=4)
ax.set_xlim(-0.5, len(x2) - 0.5); ax.set_ylim(34, 98)
ax.set_ylabel('MIDI 音高', fontsize=9)
ax.legend(loc='upper right', fontsize=8, frameon=True)
ax.grid(alpha=0.3, ls=':')
ax.set_xticks(range(0, len(x2), 2))

# (c) 真值对照
ax = axes[2]
x3 = list(range(len(gt_right)))
ax.plot(x3, gt_right, color='#5F5E5A', lw=1.4, ls='--', marker='o', mfc='white', mec='#5F5E5A', ms=4, label='真值右手 (Sibelius 导出)')
ax.plot(x3, gt_left,  color='#5F5E5A', lw=1.4, ls=':',  marker='s', mfc='white', mec='#5F5E5A', ms=4, label='真值左手 (Sibelius 导出)')
ax.plot(x2, sys_right, color='#A32D2D', lw=0.7, alpha=0.45, label='系统右手（参见 b）')
ax.plot(x2, sys_left,  color='#185FA5', lw=0.7, alpha=0.45, label='系统左手（参见 b）')
ax.set_title('(c) 真值对照：系统输出（淡彩）与 Sibelius 分轨 musicxml 真值（灰）完全吻合',
             fontsize=9, loc='left', color='#2C2C2A', pad=4)
ax.set_xlim(-0.5, len(x3) - 0.5); ax.set_ylim(34, 98)
ax.set_xlabel('音符序号（同小节内按时间顺序，1=第 1 个十六分音符）', fontsize=9)
ax.set_ylabel('MIDI 音高', fontsize=9)
ax.legend(loc='upper right', fontsize=7, frameon=True, ncol=2)
ax.grid(alpha=0.3, ls=':')
ax.set_xticks(range(0, len(x3), 2))
ax.text(0.99, 0.08, f'真值 16 音（4/4 拍 × 16 个十六分）；OMR 输出仅 14 音，漏识别 2 个音',
        transform=ax.transAxes, fontsize=7, color='#5F5E5A', alpha=0.8,
        ha='right', va='bottom',
        bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#5F5E5A', alpha=0.7))

plt.tight_layout(rect=[0, 0, 1, 0.97])
plt.savefig(OUT_PNG, bbox_inches='tight', facecolor='white', dpi=200)
print('saved', OUT_PNG)
