from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SendCodeRequest(BaseModel):
    phone: str
    purpose: str = "login"


class RegisterRequest(BaseModel):
    phone: str
    password: str = Field(min_length=6, max_length=64)
    code: str


class LoginPasswordRequest(BaseModel):
    phone: str
    password: str


class LoginCodeRequest(BaseModel):
    phone: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    phone: str
    role: str


class SchoolOut(BaseModel):
    id: int
    country: str
    school_name: str
    program_name: str
    major_track: str
    degree: str
    tuition_usd: float
    living_cost_usd: float
    ranking_score: float
    median_salary_usd: float
    safety_score: float
    course_difficulty: float
    employment_support: float
    visa_support: float
    alumni_network: float
    immigration_friendly: float
    domestic_recognition: float
    notes: str


class UploadExcelResponse(BaseModel):
    matched_school_ids: List[int]
    matched_labels: List[str]
    unmatched_cells: List[str]


class AdminSchoolCreate(BaseModel):
    country: str
    school_name: str
    program_name: str
    major_track: str = "CS"
    degree: str = "Master"
    tuition_usd: float = 0
    living_cost_usd: float = 0
    ranking_score: float = 0
    median_salary_usd: float = 0
    safety_score: float = 0
    course_difficulty: float = 0
    employment_support: float = 0
    visa_support: float = 0
    alumni_network: float = 0
    immigration_friendly: float = 0
    domestic_recognition: float = 0
    notes: str = ""


class AdminSchoolUpdate(BaseModel):
    country: str
    school_name: str
    program_name: str
    major_track: str = "CS"
    degree: str = "Master"
    tuition_usd: float = 0
    living_cost_usd: float = 0
    ranking_score: float = 0
    median_salary_usd: float = 0
    safety_score: float = 0
    course_difficulty: float = 0
    employment_support: float = 0
    visa_support: float = 0
    alumni_network: float = 0
    immigration_friendly: float = 0
    domestic_recognition: float = 0
    notes: str = ""


class AdminImportResponse(BaseModel):
    created: int
    updated: int
    errors: List[str]


class AnalysisRunRequest(BaseModel):
    country: str
    major: str = "CS"
    budget_max: float = 0
    selected_dimensions: List[str]
    school_ids: List[int]


class RankingItem(BaseModel):
    rank: int
    school_id: int
    school: str
    program: str
    total_score: float
    metrics: Dict[str, float]


class AnalysisRunResponse(BaseModel):
    analysis_id: int
    status: str
    error_message: Optional[str] = None
    model_used: str
    weights: Dict[str, int]
    ranking: List[RankingItem]
    summary_markdown: str
    result_json: Dict[str, Any]
    disclaimer: str


class AnalysisRecordOut(BaseModel):
    id: int
    status: str
    error_message: Optional[str] = None
    country: str
    major: str
    budget_max: float
    selected_dimensions: List[str]
    selected_school_ids: List[int]
    weights: Dict[str, int]
    model_used: str
    ranking: List[RankingItem]
    summary_markdown: str
    result_json: Dict[str, Any]
    disclaimer: str
    created_at: datetime
