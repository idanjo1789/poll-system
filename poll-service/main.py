from fastapi import FastAPI

from controller.questions_controller import router as questions_router
from controller.answers_controller import router as answers_router
from controller.votes_controller import router as votes_router
from controller.internal_controller import router as internal_router
from repository.database import database


app = FastAPI()

app.include_router(questions_router)
app.include_router(answers_router)
app.include_router(votes_router)
app.include_router(internal_router)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/health")
async def health():
    return {"status": "ok", "service": "poll-service"}
