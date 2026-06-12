from fastapi import FastAPI
from app.routers.users import router as users_router

from app.db.base import Base
from app.db.database import engine

import app.models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fintech Lending Platform")
app.include_router(users_router)


@app.get("/")
def health_check():
    return {"status": "running"}
