# -*- coding: utf-8 -*-
"""特征：小节内出现连续 5 个十六分音符（《音型集》口径）。

窗口内 5 个音符的时值全部为十六分音符即命中。
休止符不计入音符序列（由引擎统一处理），窗口按音符出现顺序滑动。

参数：
    window_size: 连续十六分音符个数，默认 5（《音型集》口径；
                 早期版本为 6，可通过 window_size=6 恢复旧行为）。
"""

from music21 import note

from scoreflow.analysis.features.base import ScoreFeature


class ConsecutiveSixteenths(ScoreFeature):
    name = "consecutive_sixteenths"
    description = "连续5个十六分音符"
    group_size = 5
    weight = 2.0   # 《音型集》连续十六分音符跑动难度加权

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.group_size = int(self.params.get("window_size", 5))

    def match(self, notes: list[note.Note]) -> bool:
        return all(
            n.duration.type == "16th"
            or abs(n.duration.quarterLength - 0.25) < 1e-9
            for n in notes
        )


FEATURE = ConsecutiveSixteenths
