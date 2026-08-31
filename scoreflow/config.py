# -*- coding: utf-8 -*-
"""配置加载与校验：默认值 <- config.yaml <- 命令行覆盖"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULTS = {
    "paths": {
        # HOMR 发行版中嵌入式 Python 的路径（用于调用 homr 识别）
        "homr_python": r"D:\HOMR\homr-main\python_embed\python.exe",
        # HOMR 主目录（含模型权重，运行时作为工作目录）
        "homr_dir": r"D:\HOMR\homr-main",
        "input_dir": r"D:\HOMR\input",
        "output_dir": r"D:\HOMR\output",
    },
    "pipeline": {
        "dpi": 300,          # PDF 渲染 DPI
        "gpu": "no",         # auto | no | force
        "timeout": 600,      # 单页识别超时（秒）
    },
    "analysis": {
        # 和弦的处理方式: top=取最高音(旋律线), skip=跳过和弦, all=展开每个和弦音
        "chord_mode": "top",
        # 统计占比时分母是否包含无音符的小节
        "count_empty_measures": False,
        # 滑动窗口是否允许跨越小节线（False=只在同一小节内找相邻音群）
        "across_barlines": False,
        "features": {
            "wide_leap_sum": {"enabled": True, "params": {"threshold": 12}},
            "big_single_leap": {"enabled": False, "params": {"threshold": 8}},
        },
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


@dataclass
class Config:
    homr_python: Path
    homr_dir: Path
    input_dir: Path
    output_dir: Path
    dpi: int
    gpu: str
    timeout: int
    chord_mode: str
    count_empty_measures: bool
    across_barlines: bool
    features: dict = field(default_factory=dict)

    def validate(self) -> None:
        errors = []
        if not self.homr_python.exists():
            errors.append(f"HOMR Python 不存在: {self.homr_python}")
        if not (self.homr_dir / "homr").exists():
            errors.append(f"HOMR 主目录无效（缺少 homr 包）: {self.homr_dir}")
        if self.gpu not in ("auto", "no", "force"):
            errors.append(f"gpu 必须是 auto/no/force，当前: {self.gpu}")
        if self.dpi < 72:
            errors.append(f"dpi 过小: {self.dpi}")
        if self.chord_mode not in ("top", "skip", "all"):
            errors.append(f"chord_mode 必须是 top/skip/all，当前: {self.chord_mode}")
        if errors:
            raise ConfigError("配置校验失败:\n  - " + "\n  - ".join(errors))

    def require_input(self) -> None:
        if not self.input_dir.exists():
            raise ConfigError(f"输入目录不存在: {self.input_dir}")


class ConfigError(Exception):
    pass


def load_config(config_path: str | None = None, overrides: dict | None = None) -> Config:
    """加载配置：默认值 <- config.yaml <- 命令行 overrides

    config_path 为 None 时自动加载项目根目录的 config.yaml（若存在），
    保证"编辑 config.yaml 即生效"。
    """
    data = DEFAULTS
    if config_path:
        p = Path(config_path)
        if not p.exists():
            raise ConfigError(f"配置文件不存在: {p}")
    else:
        p = Path(__file__).resolve().parents[1] / "config.yaml"
    if p.exists():
        with open(p, "r", encoding="utf-8") as f:
            data = _deep_merge(data, yaml.safe_load(f) or {})
    if overrides:
        data = _deep_merge(data, overrides)

    paths = data["paths"]
    pipe = data["pipeline"]
    ana = data["analysis"]

    # YAML 1.1 会把裸的 no/yes/on/off 解析成布尔值，这里统一转回字符串
    _gpu = pipe["gpu"]
    if isinstance(_gpu, bool):
        _gpu = "no" if not _gpu else "auto"

    # 允许用环境变量 HOMR_PYTHON 覆盖，方便 CI/其他机器
    homr_python = os.environ.get("HOMR_PYTHON", paths["homr_python"])

    cfg = Config(
        homr_python=Path(homr_python),
        homr_dir=Path(paths["homr_dir"]),
        input_dir=Path(paths["input_dir"]),
        output_dir=Path(paths["output_dir"]),
        dpi=int(pipe["dpi"]),
        gpu=_gpu,
        timeout=int(pipe["timeout"]),
        chord_mode=ana["chord_mode"],
        count_empty_measures=bool(ana["count_empty_measures"]),
        across_barlines=bool(ana["across_barlines"]),
        features=ana.get("features", {}),
    )
    cfg.validate()
    return cfg
