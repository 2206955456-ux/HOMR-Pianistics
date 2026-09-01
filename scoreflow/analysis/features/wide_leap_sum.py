# -*- coding: utf-8 -*-
"""示例特征 1（默认启用）：

小节内相邻 3 个音，前后两个音程的半音距离之和超过阈值（默认 12 = 八度）。

例如 C4 -> E5 -> G4：|E5-C4|=16, |G4-E5|=3，和为 19 > 12，命中。

参数：
    threshold:      半音数阈值，默认 12（八度）
    arpeggio_aware: 琶音感知开关，默认 false。开启后，若 3 个音的音级
                    （pitch class）集合能整体嵌入某个三和弦或常用七和弦
                    （即它们同为某个和弦的和弦音），则视为分解和弦（琶音）
                    音型，不判为宽跳。
    monotonic:      是否要求 3 音走向相同（3 高于 2 高于 1 或 3 低于 2 低于 1，
                    即前两音与后两音的走向一致），默认 false（不要求）。
                    《音型集》口径定义"伸张把位"要求走向相同，开启后
                    折返型琶音（如 A♭2→D♭2→A♭2）不再命中。

问题背景：复合音程判据（两段音程之和 > 八度）的本意是捕捉旋律宽跳，
但在琶音织体（如左手分解和弦伴奏、跨八度琶音跑动）上会系统性误报：
音群实际是"同一和弦的和弦音先后出现"，不是旋律跳进。
arpeggio_aware 用和弦归属判定（chord membership）豁免这类音型。

已知局限（详见 README「琶音误报与 arpeggio_aware 开关」）：
  - 音群混入非和弦音（经过音、倚音、和弦外音）时判定失效，仍会误报；
  - 声部交错（如和弦顶音与低音交替）形成的音群可能不满足和弦归属，
    仍会误报；
  - 和弦归属是必要条件而非充分条件——真宽跳若恰好落在同一和弦内
    （如 C4 -> E5 -> G5）也会被豁免。
"""

from music21 import chord, note

from scoreflow.analysis.features.base import ScoreFeature

# 预生成全部三和弦与常用七和弦的音级（pitch class）集合：
#   大三 {0,4,7} / 小三 {0,3,7} / 减三 {0,3,6} / 增三 {0,4,8}
#   大七 {0,4,7,11} / 小七 {0,3,7,10} / 属七 {0,4,7,10}
#   减七 {0,3,6,9} / 半减七 {0,3,6,10}
_INTERVAL_SETS = (
    (0, 4, 7), (0, 3, 7), (0, 3, 6), (0, 4, 8),
    (0, 4, 7, 11), (0, 3, 7, 10), (0, 4, 7, 10),
    (0, 3, 6, 9), (0, 3, 6, 10),
)
CHORD_PCS: frozenset[frozenset[int]] = frozenset(
    frozenset((root + iv) % 12 for iv in ivals)
    for root in range(12) for ivals in _INTERVAL_SETS
)


def _pitch_class(el) -> int:
    """元素的音级；和弦元素取最高音的音级。"""
    if isinstance(el, chord.Chord):
        return el.notes[-1].pitch.pitchClass
    return el.pitch.pitchClass


def is_arpeggio(notes) -> bool:
    """音群是否构成"分解和弦"（同一和弦的和弦音先后出现）。

    判据：音群内所有音的音级集合，是某个三和弦/常用七和弦音级集合的
    子集（任意八度、任意出现次序、允许重复音）。例如：
      A-2 -> D-2 -> A-2  音级 {A♭,D♭} ⊆ D♭ 大三和弦 -> 琶音
      C4  -> E5  -> G4   音级 {C,E,G}  =  C  大三和弦 -> 琶音
      C4  -> E5  -> G-4  音级 {C,E,G♭} 不属于任何上述和弦 -> 非琶音
    """
    pcs = frozenset(_pitch_class(el) for el in notes)
    return any(pcs <= c for c in CHORD_PCS)


class WideLeapSum(ScoreFeature):
    name = "wide_leap_sum"
    description = "相邻3音的2个音程之和超过阈值半音（默认12=八度）"
    group_size = 3
    weight = 2.0   # 《音型集》伸张把位难度加权

    def match(self, notes: list[note.Note]) -> bool:
        threshold = int(self.params.get("threshold", 12))
        total = self.semitones(notes[0], notes[1]) + self.semitones(notes[1], notes[2])
        if total <= threshold:
            return False
        # 走向相同（单调）：3 高于 2 高于 1，或 3 低于 2 低于 1
        if self.params.get("monotonic", False):
            d1 = notes[1].pitch.midi - notes[0].pitch.midi
            d2 = notes[2].pitch.midi - notes[1].pitch.midi
            if d1 * d2 <= 0:  # 走向不一致（含同音重复）不命中
                return False
        # 琶音感知：分解和弦音型豁免，不判为宽跳
        if self.params.get("arpeggio_aware", False) and is_arpeggio(notes):
            return False
        return True


FEATURE = WideLeapSum
