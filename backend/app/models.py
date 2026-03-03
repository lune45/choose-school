from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="user", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    analyses = relationship("AnalysisRecord", back_populates="user")


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(16))
    purpose: Mapped[str] = mapped_column(String(32), default="login")
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SchoolProgram(Base):
    __tablename__ = "school_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    country: Mapped[str] = mapped_column(String(64), index=True)
    school_name: Mapped[str] = mapped_column(String(255), index=True)
    program_name: Mapped[str] = mapped_column(String(255))
    major_track: Mapped[str] = mapped_column(String(64), default="CS")
    degree: Mapped[str] = mapped_column(String(64), default="Master")
    qs_rank: Mapped[float] = mapped_column(Float, default=0)
    usnews_rank: Mapped[float] = mapped_column(Float, default=0)
    times_rank: Mapped[float] = mapped_column(Float, default=0)
    program_duration_months: Mapped[float] = mapped_column(Float, default=0)
    course_list_json: Mapped[list] = mapped_column(JSON, default=list)
    query_output_json: Mapped[dict] = mapped_column(JSON, default=dict)

    tuition_usd: Mapped[float] = mapped_column(Float, default=0)
    living_cost_usd: Mapped[float] = mapped_column(Float, default=0)
    ranking_score: Mapped[float] = mapped_column(Float, default=0)
    median_salary_usd: Mapped[float] = mapped_column(Float, default=0)
    safety_score: Mapped[float] = mapped_column(Float, default=0)
    course_difficulty: Mapped[float] = mapped_column(Float, default=0)
    employment_support: Mapped[float] = mapped_column(Float, default=0)
    visa_support: Mapped[float] = mapped_column(Float, default=0)
    alumni_network: Mapped[float] = mapped_column(Float, default=0)
    immigration_friendly: Mapped[float] = mapped_column(Float, default=0)
    domestic_recognition: Mapped[float] = mapped_column(Float, default=0)

    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AnalysisRecord(Base):
    __tablename__ = "analysis_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    country: Mapped[str] = mapped_column(String(64))
    major: Mapped[str] = mapped_column(String(64), default="CS")
    budget_max: Mapped[float] = mapped_column(Float, default=0)

    selected_dimensions: Mapped[list] = mapped_column(JSON)
    selected_school_ids: Mapped[list] = mapped_column(JSON)
    weights: Mapped[dict] = mapped_column(JSON)
    concerns_json: Mapped[list] = mapped_column(JSON, default=list)
    weights_json: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    error_message: Mapped[str] = mapped_column(Text, default="")
    model_used: Mapped[str] = mapped_column(String(64), default="deepseek-chat")
    ai_summary_markdown: Mapped[str] = mapped_column(Text, default="")
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_ai_response: Mapped[str] = mapped_column(Text, default="")
    ranking_table_json: Mapped[list] = mapped_column(JSON)
    disclaimer: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="analyses")


class SchoolSearchInsight(Base):
    __tablename__ = "school_search_insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    school_program_id: Mapped[int | None] = mapped_column(ForeignKey("school_programs.id"), index=True, nullable=True)
    school_name: Mapped[str] = mapped_column(String(255), index=True)
    program_name: Mapped[str] = mapped_column(String(255), default="")
    source_provider: Mapped[str] = mapped_column(String(64), default="bing")
    raw_text: Mapped[str] = mapped_column(Text)
    edited_text: Mapped[str] = mapped_column(Text, default="")
    search_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    review_note: Mapped[str] = mapped_column(Text, default="")
    reviewed_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
