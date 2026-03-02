from __future__ import annotations

from typing import Dict, List

DEFAULT_WEIGHTS: Dict[str, int] = {
    "就业薪资": 30,
    "学校排名": 10,
    "区域优势": 15,
    "课程适配": 15,
    "成本": 10,
    "工签支持": 10,
    "校友网络": 5,
    "H1B绿卡": 5,
}

WEIGHT_ADJUSTMENTS: Dict[str, Dict[str, int]] = {
    "H1B移民": {"H1B绿卡": 5, "工签支持": 5, "学校排名": -5, "成本": -5},
    "学费压力": {"成本": 10, "学校排名": -5, "校友网络": -5},
    "回国认可度": {"学校排名": 10, "H1B绿卡": -10, "工签支持": -5, "区域优势": 5},
    "当地就业": {"区域优势": 10, "就业薪资": 5, "学校排名": -10, "校友网络": -5},
    "薪资": {"就业薪资": 10, "成本": -5, "校友网络": -5},
    "移民": {"H1B绿卡": 8, "工签支持": 5, "学校排名": -8, "成本": -5},
    "读书压力": {"课程适配": 8, "就业薪资": -5, "区域优势": -3},
    "学校排名": {"学校排名": 10, "区域优势": -5, "成本": -5},
    "课程难度": {"课程适配": 10, "就业薪资": -5, "学校排名": -5},
    "生活开销": {"成本": 12, "学校排名": -6, "区域优势": -6},
    "安全度": {"区域优势": 5, "课程适配": 3, "学校排名": -3, "就业薪资": -5},
}


def calc_weights(selected_dimensions: List[str]) -> Dict[str, int]:
    weights = DEFAULT_WEIGHTS.copy()

    for dim in selected_dimensions:
        if dim in WEIGHT_ADJUSTMENTS:
            for key, delta in WEIGHT_ADJUSTMENTS[dim].items():
                weights[key] = max(0, weights[key] + delta)

    total = sum(weights.values())
    if total == 0:
        return DEFAULT_WEIGHTS.copy()

    normalized = {k: round(v / total * 100) for k, v in weights.items()}
    drift = 100 - sum(normalized.values())
    if drift != 0:
        primary = max(normalized, key=lambda x: normalized[x])
        normalized[primary] += drift

    return normalized
