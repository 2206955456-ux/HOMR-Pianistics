# -*- coding: utf-8 -*-
"""双手拆分（hand split）诊断修复。

背景
----
钢琴跨谱表琶音（如车尔尼 Op.740 No.21 第 1 小节）中，快速分解和弦的音符
实际由左右手交替演奏，但 OMR 输出的 MusicXML 常按垂直位置把双手音符归入
同一声部/谱表，形成单个声部内跨 10 度以上（>=16 半音）的"超人手"音程。

诊断开关
--------
若某小节内合并所有谱表后的音符跨度 >= threshold 半音（默认 16 = 十度），
则触发双手拆分：按每个 onset 上的最大音程间隙把音符切分为右手（高音组）
与左手（低音组），并重建为两个独立声部（Right Hand / Left Hand）。

处理流程
--------
1. 合并当前 Score 所有 part 在对应小节的音符；
2. 按 onset 分组；
3. 检测整体跨度是否 >= threshold；
4. 若触发，将每个 onset 的音符按最大音程间隙分为 upper / lower；
   单音 onset 则根据与前一个 upper/lower 中点的距离分配，保持声部连续性；
5. 重建两个 Part：Right Hand、Left Hand；
6. 返回新 Score 与操作日志。

局限
----
- 仅处理 onset 分组内即可拆分的二元/多元和弦；声部真正交错（如一只手插入
  另一只手中间）时仍需后续符干方向信息；
- 阈值为启发值，钢琴单手最大舒适跨度约 8–9 度，默认 10 度（16 半音）留有余量。
"""

from __future__ import annotations

from music21 import chord, note, stream

DEFAULT_THRESHOLD = 16  # 十度


def _all_notes_in_measure(measure) -> list:
    """收集小节内全部音符（展开和弦为独立 Note）。

    注意：和弦内子音符的 offset 是相对于和弦容器的，需要加上和弦本身的
    offset 才是小节内的绝对 onset。
    """
    out = []
    for el in measure.recurse().notes:
        if isinstance(el, chord.Chord):
            base_off = float(el.offset)
            for n in el.notes:
                # 复制并修正绝对 offset
                n2 = n.__class__(name=n.pitch.nameWithOctave)
                n2.offset = base_off + float(n.offset)
                n2.duration.quarterLength = n.duration.quarterLength
                out.append(n2)
        else:
            out.append(el)
    return out


def _group_by_onset(notes: list, tolerance: float = 1e-5) -> dict[float, list]:
    """按 onset（offset）分组，容差处理浮点误差。"""
    groups: dict[float, list] = {}
    for n in notes:
        off = float(n.offset)
        key = round(off / tolerance) * tolerance if tolerance else off
        groups.setdefault(key, []).append(n)
    return groups


def _split_onset_group(notes: list) -> tuple[list, list]:
    """把一个 onset 上的音符按最大音程间隙拆成 upper / lower。

    返回 (upper_notes, lower_notes)。
    """
    if len(notes) == 1:
        return (notes, [])
    sorted_notes = sorted(notes, key=lambda n: n.pitch.midi)
    if len(sorted_notes) == 2:
        return ([sorted_notes[-1]], [sorted_notes[0]])
    # >=3 个音符：找最大间隙
    gaps = [
        (sorted_notes[i + 1].pitch.midi - sorted_notes[i].pitch.midi, i)
        for i in range(len(sorted_notes) - 1)
    ]
    _, idx = max(gaps)
    return (sorted_notes[idx + 1:], sorted_notes[:idx + 1])


def _midi_center(notes: list) -> float | None:
    if not notes:
        return None
    return sum(n.pitch.midi for n in notes) / len(notes)


def split_measure_notes(merged_notes: list, threshold: int = DEFAULT_THRESHOLD,
                        triggered: bool | None = None) -> tuple[list, list, bool]:
    """拆分已合并的小节音符为右手/左手两组。

    返回 (rh_notes, lh_notes, triggered)。
    """
    if not merged_notes:
        return [], [], False
    midis = [n.pitch.midi for n in merged_notes]
    if triggered is None:
        triggered = (max(midis) - min(midis)) >= threshold

    groups = _group_by_onset(merged_notes)
    rh_notes: list = []
    lh_notes: list = []
    prev_rh_center: float | None = None
    prev_lh_center: float | None = None

    for off in sorted(groups.keys()):
        grp = groups[off]
        up, low = _split_onset_group(grp)

        # 若 onset 是单音，按与前一手音域中心的距离分配
        if not up or not low:
            single = up if up else low
            # 首次无参考：按中点粗分（高于全局中点 → RH）
            if prev_rh_center is None and prev_lh_center is None:
                mid = (max(midis) + min(midis)) / 2
                up = [n for n in single if n.pitch.midi >= mid]
                low = [n for n in single if n.pitch.midi < mid]
            else:
                up = []
                low = []
                for n in single:
                    d_rh = abs(n.pitch.midi - (prev_rh_center or -1e9))
                    d_lh = abs(n.pitch.midi - (prev_lh_center or 1e9))
                    if prev_rh_center is None:
                        low.append(n)
                    elif prev_lh_center is None:
                        up.append(n)
                    elif d_rh <= d_lh:
                        up.append(n)
                    else:
                        low.append(n)

        if up:
            prev_rh_center = _midi_center(up)
        if low:
            prev_lh_center = _midi_center(low)
        rh_notes.extend(up)
        lh_notes.extend(low)

    return rh_notes, lh_notes, triggered


def split_score(score: stream.Score, threshold: int = DEFAULT_THRESHOLD,
                in_place: bool = False) -> tuple[stream.Score, list]:
    """对 Score 做双手拆分。

    返回 (new_score, ops_log)。new_score 只包含两个 Part：Right Hand、Left Hand。
    """
    parts = list(score.parts)
    if not parts:
        return score, []

    # 收集所有小节号与模板
    measure_map: dict[int, tuple] = {}  # mnum -> (offset, template_measure)
    for part in parts:
        for m in part.getElementsByClass("Measure"):
            mnum = int(m.number)
            if mnum not in measure_map:
                measure_map[mnum] = (float(m.offset), m)

    rh_part = stream.Part()
    rh_part.partName = "Right Hand"
    lh_part = stream.Part()
    lh_part.partName = "Left Hand"

    ops = []
    for mnum in sorted(measure_map.keys()):
        m_offset, template = measure_map[mnum]
        # 合并所有 part 中该小节的音符
        merged: list = []
        for part in parts:
            for m in part.getElementsByClass("Measure"):
                if int(m.number) == mnum:
                    merged.extend(_all_notes_in_measure(m))
                    break

        rh_notes, lh_notes, triggered = split_measure_notes(merged, threshold)
        if triggered:
            ops.append({
                "measure": mnum,
                "rh_count": len(rh_notes),
                "lh_count": len(lh_notes),
                "rh_range": (min(n.pitch.midi for n in rh_notes), max(n.pitch.midi for n in rh_notes)) if rh_notes else None,
                "lh_range": (min(n.pitch.midi for n in lh_notes), max(n.pitch.midi for n in lh_notes)) if lh_notes else None,
            })

        def _build_measure(notes: list, mtemplate) -> stream.Measure:
            m = stream.Measure(number=mtemplate.number)
            # 复制小节属性（调号、拍号、谱号）
            for attr in mtemplate.getElementsByClass("Attributes"):
                m.insert(0, attr)
            for n in notes:
                m.insert(n.offset, n)
            return m

        rh_part.insert(m_offset, _build_measure(rh_notes, template))
        lh_part.insert(m_offset, _build_measure(lh_notes, template))

    new_score = stream.Score()
    new_score.insert(0, rh_part)
    new_score.insert(0, lh_part)
    return new_score, ops


def analyze_and_split(xml_text: str, threshold: int = DEFAULT_THRESHOLD) -> tuple[str, list]:
    """XML 文本级入口：解析 -> 拆分 -> 写回 MusicXML 文本。

    与 cross_hand.py 风格一致，方便 engine 统一调用。
    """
    from music21 import converter
    score = converter.parseData(xml_text)
    new_score, ops = split_score(score, threshold)
    # 写回 XML（使用临时文件）
    import tempfile, os
    tmp = tempfile.NamedTemporaryFile(suffix=".xml", delete=False, mode="w", encoding="utf-8")
    tmp.close()
    gex = converter.subConverters.ConverterMusicXML()
    gex.write(new_score, fmt="musicxml", fp=tmp.name)
    text = open(tmp.name, "r", encoding="utf-8").read()
    os.unlink(tmp.name)
    return text, ops
