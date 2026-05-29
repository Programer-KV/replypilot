# backend/main.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.config import get_settings
from backend.services.scheduler import start_scheduler, shutdown_scheduler

from backend.routers import auth_router, business_router, review_router
from backend.routers import response_router, dashboard_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router, prefix="/api/auth", tags=["Auth"])
app.include_router(business_router.router, prefix="/api/businesses", tags=["Businesses"])
app.include_router(review_router.router, prefix="/api", tags=["Reviews"])
app.include_router(response_router.router, prefix="/api", tags=["AI Responses"])
app.include_router(dashboard_router.router, prefix="/api", tags=["Dashboard"])


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
