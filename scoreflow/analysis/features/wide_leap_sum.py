# -*- coding: utf-8 -*-
"""示例特征 1（默认启用）：

小节内相邻 3 个音，前后两个音程的半音距离之和超过阈值（默认 12 = 八度）。

例如 C4 -> E5 -> G4：|E5-C4|=16, |G4-E5|=3，和为 19 > 12，命中。
"""

from music21 import note

from scoreflow.analysis.features.base import ScoreFeature


class WideLeapSum(ScoreFeature):
    name = "wide_leap_sum"
    description = "相邻3音的2个音程之和超过阈值半音（默认12=八度）"
    group_size = 3

    def match(self, notes: list[note.Note]) -> bool:
        threshold = int(self.params.get("threshold", 12))
        total = self.semitones(notes[0], notes[1]) + self.semitones(notes[1], notes[2])
        return total > threshold


FEATURE = WideLeapSum
