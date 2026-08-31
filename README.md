# scoreflow —— 乐谱识别与音群特征分析工作流

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**PDF 乐谱 → MusicXML（HOMR 光学识别）→ 音群特征分析（music21）→ Markdown/JSON/Excel 报告**

一条命令完成全流程。分析特征完全可插拔：想统计什么样的"音群"，写一个小类即可，
不改引擎代码。

```
┌─────────┐   pypdfium2   ┌──────────┐    HOMR     ┌───────────┐   music21   ┌────────┐
│ 乐谱PDF  │ ───────────▶ │ 每页PNG   │ ──────────▶ │ MusicXML  │ ─────────▶ │ 特征报告 │
└─────────┘               └──────────┘  (光学识别)  └───────────┘  (滑动窗口)  └────────┘
```

## 内置示例特征

| 特征 | 说明 |
|:---|:---|
| `wide_leap_sum` | 小节内相邻 3 个音，前后 2 个音程之和超过阈值（默认 12 半音 = 八度），统计命中小节占全曲比例 |
| `big_single_leap` | 小节内相邻 2 个音存在单个大跳（默认 ≥ 8 半音 = 小六度） |
| `consecutive_sixteenths` | 小节内出现连续 6 个十六分音符（同一声部） |
| `consecutive_chords` | 小节内同一声部出现连续 6 个和弦 |

## 环境准备

本工作流依赖 [HOMR](https://github.com/liebharc/homr) 作为识别引擎。两种方式任选：

**方式 A：HOMR Windows 发行版（推荐，零配置）**

1. 获取自带 `python_embed` 的 HOMR 发行版并解压（如 `D:\HOMR\homr-main`）；
2. 确认其中存在 `python_embed\python.exe` 与 `homr\` 目录（模型权重随包附带）；
3. 在嵌入式环境中补装本项目依赖：

   ```bash
   python_embed\python.exe -m pip install pypdfium2 PyYAML
   # music21 发行版已内置；若没有则一并安装：
   python_embed\python.exe -m pip install music21
   ```

4. 修改 `config.yaml` 中 `paths.homr_python` 与 `paths.homr_dir` 指向你的解压位置。

**方式 B：源码安装 homr**

```bash
# 按 homr 官方文档安装（Python 3.11 + Poetry），然后：
pip install -r requirements.txt
```

并把 `config.yaml` 的 `homr_python` 指向该环境的 Python，`homr_dir` 指向 homr 仓库根目录
（模型权重 `homr/segmentation/*.onnx`、`homr/transformer/*.onnx` 相对它解析）。

## 快速开始

```bash
# 1. 把乐谱 PDF 放进 input 目录（config.yaml 可改路径），然后：
python run.py                      # 全流程：识别 + 分析

# 2. 或者直接指定单个 PDF / 任意目录：
python run.py path/to/score.pdf
python run.py path/to/pdf_dir/

# 3. 已识别过、只想重新分析（比如改了特征参数）：
python run.py --skip-omr

# 4. 临时改参数试效果（不改动配置文件）：
python run.py --set analysis.features.wide_leap_sum.params.threshold=16

# 5. 查看所有可用特征：
python run.py --list-features

# 6. 启用交叉手启发式声部重分配（见下方「交叉手问题」）：
python run.py --cross-hand-heuristic
```

产物（默认在 `output/` 下）：

```
output/
├── <乐谱名>/
│   └── pages/
│       ├── page_001.png          # 渲染出的页面图片
│       ├── page_001.musicxml     # HOMR 识别结果（每页一份）
│       └── page_002.musicxml
└── reports/
    ├── report.md                 # 人类可读报告（含命中小节明细表）
    ├── report.json               # 程序可读（便于二次处理/批量汇总）
    └── report.xlsx               # Excel 报告：总览表 + 每特征一张明细表
```

## 编写自己的音群特征（核心玩法）

特征 = 一个 Python 小类。**复制模板，改三处，启用即可：**

1. 复制 `scoreflow/analysis/features/_template.py` 为新文件，如 `my_feature.py`：

```python
from music21 import note
from scoreflow.analysis.features.base import ScoreFeature

class MyFeature(ScoreFeature):
    name = "my_feature"                    # ① 唯一标识
    description = "小节内出现指定音高"        # ② 报告里的描述
    group_size = 2                         # ③ 相邻几个音构成一个"音群"（滑动窗口大小）

    def match(self, notes: list[note.Note]) -> bool:
        # notes 是相邻 group_size 个音符，返回 True 即命中
        target = self.params.get("pitch", "C5")
        return any(n.pitch.nameWithOctave == target for n in notes)

FEATURE = MyFeature
```

2. 在 `config.yaml` 中启用并传参：

```yaml
analysis:
  features:
    my_feature:
      enabled: true
      params: {pitch: C5}
```

3. 重新运行：`python run.py --skip-omr`（识别结果已缓存，秒级出新报告）。

**引擎能力速查：**

- `match()` 内可直接用 `self.semitones(n1, n2)` 取两音半音距离；
- 参数全部来自 `params`，改配置不用改代码；
- `group_size` 可以是 2（两音音程）、3（两音程相加）、5（四个音程）等任意窗口；
- 统计口径相关开关（和弦取音方式、是否跨小节、空小节是否计入分母）见 `config.yaml` 的 `analysis` 段。

**统计口径说明**：以小节为单位——小节内任一音群命中即该小节命中；多声部（如钢琴
上下谱表）任一声部命中即算；多页乐谱按页分析后汇总（命中小节合计 / 含音符小节合计）。

## 交叉手问题与启发式重分配（v1.1.0）

**问题背景**：钢琴谱中"哪只手演奏哪个音"由**符干朝向**决定，而非谱表。交叉手
（crossed hands）段落中，右手可能进入低音谱表、左手可能进入高音谱表。HOMR 输出的
MusicXML 未保留 `<stem>` 标签，且按音符垂直位置分配 staff/voice，导致交叉手音符被
错误归入对方声部，进而使"同一声部"类特征（如 `wide_leap_sum`）漏检。以 etude7 为例，
32 小节中 13 小节（40.6%）在低音谱表上出现超出常规左手音域的高音（>C5）。

**启发式规则**（`scoreflow/analysis/cross_hand.py`，模拟符干朝向判断的近似）：

- staff 2 上音高 > C5（midi 72）的音符 → 重标为右手（voice 1 / staff 1）；
- staff 1 上音高 < C3（midi 48）的音符 → 重标为左手（voice 5 / staff 2）。

**用法**：

```bash
python run.py --cross-hand-heuristic          # 分析时启用重分配
python cross_hand_compare.py                  # 生成「基线 vs 重分配」论文级对比表
```

对比报告输出到 `output/reports/交叉手对比_论文版.xlsx`（5 张表：对比总览 / 按特征汇总 /
逐页命中 / 重分配音符明细 / 声部分布）与同名 `.md`（可直接粘贴进论文）。

**局限**：阈值 C3/C5 为启发式，双手音域重叠段落（如琶音跑动跨越两谱表）可能误判；
这是"提出问题 + 近似修正"的第一版方案，不保证完全还原真实演奏分配。后续方向是在
OMR 识别阶段直接读取符干方向（见「已知限制」）。

## 项目结构

```
├── run.py                    # 命令行入口（全流程编排）
├── cross_hand_compare.py     # 交叉手「基线 vs 重分配」论文级对比报告
├── config.yaml               # 全部配置（路径/识别/分析特征）
├── requirements.txt
├── scoreflow/
│   ├── config.py             # 配置加载与启动校验
│   ├── pdf_render.py         # PDF -> PNG（pypdfium2）
│   ├── homr_ocr.py           # PNG -> MusicXML（子进程调用 HOMR）
│   ├── reporting.py          # Markdown / JSON / Excel 报告
│   └── analysis/
│       ├── engine.py         # 滑动窗口 + 小节统计引擎
│       ├── cross_hand.py     # 交叉手启发式重分配（v1.1.0）
│       └── features/         # ★ 音群特征插件目录（在这里加你的分析）
│           ├── base.py       #   特征基类与工具函数
│           ├── wide_leap_sum.py   #   示例：3音双音程之和>八度
│           ├── big_single_leap.py #   示例：单个大跳
│           ├── consecutive_sixteenths.py  # 连续6个十六分音符
│           ├── consecutive_chords.py      # 连续6个和弦（和弦感知特征示例）
│           └── _template.py  #   新特征模板
└── tests/run_tests.py        # 单元测试（不依赖识别，纯内存乐谱）
```

## 测试

```bash
python tests/run_tests.py
```

测试使用 music21 在内存中构造乐谱，不依赖 HOMR 环境，任何装了 music21 的机器都能跑。

## 已知限制

- HOMR 当前专注音高与节奏，力度、复杂装饰音等会丢失；OMR 结果建议在
  MuseScore 中人工复核后再用于严肃用途；
- **交叉手声部分配（v1.1.0 已部分缓解）**：HOMR 输出的 MusicXML 未保留 `<stem>`
  标签，交叉手段落中实际演奏分配（由符干朝向决定）与按谱表分组存在偏差。当前提供
  音域启发式重分配（`--cross-hand-heuristic`）作为近似修正，但双手音域重叠段落仍
  可能误判；彻底解决需在 OMR 识别阶段直接读取符干方向并按符干分配 voice/staff；
- 每页生成独立 MusicXML，分析按页汇总，不做跨页小节拼接（对按小节统计的特征无影响）；
- 识别质量取决于乐谱扫描清晰度，印刷清楚的现代乐谱效果最好。

## 致谢

- [HOMR](https://github.com/liebharc/homr) —— 识别引擎
- [music21](https://github.com/cuthbertLab/music21) —— 乐谱分析
- [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) —— PDF 渲染

## License

[MIT](LICENSE)
