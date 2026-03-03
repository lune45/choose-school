from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SchoolProgram, User
from ..schemas import ProgramBriefOut, SchoolCatalogItemOut, SchoolDetailOut, SchoolOut, UploadExcelResponse
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


def _rank_of(program: SchoolProgram, source: str) -> float:
    source = (source or "qs").lower()
    if source == "usnews":
        value = float(program.usnews_rank or 0)
    elif source == "times":
        value = float(program.times_rank or 0)
    else:
        value = float(program.qs_rank or 0)
    if value > 0:
        return value
    if float(program.ranking_score or 0) > 0:
        return max(1.0, round(101 - float(program.ranking_score), 1))
    return 9999.0


@router.get("/school-directory", response_model=list[SchoolCatalogItemOut])
def list_school_directory(
    ranking_source: str = Query("qs"),
    q: str = Query(""),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(SchoolProgram)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (SchoolProgram.school_name.ilike(like)) | (SchoolProgram.program_name.ilike(like))
        )
    rows = query.all()
    grouped: dict[str, list[SchoolProgram]] = {}
    for row in rows:
        grouped.setdefault(row.school_name, []).append(row)

    items: list[SchoolCatalogItemOut] = []
    for school_name, programs in grouped.items():
        ranks = [_rank_of(p, ranking_source) for p in programs]
        rank = min(ranks) if ranks else 9999
        countries = sorted(set([p.country for p in programs if p.country]))
        avg_tuition = round(sum(float(p.tuition_usd or 0) for p in programs) / max(1, len(programs)), 2)
        avg_living = round(sum(float(p.living_cost_usd or 0) for p in programs) / max(1, len(programs)), 2)
        sample_programs = [p.program_name for p in sorted(programs, key=lambda x: _rank_of(x, ranking_source))[:3]]
        items.append(
            SchoolCatalogItemOut(
                school_name=school_name,
                display_rank=rank if rank < 9999 else 0,
                ranking_source=ranking_source.lower(),
                countries=countries,
                program_count=len(programs),
                avg_tuition_usd=avg_tuition,
                avg_living_cost_usd=avg_living,
                sample_programs=sample_programs,
            )
        )
    items.sort(key=lambda x: (x.display_rank <= 0, x.display_rank if x.display_rank > 0 else 9999, x.school_name))
    return items


@router.get("/school-directory/{school_name}", response_model=SchoolDetailOut)
def get_school_detail(
    school_name: str = Path(...),
    ranking_source: str = Query("qs"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = db.query(SchoolProgram).filter(SchoolProgram.school_name == school_name).all()
    if not rows:
        raise HTTPException(status_code=404, detail="学校不存在")

    rankings = {
        "qs": min([_rank_of(r, "qs") for r in rows]),
        "usnews": min([_rank_of(r, "usnews") for r in rows]),
        "times": min([_rank_of(r, "times") for r in rows]),
    }
    rankings = {k: (v if v < 9999 else 0) for k, v in rankings.items()}
    programs = sorted(rows, key=lambda x: _rank_of(x, ranking_source))
    countries = sorted(set([p.country for p in rows if p.country]))
    avg_tuition = round(sum(float(p.tuition_usd or 0) for p in rows) / max(1, len(rows)), 2)
    avg_living = round(sum(float(p.living_cost_usd or 0) for p in rows) / max(1, len(rows)), 2)

    return SchoolDetailOut(
        school_name=school_name,
        rankings=rankings,
        countries=countries,
        program_count=len(rows),
        avg_tuition_usd=avg_tuition,
        avg_living_cost_usd=avg_living,
        programs=[
            ProgramBriefOut(
                id=p.id,
                program_name=p.program_name,
                major_track=p.major_track,
                degree=p.degree,
                program_duration_months=p.program_duration_months,
                course_count=len(p.course_list_json or []),
                tuition_usd=p.tuition_usd,
                living_cost_usd=p.living_cost_usd,
                median_salary_usd=p.median_salary_usd,
            )
            for p in programs
        ],
    )


@router.get("/school-programs/{program_id}", response_model=SchoolOut)
def get_program_detail(
    program_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    row = db.query(SchoolProgram).filter(SchoolProgram.id == program_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="项目不存在")
    return SchoolOut.model_validate(row, from_attributes=True)


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
