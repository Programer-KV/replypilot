# backend/services/insight_engine.py
import json
from backend.services.gemini_service import generate_content, clean_json_response
from backend.prompts.insights import INSIGHTS_SYSTEM_PROMPT


async def generate_business_insights(
    reviews: list,
    business_name: str,
    industry: str,
) -> dict:
    """Generate business insights from a collection of reviews."""

    system = INSIGHTS_SYSTEM_PROMPT.format(
        industry=industry,
        business_name=business_name,
    )

    reviews_text_parts = []
    for i, r in enumerate(reviews, 1):
        part = (
            f"Review {i}: {r.get('reviewer_name', 'Anonymous')} "
            f"({r.get('rating', '?')}/5 stars)\n"
            f"Date: {r.get('review_date', 'unknown')}\n"
            f'"{r.get("review_text", "No text")}"'
        )
        if r.get("ai_sentiment"):
            part += f"\n[AI: sentiment={r['ai_sentiment']}, themes={r.get('ai_themes', [])}]"
        reviews_text_parts.append(part)

    reviews_text = "\n\n---\n\n".join(reviews_text_parts)

    prompt = f"""Here are {len(reviews)} customer reviews:

{reviews_text}

Analyze all reviews together and generate business insights."""

    raw_response, prompt_tokens, completion_tokens, latency_ms = await generate_content(
        prompt=prompt,
        system_instruction=system,
        json_mode=True,
        temperature=0.4,
        max_tokens=3000,
    )

    try:
        insights = json.loads(clean_json_response(raw_response))
    except json.JSONDecodeError:
        insights = {
            "overall_health": "unknown",
            "average_sentiment_score": 0.0,
            "top_positive_themes": [],
            "top_negative_themes": [],
            "operational_insights": [],
            "competitive_advantages": [],
            "improvement_priorities": [],
            "executive_summary": "Unable to generate insights.",
        }

    insights["_meta"] = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_ms": latency_ms,
        "reviews_analyzed": len(reviews),
    }

    return insights
