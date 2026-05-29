# backend/services/report_generator.py
from backend.services.gemini_service import generate_content
from backend.prompts.reports import REPORT_SYSTEM_PROMPT
from datetime import date


async def generate_weekly_report(
    reviews: list,
    insights: dict,
    business_name: str,
    industry: str,
    period_start: date,
    period_end: date,
) -> dict:
    """Generate a human-readable weekly report."""

    system = REPORT_SYSTEM_PROMPT.format(
        industry=industry,
        business_name=business_name,
    )

    total = len(reviews)
    if total > 0:
        avg_rating = sum(r.get("rating", 3) for r in reviews) / total
        sentiment_counts = {}
        for r in reviews:
            s = r.get("ai_sentiment", "unknown")
            sentiment_counts[s] = sentiment_counts.get(s, 0) + 1
    else:
        avg_rating = 0
        sentiment_counts = {}

    prompt = f"""Generate a weekly report for {business_name}.

Period: {period_start.isoformat()} to {period_end.isoformat()}

Metrics:
- Total new reviews this week: {total}
- Average rating: {avg_rating:.1f}
- Sentiment breakdown: {sentiment_counts}

AI-Generated Insights:
{insights.get('executive_summary', 'No summary available')}

Top positive themes: {[t.get('theme', '') for t in insights.get('top_positive_themes', [])]}
Top negative themes: {[t.get('theme', '') for t in insights.get('top_negative_themes', [])]}

Write the weekly report now."""

    raw_report, prompt_tokens, completion_tokens, latency_ms = await generate_content(
        prompt=prompt,
        system_instruction=system,
        temperature=0.6,
        max_tokens=1000,
    )

    return {
        "report_text": raw_report.strip(),
        "metrics": {
            "total_reviews": total,
            "average_rating": round(avg_rating, 1),
            "sentiment_breakdown": sentiment_counts,
        },
        "_meta": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
        },
    }
