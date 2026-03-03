import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .analysis import create_analysis_from_payload
from ..database import get_db
from ..models import AnalysisRecord, User
from ..schemas import AnalysisRecordOut, AnalysisRunRequest, AnalysisRunResponse, RankingItem
from ..security import get_current_user

router = APIRouter(prefix="/api/report", tags=["report"])


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


@router.post("/create", response_model=AnalysisRunResponse)
async def create_report(
    payload: AnalysisRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await create_analysis_from_payload(payload, db, current_user)


@router.get("/{analysis_id}", response_model=AnalysisRecordOut)
def get_report(
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
