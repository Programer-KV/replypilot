# backend/services/gemini_service.py
import httpx
import json
import time
import re
from backend.config import get_settings

settings = get_settings()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def clean_json_response(text: str) -> str:
    """Remove markdown code fences from JSON response."""
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()


async def generate_content(
    prompt: str,
    system_instruction: str,
    model: str = None,
    json_mode: bool = False,
    temperature: float = 0.7,
    max_tokens: int = 2048,
) -> tuple:
    """
    Generate content using Gemini via OpenRouter.
    Returns: (response_text, prompt_tokens, completion_tokens, latency_ms)
    """
    start = time.time()

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://replypilot.ai",
        "X-Title": "ReplyPilot",
    }

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": prompt},
    ]

    body = {
        "model": "google/gemini-2.0-flash-001",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    if json_mode:
        body["response_format"] = {"type": "json_object"}

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(OPENROUTER_URL, headers=headers, json=body)
        response.raise_for_status()

    data = response.json()
    latency_ms = int((time.time() - start) * 1000)

    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    return text, prompt_tokens, completion_tokens, latency_ms
