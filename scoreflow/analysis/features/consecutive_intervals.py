# -*- coding: utf-8 -*-
"""特征：连续音程（2 音叠置）支撑（《音型集》口径）。

单一声部内出现连续 3 个音程（2 音叠置的和弦）即命中。
需在基类声明 needs_chords=True，引擎会保留原始元素（含和弦类型）传给 match。

参数：
    window_size: 连续音程个数，默认 3。
    exact:       是否严格要求 2 音叠置（默认 true）；设为 false 时
                 2 音及以上叠置都算（与连续和弦特征区分）。
"""

from scoreflow.analysis.features.base import ScoreFeature


class ConsecutiveIntervals(ScoreFeature):
    name = "consecutive_intervals"
    description = "连续3个音程（同一声部，2音叠置）"
    group_size = 3
    needs_chords = True
    weight = 1.0   # 《音型集》连续音程支撑难度加权

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.group_size = int(self.params.get("window_size", 3))
        self.exact = bool(self.params.get("exact", True))

    def match(self, notes) -> bool:
        for el in notes:
            if not self.is_chord(el):
                return False
            n_notes = len(el.notes)
            if self.exact and n_notes != 2:
                return False
            if not self.exact and n_notes < 2:
                return False
        return True


FEATURE = ConsecutiveIntervals
