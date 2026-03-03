from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)

BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
SERPER_ENDPOINT = "https://google.serper.dev/search"
TAVILY_ENDPOINT = "https://api.tavily.com/search"
DUCKDUCKGO_HTML_ENDPOINT = "https://html.duckduckgo.com/html/"


def _to_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_provider(provider: str) -> str:
    p = _to_text(provider).lower()
    return p if p in {"serper", "tavily", "bing", "duckduckgo", "auto"} else "auto"


def _provider_order() -> List[str]:
    settings = get_settings()
    p = _normalize_provider(settings.search_provider)
    if p == "auto":
        return ["serper", "tavily", "bing", "duckduckgo"]
    return [p]


def _provider_has_key(provider: str) -> bool:
    settings = get_settings()
    if provider == "duckduckgo":
        return True
    if provider == "serper":
        return bool(_to_text(settings.serper_api_key))
    if provider == "tavily":
        return bool(_to_text(settings.tavily_api_key))
    if provider == "bing":
        return bool(_to_text(settings.bing_api_key))
    return False


def web_search_enabled() -> bool:
    return any(_provider_has_key(p) for p in _provider_order())


def preferred_search_provider() -> str:
    for p in _provider_order():
        if _provider_has_key(p):
            return p
    return "none"


async def _search_serper(query: str, count: int, mkt: str) -> List[Dict[str, str]]:
    settings = get_settings()
    api_key = _to_text(settings.serper_api_key)
    if not api_key:
        return []

    gl = "us"
    hl = "en"
    if mkt.lower().startswith("zh"):
        gl = "cn"
        hl = "zh-cn"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                SERPER_ENDPOINT,
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                json={"q": query, "num": count, "gl": gl, "hl": hl},
            )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("serper_search_failed query=%s error=%s", query, repr(exc))
        return []

    rows: List[Dict[str, str]] = []
    for item in data.get("organic", []):
        rows.append(
            {
                "provider": "serper",
                "query": query,
                "title": _to_text(item.get("title")),
                "url": _to_text(item.get("link")),
                "snippet": _to_text(item.get("snippet")),
            }
        )
    return rows


async def _search_tavily(query: str, count: int, _: str) -> List[Dict[str, str]]:
    settings = get_settings()
    api_key = _to_text(settings.tavily_api_key)
    if not api_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                TAVILY_ENDPOINT,
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": count,
                    "search_depth": "basic",
                    "include_raw_content": False,
                },
            )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("tavily_search_failed query=%s error=%s", query, repr(exc))
        return []

    rows: List[Dict[str, str]] = []
    for item in data.get("results", []):
        rows.append(
            {
                "provider": "tavily",
                "query": query,
                "title": _to_text(item.get("title")),
                "url": _to_text(item.get("url")),
                "snippet": _to_text(item.get("content")),
            }
        )
    return rows


async def _search_bing(query: str, count: int, mkt: str) -> List[Dict[str, str]]:
    settings = get_settings()
    api_key = _to_text(settings.bing_api_key)
    if not api_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                BING_ENDPOINT,
                headers={"Ocp-Apim-Subscription-Key": api_key},
                params={"q": query, "count": count, "mkt": mkt},
            )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("bing_search_failed query=%s error=%s", query, repr(exc))
        return []

    rows: List[Dict[str, str]] = []
    for item in data.get("webPages", {}).get("value", []):
        rows.append(
            {
                "provider": "bing",
                "query": query,
                "title": _to_text(item.get("name")),
                "url": _to_text(item.get("url")),
                "snippet": _to_text(item.get("snippet")),
            }
        )
    return rows


def _strip_html(text: str) -> str:
    import re

    value = re.sub(r"<[^>]+>", " ", text or "")
    value = value.replace("&nbsp;", " ").replace("&amp;", "&")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


async def _search_duckduckgo(query: str, count: int, _: str) -> List[Dict[str, str]]:
    import re
    from urllib.parse import parse_qs, unquote, urlparse

    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(
                DUCKDUCKGO_HTML_ENDPOINT,
                params={"q": query},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
                    )
                },
            )
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        logger.warning("duckduckgo_search_failed query=%s error=%s", query, repr(exc))
        return []

    rows: List[Dict[str, str]] = []
    result_pattern = re.compile(
        r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    snippet_pattern = re.compile(
        r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
        flags=re.IGNORECASE | re.DOTALL,
    )

    links = list(result_pattern.finditer(html))
    snippets = [m.group(1) for m in snippet_pattern.finditer(html)]
    for idx, match in enumerate(links[:count]):
        raw_url = _to_text(match.group(1))
        parsed = urlparse(raw_url)
        if parsed.path == "/l/" and parsed.query:
            q = parse_qs(parsed.query).get("uddg", [""])[0]
            url = unquote(q) if q else raw_url
        else:
            url = raw_url

        rows.append(
            {
                "provider": "duckduckgo",
                "query": query,
                "title": _strip_html(match.group(2)),
                "url": url,
                "snippet": _strip_html(snippets[idx]) if idx < len(snippets) else "",
            }
        )
    return rows


async def search_web(query: str, count: int = 5, mkt: str = "zh-CN") -> List[Dict[str, str]]:
    for provider in _provider_order():
        rows: List[Dict[str, str]] = []
        if provider == "serper":
            rows = await _search_serper(query, count, mkt)
        elif provider == "tavily":
            rows = await _search_tavily(query, count, mkt)
        elif provider == "bing":
            rows = await _search_bing(query, count, mkt)
        elif provider == "duckduckgo":
            rows = await _search_duckduckgo(query, count, mkt)
        if rows:
            return rows
    return []


async def _search_school_items(
    school_name: str,
    program_name: str,
    _: str = "",
) -> List[Dict[str, str]]:
    queries = [
        f"{school_name} {program_name} student experience reddit",
        f"{school_name} 就读体验 留学",
    ]
    items: List[Dict[str, str]] = []
    for q in queries:
        rows = await search_web(q, count=3, mkt="zh-CN")
        for item in rows:
            snippet = _to_text(item.get("snippet"))
            if not snippet:
                continue
            items.append(
                {
                    "provider": _to_text(item.get("provider")) or preferred_search_provider(),
                    "query": q,
                    "title": _to_text(item.get("title")),
                    "url": _to_text(item.get("url")),
                    "snippet": snippet,
                }
            )
    return items


async def search_school_experience(
    school_name: str,
    program_name: str,
    api_key: str = "",
) -> str:
    items = await _search_school_items(school_name, program_name, api_key)
    snippets = [x.get("snippet", "") for x in items if x.get("snippet", "")]
    return "\n".join(snippets[:5]) if snippets else ""


async def batch_search_schools(
    schools: List[dict],
    api_key: str = "",
) -> dict:
    valid_schools = [s for s in schools if isinstance(s, dict) and s.get("school_name")]
    tasks = {
        s["school_name"]: search_school_experience(
            s["school_name"], s.get("program_name", ""), api_key
        )
        for s in valid_schools
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    return {
        name: (r if isinstance(r, str) else "")
        for name, r in zip(tasks.keys(), results)
    }


async def batch_search_school_records(
    schools: List[dict],
    api_key: str = "",
) -> List[dict]:
    valid_schools = [s for s in schools if isinstance(s, dict) and s.get("school_name")]
    tasks = [
        _search_school_items(s["school_name"], s.get("program_name", ""), api_key)
        for s in valid_schools
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    records: List[dict] = []
    for school, result in zip(valid_schools, results):
        items = result if isinstance(result, list) else []
        snippets = [x.get("snippet", "") for x in items if isinstance(x, dict) and x.get("snippet")]
        summary_text = "\n".join(snippets[:5]) if snippets else ""
        provider = _to_text(items[0].get("provider")) if items else preferred_search_provider()
        records.append(
            {
                "school_id": school.get("id"),
                "school_name": school.get("school_name", ""),
                "program_name": school.get("program_name", ""),
                "provider": provider or "web-search",
                "summary_text": summary_text,
                "items": items,
            }
        )
    return records
