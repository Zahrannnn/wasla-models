# Wasla AI Agent - Docker Deployment Guide

This guide explains how to deploy the Wasla AI Agent backend using Docker for easy distribution to other teams.

## 📋 Prerequisites

Before deploying, ensure you have:

- **Docker** (version 20.10 or later) installed
- **Docker Compose** (version 2.0 or later) installed
- **LLM API Key** from one of:
  - [OpenRouter](https://openrouter.ai) - Free tier available, no credit card needed
  - [HuggingFace](https://hf.co/settings/tokens) - Free tier available

## 🚀 Quick Start

### 1. Get the Application Code

Clone the repository or extract the provided archive:

```bash
cd wasla-models
```

### 2. Configure Environment Variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and set your LLM API key:

```env
# Option A - OpenRouter (Recommended - Free tier)
LLM_API_KEY=sk-or-v1-your-api-key-here
LLM_BASE_URL=https://openrouter.ai/api/v1

# Option B - HuggingFace
# LLM_API_KEY=hf-your-api-key-here
# LLM_BASE_URL=https://router.huggingface.co/v1
```

### 3. Start the Application

Use Docker Compose to start all services:

```bash
docker-compose up -d
```

This will:
- Build the application container
- Start Redis for rate limiting
- Start the Wasla AI Agent backend
- Expose the API on port 8000

### 4. Verify Deployment

Check if the service is running:

```bash
# Check containers
docker-compose ps

# Check health
curl http://localhost:8000/health
```

### 5. Access API Documentation

Open your browser and navigate to:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🛠️ Configuration Options

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | Your LLM provider API key | `sk-or-v1-xxxx` |
| `LLM_BASE_URL` | LLM provider endpoint | `https://openrouter.ai/api/v1` |

### Optional Variables

#### Model Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `MAIN_CHAT_MODEL` | `qwen/qwen3-14b:free` | Primary chat model (Route 1) |
| `VOICE_STREAM_MODEL` | `qwen/qwen3-8b:free` | Voice streaming model (Route 2) |
| `FALLBACK_CHAT_MODEL` | `qwen/qwen3-8b:free` | Fallback model when primary fails |

#### Agent Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_TOOL_ITERATIONS` | `3` | Maximum tool calling iterations |
| `MAX_CHAT_TOKENS` | `1024` | Max output tokens for chat |
| `MAX_VOICE_TOKENS` | `250` | Max output tokens for voice |
| `MAX_CONTEXT_TOKENS` | `8192` | Context window budget |

#### API Endpoints

| Variable | Default | Description |
|----------|---------|-------------|
| `CRM_API_BASE_URL` | `http://waslacrm.runasp.net/api/customer-portal` | Customer portal API |
| `COMPANY_API_BASE_URL` | `http://waslacrm.runasp.net/api` | Company portal API |
| `CRM_API_TIMEOUT_SECONDS` | `10` | API request timeout |
| `COMPANY_API_TIMEOUT_SECONDS` | `10` | API request timeout |

#### Rate Limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection string |
| `RATE_LIMIT_REQUESTS` | `30` | Requests per time window |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Time window in seconds |

#### Voice Features

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_VOICE` | `af_heart` | Kokoro TTS voice preset |
| `TTS_LANG_CODE` | `a` | TTS language code |
| `STT_MODEL` | `openai/whisper-large-v3-turbo` | Speech-to-text model |

## 📡 API Endpoints

### Route 1: Main Chat (Agentic Tool Calling)

```http
POST /api/chat/{company_id}
Content-Type: application/json

{
  "prompt": "Show me the top 5 customers",
  "conversation_history": []
}
```

### Route 2: Voice Streaming (SSE)

```http
POST /api/chat/{company_id}/stream
Content-Type: application/json

{
  "prompt": "What are today's sales?",
  "conversation_history": []
}
```

Response: Server-Sent Events (text/event-stream)

### Route 4: Text-to-Speech (One-shot)

```http
POST /api/voice/tts
Content-Type: application/json

{
  "text": "Hello, welcome to Wasla."
}
```

Response: Audio WAV binary

### Route 5: Voice Conversation (WebSocket)

```javascript
const ws = new WebSocket("ws://localhost:8000/api/voice/conversation/{company_id}");

// Send audio
ws.send(JSON.stringify({
  "type": "audio",
  "data": "<base64-encoded-audio>"
}));

// Or send text directly
ws.send(JSON.stringify({
  "type": "text",
  "data": "Hello"
}));
```

### Health Check

```http
GET /health
```

Returns service status and configured models.

## 🔧 Common Operations

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f wasla-ai-agent
docker-compose logs -f redis
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart wasla-ai-agent
```

### Stop Services

```bash
docker-compose down
```

### Update the Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up -d --build
```

### Access Container Shell

```bash
docker-compose exec wasla-ai-agent bash
```

## 🐛 Troubleshooting

### Issue: Container won't start

**Solution:** Check if port 8000 is already in use:

```bash
# Windows
netstat -ano | findstr :8000

# Linux/Mac
lsof -i :8000
```

Change the port in `docker-compose.yml`:

```yaml
ports:
  - "8001:8000"  # Use different host port
```

### Issue: LLM API errors (HTTP 429)

**Solution**: This is a rate limit from the free tier. The app automatically retries with exponential backoff. To reduce frequency:
- Increase `RATE_LIMIT_WINDOW_SECONDS`
- Decrease `RATE_LIMIT_REQUESTS`

### Issue: Redis connection timeout

**Solution**: The app degrades gracefully without Redis. Check if Redis is running:

```bash
docker-compose ps redis
```

### Issue: TTS not working

**Solution**: Ensure the container has access to audio libraries. The Dockerfile includes `libsndfile1`. Rebuild if needed:

```bash
docker-compose build --no-cache wasla-ai-agent
docker-compose up -d
```

### Issue: High memory usage

**Solution**: Switch to smaller models in `.env`:

```env
MAIN_CHAT_MODEL=qwen/qwen3-8b:free
VOICE_STREAM_MODEL=qwen/qwen3-8b:free
```

## 🔐 Security Considerations

### For Production Deployment

1. **Restrict CORS origins** in `app/main.py:121`:

```python
allow_origins=["https://yourdomain.com"]
```

2. **Use secrets management** instead of `.env` file:
   - Docker Secrets
   - Kubernetes Secrets
   - Environment variable injection

3. **Enable HTTPS**:
   - Use a reverse proxy (nginx, Traefik)
   - Or use cloud provider load balancers

4. **Network isolation**:
   - Don't expose Redis port (6379) externally
   - Keep services in private networks

5. **Rate limiting**:
   - Keep Redis enabled
   - Adjust limits based on expected traffic

## 📦 Distribution to Other Teams

### Option 1: Git Repository

1. Push the code to a shared repository
2. Teams clone: `git clone <repository-url>`
3. Follow the Quick Start guide

### Option 2: Docker Image Registry

Build and push the image:

```bash
# Tag the image
docker tag wasla-models-wasla-ai-agent your-registry/wasla-ai-agent:latest

# Push to registry
docker push your-registry/wasla-ai-agent:latest
```

Teams can then use:

```yaml
# In their docker-compose.yml
services:
  wasla-ai-agent:
    image: your-registry/wasla-ai-agent:latest
    # ... rest of configuration
```

### Option 3: Pre-built Archive

Create a distributable package:

```bash
# Create archive (excluding .git, venv, etc.)
tar -czf wasla-ai-agent.tar.gz \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  .

# Teams extract and deploy
tar -xzf wasla-ai-agent.tar.gz
cd wasla-models
docker-compose up -d
```

## 📚 Additional Resources

- **Main README**: See `README.md` for detailed API documentation
- **HuggingFace Models**: https://huggingface.co/models
- **OpenRouter Models**: https://openrouter.ai/models
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Docker Compose**: https://docs.docker.com/compose

## 💡 Tips

1. **Monitor Resource Usage**: Use `docker stats` to monitor CPU and memory
2. **Health Checks**: The container includes built-in health checks
3. **Log Rotation**: Configure Docker log driver to prevent disk full issues
4. **Backup Redis**: Use `docker exec wasla-redis redis-cli SAVE` to persist data

## 🆘 Support

For issues or questions:
1. Check this guide's Troubleshooting section
2. Review logs: `docker-compose logs -f`
3. Check health endpoint: `curl http://localhost:8000/health`
4. Contact the Wasla AI team
