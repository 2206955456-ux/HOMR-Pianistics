# -*- coding: utf-8 -*-
"""特征：同一声部内连续 3 个和弦（《音型集》口径：3 音及以上叠置）。

窗口内 3 个元素全部是和弦（Chord）且每个和弦音数 ≥ min_notes 即命中。
需在基类声明 needs_chords=True，引擎会保留原始元素（含和弦类型）传给 match。

参数：
    window_size: 连续和弦个数，默认 3（《音型集》口径；早期版本为 6，
                 可通过 window_size=6 恢复旧行为）。
    min_notes:   和弦最少音数，默认 3（3 音及以上叠置；设为 1 则任意和弦
                 都算，等价于旧"连续和弦"口径）。
"""

from scoreflow.analysis.features.base import ScoreFeature


class ConsecutiveChords(ScoreFeature):
    name = "consecutive_chords"
    description = "连续3个和弦（同一声部，3音及以上叠置）"
    group_size = 3
    needs_chords = True
    weight = 2.0   # 《音型集》连续和弦支撑难度加权

    def __init__(self, params: dict | None = None):
        super().__init__(params)
        self.group_size = int(self.params.get("window_size", 3))
        self.min_notes = int(self.params.get("min_notes", 3))

    def match(self, notes) -> bool:
        return all(
            self.is_chord(el) and len(el.notes) >= self.min_notes
            for el in notes
        )


FEATURE = ConsecutiveChords
