# backend/routers/review_router.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, Depends, Query
from backend.auth import get_current_user
from backend.database import supabase
from backend.services.google_places import fetch_and_store_reviews
from backend.services.review_analyzer import analyze_review
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/businesses/{business_id}/fetch-reviews")
async def fetch_reviews(business_id: str, current_user: dict = Depends(get_current_user)):
    biz = supabase.table("businesses").select("*").eq(
        "id", business_id
    ).eq("owner_id", current_user["id"]).single().execute()

    if not biz.data:
        raise HTTPException(status_code=404, detail="Business not found")

    business = biz.data

    if not business.get("google_place_id"):
        raise HTTPException(status_code=400, detail="No Google Place ID configured")

    fetch_result = await fetch_and_store_reviews(business_id, business["google_place_id"])

    unanalyzed = supabase.table("reviews").select("*").eq(
        "business_id", business_id
    ).is_("ai_sentiment", "null").execute()

    analyzed_count = 0
    for review in (unanalyzed.data or []):
        if not review.get("review_text"):
            continue

        try:
            analysis = await analyze_review(
                review_text=review["review_text"],
                rating=review["rating"],
                reviewer_name=review.get("reviewer_name", "Anonymous"),
                business_name=business["name"],
                industry=business.get("industry", "general"),
            )

            supabase.table("reviews").update({
                "ai_sentiment": analysis.get("sentiment"),
                "ai_sentiment_score": analysis.get("sentiment_score"),
                "ai_themes": analysis.get("themes", []),
                "ai_is_urgent": analysis.get("is_urgent", False),
                "ai_urgency_reason": analysis.get("urgency_reason"),
                "ai_summary": analysis.get("summary"),
                "ai_analyzed_at": datetime.utcnow().isoformat(),
            }).eq("id", review["id"]).execute()

            if analysis.get("is_urgent"):
                supabase.table("alerts").insert({
                    "id": str(uuid.uuid4()),
                    "business_id": business_id,
                    "alert_type": "urgent_review",
                    "title": f"Urgent: {review.get('reviewer_name', 'Customer')} left a {review['rating']}-star review",
                    "message": analysis.get("urgency_reason", "Low rating review"),
                    "related_review_id": review["id"],
                }).execute()

            analyzed_count += 1

            meta = analysis.get("_meta", {})
            supabase.table("activity_log").insert({
                "id": str(uuid.uuid4()),
                "business_id": business_id,
                "action": "review_analyzed",
                "actor": "ai",
                "details": {
                    "review_id": review["id"],
                    "sentiment": analysis.get("sentiment"),
                    "themes": analysis.get("themes"),
                    "is_urgent": analysis.get("is_urgent"),
                },
                "gemini_model": "gemini-2.0-flash",
                "processing_time_ms": meta.get("latency_ms"),
            }).execute()

        except Exception as e:
            print(f"Error analyzing review {review['id']}: {e}")
            continue

    return {
        "fetch_result": fetch_result,
        "analyzed": analyzed_count,
    }


@router.get("/businesses/{business_id}/reviews")
async def list_reviews(
    business_id: str,
    sentiment: str = Query(None),
    urgent_only: bool = Query(False),
    min_rating: int = Query(None),
    max_rating: int = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    current_user: dict = Depends(get_current_user),
):
    biz = supabase.table("businesses").select("id").eq(
        "id", business_id
    ).eq("owner_id", current_user["id"]).execute()

    if not biz.data:
        raise HTTPException(status_code=404, detail="Business not found")

    query = supabase.table("reviews").select(
        "*, ai_responses(response_text, status, created_at)"
    ).eq("business_id", business_id)

    if sentiment:
        query = query.eq("ai_sentiment", sentiment)
    if urgent_only:
        query = query.eq("ai_is_urgent", True)
    if min_rating is not None:
        query = query.gte("rating", min_rating)
    if max_rating is not None:
        query = query.lte("rating", max_rating)

    query = query.order("review_date", desc=True).range(offset, offset + limit - 1)
    result = query.execute()

    reviews = []
    for r in (result.data or []):
        latest_response = None
        if r.get("ai_responses"):
            sorted_responses = sorted(
                r["ai_responses"],
                key=lambda x: x.get("created_at", ""),
                reverse=True,
            )
            if sorted_responses:
                latest_response = sorted_responses[0]["response_text"]

        reviews.append({
            "id": r["id"],
            "business_id": r["business_id"],
            "reviewer_name": r.get("reviewer_name"),
            "reviewer_avatar_url": r.get("reviewer_avatar_url"),
            "rating": r["rating"],
            "review_text": r.get("review_text"),
            "review_date": r.get("review_date"),
            "owner_response": r.get("owner_response"),
            "ai_sentiment": r.get("ai_sentiment"),
            "ai_sentiment_score": r.get("ai_sentiment_score"),
            "ai_themes": r.get("ai_themes"),
            "ai_is_urgent": r.get("ai_is_urgent", False),
            "ai_urgency_reason": r.get("ai_urgency_reason"),
            "ai_summary": r.get("ai_summary"),
            "has_ai_response": latest_response is not None,
            "ai_response_status": r.get("ai_response_status"),
            "latest_ai_response": latest_response,
            "created_at": r["created_at"],
        })

    return reviews


@router.get("/businesses/{business_id}/reviews/stats")
async def get_review_stats(business_id: str, current_user: dict = Depends(get_current_user)):
    biz = supabase.table("businesses").select("id").eq(
        "id", business_id
    ).eq("owner_id", current_user["id"]).execute()

    if not biz.data:
        raise HTTPException(status_code=404, detail="Business not found")

    result = supabase.table("reviews").select(
        "rating, ai_sentiment, ai_themes, ai_is_urgent, has_ai_response"
    ).eq("business_id", business_id).execute()

    reviews = result.data or []
    total = len(reviews)

    if total == 0:
        return {
            "total_reviews": 0,
            "average_rating": 0.0,
            "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            "sentiment_breakdown": {},
            "urgent_count": 0,
            "response_rate": 0.0,
            "top_themes": [],
        }

    rating_dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in reviews:
        rating_dist[r["rating"]] = rating_dist.get(r["rating"], 0) + 1

    sentiment_breakdown = {}
    for r in reviews:
        s = r.get("ai_sentiment", "unknown")
        sentiment_breakdown[s] = sentiment_breakdown.get(s, 0) + 1

    theme_counts = {}
    for r in reviews:
        for theme in (r.get("ai_themes") or []):
            theme_counts[theme] = theme_counts.get(theme, 0) + 1
    top_themes = sorted(
        [{"theme": k, "count": v} for k, v in theme_counts.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    responded = sum(1 for r in reviews if r.get("has_ai_response"))
    urgent_count = sum(1 for r in reviews if r.get("ai_is_urgent"))

    return {
        "total_reviews": total,
        "average_rating": round(sum(r["rating"] for r in reviews) / total, 2),
        "rating_distribution": rating_dist,
        "sentiment_breakdown": sentiment_breakdown,
        "urgent_count": urgent_count,
        "response_rate": round((responded / total) * 100, 1),
        "top_themes": top_themes,
    }
