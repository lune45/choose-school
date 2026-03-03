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
    qs_rank: float
    usnews_rank: float
    times_rank: float
    program_duration_months: float
    course_list_json: Optional[List[str]] = Field(default_factory=list)
    query_output_json: Optional[Dict[str, Any]] = Field(default_factory=dict)
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
    qs_rank: float = 0
    usnews_rank: float = 0
    times_rank: float = 0
    program_duration_months: float = 0
    course_list_json: List[str] = Field(default_factory=list)
    query_output_json: Dict[str, Any] = Field(default_factory=dict)
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
    qs_rank: float = 0
    usnews_rank: float = 0
    times_rank: float = 0
    program_duration_months: float = 0
    course_list_json: List[str] = Field(default_factory=list)
    query_output_json: Dict[str, Any] = Field(default_factory=dict)
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


class AdminInsightOut(BaseModel):
    id: int
    school_program_id: Optional[int] = None
    school_name: str
    program_name: str
    source_provider: str
    raw_text: str
    edited_text: str
    search_payload: Dict[str, Any]
    status: str
    review_note: str
    reviewed_by_user_id: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class AdminInsightEditRequest(BaseModel):
    edited_text: str = ""
    review_note: str = ""


class AdminInsightApproveRequest(BaseModel):
    final_text: str = ""
    review_note: str = ""


class AdminInsightRejectRequest(BaseModel):
    review_note: str = ""


class AdminRagSearchRequest(BaseModel):
    country: str = ""
    major: str = ""
    limit: int = Field(default=5, ge=1, le=20)


class AdminRagSearchResponse(BaseModel):
    message: str
    scanned: int
    created: int
    skipped: int
    queued_targets: List[str]
    completed_targets: List[str]
    memory_file: str


class AdminRagMemoryResponse(BaseModel):
    today: str
    long_term_instruction: str = ""
    ranking_sources: List[str] = Field(default_factory=list)
    priority_targets: List[str] = Field(default_factory=list)
    todo: List[str]
    done: List[str]
    retry_queue: List[Dict[str, Any]] = Field(default_factory=list)
    failure_history: List[Dict[str, Any]] = Field(default_factory=list)
    logs: List[str]
    raw_markdown: str


class AdminRagMemoryUpdateRequest(BaseModel):
    raw_markdown: str = ""
    long_term_instruction: str = ""
    ranking_sources: List[str] = Field(default_factory=list)
    priority_targets: List[str] = Field(default_factory=list)


class AdminRagChatRequest(BaseModel):
    message: str = ""
    quick_action: str = ""
    country: str = ""
    major: str = ""
    limit: int = Field(default=5, ge=1, le=20)


class AdminRagChatResponse(BaseModel):
    role: str = "assistant"
    reply: str
    scanned: int = 0
    created: int = 0
    skipped: int = 0
    completed_targets: List[str] = Field(default_factory=list)
    memory_excerpt: str = ""


class AnalysisRunRequest(BaseModel):
    country: str
    major: str = "CS"
    budget_max: float = 0
    selected_dimensions: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    weights: Dict[str, int] = Field(default_factory=dict)
    school_ids: List[int] = Field(default_factory=list)
    schools: List[int] = Field(default_factory=list)


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
    concerns_json: List[str] = Field(default_factory=list)
    weights_json: Dict[str, int] = Field(default_factory=dict)
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
    concerns_json: List[str] = Field(default_factory=list)
    selected_school_ids: List[int]
    weights: Dict[str, int]
    weights_json: Dict[str, int] = Field(default_factory=dict)
    model_used: str
    ranking: List[RankingItem]
    summary_markdown: str
    result_json: Dict[str, Any]
    disclaimer: str
    created_at: datetime


class SchoolCatalogItemOut(BaseModel):
    school_name: str
    display_rank: float
    ranking_source: str
    countries: List[str]
    program_count: int
    avg_tuition_usd: float
    avg_living_cost_usd: float
    sample_programs: List[str]


class ProgramBriefOut(BaseModel):
    id: int
    program_name: str
    major_track: str
    degree: str
    program_duration_months: float
    course_count: int
    tuition_usd: float
    living_cost_usd: float
    median_salary_usd: float


class SchoolDetailOut(BaseModel):
    school_name: str
    rankings: Dict[str, float]
    countries: List[str]
    program_count: int
    avg_tuition_usd: float
    avg_living_cost_usd: float
    programs: List[ProgramBriefOut]
