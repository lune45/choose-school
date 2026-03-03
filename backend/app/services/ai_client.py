from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from typing import Any, Dict, List, Tuple

import httpx

from ..config import get_settings
from .deepseek import DISCLAIMER
from .query_schema import compose_query_output, enforce_country_specific_dash, get_query_output_schema

logger = logging.getLogger(__name__)

STRICT_JSON_SYSTEM_PROMPT = (
    "你是留学择校分析助手，必须严格基于提供的数据。"
    "你必须只返回合法JSON，不要包含任何markdown代码块、"
    "不要有```json标记、不要有任何前缀文字或解释，"
    "直接从{开始，到}结束。"
)

DETAILED_OUTPUT_REQUIREMENTS = f"""
【补充输出要求（必须严格遵守）】
1. 顶层JSON结构保持不变，并新增 executive_summary 字段（放在 comprehensive_ranking 之前）。
2. 顶层字段要求：
   - executive_summary：150字以上，整体概述用户画像、核心取舍和择校方向。
   - comprehensive_ranking：字段名保持现有格式不变。
   - school_assessments：字段名保持现有格式不变，并在每所学校中新增“就读体验”“行动建议”。
   - final_recommendation：200字以上，必须明确给出“首选、备选、预算有限”三种情形建议。
   - disclaimer：保持为“{DISCLAIMER}”。
3. school_assessments 每所学校内容深度要求：
   - 亮点：至少3条，每条50字以上，必须包含具体数据支撑。
   - 短板：至少2条，每条40字以上。
   - 就业前景：100字以上，必须包含具体公司名称、薪资区间、就业路径。
   - 就读体验：80字以上，描述课程强度、华人比例、城市生活感受。
   - 行动建议：3条具体建议，例如“建议入学前完成LeetCode 200题”。
   - query_output：必须输出标准化查询字段对象；所有key都要有值，不适用或缺失写"-"。
4. 除新增字段外，不要改已有字段名，不要删除已有字段。
"""


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [_to_text(x) for x in value if _to_text(x)]
    if isinstance(value, str):
        return [x.strip() for x in re.split(r"\n|；|;|。|,|，", value) if x.strip()]
    return []


def _normalize_concern_analysis(value: Any, selected_dimensions: List[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if isinstance(value, dict):
        for k, v in value.items():
            key = _to_text(k)
            val = _to_text(v)
            if key and val:
                rows.append({"concern": key, "analysis": val})
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str):
                text = _to_text(item)
                if text:
                    rows.append({"concern": "关注点分析", "analysis": text})
                continue
            if not isinstance(item, dict):
                continue
            key = _to_text(item.get("concern") or item.get("key") or item.get("name") or item.get("title"))
            val = _to_text(item.get("analysis") or item.get("value") or item.get("detail") or item.get("content"))
            if key and val:
                rows.append({"concern": key, "analysis": val})
    elif isinstance(value, str):
        text = _to_text(value)
        if text:
            rows.append({"concern": "关注点分析", "analysis": text})

    if rows:
        return rows
    if selected_dimensions:
        return [{"concern": dim, "analysis": "该维度需要进一步结合个人背景与最新官方信息确认。"} for dim in selected_dimensions]
    return [{"concern": "综合建议", "analysis": "建议结合预算、就业目标与申请成功率进一步确认。"}]


def _safe_score(value: Any, fallback: int = 70) -> int:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return fallback
    score = round(score)
    return max(0, min(100, int(score)))


def _build_query_output_map(schools_json: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    mapping: Dict[str, Dict[str, str]] = {}
    for item in schools_json:
        if not isinstance(item, dict):
            continue
        school_name = _to_text(item.get("school_name"))
        program_name = _to_text(item.get("program_name"))
        if not school_name or not program_name:
            continue
        raw_query_output = item.get("query_output") if isinstance(item.get("query_output"), dict) else {}
        merged = compose_query_output(item, raw_query_output)
        mapping[f"{school_name}::{program_name}"] = merged
    return mapping


def _normalize_query_output(
    value: Any,
    fallback_query_output: Dict[str, str],
) -> Dict[str, str]:
    normalized = {k: (_to_text(v) or "-") for k, v in fallback_query_output.items()}
    incoming = value if isinstance(value, dict) else {}
    for key, raw_value in incoming.items():
        text = _to_text(raw_value)
        normalized[_to_text(key)] = text if text else "-"
    for key, raw_value in normalized.items():
        if _to_text(raw_value) in {"", "0", "0.0", "None", "null", "N/A", "n/a"}:
            normalized[key] = "-"
    return enforce_country_specific_dash(normalized)


def _default_school_cards(schools_json: List[Dict[str, Any]], selected_dimensions: List[str]) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    for item in schools_json:
        fallback_query_output = compose_query_output(item if isinstance(item, dict) else {}, {})
        raw_query_output = item.get("query_output") if isinstance(item, dict) and isinstance(item.get("query_output"), dict) else {}
        query_output = _normalize_query_output(raw_query_output, fallback_query_output)
        cards.append(
            {
                "school_name": _to_text(item.get("school_name")) or "未知院校",
                "program_name": _to_text(item.get("program_name")) or "未知项目",
                "fit_score": 70,
                "pros": ["课程与就业路径具备一定匹配度。"],
                "cons": ["需要结合个人背景与申请难度进一步评估。"],
                "concern_analysis": _normalize_concern_analysis({}, selected_dimensions),
                "recommended_actions": [
                    "核对最新官方课程与学费信息。",
                    "结合个人预算和就业目标进行优先级排序。",
                ],
                "query_output": query_output,
            }
        )
    return cards


def normalize_report_json(
    parsed: Dict[str, Any],
    schools_json: List[Dict[str, Any]],
    selected_dimensions: List[str],
) -> Dict[str, Any]:
    data = parsed if isinstance(parsed, dict) else {}
    defaults = _default_school_cards(schools_json, selected_dimensions)
    query_output_map = _build_query_output_map(schools_json)
    query_output_schema = get_query_output_schema()

    raw_ranking = data.get("comprehensive_ranking") if isinstance(data.get("comprehensive_ranking"), list) else []
    raw_assessments = (
        data.get("school_assessments")
        or data.get("school_analysis")
        or data.get("school_evaluations")
        or data.get("school_cards")
        or data.get("results")
        or data.get("schools")
    )
    raw_assessments = raw_assessments if isinstance(raw_assessments, list) else []

    ranking_info_map: Dict[str, Dict[str, Any]] = {}
    normalized_ranking: List[Dict[str, Any]] = []

    for idx, row in enumerate(raw_ranking, start=1):
        if not isinstance(row, dict):
            continue
        school_name = _to_text(row.get("school_name") or row.get("school") or row.get("院校") or row.get("学校"))
        program_name = _to_text(row.get("program_name") or row.get("program") or row.get("项目"))
        if not school_name or not program_name:
            continue

        fit_score = _safe_score(
            row.get("fit_score") or row.get("total_score") or row.get("score") or row.get("总分"),
            70,
        )
        rank_value = row.get("rank") or row.get("排名") or idx
        score_breakdown_raw = row.get("score_breakdown") if isinstance(row.get("score_breakdown"), dict) else {}

        score_breakdown = {
            "就业薪资": score_breakdown_raw.get("就业薪资", ""),
            "学校排名": score_breakdown_raw.get("学校排名", ""),
            "区域优势": score_breakdown_raw.get("区域优势", ""),
            "课程适配": score_breakdown_raw.get("课程适配", ""),
            "成本控制": score_breakdown_raw.get("成本控制", score_breakdown_raw.get("成本", "")),
            "工签支持": score_breakdown_raw.get("工签支持", ""),
            "校友网络": score_breakdown_raw.get("校友网络", ""),
            "H1B绿卡": score_breakdown_raw.get("H1B绿卡", score_breakdown_raw.get("H1B", "")),
        }

        normalized_row = {
            "rank": rank_value,
            "school_name": school_name,
            "program_name": program_name,
            "fit_score": fit_score,
            "score_breakdown": score_breakdown,
        }
        normalized_ranking.append(normalized_row)
        ranking_info_map[f"{school_name}::{program_name}"] = normalized_row

    normalized_schools: List[Dict[str, Any]] = []
    normalized_assessments: List[Dict[str, Any]] = []

    for idx, row in enumerate(raw_assessments):
        if not isinstance(row, dict):
            continue
        fallback = defaults[idx] if idx < len(defaults) else {
            "school_name": "未知院校",
            "program_name": "未知项目",
            "fit_score": 70,
        }

        school_name = _to_text(
            row.get("school_name")
            or row.get("school")
            or row.get("name")
            or row.get("学校")
            or row.get("院校")
            or fallback["school_name"]
        ) or fallback["school_name"]
        program_name = _to_text(
            row.get("program_name")
            or row.get("program")
            or row.get("项目")
            or fallback["program_name"]
        ) or fallback["program_name"]

        ranking_info = ranking_info_map.get(f"{school_name}::{program_name}", {})
        fallback_query_output = query_output_map.get(f"{school_name}::{program_name}", {})
        ranking_breakdown = (
            ranking_info.get("score_breakdown")
            if isinstance(ranking_info.get("score_breakdown"), dict)
            else {}
        )

        row_score_breakdown = row.get("score_breakdown") if isinstance(row.get("score_breakdown"), dict) else {}
        merged_breakdown = {
            "就业薪资": row_score_breakdown.get("就业薪资", ranking_breakdown.get("就业薪资", "")),
            "学校排名": row_score_breakdown.get("学校排名", ranking_breakdown.get("学校排名", "")),
            "区域优势": row_score_breakdown.get("区域优势", ranking_breakdown.get("区域优势", "")),
            "课程适配": row_score_breakdown.get("课程适配", ranking_breakdown.get("课程适配", "")),
            "成本控制": row_score_breakdown.get("成本控制", ranking_breakdown.get("成本控制", "")),
            "工签支持": row_score_breakdown.get("工签支持", ranking_breakdown.get("工签支持", "")),
            "校友网络": row_score_breakdown.get("校友网络", ranking_breakdown.get("校友网络", "")),
            "H1B绿卡": row_score_breakdown.get("H1B绿卡", ranking_breakdown.get("H1B绿卡", "")),
        }

        fit_score = _safe_score(
            row.get("fit_score")
            or row.get("total_score")
            or row.get("score")
            or ranking_info.get("fit_score"),
            fallback=_safe_score(fallback.get("fit_score"), 70),
        )

        pros = _to_list(row.get("pros") or row.get("亮点") or row.get("advantages")) or ["该项目在目标国家具备一定竞争力。"]
        cons = _to_list(row.get("cons") or row.get("短板") or row.get("risks")) or ["仍需结合申请难度与个人背景进一步评估。"]
        concern_source = row.get("concern_analysis") or row.get("concerns") or row.get("concernAnalysis")
        concern_analysis = _normalize_concern_analysis(concern_source, selected_dimensions)
        experience = _to_text(row.get("experience") or row.get("就读体验"))
        total_cost = _to_text(row.get("total_cost") or row.get("总成本") or row.get("cost"))
        outlook = _to_text(row.get("就业前景") or row.get("outlook"))
        actions = _to_list(row.get("recommended_actions") or row.get("行动建议") or row.get("actions") or row.get("next_steps")) or [
            "核对该项目最新录取要求和课程设置。",
            "结合预算与就业目标制定申请优先级。",
        ]
        evidence_used = _to_list(row.get("evidence_used") or row.get("evidence"))
        query_output = _normalize_query_output(row.get("query_output"), fallback_query_output)

        school_obj = {
            "school_name": school_name,
            "program_name": program_name,
            "fit_score": fit_score,
            "pros": pros,
            "cons": cons,
            "concern_analysis": concern_analysis,
            "experience": experience,
            "就读体验": experience,
            "total_cost": total_cost,
            "就业前景": outlook,
            "recommended_actions": actions,
            "evidence_used": evidence_used,
            "query_output": query_output,
            "score_breakdown": merged_breakdown,
            "就业薪资": merged_breakdown.get("就业薪资", ""),
            "学校排名": merged_breakdown.get("学校排名", ""),
            "区域": merged_breakdown.get("区域优势", ""),
            "课程": merged_breakdown.get("课程适配", ""),
            "成本": merged_breakdown.get("成本控制", ""),
            "工签": merged_breakdown.get("工签支持", ""),
            "校友": merged_breakdown.get("校友网络", ""),
            "H1B": merged_breakdown.get("H1B绿卡", ""),
        }
        normalized_schools.append(school_obj)

        concern_dict = {item["concern"]: item["analysis"] for item in concern_analysis if item.get("concern") and item.get("analysis")}
        normalized_assessments.append(
            {
                "school_name": school_name,
                "program_name": program_name,
                "fit_score": fit_score,
                "total_cost": total_cost,
                "pros": pros,
                "cons": cons,
                "concern_analysis": concern_dict,
                "experience": experience,
                "recommended_actions": actions,
                "evidence_used": evidence_used,
                "query_output": query_output,
            }
        )

    if not normalized_schools:
        normalized_schools = defaults

    executive_summary = _to_text(
        data.get("executive_summary") or data.get("executiveSummary") or data.get("summary") or data.get("overview")
    )
    if not executive_summary:
        executive_summary = "已基于你的关注点完成分析，请结合学校卡片信息进行最终选择。"

    final_recommendation = _to_text(
        data.get("final_recommendation")
        or data.get("finalRecommendation")
        or data.get("recommendation")
        or data.get("conclusion")
    )
    if not final_recommendation:
        final_recommendation = "建议优先选择综合匹配度高、总成本可控且就业回报更稳健的项目。"

    disclaimer = _to_text(data.get("disclaimer")) or DISCLAIMER

    return {
        "executive_summary": executive_summary,
        "comprehensive_ranking": normalized_ranking,
        "school_assessments": normalized_assessments,
        "schools": normalized_schools,
        "query_output_schema": query_output_schema,
        "final_recommendation": final_recommendation,
        "disclaimer": disclaimer,
    }


def parse_deepseek_json(raw: str) -> Dict[str, Any]:
    clean = re.sub(r"```json\s*", "", raw, flags=re.IGNORECASE)
    clean = re.sub(r"```\s*", "", clean, flags=re.IGNORECASE).strip()
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError("DeepSeek返回内容中未找到JSON边界")
    return json.loads(clean[start:end])


def result_json_to_markdown(result_json: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("## Executive Summary")
    lines.append(_to_text(result_json.get("executive_summary")) or "暂无")
    lines.append("")

    schools = result_json.get("schools") if isinstance(result_json.get("schools"), list) else []
    lines.append("## 逐校评估")
    for idx, row in enumerate(schools, start=1):
        if not isinstance(row, dict):
            continue
        school_name = _to_text(row.get("school_name")) or "未知院校"
        program_name = _to_text(row.get("program_name")) or "未知项目"
        fit_score = _safe_score(row.get("fit_score"), 70)
        lines.append(f"### {idx}. {school_name} · {program_name}")
        lines.append(f"- Fit Score: {fit_score}")

        pros = _to_list(row.get("pros"))
        cons = _to_list(row.get("cons"))
        actions = _to_list(row.get("recommended_actions"))

        if pros:
            lines.append(f"- 优势：{'；'.join(pros)}")
        if cons:
            lines.append(f"- 短板：{'；'.join(cons)}")
        if actions:
            lines.append(f"- 建议动作：{'；'.join(actions)}")
        lines.append("")

    lines.append("## 最终建议")
    lines.append(_to_text(result_json.get("final_recommendation")) or "暂无")
    lines.append("")
    lines.append(_to_text(result_json.get("disclaimer")) or DISCLAIMER)
    return "\n".join(lines).strip()


async def generate_report(
    prompt: str,
    schools_json: List[Dict[str, Any]],
    selected_dimensions: List[str],
) -> Tuple[str, Dict[str, Any], str]:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，无法生成AI分析")

    def _save_pending_search_insights(records: List[Dict[str, Any]]) -> None:
        if not records:
            return
        try:
            from ..database import SessionLocal
            from ..models import SchoolSearchInsight
        except Exception as exc:
            logger.warning("save_pending_search_insights import failed error=%s", repr(exc))
            return

        with SessionLocal() as db:
            created = 0
            for record in records:
                summary_text = _to_text(record.get("summary_text"))
                school_name = _to_text(record.get("school_name"))
                if not summary_text or not school_name:
                    continue

                school_program_id = record.get("school_id")
                content_hash = hashlib.sha256(summary_text.encode("utf-8")).hexdigest()
                exists = (
                    db.query(SchoolSearchInsight)
                    .filter(
                        SchoolSearchInsight.school_program_id == school_program_id,
                        SchoolSearchInsight.school_name == school_name,
                        SchoolSearchInsight.status == "pending",
                    )
                    .all()
                )
                duplicated = any(
                    hashlib.sha256(_to_text(x.raw_text).encode("utf-8")).hexdigest() == content_hash
                    for x in exists
                )
                if duplicated:
                    continue

                db.add(
                    SchoolSearchInsight(
                        school_program_id=school_program_id,
                        school_name=school_name,
                        program_name=_to_text(record.get("program_name")),
                        source_provider=_to_text(record.get("provider")) or "web-search",
                        raw_text=summary_text,
                        search_payload={
                            "items": record.get("items", []),
                            "query_count": len(record.get("items", []) or []),
                        },
                        status="pending",
                    )
                )
                created += 1
            if created:
                db.commit()

    # 如果配置了联网搜索提供商，先搜索就读体验
    experience_context = ""
    try:
        from .search import batch_search_school_records, web_search_enabled

        if web_search_enabled():
            records = await batch_search_school_records(schools_json)
            lines = []
            for row in records:
                school_name = _to_text(row.get("school_name"))
                program_name = _to_text(row.get("program_name"))
                text = _to_text(row.get("summary_text"))
                if text:
                    title = f"{school_name} · {program_name}" if program_name else school_name
                    lines.append(f"【{title}真实就读反馈（来自网络）】\n{text}")
            experience_context = "\n\n".join(lines)
            _save_pending_search_insights(records)
    except Exception as exc:
        logger.warning("web_search skipped due to error=%s", repr(exc))

    if experience_context:
        prompt += f"\n\n【联网搜索到的就读体验（仅供参考，请甄别真实性）】\n{experience_context}"

    url = f"{settings.deepseek_api_base.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": STRICT_JSON_SYSTEM_PROMPT},
            {"role": "user", "content": f"{prompt}\n\n{DETAILED_OUTPUT_REQUIREMENTS}"},
        ],
        "temperature": 0.2,
    }

    last_error: Exception | None = None
    for attempt in range(1, 4):
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
            elapsed_ms = (time.perf_counter() - started) * 1000
            resp.raise_for_status()

            body = resp.json()
            usage = body.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")

            raw = _to_text(body["choices"][0]["message"]["content"])
            if not raw:
                raise RuntimeError("DeepSeek 返回空内容")

            logger.info(
                "deepseek_call success attempt=%s elapsed_ms=%.2f prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                attempt,
                elapsed_ms,
                prompt_tokens,
                completion_tokens,
                total_tokens,
            )

            try:
                parsed = parse_deepseek_json(raw)
            except Exception as parse_err:
                logger.exception(
                    "deepseek_json_parse_failed error=%s raw_ai_response=%s",
                    repr(parse_err),
                    raw,
                )
                parsed = {}

            normalized = normalize_report_json(parsed, schools_json, selected_dimensions)
            logger.info("deepseek_raw_response attempt=%s content=%s", attempt, raw)
            return settings.deepseek_model, normalized, raw
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started) * 1000
            last_error = exc
            logger.warning(
                "deepseek_call failed attempt=%s elapsed_ms=%.2f prompt_tokens=%s completion_tokens=%s total_tokens=%s error=%s",
                attempt,
                elapsed_ms,
                "n/a",
                "n/a",
                "n/a",
                repr(exc),
            )
            if attempt < 3:
                await asyncio.sleep(2)

    raise RuntimeError(f"DeepSeek调用失败（已重试3次）: {last_error}")
