"""
TTS service — Kokoro-82M local text-to-speech.

Uses the ``kokoro`` Python library to run the Kokoro-82M model
locally.  It's only 82 M parameters, Apache-licensed, and fast
enough for real-time use — no paid API needed.

The model weights are downloaded once on first use and cached
by Hugging Face Hub automatically.

Public API
----------
* ``synthesize_speech(text)``  → full WAV bytes  (Route 4)
* ``stream_speech(text)``      → async generator of PCM16 chunks  (WS)
"""

from __future__ import annotations

import asyncio
import io
import logging
import struct
from functools import lru_cache
from typing import AsyncIterator

import numpy as np
import soundfile as sf

from app.core.config import get_settings

logger = logging.getLogger("wasla.tts")
_settings = get_settings()

# 24 kHz mono — Kokoro's native sample rate
SAMPLE_RATE = 24_000


@lru_cache(maxsize=1)
def _get_pipeline():
    """Lazy-load the Kokoro pipeline (downloads weights on first call)."""
    from kokoro import KPipeline
    logger.info("Loading Kokoro TTS pipeline (voice=%s) …", _settings.tts_voice)
    return KPipeline(lang_code=_settings.tts_lang_code)


def _float_to_pcm16(audio: np.ndarray) -> bytes:
    """Convert float32 numpy audio to 16-bit PCM bytes."""
    # Clip to [-1, 1] and scale to int16 range
    audio = np.clip(audio, -1.0, 1.0)
    pcm = (audio * 32767).astype(np.int16)
    return pcm.tobytes()


def _make_wav_header(data_size: int) -> bytes:
    """Build a minimal WAV header for 24 kHz mono PCM16."""
    channels = 1
    sample_width = 2  # 16-bit
    byte_rate = SAMPLE_RATE * channels * sample_width
    block_align = channels * sample_width
    # RIFF header + fmt chunk + data chunk header
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,       # file size - 8
        b"WAVE",
        b"fmt ",
        16,                   # fmt chunk size
        1,                    # PCM format
        channels,
        SAMPLE_RATE,
        byte_rate,
        block_align,
        16,                   # bits per sample
        b"data",
        data_size,
    )
    return header


# ─────────────────────────────────────────────────────────────────
#  Full-file synthesis  (Route 4 — POST /api/voice/tts)
# ─────────────────────────────────────────────────────────────────

async def synthesize_speech(text: str) -> bytes:
    """
    Convert *text* to WAV audio bytes using Kokoro-82M.

    Returns
    -------
    Raw WAV bytes (24 kHz, mono, PCM16).
    """
    try:
        pipeline = _get_pipeline()

        audio_chunks: list[np.ndarray] = []
        for _gs, _ps, audio in pipeline(text, voice=_settings.tts_voice):
            audio_chunks.append(audio)

        if not audio_chunks:
            raise RuntimeError("Kokoro produced no audio output")

        full_audio = np.concatenate(audio_chunks)

        # Encode as WAV in memory
        pcm_data = _float_to_pcm16(full_audio)
        wav_bytes = _make_wav_header(len(pcm_data)) + pcm_data

        logger.info(
            "TTS generated %d bytes (%.1f s) for %d chars",
            len(wav_bytes),
            len(full_audio) / SAMPLE_RATE,
            len(text),
        )
        return wav_bytes

    except Exception as exc:
        logger.error("TTS synthesis failed: %s", exc)
        raise


# ─────────────────────────────────────────────────────────────────
#  Streaming synthesis  (WebSocket voice conversation)
# ─────────────────────────────────────────────────────────────────

async def stream_speech(text: str) -> AsyncIterator[bytes]:
    """
    Yield PCM16 audio chunks as Kokoro generates them.

    Each chunk is raw 24 kHz mono 16-bit PCM (no WAV header).
    The first yielded item is a 44-byte WAV header so the
    receiver can start playback immediately; subsequent items
    are raw PCM data.

    This enables the WebSocket endpoint to push audio to the
    client as soon as the first sentence is synthesized, rather
    than waiting for the full utterance.
    """
    pipeline = _get_pipeline()

    header_sent = False
    total_samples = 0

    for _gs, _ps, audio in pipeline(text, voice=_settings.tts_voice):
        pcm = _float_to_pcm16(audio)

        if not header_sent:
            # Send a WAV header with max data_size — the client
            # should play incrementally and not rely on the header
            # length field (streaming pattern).
            yield _make_wav_header(0xFFFFFFFF)
            header_sent = True

        yield pcm
        total_samples += len(audio)
        # Let the event loop breathe between chunks
        await asyncio.sleep(0)

    logger.info(
        "TTS streamed %.1f s of audio for %d chars",
        total_samples / SAMPLE_RATE,
        len(text),
    )

