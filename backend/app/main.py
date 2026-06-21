import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer

from app.db.base import Base
from app.db.database import SessionLocal, engine
import app.models

from app.routers.admin import router as admin_router
from app.routers.agreement import router as agreement_router
from app.routers.auth import router as auth_router
from app.routers.kyc import router as kyc_router
from app.routers.loans import router as loans_router
from app.routers.users import router as users_router
from app.services import overdue

logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)


def _run_mark_overdue():
    db = SessionLocal()
    try:
        count = overdue.mark_overdue(db)
        if count:
            logger.info("Overdue job: marked %d installment(s) overdue", count)
        else:
            logger.debug("Overdue job: no installments to mark overdue")
    except Exception:
        logger.exception("Overdue job failed")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    # Run daily at 00:30 IST (19:00 UTC previous day) — after midnight so all due dates have passed
    scheduler.add_job(_run_mark_overdue, "cron", hour=19, minute=0, timezone="UTC", id="mark_overdue")
    scheduler.start()
    logger.info("Scheduler started — overdue job runs daily at 00:30 IST")

    # Run once at startup to catch any installments missed while server was down
    _run_mark_overdue()

    yield

    scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Fintech Lending Platform",
    swagger_ui_init_oauth={},
    lifespan=lifespan,
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version="0.1.0",
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            if "security" in operation:
                operation["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(kyc_router)
app.include_router(loans_router)
app.include_router(agreement_router)
app.include_router(admin_router)


@app.get("/")
def health_check():
    return {"status": "running"}
