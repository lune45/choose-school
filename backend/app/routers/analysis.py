from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AnalysisRecord, SchoolProgram, User
from ..schemas import AnalysisRecordOut, AnalysisRunRequest, AnalysisRunResponse, RankingItem
from ..security import get_current_user
from ..services.deepseek import DISCLAIMER, build_prompt, generate_analysis
from ..services.pdf_report import render_pdf
from ..services.scoring import rank_programs
from ..services.weights import calc_weights

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _program_to_dict(p: SchoolProgram) -> dict:
    return {
        "id": p.id,
        "country": p.country,
        "school_name": p.school_name,
        "program_name": p.program_name,
        "major_track": p.major_track,
        "degree": p.degree,
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


def _rule_based_summary(ranking: list[dict], dimensions: list[str], note: str) -> str:
    if not ranking:
        return "未选择学校，无法生成建议。"
    top = ranking[0]
    second = ranking[1] if len(ranking) > 1 else None
    cheapest = max(ranking, key=lambda x: x["metrics"]["成本"])  # 成本分越高越省钱

    lines = [
        "## 最终建议（规则评分）",
        f"首选 {top['school']} · {top['program']}，综合分 {top['total_score']}。",
    ]
    if second:
        lines.append(f"备选 {second['school']} · {second['program']}，综合分 {second['total_score']}。")
    lines.append(
        f"如果预算压力较大，可优先考虑 {cheapest['school']} · {cheapest['program']}（成本维度更优）。"
    )
    lines.append(f"重点关注维度：{'、'.join(dimensions)}。")
    lines.append(note)
    lines.append(DISCLAIMER)
    return "\n\n".join(lines)


@router.post("/run", response_model=AnalysisRunResponse)
async def run_analysis(
    payload: AnalysisRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.school_ids:
        raise HTTPException(status_code=400, detail="至少选择一个学校项目")

    programs = (
        db.query(SchoolProgram)
        .filter(SchoolProgram.id.in_(payload.school_ids), SchoolProgram.country == payload.country)
        .all()
    )
    if not programs:
        raise HTTPException(status_code=400, detail="未找到所选国家下的学校项目")

    weights = calc_weights(payload.selected_dimensions)
    ranking = rank_programs(programs, weights)

    schools_json = [_program_to_dict(p) for p in programs]
    prompt = build_prompt(
        country=payload.country,
        major=payload.major,
        budget_max=payload.budget_max,
        selected_dimensions=payload.selected_dimensions,
        weights=weights,
        schools_json=schools_json,
    )

    model_used, summary_markdown = await generate_analysis(prompt)
    if model_used == "rule-based":
        summary_markdown = _rule_based_summary(ranking, payload.selected_dimensions, summary_markdown)
    elif DISCLAIMER not in summary_markdown:
        summary_markdown = summary_markdown + "\n\n" + DISCLAIMER

    record = AnalysisRecord(
        user_id=current_user.id,
        country=payload.country,
        major=payload.major,
        budget_max=payload.budget_max,
        selected_dimensions=payload.selected_dimensions,
        selected_school_ids=payload.school_ids,
        weights=weights,
        model_used=model_used,
        ai_summary_markdown=summary_markdown,
        ranking_table_json=ranking,
        disclaimer=DISCLAIMER,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return AnalysisRunResponse(
        analysis_id=record.id,
        model_used=model_used,
        weights=weights,
        ranking=[RankingItem(**r) for r in ranking],
        summary_markdown=summary_markdown,
        disclaimer=DISCLAIMER,
    )


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

    return AnalysisRecordOut(
        id=row.id,
        country=row.country,
        major=row.major,
        budget_max=row.budget_max,
        selected_dimensions=row.selected_dimensions,
        selected_school_ids=row.selected_school_ids,
        weights=row.weights,
        model_used=row.model_used,
        ranking=[RankingItem(**r) for r in row.ranking_table_json],
        summary_markdown=row.ai_summary_markdown,
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
