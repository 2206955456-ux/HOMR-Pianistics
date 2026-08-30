# -*- coding: utf-8 -*-
"""分析引擎：加载 MusicXML -> 逐小节滑动窗口 -> 应用音群特征 -> 统计。

统计口径：
  - 以"小节"为单位：某小节内任一音群命中特征，则该小节计为命中；
  - 多声部（如钢琴上下谱表）：任一声部命中即该小节命中；
  - 多页乐谱：逐页分析后汇总（命中小节数之和 / 总小节数之和）；
  - 分母默认只统计含音符的小节（count_empty_measures 可改为含空小节）。
"""

from dataclasses import dataclass, field
from pathlib import Path

from music21 import chord, converter, note

from scoreflow.analysis.features import ScoreFeature


@dataclass
class MeasureHit:
    measure_number: int
    part_name: str
    notes_desc: str      # 命中音群，如 "C4 -> E5 -> G4 (16+3=19半音)"


@dataclass
class FeatureResult:
    feature: ScoreFeature
    total_measures: int = 0
    matched_measures: int = 0
    hits: list[MeasureHit] = field(default_factory=list)

    @property
    def ratio(self) -> float:
        return self.matched_measures / self.total_measures if self.total_measures else 0.0

    @property
    def ratio_str(self) -> str:
        return f"{self.ratio:.1%}" if self.total_measures else "N/A"


@dataclass
class ScoreResult:
    source: Path
    pages: int = 0
    feature_results: dict[str, FeatureResult] = field(default_factory=dict)


class AnalysisEngine:
    def __init__(self, features: list[ScoreFeature], chord_mode: str = "top",
                 count_empty_measures: bool = False, across_barlines: bool = False):
        self.features = features
        self.chord_mode = chord_mode
        self.count_empty_measures = count_empty_measures
        self.across_barlines = across_barlines

    # ------------------------------------------------------------------
    def analyze_file(self, musicxml_path: Path) -> ScoreResult:
        score = converter.parse(str(musicxml_path))
        return self.analyze_score(score, source=musicxml_path)

    def analyze_score(self, score, source: Path | None = None) -> ScoreResult:
        result = ScoreResult(source=source or Path("<memory>"))
        result.feature_results = {
            f.name: FeatureResult(feature=f) for f in self.features
        }
        result.pages = 1
        if not self.features:
            return result
        min_group = min(f.group_size for f in self.features)

        parts = score.parts if score.parts else [score]
        # measure_number -> {feature_name: [MeasureHit]}
        measure_hits: dict[int, dict[str, list[MeasureHit]]] = {}
        # 含音符的小节号集合（默认作为分母）
        counted_measures: set[int] = set()
        all_measure_numbers: set[int] = set()

        for part_idx, part in enumerate(parts, 1):
            part_name = part.partName or "Part"
            if len(parts) > 1:
                part_name = f"{part_name}#{part_idx}"
            for measure in part.getElementsByClass("Measure"):
                mnum = int(measure.number)
                all_measure_numbers.add(mnum)
                note_seq = self._collect_notes(measure)
                if note_seq:
                    counted_measures.add(mnum)
                if len(note_seq) < min_group:
                    continue

                for feature in self.features:
                    for window, desc in self._slide(note_seq, feature.group_size):
                        if feature.match(window):
                            hit = MeasureHit(
                                measure_number=mnum,
                                part_name=part_name,
                                notes_desc=desc,
                            )
                            measure_hits.setdefault(mnum, {}).setdefault(
                                feature.name, []).append(hit)

        denominator_pool = (
            all_measure_numbers if self.count_empty_measures else counted_measures
        )
        for name, fres in result.feature_results.items():
            fres.total_measures = len(denominator_pool)
            matched = {m for m, fmap in measure_hits.items() if name in fmap}
            fres.matched_measures = len(matched)
            for m in sorted(matched):
                fres.hits.extend(measure_hits[m][name])
        return result

    # ------------------------------------------------------------------
    def _collect_notes(self, measure) -> list[note.Note]:
        """收集小节内的音符序列。和弦按 chord_mode 处理：
        top=只取最高音（旋律线），skip=忽略和弦，all=展开全部和弦音。"""
        seq: list[note.Note] = []
        for el in measure.recurse().notes:
            if isinstance(el, chord.Chord):
                if self.chord_mode == "skip":
                    continue
                if self.chord_mode == "top":
                    seq.append(el.notes[-1])  # 和弦最高音
                else:  # all
                    seq.extend(el.notes)
            else:
                seq.append(el)
        return seq

    def _slide(self, notes: list[note.Note], group_size: int):
        """滑动窗口，产出 (音群, 人类可读描述)，如 "C4 -> E5 -> G4 (16+3=19半音)"。"""
        for i in range(len(notes) - group_size + 1):
            window = notes[i:i + group_size]
            semis = [
                abs(window[k + 1].pitch.midi - window[k].pitch.midi)
                for k in range(group_size - 1)
            ]
            arrow = " -> ".join(n.pitch.nameWithOctave for n in window)
            desc = arrow if not semis else (
                f"{arrow} ({'+'.join(map(str, semis))}={sum(semis)}半音)"
            )
            yield window, desc
