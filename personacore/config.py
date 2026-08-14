"""配置加载：大五维度定义、权重、合格线、一票否决等。

维度与题库来自 config/dimensions.yaml，管理员可修改权重 / 阈值 / 锚点 / 题目。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import yaml


@dataclass
class Dimension:
    key: str
    name: str
    bigfive: str
    anchors_positive: List[str]
    anchors_negative: List[str]
    questions: List[str]
    weight: float
    threshold: float
    veto: bool


@dataclass
class AppConfig:
    dimensions: List[Dimension]
    scale_min: int = 1
    scale_max: int = 5
    max_probes: int = 2

    @property
    def total_weight(self) -> float:
        return sum(d.weight for d in self.dimensions) or 1.0


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    defaults = raw.get("defaults", {}) or {}
    scale_min = int(defaults.get("scale_min", 1))
    scale_max = int(defaults.get("scale_max", 5))
    max_probes = int(defaults.get("max_probes", 2))
    def_weight = float(defaults.get("weight", 0.2))
    def_threshold = float(defaults.get("threshold", 3.0))
    def_veto = bool(defaults.get("veto", False))

    dimensions: List[Dimension] = []
    for d in raw.get("dimensions", []):
        anchors = d.get("anchors", {}) or {}
        dimensions.append(
            Dimension(
                key=d["key"],
                name=d["name"],
                bigfive=d.get("bigfive", ""),
                anchors_positive=list(anchors.get("positive", [])),
                anchors_negative=list(anchors.get("negative", [])),
                questions=list(d.get("questions", [])),
                weight=float(d.get("weight", def_weight)),
                threshold=float(d.get("threshold", def_threshold)),
                veto=bool(d.get("veto", def_veto)),
            )
        )

    return AppConfig(
        dimensions=dimensions,
        scale_min=scale_min,
        scale_max=scale_max,
        max_probes=max_probes,
    )
