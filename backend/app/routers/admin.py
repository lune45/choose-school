from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from io import BytesIO, StringIO
from typing import Any, Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SchoolProgram, SchoolSearchInsight, User
from ..schemas import (
    AdminImportResponse,
    AdminRagChatRequest,
    AdminRagChatResponse,
    AdminRagMemoryResponse,
    AdminRagMemoryUpdateRequest,
    AdminRagSearchRequest,
    AdminRagSearchResponse,
    AdminInsightApproveRequest,
    AdminInsightEditRequest,
    AdminInsightOut,
    AdminInsightRejectRequest,
    AdminSchoolCreate,
    AdminSchoolUpdate,
    SchoolOut,
)
from ..security import get_admin_user
from ..services.query_schema import (
    compose_query_output,
    get_query_output_keys,
    get_query_output_label_map,
)
from ..services.rag_agent import admin_assistant_chat, read_memory, run_rag_ingestion, update_memory, write_memory_markdown

router = APIRouter(prefix="/api/admin", tags=["admin"])

COLUMNS = [
    "country",
    "school_name",
    "program_name",
    "major_track",
    "degree",
    "qs_rank",
    "usnews_rank",
    "times_rank",
    "program_duration_months",
    "course_list_json",
    "tuition_usd",
    "living_cost_usd",
    "ranking_score",
    "median_salary_usd",
    "safety_score",
    "course_difficulty",
    "employment_support",
    "visa_support",
    "alumni_network",
    "immigration_friendly",
    "domestic_recognition",
    "notes",
]

ALIASES: Dict[str, List[str]] = {
    "country": ["country", "国家", "留学国家", "目标国家/地区"],
    "school_name": ["school_name", "school_name_en", "学校", "院校", "学校名称", "学校英文全称"],
    "program_name": ["program_name", "项目", "项目名称", "专业项目", "program", "项目全称"],
    "major_track": ["major_track", "方向", "专业方向", "track", "major_category", "major_sub", "专业大类", "专业细分"],
    "degree": ["degree", "学位", "degree_type", "学位类型"],
    "qs_rank": ["qs_rank", "qs排名", "QS排名", "qs", "qs_world_rank", "QS世界综合排名"],
    "usnews_rank": ["usnews_rank", "usnews排名", "USNews排名", "usnews", "local_rank", "本地排名"],
    "times_rank": ["times_rank", "times排名", "泰晤士排名", "times", "the_rank", "THE排名"],
    "program_duration_months": ["program_duration_months", "项目时长(月)", "项目时长", "学制(月)", "duration_months", "duration_months(月)"],
    "course_list_json": ["course_list_json", "选课清单", "课程列表", "核心课程", "course_list"],
    "tuition_usd": ["tuition_usd", "学费", "tuition", "tuition_total_usd", "总学费(USD)"],
    "living_cost_usd": ["living_cost_usd", "生活费", "living_cost", "living_cost_annual_usd", "年均生活费(USD)"],
    "ranking_score": ["ranking_score", "排名分", "排名", "ranking"],
    "median_salary_usd": ["median_salary_usd", "毕业薪资中位数", "薪资中位数", "salary", "起薪中位数(USD)"],
    "safety_score": ["safety_score", "安全分", "安全度", "safety", "safety_rating", "安全评级"],
    "course_difficulty": ["course_difficulty", "课程难度", "难度", "workload_level", "课业压力"],
    "employment_support": ["employment_support", "就业支持", "就业服务"],
    "visa_support": ["visa_support", "工签支持", "签证支持"],
    "alumni_network": ["alumni_network", "校友网络", "校友"],
    "immigration_friendly": ["immigration_friendly", "移民友好度", "移民友好", "h1b绿卡"],
    "domestic_recognition": ["domestic_recognition", "回国认可度", "国内认可度", "china_recognition"],
    "notes": ["notes", "备注", "说明", "curator_notes", "录入备注"],
}

NUMERIC_FIELDS = {
    "qs_rank",
    "usnews_rank",
    "times_rank",
    "program_duration_months",
    "tuition_usd",
    "living_cost_usd",
    "ranking_score",
    "median_salary_usd",
    "safety_score",
    "course_difficulty",
    "employment_support",
    "visa_support",
    "alumni_network",
    "immigration_friendly",
    "domestic_recognition",
}

QUERY_OUTPUT_KEYS = get_query_output_keys()
QUERY_OUTPUT_LABEL_MAP = get_query_output_label_map()
QUERY_OUTPUT_IMPORT_PREFIX = "__query_output__:"
TEMPLATE_COLUMNS = COLUMNS + [x for x in QUERY_OUTPUT_KEYS if x not in COLUMNS]



def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "", str(text).strip().lower())



def _to_float(value) -> float:
    try:
        if value is None:
            return 0.0
        s = str(value).strip().replace(",", "")
        if s == "" or s.lower() in {"nan", "none"}:
            return 0.0
        return float(s)
    except Exception:
        return 0.0


def _to_str_list(value: Any) -> List[str]:
    if isinstance(value, list):
        items = [str(x).strip() for x in value if str(x).strip()]
        return list(dict.fromkeys(items))
    if value is None:
        return []
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none"}:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            arr = json.loads(text)
            if isinstance(arr, list):
                items = [str(x).strip() for x in arr if str(x).strip()]
                return list(dict.fromkeys(items))
        except Exception:
            pass
    parts = re.split(r"\n|；|;|、|,|，|\|", text)
    items = [x.strip() for x in parts if x.strip()]
    return list(dict.fromkeys(items))


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _to_query_output_value(value: Any) -> str:
    text = _to_text(value)
    if text.lower() in {"", "none", "null", "nan", "n/a"}:
        return "-"
    return text


def _extract_query_output_from_record(record: Dict[str, Any], col_map: Dict[str, str]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for key in QUERY_OUTPUT_KEYS:
        mapped = col_map.get(f"{QUERY_OUTPUT_IMPORT_PREFIX}{key}")
        if mapped is None:
            continue
        value = _to_query_output_value(record.get(mapped))
        result[key] = value
    return result


def _program_dict_from_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "country": item.get("country", ""),
        "school_name": item.get("school_name", ""),
        "program_name": item.get("program_name", ""),
        "major_track": item.get("major_track", ""),
        "degree": item.get("degree", ""),
        "qs_rank": item.get("qs_rank", 0),
        "usnews_rank": item.get("usnews_rank", 0),
        "times_rank": item.get("times_rank", 0),
        "program_duration_months": item.get("program_duration_months", 0),
        "course_list_json": item.get("course_list_json", []),
        "tuition_usd": item.get("tuition_usd", 0),
        "living_cost_usd": item.get("living_cost_usd", 0),
        "ranking_score": item.get("ranking_score", 0),
        "median_salary_usd": item.get("median_salary_usd", 0),
        "safety_score": item.get("safety_score", 0),
        "course_difficulty": item.get("course_difficulty", 0),
        "employment_support": item.get("employment_support", 0),
        "visa_support": item.get("visa_support", 0),
        "alumni_network": item.get("alumni_network", 0),
        "immigration_friendly": item.get("immigration_friendly", 0),
        "domestic_recognition": item.get("domestic_recognition", 0),
        "notes": item.get("notes", ""),
    }


def _program_dict_from_model(row: SchoolProgram) -> Dict[str, Any]:
    return {
        "country": row.country,
        "school_name": row.school_name,
        "program_name": row.program_name,
        "major_track": row.major_track,
        "degree": row.degree,
        "qs_rank": row.qs_rank,
        "usnews_rank": row.usnews_rank,
        "times_rank": row.times_rank,
        "program_duration_months": row.program_duration_months,
        "course_list_json": row.course_list_json or [],
        "tuition_usd": row.tuition_usd,
        "living_cost_usd": row.living_cost_usd,
        "ranking_score": row.ranking_score,
        "median_salary_usd": row.median_salary_usd,
        "safety_score": row.safety_score,
        "course_difficulty": row.course_difficulty,
        "employment_support": row.employment_support,
        "visa_support": row.visa_support,
        "alumni_network": row.alumni_network,
        "immigration_friendly": row.immigration_friendly,
        "domestic_recognition": row.domestic_recognition,
        "notes": row.notes,
    }


def _structured_duration_and_courses(payload: Any) -> tuple[float, List[str]]:
    duration = 0.0
    courses: List[str] = []
    if not isinstance(payload, dict):
        return duration, courses

    def parse_duration(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        m = re.search(r"(\d+(?:\.\d+)?)", str(value))
        return float(m.group(1)) if m else 0.0

    duration = parse_duration(payload.get("duration_months") or payload.get("program_duration_months"))
    courses = _to_str_list(payload.get("course_list") or payload.get("course_list_json"))

    facts = payload.get("facts")
    if isinstance(facts, list):
        for fact in facts:
            if not isinstance(fact, dict):
                continue
            field_name = str(fact.get("field") or "").strip().lower()
            value = fact.get("value")
            if not duration and field_name in {"duration", "duration_months", "program_duration_months"}:
                duration = parse_duration(value)
            if field_name in {"course_list", "courses", "curriculum"}:
                courses.extend(_to_str_list(value))
    return duration, list(dict.fromkeys([x for x in courses if x]))



def _resolve_column_map(df_cols: List[str]) -> Dict[str, str]:
    normalized = {_norm(c): c for c in df_cols}
    resolved: Dict[str, str] = {}
    for target, aliases in ALIASES.items():
        for alias in aliases:
            alias_key = _norm(alias)
            if alias_key in normalized:
                resolved[target] = normalized[alias_key]
                break
    for key in QUERY_OUTPUT_KEYS:
        aliases = [key]
        label = QUERY_OUTPUT_LABEL_MAP.get(key, "")
        if label:
            aliases.append(label)
        for alias in aliases:
            alias_key = _norm(alias)
            if alias_key in normalized:
                resolved[f"{QUERY_OUTPUT_IMPORT_PREFIX}{key}"] = normalized[alias_key]
                break
    return resolved


@router.get("/schools", response_model=list[SchoolOut])
def admin_list_schools(
    country: str | None = Query(None),
    q: str = Query(""),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    query = db.query(SchoolProgram)
    if country:
        query = query.filter(SchoolProgram.country == country)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (SchoolProgram.school_name.ilike(like))
            | (SchoolProgram.program_name.ilike(like))
            | (SchoolProgram.major_track.ilike(like))
        )

    rows = query.order_by(SchoolProgram.id.desc()).offset(skip).limit(limit).all()
    return [SchoolOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/schools", response_model=SchoolOut)
def admin_create_school(
    payload: AdminSchoolCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    payload_data = payload.model_dump()
    incoming_query_output = payload_data.pop("query_output_json", {}) or {}
    program_data = _program_dict_from_item(payload_data)
    payload_data["query_output_json"] = compose_query_output(program_data, incoming_query_output)

    row = SchoolProgram(**payload_data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return SchoolOut.model_validate(row, from_attributes=True)


@router.put("/schools/{school_id}", response_model=SchoolOut)
def admin_update_school(
    school_id: int,
    payload: AdminSchoolUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    row = db.query(SchoolProgram).filter(SchoolProgram.id == school_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="学校项目不存在")

    payload_data = payload.model_dump(exclude_unset=True)
    incoming_query_output = payload_data.pop("query_output_json", None)

    for k, v in payload_data.items():
        setattr(row, k, v)

    current_query_output = row.query_output_json if isinstance(row.query_output_json, dict) else {}
    query_override = incoming_query_output if isinstance(incoming_query_output, dict) else current_query_output
    row.query_output_json = compose_query_output(_program_dict_from_model(row), query_override)
    db.commit()
    db.refresh(row)
    return SchoolOut.model_validate(row, from_attributes=True)


@router.delete("/schools/{school_id}")
def admin_delete_school(
    school_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    row = db.query(SchoolProgram).filter(SchoolProgram.id == school_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="学校项目不存在")
    db.delete(row)
    db.commit()
    return {"message": "删除成功", "id": school_id}


@router.post("/schools/import-excel", response_model=AdminImportResponse)
async def admin_import_schools_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="请上传Excel文件")

    content = await file.read()
    xls = pd.ExcelFile(BytesIO(content))
    if not xls.sheet_names:
        raise HTTPException(status_code=400, detail="Excel为空")

    df = xls.parse(sheet_name=xls.sheet_names[0])
    if df.empty:
        return AdminImportResponse(created=0, updated=0, errors=[])

    col_map = _resolve_column_map(list(df.columns))
    missing_required = [k for k in ["country", "school_name", "program_name"] if k not in col_map]
    if missing_required:
        raise HTTPException(
            status_code=400,
            detail=f"缺少必要列: {', '.join(missing_required)}。可先下载模板后填充。",
        )

    created = 0
    updated = 0
    errors: List[str] = []

    for idx, record in enumerate(df.to_dict(orient="records"), start=2):
        item = {}
        for field in COLUMNS:
            col = col_map.get(field)
            val = record.get(col) if col is not None else None
            if field in NUMERIC_FIELDS:
                item[field] = _to_float(val)
            elif field == "course_list_json":
                item[field] = _to_str_list(val)
            else:
                if val is None or str(val).strip().lower() in {"", "nan", "none"}:
                    item[field] = ""
                else:
                    item[field] = str(val).strip()

        query_output_override = _extract_query_output_from_record(record, col_map)

        if not item["country"] or not item["school_name"] or not item["program_name"]:
            errors.append(f"第{idx}行缺少 country/school_name/program_name")
            continue

        row = (
            db.query(SchoolProgram)
            .filter(
                SchoolProgram.country == item["country"],
                SchoolProgram.school_name == item["school_name"],
                SchoolProgram.program_name == item["program_name"],
            )
            .first()
        )

        if row:
            for k, v in item.items():
                setattr(row, k, v)
            existing_query_output = row.query_output_json if isinstance(row.query_output_json, dict) else {}
            row.query_output_json = compose_query_output(
                _program_dict_from_model(row),
                query_output_override or existing_query_output,
            )
            updated += 1
        else:
            item["query_output_json"] = compose_query_output(
                _program_dict_from_item(item),
                query_output_override,
            )
            db.add(SchoolProgram(**item))
            created += 1

    db.commit()
    return AdminImportResponse(created=created, updated=updated, errors=errors[:50])


@router.get("/schools/template")
def admin_download_template(_: User = Depends(get_admin_user)):
    sample = {
        "country": "美国",
        "school_name": "Example University",
        "program_name": "MS in Computer Science",
        "major_track": "CS",
        "degree": "Master",
        "qs_rank": 25,
        "usnews_rank": 31,
        "times_rank": 34,
        "program_duration_months": 18,
        "course_list_json": "Machine Learning;Distributed Systems;Database Systems",
        "tuition_usd": 42000,
        "living_cost_usd": 22000,
        "ranking_score": 85,
        "median_salary_usd": 120000,
        "safety_score": 78,
        "course_difficulty": 7,
        "employment_support": 82,
        "visa_support": 75,
        "alumni_network": 80,
        "immigration_friendly": 60,
        "domestic_recognition": 84,
        "notes": "示例行，可删除",
    }
    for key in QUERY_OUTPUT_KEYS:
        sample.setdefault(key, "-")
    sample["country"] = "美国"
    sample["school_name_en"] = "Example University"
    sample["school_name_cn"] = "示例大学"
    sample["program_name"] = "MS in Computer Science"
    sample["duration_months"] = "18"
    sample["course_list_json"] = "Machine Learning;Distributed Systems;Database Systems"
    sample["post_study_work"] = "OPT 1-3年"
    sample["h1b_sponsor_rate_pct"] = "35"
    sample["policy_last_checked"] = datetime.utcnow().strftime("%Y-%m-%d")

    csv_io = StringIO()
    writer = csv.DictWriter(csv_io, fieldnames=TEMPLATE_COLUMNS)
    writer.writeheader()
    writer.writerow(sample)

    data = "\ufeff" + csv_io.getvalue()
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=school_import_template.csv"},
    )


@router.get("/rag/memory", response_model=AdminRagMemoryResponse)
def admin_rag_memory(_: User = Depends(get_admin_user)):
    data = read_memory()
    return AdminRagMemoryResponse(
        today=data.get("today", ""),
        long_term_instruction=data.get("long_term_instruction", ""),
        ranking_sources=data.get("ranking_sources", []),
        priority_targets=data.get("priority_targets", []),
        todo=data.get("todo", []),
        done=data.get("done", []),
        retry_queue=data.get("retry_queue", []),
        failure_history=data.get("failure_history", []),
        logs=data.get("logs", []),
        raw_markdown=data.get("raw_markdown", ""),
    )


@router.patch("/rag/memory", response_model=AdminRagMemoryResponse)
def admin_update_rag_memory(
    payload: AdminRagMemoryUpdateRequest,
    _: User = Depends(get_admin_user),
):
    if payload.raw_markdown.strip():
        data = write_memory_markdown(payload.raw_markdown)
    else:
        patch = {}
        if payload.long_term_instruction.strip():
            patch["long_term_instruction"] = payload.long_term_instruction.strip()
        if payload.ranking_sources:
            patch["ranking_sources"] = [x.lower() for x in payload.ranking_sources if x.strip()]
        if payload.priority_targets:
            patch["priority_targets"] = [x.strip() for x in payload.priority_targets if x.strip()]
        data = update_memory(long_term_patch=patch, log_add="管理员更新长期记忆策略")

    return AdminRagMemoryResponse(
        today=data.get("today", ""),
        long_term_instruction=data.get("long_term_instruction", ""),
        ranking_sources=data.get("ranking_sources", []),
        priority_targets=data.get("priority_targets", []),
        todo=data.get("todo", []),
        done=data.get("done", []),
        retry_queue=data.get("retry_queue", []),
        failure_history=data.get("failure_history", []),
        logs=data.get("logs", []),
        raw_markdown=data.get("raw_markdown", ""),
    )


@router.post("/rag/search", response_model=AdminRagSearchResponse)
async def admin_rag_search(
    payload: AdminRagSearchRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    try:
        result = await run_rag_ingestion(
            db,
            country=payload.country.strip(),
            major=payload.major.strip(),
            limit=payload.limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AdminRagSearchResponse(**result)


@router.post("/rag/chat", response_model=AdminRagChatResponse)
async def admin_rag_chat(
    payload: AdminRagChatRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    try:
        data = await admin_assistant_chat(
            db,
            message=payload.message,
            quick_action=payload.quick_action,
            country=payload.country.strip(),
            major=payload.major.strip(),
            limit=payload.limit,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AdminRagChatResponse(**data)


@router.get("/insights", response_model=list[AdminInsightOut])
def admin_list_insights(
    status: str = Query("pending"),
    q: str = Query(""),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    query = db.query(SchoolSearchInsight)
    if status and status != "all":
        query = query.filter(SchoolSearchInsight.status == status)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (SchoolSearchInsight.school_name.ilike(like))
            | (SchoolSearchInsight.program_name.ilike(like))
            | (SchoolSearchInsight.raw_text.ilike(like))
        )
    rows = query.order_by(SchoolSearchInsight.id.desc()).offset(skip).limit(limit).all()
    return [AdminInsightOut.model_validate(r, from_attributes=True) for r in rows]


@router.patch("/insights/{insight_id}", response_model=AdminInsightOut)
def admin_edit_insight(
    insight_id: int,
    payload: AdminInsightEditRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    row = db.query(SchoolSearchInsight).filter(SchoolSearchInsight.id == insight_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="待审批资料不存在")
    row.edited_text = payload.edited_text.strip()
    if payload.review_note.strip():
        row.review_note = payload.review_note.strip()
    db.commit()
    db.refresh(row)
    return AdminInsightOut.model_validate(row, from_attributes=True)


@router.post("/insights/{insight_id}/approve", response_model=AdminInsightOut)
def admin_approve_insight(
    insight_id: int,
    payload: AdminInsightApproveRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user),
):
    row = db.query(SchoolSearchInsight).filter(SchoolSearchInsight.id == insight_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="待审批资料不存在")

    final_text = payload.final_text.strip() or row.edited_text.strip() or row.raw_text.strip()
    if not final_text:
        raise HTTPException(status_code=400, detail="通过入库前需要可用文本")

    row.status = "approved"
    row.review_note = payload.review_note.strip() or row.review_note
    row.edited_text = final_text
    row.reviewed_by_user_id = current_admin.id
    row.reviewed_at = datetime.utcnow()

    if row.school_program_id:
        program = db.query(SchoolProgram).filter(SchoolProgram.id == row.school_program_id).first()
        if program:
            structured_json = {}
            if isinstance(row.search_payload, dict):
                maybe_structured = row.search_payload.get("structured_json")
                if isinstance(maybe_structured, dict):
                    structured_json = maybe_structured

            duration_months, course_list = _structured_duration_and_courses(structured_json)
            if duration_months > 0:
                program.program_duration_months = duration_months
            if course_list:
                merged_courses = list(dict.fromkeys([*(program.course_list_json or []), *course_list]))
                program.course_list_json = merged_courses

            stamp = datetime.utcnow().strftime("%Y-%m-%d")
            merged = f"[联网检索就读体验 {stamp}] {final_text}"
            if not program.notes:
                program.notes = merged
            elif merged not in program.notes:
                program.notes = f"{program.notes}\n\n{merged}"

            existing_query_output = program.query_output_json if isinstance(program.query_output_json, dict) else {}
            program.query_output_json = compose_query_output(
                _program_dict_from_model(program),
                existing_query_output,
            )

    db.commit()
    db.refresh(row)
    return AdminInsightOut.model_validate(row, from_attributes=True)


@router.post("/insights/{insight_id}/reject", response_model=AdminInsightOut)
def admin_reject_insight(
    insight_id: int,
    payload: AdminInsightRejectRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_admin_user),
):
    row = db.query(SchoolSearchInsight).filter(SchoolSearchInsight.id == insight_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="待审批资料不存在")

    row.status = "rejected"
    row.review_note = payload.review_note.strip() or row.review_note
    row.reviewed_by_user_id = current_admin.id
    row.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return AdminInsightOut.model_validate(row, from_attributes=True)
