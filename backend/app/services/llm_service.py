import os

import httpx


OPENAI_API_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
LLM_TIMEOUT = 15.0


class LLMServiceError(Exception):
    """LLM API 호출 실패."""


def generate_llm_response(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise LLMServiceError("OPENAI_API_KEY is not configured")

    try:
        response = httpx.post(
            OPENAI_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "instructions": (
                    "You are a financial security assistant. "
                    "Explain login security information clearly "
                    "in Korean. Do not make authentication decisions. "
                    "Do not ask users for passwords or verification codes."
                ),
                "input": prompt,
                "max_output_tokens": 300,
            },
            timeout=LLM_TIMEOUT,
        )

        response.raise_for_status()
        result = response.json()

        texts = [
            content.get("text", "")
            for item in result.get("output", [])
            if item.get("type") == "message"
            for content in item.get("content", [])
            if content.get("type") == "output_text"
        ]

        answer = "\n".join(texts).strip()

        if not answer:
            raise LLMServiceError("LLM returned an empty response")

        return answer

    except httpx.TimeoutException as exc:
        raise LLMServiceError("LLM request timed out") from exc

    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise LLMServiceError("LLM API request failed") from exc