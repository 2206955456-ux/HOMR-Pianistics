# -*- coding: utf-8 -*-
"""特征：收缩把位（《音型集》口径）。

相邻 5 个音构成的 4 个音程的半音距离之和 < 阈值（默认 6 半音 = 减五度）。
即音符被压缩在一个极窄的音域内连续跑动，典型于单音反复、窄音程颤音、
同音换指等音型。

参数：
    threshold: 4 个音程之和的阈值（半音），默认 6（减五度）。
               "小于"阈值才命中（严格小于）。
"""

from music21 import note

from scoreflow.analysis.features.base import ScoreFeature


class ContractedGrip(ScoreFeature):
    name = "contracted_grip"
    description = "相邻5音的4个音程之和小于阈值半音（默认6=减五度）"
    group_size = 5
    weight = 1.0   # 《音型集》收缩把位难度加权

    def match(self, notes: list[note.Note]) -> bool:
        threshold = int(self.params.get("threshold", 6))
        total = sum(
            self.semitones(notes[i], notes[i + 1])
            for i in range(len(notes) - 1)
        )
        return total < threshold


FEATURE = ContractedGrip
