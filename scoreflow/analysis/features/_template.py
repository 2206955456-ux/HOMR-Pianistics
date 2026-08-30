# -*- coding: utf-8 -*-
"""自定义特征模板：复制本文件，改类名和逻辑，然后在 config.yaml 启用。

规则：
  - 文件里必须有一个变量 FEATURE，指向特征类的实例化结果（或类）。
  - 类名任意，但 name 必须全局唯一（config.yaml 里用 name 启用）。
"""

from music21 import note

from scoreflow.analysis.features.base import ScoreFeature


class MyFeature(ScoreFeature):
    name = "my_feature"          # 改成你的特征名
    description = "把这一行改成人类可读的特征描述"
    group_size = 2               # 相邻几个音构成一个音群

    def match(self, notes: list[note.Note]) -> bool:
        # 这里写你的判断逻辑，例如：音群中包含指定的音高
        # target = self.params.get("pitch", "C5")
        # return any(n.pitch.nameWithOctave == target for n in notes)
        return False


FEATURE = MyFeature
