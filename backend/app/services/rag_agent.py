from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import SchoolProgram, SchoolSearchInsight
from .search import preferred_search_provider, search_web, web_search_enabled

logger = logging.getLogger(__name__)

MEMORY_FILE = Path(__file__).resolve().parents[3] / "memory.md"
MEMORY_STATE_START = "<!-- MEMORY_STATE_START -->"
MEMORY_STATE_END = "<!-- MEMORY_STATE_END -->"


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_memory(today: str) -> Dict[str, Any]:
    return {
        "identity": "数据库检索员",
        "long_term_instruction": "优先抓取官网可验证信息，补全项目时长与选课清单，保留来源链接，无法确定则标注估算。",
        "ranking_sources": ["qs", "usnews", "times"],
        "priority_targets": [],
        "today": today,
        "todo": [],
        "done": [],
        "logs": [],
        "retry_queue": [],
        "failure_history": [],
    }


def _render_memory_md(memory: Dict[str, Any]) -> str:
    today = memory.get("today") or _today()
    identity = _to_text(memory.get("identity")) or "数据库检索员"
    long_term_instruction = _to_text(memory.get("long_term_instruction")) or "-"
    ranking_sources = [x for x in memory.get("ranking_sources", []) if _to_text(x)]
    priority_targets = [x for x in memory.get("priority_targets", []) if _to_text(x)]
    todo = memory.get("todo") or []
    done = memory.get("done") or []
    logs = memory.get("logs") or []
    retry_queue = memory.get("retry_queue") or []
    failure_history = memory.get("failure_history") or []

    ranking_text = " > ".join([_to_text(x).upper() for x in ranking_sources]) if ranking_sources else "-"
    priority_lines = "\n".join([f"- {x}" for x in priority_targets]) if priority_targets else "- 暂无"
    todo_lines = "\n".join([f"- {x}" for x in todo]) if todo else "- 暂无"
    done_lines = "\n".join([f"- {x}" for x in done]) if done else "- 暂无"
    log_lines = "\n".join([f"- {x}" for x in logs]) if logs else "- 暂无"
    retry_lines = (
        "\n".join(
            [
                f"- {x.get('target','?')} | 次数:{x.get('attempts',0)} | 下次:{x.get('next_retry_at','-')} | 原因:{x.get('last_reason','-')}"
                for x in retry_queue
            ]
        )
        if retry_queue
        else "- 暂无"
    )
    failure_lines = (
        "\n".join(
            [
                f"- {x.get('time','-')} | {x.get('target','?')} | {x.get('reason','-')}"
                for x in failure_history[-20:]
            ]
        )
        if failure_history
        else "- 暂无"
    )
    state_block = json.dumps(memory, ensure_ascii=False, indent=2)

    return (
        "# 数据库检索员记忆\n\n"
        f"身份：{identity}（负责联网检索学校/项目信息并提交管理员审批）\n\n"
        f"最后更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"## 长期记忆策略\n- 指令：{long_term_instruction}\n- 排名来源优先级：{ranking_text}\n\n"
        f"## 长期优先目标\n{priority_lines}\n\n"
        f"## 今日待搜（{today}）\n{todo_lines}\n\n"
        f"## 今日已搜（{today}）\n{done_lines}\n\n"
        f"## 自动重试队列\n{retry_lines}\n\n"
        f"## 最近失败原因\n{failure_lines}\n\n"
        "## 运行日志\n"
        f"{log_lines}\n\n"
        f"{MEMORY_STATE_START}\n```json\n{state_block}\n```\n{MEMORY_STATE_END}\n"
    )


def _parse_memory_md_legacy(raw: str) -> Dict[str, Any]:
    memory = _default_memory(_today())
    if not raw.strip():
        return memory

    section = ""
    section_date = memory["today"]
    for line in raw.splitlines():
        text = line.strip()
        if text.startswith("## 今日待搜"):
            section = "todo"
            m = re.search(r"（(.+?)）", text)
            if m:
                section_date = m.group(1)
            continue
        if text.startswith("## 今日已搜"):
            section = "done"
            m = re.search(r"（(.+?)）", text)
            if m:
                section_date = m.group(1)
            continue
        if text.startswith("## 运行日志"):
            section = "logs"
            continue
        if not text.startswith("- "):
            continue
        value = text[2:].strip()
        if not value or value == "暂无":
            continue
        if section in {"todo", "done"} and section_date != memory["today"]:
            continue
        if section in memory:
            memory[section].append(value)

    return memory


def _parse_memory_md(raw: str) -> Dict[str, Any]:
    if not raw.strip():
        return _default_memory(_today())

    pattern = re.compile(
        rf"{re.escape(MEMORY_STATE_START)}\s*```json\s*(.*?)\s*```\s*{re.escape(MEMORY_STATE_END)}",
        flags=re.DOTALL,
    )
    matched = pattern.search(raw)
    if matched:
        text = matched.group(1).strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                default = _default_memory(_today())
                default.update(parsed)
                return default
        except Exception:
            pass
    return _parse_memory_md_legacy(raw)


def _save_memory_state(state: Dict[str, Any]) -> Dict[str, Any]:
    today = _today()
    default = _default_memory(today)
    merged = {**default, **(state or {})}
    merged["today"] = _to_text(merged.get("today")) or today
    merged["todo"] = list(dict.fromkeys([_to_text(x) for x in merged.get("todo", []) if _to_text(x)]))
    merged["done"] = list(dict.fromkeys([_to_text(x) for x in merged.get("done", []) if _to_text(x)]))
    for x in merged["done"]:
        if x in merged["todo"]:
            merged["todo"].remove(x)
    merged["logs"] = [_to_text(x) for x in merged.get("logs", []) if _to_text(x)][-60:]
    ranking_sources = [_to_text(x).lower() for x in merged.get("ranking_sources", []) if _to_text(x)]
    allowed_ranking_sources = {"qs", "usnews", "times"}
    ranking_sources = [x for x in ranking_sources if x in allowed_ranking_sources]
    merged["ranking_sources"] = ranking_sources or ["qs", "usnews", "times"]
    merged["priority_targets"] = list(dict.fromkeys([_to_text(x) for x in merged.get("priority_targets", []) if _to_text(x)]))
    merged["retry_queue"] = [x for x in merged.get("retry_queue", []) if isinstance(x, dict)]
    merged["failure_history"] = [x for x in merged.get("failure_history", []) if isinstance(x, dict)][-100:]
    MEMORY_FILE.write_text(_render_memory_md(merged), encoding="utf-8")
    return read_memory()


def read_memory() -> Dict[str, Any]:
    if not MEMORY_FILE.exists():
        return _save_memory_state(_default_memory(_today()))

    raw = MEMORY_FILE.read_text(encoding="utf-8")
    parsed = _parse_memory_md(raw)
    parsed.setdefault("today", _today())
    parsed.setdefault("retry_queue", [])
    parsed.setdefault("failure_history", [])
    parsed["raw_markdown"] = raw
    parsed["memory_file"] = str(MEMORY_FILE)
    parsed["state"] = {k: v for k, v in parsed.items() if k not in {"raw_markdown", "memory_file", "state"}}
    return parsed


def update_memory(
    todo_add: List[str] | None = None,
    done_add: List[str] | None = None,
    log_add: str = "",
    retry_updates: List[Dict[str, Any]] | None = None,
    failure_add: List[Dict[str, Any]] | None = None,
    long_term_patch: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    memory = read_memory().get("state", {})
    today = _today()
    if memory.get("today") != today:
        memory = _default_memory(today)

    todo = memory.get("todo") or []
    done = memory.get("done") or []
    logs = memory.get("logs") or []

    if todo_add:
        for item in todo_add:
            text = _to_text(item)
            if text and text not in todo:
                todo.append(text)
    if done_add:
        for item in done_add:
            text = _to_text(item)
            if text and text not in done:
                done.append(text)
                if text in todo:
                    todo.remove(text)
    if log_add:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {log_add}")
        logs = logs[-40:]
    retry_queue = memory.get("retry_queue") or []
    if retry_updates:
        retry_queue = retry_updates
    failure_history = memory.get("failure_history") or []
    if failure_add:
        failure_history.extend([x for x in failure_add if isinstance(x, dict)])

    merged = {
        **memory,
        "today": today,
        "todo": todo,
        "done": done,
        "logs": logs,
        "retry_queue": retry_queue,
        "failure_history": failure_history,
    }
    if long_term_patch:
        merged.update(long_term_patch)
    return _save_memory_state(merged)


def write_memory_markdown(raw_markdown: str) -> Dict[str, Any]:
    text = _to_text(raw_markdown)
    if not text:
        return read_memory()
    parsed = _parse_memory_md(text)
    return _save_memory_state(parsed)


def _looks_official(url: str, school_name: str) -> bool:
    if not url:
        return False
    host = urlparse(url).netloc.lower()
    if any(
        suffix in host
        for suffix in [".edu", ".ac.uk", ".edu.au", ".ac.nz", ".edu.sg", ".ac.jp", ".edu.cn", ".edu.hk"]
    ):
        return True

    words = [w.lower() for w in re.split(r"[^a-zA-Z]+", school_name) if len(w) >= 4]
    return any(w in host for w in words[:3])


async def _fetch_page_excerpt(url: str) -> str:
    if not re.match(r"^https?://", url):
        return ""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36"
            )
        }
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
        if resp.status_code >= 400:
            return ""
        html = resp.text
    except Exception:
        return ""

    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:1800]


def _parse_json_loose(raw: str) -> Dict[str, Any]:
    clean = re.sub(r"```json\s*", "", raw, flags=re.IGNORECASE)
    clean = re.sub(r"```\s*", "", clean, flags=re.IGNORECASE).strip()
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start < 0 or end <= start:
        return {}
    try:
        return json.loads(clean[start:end])
    except Exception:
        return {}


async def _deepseek_chat(messages: List[Dict[str, str]], *, temperature: float = 0.2) -> str:
    settings = get_settings()
    if not settings.deepseek_api_key:
        return ""

    url = f"{settings.deepseek_api_base.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}", "Content-Type": "application/json"}
    payload = {
        "model": settings.deepseek_model,
        "messages": messages,
        "temperature": temperature,
    }
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            body = resp.json()
            return _to_text(body["choices"][0]["message"]["content"])
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                await asyncio.sleep(2)
    logger.warning("deepseek_chat_failed error=%s", repr(last_error))
    return ""


async def _deepseek_reasoner_with_tools(
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
) -> Dict[str, Any]:
    settings = get_settings()
    if not settings.deepseek_api_key:
        return {}

    model = _to_text(settings.deepseek_reasoner_model) or _to_text(settings.deepseek_model) or "deepseek-reasoner"
    url = f"{settings.deepseek_api_base.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.deepseek_api_key}", "Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "tools": tools,
    }
    # 在 deepseek-chat + thinking 模式下启用思维链；reasoner 模型会忽略该参数。
    if model != "deepseek-reasoner":
        payload["thinking"] = {"type": "enabled"}

    try:
        async with httpx.AsyncClient(timeout=70.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        body = resp.json()
        message = body.get("choices", [{}])[0].get("message") or {}
        if isinstance(message, dict):
            return message
        return {}
    except Exception as exc:
        logger.warning("deepseek_reasoner_with_tools_failed error=%s", repr(exc))
        return {}


def _dedup_sources(items: List[Dict[str, Any]], school_name: str) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        url = _to_text(item.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)
        row = {
            "provider": _to_text(item.get("provider")) or preferred_search_provider(),
            "query": _to_text(item.get("query")),
            "title": _to_text(item.get("title")),
            "url": url,
            "snippet": _to_text(item.get("snippet")),
            "page_excerpt": _to_text(item.get("page_excerpt")),
        }
        row["is_official"] = _looks_official(url, school_name)
        merged.append(row)
    return merged


async def _extract_structured_with_tool_calls(
    school: SchoolProgram,
    seed_sources: List[Dict[str, Any]],
) -> Dict[str, Any]:
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "联网搜索并返回候选网页列表",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "count": {"type": "integer", "minimum": 1, "maximum": 10},
                        "mkt": {"type": "string"},
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "fetch_url",
                "description": "抓取网页正文摘要，验证页面是否包含学费、课程、就业等关键信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "max_chars": {"type": "integer", "minimum": 200, "maximum": 4000},
                    },
                    "required": ["url"],
                },
            },
        },
    ]

    source_map: Dict[str, Dict[str, Any]] = {}
    for item in _dedup_sources(seed_sources, school.school_name):
        source_map[_to_text(item.get("url"))] = item

    seed_blob = json.dumps(list(source_map.values())[:12], ensure_ascii=False)
    system_prompt = (
        "你是数据库检索员。你可以调用 search_web / fetch_url 工具补充证据。"
        "最终必须输出合法JSON，不要markdown。"
    )
    user_prompt = f"""
目标：整理 {school.school_name} · {school.program_name} 的可入库候选信息。
国家：{school.country}
专业方向：{school.major_track}

你可先搜索 QS、学校官网、项目官网、就业去向，再输出JSON：
{{
  "school_name": "{school.school_name}",
  "program_name": "{school.program_name}",
  "summary": "120字以上",
  "duration_months": 18,
  "course_list": ["课程1", "课程2", "课程3"],
  "facts": [
    {{
      "field": "tuition_usd | duration_months | course_list | admission_requirements | curriculum | internship | employment | visa | location_safety | experience",
      "value": "字段值",
      "evidence": "证据简述",
      "source_url": "来源URL",
      "is_estimate": false
    }}
  ],
  "confidence": 0,
  "missing_fields": []
}}

初始来源（可继续通过工具扩展）：
{seed_blob}
"""
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    for _ in range(8):
        message = await _deepseek_reasoner_with_tools(messages, tools)
        if not message:
            return {}

        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": _to_text(message.get("content"))}
        if message.get("tool_calls"):
            assistant_msg["tool_calls"] = message.get("tool_calls")
        if message.get("reasoning_content"):
            assistant_msg["reasoning_content"] = message.get("reasoning_content")
        messages.append(assistant_msg)

        tool_calls = message.get("tool_calls") if isinstance(message.get("tool_calls"), list) else []
        if not tool_calls:
            parsed = _parse_json_loose(_to_text(message.get("content")))
            if not parsed:
                return {}
            parsed["_tool_sources"] = list(source_map.values())[:20]
            return parsed

        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                continue
            call_id = _to_text(tool_call.get("id")) or f"call_{len(messages)}"
            fn = tool_call.get("function") if isinstance(tool_call.get("function"), dict) else {}
            fn_name = _to_text(fn.get("name"))
            args_raw = _to_text(fn.get("arguments")) or "{}"
            try:
                args = json.loads(args_raw)
            except Exception:
                args = {}

            result_content = "{}"
            if fn_name == "search_web":
                query = _to_text(args.get("query"))
                count = int(args.get("count") or 5)
                count = max(1, min(10, count))
                mkt = _to_text(args.get("mkt")) or "en-US"
                rows = await search_web(query, count=count, mkt=mkt) if query else []
                rows = _dedup_sources(rows, school.school_name)[:count]
                for row in rows:
                    source_map[_to_text(row.get("url"))] = row
                result_content = json.dumps({"results": rows}, ensure_ascii=False)
            elif fn_name == "fetch_url":
                url = _to_text(args.get("url"))
                max_chars = int(args.get("max_chars") or 1800)
                max_chars = max(200, min(4000, max_chars))
                excerpt = await _fetch_page_excerpt(url)
                excerpt = excerpt[:max_chars]
                if url:
                    exists = source_map.get(url, {"url": url, "provider": preferred_search_provider(), "title": "", "query": "", "snippet": ""})
                    exists["page_excerpt"] = excerpt
                    exists["is_official"] = _looks_official(url, school.school_name)
                    source_map[url] = exists
                result_content = json.dumps({"url": url, "excerpt": excerpt}, ensure_ascii=False)
            else:
                result_content = json.dumps({"error": f"unknown function: {fn_name}"}, ensure_ascii=False)

            messages.append({"role": "tool", "tool_call_id": call_id, "content": result_content})

    return {}


async def _extract_ranked_school_names(source: str, country: str, major: str, limit: int) -> List[str]:
    if not web_search_enabled():
        return []

    year = datetime.now().year
    src = (source or "qs").lower()
    if src == "usnews":
        queries = [
            f"US News Best Global Universities {year} {country} {major}",
            f"US News {year} {country} computer science ranking",
        ]
    elif src == "times":
        queries = [
            f"Times Higher Education World University Rankings {year} {country} {major}",
            f"THE {year} {country} computer science ranking",
        ]
    else:
        queries = [
            f"QS World University Rankings {year} {country} {major} site:topuniversities.com",
            f"QS {year} {country} university ranking computer science top universities",
        ]

    all_items: List[Dict[str, str]] = []
    for q in queries:
        all_items.extend(await search_web(q, count=8, mkt="en-US"))
    if not all_items:
        return []

    items_text = json.dumps(all_items[:18], ensure_ascii=False)
    prompt = (
        f"你是数据库检索员。根据下面搜索结果，提取院校英文全名，按{src.upper()}相关性排序。"
        f"仅返回JSON：{{\"schools\":[\"...\", \"...\"]}}，最多{max(limit, 5)}所。\n\n"
        f"搜索结果：{items_text}"
    )
    raw = await _deepseek_chat(
        [
            {"role": "system", "content": "你是严谨的信息抽取助手，只返回JSON。"},
            {"role": "user", "content": prompt},
        ]
    )
    parsed = _parse_json_loose(raw)
    schools = parsed.get("schools") if isinstance(parsed, dict) else []
    if not isinstance(schools, list):
        return []

    result: List[str] = []
    for name in schools:
        text = _to_text(name)
        if text and text not in result:
            result.append(text)
    return result[: max(limit, 5)]


def _pick_candidates(
    db: Session,
    country: str,
    major: str,
    limit: int,
    preferred_school_names: List[str],
    done_labels: List[str],
) -> List[SchoolProgram]:
    query = db.query(SchoolProgram)
    if country:
        query = query.filter(SchoolProgram.country == country)
    if major:
        query = query.filter(SchoolProgram.major_track.ilike(f"%{major}%"))

    rows = query.order_by(SchoolProgram.ranking_score.desc(), SchoolProgram.id.asc()).all()
    if not rows:
        return []

    done_set = {x.lower() for x in done_labels}
    selected: List[SchoolProgram] = []
    picked_ids: set[int] = set()

    def _label(row: SchoolProgram) -> str:
        return f"{row.school_name} · {row.program_name}"

    if preferred_school_names:
        for name in preferred_school_names:
            key = name.lower()
            for row in rows:
                if row.id in picked_ids:
                    continue
                label = _label(row).lower()
                if label in done_set:
                    continue
                if key in row.school_name.lower() or row.school_name.lower() in key:
                    selected.append(row)
                    picked_ids.add(row.id)
                    if len(selected) >= limit:
                        return selected

    for row in rows:
        if row.id in picked_ids:
            continue
        label = _label(row).lower()
        if label in done_set:
            continue
        selected.append(row)
        picked_ids.add(row.id)
        if len(selected) >= limit:
            break

    return selected


async def _collect_sources_for_program(
    school_name: str,
    program_name: str,
) -> List[Dict[str, Any]]:
    queries = [
        f"{school_name} {program_name} official site tuition",
        f"{school_name} {program_name} program duration months",
        f"{school_name} {program_name} course list syllabus",
        f"{school_name} {program_name} curriculum admission requirements",
        f"{school_name} {program_name} employment outcomes",
        f"{school_name} {program_name} student experience reddit",
        f"{school_name} {program_name} 课程列表 学制",
    ]

    raw_items: List[Dict[str, Any]] = []
    for query in queries:
        raw_items.extend(await search_web(query, count=5, mkt="en-US"))

    dedup: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()
    for item in raw_items:
        url = _to_text(item.get("url"))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        item["is_official"] = _looks_official(url, school_name)
        dedup.append(item)

    # 抓取优先官方来源页面正文片段
    for item in dedup[:10]:
        if item.get("is_official"):
            item["page_excerpt"] = await _fetch_page_excerpt(_to_text(item.get("url")))
        else:
            item["page_excerpt"] = ""

    return dedup[:12]


def _build_insight_text(structured: Dict[str, Any], sources: List[Dict[str, Any]]) -> str:
    summary = _to_text(structured.get("summary"))
    duration_text = _to_text(structured.get("duration_months") or structured.get("program_duration_months"))
    course_list = structured.get("course_list") or structured.get("course_list_json") or []
    course_items = [str(x).strip() for x in course_list] if isinstance(course_list, list) else []
    facts = structured.get("facts") if isinstance(structured.get("facts"), list) else []
    lines = [summary] if summary else []
    if duration_text:
        lines.append(f"项目时长(月)：{duration_text}")
    if course_items:
        lines.append("选课清单：" + "；".join(course_items[:12]))
    if facts:
        lines.append("结构化字段：")
        for fact in facts[:12]:
            if not isinstance(fact, dict):
                continue
            field_name = _to_text(fact.get("field")) or "field"
            value = _to_text(fact.get("value")) or "-"
            evidence = _to_text(fact.get("evidence"))
            source_url = _to_text(fact.get("source_url"))
            detail = f"- {field_name}: {value}"
            if evidence:
                detail += f"（证据：{evidence}）"
            if source_url:
                detail += f" [{source_url}]"
            lines.append(detail)

    if not lines:
        snippets = [_to_text(x.get("snippet")) for x in sources if _to_text(x.get("snippet"))]
        lines = snippets[:5]
    return "\n".join(lines).strip()


async def _extract_program_structured_json(
    school: SchoolProgram,
    sources: List[Dict[str, Any]],
) -> Dict[str, Any]:
    # 优先使用 deepseek-reasoner + tool calling 做二次检索与证据补齐。
    tool_result = await _extract_structured_with_tool_calls(school, sources)
    if isinstance(tool_result, dict) and tool_result.get("facts"):
        return tool_result

    source_blob = json.dumps(sources, ensure_ascii=False)
    prompt = f"""
你是数据库检索员，请根据检索结果抽取学校项目信息，并严格输出JSON。

学校：{school.school_name}
项目：{school.program_name}
国家：{school.country}
专业方向：{school.major_track}

请只根据给定来源抽取，不能确定就标注"估算"。
输出JSON结构：
{{
  "school_name": "{school.school_name}",
  "program_name": "{school.program_name}",
  "summary": "120字以上总结，重点是官网信息与就读体验",
  "duration_months": 18,
  "course_list": ["课程1", "课程2", "课程3"],
  "facts": [
    {{
      "field": "tuition_usd | duration_months | course_list | admission_requirements | curriculum | internship | employment | visa | location_safety | experience",
      "value": "字段值",
      "evidence": "一句证据说明，可含数字",
      "source_url": "来源URL",
      "is_estimate": false
    }}
  ],
  "confidence": 0,
  "missing_fields": ["缺失字段名"]
}}

来源数据：
{source_blob}
"""
    raw = await _deepseek_chat(
        [
            {"role": "system", "content": "你是数据库检索员，必须返回合法JSON，不要markdown。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    parsed = _parse_json_loose(raw)
    if not parsed:
        parsed = {
            "school_name": school.school_name,
            "program_name": school.program_name,
            "summary": "",
            "duration_months": 0,
            "course_list": [],
            "facts": [],
            "confidence": 0,
            "missing_fields": ["all"],
        }
    return parsed


def _insight_label(school_name: str, program_name: str) -> str:
    return f"{school_name} · {program_name}"


def _retry_delay_minutes(attempts: int) -> int:
    if attempts <= 1:
        return 15
    if attempts == 2:
        return 60
    if attempts == 3:
        return 360
    return 24 * 60


def _retry_due(entry: Dict[str, Any]) -> bool:
    value = _to_text(entry.get("next_retry_at"))
    if not value:
        return True
    try:
        return datetime.fromisoformat(value) <= datetime.now()
    except Exception:
        return True


def _merge_retry(
    retry_queue: List[Dict[str, Any]],
    *,
    school_program_id: int,
    target: str,
    reason: str,
) -> List[Dict[str, Any]]:
    queue = [x for x in retry_queue if isinstance(x, dict)]
    existing = next((x for x in queue if int(x.get("school_program_id") or 0) == int(school_program_id)), None)
    now = datetime.now()
    if existing:
        attempts = int(existing.get("attempts") or 0) + 1
        existing["attempts"] = attempts
        existing["last_reason"] = reason
        existing["updated_at"] = now.isoformat()
        existing["next_retry_at"] = (now + timedelta(minutes=_retry_delay_minutes(attempts))).isoformat()
        return queue
    attempts = 1
    queue.append(
        {
            "school_program_id": school_program_id,
            "target": target,
            "attempts": attempts,
            "last_reason": reason,
            "updated_at": now.isoformat(),
            "next_retry_at": (now + timedelta(minutes=_retry_delay_minutes(attempts))).isoformat(),
        }
    )
    return queue


def _clear_retry(retry_queue: List[Dict[str, Any]], school_program_id: int) -> List[Dict[str, Any]]:
    return [x for x in retry_queue if int(x.get("school_program_id") or 0) != int(school_program_id)]


async def run_rag_ingestion(
    db: Session,
    *,
    country: str = "",
    major: str = "",
    limit: int = 5,
) -> Dict[str, Any]:
    if not web_search_enabled():
        raise RuntimeError("搜索API未配置：请设置 SERPER_API_KEY（推荐）或 TAVILY_API_KEY/BING_API_KEY，或改用 SEARCH_PROVIDER=duckduckgo")

    memory = read_memory()
    done_labels = memory.get("done") or []
    ranking_sources = [x for x in (memory.get("ranking_sources") or ["qs", "usnews", "times"]) if _to_text(x)] or ["qs", "usnews", "times"]
    retry_queue = [x for x in (memory.get("retry_queue") or []) if isinstance(x, dict)]
    new_failures: List[Dict[str, Any]] = []

    # 先消费到期重试队列，再补充新候选。
    retry_candidates: List[SchoolProgram] = []
    retry_ids_seen: set[int] = set()
    for entry in retry_queue:
        if not _retry_due(entry):
            continue
        school_program_id = int(entry.get("school_program_id") or 0)
        if school_program_id <= 0 or school_program_id in retry_ids_seen:
            continue
        row = db.query(SchoolProgram).filter(SchoolProgram.id == school_program_id).first()
        if not row:
            continue
        retry_ids_seen.add(school_program_id)
        retry_candidates.append(row)

    ranked_names: List[str] = []
    for src in ranking_sources:
        ranked_names.extend(
            await _extract_ranked_school_names(src, country or "global", major or "Computer Science", max(5, limit))
        )
    ranked_names = list(dict.fromkeys([x for x in ranked_names if _to_text(x)]))
    ranking_source_text = " / ".join([_to_text(x).upper() for x in ranking_sources]) if ranking_sources else "QS"

    fresh_candidates = _pick_candidates(db, country, major, max(0, limit - len(retry_candidates)), ranked_names, done_labels)
    candidates = retry_candidates + [x for x in fresh_candidates if x.id not in retry_ids_seen]

    queued_targets = [_insight_label(x.school_name, x.program_name) for x in candidates]
    update_memory(
        todo_add=queued_targets,
        log_add=(
            f"开始检索：ranking={ranking_source_text} country={country or '全部'} "
            f"major={major or '全部'} limit={limit}，候选{len(queued_targets)}个（重试{len(retry_candidates)}）"
        ),
    )

    created = 0
    skipped = 0
    completed_targets: List[str] = []

    for row in candidates:
        sources = await _collect_sources_for_program(row.school_name, row.program_name)
        if not sources:
            target = _insight_label(row.school_name, row.program_name)
            reason = "联网搜索无结果"
            retry_queue = _merge_retry(retry_queue, school_program_id=row.id, target=target, reason=reason)
            new_failures.append(
                {"time": datetime.now().isoformat(), "target": target, "reason": reason}
            )
            skipped += 1
            continue
        structured = await _extract_program_structured_json(row, sources)
        tool_sources = structured.pop("_tool_sources", []) if isinstance(structured, dict) else []
        if isinstance(tool_sources, list) and tool_sources:
            sources = _dedup_sources([*sources, *tool_sources], row.school_name)
        raw_text = _build_insight_text(structured, sources)
        if not raw_text:
            target = _insight_label(row.school_name, row.program_name)
            reason = "结构化抽取为空"
            retry_queue = _merge_retry(retry_queue, school_program_id=row.id, target=target, reason=reason)
            new_failures.append(
                {"time": datetime.now().isoformat(), "target": target, "reason": reason}
            )
            skipped += 1
            continue

        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        existing = (
            db.query(SchoolSearchInsight)
            .filter(
                SchoolSearchInsight.school_program_id == row.id,
                SchoolSearchInsight.status == "pending",
            )
            .all()
        )
        if any(hashlib.sha256(_to_text(x.raw_text).encode("utf-8")).hexdigest() == content_hash for x in existing):
            skipped += 1
            completed_targets.append(_insight_label(row.school_name, row.program_name))
            retry_queue = _clear_retry(retry_queue, row.id)
            continue

        db.add(
                SchoolSearchInsight(
                    school_program_id=row.id,
                    school_name=row.school_name,
                    program_name=row.program_name,
                    source_provider=f"{preferred_search_provider()}+deepseek-rag",
                    raw_text=raw_text,
                    search_payload={
                        "ranking_sources": ranking_sources,
                        "ranking_candidates": ranked_names,
                        "items": sources,
                        "structured_json": structured,
                    },
                    status="pending",
                )
        )
        created += 1
        completed_targets.append(_insight_label(row.school_name, row.program_name))
        retry_queue = _clear_retry(retry_queue, row.id)

    db.commit()

    update_memory(
        done_add=completed_targets,
        retry_updates=retry_queue,
        failure_add=new_failures,
        log_add=f"检索完成：新增待审批{created}条，跳过{skipped}条，重试队列{len(retry_queue)}条",
    )
    final_memory = read_memory()
    return {
        "message": f"数据库检索员已完成本轮检索，新增待审批 {created} 条。",
        "scanned": len(candidates),
        "created": created,
        "skipped": skipped,
        "queued_targets": queued_targets,
        "completed_targets": completed_targets,
        "memory_file": _to_text(final_memory.get("memory_file")),
    }


def _memory_brief(memory: Dict[str, Any]) -> str:
    todo = memory.get("todo") or []
    done = memory.get("done") or []
    retry_queue = memory.get("retry_queue") or []
    return (
        f"今天待搜 {len(todo)} 项，已搜 {len(done)} 项，自动重试队列 {len(retry_queue)} 项。"
        f"待搜示例：{_to_text(todo[0]) if todo else '无'}。"
    )


async def admin_assistant_chat(
    db: Session,
    *,
    message: str = "",
    quick_action: str = "",
    country: str = "",
    major: str = "",
    limit: int = 5,
) -> Dict[str, Any]:
    memory = read_memory()
    lower_msg = _to_text(message).lower()
    action = _to_text(quick_action).lower()

    if action == "search_10":
        limit = 10
        action = "search_5"
    if "继续搜索" in lower_msg or "search" in lower_msg:
        action = "search_5"

    if action == "search_5":
        result = await run_rag_ingestion(db, country=country, major=major, limit=limit)
        brief = _memory_brief(read_memory())
        ranking_text = " / ".join([_to_text(x).upper() for x in memory.get("ranking_sources", []) if _to_text(x)]) or "QS"
        return {
            "role": "assistant",
            "reply": (
                f"你好，我是数据库检索员。已按{ranking_text}线索完成本轮搜索并生成待审批资料。\n"
                f"{result['message']}\n{brief}\n"
                "你可以在下方逐条选择：接受入库 / 不接受 / 编辑后入库。"
            ),
            **{k: result[k] for k in ["scanned", "created", "skipped", "completed_targets"]},
            "memory_excerpt": brief,
        }

    if action == "show_memory":
        brief = _memory_brief(memory)
        return {
            "role": "assistant",
            "reply": f"数据库检索员记忆：\n{brief}",
            "memory_excerpt": brief,
            "scanned": 0,
            "created": 0,
            "skipped": 0,
            "completed_targets": [],
        }

    if not _to_text(message):
        brief = _memory_brief(memory)
        ranking_text = " / ".join([_to_text(x).upper() for x in memory.get("ranking_sources", []) if _to_text(x)]) or "QS"
        return {
            "role": "assistant",
            "reply": (
                "你好，我是数据库检索员。"
                f"我可以继续按{ranking_text}榜单线索检索学校项目信息，输出来源可追溯的候选数据供你审批入库。\n"
                f"{brief}\n要继续吗？可直接点击“继续搜索入库5个学校信息”。"
            ),
            "memory_excerpt": brief,
            "scanned": 0,
            "created": 0,
            "skipped": 0,
            "completed_targets": [],
        }

    prompt = (
        "你是数据库检索员，请用简洁中文回答管理员。"
        "你需要根据记忆说明接下来应搜哪些学校与项目，语气专业直接。\n\n"
        f"记忆：{memory.get('raw_markdown', '')}\n\n"
        f"管理员问题：{message}"
    )
    llm_reply = await _deepseek_chat(
        [
            {"role": "system", "content": "你是数据库检索员，回答要简洁、可执行。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    if not llm_reply:
        llm_reply = "我已记录你的指令。建议先点击“继续搜索入库5个学校信息”，完成一轮可审核数据再决定下一步。"
    return {
        "role": "assistant",
        "reply": llm_reply,
        "memory_excerpt": _memory_brief(memory),
        "scanned": 0,
        "created": 0,
        "skipped": 0,
        "completed_targets": [],
    }
