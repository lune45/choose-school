from __future__ import annotations

import csv
import re
from io import BytesIO, StringIO
from typing import Dict, List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SchoolProgram, User
from ..schemas import AdminImportResponse, AdminSchoolCreate, AdminSchoolUpdate, SchoolOut
from ..security import get_admin_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

COLUMNS = [
    "country",
    "school_name",
    "program_name",
    "major_track",
    "degree",
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
    "country": ["country", "国家", "留学国家"],
    "school_name": ["school_name", "学校", "院校", "学校名称"],
    "program_name": ["program_name", "项目", "项目名称", "专业项目", "program"],
    "major_track": ["major_track", "方向", "专业方向", "track"],
    "degree": ["degree", "学位"],
    "tuition_usd": ["tuition_usd", "学费", "tuition"],
    "living_cost_usd": ["living_cost_usd", "生活费", "living_cost"],
    "ranking_score": ["ranking_score", "排名分", "排名", "ranking"],
    "median_salary_usd": ["median_salary_usd", "毕业薪资中位数", "薪资中位数", "salary"],
    "safety_score": ["safety_score", "安全分", "安全度", "safety"],
    "course_difficulty": ["course_difficulty", "课程难度", "难度"],
    "employment_support": ["employment_support", "就业支持", "就业服务"],
    "visa_support": ["visa_support", "工签支持", "签证支持"],
    "alumni_network": ["alumni_network", "校友网络", "校友"],
    "immigration_friendly": ["immigration_friendly", "移民友好度", "移民友好", "h1b绿卡"],
    "domestic_recognition": ["domestic_recognition", "回国认可度", "国内认可度"],
    "notes": ["notes", "备注", "说明"],
}

NUMERIC_FIELDS = {
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



def _resolve_column_map(df_cols: List[str]) -> Dict[str, str]:
    normalized = {_norm(c): c for c in df_cols}
    resolved: Dict[str, str] = {}
    for target, aliases in ALIASES.items():
        for alias in aliases:
            alias_key = _norm(alias)
            if alias_key in normalized:
                resolved[target] = normalized[alias_key]
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
    row = SchoolProgram(**payload.model_dump())
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

    for k, v in payload.model_dump().items():
        setattr(row, k, v)
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
            else:
                if val is None or str(val).strip().lower() in {"", "nan", "none"}:
                    item[field] = ""
                else:
                    item[field] = str(val).strip()

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
            updated += 1
        else:
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

    csv_io = StringIO()
    writer = csv.DictWriter(csv_io, fieldnames=COLUMNS)
    writer.writeheader()
    writer.writerow(sample)

    data = "\ufeff" + csv_io.getvalue()
    return StreamingResponse(
        iter([data]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=school_import_template.csv"},
    )
