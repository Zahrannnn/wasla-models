# 📦 Docker Deployment Package - What's Included

This package contains everything needed to deploy the Wasla AI Agent backend using Docker.

## 📁 Files Created

| File | Purpose |
|------|---------|
| `Dockerfile` | Builds the application container |
| `docker-compose.yml` | Orchestrates app services |
| `.dockerignore` | Excludes unnecessary files from Docker image |
| `DOCKER_SETUP.md` | Comprehensive deployment guide |
| `QUICKSTART.md` | 5-minute quick start guide |
| `Makefile` | Convenient commands for common operations |
| `README.md` | Updated with Docker section |

## 🚀 Fastest Way to Start

1. **Get API Key**: https://openrouter.ai (free, no credit card needed)
2. **Configure**: Copy `.env.example` to `.env` and add your API key
3. **Run**: `docker-compose up -d`
4. **Access**: http://localhost:8000/docs

## 📖 Documentation

- **Quick Start**: `QUICKSTART.md` - Get running in 5 minutes
- **Full Guide**: `DOCKER_SETUP.md` - Detailed configuration, troubleshooting, and security
- **API Reference**: `README.md` - Complete API documentation
- **Make Commands**: `make help` - See all available commands

## 🛠️ Common Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Or use Make
make up      # Start
make logs    # View logs
make down    # Stop
make health  # Check health
make test    # Quick API test
make help    # Show all commands
```

## 📡 API Endpoints

Once running, the API is available at:

- **Documentation**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health
- **Main Chat**: POST /api/chat/{company_id}
- **Voice Stream**: POST /api/chat/{company_id}/stream
- **TTS**: POST /api/voice/tts
- **Voice WebSocket**: WS /api/voice/conversation/{company_id}

## 🔧 What's Included in the Docker Image

- Python 3.11 runtime
- All dependencies from `requirements.txt`
- Audio libraries for TTS (Kokoro-82M)
- FastAPI application code
- Health checks
- Non-root user for security

## 🌐 Services

The docker-compose.yml includes:

1. **wasla-ai-agent** - Main application (port 8000)

Features:
- Auto-restart on failure
- Health checks
- Isolated network

## 🔐 Security Notes

⚠️ **Important**: The `.env` file is NOT included in the Docker image (see `.dockerignore`).

Each deployment team MUST:
1. Create their own `.env` file from `.env.example`
2. Set their own API keys
3. Never commit `.env` to version control

## 📦 Distribution Options

### Option 1: Git Repository
```bash
git clone <repository-url>
cd wasla-models
docker-compose up -d
```

### Option 2: Docker Image Registry
```bash
docker pull your-registry/wasla-ai-agent:latest
# Use in docker-compose.yml with custom configuration
```

### Option 3: Archive
```bash
tar -xzf wasla-ai-agent.tar.gz
cd wasla-models
docker-compose up -d
```

## 🐛 Troubleshooting

**Port already in use?**
Change port in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Use different host port
```

**Memory issues?**
Use smaller models in `.env`:
```env
MAIN_CHAT_MODEL=qwen/qwen3-8b:free
```

**See full troubleshooting guide**: `DOCKER_SETUP.md` section "Troubleshooting"

## 📚 Additional Resources

- OpenRouter Free Models: https://openrouter.ai/models
- HuggingFace Models: https://huggingface.co/models
- Docker Compose Docs: https://docs.docker.com/compose
- FastAPI Docs: https://fastapi.tiangolo.com

## 💡 Tips for Teams

1. **Use Make Commands**: `make help` shows all available commands
2. **Monitor Resources**: `docker stats` to check CPU/memory usage
3. **Check Health**: `make health` or curl http://localhost:8000/health
4. **View Logs**: `make logs` for real-time monitoring
5. **Customize**: Edit `.env` for your specific needs

## 🆘 Need Help?

1. Check `DOCKER_SETUP.md` for detailed guides
2. Review logs: `docker-compose logs -f`
3. Check health: `curl http://localhost:8000/health`
4. Contact the Wasla AI team

---

**Ready to deploy? Start with [QUICKSTART.md](QUICKSTART.md)**
