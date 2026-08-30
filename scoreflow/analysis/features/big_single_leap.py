# -*- coding: utf-8 -*-
"""示例特征 2（默认关闭，config.yaml 中可启用）：

小节内相邻 2 个音之间存在单个大跳（音程 >= 阈值半音，默认 8 = 小六度）。
"""

from music21 import note

from scoreflow.analysis.features.base import ScoreFeature


class BigSingleLeap(ScoreFeature):
    name = "big_single_leap"
    description = "相邻2音之间存在单个大跳（音程>=阈值半音，默认8=小六度）"
    group_size = 2

    def match(self, notes: list[note.Note]) -> bool:
        threshold = int(self.params.get("threshold", 8))
        return self.semitones(notes[0], notes[1]) >= threshold


FEATURE = BigSingleLeap
