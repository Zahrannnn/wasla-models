# Wasla AI Agent Backend

> AI chat backend powered by **free Hugging Face open-weights models**.
> Drop-in replacement for Google Gemini-2.5-Flash.

---

## Architecture

```
ai_agent_backend/
├── requirements.txt
├── .env
└── app/
    ├── main.py                     # FastAPI app init, CORS, lifespan
    ├── core/
    │   ├── config.py               # Pydantic BaseSettings (env var validation)
    ├── api/
    │   ├── dependencies.py         # Reusable deps (company_id, schemas)
    │   └── routes/
    │       ├── chat.py             # Route 1 (Main Chat) & Route 2 (Voice Stream)
    │       └── voice.py            # Route 4 (TTS) & Route 5 (Voice Conversation WS)
    ├── services/
    │   ├── llm_service.py          # Hugging Face LLM logic & tool-calling loop
    │   ├── tts_service.py          # Kokoro-82M local text-to-speech (full + streaming)
    │   └── stt_service.py          # Whisper STT via HF Inference API
    ├── tools/
    │   ├── schemas.py              # Tool definitions (JSON schemas for the LLM)
    │   ├── operations.py           # The actual functions (Read, Write, Navigate)
    │   └── registry.py             # Maps tool JSON names → Python functions
    └── utils/
        ├── context_manager.py      # Trims chat history to fit 8k token limits
        └── retries.py              # Tenacity config for HF free-tier 429 errors
```

---

## Routes

| Route | Endpoint | Model | Purpose |
|-------|----------|-------|---------|
| **1** | `POST /api/chat/{company_id}` | `Llama-3.3-70B-Instruct` | Main chat — 3-iteration tool-calling loop |
| **2** | `POST /api/chat/{company_id}/stream` | `Llama-3.1-8B-Instruct` | Voice SSE streaming (low latency) |
| **4** | `POST /api/voice/tts` | `Kokoro-82M (local)` | Text-to-speech (one-shot) |
| **5** | `WS /api/voice/conversation/{company_id}` | Whisper + Llama-3.1-8B + Kokoro | Full-duplex voice conversation |
| — | `GET /health` | — | Service status & model info |

### Model Selection

| Use Case | Primary | Fallback |
|----------|---------|----------|
| Complex tool calling | `meta-llama/Llama-3.3-70B-Instruct` | `Qwen/Qwen2.5-72B-Instruct` |
| Voice streaming | `meta-llama/Llama-3.1-8B-Instruct` | — |
| Text-to-speech | `hexgrad/Kokoro-82M` (local) | — |
| Speech-to-text | `openai/whisper-large-v3-turbo` (HF API) | — |

---

## Quick Start

### 1. Install

```bash
cd wasla-models
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — set HUGGINGFACE_TOKEN at minimum
```

### 3. Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

---

## 🐳 Docker Deployment (Recommended)

For easy deployment and distribution to teams, use Docker:

### Quick Docker Start

```bash
# 1. Configure API key
cp .env.example .env
# Edit .env and set LLM_API_KEY

# 2. Start with Docker Compose
docker-compose up -d

# 3. Access API
# http://localhost:8000/docs
```

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed deployment guide or [QUICKSTART.md](QUICKSTART.md) for the fastest way to get started.

---

## API Reference

### Route 1 — Main Chat

```http
POST /api/chat/{company_id}
Content-Type: application/json

{
  "prompt": "Show me the top 5 customers",
  "conversation_history": []
}
```

```json
{
  "response": "Here are your top 5 customers...",
  "tool_calls_made": 1,
  "model_used": "meta-llama/Llama-3.3-70B-Instruct"
}
```

### Route 2 — Voice Stream (SSE)

```http
POST /api/chat/{company_id}/stream
Content-Type: application/json

{
  "prompt": "What are today's sales?",
  "conversation_history": []
}
```

Response: `text/event-stream`
```
data: Today's
data:  sales
data:  look
data:  great!
data: [DONE]
```

### Route 4 — TTS (one-shot)

```http
POST /api/voice/tts
Content-Type: application/json

{ "text": "Hello, welcome to Wasla." }
```

Response: `audio/wav` binary

### Route 5 — Voice Conversation (WebSocket)

```
WS /api/voice/conversation/{company_id}
```

**Full-duplex voice conversation.** Each turn:
1. Client sends recorded audio → server transcribes (Whisper STT)
2. Server streams LLM response tokens (live captions)
3. Server streams TTS audio chunks (Kokoro)
4. Server signals turn complete → client can speak again

#### Client → Server messages

```jsonc
// Send recorded audio (base64-encoded WAV/WebM/MP3)
{ "type": "audio", "data": "<base64 audio bytes>" }

// Or send text directly (skip STT)
{ "type": "text", "data": "typed user message" }

// End the conversation
{ "type": "end" }
```

#### Server → Client messages

```jsonc
{ "type": "transcript", "data": "what the user said" }   // STT result
{ "type": "llm_token",  "data": "Hello"  }               // streamed LLM token
{ "type": "audio",      "data": "<base64 PCM16 chunk>" } // TTS audio chunk (24kHz mono)
{ "type": "done" }                                        // turn complete
{ "type": "error",      "data": "error message" }        // error
```

#### JavaScript example

```javascript
const ws = new WebSocket("ws://localhost:8000/api/voice/conversation/my-company");

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === "transcript")  showTranscript(msg.data);
  if (msg.type === "llm_token")   appendCaption(msg.data);
  if (msg.type === "audio")       playAudioChunk(atob(msg.data));
  if (msg.type === "done")        enableMicrophone();
};

// Send recorded audio
function sendAudio(blob) {
  const reader = new FileReader();
  reader.onload = () => {
    const b64 = btoa(String.fromCharCode(...new Uint8Array(reader.result)));
    ws.send(JSON.stringify({ type: "audio", data: b64 }));
  };
  reader.readAsArrayBuffer(blob);
}
```

---

## 🚨 Migration Warnings (Gemini → Hugging Face)

### 1. Context Window Collapse

| Model | Window |
|-------|--------|
| Gemini 2.5 Flash | **1 000 000 tokens** |
| HF Free Tier | **~8 192 tokens** |

**Handled by:** `app/utils/context_manager.py` — `trim_messages()` automatically truncates history, keeping the system prompt + most recent messages.

### 2. WebRTC / Route 3 is Dead

Gemini Live's proprietary WebRTC audio-to-audio has **no equivalent** on HF.

**Replacement:** Route 5 WebSocket — full-duplex voice conversation using Whisper STT → LLM streaming → Kokoro TTS streaming.

### 3. Free Tier Rate Limits (HTTP 429)

**Handled by:** `app/utils/retries.py` — `@hf_retry` decorator with tenacity (5 attempts, exponential backoff 2 s → 60 s). Route 1 also auto-falls back from Llama-70B to Qwen-72B.

---

## Adding New Tools

1. Add the JSON schema → `app/tools/schemas.py`
2. Write the async function → `app/tools/operations.py`
3. Register the mapping → `app/tools/registry.py`

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HUGGINGFACE_TOKEN` | — | HF API token (**required**) |
| `MAIN_CHAT_MODEL` | `meta-llama/Llama-3.3-70B-Instruct` | Route 1 primary |
| `VOICE_STREAM_MODEL` | `meta-llama/Llama-3.1-8B-Instruct` | Route 2 streaming |
| `FALLBACK_CHAT_MODEL` | `Qwen/Qwen2.5-72B-Instruct` | Fallback when primary is down |
| `TTS_VOICE` | `af_heart` | Route 4/5 Kokoro voice preset |
| `TTS_LANG_CODE` | `a` | Kokoro language code (a = American English) |
| `STT_MODEL` | `openai/whisper-large-v3-turbo` | Route 5 speech-to-text model |
| `MAX_TOOL_ITERATIONS` | `3` | Max tool loop iterations |
| `MAX_CHAT_TOKENS` | `1024` | Max output tokens (chat) |
| `MAX_VOICE_TOKENS` | `250` | Max output tokens (voice) |
| `MAX_CONTEXT_TOKENS` | `8192` | HF context window budget |
