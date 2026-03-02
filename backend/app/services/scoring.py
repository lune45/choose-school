from __future__ import annotations

from typing import Dict, List

from ..models import SchoolProgram

METRIC_KEYS = ["就业薪资", "学校排名", "区域优势", "课程适配", "成本", "工签支持", "校友网络", "H1B绿卡"]


def _normalize(values: List[float], reverse: bool = False) -> List[float]:
    if not values:
        return []

    lo = min(values)
    hi = max(values)
    if hi == lo:
        return [75.0 for _ in values]

    result = []
    for v in values:
        ratio = (v - lo) / (hi - lo)
        score = (1 - ratio) * 100 if reverse else ratio * 100
        result.append(round(score, 2))
    return result


def _extract_metric_raw(s: SchoolProgram) -> Dict[str, float]:
    total_cost = float(s.tuition_usd + s.living_cost_usd)
    course_fit = 100 - float(s.course_difficulty) * 10
    region = (float(s.employment_support) * 0.6 + float(s.safety_score) * 0.4)

    return {
        "就业薪资": float(s.median_salary_usd),
        "学校排名": float(s.ranking_score),
        "区域优势": region,
        "课程适配": max(0.0, min(100.0, course_fit)),
        "成本": total_cost,
        "工签支持": float(s.visa_support),
        "校友网络": float(s.alumni_network),
        "H1B绿卡": float(s.immigration_friendly),
    }


def rank_programs(programs: List[SchoolProgram], weights: Dict[str, int]) -> List[Dict]:
    if not programs:
        return []

    raw_matrix = [_extract_metric_raw(p) for p in programs]

    normalized_matrix: List[Dict[str, float]] = [{k: 0.0 for k in METRIC_KEYS} for _ in programs]
    for metric in METRIC_KEYS:
        column = [row[metric] for row in raw_matrix]
        reverse = metric == "成本"
        norm_values = _normalize(column, reverse=reverse)
        for idx, nv in enumerate(norm_values):
            normalized_matrix[idx][metric] = nv

    ranking = []
    for idx, program in enumerate(programs):
        metric_scores = normalized_matrix[idx]
        total = 0.0
        for key in METRIC_KEYS:
            total += metric_scores[key] * weights.get(key, 0) / 100.0

        ranking.append(
            {
                "school_id": program.id,
                "school": program.school_name,
                "program": program.program_name,
                "total_score": round(total, 2),
                "metrics": {k: round(v, 2) for k, v in metric_scores.items()},
            }
        )

    ranking.sort(key=lambda x: x["total_score"], reverse=True)
    for i, row in enumerate(ranking, start=1):
        row["rank"] = i
    return ranking
