# -*- coding: utf-8 -*-
"""特征注册表：自动发现本目录下的所有特征模块。

约定：每个特征模块需要暴露模块级变量 FEATURE（类或实例）。
新增特征只需新建 .py 文件，无需改动引擎代码。
"""

import importlib
import pkgutil
from pathlib import Path

from scoreflow.analysis.features.base import ScoreFeature

_PKG_DIR = Path(__file__).parent
_REGISTRY: dict[str, type[ScoreFeature]] = {}


def _discover() -> None:
    for mod_info in pkgutil.iter_modules([str(_PKG_DIR)]):
        if mod_info.name.startswith("_"):
            continue  # 跳过 __init__ / _template
        try:
            module = importlib.import_module(f"scoreflow.analysis.features.{mod_info.name}")
        except Exception as e:  # 单个特征导入失败不影响其他特征
            print(f"  ⚠ 特征模块 {mod_info.name} 导入失败: {e}")
            continue
        feature = getattr(module, "FEATURE", None)
        if feature is None:
            continue
        cls = feature if isinstance(feature, type) else type(feature)
        if not issubclass(cls, ScoreFeature):
            continue
        _REGISTRY[cls.name] = cls


_discover()


def all_features() -> dict[str, type[ScoreFeature]]:
    return dict(_REGISTRY)


def build_features(feature_config: dict) -> list[ScoreFeature]:
    """根据 config.yaml 的 analysis.features 配置实例化启用的特征。"""
    instances = []
    for name, setting in (feature_config or {}).items():
        if not isinstance(setting, dict) or not setting.get("enabled", False):
            continue
        cls = _REGISTRY.get(name)
        if cls is None:
            raise KeyError(
                f"未知特征 '{name}'。可用特征: {sorted(_REGISTRY)}；"
                f"自定义特征请放到 scoreflow/analysis/features/ 目录"
            )
        instances.append(cls(setting.get("params", {})))
    return instances
