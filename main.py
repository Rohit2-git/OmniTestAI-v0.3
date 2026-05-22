from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.database import db
from app.routers import health, tests, results, generate, execute

app = FastAPI(
    title="OmniTestAI",
    description="Agentic test automation API — Web, API, Performance, Accessibility, Security, Mobile",
    version="1.0.0"
)


@app.on_event("startup")
async def startup():
    await db.connect()


@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()


app.include_router(health.router)
app.include_router(tests.router)
app.include_router(results.router)
app.include_router(generate.router)
app.include_router(execute.router)