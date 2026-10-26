"""Groq-backed financial assistant.

Credentials must be supplied by server-side GROQ_API_KEY. Never commit API keys.
"""
import logging
import os

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"


class AIProviderError(Exception):
    """A safe, user-displayable AI service failure."""

    def __init__(self, message: str, *, code: str, status_code: int = 503):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def ask_openai(prompt: str, user_currency: str = "INR") -> str:
    """Get a Groq response via its OpenAI-compatible API."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise AIProviderError(
            "AI is not configured. The server administrator needs to set GROQ_API_KEY.",
            code="missing_api_key",
        )

    system_prompt = (
        "You are a finance-focused AI assistant. Give educational information, "
        "not individualized professional financial advice. Always use "
        f"{user_currency} for monetary amounts unless the user requests another currency. "
        "Be concise and accurate. Do not render charts as ASCII text."
    )

    try:
        client = OpenAI(
            api_key=api_key,
            base_url=GROQ_BASE_URL,
            timeout=25.0,
            max_retries=1,
        )
        response = client.chat.completions.create(
            model=os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=1000,
        )
    except AuthenticationError:
        logger.warning("Groq rejected the configured API key (401)")
        raise AIProviderError(
            "AI authentication failed. The server administrator must replace the Groq API key.",
            code="invalid_api_key",
        ) from None
    except RateLimitError:
        logger.warning("Groq rate limit or quota exceeded (429)")
        raise AIProviderError(
            "The AI provider's rate limit or quota was reached. Try again later.",
            code="rate_limited",
            status_code=429,
        ) from None
    except (APIConnectionError, APITimeoutError):
        logger.warning("Could not reach Groq API")
        raise AIProviderError(
            "The AI provider is temporarily unreachable. Please try again.",
            code="provider_unavailable",
        ) from None
    except APIStatusError as error:
        logger.warning("Groq request failed with status %s", error.status_code)
        raise AIProviderError(
            "The AI provider rejected this request. Check the configured model and provider account.",
            code="provider_request_failed",
            status_code=502,
        ) from None
    except OpenAIError:
        logger.warning("Groq SDK failed")
        raise AIProviderError(
            "The AI provider encountered a problem. Please try again.",
            code="provider_error",
            status_code=502,
        ) from None

    if not response.choices or not response.choices[0].message.content:
        raise AIProviderError(
            "The AI provider returned an empty response. Please try again.",
            code="empty_response",
            status_code=502,
        )

    return response.choices[0].message.content.strip()
