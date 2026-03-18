import time

from openai import OpenAI

from common.config import INFERENCE_BASE_URL, INFERENCE_API_KEY, INFERENCE_MODEL

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=INFERENCE_BASE_URL, api_key=INFERENCE_API_KEY)
    return _client


def complete(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 2000,
    max_retries: int = 2,
) -> str:
    """Send a chat completion request. Returns the content string."""
    client = _get_client()
    model = model or INFERENCE_MODEL

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            if attempt == max_retries:
                raise
            time.sleep(1)
