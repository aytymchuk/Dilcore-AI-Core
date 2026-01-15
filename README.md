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
AI POC/
├── src/
│   └── ai_agent/
│       ├── __init__.py
│       ├── main.py              # 🚀 ENTRYPOINT - FastAPI application factory
│       ├── config/
│       │   ├── __init__.py
│       │   └── settings.py      # Pydantic settings with .env support
│       ├── api/
│       │   ├── __init__.py      # Router exports
│       │   ├── routes.py        # Sync generate endpoint + health
│       │   ├── streaming_routes.py  # SSE streaming endpoint
│       │   └── dependencies.py  # FastAPI dependency injection
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── core.py          # TemplateAgent (sync generation)
│       │   ├── streaming.py     # StreamingTemplateAgent (SSE)
│       │   └── prompts.py       # System/user prompt templates
│       └── schemas/
│           ├── __init__.py
│           ├── request.py       # API request models
│           ├── response.py      # Template response models
│           └── streaming.py     # SSE event models
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_agent.py            # Agent unit tests
│   ├── test_api.py              # API endpoint tests
│   ├── test_config.py           # Configuration tests
│   └── test_streaming.py        # Streaming tests
├── .env.example                 # Environment template
├── pyproject.toml               # Project dependencies
└── README.md
```

## Scripts & Commands

### Development Server

```bash
# Start with auto-reload
uvicorn src.ai_agent.main:app --reload

# Start on specific port
uvicorn src.ai_agent.main:app --reload --port 8080

# Start with debug logging
LOG_LEVEL=DEBUG uvicorn src.ai_agent.main:app --reload
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src/ai_agent

# Run specific test file
pytest tests/test_streaming.py -v
```

### API Testing

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Generate template (sync)
curl -X POST http://localhost:8000/api/v1/metadata/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a contact form"}'

# Generate template (streaming)
curl -X POST http://localhost:8000/api/v1/metadata/generate-stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a user registration form"}' \
  --no-buffer
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
