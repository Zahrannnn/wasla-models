"""
Voice routes.

Route 4  — POST /api/voice/tts                        → audio/wav bytes
Route 5  — WS   /api/voice/conversation/{company_id}   → full-duplex voice
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from app.api.dependencies import TTSRequest
from app.services.llm_service import stream_chat
from app.services.stt_service import transcribe_audio
from app.services.tts_service import synthesize_speech, stream_speech

logger = logging.getLogger("wasla.routes.voice")
router = APIRouter(tags=["Voice"])


# ─────────────────────────────────────────────────────────────────
#  Route 4 — TTS (one-shot)
# ─────────────────────────────────────────────────────────────────
@router.post(
    "/api/voice/tts",
    summary="Route 4 — Text-to-speech (one-shot)",
    operation_id="textToSpeech",
    response_description="WAV audio file (24 kHz, mono, PCM16).",
    responses={
        200: {
            "description": "Audio file generated successfully.",
            "content": {"audio/wav": {}},
        },
        503: {"description": "TTS service is unavailable."},
    },
)
async def text_to_speech(body: TTSRequest):
    """
    **Convert text to speech** using Kokoro-82M (local model, 24 kHz mono).

    Returns raw WAV audio bytes. The frontend can play this directly
    via an `<audio>` element or the Web Audio API.

    - **Model:** `hexgrad/Kokoro-82M` (Apache-2.0, runs locally)
    - **Voice:** configurable via `TTS_VOICE` env var (default: `af_heart`)
    - **Max text length:** 1 000 characters
    """
    try:
        audio_bytes = await synthesize_speech(body.text)
    except Exception as exc:
        logger.exception("TTS failed")
        raise HTTPException(
            status_code=503,
            detail="Text-to-speech service is unavailable.",
        ) from exc

    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=speech.wav"},
    )


# ─────────────────────────────────────────────────────────────────
#  Route 5 — Voice Conversation (WebSocket)
# ─────────────────────────────────────────────────────────────────
#
#  Protocol (JSON messages over WebSocket):
#
#  CLIENT → SERVER:
#    { "type": "audio", "data": "<base64 audio>" }
#        Raw audio from the microphone (WAV/WebM/MP3).
#
#    { "type": "text", "data": "typed user message" }
#        Optional: user may also type a message instead.
#
#    { "type": "end" }
#        Client signals end of conversation.
#
#  SERVER → CLIENT:
#    { "type": "transcript", "data": "transcribed text" }
#        The STT result so the UI can display it.
#
#    { "type": "llm_token", "data": "token" }
#        Each streamed LLM token (for live caption display).
#
#    { "type": "audio", "data": "<base64 PCM16 chunk>" }
#        Streaming TTS audio chunk (24 kHz mono PCM16).
#        First chunk is a 44-byte WAV header.
#
#    { "type": "done" }
#        Turn is complete — client can start next recording.
#
#    { "type": "error", "data": "error message" }
#        Something went wrong.
#
# ─────────────────────────────────────────────────────────────────

@router.websocket("/api/voice/conversation/{company_id}")
async def voice_conversation(ws: WebSocket, company_id: str):
    """
    **Route 5 — Full-duplex voice conversation via WebSocket.**

    Maintains multi-turn conversation context. Each turn flows:

    1. **Client → Server:** `{"type": "audio", "data": "<base64>"}` or `{"type": "text", "data": "..."}`
    2. **Server → Client:** `{"type": "transcript", "data": "..."}` (STT result)
    3. **Server → Client:** `{"type": "llm_token", "data": "..."}` (streamed, one per token)
    4. **Server → Client:** `{"type": "audio", "data": "<base64 PCM16>"}` (streamed TTS chunks, 24 kHz)
    5. **Server → Client:** `{"type": "done"}` (turn complete)

    Send `{"type": "end"}` to gracefully close the conversation.

    **Models used:** Whisper large-v3-turbo (STT) → Llama-3.1-8B (LLM) → Kokoro-82M (TTS)
    """
    await ws.accept()
    logger.info("Voice WS connected — company=%s", company_id)

    # Persistent conversation history for multi-turn context
    conversation: list[dict] = [
        {
            "role": "system",
            "content": (
                f"You are a friendly voice assistant for company '{company_id}'. "
                "Keep answers concise — under 3 sentences. "
                "Do NOT use markdown, bullet points, or code blocks. "
                "Speak naturally as if talking on the phone."
            ),
        },
    ]

    try:
        while True:
            # ── 1. Receive client message ─────────────────────────
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "data": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            if msg_type == "end":
                logger.info("Client ended conversation — company=%s", company_id)
                break

            # ── 2. Get user text (from audio or directly) ─────────
            user_text = ""

            if msg_type == "audio":
                audio_b64 = msg.get("data", "")
                if not audio_b64:
                    await ws.send_json({"type": "error", "data": "Empty audio"})
                    continue

                try:
                    audio_bytes = base64.b64decode(audio_b64)
                    user_text = await transcribe_audio(audio_bytes)
                except Exception as exc:
                    logger.error("STT failed: %s", exc)
                    await ws.send_json({"type": "error", "data": f"Transcription failed: {exc}"})
                    continue

                # Send transcript back so the UI can display it
                await ws.send_json({"type": "transcript", "data": user_text})

            elif msg_type == "text":
                user_text = msg.get("data", "").strip()

            if not user_text:
                await ws.send_json({"type": "error", "data": "No speech detected"})
                continue

            # ── 3. Stream LLM response ────────────────────────────
            conversation.append({"role": "user", "content": user_text})

            llm_messages = list(conversation)  # shallow copy
            full_response = []

            async for sse_frame in stream_chat(llm_messages):
                # sse_frame is "data: token\n\n" or "data: [DONE]\n\n"
                token = sse_frame.removeprefix("data: ").rstrip("\n")
                if token in ("[DONE]", "") or token.startswith("[ERROR]"):
                    continue
                full_response.append(token)
                await ws.send_json({"type": "llm_token", "data": token})

            assistant_text = "".join(full_response)
            conversation.append({"role": "assistant", "content": assistant_text})

            # ── 4. Stream TTS audio ───────────────────────────────
            if assistant_text:
                try:
                    async for audio_chunk in stream_speech(assistant_text):
                        chunk_b64 = base64.b64encode(audio_chunk).decode("ascii")
                        await ws.send_json({"type": "audio", "data": chunk_b64})
                except Exception as exc:
                    logger.error("TTS streaming failed: %s", exc)
                    await ws.send_json({"type": "error", "data": f"TTS failed: {exc}"})

            # ── 5. Signal turn complete ───────────────────────────
            await ws.send_json({"type": "done"})

    except WebSocketDisconnect:
        logger.info("Voice WS disconnected — company=%s", company_id)
    except Exception as exc:
        logger.exception("Voice WS error — company=%s", company_id)
        try:
            await ws.send_json({"type": "error", "data": str(exc)})
        except Exception:
            pass
