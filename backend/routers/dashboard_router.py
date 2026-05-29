# backend/routers/dashboard_router.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Depends
from backend.auth import get_current_user
from backend.database import supabase

router = APIRouter()


@router.get("/businesses/{business_id}/dashboard")
async def get_dashboard(business_id: str, current_user: dict = Depends(get_current_user)):
    biz_result = supabase.table("businesses").select("*").eq(
        "id", business_id
    ).eq("owner_id", current_user["id"]).single().execute()

    if not biz_result.data:
        raise HTTPException(status_code=404, detail="Business not found")

    business = biz_result.data

    reviews_result = supabase.table("reviews").select("*").eq(
        "business_id", business_id
    ).order("review_date", desc=True).limit(50).execute()
    reviews = reviews_result.data or []

    responses_result = supabase.table("ai_responses").select("*").eq(
        "business_id", business_id
    ).order("created_at", desc=True).limit(10).execute()
    responses = responses_result.data or []

    alerts_result = supabase.table("alerts").select("*").eq(
        "business_id", business_id
    ).eq("is_read", False).order("created_at", desc=True).limit(10).execute()
    alerts = alerts_result.data or []

    ops_result = supabase.table("activity_log").select(
        "id", count="exact"
    ).eq("business_id", business_id).eq("actor", "ai").execute()
    ai_ops_count = ops_result.count or 0

    total = len(reviews)
    avg_rating = (sum(r["rating"] for r in reviews) / total) if total > 0 else 0.0
    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    sentiment_dist = {}
    theme_counts = {}
    urgent_count = 0
    responded_count = 0

    for r in reviews:
        rating_dist[r["rating"]] = rating_dist.get(r["rating"], 0) + 1
        s = r.get("ai_sentiment", "unknown")
        sentiment_dist[s] = sentiment_dist.get(s, 0) + 1
        for theme in (r.get("ai_themes") or []):
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
        if r.get("ai_is_urgent"):
            urgent_count += 1
        if r.get("has_ai_response"):
            responded_count += 1

    top_themes = sorted(
        [{"theme": k, "count": v} for k, v in theme_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    response_rate = (responded_count / total * 100) if total > 0 else 0.0
    time_saved = responded_count * 5

    return {
        "business": {
            "id": business["id"],
            "name": business["name"],
            "industry": business.get("industry"),
            "subscription_status": business.get("subscription_status"),
            "subscription_plan": business.get("subscription_plan"),
        },
        "stats": {
            "total_reviews": total,
            "average_rating": round(avg_rating, 1),
            "rating_distribution": rating_dist,
            "sentiment_breakdown": sentiment_dist,
            "urgent_count": urgent_count,
            "response_rate": round(response_rate, 1),
            "top_themes": top_themes,
        },
        "recent_reviews": [
            {
                "id": r["id"],
                "reviewer_name": r.get("reviewer_name"),
                "rating": r["rating"],
                "review_text": r.get("review_text"),
                "review_date": r.get("review_date"),
                "ai_sentiment": r.get("ai_sentiment"),
                "ai_themes": r.get("ai_themes"),
                "ai_is_urgent": r.get("ai_is_urgent", False),
                "ai_summary": r.get("ai_summary"),
                "has_ai_response": r.get("has_ai_response", False),
            }
            for r in reviews[:10]
        ],
        "recent_responses": [
            {
                "id": r["id"],
                "review_id": r["review_id"],
                "response_text": r["response_text"],
                "status": r["status"],
                "created_at": r["created_at"],
            }
            for r in responses
        ],
        "unread_alerts": [
            {
                "id": a["id"],
                "alert_type": a["alert_type"],
                "title": a["title"],
                "message": a["message"],
                "created_at": a["created_at"],
            }
            for a in alerts
        ],
        "ai_operations_count": ai_ops_count,
        "time_saved_minutes": time_saved,
    }


@router.get("/businesses/{business_id}/activity")
async def get_activity_log(
    business_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    biz = supabase.table("businesses").select("id").eq(
        "id", business_id
    ).eq("owner_id", current_user["id"]).execute()

    if not biz.data:
        raise HTTPException(status_code=404, detail="Business not found")

    result = supabase.table("activity_log").select("*").eq(
        "business_id", business_id
    ).order("created_at", desc=True).limit(limit).execute()

    return result.data or []
