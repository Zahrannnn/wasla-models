# ✅ Distribution Checklist for Teams

Use this checklist to ensure your team has everything needed to deploy the Wasla AI Agent.

## 📋 Pre-Deployment Checklist

### Prerequisites
- [ ] Docker installed (version 20.10+)
  - Download from https://www.docker.com/products/docker-desktop
  - Verify: `docker --version`
- [ ] Docker Compose installed (version 2.0+)
  - Usually included with Docker Desktop
  - Verify: `docker compose version` or `docker-compose --version`
- [ ] LLM API Key obtained
  - Option A: OpenRouter (Free) - https://openrouter.ai/settings/keys
  - Option B: HuggingFace - https://hf.co/settings/tokens

### Files Received
- [ ] Dockerfile
- [ ] docker-compose.yml
- [ ] requirements.txt
- [ ] app/ directory with all Python code
- [ ] .env.example
- [ ] DOCKER_SETUP.md (comprehensive guide)
- [ ] QUICKSTART.md (5-minute guide)
- [ ] Makefile (Linux/Mac) or validate-setup.bat (Windows)

### Configuration
- [ ] Copied `.env.example` to `.env`
- [ ] Set `LLM_API_KEY` in `.env`
- [ ] Reviewed other environment variables in `.env`
- [ ] Adjusted ports if needed (default: 8000)

## 🚀 Deployment Steps

### Quick Start (5 minutes)
1. [ ] Run validation script:
   - Windows: `validate-setup.bat`
   - Linux/Mac: `bash validate-setup.sh`
2. [ ] Start services: `docker-compose up -d`
3. [ ] Verify health: `curl http://localhost:8000/health`
4. [ ] Access API docs: http://localhost:8000/docs

### Full Deployment
1. [ ] Read DOCKER_SETUP.md completely
2. [ ] Configure all required environment variables
3. [ ] Review security considerations
4. [ ] Test all API endpoints
5. [ ] Set up monitoring and logging

## 🔍 Post-Deployment Verification

### Health Checks
- [ ] API responds at http://localhost:8000/health
- [ ] API documentation accessible at http://localhost:8000/docs
- [ ] Main chat endpoint works (Route 1)
- [ ] Voice streaming works (Route 2)
- [ ] TTS endpoint works (Route 4)

### Log Checks
- [ ] No error messages in logs: `docker-compose logs`
- [ ] LLM API calls successful
- [ ] Health checks passing

## 🛠️ Common Tasks

After deployment, you should know how to:

- [ ] View logs: `docker-compose logs -f`
- [ ] Restart services: `docker-compose restart`
- [ ] Stop services: `docker-compose down`
- [ ] Check status: `docker-compose ps`
- [ ] Access shell: `docker-compose exec wasla-ai-agent bash`
- [ ] Use Make commands (Linux/Mac): `make help`

## 🔐 Security Review (For Production)

Before going to production:

- [ ] Changed default CORS origins in `app/main.py`
- [ ] Using secrets management (not `.env` file)
- [ ] Enabled HTTPS via reverse proxy
- [ ] Network isolation configured
- [ ] Rate limiting properly configured
- [ ] Monitoring and alerting set up
- [ ] Backup strategy in place

## 📚 Documentation

Team members should review:

- [ ] QUICKSTART.md - Quick start guide
- [ ] DOCKER_SETUP.md - Full deployment guide
- [ ] DOCKER_PACKAGE_README.md - Package overview
- [ ] README.md - Complete API documentation
- [ ] validate-setup.bat/sh - Environment validation

## 🆘 Support Contacts

If issues arise:

1. Check DOCKER_SETUP.md Troubleshooting section
2. Review logs: `docker-compose logs -f`
3. Check health: `curl http://localhost:8000/health`
4. Contact: [Your support contact/email]

## 📝 Notes

```
Add any team-specific notes here:

- API Key: ___________________________
- Custom Configuration: _______________
- Deployment Date: ____________________
- Team Contact: _______________________
```

---

**Need help?** See DOCKER_SETUP.md or contact the Wasla AI team.
