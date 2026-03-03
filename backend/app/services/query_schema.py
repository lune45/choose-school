from __future__ import annotations

import json
import re
from datetime import date
from typing import Any, Dict, List


QUERY_OUTPUT_SCHEMA: List[Dict[str, Any]] = [
    {
        "group": "🏫 基础标识",
        "fields": [
            {"key": "country", "label": "目标国家/地区"},
            {"key": "region_group", "label": "地区分组"},
            {"key": "school_name_en", "label": "学校英文全称"},
            {"key": "school_name_cn", "label": "学校中文常用名"},
            {"key": "school_abbr", "label": "学校缩写"},
            {"key": "program_name", "label": "项目全称"},
            {"key": "major_category", "label": "专业大类"},
            {"key": "major_sub", "label": "专业细分"},
            {"key": "degree_type", "label": "学位类型"},
            {"key": "duration_months", "label": "项目时长(月)"},
            {"key": "city", "label": "授课城市"},
            {"key": "campus_region", "label": "校园区域/就业圈"},
            {"key": "teaching_language", "label": "教学语言"},
            {"key": "intake_season", "label": "入学季"},
            {"key": "program_size", "label": "每届招生人数"},
            {"key": "is_online_option", "label": "在线/混合模式"},
        ],
    },
    {
        "group": "💰 成本",
        "fields": [
            {"key": "tuition_total_usd", "label": "总学费(USD)"},
            {"key": "tuition_local", "label": "总学费(本地货币)"},
            {"key": "tuition_currency", "label": "本地货币"},
            {"key": "tuition_cny_est", "label": "总学费(CNY估算)"},
            {"key": "living_cost_annual_usd", "label": "年均生活费(USD)"},
            {"key": "living_cost_local", "label": "年均生活费(本地货币)"},
            {"key": "scholarship_info", "label": "奖学金/助学金"},
            {"key": "app_fee_usd", "label": "申请费(USD)"},
            {"key": "deposit_usd", "label": "录取押金(USD估算)"},
            {"key": "roi_notes", "label": "性价比备注"},
        ],
    },
    {
        "group": "📊 排名",
        "fields": [
            {"key": "qs_world_rank", "label": "QS世界综合排名"},
            {"key": "qs_subject_rank", "label": "QS专业排名"},
            {"key": "the_rank", "label": "THE排名"},
            {"key": "arwu_rank", "label": "ARWU排名"},
            {"key": "local_rank", "label": "本地排名"},
            {"key": "china_brand_tier", "label": "国内品牌档次"},
            {"key": "prestigious_group", "label": "知名校群"},
        ],
    },
    {
        "group": "💼 就业&薪资",
        "fields": [
            {"key": "employment_rate_pct", "label": "就业率%"},
            {"key": "median_salary_local", "label": "起薪中位数(本币)"},
            {"key": "median_salary_usd", "label": "起薪中位数(USD)"},
            {"key": "top_employers", "label": "主要雇主"},
            {"key": "big_tech_rate_pct", "label": "顶级雇主概率%"},
            {"key": "local_job_market", "label": "当地就业市场"},
            {"key": "returnee_job_prospect", "label": "回国就业前景"},
            {"key": "industry_focus", "label": "主要就业行业"},
        ],
    },
    {
        "group": "🛂 签证&移民",
        "fields": [
            {"key": "post_study_work", "label": "毕业后工作签证"},
            {"key": "pr_pathway", "label": "永居/长居路径"},
            {"key": "pr_difficulty", "label": "PR难度"},
            {"key": "visa_notes", "label": "签证备注"},
            {"key": "stem_eligible", "label": "STEM认证(美国)"},
            {"key": "h1b_sponsor_rate_pct", "label": "H1B Sponsor率%(美国)"},
            {"key": "au_485_years", "label": "485年限(澳洲)"},
            {"key": "au_occupation_list", "label": "紧缺职业清单(澳洲)"},
            {"key": "au_state_nomination", "label": "州担保(澳洲)"},
            {"key": "ca_pgwp_eligible", "label": "PGWP(加拿大)"},
            {"key": "hk_iang_eligible", "label": "IANG(香港)"},
            {"key": "sg_ep_difficulty", "label": "EP难度(新加坡)"},
            {"key": "partner_visa", "label": "配偶/家属签证"},
            {"key": "policy_last_checked", "label": "签证政策核查日期"},
        ],
    },
    {
        "group": "📚 课程&学业",
        "fields": [
            {"key": "focus_tags", "label": "方向标签"},
            {"key": "course_flexibility", "label": "选课灵活度"},
            {"key": "has_internship", "label": "是否有实习学期"},
            {"key": "has_coop", "label": "是否有Co-op"},
            {"key": "workload_level", "label": "课业压力"},
            {"key": "language_barrier", "label": "语言障碍"},
            {"key": "local_language_required", "label": "当地语言要求"},
            {"key": "english_req_ielts", "label": "雅思要求"},
            {"key": "admission_difficulty", "label": "录取难度"},
            {"key": "gpa_req", "label": "GPA要求"},
            {"key": "has_capstone", "label": "毕业项目/论文"},
        ],
    },
    {
        "group": "🏙️ 生活&安全",
        "fields": [
            {"key": "safety_rating", "label": "安全评级"},
            {"key": "chinese_community", "label": "华人社区规模"},
            {"key": "weather_note", "label": "气候"},
            {"key": "transport_rating", "label": "公共交通"},
            {"key": "fun_rating", "label": "生活丰富度"},
            {"key": "food_cn_friendly", "label": "中餐便利度"},
            {"key": "racism_concern", "label": "歧视风险"},
            {"key": "timezone_cn_diff", "label": "与北京时间差"},
        ],
    },
    {
        "group": "🇨🇳 回国认可",
        "fields": [
            {"key": "china_recognition", "label": "回国认可度"},
            {"key": "留服认证难度", "label": "留服认证难度"},
            {"key": "returnee_salary_premium", "label": "归国薪资溢价"},
            {"key": "popular_with_cn_employers", "label": "国内雇主认知"},
        ],
    },
    {
        "group": "🔗 数据维护",
        "fields": [
            {"key": "alumni_network", "label": "校友网络"},
            {"key": "career_service", "label": "就业服务评分"},
            {"key": "data_confidence", "label": "数据置信度"},
            {"key": "data_sources", "label": "数据来源"},
            {"key": "last_updated", "label": "最后更新"},
            {"key": "curator_notes", "label": "录入备注"},
        ],
    },
]

NULL_LIKE_VALUES = {"", "0", "0.0", "none", "null", "n/a", "nan"}


COUNTRY_SPECIFIC_KEYS: Dict[str, set[str]] = {
    "美国": {"stem_eligible", "h1b_sponsor_rate_pct"},
    "澳洲": {"au_485_years", "au_occupation_list", "au_state_nomination"},
    "加拿大": {"ca_pgwp_eligible"},
    "香港": {"hk_iang_eligible"},
    "新加坡": {"sg_ep_difficulty"},
    "美国/加拿大": {"has_coop"},
    "日本/韩国/德国": {"language_barrier"},
}


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        text = str(value).strip().replace(",", "")
        if not text:
            return 0.0
        return float(text)
    except Exception:
        return 0.0


def _fmt_number(value: Any) -> str:
    number = _to_float(value)
    if number <= 0:
        return "-"
    if abs(number - round(number)) < 1e-9:
        return str(int(round(number)))
    return f"{number:.2f}".rstrip("0").rstrip(".")


def _level_3(value: Any) -> str:
    score = _to_float(value)
    if score <= 0:
        return "-"
    if score >= 80:
        return "高"
    if score >= 60:
        return "中"
    return "低"


def _difficulty_level(value: Any) -> str:
    score = _to_float(value)
    if score <= 0:
        return "-"
    if score >= 8:
        return "高"
    if score >= 5:
        return "中"
    return "低"


def _brand_tier(value: Any) -> str:
    score = _to_float(value)
    if score <= 0:
        return "-"
    if score >= 90:
        return "S"
    if score >= 80:
        return "A"
    if score >= 65:
        return "B"
    return "C"


def _extract_notes_json(program: Dict[str, Any]) -> Dict[str, Any]:
    notes = _to_text(program.get("notes"))
    if not notes:
        return {}
    if notes.startswith("{") and notes.endswith("}"):
        try:
            parsed = json.loads(notes)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def _extract_first_url(text: str) -> str:
    found = re.findall(r"https?://[^\s]+", text or "")
    return found[0] if found else "-"


def _abbr_from_school(name: str) -> str:
    text = _to_text(name)
    if not text:
        return "-"
    candidates = re.findall(r"[A-Z][A-Za-z]*", text)
    if len(candidates) >= 2:
        abbr = "".join(x[0] for x in candidates if x)
        return abbr[:8] if abbr else "-"
    words = [w for w in re.split(r"\s+", text) if w]
    if len(words) >= 2:
        return "".join(w[0].upper() for w in words if w)[:8]
    return text[:8]


def _region_group(country: str) -> str:
    c = _to_text(country)
    if c in {"美国", "英国", "澳洲", "加拿大", "新加坡", "香港"}:
        return "英语国家"
    if c in {"日本", "韩国", "香港", "新加坡"}:
        return "亚洲"
    if c in {"德国", "法国", "荷兰", "瑞典", "丹麦", "瑞士"}:
        return "欧洲"
    return "-"


def query_schema_prompt_text() -> str:
    lines: List[str] = []
    for group in QUERY_OUTPUT_SCHEMA:
        group_name = _to_text(group.get("group")) or "字段"
        lines.append(f"- {group_name}")
        for field in group.get("fields", []):
            key = _to_text(field.get("key"))
            label = _to_text(field.get("label"))
            if key:
                lines.append(f"  - {key}: {label}")
    return "\n".join(lines)


def get_query_output_schema() -> List[Dict[str, Any]]:
    return QUERY_OUTPUT_SCHEMA


def get_query_output_keys() -> List[str]:
    return [
        _to_text(field.get("key"))
        for group in QUERY_OUTPUT_SCHEMA
        for field in group.get("fields", [])
        if _to_text(field.get("key"))
    ]


def get_query_output_label_map() -> Dict[str, str]:
    return {
        _to_text(field.get("key")): _to_text(field.get("label"))
        for group in QUERY_OUTPUT_SCHEMA
        for field in group.get("fields", [])
        if _to_text(field.get("key"))
    }


def enforce_country_specific_dash(query_output: Dict[str, str]) -> Dict[str, str]:
    country = _to_text(query_output.get("country"))
    normalized = dict(query_output)
    if country != "美国":
        for key in COUNTRY_SPECIFIC_KEYS["美国"]:
            normalized[key] = "-"
    if country != "澳洲":
        for key in COUNTRY_SPECIFIC_KEYS["澳洲"]:
            normalized[key] = "-"
    if country != "加拿大":
        for key in COUNTRY_SPECIFIC_KEYS["加拿大"]:
            normalized[key] = "-"
    if country != "香港":
        for key in COUNTRY_SPECIFIC_KEYS["香港"]:
            normalized[key] = "-"
    if country != "新加坡":
        for key in COUNTRY_SPECIFIC_KEYS["新加坡"]:
            normalized[key] = "-"
    if country not in {"美国", "加拿大"}:
        for key in COUNTRY_SPECIFIC_KEYS["美国/加拿大"]:
            normalized[key] = "-"
    if country not in {"日本", "韩国", "德国"}:
        for key in COUNTRY_SPECIFIC_KEYS["日本/韩国/德国"]:
            normalized[key] = "-"
    return normalized


def compose_query_output(program: Dict[str, Any], existing: Dict[str, Any] | None = None) -> Dict[str, str]:
    base = build_query_output_for_program(program)
    keys = get_query_output_keys()
    existing_data = existing if isinstance(existing, dict) else {}

    for key in keys:
        if key not in existing_data:
            continue
        text = _to_text(existing_data.get(key))
        if text.lower() in NULL_LIKE_VALUES:
            base[key] = "-"
        else:
            base[key] = text

    # country 以主数据为准，避免已有脏值破坏国别字段约束。
    country = _to_text(program.get("country"))
    if country:
        base["country"] = country

    for key in keys:
        text = _to_text(base.get(key))
        if text.lower() in NULL_LIKE_VALUES:
            base[key] = "-"

    base = enforce_country_specific_dash(base)
    if _to_text(base.get("last_updated")) in {"", "-"}:
        base["last_updated"] = date.today().isoformat()
    return base


def build_query_output_for_program(program: Dict[str, Any]) -> Dict[str, str]:
    country = _to_text(program.get("country")) or "-"
    notes = _to_text(program.get("notes"))
    notes_json = _extract_notes_json(program)

    query_output: Dict[str, str] = {}
    for group in QUERY_OUTPUT_SCHEMA:
        for field in group.get("fields", []):
            key = _to_text(field.get("key"))
            if key:
                query_output[key] = "-"

    tuition_usd = _to_float(program.get("tuition_usd"))
    living_usd = _to_float(program.get("living_cost_usd"))
    salary_usd = _to_float(program.get("median_salary_usd"))

    query_output.update(
        {
            "country": country,
            "region_group": _region_group(country),
            "school_name_en": _to_text(program.get("school_name")) or "-",
            "school_name_cn": "-",
            "school_abbr": _abbr_from_school(_to_text(program.get("school_name"))),
            "program_name": _to_text(program.get("program_name")) or "-",
            "major_category": _to_text(program.get("major_track")) or "-",
            "major_sub": _to_text(program.get("major_track")) or "-",
            "degree_type": _to_text(program.get("degree")) or "-",
            "duration_months": _fmt_number(program.get("program_duration_months")),
            "city": "-",
            "campus_region": "-",
            "teaching_language": "英语" if country in {"美国", "英国", "澳洲", "加拿大", "香港", "新加坡"} else "-",
            "intake_season": "-",
            "program_size": "-",
            "is_online_option": "-",
            "tuition_total_usd": _fmt_number(tuition_usd),
            "tuition_local": _fmt_number(tuition_usd),
            "tuition_currency": "USD",
            "tuition_cny_est": _fmt_number(tuition_usd * 7.2) if tuition_usd > 0 else "-",
            "living_cost_annual_usd": _fmt_number(living_usd),
            "living_cost_local": _fmt_number(living_usd),
            "scholarship_info": "-",
            "app_fee_usd": "-",
            "deposit_usd": "-",
            "roi_notes": _to_text(program.get("notes"))[:120] or "-",
            "qs_world_rank": _fmt_number(program.get("qs_rank")),
            "qs_subject_rank": _fmt_number(program.get("qs_rank")),
            "the_rank": _fmt_number(program.get("times_rank")),
            "arwu_rank": "-",
            "local_rank": _fmt_number(program.get("usnews_rank")) if _to_float(program.get("usnews_rank")) > 0 else "-",
            "china_brand_tier": _brand_tier(program.get("domestic_recognition")),
            "prestigious_group": "-",
            "employment_rate_pct": "-",
            "median_salary_local": _fmt_number(salary_usd),
            "median_salary_usd": _fmt_number(salary_usd),
            "top_employers": "-",
            "big_tech_rate_pct": "-",
            "local_job_market": "-",
            "returnee_job_prospect": _level_3(program.get("domestic_recognition")),
            "industry_focus": _to_text(program.get("major_track")) or "-",
            "post_study_work": "-",
            "pr_pathway": "-",
            "pr_difficulty": "-",
            "visa_notes": "-",
            "partner_visa": "-",
            "policy_last_checked": "-",
            "focus_tags": _to_text(program.get("major_track")) or "-",
            "course_flexibility": "-",
            "has_internship": "-",
            "has_coop": "-",
            "workload_level": _difficulty_level(program.get("course_difficulty")),
            "language_barrier": "-",
            "local_language_required": "-",
            "english_req_ielts": "-",
            "admission_difficulty": "-",
            "gpa_req": "-",
            "has_capstone": "-",
            "safety_rating": _level_3(program.get("safety_score")),
            "chinese_community": "-",
            "weather_note": "-",
            "transport_rating": "-",
            "fun_rating": "-",
            "food_cn_friendly": "-",
            "racism_concern": "-",
            "timezone_cn_diff": "-",
            "china_recognition": _level_3(program.get("domestic_recognition")),
            "留服认证难度": "-",
            "returnee_salary_premium": "-",
            "popular_with_cn_employers": "-",
            "alumni_network": _level_3(program.get("alumni_network")),
            "career_service": _fmt_number(round(_to_float(program.get("employment_support")) / 20.0, 1)),
            "data_confidence": "估算",
            "data_sources": _extract_first_url(notes),
            "last_updated": "-",
            "curator_notes": notes[:120] if notes else "-",
        }
    )

    # 基于国家填充少量签证字段默认值
    if country == "美国":
        query_output["post_study_work"] = "OPT 1-3年"
        query_output["pr_pathway"] = "H1B抽签→绿卡"
        query_output["pr_difficulty"] = "极高"
        query_output["visa_notes"] = "H1B抽签与雇主担保"
        query_output["stem_eligible"] = "-"
        query_output["h1b_sponsor_rate_pct"] = _fmt_number(program.get("visa_support"))
    elif country == "澳洲":
        query_output["post_study_work"] = "485 2-4年"
        query_output["pr_pathway"] = "积分制+州担保"
        query_output["pr_difficulty"] = "中"
        query_output["visa_notes"] = "关注SOL职业清单"
        query_output["au_485_years"] = "-"
        query_output["au_occupation_list"] = "-"
        query_output["au_state_nomination"] = "-"
        query_output["tuition_currency"] = "AUD"
    elif country == "加拿大":
        query_output["post_study_work"] = "PGWP 最长3年"
        query_output["pr_pathway"] = "Express Entry"
        query_output["ca_pgwp_eligible"] = "-"
    elif country == "香港":
        query_output["post_study_work"] = "IANG"
        query_output["hk_iang_eligible"] = "-"
    elif country == "新加坡":
        query_output["post_study_work"] = "EP/S Pass"
        query_output["sg_ep_difficulty"] = "-"

    # notes 中可用json覆盖字段
    for k, v in notes_json.items():
        key = _to_text(k)
        if key and key in query_output:
            query_output[key] = _to_text(v) or "-"

    # 统一缺失值为 "-"
    for key, value in list(query_output.items()):
        text = _to_text(value)
        if text.lower() in NULL_LIKE_VALUES:
            query_output[key] = "-"

    # 强制国家不适用字段为 "-"
    query_output = enforce_country_specific_dash(query_output)

    # 若整体信息不足，标记低置信度；否则中置信度。
    known = sum(1 for v in query_output.values() if _to_text(v) and _to_text(v) != "-")
    query_output["data_confidence"] = "中" if known >= 20 else "低"
    query_output["last_updated"] = date.today().isoformat()
    return query_output
