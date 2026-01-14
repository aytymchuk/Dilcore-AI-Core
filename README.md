# AI Template Agent

A Python AI agent built with LangChain and OpenRouter that generates structured JSON templates via a WebAPI.

## Features

- 🤖 **AI-Powered Template Generation** - Uses LangChain with OpenRouter for structured JSON output
- 🚀 **FastAPI WebAPI** - Modern async API with automatic validation
- 📚 **Scalar Documentation** - Beautiful, interactive API docs at `/scalar`
- ⚙️ **Type-Safe Configuration** - Pydantic settings with `.env` file support

## Quick Start

### Prerequisites

- Python 3.12+
- OpenRouter API key ([get one here](https://openrouter.ai/keys))

### Installation

1. **Clone and navigate to the project**
   ```bash
   cd /path/to/AI\ POC
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENROUTER_API_KEY
   ```

5. **Run the server**
   ```bash
   uvicorn src.ai_agent.main:app --reload
   ```

6. **Open API docs**
   - Navigate to http://localhost:8000/scalar

## API Endpoints

### Metadata Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/metadata/generate` | Generate a template from a prompt (synchronous) |
| `POST` | `/api/v1/metadata/generate-stream` | Stream template generation with SSE (real-time) |
| `GET` | `/api/v1/health` | Health check |

### Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/scalar` | Interactive API documentation |
| `GET` | `/` | Root endpoint with docs link |

### Streaming Endpoint

The `/generate-stream` endpoint uses Server-Sent Events (SSE) for real-time generation:

```bash
curl -X POST http://localhost:8000/api/v1/metadata/generate-stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a user registration form"}' \
  --no-buffer
```

**Event Types:**
- `thinking` - Reasoning content (if model supports thinking mode)
- `content` - Generation content chunks
- `template` - Final structured template with explanation
- `error` - Error event
- `done` - Stream completed

## Project Structure

```
ai-poc/
├── src/ai_agent/
│   ├── main.py          # FastAPI application
│   ├── config/          # Settings and configuration
│   ├── api/             # API routes and dependencies
│   ├── agent/           # LangChain agent implementation
│   └── schemas/         # Pydantic models
└── tests/               # Test suite
```

## Configuration

All configuration is managed via environment variables (`.env` file):

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENROUTER__API_KEY` | Your OpenRouter API key | *required* |
| `OPENROUTER__BASE_URL` | OpenRouter API endpoint | `https://openrouter.ai/api/v1` |
| `OPENROUTER__MODEL` | Model to use | `openai/gpt-oss-20b:free` |
| `APP_DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

