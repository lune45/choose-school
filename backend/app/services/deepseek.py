from __future__ import annotations

import json
from typing import Dict, List, Tuple

import httpx

from ..config import get_settings

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
    selected_names = "\n".join([f"- {x['school_name']} · {x['program_name']}" for x in schools_json])

    return f"""你是专注{country} {major}硕士留学的专业规划师，以{primary}为核心评估标准。

【用户背景】
专业方向：{major}
预算上限：{budget_max}
最关注的问题：{dimensions}

【权重配置（总分100）】
{weights_text}

【各校数据（来自数据库，以此为准，不要使用训练数据）】
{json.dumps(schools_json, ensure_ascii=False, indent=2)}

【严格只评估以下清单，不评估清单外的学校】
{selected_names}

【输出格式】
一、综合排名表
| 排名 | 院校 | 项目 | 总分 | 就业薪资 | 排名 | 区域 | 课程 | 成本 | 工签 | 校友 | H1B |

二、逐校精简评估（每校150字以内）
格式：
**{{学校名}}·{{项目名}}**
亮点：...
短板：...
总成本：$XX万/人民币XX万
就业前景：...

三、最终择校建议
直接给出结论，不要模棱两可。
格式：首选{{学校}}，理由是...；备选{{学校}}，适合...；如预算有限选{{学校}}。

【规则】
- 所有数据以【各校数据】中提供的为准，数据库没有的字段才可用行业经验估算，并标注(估算)
- 量化打分，不空谈排名
- 优先就业回报率
- 末尾固定输出免责声明：{DISCLAIMER}
"""


async def generate_analysis(prompt: str) -> Tuple[str, str]:
    settings = get_settings()
    if not settings.deepseek_api_key:
        return "rule-based", "未配置DEEPSEEK_API_KEY，已使用规则评分结果。"

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

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return settings.deepseek_model, content
    except Exception as exc:
        return "rule-based", f"DeepSeek调用失败，已使用规则评分。错误摘要: {exc}"
