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
    # 交叉手启发式重分配操作记录（未启用时为空）
    cross_hand_ops: list = field(default_factory=list)
    # 难度加权分（《音型集》口径）：
    #   总分 = Σ_特征 Σ_命中小节 (特征权重 × 双手系数)
    #   双手系数 = 2（该小节双手/两声部同时出现该技术）否则 1
    difficulty_score: float = 0.0
    # 逐特征难度明细: {feature_name: {weight, hit_measures, two_hand_measures, score}}
    difficulty_detail: dict = field(default_factory=dict)


class AnalysisEngine:
    def __init__(self, features: list[ScoreFeature], chord_mode: str = "top",
                 count_empty_measures: bool = False, across_barlines: bool = False,
                 cross_hand_heuristic: bool = False):
        self.features = features
        self.chord_mode = chord_mode
        self.count_empty_measures = count_empty_measures
        self.across_barlines = across_barlines
        # 交叉手启发式：按音域把误标到对方谱表的音符重标回实际演奏声部
        # （详见 scoreflow/analysis/cross_hand.py）
        self.cross_hand_heuristic = cross_hand_heuristic

    # ------------------------------------------------------------------
    def analyze_file(self, musicxml_path: Path) -> ScoreResult:
        if self.cross_hand_heuristic:
            text = musicxml_path.read_text(encoding="utf-8", errors="ignore")
            from scoreflow.analysis.cross_hand import reassign
            text, ops = reassign(text)
            score = converter.parseData(text)
            result = self.analyze_score(score, source=musicxml_path)
            result.cross_hand_ops = ops
            return result
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

        parts = list(score.parts)
        if not parts:
            parts = [score]
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
                # 每个特征独立收集音符流：和弦感知特征用原始流，其余用压平流
                seq_cache: dict[str, list] = {}
                for feature in self.features:
                    keep_chords = bool(getattr(feature, "needs_chords", False))
                    seq_key = "raw" if keep_chords else "flat"
                    note_seq = seq_cache.get(seq_key)
                    if note_seq is None:
                        note_seq = self._collect_notes(measure, keep_chords=keep_chords)
                        seq_cache[seq_key] = note_seq
                    if note_seq:
                        counted_measures.add(mnum)
                    if len(note_seq) < feature.group_size:
                        continue

                    for window, desc in self._slide(
                            note_seq, feature.group_size, keep_chords=keep_chords):
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

        # ---- 难度加权分（《音型集》口径）----
        # 每特征权重 weight；若某小节内双手（两个及以上不同声部）同时
        # 出现该技术，该小节该特征的加权贡献 ×2。
        difficulty_score = 0.0
        for feature in self.features:
            w = float(getattr(feature, "weight", 1.0))
            hit_measures = set()
            two_hand_measures = set()
            for m, fmap in measure_hits.items():
                hits = fmap.get(feature.name)
                if not hits:
                    continue
                hit_measures.add(m)
                parts = {h.part_name for h in hits}
                if len(parts) >= 2:   # 双手/两声部同时出现
                    two_hand_measures.add(m)
            # 单特征难度贡献 = 权重 × (单手命中小节数 + 双手命中小节数×2)
            single_hand = hit_measures - two_hand_measures
            score = w * (len(single_hand) + 2 * len(two_hand_measures))
            result.difficulty_detail[feature.name] = {
                "weight": w,
                "hit_measures": len(hit_measures),
                "two_hand_measures": len(two_hand_measures),
                "score": round(score, 2),
            }
            difficulty_score += score
        result.difficulty_score = round(difficulty_score, 2)
        return result

    # ------------------------------------------------------------------
    def _collect_notes(self, measure, keep_chords: bool = False) -> list:
        """收集小节内的音符序列。
        keep_chords=False（默认）：和弦按 chord_mode 压平，
            top=只取最高音（旋律线），skip=忽略和弦，all=展开全部和弦音；
        keep_chords=True：保留原始元素（Note 或 Chord），供和弦感知特征使用。"""
        if keep_chords:
            return list(measure.recurse().notes)
        seq: list[note.Note] = []
        for el in measure.recurse().notes:
            if isinstance(el, chord.Chord):
                if self.chord_mode == "skip":
                    continue
                if self.chord_mode == "top":
                    seq.append(_chord_top_note(el))  # 和弦最高音
                else:  # all
                    seq.extend(el.notes)
            else:
                seq.append(el)
        return seq

    def _slide(self, notes: list, group_size: int, keep_chords: bool = False):
        """滑动窗口，产出 (音群, 人类可读描述)。
        和弦元素显示为 [最高音]，如 "C4 -> [G5] -> E4 (16+17=33半音)"。"""
        for i in range(len(notes) - group_size + 1):
            window = notes[i:i + group_size]
            semis = [
                abs(_el_midi(window[k + 1]) - _el_midi(window[k]))
                for k in range(group_size - 1)
            ]
            arrow = " -> ".join(_el_name(n) for n in window)
            desc = arrow if not semis else (
                f"{arrow} ({'+'.join(map(str, semis))}={sum(semis)}半音)"
            )
            yield window, desc


def _chord_top_note(el: chord.Chord) -> note.Note:
    """取和弦中音高最高的音符（按 MIDI 编号）。"""
    return max(el.notes, key=lambda n: n.pitch.midi)


def _el_midi(el) -> int:
    """元素的中音区编号；和弦取最高音。"""
    if isinstance(el, chord.Chord):
        return _chord_top_note(el).pitch.midi
    return el.pitch.midi


def _el_name(el) -> str:
    """元素名称；和弦显示为 [最高音]。"""
    if isinstance(el, chord.Chord):
        return f"[{_chord_top_note(el).pitch.nameWithOctave}]"
    return el.pitch.nameWithOctave
