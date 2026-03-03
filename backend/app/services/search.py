import asyncio
from typing import List

import httpx

BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"


async def search_school_experience(
    school_name: str,
    program_name: str,
    bing_api_key: str,
) -> str:
    """搜索学校就读体验，返回摘要文本"""
    queries = [
        f"{school_name} {program_name} student experience reddit",
        f"{school_name} 就读体验 留学",
    ]
    snippets: List[str] = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for q in queries:
            try:
                resp = await client.get(
                    BING_ENDPOINT,
                    headers={"Ocp-Apim-Subscription-Key": bing_api_key},
                    params={"q": q, "count": 3, "mkt": "zh-CN"},
                )
                data = resp.json()
                for item in data.get("webPages", {}).get("value", []):
                    snippet = item.get("snippet", "")
                    if snippet:
                        snippets.append(snippet)
            except Exception:
                pass
    return "\n".join(snippets[:5]) if snippets else ""


async def batch_search_schools(
    schools: List[dict],
    bing_api_key: str,
) -> dict:
    """并发搜索所有学校，返回 {school_name: experience_text}"""
    valid_schools = [s for s in schools if isinstance(s, dict) and s.get("school_name")]
    tasks = {
        s["school_name"]: search_school_experience(
            s["school_name"], s.get("program_name", ""), bing_api_key
        )
        for s in valid_schools
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return {
        name: (r if isinstance(r, str) else "")
        for name, r in zip(tasks.keys(), results)
    }
