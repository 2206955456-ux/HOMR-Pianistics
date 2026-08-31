# Changelog

本仓库的版本更新记录。语义化版本：`主.次.补丁`。

## v1.1.0 (2026-08-31)

### 新增功能
- **交叉手启发式声部重分配**（`--cross-hand-heuristic` / `config.yaml: analysis.cross_hand_heuristic`）
  - 新模块 `scoreflow/analysis/cross_hand.py`
  - 规则：低音谱表(staff2)上 > C5(midi 72) 的音符 → 重标为右手（voice 1 / staff 1）；
    高音谱表(staff1)上 < C3(midi 48) 的音符 → 重标为左手（voice 5 / staff 2）
  - 用于缓解 HOMR 未保留 `<stem>` 标签导致的交叉手段落声部错配问题
- **论文级对比报告**（`cross_hand_compare.py`）
  - 输出「基线 vs 重分配」对比 Excel（5 张表：对比总览 / 按特征汇总 / 逐页命中 /
    重分配音符明细 / 声部分布）与 Markdown 版，可直接放入论文
- **人工标注一致性评估**（`agreement_eval.py`）
  - 生成标注模板（`标注模板_4首.xlsx`，40 小节）+ 计算 P / R / F1 / Cohen's Kappa

### Bug 修复
- **声部重复计数**：`score.parts` 返回惰性迭代器（StreamIterator），被 `len()` 消费后
  迭代状态错乱，导致同一高音声部产出两次（Piano#1 = Piano#2）、命中记录虚高一倍；
  修复为先物化 `list(score.parts)` 再迭代
- **总览合计行公式**：单曲时引用错行；多曲时占比不可直接相加，改为不输出合计行避免误导

### 数据结果（4 首中国音乐学院考级 7–10 级练习曲，195 小节）
- 全语料重分配 118 个音符（LH→RH 105、RH→LH 13）
- etude7 的 wide_leap_sum 命中率 90.6% → 96.9%（+6.2pp）
- etude8 的 consecutive_sixteenths 命中率 86.8% → 89.5%（+2.6pp）
- 详见 `output/reports/交叉手对比_论文版.xlsx`

### 文档
- README 新增「交叉手问题与启发式重分配」一节与「已知限制」

## v1.0.0 (2026-08-30)

- 初始版本：PDF → HOMR 识别 → music21 特征分析 一站式工作流
- 内置 4 个可插拔音群特征（wide_leap_sum / big_single_leap / consecutive_sixteenths / consecutive_chords）
- 报告输出：report.md / report.json / report.xlsx（总览 + 每特征明细）
