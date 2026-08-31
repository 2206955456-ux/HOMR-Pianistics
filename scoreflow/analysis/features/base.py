# -*- coding: utf-8 -*-
"""音群特征基类。

自定义一个分析特征只需三步：
  1. 在本目录新建一个 .py 文件，继承 ScoreFeature；
  2. 填 name / description / group_size，实现 match()；
  3. 在 config.yaml 的 analysis.features 中启用它并传参数。

match() 收到的是相邻 group_size 个音符（list[music21.note.Note]），
返回 True 表示这个音群命中特征。
"""

from music21 import chord, note


class ScoreFeature:
    #: 特征唯一标识（与 config.yaml 中 analysis.features 的键对应）
    name: str = "base"
    #: 人类可读描述（写进报告）
    description: str = ""
    #: 滑动窗口大小：相邻多少个音构成一个"音群"
    group_size: int = 2
    #: 为 True 时窗口元素保留原始对象（note.Note 或 chord.Chord），
    #: 用于"连续和弦"这类需要判断元素类型的特征；
    #: 为 False（默认）时和弦按 chord_mode 压平为单音。
    needs_chords: bool = False

    def __init__(self, params: dict | None = None):
        self.params = params or {}

    def match(self, notes) -> bool:
        """判断一个相邻音群是否符合特征，必须实现。"""
        raise NotImplementedError

    # ---- 常用工具 ----
    @staticmethod
    def semitones(n1: note.Note, n2: note.Note) -> int:
        """两个音的半音距离（绝对值）。"""
        return abs(n2.pitch.midi - n1.pitch.midi)

    @staticmethod
    def is_chord(el) -> bool:
        """元素是否是和弦（needs_chords=True 时窗口元素可能是 Chord）。"""
        return isinstance(el, chord.Chord)

    @staticmethod
    def el_midi(el) -> int:
        """元素的中音区编号；和弦取最高音。"""
        if isinstance(el, chord.Chord):
            return el.notes[-1].pitch.midi
        return el.pitch.midi

    def describe_params(self) -> str:
        return ", ".join(f"{k}={v}" for k, v in self.params.items())
