import sys
import os

_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "ReplyPilot"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    FRONTEND_URL: str = "http://localhost:8501"

    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_KEY: str
    DATABASE_URL: str

    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OPENROUTER_API_KEY: str = "placeholder"


    GOOGLE_PLACES_API_KEY: str = "placeholder"
    STRIPE_SECRET_KEY: str = "placeholder"
    STRIPE_PUBLISHABLE_KEY: str = "placeholder"
    STRIPE_WEBHOOK_SECRET: str = "placeholder"
    STRIPE_STARTER_PRICE_ID: str = "placeholder"
    STRIPE_GROWTH_PRICE_ID: str = "placeholder"
    STRIPE_AGENCY_PRICE_ID: str = "placeholder"

    RESEND_API_KEY: str = "placeholder"
    FROM_EMAIL: str = "replypilot@mail.replypilot.ai"

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 72

    class Config:
        env_file = os.path.join(_project_root, ".env")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
