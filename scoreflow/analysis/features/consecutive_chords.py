# -*- coding: utf-8 -*-
"""特征：同一声部内连续 6 个和弦。

窗口内 6 个元素全部是和弦（Chord）即命中。
需在基类声明 needs_chords=True，引擎会保留原始元素（含和弦类型）传给 match。
"""

from scoreflow.analysis.features.base import ScoreFeature


class ConsecutiveChords(ScoreFeature):
    name = "consecutive_chords"
    description = "连续6个和弦（同一声部）"
    group_size = 6
    needs_chords = True

    def match(self, notes) -> bool:
        return all(self.is_chord(el) for el in notes)


FEATURE = ConsecutiveChords
