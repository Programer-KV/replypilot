# backend/routers/business_router.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Depends
from backend.auth import get_current_user
from backend.database import supabase
from backend.models import BusinessCreate, BusinessUpdate, BusinessResponse
import uuid
from datetime import datetime, timedelta

router = APIRouter()


@router.post("", response_model=BusinessResponse)
async def create_business(data: BusinessCreate, current_user: dict = Depends(get_current_user)):
    business_id = str(uuid.uuid4())

    place_id = data.google_place_id
    if data.google_maps_url and not place_id:
        import re
        match = re.search(r'place/([^/]+)/([^/]+)', data.google_maps_url)
        if match:
            place_id = match.group(2)

    result = supabase.table("businesses").insert({
        "id": business_id,
        "owner_id": current_user["id"],
        "name": data.name,
        "google_place_id": place_id,
        "google_maps_url": data.google_maps_url,
        "industry": data.industry,
        "brand_voice_description": data.brand_voice_description,
        "tone_preset": data.tone_preset,
        "subscription_status": "trial",
        "subscription_plan": "growth",
        "trial_ends_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
    }).execute()

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create business")

    biz = result.data[0]
    return BusinessResponse(
        id=biz["id"],
        name=biz["name"],
        industry=biz["industry"],
        google_place_id=biz.get("google_place_id"),
        brand_voice_description=biz["brand_voice_description"],
        tone_preset=biz["tone_preset"],
        subscription_status=biz["subscription_status"],
        subscription_plan=biz["subscription_plan"],
        created_at=biz["created_at"],
    )


@router.get("", response_model=list)
async def list_businesses(current_user: dict = Depends(get_current_user)):
    result = supabase.table("businesses").select("*").eq(
        "owner_id", current_user["id"]
    ).order("created_at", desc=True).execute()

    businesses = []
    for biz in (result.data or []):
        reviews_result = supabase.table("reviews").select(
            "rating"
        ).eq("business_id", biz["id"]).execute()

        reviews = reviews_result.data or []
        total = len(reviews)
        avg_rating = (sum(r["rating"] for r in reviews) / total) if total > 0 else 0.0

        businesses.append({
            "id": biz["id"],
            "name": biz["name"],
            "industry": biz["industry"],
            "google_place_id": biz.get("google_place_id"),
            "brand_voice_description": biz["brand_voice_description"],
            "tone_preset": biz["tone_preset"],
            "subscription_status": biz["subscription_status"],
            "subscription_plan": biz["subscription_plan"],
            "total_reviews": total,
            "average_rating": round(avg_rating, 1),
            "response_rate": 0.0,
            "created_at": biz["created_at"],
        })

    return businesses


@router.get("/{business_id}")
async def get_business(business_id: str, current_user: dict = Depends(get_current_user)):
    result = supabase.table("businesses").select("*").eq(
        "id", business_id
    ).eq("owner_id", current_user["id"]).single().execute()

    if not result.data:
        raise HTTPException(status_code=404, detail="Business not found")

    biz = result.data
    return biz


@router.put("/{business_id}")
async def update_business(
    business_id: str,
    data: BusinessUpdate,
    current_user: dict = Depends(get_current_user),
):
    existing = supabase.table("businesses").select("id").eq(
        "id", business_id
    ).eq("owner_id", current_user["id"]).execute()

    if not existing.data:
        raise HTTPException(status_code=404, detail="Business not found")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow().isoformat()

    result = supabase.table("businesses").update(update_data).eq("id", business_id).execute()
    return result.data[0]
