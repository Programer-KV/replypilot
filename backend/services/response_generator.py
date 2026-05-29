# backend/services/response_generator.py
from backend.services.gemini_service import generate_content
from backend.prompts.responder import RESPONDER_SYSTEM_PROMPT


TONE_MAP = {
    "warm": "Warm, friendly, and personal. Like talking to a neighbor.",
    "professional": "Professional and courteous. Respectful but approachable.",
    "casual": "Casual and relaxed. Conversational, like texting a friend.",
    "formal": "Formal and polished. Like a well-written business letter.",
    "enthusiastic": "Enthusiastic and energetic. Show genuine excitement.",
}


async def generate_review_response(
    review_text: str,
    rating: int,
    reviewer_name: str,
    business_name: str,
    industry: str,
    brand_voice: str,
    tone: str,
    ai_sentiment: str,
    ai_themes: list,
    ai_summary: str,
    owner_response: str = None,
) -> dict:
    """Generate a personalized response to a review."""

    tone_description = TONE_MAP.get(tone, TONE_MAP["warm"])

    system = RESPONDER_SYSTEM_PROMPT.format(
        business_name=business_name,
        industry=industry,
        brand_voice=brand_voice,
        tone=tone_description,
    )

    context_parts = [
        f"Reviewer: {reviewer_name}",
        f"Rating: {rating}/5 stars",
        f"Sentiment: {ai_sentiment}",
        f"Key themes: {', '.join(ai_themes)}",
        f"Summary: {ai_summary}",
        f'\nFull review text:\n"{review_text}"',
    ]

    if owner_response:
        context_parts.append(
            f"\nNote: The business owner already responded. Generate a BETTER version."
        )

    prompt = "\n".join(context_parts)

    raw_response, prompt_tokens, completion_tokens, latency_ms = await generate_content(
        prompt=prompt,
        system_instruction=system,
        temperature=0.7,
        max_tokens=500,
    )

    response_text = raw_response.strip().strip('"').strip("'")

    key_points = []
    for theme in ai_themes:
        if theme.replace("_", " ") in response_text.lower():
            key_points.append(theme)

    return {
        "response_text": response_text,
        "tone_used": tone,
        "key_points_addressed": key_points,
        "_meta": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
        },
    }
