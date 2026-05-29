# backend/services/review_analyzer.py
import json
from backend.services.gemini_service import generate_content, clean_json_response
from backend.prompts.analyzer import ANALYZER_SYSTEM_PROMPT


async def analyze_review(
    review_text: str,
    rating: int,
    reviewer_name: str,
    business_name: str,
    industry: str,
) -> dict:
    """Analyze a single review using Gemini."""

    system = ANALYZER_SYSTEM_PROMPT.format(
        industry=industry,
        business_name=business_name,
    )

    prompt = f"""Review from {reviewer_name}:
Rating: {rating}/5 stars
Text: "{review_text}"

Analyze this review and return the JSON analysis."""

    raw_response, prompt_tokens, completion_tokens, latency_ms = await generate_content(
        prompt=prompt,
        system_instruction=system,
        json_mode=True,
        temperature=0.3,
    )

    try:
        analysis = json.loads(clean_json_response(raw_response))
    except json.JSONDecodeError:
        analysis = {
            "sentiment": "negative" if rating <= 2 else "positive" if rating >= 4 else "neutral",
            "sentiment_score": (rating - 3) / 2.0,
            "themes": [],
            "is_urgent": rating <= 2,
            "urgency_reason": "Low rating review" if rating <= 2 else None,
            "summary": f"{rating}-star review from {reviewer_name}",
        }

    analysis["_meta"] = {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_ms": latency_ms,
    }

    return analysis
