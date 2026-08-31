# -*- coding: utf-8 -*-
"""交叉手启发式重分配实验：对比「按谱表分组」vs「启发式重分配」的特征统计。

启发式规则（模拟符干朝向判断的近似）：
  - staff 2 上音高 > C5(midi 72)：左手跑到高音区（符干朝上的交叉音符）→ 重标为右手 voice1/staff1
  - staff 1 上音高 < C3(midi 48)：右手跑到低音区（符干朝下的交叉音符）→ 重标为左手 voice5/staff2
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, r"D:\HOMR\homr-score-analyzer")

from music21 import converter
from scoreflow.analysis.engine import AnalysisEngine
from scoreflow.analysis.features import build_features
from scoreflow.config import load_config

SEMIS = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
C5 = 72   # staff2 上的高音阈值
C3 = 48   # staff1 上的低音阈值


def note_midi(note_xml: str):
    step = re.search(r"<step>([A-G])</step>", note_xml)
    octave = re.search(r"<octave>(\d+)</octave>", note_xml)
    alter = re.search(r"<alter>(-?\d+)</alter>", note_xml)
    if not step or not octave:
        return None
    return (int(octave.group(1)) + 1) * 12 + SEMIS[step.group(1)] + (int(alter.group(1)) if alter else 0)


def reassign(xml_text: str, verbose=False) -> tuple[str, list]:
    """返回 (重分配后的 XML 文本, 重分配操作列表)。"""
    ops = []

    def repl(m):
        n = m.group(0)
        midi = note_midi(n)
        if midi is None:
            return n
        staff = re.search(r"<staff>(\d)</staff>", n)
        voice = re.search(r"<voice>(\d+)</voice>", n)
        if not staff:
            return n
        s = staff.group(1)
        v = voice.group(1) if voice else "1"
        step = re.search(r"<step>([A-G])</step>", n)
        octave = re.search(r"<octave>(\d+)</octave>", n)
        name = f"{step.group(1)}{octave.group(1)}" if step and octave else "?"
        if s == "2" and midi > C5 and v.startswith("5"):
            ops.append(("LH->RH", name, midi))
            n = re.sub(r"<voice>\d+</voice>", "<voice>1</voice>", n, count=1)
            n = n.replace("<staff>2</staff>", "<staff>1</staff>")
        elif s == "1" and midi < C3 and v in ("1", "2"):
            ops.append(("RH->LH", name, midi))
            n = re.sub(r"<voice>\d+</voice>", "<voice>5</voice>", n, count=1)
            n = n.replace("<staff>1</staff>", "<staff>2</staff>")
        return n

    out = re.sub(r"<note>.*?</note>", repl, xml_text, flags=re.S)
    return out, ops


def run_engine(xml_text: str, cfg):
    """把 XML 文本解析成 score，用引擎分析，返回 (特征名 -> 各声部命中统计)。"""
    import io
    score = converter.parseData(xml_text)
    engine = AnalysisEngine(
        build_features(cfg.features), cfg.chord_mode,
        cfg.count_empty_measures, cfg.across_barlines,
    )
    result = engine.analyze_score(score)
    stats = {}
    for fname, fres in result.feature_results.items():
        by_part = defaultdict(list)
        for h in fres.hits:
            by_part[h.part_name].append((h.measure_number, h.notes_desc))
        stats[fname] = {
            "total": fres.total_measures,
            "matched": fres.matched_measures,
            "ratio": f"{fres.ratio:.1%}",
            "parts": {k: len(v) for k, v in sorted(by_part.items())},
        }
    return stats


def main():
    cfg = load_config(None, {})
    pages = sorted(Path(r"D:\HOMR\output\etude7\pages").glob("*.musicxml"))
    total_ops = defaultdict(int)
    for xml in pages:
        text = open(xml, encoding="utf-8").read()
        new_text, ops = reassign(text)
        for kind, name, midi in ops:
            total_ops[kind] += 1
            print(f"  重分配: {kind} {name} (midi {midi}) @ {xml.name}")

    print(f"\n===== 重分配操作汇总：共 {sum(total_ops.values())} 个音符被重分配 {dict(total_ops)} =====")
    print(f"\n{'特征':<28}{'按谱表分组(现状)':<34}{'启发式重分配'}")
    print("-" * 100)
    for xml in pages:
        text = open(xml, encoding="utf-8").read()
        new_text, _ = reassign(text)
        orig = run_engine(text, cfg)
        new = run_engine(new_text, cfg)
        print(f"\n--- {xml.name} ---")
        for fname in orig:
            o, n = orig[fname], new[fname]
            print(f"  {fname:<24} 命中 {o['matched']}/{o['total']} ({o['ratio']}) 声部{o['parts']}")
            print(f"  {'':<24} 重分配后 命中 {n['matched']}/{n['total']} ({n['ratio']}) 声部{n['parts']}")


if __name__ == "__main__":
    main()
