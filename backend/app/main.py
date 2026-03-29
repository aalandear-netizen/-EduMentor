"""
EduMentor FastAPI application entry point.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import tutoring, kg

app = FastAPI(
    title="EduMentor API",
    version="1.0.0",
    description="AI-powered adaptive STEM tutoring backend.",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(tutoring.router, prefix="/tutoring", tags=["tutoring"])
app.include_router(kg.router, prefix="/kg", tags=["knowledge-graph"])


# ---------------------------------------------------------------------------
# Health / readiness probes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    return {"status": "ready"}
