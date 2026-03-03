from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Dict, List, Tuple

import httpx

from ..config import get_settings
from .query_schema import query_schema_prompt_text

logger = logging.getLogger(__name__)
DISCLAIMER = "本报告由AI基于公开数据生成，仅供参考，不构成录取、就业或移民保证，请结合最新官方信息决策。"


def build_prompt(
    country: str,
    major: str,
    budget_max: float,
    selected_dimensions: List[str],
    weights: Dict[str, int],
    schools_json: List[Dict],
) -> str:
    primary = selected_dimensions[0] if selected_dimensions else "就业薪资"
    dimensions = "、".join(selected_dimensions) if selected_dimensions else "就业薪资"
    weights_text = "\n".join([f"{k}：{v}分" for k, v in weights.items()])
    selected_names = "\n".join(
        [f"- {x['school_name']} · {x['program_name']}" for x in schools_json]
    )
    query_schema_text = query_schema_prompt_text()

    return f"""你是专注{country} {major}硕士留学的专业规划师，以{primary}为核心评估标准。

【用户背景】
专业方向：{major}
预算上限：${budget_max:,.0f} USD
最关注的问题（按优先级排序）：{dimensions}

【权重配置（总分100分，你需要按此权重给每所学校打分）】
{weights_text}

【参考数据（来自数据库，可作为评分依据，但你可以结合自己的知识补充）】
{json.dumps(schools_json, ensure_ascii=False, indent=2)}

【评分规则】
- 对每所学校的每个维度，由你独立评估打分（0-100分）
- 维度得分 × 权重/100 = 该维度加权分
- 所有维度加权分之和 = fit_score（总分，0-100）
- 数据库字段为0或null时，基于你的知识估算，并在evidence_used中标注"估算"
- 不要机械套用数据库数字，要结合实际就业市场判断
- 对于签证政策不适用场景必须明确填"-"（例如澳洲项目的OPT/H1B字段）

【标准化查询输出字段（所有学校都必须输出，缺失或不适用填"-"）】
{query_schema_text}

【严格只评估以下学校，不评估清单外的学校】
{selected_names}

【输出要求】
直接输出合法JSON，从{{开始到}}结束，不要有任何markdown、代码块或前缀文字。

JSON结构如下：
{{
  "executive_summary": "150字以上整体概述，说明这几所学校的核心差异和择校逻辑",
  
  "comprehensive_ranking": [
    {{
      "rank": 1,
      "school_name": "学校英文全名",
      "program_name": "项目名",
      "fit_score": 82,
      "score_breakdown": {{
        "就业薪资": 85,
        "学校排名": 90,
        "区域优势": 75,
        "课程适配": 80,
        "成本控制": 60,
        "工签支持": 70,
        "校友网络": 65,
        "H1B绿卡": 72
      }}
    }}
  ],
  
  "school_assessments": [
    {{
      "school_name": "学校英文全名",
      "program_name": "项目名",
      "fit_score": 82,
      "total_cost": "学费+生活费总计，如$8.0万/约57万人民币",
      
      "pros": [
        "亮点一：完整的一句话，包含具体数据，50字以上。例：CMU MSCS毕业生在FAANG就业率约40%，起薪中位数$145K，远超行业均值$110K，投资回报期约2年",
        "亮点二：...",
        "亮点三：..."
      ],
      
      "cons": [
        "短板一：完整的一句话，40字以上，说明具体影响。例：Pittsburgh本地科技岗位极少，需主动异地投递，对社交能力要求高",
        "短板二：..."
      ],
      
      "concern_analysis": {{
        "{primary}": "针对用户最关注维度的深度分析，100字以上，包含具体数据和就业路径",
        {chr(10).join([f'"{dim}": "针对{dim}的具体分析，80字以上"' for dim in selected_dimensions[1:3]])}
      }},
      
      "experience": "就读体验80字以上：课程强度如何、华人比例大概多少、所在城市生活感受、租房成本大概范围",
      
      "recommended_actions": [
        "行动建议一：具体可执行，如'建议提前准备系统设计面试，CMU校招集中在秋招9-11月'",
        "行动建议二：...",
        "行动建议三：..."
      ],

      "query_output": {{
        "country": "目标国家/地区",
        "school_name_en": "学校英文全称",
        "program_name": "项目全称",
        "degree_type": "学位类型",
        "duration_months": "项目时长(月)",
        "post_study_work": "毕业工签名称与年限",
        "pr_pathway": "PR路径评估",
        "stem_eligible": "-",
        "h1b_sponsor_rate_pct": "-",
        "au_485_years": "-",
        "ca_pgwp_eligible": "-",
        "hk_iang_eligible": "-",
        "sg_ep_difficulty": "-",
        "policy_last_checked": "YYYY-MM-DD"
      }},
      
      "evidence_used": ["列出你用到的数据字段或标注'估算'的项目"]
    }}
  ],
  
  "final_recommendation": "200字以上。格式：首选[学校]，理由是...（2-3句具体说明）；备选[学校]，适合...（1-2句）；如预算有限选[学校]，原因是...（1-2句）。最后一句给出时间敏感的行动建议。",
  
  "disclaimer": "{DISCLAIMER}"
}}

【内容质量要求】
- 亮点必须有具体数字（薪资、就业率、排名等），不接受"就业支持强"这种空话
- 短板必须说明对用户的实际影响，不接受"成本较高"这种废话
- concern_analysis必须针对用户选的{dimensions}深度展开
- 如果数据库某字段为0或缺失，结合行业知识估算，在evidence_used中标注(估算)
- query_output 必须包含完整字段清单中的所有key；不确定或不适用统一填"-"
"""


async def generate_analysis(prompt: str) -> Tuple[str, str]:
    settings = get_settings()
    if not settings.deepseek_api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 未配置，无法生成AI分析")

    url = f"{settings.deepseek_api_base.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.deepseek_model,
        "messages": [
            {"role": "system", "content": "你是留学择校分析助手，必须严格基于提供的数据。"},
            {"role": "user", "content": prompt},
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

            data = resp.json()
            usage = data.get("usage") or {}
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")

            content = data["choices"][0]["message"]["content"]
            if not content or not str(content).strip():
                raise RuntimeError("DeepSeek 返回空内容")

            logger.info(
                "deepseek_call success attempt=%s elapsed_ms=%.2f prompt_tokens=%s completion_tokens=%s total_tokens=%s",
                attempt,
                elapsed_ms,
                prompt_tokens,
                completion_tokens,
                total_tokens,
            )
            return settings.deepseek_model, content
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
