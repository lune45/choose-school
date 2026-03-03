from io import BytesIO
import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import AnalysisRecord, SchoolProgram, User
from ..schemas import AnalysisRecordOut, AnalysisRunRequest, AnalysisRunResponse, RankingItem
from ..security import get_current_user
from ..services.ai_client import generate_report, result_json_to_markdown
from ..services.deepseek import DISCLAIMER, build_prompt
from ..services.pdf_report import render_pdf
from ..services.query_schema import compose_query_output
from ..services.scoring import rank_programs
from ..services.weights import (
    calc_weights,
    concern_labels,
    label_weight_map,
    map_user_weights_to_internal,
    normalize_dimension_keys,
    normalize_user_weights,
)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _program_to_dict(p: SchoolProgram) -> dict:
    program = {
        "id": p.id,
        "country": p.country,
        "school_name": p.school_name,
        "program_name": p.program_name,
        "major_track": p.major_track,
        "degree": p.degree,
        "qs_rank": p.qs_rank,
        "usnews_rank": p.usnews_rank,
        "times_rank": p.times_rank,
        "program_duration_months": p.program_duration_months,
        "course_list_json": p.course_list_json or [],
        "tuition_usd": p.tuition_usd,
        "living_cost_usd": p.living_cost_usd,
        "ranking_score": p.ranking_score,
        "median_salary_usd": p.median_salary_usd,
        "safety_score": p.safety_score,
        "course_difficulty": p.course_difficulty,
        "employment_support": p.employment_support,
        "visa_support": p.visa_support,
        "alumni_network": p.alumni_network,
        "immigration_friendly": p.immigration_friendly,
        "domestic_recognition": p.domestic_recognition,
        "notes": p.notes,
    }
    stored = p.query_output_json if isinstance(p.query_output_json, dict) else {}
    program["query_output"] = compose_query_output(program, stored)
    return program


def _coerce_result_json(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _unique_school_ids(raw_ids: list[int]) -> list[int]:
    result: list[int] = []
    seen = set()
    for item in raw_ids:
        try:
            value = int(item)
        except Exception:
            continue
        if value <= 0 or value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _resolve_request_inputs(payload: AnalysisRunRequest) -> tuple[list[str], list[int], Dict[str, int], list[str]]:
    concerns_raw = payload.selected_dimensions or payload.concerns
    concerns = normalize_dimension_keys(concerns_raw)
    school_ids = _unique_school_ids(payload.school_ids or payload.schools)
    user_weights = normalize_user_weights(concerns, payload.weights or {})
    return concerns, school_ids, user_weights, concerns_raw


async def create_analysis_from_payload(
    payload: AnalysisRunRequest,
    db: Session,
    current_user: User,
) -> AnalysisRunResponse:
    selected_dimensions, school_ids, user_weights, concerns_raw = _resolve_request_inputs(payload)
    if len(selected_dimensions) < 2:
        raise HTTPException(status_code=400, detail="请至少选择2个关注维度")
    if not school_ids:
        raise HTTPException(status_code=400, detail="至少选择一个学校项目")

    programs = (
        db.query(SchoolProgram)
        .filter(SchoolProgram.id.in_(school_ids), SchoolProgram.country == payload.country)
        .all()
    )
    if not programs:
        raise HTTPException(status_code=400, detail="未找到所选国家下的学校项目")

    if payload.weights and isinstance(payload.weights, dict) and user_weights:
        internal_weights = map_user_weights_to_internal(user_weights)
    else:
        internal_weights = calc_weights(concerns_raw)
        if not user_weights:
            user_weights = normalize_user_weights(selected_dimensions, {})
    ranking = rank_programs(programs, internal_weights)
    concerns_label_list = concern_labels(selected_dimensions)
    prompt_weights = label_weight_map(user_weights) if payload.weights else internal_weights

    schools_json = [_program_to_dict(p) for p in programs]
    prompt = build_prompt(
        country=payload.country,
        major=payload.major,
        budget_max=payload.budget_max,
        selected_dimensions=concerns_label_list,
        weights=prompt_weights,
        schools_json=schools_json,
    )

    settings = get_settings()
    status = "completed"
    error_message = ""
    model_used = settings.deepseek_model
    summary_markdown = ""
    result_json: Dict[str, Any] = {}
    raw_ai_response = ""
    ranking_to_save = ranking
    ranking_to_return = [RankingItem(**r) for r in ranking]

    try:
        model_used, result_json, raw_ai_response = await generate_report(
            prompt=prompt,
            schools_json=schools_json,
            selected_dimensions=concerns_label_list,
        )
        summary_markdown = result_json_to_markdown(result_json)
        if DISCLAIMER not in summary_markdown:
            summary_markdown = summary_markdown + "\n\n" + DISCLAIMER
    except Exception as exc:
        status = "failed"
        error_message = str(exc)
        summary_markdown = ""
        result_json = {}
        raw_ai_response = ""
        ranking_to_save = []
        ranking_to_return = []

    record = AnalysisRecord(
        user_id=current_user.id,
        country=payload.country,
        major=payload.major,
        budget_max=payload.budget_max,
        selected_dimensions=selected_dimensions,
        concerns_json=selected_dimensions,
        selected_school_ids=school_ids,
        weights=internal_weights,
        weights_json=user_weights,
        status=status,
        error_message=error_message,
        model_used=model_used,
        ai_summary_markdown=summary_markdown,
        result_json=result_json,
        raw_ai_response=raw_ai_response,
        ranking_table_json=ranking_to_save,
        disclaimer=DISCLAIMER,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return AnalysisRunResponse(
        analysis_id=record.id,
        status=status,
        error_message=error_message or None,
        model_used=model_used,
        weights=internal_weights,
        concerns_json=selected_dimensions,
        weights_json=user_weights,
        ranking=ranking_to_return,
        summary_markdown=summary_markdown,
        result_json=result_json,
        disclaimer=DISCLAIMER,
    )


@router.post("/run", response_model=AnalysisRunResponse)
async def run_analysis(
    payload: AnalysisRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_analysis_from_payload(payload, db, current_user)


@router.get("/{analysis_id}", response_model=AnalysisRecordOut)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.id == analysis_id, AnalysisRecord.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    ranking = row.ranking_table_json if isinstance(row.ranking_table_json, list) else []
    result_json = _coerce_result_json(row.result_json)

    return AnalysisRecordOut(
        id=row.id,
        status=row.status,
        error_message=row.error_message or None,
        country=row.country,
        major=row.major,
        budget_max=row.budget_max,
        selected_dimensions=row.selected_dimensions,
        concerns_json=row.concerns_json if isinstance(row.concerns_json, list) else row.selected_dimensions,
        selected_school_ids=row.selected_school_ids,
        weights=row.weights,
        weights_json=row.weights_json if isinstance(row.weights_json, dict) else row.weights,
        model_used=row.model_used,
        ranking=[RankingItem(**r) for r in ranking],
        summary_markdown=row.ai_summary_markdown,
        result_json=result_json,
        disclaimer=row.disclaimer,
        created_at=row.created_at,
    )


@router.get("/{analysis_id}/pdf")
def download_pdf(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.id == analysis_id, AnalysisRecord.user_id == current_user.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="分析记录不存在")
    if row.status == "failed":
        raise HTTPException(status_code=400, detail="报告生成失败，无法下载PDF")

    ranking = row.ranking_table_json if isinstance(row.ranking_table_json, list) else []
    pdf_bytes = render_pdf(
        title="留学择校分析报告",
        user_profile={
            "country": row.country,
            "major": row.major,
            "budget_max": row.budget_max,
            "selected_dimensions": row.selected_dimensions,
        },
        weights=row.weights,
        ranking=ranking,
        summary_markdown=row.ai_summary_markdown,
        disclaimer=row.disclaimer,
    )

    stream = BytesIO(pdf_bytes)
    filename = f"study_report_{analysis_id}.pdf"
    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
