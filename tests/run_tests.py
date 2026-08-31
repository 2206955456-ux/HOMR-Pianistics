# -*- coding: utf-8 -*-
"""音群特征引擎单元测试（不依赖 OMR，纯 music21 内存构造）。

运行: python tests/run_tests.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from music21 import chord, meter, note, stream

from scoreflow.analysis.engine import AnalysisEngine
from scoreflow.analysis.features import all_features, build_features
from scoreflow.analysis.features.big_single_leap import BigSingleLeap
from scoreflow.analysis.features.consecutive_chords import ConsecutiveChords
from scoreflow.analysis.features.consecutive_sixteenths import ConsecutiveSixteenths
from scoreflow.analysis.features.wide_leap_sum import WideLeapSum, is_arpeggio


def make_score(measures_notes: list[list[str]]) -> stream.Score:
    """构造乐谱：每小节一组音名（如 'C4'），单声部，4/4。"""
    sc = stream.Score()
    part = stream.Part()
    for i, names in enumerate(measures_notes, 1):
        m = stream.Measure(number=i)
        m.append(meter.TimeSignature("4/4"))
        for name in names:
            m.append(note.Note(name))
        part.append(m)
    sc.append(part)
    return sc


def test_wide_leap_sum():
    f = WideLeapSum({"threshold": 12})
    # C4->E5 (16半音) ->G4 (3半音)，和 19 > 12，命中
    assert f.match([note.Note("C4"), note.Note("E5"), note.Note("G4")])
    # C4->E4->G4，各 4 半音，和 8，不命中
    assert not f.match([note.Note("C4"), note.Note("E4"), note.Note("G4")])
    # 恰好等于 12 不命中（要求"大于"）
    assert not f.match([note.Note("C4"), note.Note("A4"), note.Note("C5")])


def test_is_arpeggio():
    # 三和弦琶音：任意八度、任意次序、允许重复音
    assert is_arpeggio([note.Note("C4"), note.Note("E5"), note.Note("G4")])    # C 大三
    assert is_arpeggio([note.Note("A-2"), note.Note("D-2"), note.Note("A-2")])  # {A♭,D♭} ⊆ D♭ 大三
    assert is_arpeggio([note.Note("D2"), note.Note("A2"), note.Note("F3")])    # D 小三
    # 七和弦琶音：属七 G-B-D-F 的子集
    assert is_arpeggio([note.Note("G2"), note.Note("B2"), note.Note("F3")])
    # 减三和弦琶音
    assert is_arpeggio([note.Note("B3"), note.Note("D4"), note.Note("F4")])
    # 非琶音：和弦外音 / 无和弦归属
    assert not is_arpeggio([note.Note("E2"), note.Note("B2"), note.Note("A3")])  # A 非和弦音
    assert not is_arpeggio([note.Note("C4"), note.Note("C#4"), note.Note("D4")])  # 连续半音


def test_wide_leap_arpeggio_aware():
    f_off = WideLeapSum({"threshold": 12})
    f_on = WideLeapSum({"threshold": 12, "arpeggio_aware": True})
    # 琶音音群（16+3=19 > 12，音级 {C,E,G} ⊆ C 大三和弦）：开关后豁免
    arp = [note.Note("C4"), note.Note("E5"), note.Note("G4")]
    assert f_off.match(arp)
    assert not f_on.match(arp)
    # 非琶音宽跳（7+10=17，音级 {E,B,A} 无和弦归属）：两版都命中
    leap = [note.Note("E2"), note.Note("B2"), note.Note("A3")]
    assert f_off.match(leap)
    assert f_on.match(leap)
    # 阈值以下不受开关影响
    assert not f_on.match([note.Note("C4"), note.Note("E4"), note.Note("G4")])


def test_engine_arpeggio_aware():
    # 一小节纯琶音跑动 C4-G4-E5-C5：C4->G4->E5 和 15>12 命中（音级 {C,G,E} 为琶音）
    sc = make_score([["C4", "G4", "E5", "C5"]])
    eng_off = AnalysisEngine([WideLeapSum({"threshold": 12})], chord_mode="top")
    eng_on = AnalysisEngine(
        [WideLeapSum({"threshold": 12, "arpeggio_aware": True})], chord_mode="top")
    assert eng_off.analyze_score(sc).feature_results["wide_leap_sum"].matched_measures == 1
    assert eng_on.analyze_score(sc).feature_results["wide_leap_sum"].matched_measures == 0


def test_engine_ratio():
    features = [WideLeapSum({"threshold": 12})]
    engine = AnalysisEngine(features, chord_mode="top")
    # 3 个小节：第 1 小节有大跳音群，后 2 小节平稳
    sc = make_score([
        ["C4", "E5", "G4", "C5"],   # 命中：16+3=19
        ["C4", "E4", "G4", "C5"],   # 平稳
        ["D4", "F4", "A4", "D5"],   # 平稳
    ])
    res = engine.analyze_score(sc)
    fr = res.feature_results["wide_leap_sum"]
    assert fr.total_measures == 3, fr.total_measures
    assert fr.matched_measures == 1, fr.matched_measures
    assert abs(fr.ratio - 1 / 3) < 1e-9


def test_engine_empty_measures():
    features = [WideLeapSum({"threshold": 12})]
    engine = AnalysisEngine(features)
    sc = make_score([["C4", "E5", "G4", "C5"], []])  # 第 2 小节空
    res = engine.analyze_score(sc)
    assert res.feature_results["wide_leap_sum"].total_measures == 1  # 默认排除空小节

    engine2 = AnalysisEngine(features, count_empty_measures=True)
    res2 = engine2.analyze_score(sc)
    assert res2.feature_results["wide_leap_sum"].total_measures == 2


def test_chord_top_mode():
    features = [WideLeapSum({"threshold": 12})]
    engine = AnalysisEngine(features, chord_mode="top")
    sc = stream.Score()
    part = stream.Part()
    m = stream.Measure(number=1)
    m.append(meter.TimeSignature("4/4"))
    m.append(note.Note("C4"))
    m.append(chord.Chord(["E4", "G4", "C6"]))  # top 模式取 C6
    m.append(note.Note("D5"))
    part.append(m)
    sc.append(part)
    # C4->C6 = 22, C6->D5 = 10，和 32 > 12 命中
    res = engine.analyze_score(sc)
    assert res.feature_results["wide_leap_sum"].matched_measures == 1


def test_consecutive_sixteenths():
    f = ConsecutiveSixteenths()
    sixteenths = [note.Note("C4", type="16th") for _ in range(6)]
    assert f.match(sixteenths)
    # 5 个十六分 + 1 个八分，不算连续 6 个十六分
    mixed = sixteenths[:5] + [note.Note("C4", type="eighth")]
    assert not f.match(mixed)

    # 引擎集成：一小节 6 个十六分音符 -> 命中
    features = [ConsecutiveSixteenths()]
    engine = AnalysisEngine(features)
    sc = stream.Score()
    part = stream.Part()
    m = stream.Measure(number=1)
    m.append(meter.TimeSignature("4/4"))
    for _ in range(6):
        m.append(note.Note("G4", type="16th"))
    part.append(m)
    sc.append(part)
    res = engine.analyze_score(sc)
    assert res.feature_results["consecutive_sixteenths"].matched_measures == 1


def test_consecutive_chords():
    f = ConsecutiveChords()
    chords = [chord.Chord(["C4", "E4", "G4"]) for _ in range(6)]
    assert f.match(chords)
    # 5 个和弦 + 1 个单音，不算连续 6 和弦
    assert not f.match(chords[:5] + [note.Note("C4")])

    # 引擎集成：6 个和弦的小节 -> 命中（chord_mode=top 不影响本特征）
    features = [ConsecutiveChords()]
    engine = AnalysisEngine(features, chord_mode="top")
    sc = stream.Score()
    part = stream.Part()
    m = stream.Measure(number=1)
    m.append(meter.TimeSignature("4/4"))
    for _ in range(6):
        m.append(chord.Chord(["C4", "E4", "G4"]))
    part.append(m)
    sc.append(part)
    res = engine.analyze_score(sc)
    assert res.feature_results["consecutive_chords"].matched_measures == 1


def test_feature_discovery_and_config():
    assert "wide_leap_sum" in all_features()
    assert "big_single_leap" in all_features()
    assert "consecutive_sixteenths" in all_features()
    assert "consecutive_chords" in all_features()
    cfg = {
        "wide_leap_sum": {"enabled": True, "params": {"threshold": 16}},
        "big_single_leap": {"enabled": False},
    }
    feats = build_features(cfg)
    assert len(feats) == 1
    assert isinstance(feats[0], WideLeapSum)
    assert feats[0].params["threshold"] == 16

    feats2 = build_features({
        "big_single_leap": {"enabled": True, "params": {"threshold": 8}}
    })
    assert isinstance(feats2[0], BigSingleLeap)


def test_unknown_feature_raises():
    try:
        build_features({"no_such_feature": {"enabled": True}})
        assert False, "应当抛出 KeyError"
    except KeyError:
        pass


def main() -> int:
    tests = [(k, v) for k, v in globals().items() if k.startswith("test_")]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {name}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {name}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} 通过")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
