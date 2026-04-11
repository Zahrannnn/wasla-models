# Wasla AI Agent - Complete Docker Deployment Guide

This comprehensive guide covers everything you need to deploy and distribute the Wasla AI Agent backend using Docker.

## 📋 Table of Contents

1. [Quick Start](#quick-start) - Get running in 5 minutes
2. [Prerequisites](#prerequisites) - System requirements
3. [Configuration](#configuration) - Environment variables
4. [Deployment Options](#deployment-options) - Different ways to deploy
5. [API Endpoints](#api-endpoints) - Available endpoints
6. [Common Operations](#common-operations) - Daily tasks
7. [Troubleshooting](#troubleshooting) - Issue resolution
8. [Security](#security) - Production security
9. [Distribution](#distribution) - Sharing with other teams

---

## 🚀 Quick Start

Get the Wasla AI Agent up and running in 5 minutes.

### Step 1: Get Your API Key

Choose one option:

**Option A - OpenRouter (Recommended - Free)**
1. Go to https://openrouter.ai
2. Sign up (free, no credit card needed)
3. Get API key from https://openrouter.ai/settings/keys

**Option B - HuggingFace**
1. Go to https://hf.co/settings/tokens
2. Create a new token

### Step 2: Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```env
# Option A - OpenRouter (Recommended)
LLM_API_KEY=sk-or-v1-your-api-key-here
LLM_BASE_URL=https://openrouter.ai/api/v1

# Option B - HuggingFace
# LLM_API_KEY=hf-your-api-key-here
# LLM_BASE_URL=https://router.huggingface.co/v1
```

### Step 3: Start the Application

```bash
docker-compose up -d
```

This will:
- Build the application container
- Start the Wasla AI Agent backend
- Expose the API on port 8000

### Step 4: Verify Deployment

```bash
# Check containers
docker-compose ps

# Check health
curl http://localhost:8000/health

# Or use Make
make health
```

### Step 5: Access API Documentation

Open your browser:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Quick Test

```bash
curl -X POST http://localhost:8000/api/chat/test-company \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!", "conversation_history": []}'
```

**Done! 🎉 The API is now running on http://localhost:8000**

---

## 📦 Prerequisites

Before deploying, ensure you have:

### System Requirements

- **Docker** (version 20.10 or later)
  - Download: https://www.docker.com/products/docker-desktop
  - Verify: `docker --version`

- **Docker Compose** (version 2.0 or later)
  - Usually included with Docker Desktop
  - Verify: `docker compose version` or `docker-compose --version`

### API Keys

- **LLM API Key** from one of:
  - [OpenRouter](https://openrouter.ai) - Free tier available, no credit card needed
  - [HuggingFace](https://hf.co/settings/tokens) - Free tier available

### Validate Your Setup

Run the validation script to check your environment:

**Windows:**
```bash
validate-setup.bat
```

**Linux/Mac:**
```bash
bash validate-setup.sh
```

---

## ⚙️ Configuration

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

**Free Models on OpenRouter:**
- `qwen/qwen3-14b:free` - 14B parameters, good for general chat
- `qwen/qwen3-8b:free` - 8B parameters, faster for streaming
- `google/gemma-7b-it:free` - 7B parameters, good performance
- `meta-llama/llama-3-8b-instruct:free` - 8B parameters, popular

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

#### Voice Features

| Variable | Default | Description |
|----------|---------|-------------|
| `TTS_VOICE` | `af_heart` | Kokoro TTS voice preset |
| `TTS_LANG_CODE` | `a` | TTS language code (a = American) |
| `STT_MODEL` | `openai/whisper-large-v3-turbo` | Speech-to-text model |

**Available TTS Voices:**
- `af_heart` - American female, emotional
- `af_bella` - American female, calm
- `af_nicole` - American female, professional
- `af_sarah` - American female, neutral
- `am_michael` - American male, neutral

---

## 📡 API Endpoints

### Route 1: Main Chat (Agentic Tool Calling)

**Endpoint**: `POST /api/chat/{company_id}`

**Purpose**: Main chat endpoint with 3-iteration agentic tool-calling loop

**Request**:
```http
POST /api/chat/test-company
Content-Type: application/json

{
  "prompt": "Show me the top 5 customers",
  "conversation_history": []
}
```

**Response**:
```json
{
  "response": "Here are your top 5 customers...",
  "tool_calls_made": 1,
  "model_used": "meta-llama/Llama-3.3-70B-Instruct"
}
```

### Route 2: Voice Streaming (SSE)

**Endpoint**: `POST /api/chat/{company_id}/stream`

**Purpose**: Low-latency token streaming for voice applications

**Request**:
```http
POST /api/chat/test-company/stream
Content-Type: application/json

{
  "prompt": "What are today's sales?",
  "conversation_history": []
}
```

**Response**: Server-Sent Events (text/event-stream)
```
data: Today's
data:  sales
data:  look
data:  great!
data: [DONE]
```

### Route 4: Text-to-Speech (One-shot)

**Endpoint**: `POST /api/voice/tts`

**Purpose**: Convert text to speech using Kokoro-82M (local model)

**Request**:
```http
POST /api/voice/tts
Content-Type: application/json

{
  "text": "Hello, welcome to Wasla."
}
```

**Response**: Audio WAV binary

### Route 5: Voice Conversation (WebSocket)

**Endpoint**: `WS /api/voice/conversation/{company_id}`

**Purpose**: Full-duplex voice conversation (Whisper STT → LLM streaming → Kokoro TTS)

**JavaScript Example**:
```javascript
const ws = new WebSocket("ws://localhost:8000/api/voice/conversation/test-company");

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

// Or send text directly
ws.send(JSON.stringify({
  "type": "text",
  "data": "Hello from the browser"
}));
```

**Client → Server Messages**:
```jsonc
// Send recorded audio (base64-encoded WAV/WebM/MP3)
{ "type": "audio", "data": "<base64 audio bytes>" }

// Or send text directly (skip STT)
{ "type": "text", "data": "typed user message" }

// End the conversation
{ "type": "end" }
```

**Server → Client Messages**:
```jsonc
{ "type": "transcript", "data": "what the user said" }   // STT result
{ "type": "llm_token",  "data": "Hello"  }               // streamed LLM token
{ "type": "audio",      "data": "<base64 PCM16 chunk>" } // TTS audio chunk (24kHz mono)
{ "type": "done" }                                        // turn complete
{ "type": "error",      "data": "error message" }        // error
```

### Health Check

**Endpoint**: `GET /health`

**Purpose**: Service health check and configuration status

**Response**:
```json
{
  "status": "ok",
  "main_model": "meta-llama/Llama-3.3-70B-Instruct",
  "fallback_model": "Qwen/Qwen2.5-72B-Instruct",
  "voice_model": "meta-llama/Llama-3.1-8B-Instruct",
  "tts_voice": "af_heart",
  "stt_model": "openai/whisper-large-v3-turbo",
  "max_context_tokens": 8192
}
```

### Root Endpoint

**Endpoint**: `GET /`

**Purpose**: Service information

**Response**:
```json
{
  "service": "Wasla AI Agent API",
  "docs": "/docs",
  "health": "/health"
}
```

---

## 🛠️ Common Operations

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f wasla-ai-agent

# Using Make
make logs        # All services
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart wasla-ai-agent

# Using Make
make restart
```

### Stop Services

```bash
docker-compose down

# Using Make
make down
```

### Check Status

```bash
# Show running containers
docker-compose ps

# Check health
curl http://localhost:8000/health

# Using Make
make ps
make health
```

### Update the Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up -d --build

# Using Make
make rebuild
```

### Access Container Shell

```bash
docker-compose exec wasla-ai-agent bash

# Using Make
make shell
```

### Makefile Commands

```bash
make help  # Show all available commands
```

Available commands:
- `make build` - Build Docker images
- `make up` - Start all services
- `make down` - Stop all services
- `make restart` - Restart all services
- `make logs` - View logs
- `make ps` - Show running containers
- `make health` - Check health status
- `make test` - Run quick API test
- `make clean` - Stop and remove everything
- `make rebuild` - Rebuild and restart
- `make shell` - Access application shell

---

## 🐛 Troubleshooting

### Issue: Container won't start

**Symptoms**: `docker-compose ps` shows Exit status

**Solution**: Check if port 8000 is already in use

**Windows**:
```bash
netstat -ano | findstr :8000
```

**Linux/Mac**:
```bash
lsof -i :8000
```

Change the port in `docker-compose.yml`:
```yaml
services:
  wasla-ai-agent:
    ports:
      - "8001:8000"  # Use different host port
```

### Issue: TTS not working

**Symptoms**: Text-to-speech returns errors

**Solution**: Ensure the container has access to audio libraries. The Dockerfile includes `libsndfile1`. Rebuild if needed:

```bash
docker-compose build --no-cache wasla-ai-agent
docker-compose up -d
```

### Issue: High memory usage

**Symptoms**: Container uses excessive RAM

**Solution**: Switch to smaller models in `.env`:

```env
MAIN_CHAT_MODEL=qwen/qwen3-8b:free
VOICE_STREAM_MODEL=qwen/qwen3-8b:free
FALLBACK_CHAT_MODEL=qwen/qwen3-8b:free
```

### Issue: Can't access API from other machines

**Symptoms**: API works on localhost but not from other computers

**Solution**: Check firewall settings and ensure Docker is binding to all interfaces:

```bash
# Test from other machine
curl http://your-server-ip:8000/health
```

If using firewall, open port 8000:

**Windows Firewall**:
```powershell
New-NetFirewallRule -DisplayName "Wasla AI Agent" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

**Linux (UFW)**:
```bash
sudo ufw allow 8000/tcp
```

### Issue: Health check failing

**Symptoms**: `/health` endpoint returns errors or 500

**Solution**: Check logs for specific errors:

```bash
docker-compose logs wasla-ai-agent
```

Common causes:
- Missing or invalid LLM_API_KEY
- Backend API unreachable
- Model not available

### Issue: Docker build fails

**Symptoms**: `docker-compose build` fails with errors

**Solution**:

1. Clear Docker cache:
```bash
docker-compose build --no-cache
```

2. Check Docker disk space:
```bash
docker system df
```

3. Clean up if needed:
```bash
docker system prune -a
```

### Issue: Slow response times

**Symptoms**: API takes long to respond

**Solutions**:

1. Use a faster model:
```env
MAIN_CHAT_MODEL=qwen/qwen3-8b:free
```
3. Check network latency to LLM provider
4. Monitor resource usage:
```bash
docker stats
```

---

## 🔐 Security

### For Production Deployment

#### 1. Restrict CORS Origins

Edit `app/main.py` line 121:

```python
# Before (insecure - allows all origins)
allow_origins=["*"]

# After (secure - specific domains only)
allow_origins=["https://yourdomain.com", "https://app.yourdomain.com"]
```

Rebuild after changes:
```bash
docker-compose up -d --build
```

#### 2. Use Secrets Management

**Never commit `.env` to version control**

Instead, use:

**Option A - Docker Secrets**:
```yaml
# docker-compose.yml
services:
  wasla-ai-agent:
    secrets:
      - llm_api_key
    environment:
      LLM_API_KEY_FILE: /run/secrets/llm_api_key

secrets:
  llm_api_key:
    file: ./secrets/llm_api_key.txt
```

**Option B - Kubernetes Secrets**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: wasla-secrets
type: Opaque
data:
  LLM_API_KEY: <base64-encoded-key>
```

**Option C - Environment Variable Injection**:
- Use your cloud provider's secret manager
- Inject secrets at container start time
- Never store in image or repository

#### 3. Enable HTTPS

**Option A - Nginx Reverse Proxy**:
```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Option B - Traefik**:
```yaml
# docker-compose.yml
services:
  wasla-ai-agent:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.wasla.rule=Host(`yourdomain.com`)"
      - "traefik.http.routers.wasla.tls=true"
```

**Option C - Cloud Load Balancer**:
- Use AWS ALB, GCP Load Balancer, etc.
- Configure SSL certificates
- Forward traffic to Docker container

#### 4. Network Isolation

```yaml
# docker-compose.yml
services:
  wasla-ai-agent:
    networks:
      - public    # Exposed only on port 8000

networks:
  public:
    driver: bridge
```

#### 6. Container Security

The Dockerfile already includes:
- Non-root user (`appuser`)
- Minimal base image (`python:3.11-slim`)
- Health checks

Additional recommendations:
- Scan images for vulnerabilities:
```bash
docker scan wasla-ai-agent
```
- Keep base images updated
- Use specific version tags (not `latest`)

#### 7. Logging and Monitoring

```yaml
# docker-compose.yml
services:
  wasla-ai-agent:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

Set up monitoring:
- Prometheus for metrics
- Grafana for dashboards
- ELK stack for log aggregation

---

## 📦 Distribution

### Option 1: Git Repository

Best for: Teams with Git access, frequent updates

**Steps**:

1. Push code to shared repository:
```bash
git add .
git commit -m "Add Docker deployment"
git push origin main
```

2. Teams clone and deploy:
```bash
git clone <repository-url>
cd wasla-models
cp .env.example .env
# Edit .env with their API key
docker-compose up -d
```

**Pros**:
- Easy updates with `git pull`
- Version control
- Team collaboration
- CI/CD integration

**Cons**:
- Requires Git access
- Repository size

### Option 2: Docker Image Registry

Best for: Production deployments, multiple environments

**Steps**:

1. Build and tag image:
```bash
docker build -t your-registry/wasla-ai-agent:latest .
```

2. Push to registry:
```bash
# Docker Hub
docker push your-registry/wasla-ai-agent:latest

# AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com
docker tag wasla-ai-agent:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/wasla-ai-agent:latest
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/wasla-ai-agent:latest

# Google GCR
gcloud auth configure-docker gcr.io
docker tag wasla-ai-agent:latest gcr.io/your-project/wasla-ai-agent:latest
docker push gcr.io/your-project/wasla-ai-agent:latest
```

3. Teams use custom docker-compose.yml:
```yaml
version: '3.8'
services:
  wasla-ai-agent:
    image: your-registry/wasla-ai-agent:latest
    environment:
      LLM_API_KEY: ${LLM_API_KEY}
      # ... other config
```

**Pros**:
- Faster deployment (no build step)
- Smaller distribution (just compose file)
- Versioned images
- Scalable

**Cons**:
- Registry access required
- Image size considerations

### Option 3: Pre-built Archive

Best for: One-time distribution, offline deployment

**Steps**:

1. Create archive:
```bash
tar -czf wasla-ai-agent.tar.gz \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.env' \
  --exclude='specs' \
  --exclude='test_output.wav' \
  Dockerfile \
  docker-compose.yml \
  requirements.txt \
  app/ \
  .env.example \
  *.md \
  Makefile \
  validate-setup.* \
  .dockerignore
```

2. Share archive (email, USB, file share, etc.)

3. Teams extract and deploy:
```bash
tar -xzf wasla-ai-agent.tar.gz
cd wasla-models
cp .env.example .env
# Edit .env
docker-compose up -d
```

**Pros**:
- Self-contained
- No external dependencies
- Works offline
- Easy to share

**Cons**:
- Larger file size
- Manual updates

### Option 4: Team Distribution Package

Create a comprehensive package for teams:

```bash
# Create distribution folder
mkdir -p dist/wasla-ai-agent

# Copy necessary files
cp Dockerfile dist/wasla-ai-agent/
cp docker-compose.yml dist/wasla-ai-agent/
cp requirements.txt dist/wasla-ai-agent/
cp -r app dist/wasla-ai-agent/
cp .env.example dist/wasla-ai-agent/
cp DOCKER_DEPLOYMENT_GUIDE.md dist/wasla-ai-agent/
cp DEPLOYMENT_CHECKLIST.md dist/wasla-ai-agent/
cp Makefile dist/wasla-ai-agent/  # Linux/Mac
cp validate-setup.bat dist/wasla-ai-agent/  # Windows

# Create archive
cd dist
tar -czf wasla-ai-agent-v2.0.0.tar.gz wasla-ai-agent/
zip -r wasla-ai-agent-v2.0.0.zip wasla-ai-agent/
```

Package includes:
- All deployment files
- Comprehensive guide (this document)
- Deployment checklist
- Validation scripts
- Make commands

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                       │
│                                                          │
│  ┌─────────────────┐                                    │
│  │  Client         │                                    │
│  │  (Browser/App)  │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
│           ▼                                             │
│  ┌─────────────────┐                                    │
│  │  Port 8000      │                                    │
│  └────────┬────────┘                                    │
└───────────┼────────────────────────────────────────────┘
            │
┌───────────┼────────────────────────────────────────────┐
            ▼
│  ┌─────────────────┐                                    │
│  │  wasla-ai-agent │                                    │
│  │                 │                                    │
│  │  - FastAPI      │                                    │
│  │  - Chat API     │                                    │
│  │  - Voice API    │                                    │
│  │  - TTS/STT      │                                    │
│  │                 │                                    │
│  └────────┬────────┘                                    │
│           │                                             │
└───────────┼────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────┐
│  External Services                                       │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ OpenRouter  │  │ HuggingFace  │  │ Backend API  │  │
│  │ / HF API    │  │ Inference    │  │ (CRM/Company) │  │
│  └─────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Container Details

**wasla-ai-agent Container**
- Base: `python:3.11-slim`
- Port: 8000 (HTTP)
- Dependencies: FastAPI, OpenAI, Kokoro, etc.
- Health check: `/health` endpoint every 30s
- Auto-restart: `unless-stopped`

---

## 💡 Tips and Best Practices

### Development

1. **Use hot reload** for development:
```yaml
# docker-compose.dev.yml
services:
  wasla-ai-agent:
    volumes:
      - ./app:/app/app  # Mount code directory
```

2. **Debug logs**:
```env
LOG_LEVEL=DEBUG
```

3. **Test locally first** before deploying to production

### Production

1. **Monitor resources**:
```bash
docker stats
```

2. **Set up alerts** for:
   - Container restarts
   - High CPU/memory usage
   - API error rates

3. **Regular backups**:
    - Configuration files
    - Environment variables (securely stored)

4. **Update regularly**:
    - Security patches
    - Model updates
    - Dependency updates

### Performance

1. **Use appropriate models**:
   - Faster models for voice/streaming
   - Larger models for complex reasoning

2. **Optimize requests**:
   - Batch requests when possible

3. **Scale horizontally**:
```bash
docker-compose up -d --scale wasla-ai-agent=3
```
Load balancer needed for scaling.

### Cost Optimization

1. **Use free tier models** when possible
2. **Implement caching** to reduce API calls
3. **Monitor usage** and adjust rate limits
4. **Batch requests** when possible

---

## 📚 Additional Resources

### Official Documentation
- **FastAPI**: https://fastapi.tiangolo.com
- **Docker**: https://docs.docker.com
- **Docker Compose**: https://docs.docker.com/compose
- **OpenRouter**: https://openrouter.ai/docs
- **HuggingFace**: https://huggingface.co/docs

### Models
- **OpenRouter Free Models**: https://openrouter.ai/models?order=popular&free=true
- **HuggingFace Models**: https://huggingface.co/models
- **Llama Models**: https://huggingface.co/meta-llama
- **Qwen Models**: https://huggingface.co/Qwen

### Tools
- **Docker Desktop**: https://www.docker.com/products/docker-desktop
- **Kokoro TTS**: https://github.com/hexgrad/Kokoro
- **Whisper STT**: https://github.com/openai/whisper

---

## 🆘 Support

### Getting Help

1. **Check this guide** - Most issues are covered in troubleshooting
2. **Review logs** - `docker-compose logs -f`
3. **Check health** - `curl http://localhost:8000/health`
4. **Search issues** - Check GitHub issues if available

### Common Issues Reference

| Issue | Solution |
|-------|----------|
| Port already in use | Change port in docker-compose.yml |
| API key errors | Verify LLM_API_KEY in .env |
| Slow responses | Use faster model or check network |
| Memory issues | Switch to smaller model |
| Can't access from other machines | Check firewall settings |

### Community

- **Documentation**: See README.md for API reference
- **Examples**: Check app/api/routes/ for endpoint implementations
- **Tools**: See app/tools/ for available tools

### Contact

For issues not covered here:
- Contact the Wasla AI team
- Create an issue in the repository
- Join community forums (if available)

---

## 📝 Changelog

### Version 2.0.0 (Current)
- Added Docker deployment
- Comprehensive documentation
- Validation scripts
- Make commands
- Security guidelines
- Distribution options

### Future Enhancements
- Kubernetes deployment guide
- CI/CD pipeline examples
- Monitoring dashboard setup
- Advanced scaling strategies

---

## ✅ Deployment Checklist

Before going to production, ensure:

- [ ] LLM API key configured and valid
- [ ] All environment variables set
- [ ] CORS origins restricted
- [ ] HTTPS enabled
- [ ] Health checks passing
- [ ] Logging and monitoring set up
- [ ] Security review completed
- [ ] Load testing performed
- [ ] Documentation updated for team
- [ ] Support contacts established

---

**Need to deploy quickly? Start with the [Quick Start](#quick-start) section above!**

**For detailed information, use the Table of Contents to navigate to specific topics.**

**Happy deploying! 🚀**
