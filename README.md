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

## 音型集特征（六类）

本框架内置《音型（音群）集》定义的六类钢琴技术音群特征，判定口径与难度加权见
[音型集标准.md](音型集标准.md)。

| 特征（代码名） | 窗口 | 命中判据 | 加权 |
|:---|:---:|:---|:---:|
| 伸张把位（`stretched_grip`） | 3 音 | 相邻 3 音音高走向相同（单调）且两段音程之和 > 12 半音（八度） | 2 |
| 收缩把位（`contracted_grip`） | 5 音 | 相邻 4 个音程之和 < 6 半音（减五度） | 1 |
| 连续十六分跑动（`consecutive_sixteenths`） | 5 音 | 单声部连续 5 个十六分音符 | 2 |
| 连续八分跑动（`consecutive_eighths`） | 3 音 | 单声部连续 3 个八分音符 | 1 |
| 连续和弦支撑（`consecutive_chords`） | 3 和弦 | 单声部连续 3 个和弦（≥3 音叠置） | 2 |
| 连续音程支撑（`consecutive_intervals`） | 3 音程 | 单声部连续 3 个双音叠置 | 1 |

难度加权模型：`D = Σ w_f · (m_f^1 + 2·m_f^2)`——双手同节技术加倍计分（详见
[音型集标准.md](音型集标准.md)）。

> `big_single_leap`（单个大跳）为预留特征，默认关闭，不在六类之内。

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
python run.py --set analysis.features.stretched_grip.params.threshold=16

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
错误归入对方声部，进而使"同一声部"类特征（如 `stretched_grip`）漏检。以 etude7 为例，
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

## 双手拆分诊断（v1.4.0）

**问题背景**：跨谱表琶音（如车尔尼 Op.740 No.21 第 1 小节）中，快速分解和弦实际由
左右手交替演奏，但 OMR 输出可能将双手音符归入同一声部/谱表，形成单声部内跨 10 度
以上（>=16 半音）的"超人手"音程。若直接在该合并声部上统计伸张把位，会得到与演奏
实际不符的虚假轮廓。

**诊断开关**（`scoreflow/analysis/hand_split.py`）：

- 合并某小节所有谱表的音符；
- 若整体跨度 >= `hand_split_threshold`（默认 16 半音 = 十度），则触发拆分；
- 按每个 onset 上的最大音程间隙把音符切分为右手（高音组）与左手（低音组）；
- 重建独立的 `Right Hand` / `Left Hand` 两个声部，再送入特征检测。

**用法**：

```bash
python run.py                              # config.yaml 中 hand_split_threshold 默认 16
python run.py --hand-split-threshold 16    # 命令行显式启用
python run.py --hand-split-threshold 0     # 关闭
```

**效果示例**：etude7 第 1 小节经拆分后，右手轮廓为 F#3→A6 的平滑上行再下行，左手
轮廓为 D2→F#5 的平行低八度线条，与乐谱标注的双手分配一致。

**局限**：该诊断以 onset 为单位按音高间隙粗分，无法处理声部真正交错（一只手插入
另一只手中间）的复杂织体；彻底解决仍需 OMR 阶段读取符干方向。

## 琶音误报与 arpeggio_aware 开关（v1.2.0）

**问题背景**：`stretched_grip` 的复合音程判据（相邻 3 音的两段音程之和 > 八度）本意
是捕捉伸张把位，但在琶音织体上会**系统性误报**。人工核查 4 首考级练习曲发现：
etude7 实际几乎不存在伸张把位——通篇是整齐的琶音跑动与左手和弦，但该特征基线
命中占比高达 96.9%（31/32 小节）。原因是跨八度琶音（如 `C4 -> G4 -> E5`，7+8=15
半音）满足"音程之和 > 八度"，却被复合判据误判为伸张把位。

**开关方案**（`wide_leap_sum` 参数 `arpeggio_aware`，默认关闭）：

启用后，若音群 3 个音的**音级（pitch class）集合可整体嵌入某个三和弦或常用七和弦**
（大小三 / 减 / 增三和弦，大 / 小 / 属 / 减 / 半减七和弦的任意转位，任意八度、任意
出现次序、允许重复音），则视为**分解和弦（琶音）音型**予以豁免，不判为伸张把位。
判定依据是和弦归属（chord membership）而非音程方向——因为实际误报中大量是
折返型琶音（如 `A-2 -> D-2 -> A-2`，7+7=14 半音），仅靠"单调方向过滤"无法覆盖。

**用法**：

```bash
python run.py --set analysis.features.stretched_grip.params.arpeggio_aware=true
python arpeggio_compare.py    # 生成「基线 vs 开关」论文级对比表
```

对比报告输出到 `output/reports/琶音感知对比_论文版.xlsx`（5 张表：对比总览 /
命中分解 / 逐小节明细 / 其他特征校验 / 全语料汇总）与同名 `.md`。
两版引擎均启用交叉手重分配，唯一变量是本开关。

**数据结果**（4 首考级练习曲，195 小节）：

| 乐谱 | 基线占比 | 开关后 | Δ | 基线命中中琶音占比 |
|:---|:---:|:---:|:---:|:---:|
| etude7 | 96.9% | 25.0% | -71.9pp | 94.5% |
| etude8 | 71.1% | 2.6% | -68.4pp | 98.0% |
| etude9 | 75.0% | 38.6% | -36.4pp | 80.7% |
| etude10 | 77.8% | 44.4% | -33.3pp | 80.3% |
| 全语料 | 79.0% | 31.8% | -47.2pp | 87.1% |

其余特征（`consecutive_sixteenths` / `consecutive_chords`）逐页结果完全一致（Δ=0），
证明开关无副作用。

**局限**：本开关**不彻底解决**误报问题，属于"提出问题 + 部分修正"的一版方案：

- 音群混入非和弦音（经过音、倚音）时和弦归属判定失效。典型残留：etude7 的
  `E2 -> B2 -> A3`（7+10=17 半音）中 A 为 E 大三和弦外音，仍被判为宽跳；
- 声部交错（和弦顶音与低音交替）形成的音群可能不满足和弦归属，仍会误报；
- 和弦归属是必要不充分条件：真旋律宽跳若恰为同一和弦的和弦音（如
  `C4 -> E5 -> G5` 的右手宽幅琶音式旋律）也会被豁免。

完整解决需要和弦还原（调性分析确定当前和声）与更精细的声部分离，见「已知限制」。

## 项目结构

```
├── run.py                    # 命令行入口（全流程编排）
├── cross_hand_compare.py     # 交叉手「基线 vs 重分配」论文级对比报告
├── arpeggio_compare.py       # 琶音感知开关「基线 vs 开启」论文级对比报告（v1.2.0）
├── grades_summary.py         # 1-10 级分级汇总（难度加权 + 等级趋势，v1.3.0）
├── config.yaml               # 全部配置（路径/识别/分析特征）
├── 音型集标准.md             # 音群特征判定标准（六类特征 + 难度加权）
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
│           ├── stretched_grip.py   #   伸张把位：3音单调且双音程之和>八度（加权2）
│           ├── contracted_grip.py #   收缩把位：5音4音程之和<减五度（加权1）
│           ├── consecutive_sixteenths.py  # 连续十六分跑动：连续5个（加权2）
│           ├── consecutive_eighths.py     # 连续八分跑动：连续3个（加权1）
│           ├── consecutive_chords.py      # 连续和弦支撑：连续3个和弦（加权2）
│           ├── consecutive_intervals.py   # 连续音程支撑：连续3个双音（加权1）
│           ├── big_single_leap.py #   预留：单个大跳（默认关闭）
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
- **琶音织体上的伸张把位误报（v1.2.0 已部分缓解）**：复合音程判据会把分解和弦跑动误判
  为伸张把位。`arpeggio_aware` 开关用和弦归属豁免纯琶音音群，但音群含非和弦音
  （经过音/倚音）或声部交错时仍会误报；彻底解决需结合调性和声分析（和弦还原）与
  声部分离；
- 每页生成独立 MusicXML，分析按页汇总，不做跨页小节拼接（对按小节统计的特征无影响）；
- 识别质量取决于乐谱扫描清晰度，印刷清楚的现代乐谱效果最好。

## 致谢

- [HOMR](https://github.com/liebharc/homr) —— 识别引擎
- [music21](https://github.com/cuthbertLab/music21) —— 乐谱分析
- [pypdfium2](https://github.com/pypdfium2-team/pypdfium2) —— PDF 渲染

## License

[MIT](LICENSE)
