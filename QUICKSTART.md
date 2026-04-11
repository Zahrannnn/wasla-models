# 🚀 Quick Start Guide - Wasla AI Agent

Get the Wasla AI Agent up and running in 5 minutes using Docker.

## Step 1: Get Your API Key

Choose one option:

**Option A - OpenRouter (Recommended - Free)**
1. Go to https://openrouter.ai
2. Sign up (free, no credit card)
3. Get API key from https://openrouter.ai/settings/keys

**Option B - HuggingFace**
1. Go to https://hf.co/settings/tokens
2. Create a new token

## Step 2: Configure

Copy and edit the environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your API key:

```env
LLM_API_KEY=your-api-key-here
```

## Step 3: Start the App

```bash
docker-compose up -d
```

Wait a moment for the services to start.

## Step 4: Verify It's Working

Open these in your browser:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Done! 🎉

The API is now running on `http://localhost:8000`

### Quick Test

Try a chat request:

```bash
curl -X POST http://localhost:8000/api/chat/test-company \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!", "conversation_history": []}'
```

## Need Help?

See `DOCKER_SETUP.md` for detailed configuration and troubleshooting.
