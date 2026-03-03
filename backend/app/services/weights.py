from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List

INTERNAL_KEYS = ["就业薪资", "学校排名", "区域优势", "课程适配", "成本", "工签支持", "校友网络", "H1B绿卡"]

DIMENSION_META = [
    {"key": "employment", "label": "就业前景"},
    {"key": "salary", "label": "薪资水平"},
    {"key": "visa", "label": "签证/移民"},
    {"key": "ranking", "label": "学校排名"},
    {"key": "cost", "label": "总体费用"},
    {"key": "returnee", "label": "回国认可"},
    {"key": "location", "label": "地理位置"},
    {"key": "curriculum", "label": "课程质量"},
    {"key": "workload", "label": "读书压力"},
    {"key": "safety", "label": "安全环境"},
    {"key": "living", "label": "生活质量"},
    {"key": "alumni", "label": "校友资源"},
    {"key": "academic", "label": "学术声誉"},
]

DIMENSION_LABEL_MAP = {item["key"]: item["label"] for item in DIMENSION_META}

LEGACY_CONCERN_MAP = {
    "学历提升": "academic",
    "学费压力": "cost",
    "学校排名": "ranking",
    "当地就业": "employment",
    "就业去向": "employment",
    "移民": "visa",
    "薪资": "salary",
    "回国认可度": "returnee",
    "读书压力": "workload",
    "课程难度": "workload",
    "安全度": "safety",
    "生活开销": "cost",
    "生活质量": "living",
    "H1B移民": "visa",
    "就业薪资": "salary",
}

DIMENSION_TO_INTERNAL_RATIO: Dict[str, Dict[str, int]] = {
    "employment": {"就业薪资": 45, "区域优势": 30, "工签支持": 15, "校友网络": 10},
    "salary": {"就业薪资": 80, "学校排名": 20},
    "visa": {"工签支持": 50, "H1B绿卡": 50},
    "ranking": {"学校排名": 80, "校友网络": 20},
    "cost": {"成本": 100},
    "returnee": {"学校排名": 60, "校友网络": 25, "区域优势": 15},
    "location": {"区域优势": 100},
    "curriculum": {"课程适配": 100},
    "workload": {"课程适配": 80, "成本": 20},
    "safety": {"区域优势": 75, "成本": 25},
    "living": {"区域优势": 70, "成本": 30},
    "alumni": {"校友网络": 100},
    "academic": {"学校排名": 85, "课程适配": 15},
}

DEFAULT_INTERNAL_WEIGHTS: Dict[str, int] = {
    "就业薪资": 30,
    "学校排名": 10,
    "区域优势": 15,
    "课程适配": 15,
    "成本": 10,
    "工签支持": 10,
    "校友网络": 5,
    "H1B绿卡": 5,
}

LEGACY_WEIGHT_ADJUSTMENTS: Dict[str, Dict[str, int]] = {
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


def _to_int(value: object) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


def _normalize_sum_100(weights: Dict[str, int]) -> Dict[str, int]:
    if not weights:
        return {}
    total = sum(max(0, _to_int(v)) for v in weights.values())
    if total <= 0:
        equal = round(100 / max(1, len(weights)))
        values = {k: equal for k in weights.keys()}
    else:
        values = {k: round(max(0, _to_int(v)) / total * 100) for k, v in weights.items()}

    drift = 100 - sum(values.values())
    if drift != 0 and values:
        first_key = next(iter(values))
        values[first_key] += drift
    return values


def normalize_dimension_keys(selected_dimensions: List[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for item in selected_dimensions or []:
        raw = str(item).strip()
        if not raw:
            continue
        key = raw
        if key in LEGACY_CONCERN_MAP:
            key = LEGACY_CONCERN_MAP[key]
        if key not in DIMENSION_LABEL_MAP:
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(key)
    return result


def rank_formula_weights(selected_dimensions: List[str]) -> Dict[str, int]:
    ordered = normalize_dimension_keys(selected_dimensions)
    n = len(ordered)
    if n <= 0:
        return {}
    denom = n * (n + 1) / 2
    result: "OrderedDict[str, int]" = OrderedDict()
    running = 0
    for idx, key in enumerate(ordered, start=1):
        if idx == n:
            score = 100 - running
        else:
            score = round((n - idx + 1) / denom * 100)
            running += score
        result[key] = max(0, score)
    return dict(result)


def normalize_user_weights(
    selected_dimensions: List[str],
    provided_weights: Dict[str, int] | None = None,
) -> Dict[str, int]:
    ordered = normalize_dimension_keys(selected_dimensions)
    if not ordered:
        return {}

    if isinstance(provided_weights, dict) and provided_weights:
        candidate: "OrderedDict[str, int]" = OrderedDict()
        for key in ordered:
            if key in provided_weights:
                candidate[key] = max(0, _to_int(provided_weights.get(key)))
        raw_total = sum(candidate.values())
        if len(candidate) >= 2 and raw_total > 0 and abs(raw_total - 100) <= 3:
            return _normalize_sum_100(dict(candidate))

    return rank_formula_weights(ordered)


def map_user_weights_to_internal(user_weights: Dict[str, int]) -> Dict[str, int]:
    if not user_weights:
        return DEFAULT_INTERNAL_WEIGHTS.copy()

    acc = {k: 0.0 for k in INTERNAL_KEYS}
    for dim_key, weight in user_weights.items():
        if dim_key not in DIMENSION_TO_INTERNAL_RATIO:
            continue
        w = max(0.0, float(_to_int(weight)))
        split = DIMENSION_TO_INTERNAL_RATIO[dim_key]
        for internal_key, ratio in split.items():
            acc[internal_key] += w * float(ratio) / 100.0

    total = sum(acc.values())
    if total <= 0:
        return DEFAULT_INTERNAL_WEIGHTS.copy()

    normalized = {k: round(v / total * 100) for k, v in acc.items()}
    drift = 100 - sum(normalized.values())
    if drift != 0:
        primary = max(normalized, key=lambda x: normalized[x])
        normalized[primary] += drift
    return normalized


def concern_labels(selected_dimensions: List[str]) -> List[str]:
    ordered = normalize_dimension_keys(selected_dimensions)
    return [DIMENSION_LABEL_MAP[k] for k in ordered]


def label_weight_map(user_weights: Dict[str, int]) -> Dict[str, int]:
    ordered = OrderedDict()
    for key, value in user_weights.items():
        label = DIMENSION_LABEL_MAP.get(key, key)
        ordered[label] = _to_int(value)
    return _normalize_sum_100(dict(ordered))


def legacy_internal_weights(selected_dimensions: List[str]) -> Dict[str, int]:
    weights = DEFAULT_INTERNAL_WEIGHTS.copy()
    for dim in selected_dimensions or []:
        if dim in LEGACY_WEIGHT_ADJUSTMENTS:
            for key, delta in LEGACY_WEIGHT_ADJUSTMENTS[dim].items():
                weights[key] = max(0, weights[key] + delta)
    return _normalize_sum_100(weights)


# backward compatibility
def calc_weights(selected_dimensions: List[str]) -> Dict[str, int]:
    return legacy_internal_weights(selected_dimensions)
