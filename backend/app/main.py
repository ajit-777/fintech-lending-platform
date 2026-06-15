from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.security import HTTPBearer

from app.db.base import Base
from app.db.database import engine
import app.models

from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.loans import router as loans_router
from app.routers.users import router as users_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Fintech Lending Platform",
    swagger_ui_init_oauth={},
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

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(loans_router)
app.include_router(admin_router)


@app.get("/")
def health_check():
    return {"status": "running"}
