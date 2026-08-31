# -*- coding: utf-8 -*-
"""特征：小节内出现连续 6 个十六分音符。

窗口内 6 个音符的时值全部为十六分音符即命中。
休止符不计入音符序列（由引擎统一处理），窗口按音符出现顺序滑动。
"""

from music21 import note

from scoreflow.analysis.features.base import ScoreFeature


class ConsecutiveSixteenths(ScoreFeature):
    name = "consecutive_sixteenths"
    description = "连续6个十六分音符"
    group_size = 6

    def match(self, notes: list[note.Note]) -> bool:
        return all(
            n.duration.type == "16th"
            or abs(n.duration.quarterLength - 0.25) < 1e-9
            for n in notes
        )


FEATURE = ConsecutiveSixteenths
