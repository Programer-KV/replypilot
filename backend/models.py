# backend/models.py
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class ResponseStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    EDITED = "edited"
    POSTED = "posted"
    REJECTED = "rejected"

class SubscriptionStatus(str, Enum):
    TRIAL = "trial"
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"

class SubscriptionPlan(str, Enum):
    STARTER = "starter"
    GROWTH = "growth"
    AGENCY = "agency"


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class BusinessCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None
    industry: str = Field(default="general")
    brand_voice_description: str = Field(
        default="professional and friendly",
        max_length=1000
    )
    tone_preset: str = Field(default="warm")

class BusinessUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    brand_voice_description: Optional[str] = None
    tone_preset: Optional[str] = None
    google_place_id: Optional[str] = None
    google_maps_url: Optional[str] = None

class BusinessResponse(BaseModel):
    id: str
    name: str
    industry: str
    google_place_id: Optional[str]
    brand_voice_description: str
    tone_preset: str
    subscription_status: str
    subscription_plan: str
    total_reviews: int = 0
    average_rating: float = 0.0
    response_rate: float = 0.0
    created_at: datetime


class ReviewResponse(BaseModel):
    id: str
    business_id: str
    reviewer_name: Optional[str]
    reviewer_avatar_url: Optional[str]
    rating: int
    review_text: Optional[str]
    review_date: Optional[datetime]
    owner_response: Optional[str]
    ai_sentiment: Optional[str]
    ai_sentiment_score: Optional[float]
    ai_themes: Optional[list[str]]
    ai_is_urgent: bool = False
    ai_urgency_reason: Optional[str]
    ai_summary: Optional[str]
    has_ai_response: bool = False
    ai_response_status: Optional[str]
    latest_ai_response: Optional[str]
    created_at: datetime

class ReviewStats(BaseModel):
    total_reviews: int
    average_rating: float
    rating_distribution: dict
    sentiment_breakdown: dict
    urgent_count: int
    response_rate: float
    top_themes: list[dict]


class AIResponseResult(BaseModel):
    id: str
    review_id: str
    response_text: str
    status: str
    tone_used: str
    key_points_addressed: list[str]
    created_at: datetime

class ResponseEdit(BaseModel):
    response_text: str = Field(min_length=1, max_length=2000)


class BusinessInsights(BaseModel):
    overall_health: str
    average_sentiment_score: float
    top_positive_themes: list[dict]
    top_negative_themes: list[dict]
    operational_insights: list[dict]
    competitive_advantages: list[str]
    improvement_priorities: list[dict]
    executive_summary: str


class ReportResponse(BaseModel):
    id: str
    business_id: str
    report_type: str
    period_start: str
    period_end: str
    total_reviews: int
    new_reviews: int
    average_rating: float
    rating_change: Optional[float]
    sentiment_breakdown: Optional[dict]
    executive_summary: Optional[str]
    key_insights: Optional[list[str]]
    created_at: datetime


class CheckoutRequest(BaseModel):
    plan: SubscriptionPlan
