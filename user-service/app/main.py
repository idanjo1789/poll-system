
from fastapi import FastAPI

from app.config import SERVICE_NAME
from app.db import database
from app.controllers.user_controller import router as users_router

app = FastAPI(title=SERVICE_NAME)


app.include_router(users_router)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/health")
def health():
    return {"status": "ok"}

