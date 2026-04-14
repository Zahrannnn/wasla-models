"""
Tenacity retry configuration for LLM API calls.

Apply ``@llm_retry`` to any async function that calls the LLM API.
Retries on rate-limit (429) and transient server errors (5xx)
up to 5 times with exponential delays (2 s -> 60 s).
"""

from __future__ import annotations

import logging

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from openai import RateLimitError, APIConnectionError, APITimeoutError

logger = logging.getLogger("wasla.retries")


llm_retry = retry(
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    before_sleep=lambda rs: logger.warning(
        "LLM rate-limited — retrying in %.1f s (attempt %d)",
        rs.next_action.sleep,  # type: ignore[union-attr]
        rs.attempt_number,
    ),
    reraise=True,
)
