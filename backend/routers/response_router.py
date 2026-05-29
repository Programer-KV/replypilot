# backend/routers/response_router.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Depends
from backend.auth import get_current_user
from backend.database import supabase
from backend.services.response_generator import generate_review_response
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/reviews/{review_id}/generate-response")
async def generate_response(review_id: str, current_user: dict = Depends(get_current_user)):
    review_result = supabase.table("reviews").select("*, businesses(*)").eq(
        "id", review_id
    ).single().execute()

    if not review_result.data:
        raise HTTPException(status_code=404, detail="Review not found")

    review = review_result.data
    business = review.get("businesses", {})

    if business.get("owner_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not review.get("review_text"):
        raise HTTPException(status_code=400, detail="Review has no text")

    result = await generate_review_response(
        review_text=review["review_text"],
        rating=review["rating"],
        reviewer_name=review.get("reviewer_name", "there"),
        business_name=business.get("name", "Our Business"),
        industry=business.get("industry", "general"),
        brand_voice=business.get("brand_voice_description", "professional and friendly"),
        tone=business.get("tone_preset", "warm"),
        ai_sentiment=review.get("ai_sentiment", "neutral"),
        ai_themes=review.get("ai_themes", []),
        ai_summary=review.get("ai_summary", ""),
        owner_response=review.get("owner_response"),
    )

    response_id = str(uuid.uuid4())
    supabase.table("ai_responses").insert({
        "id": response_id,
        "review_id": review_id,
        "business_id": review["business_id"],
        "response_text": result["response_text"],
        "status": "draft",
        "gemini_model_used": "gemini-2.0-flash",
        "prompt_tokens": result["_meta"]["prompt_tokens"],
        "completion_tokens": result["_meta"]["completion_tokens"],
        "tone_used": result["tone_used"],
        "key_points_addressed": result["key_points_addressed"],
    }).execute()

    supabase.table("reviews").update({
        "has_ai_response": True,
        "ai_response_status": "draft",
    }).eq("id", review_id).execute()

    supabase.table("activity_log").insert({
        "id": str(uuid.uuid4()),
        "business_id": review["business_id"],
        "action": "response_generated",
        "actor": "ai",
        "details": {
            "review_id": review_id,
            "rating": review["rating"],
            "sentiment": review.get("ai_sentiment"),
            "response_length": len(result["response_text"]),
        },
        "gemini_model": "gemini-2.0-flash",
        "processing_time_ms": result["_meta"]["latency_ms"],
    }).execute()

    return {
        "id": response_id,
        "review_id": review_id,
        "response_text": result["response_text"],
        "status": "draft",
        "tone_used": result["tone_used"],
        "key_points_addressed": result["key_points_addressed"],
        "created_at": datetime.utcnow().isoformat(),
    }


@router.get("/reviews/{review_id}/responses")
async def list_responses(review_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase.table("ai_responses").select("*").eq(
        "review_id", review_id
    ).order("created_at", desc=True).execute()

    return result.data or []


@router.put("/responses/{response_id}")
async def edit_response(response_id: str, data: dict, current_user: dict = Depends(get_current_user)):
    result = supabase.table("ai_responses").update({
        "edited_response": data.get("response_text"),
        "status": "edited",
    }).eq("id", response_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Response not found")

    return result.data[0]


@router.post("/responses/{response_id}/approve")
async def approve_response(response_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase.table("ai_responses").update({
        "status": "approved",
        "approved_by": current_user["id"],
        "approved_at": datetime.utcnow().isoformat(),
    }).eq("id", response_id).execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Response not found")

    r = result.data[0]

    supabase.table("reviews").update({
        "ai_response_status": "approved",
    }).eq("id", r["review_id"]).execute()

    supabase.table("activity_log").insert({
        "id": str(uuid.uuid4()),
        "business_id": r.get("business_id"),
        "action": "response_approved",
        "actor": "user",
        "details": {"response_id": response_id, "review_id": r["review_id"]},
    }).execute()

    return r


@router.post("/responses/{response_id}/reject")
async def reject_response(response_id: str, current_user: dict = Depends(get_current_user)):
    supabase.table("ai_responses").update({"status": "rejected"}).eq("id", response_id).execute()
    return {"status": "rejected", "id": response_id}
