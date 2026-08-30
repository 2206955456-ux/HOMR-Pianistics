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
from scoreflow.analysis.features.wide_leap_sum import WideLeapSum


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


def test_feature_discovery_and_config():
    assert "wide_leap_sum" in all_features()
    assert "big_single_leap" in all_features()
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
