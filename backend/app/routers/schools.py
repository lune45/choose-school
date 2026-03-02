from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SchoolProgram, User
from ..schemas import SchoolOut, UploadExcelResponse
from ..security import get_current_user
from ..services.excel_match import match_excel_schools

router = APIRouter(prefix="/api", tags=["schools"])


@router.get("/countries")
def list_countries(db: Session = Depends(get_db)):
    rows = db.query(distinct(SchoolProgram.country)).all()
    return {"countries": [x[0] for x in rows]}


@router.get("/schools", response_model=list[SchoolOut])
def list_schools(
    country: str = Query(...),
    q: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(SchoolProgram).filter(SchoolProgram.country == country)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (SchoolProgram.school_name.ilike(like)) | (SchoolProgram.program_name.ilike(like))
        )
    rows = query.order_by(SchoolProgram.ranking_score.desc()).all()
    return [SchoolOut.model_validate(r, from_attributes=True) for r in rows]


@router.post("/schools/upload-excel", response_model=UploadExcelResponse)
async def upload_excel(
    file: UploadFile = File(...),
    country: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="请上传Excel文件")

    content = await file.read()
    query = db.query(SchoolProgram)
    if country:
        query = query.filter(SchoolProgram.country == country)
    programs = query.all()

    if not programs:
        raise HTTPException(status_code=404, detail="数据库中暂无可匹配学校")

    matched_ids, matched_labels, unmatched_cells = match_excel_schools(content, programs)
    return UploadExcelResponse(
        matched_school_ids=matched_ids,
        matched_labels=matched_labels,
        unmatched_cells=unmatched_cells,
    )
