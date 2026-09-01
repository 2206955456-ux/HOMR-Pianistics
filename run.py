#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scoreflow —— 乐谱 PDF -> MusicXML(HOMR) -> 音群特征分析 一站式命令行工作流

用法：
    python run.py                        # 处理 input 目录下所有 PDF（全流程）
    python run.py 某乐谱.pdf              # 处理单个 PDF
    python run.py --skip-omr             # 跳过识别，直接分析已有 MusicXML
    python run.py --list-features        # 列出全部可用音群特征
    python run.py --config my.yaml       # 使用自定义配置
    python run.py --set analysis.features.wide_leap_sum.params.threshold=16
                                         # 临时覆盖某个配置项（不改文件）

流程： PDF --pypdfium2--> 每页PNG --HOMR--> 每页MusicXML --music21--> 特征分析报告
"""

import argparse
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")  # 屏蔽依赖库的版本警告噪音

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scoreflow import __version__
from scoreflow.analysis.engine import AnalysisEngine
from scoreflow.analysis.features import all_features, build_features
from scoreflow.config import ConfigError, load_config
from scoreflow.homr_ocr import recognize_pages
from scoreflow.pdf_render import render_pdf
from scoreflow.reporting import print_summary, write_excel, write_json, write_markdown


def parse_override(kv: str) -> dict:
    """把 a.b.c=value 解析成嵌套 dict（value 自动转 int/float/bool）。"""
    keys, _, raw = kv.partition("=")
    value: object = raw
    if raw.lower() in ("true", "false"):
        value = raw.lower() == "true"
    else:
        try:
            value = int(raw)
        except ValueError:
            try:
                value = float(raw)
            except ValueError:
                pass
    node: dict = {}
    root = node
    parts = keys.strip(".").split(".")
    for k in parts[:-1]:
        node[k] = {}
        node = node[k]
    node[parts[-1]] = value
    return root


def collect_pdfs(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    if target.is_dir():
        return sorted(target.glob("*.pdf"))
    return []


def run_pipeline(args) -> int:
    overrides = {}
    for kv in (args.set or []):
        overrides = _merge(overrides, parse_override(kv))
    if args.dpi:
        overrides.setdefault("pipeline", {})["dpi"] = args.dpi
    if args.gpu:
        overrides.setdefault("pipeline", {})["gpu"] = args.gpu

    try:
        cfg = load_config(args.config, overrides)
        cfg.require_input()
    except ConfigError as e:
        print(f"✗ 配置错误: {e}")
        return 1

    # XML 数据根目录固定用 config.yaml 的 output_dir；-o 只影响报告输出位置
    xml_root = cfg.output_dir
    if args.output:
        cfg.output_dir = Path(args.output)
    if args.cross_hand_heuristic:
        cfg.cross_hand_heuristic = True
    if args.hand_split_threshold is not None:
        cfg.hand_split_threshold = args.hand_split_threshold if args.hand_split_threshold > 0 else None

    input_target = Path(args.input).expanduser().resolve() if args.input else cfg.input_dir
    pdfs = collect_pdfs(input_target)
    if not pdfs and not args.skip_omr:
        print(f"✗ 未找到 PDF: {input_target}")
        return 1

    print("=" * 62)
    print(f"scoreflow v{__version__} —— 乐谱识别与音群特征分析")
    print("=" * 62)
    print(f"输入: {input_target}")
    print(f"输出: {cfg.output_dir}")
    print(f"识别: HOMR (gpu={cfg.gpu}, dpi={cfg.dpi})")

    engine = AnalysisEngine(
        features=build_features(cfg.features),
        chord_mode=cfg.chord_mode,
        count_empty_measures=cfg.count_empty_measures,
        across_barlines=cfg.across_barlines,
        cross_hand_heuristic=cfg.cross_hand_heuristic,
        hand_split_threshold=cfg.hand_split_threshold,
    )
    if not engine.features:
        print("✗ 未启用任何分析特征，请检查 config.yaml 的 analysis.features")
        return 1

    from scoreflow.analysis.engine import ScoreResult
    all_results: list[ScoreResult] = []
    reports_dir = cfg.output_dir / "reports"
    exit_code = 0

    # -------- 每份 PDF 一条流水线 --------
    work_items = pdfs if pdfs else [None]  # skip-omr 模式下用已有 XML
    for pdf in work_items:
        if pdf is not None:
            print("\n" + "-" * 62)
            print(f"▶ {pdf.name}")
            stem_dir = xml_root / pdf.stem
            pages_dir = stem_dir / "pages"
            xml_files: list[Path] = []

            if args.skip_omr:
                xml_files = sorted(pages_dir.glob("page_*.musicxml"))
                print(f"  跳过识别，复用 {len(xml_files)} 个已有 MusicXML")
            else:
                print(f"  [1/3] 渲染 PDF (dpi={cfg.dpi}) ...")
                try:
                    images = render_pdf(pdf, pages_dir, cfg.dpi)
                except Exception as e:
                    print(f"  ✗ 渲染失败: {e}")
                    exit_code = 2
                    continue
                print(f"  ✓ {len(images)} 页")

                print("  [2/3] HOMR 识别 ...")
                xml_files = recognize_pages(
                    cfg.homr_python, cfg.homr_dir, images,
                    gpu=cfg.gpu, timeout=cfg.timeout)
                if not xml_files:
                    print("  ✗ 所有页面识别失败")
                    exit_code = 2
                    continue
                print(f"  ✓ 成功 {len(xml_files)}/{len(images)} 页")

            print("  [3/3] 音群特征分析 ...")
            source_pdf = str(pdf)
        else:
            # 无 PDF（--skip-omr 且未指定输入）：直接扫输出目录下所有 musicxml
            print("\n▶ 扫描已有 MusicXML ...")
            xml_files = sorted(xml_root.rglob("page_*.musicxml"))
            if not xml_files:
                print("✗ 输出目录中没有 MusicXML")
                return 1
            source_pdf = ""

        try:
            results = [engine.analyze_file(x) for x in xml_files]
        except Exception as e:
            print(f"  ✗ 分析失败: {e}")
            exit_code = 2
            continue

        if not results:
            print("  ✗ 没有可分析的 MusicXML："
                  "这份谱子还没识别过，请先不带 --skip-omr 跑一次完整流程")
            exit_code = 2
            continue

        # 多页结果合并为一份（小节数、命中小节数累加）
        merged = _merge_results(results, source_pdf, xml_files)
        all_results.append(merged)
        print(f"  ✓ 分析完成: {merged.pages} 页 / "
              f"{merged.feature_results[engine.features[0].name].total_measures} 小节")

    if not all_results:
        return exit_code or 1

    # -------- 汇总输出 --------
    print_summary(all_results)
    md = write_markdown(all_results, reports_dir / "report.md",
                        source_pdf=all_results[0].source.name)
    js = write_json(all_results, reports_dir / "report.json",
                    source_pdf=str(input_target))
    xlsx = write_excel(all_results, reports_dir / "report.xlsx",
                       source_pdf=str(input_target))
    print(f"\n报告已生成:\n  - {md}\n  - {js}\n  - {xlsx}")
    return exit_code


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _merge_results(results, source_pdf: str, xml_files: list[Path]):
    """把多页的 ScoreResult 合并成一份（特征小节数相加）。"""
    from scoreflow.analysis.engine import ScoreResult
    merged = ScoreResult(source=Path(source_pdf) if source_pdf else xml_files[0],
                         pages=len(results))
    for name in results[0].feature_results:
        total = sum(r.feature_results[name].total_measures for r in results)
        matched = sum(r.feature_results[name].matched_measures for r in results)
        hits = []
        offset = 0
        for r in results:
            fres = r.feature_results[name]
            for h in fres.hits:
                hits.append(h)
            offset += 0
        merged.feature_results[name] = type(results[0].feature_results[name])(
            feature=results[0].feature_results[name].feature,
            total_measures=total,
            matched_measures=matched,
            hits=hits,
        )
    # 难度加权：各页独立计算后求和（页内小节号唯一，跨页不冲突）
    merged.difficulty_score = round(sum(r.difficulty_score for r in results), 2)
    for name in results[0].feature_results:
        agg = {"weight": 0.0, "hit_measures": 0, "two_hand_measures": 0, "score": 0.0}
        for r in results:
            rd = r.difficulty_detail.get(name)
            if not rd:
                continue
            agg["weight"] = rd["weight"]
            agg["hit_measures"] += rd["hit_measures"]
            agg["two_hand_measures"] += rd["two_hand_measures"]
            agg["score"] += rd["score"]
        merged.difficulty_detail[name] = agg
    return merged


def list_features() -> None:
    print("可用音群特征（在 config.yaml 的 analysis.features 中启用）：\n")
    for name, cls in sorted(all_features().items()):
        print(f"  {name:20s} 窗口={cls.group_size}音  {cls.description}")
    print("\n自定义特征：复制 scoreflow/analysis/features/_template.py 修改即可，")
    print("详见 README「编写自己的音群特征」一节。")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="scoreflow",
        description="乐谱 PDF -> MusicXML(HOMR) -> 音群特征分析 一站式工作流",
    )
    parser.add_argument("input", nargs="?", help="PDF 文件或目录（默认用 config.yaml 的 input_dir）")
    parser.add_argument("-o", "--output", help="输出目录")
    parser.add_argument("--config", help="配置文件路径（默认 config.yaml）")
    parser.add_argument("--skip-omr", action="store_true",
                        help="跳过识别，直接分析输出目录中已有的 MusicXML")
    parser.add_argument("--dpi", type=int, help="PDF 渲染 DPI")
    parser.add_argument("--gpu", choices=("auto", "no", "force"), help="GPU 模式")
    parser.add_argument("--set", action="append", metavar="KEY=VALUE",
                        help="临时覆盖配置项，如 --set analysis.features.wide_leap_sum.params.threshold=16")
    parser.add_argument("--cross-hand-heuristic", action="store_true",
                        help="启用交叉手启发式声部重分配（按音域把误标到对方谱表的音符重标回实际演奏声部）")
    parser.add_argument("--hand-split-threshold", type=int, metavar="N",
                        help="启用双手拆分诊断，合并后声部跨度 >= N 半音时拆成右手/左手轨道（默认读取 config.yaml）")
    parser.add_argument("--list-features", action="store_true", help="列出可用音群特征")
    parser.add_argument("--version", action="version", version=f"scoreflow {__version__}")
    args = parser.parse_args()

    if args.list_features:
        list_features()
        return 0
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
