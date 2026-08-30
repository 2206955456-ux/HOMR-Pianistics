# -*- coding: utf-8 -*-
"""报告输出：控制台摘要 + Markdown 报告 + JSON（供程序消费）。"""

import json
import time
from pathlib import Path

from scoreflow.analysis.engine import ScoreResult


def print_summary(results: list[ScoreResult]) -> None:
    for res in results:
        print(f"\n■ {res.source.name if res.source else '<memory>'}")
        for name, fres in res.feature_results.items():
            print(f"  [{fres.feature.name}] {fres.feature.description}")
            if fres.feature.describe_params():
                print(f"      参数: {fres.feature.describe_params()}")
            print(f"      命中小节: {fres.matched_measures}/{fres.total_measures}"
                  f"  占比 {fres.ratio_str}")


def write_markdown(results: list[ScoreResult], out_path: Path, source_pdf: str = "") -> Path:
    lines = [
        "# 乐谱音群特征分析报告",
        "",
        f"- 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 源文件: {source_pdf or (results[0].source.name if results else '')}",
        f"- 分析页数: {sum(r.pages for r in results)}",
        "",
    ]
    for res in results:
        lines.append(f"## {res.source.name if res.source else '<memory>'}")
        lines.append("")
        for name, fres in res.feature_results.items():
            params = fres.feature.describe_params()
            lines += [
                f"### {fres.feature.name} — {fres.feature.description}"
                + (f"（{params}）" if params else ""),
                "",
                f"- 命中小节: **{fres.matched_measures} / {fres.total_measures}**",
                f"- 占全曲比例: **{fres.ratio_str}**",
                "",
            ]
            if fres.hits:
                lines.append("| 小节 | 声部 | 命中音群 |")
                lines.append("|---:|:---|:---|")
                for h in fres.hits:
                    lines.append(f"| {h.measure_number} | {h.part_name} | {h.notes_desc} |")
                lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


def write_json(results: list[ScoreResult], out_path: Path, source_pdf: str = "") -> Path:
    data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source_pdf": source_pdf,
        "scores": [],
    }
    for res in results:
        data["scores"].append({
            "musicxml": str(res.source) if res.source else None,
            "pages": res.pages,
            "features": {
                name: {
                    "description": fres.feature.description,
                    "params": fres.feature.params,
                    "matched_measures": fres.matched_measures,
                    "total_measures": fres.total_measures,
                    "ratio": round(fres.ratio, 4),
                    "hits": [
                        {
                            "measure": h.measure_number,
                            "part": h.part_name,
                            "notes": h.notes_desc,
                        }
                        for h in fres.hits
                    ],
                }
                for name, fres in res.feature_results.items()
            },
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
