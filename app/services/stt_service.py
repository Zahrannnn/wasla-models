"""
STT service — Speech-to-text via Hugging Face Inference API.

Uses ``openai/whisper-large-v3-turbo`` on the free HF Inference API
to transcribe audio bytes to text.  No local GPU required.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from huggingface_hub import InferenceClient

from app.core.config import get_settings
from app.utils.retries import hf_retry

logger = logging.getLogger("wasla.stt")
_settings = get_settings()


@lru_cache(maxsize=1)
def _get_client() -> InferenceClient:
    return InferenceClient(
        model=_settings.stt_model,
        token=_settings.huggingface_token,
    )


@hf_retry
async def transcribe_audio(audio_bytes: bytes) -> str:
    """
    Transcribe raw audio bytes to text.

    Parameters
    ----------
    audio_bytes : bytes
        WAV / FLAC / MP3 / WebM audio data.

    Returns
    -------
    Transcribed text string.
    """
    import asyncio

    client = _get_client()

    # InferenceClient.automatic_speech_recognition is synchronous,
    # so we run it in a thread to avoid blocking the event loop.
    result = await asyncio.to_thread(
        client.automatic_speech_recognition, audio_bytes
    )

    text = result.text if hasattr(result, "text") else str(result)
    logger.info("STT transcribed %d audio bytes → %d chars", len(audio_bytes), len(text))
    return text.strip()
