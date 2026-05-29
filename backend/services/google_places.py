# backend/services/google_places.py
import re
import uuid
from datetime import datetime
from backend.database import supabase


async def extract_place_id(maps_url: str) -> str | None:
    """Extract Google Place ID from a Google Maps URL."""
    patterns = [
        r'place/[^/]+/([A-Za-z0-9_-]+)',
        r'place_id=([A-Za-z0-9_-]+)',
        r'cid=(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, maps_url)
        if match:
            return match.group(1)
    return None


def fetch_reviews_for_place(place_id: str) -> list:
    """Fetch reviews for a Google Place using the Places API."""
    import googlemaps
    from backend.config import get_settings

    settings = get_settings()
    gmaps = googlemaps.Client(key=settings.GOOGLE_PLACES_API_KEY)

    try:
        result = gmaps.place(
            place_id=place_id,
            fields=["reviews", "name", "rating", "user_ratings_total"],
            reviews_sort="newest",
        )

        place_data = result.get("result", {})
        raw_reviews = place_data.get("reviews", [])

        reviews = []
        for r in raw_reviews:
            owner_resp = r.get("owner_response")
            owner_text = None
            if owner_resp and isinstance(owner_resp, dict):
                owner_text = owner_resp.get("text")

            reviews.append({
                "external_id": str(r.get("time", "")),
                "reviewer_name": r.get("author_name", "Anonymous"),
                "reviewer_avatar_url": r.get("profile_photo_url"),
                "rating": r.get("rating", 3),
                "review_text": r.get("text", ""),
                "review_date": datetime.fromtimestamp(r.get("time", 0)).isoformat(),
                "owner_response": owner_text,
                "source": "google",
            })

        return reviews

    except Exception as e:
        print(f"Error fetching reviews: {e}")
        return []


async def fetch_and_store_reviews(business_id: str, place_id: str) -> dict:
    """Fetch reviews from Google and store them."""
    import time
    start = time.time()

    biz_result = supabase.table("businesses").select("*").eq("id", business_id).single().execute()
    business = biz_result.data

    if not business:
        return {"error": "Business not found", "new_reviews": 0}

    raw_reviews = fetch_reviews_for_place(place_id)

    if not raw_reviews:
        return {"error": "No reviews found or API error", "new_reviews": 0}

    existing = supabase.table("reviews").select("external_id").eq(
        "business_id", business_id
    ).execute()
    existing_ids = {r["external_id"] for r in (existing.data or [])}

    new_reviews = [r for r in raw_reviews if r["external_id"] not in existing_ids]

    if not new_reviews:
        return {"new_reviews": 0, "total_fetched": len(raw_reviews), "message": "No new reviews"}

    stored_count = 0
    for review in new_reviews:
        review_data = {
            "id": str(uuid.uuid4()),
            "business_id": business_id,
            "source": review["source"],
            "external_id": review["external_id"],
            "reviewer_name": review["reviewer_name"],
            "reviewer_avatar_url": review["reviewer_avatar_url"],
            "rating": review["rating"],
            "review_text": review["review_text"],
            "review_date": review["review_date"],
            "owner_response": review.get("owner_response"),
        }

        result = supabase.table("reviews").insert(review_data).execute()
        if result.data:
            stored_count += 1

    elapsed = int((time.time() - start) * 1000)

    supabase.table("activity_log").insert({
        "id": str(uuid.uuid4()),
        "business_id": business_id,
        "action": "reviews_fetched",
        "actor": "system",
        "details": {
            "source": "google",
            "fetched": len(raw_reviews),
            "new": stored_count,
            "duplicates_skipped": len(raw_reviews) - stored_count,
        },
        "processing_time_ms": elapsed,
    }).execute()

    return {
        "new_reviews": stored_count,
        "total_fetched": len(raw_reviews),
        "duplicates_skipped": len(raw_reviews) - stored_count,
    }
