# -*- coding: utf-8 -*-
"""特征：连续八分音符跑动（《音型集》口径）。

小节内出现连续 3 个八分音符即命中。

参数：
    window_size: 连续八分音符个数，默认 3。
"""

from music21 import note

from scoreflow.analysis.features.base import ScoreFeature


class ConsecutiveEighths(ScoreFeature):
    name = "consecutive_eighths"
    description = "连续3个八分音符"
    group_size = 3
    weight = 1.0   # 《音型集》连续八分音符跑动难度加权

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.group_size = int(self.params.get("window_size", 3))

    def match(self, notes: list[note.Note]) -> bool:
        return all(
            n.duration.type == "eighth"
            or abs(n.duration.quarterLength - 0.5) < 1e-9
            for n in notes
        )


FEATURE = ConsecutiveEighths
