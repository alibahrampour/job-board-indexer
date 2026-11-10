from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, companies, health, jobs, sources
from app.config import settings

app = FastAPI(
    title="Job Board Indexer",
    version="0.1.0",
    description="Aggregates, normalizes and serves job postings from ATS platforms and job boards.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(companies.router)
app.include_router(jobs.router)
app.include_router(sources.router)
app.include_router(admin.router)
