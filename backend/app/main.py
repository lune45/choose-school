from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .database import Base, SessionLocal, engine, run_sqlite_migrations
from .routers.admin import router as admin_router
from .routers.analysis import router as analysis_router
from .routers.auth import router as auth_router
from .routers.report import router as report_router
from .routers.schools import router as schools_router
from .seed_data import seed_schools

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
run_sqlite_migrations()
with SessionLocal() as db:
    seed_schools(db)

app.include_router(auth_router)
app.include_router(schools_router)
app.include_router(analysis_router)
app.include_router(report_router)
app.include_router(admin_router)

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def root():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Study Planner API is running"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
