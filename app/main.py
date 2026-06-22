from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.employees import router as employees_router
from app.api.holidays import router as holidays_router
from app.api.reports import router as reports_router
from app.api.summary import router as summary_router
from app.api.worklogs import router as worklogs_router
from app.core.config import get_settings
from app.core.logging_config import setup_logging
from app.scheduler.scheduler import scheduler
from app.api.worklist import router as worklist_router

setup_logging()
settings = get_settings()

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(employees_router)
app.include_router(reports_router)
app.include_router(summary_router)
app.include_router(worklogs_router)
app.include_router(holidays_router)
app.include_router(audit_router)
app.include_router(worklist_router)


@app.get("/health")
def health():
    return {"status": "ok", "app": settings.app_name}


@app.on_event("startup")
def startup():
    scheduler.start()


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()
