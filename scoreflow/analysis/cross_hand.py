# -*- coding: utf-8 -*-
"""交叉手（crossed hands）启发式声部重分配。

背景
----
钢琴谱中"哪只手演奏哪个音"由**符干朝向**决定，而非谱表（staff）。交叉手段落中，
右手可能进入低音谱表、左手可能进入高音谱表。HOMR 输出的 MusicXML 未保留
`<stem>` 标签，且按音符垂直位置（pitch）分配 staff/voice，导致交叉手音符被
错误归入对方声部，进而使"同一声部"类特征（如 wide_leap_sum）漏检。

本模块提供一种**启发式近似**（模拟符干朝向判断）：
  - staff 2（低音谱表）上音高 > C5（midi 72）的音符：左手跑到高音区的交叉音符
    （正常演奏时符干朝上）→ 重标为右手（voice 1 / staff 1）；
  - staff 1（高音谱表）上音高 < C3（midi 48）的音符：右手跑到低音区的交叉音符
    （正常演奏时符干朝下）→ 重标为左手（voice 5 / staff 2）。

局限
----
双手音域重叠段落（如琶音跑动跨越两个谱表）可能被误判，阈值 C3/C5 可调。
该启发式是"提出问题 + 近似修正"的第一版方案，不保证完全还原真实演奏分配；
后续应在 OMR 识别阶段直接读取符干方向（见 README「已知限制」）。

用法
----
    from scoreflow.analysis.cross_hand import reassign
    new_text, ops = reassign(xml_text, high_threshold=72, low_threshold=48)
"""

from __future__ import annotations

import re
from collections import defaultdict

SEMIS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
DEFAULT_HIGH = 72  # staff2 上的高音阈值（C5）
DEFAULT_LOW = 48   # staff1 上的低音阈值（C3）


def note_midi(note_xml: str):
    """从单个 <note> 文本中解析 midi 编号（无音高信息返回 None）。"""
    step = re.search(r"<step>([A-G])</step>", note_xml)
    octave = re.search(r"<octave>(\d+)</octave>", note_xml)
    alter = re.search(r"<alter>(-?\d+)</alter>", note_xml)
    if not step or not octave:
        return None
    return ((int(octave.group(1)) + 1) * 12
            + SEMIS[step.group(1)]
            + (int(alter.group(1)) if alter else 0))


def reassign(xml_text: str, high_threshold: int = DEFAULT_HIGH,
             low_threshold: int = DEFAULT_LOW) -> tuple[str, list]:
    """对 MusicXML 文本做交叉手启发式重分配。

    返回 (重分配后的 XML 文本, 操作列表)。操作项为 dict：
      {kind: "LH->RH"|"RH->LH", note: "G5", midi: 79,
       voice: 原voice, staff: 原staff, measure: 小节号}

    按 <measure> 分段处理，因此操作记录带小节号；无 number 属性时按页内顺序编号。
    只处理 <note> 内同时含 pitch 与 <staff> 的元素。
    """
    ops = []
    measure_counter = 0

    def repl_note(n: str, measure_num: str) -> str:
        midi = note_midi(n)
        if midi is None:
            return n
        staff_m = re.search(r"<staff>(\d)</staff>", n)
        voice_m = re.search(r"<voice>(\d+)</voice>", n)
        if not staff_m:
            return n
        s = staff_m.group(1)
        v = voice_m.group(1) if voice_m else "1"
        step = re.search(r"<step>([A-G])</step>", n)
        octave = re.search(r"<octave>(\d+)</octave>", n)
        name = f"{step.group(1)}{octave.group(1)}" if step and octave else "?"
        if s == "2" and midi > high_threshold and v.startswith("5"):
            ops.append({"kind": "LH->RH", "note": name, "midi": midi,
                        "voice": v, "staff": s, "measure": measure_num})
            n = re.sub(r"<voice>\d+</voice>", "<voice>1</voice>", n, count=1)
            n = n.replace("<staff>2</staff>", "<staff>1</staff>")
        elif s == "1" and midi < low_threshold and v in ("1", "2"):
            ops.append({"kind": "RH->LH", "note": name, "midi": midi,
                        "voice": v, "staff": s, "measure": measure_num})
            n = re.sub(r"<voice>\d+</voice>", "<voice>5</voice>", n, count=1)
            n = n.replace("<staff>1</staff>", "<staff>2</staff>")
        return n

    def repl_measure(m) -> str:
        nonlocal measure_counter
        measure_counter += 1
        tag = m.group(0)
        mnum = re.search(r'<measure[^>]*number="(\d+)"', tag)
        num = mnum.group(1) if mnum else str(measure_counter)
        return re.sub(r"<note>.*?</note>",
                      lambda nm: repl_note(nm.group(0), num), tag, flags=re.S)

    out = re.sub(r"<measure[^>]*>.*?</measure>", repl_measure, xml_text, flags=re.S)
    return out, ops


def summarize_ops(ops: list[dict]) -> dict:
    """按方向汇总重分配操作数：{"LH->RH": n, "RH->LH": n}。"""
    total = defaultdict(int)
    for op in ops:
        total[op["kind"]] += 1
    return dict(total)
