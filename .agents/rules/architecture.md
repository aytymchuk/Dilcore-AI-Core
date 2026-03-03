---
trigger: always_on
glob:
description:
---

# Dilcore AI Core — Architecture Reference

## Project Overview

This project is an **AI Agent service** built with FastAPI and LangGraph, providing structured JSON template generation and persona-based intent resolution.

## Directory Structure

```
src/
├── main.py                          # FastAPI entry point
│
├── api/                             # HTTP layer — request/response
│   ├── schemas/                     # Pydantic I/O models
│   │   ├── request.py               # GenerateRequest
│   │   ├── response.py              # TemplateResponse, TemplateSection, TemplateField
│   │   ├── streaming.py             # StreamEvent, StreamEventType, StreamingTemplateResponse
│   │   ├── persona.py               # PersonaRequest, PersonaResponse, FormViewResolution
│   │   └── errors.py                # ProblemDetails (RFC 7807)
│   ├── controllers/                 # FastAPI routers
│   │   ├── blueprints.py            # /api/v1/blueprints — generate & stream
│   │   ├── health.py                # /api/v1/health
│   │   ├── persona.py               # /api/v1/persona — resolve, index-metadata, index-data
│   │   ├── streaming.py             # /api/v1/metadata — legacy SSE endpoint
│   │   └── dependencies.py          # FastAPI DI: Settings, BlueprintsService, PersonaGraph
│   └── middleware/
│       └── exception_handler.py     # Global RFC 7807 error handling
│
├── agents/                          # AI agent implementations
│   └── blueprints/                  # Blueprints agent (LangGraph)
│       ├── __init__.py
│       ├── state.py                 # BlueprintsState TypedDict
│       ├── prompts.py               # All system/generation prompts
│       ├── graph.py                 # BlueprintsGraph — StateGraph compilation & run
│       ├── nodes/
│       │   ├── retrieve.py          # Node: vector store lookup for related entities
│       │   └── generate.py          # Node: LLM call + parse TemplateResponse
│       ├── tools/
│       │   └── vector_search.py     # LangChain @tool wrapping FAISS search
│       └── sub_agents/
│           └── persona/             # Persona sub-agent (intent resolution)
│               ├── state.py → PersonaState (defined inline in graph.py)
│               ├── graph.py         # PersonaGraph — retrieve_metadata→retrieve_data→resolve_intent
│               ├── nodes/
│               │   └── resolve.py   # LLM-based intent → FormViewResolution
│               └── tools/           # (placeholder)
│
├── infrastructure/                  # External connectivity
│   ├── llm/
│   │   └── client.py               # create_llm(), create_embeddings() factories
│   ├── tracing/
│   │   └── __init__.py             # configure_tracing() — LangSmith / OTEL
│   ├── messaging/                   # Placeholder — RabbitMQ, Kafka, etc.
│   └── http/
│       └── __init__.py             # create_http_client() — httpx async client
│
├── application/                     # Domain logic & orchestration
│   ├── services/
│   │   └── blueprints_service.py   # BlueprintsService — mediates API ↔ LangGraph
│   └── domain/                     # Domain models (future)
│
├── shared/                          # Cross-cutting concerns
│   ├── config/
│   │   └── settings.py             # Settings (Pydantic BaseSettings), get_settings()
│   ├── exceptions/
│   │   └── base.py                 # AIAgentException hierarchy
│   └── utils/                       # Utility helpers
│
└── store/                           # Storage adapters
    ├── vector/
    │   └── faiss_store.py          # FaissVectorStore — load/save/search wrapper
    ├── cache/                       # Placeholder — Redis / in-memory
    └── mongo/                       # Placeholder — MongoDB
```

## Key Design Rules

1. **Layered imports**: Controllers → Services → Agents → Infrastructure/Store. Never import backwards.
2. **Shared is common**: `shared/` may be imported by ANY layer. It imports nothing from other layers.
3. **Store is infrastructure-adjacent**: `store/` uses infrastructure (embeddings) but no agent logic.
4. **Agents own business logic**: Agent nodes and graphs contain the LLM reasoning. Controllers are thin.
5. **Schemas live in `api/schemas/`**: All Pydantic I/O models for HTTP belong here — even if agents use them for parsing.
6. **LangGraph for agents**: All nontrivial agents must use LangGraph StateGraph. Single-shot agents may use plain async functions.

## Key Files

| File | Responsibility |
|---|---|
| `src/main.py` | FastAPI app creation, routers, lifespan |
| `src/agents/blueprints/graph.py` | Main LangGraph graph — retrieve → generate |
| `src/agents/blueprints/sub_agents/persona/graph.py` | Persona sub-agent graph |
| `src/application/services/blueprints_service.py` | Orchestration between API and agents |
| `src/shared/config/settings.py` | All environment-based configuration |
| `src/shared/exceptions/base.py` | `AIAgentException` hierarchy |
| `src/store/vector/faiss_store.py` | FAISS vector store adapter |
| `src/infrastructure/llm/client.py` | `create_llm()` / `create_embeddings()` |

## Dependencies

- **FastAPI** (HTTP framework)
- **LangGraph ≥ 0.2.0** (stateful agent graphs)
- **LangChain** (LLM abstractions, tools, parsers)
- **langchain-openai** (OpenAI / OpenRouter LLM)
- **langchain-community** (FAISS vector store)
- **faiss-cpu** (vector index)
- **pydantic-settings** (environment configuration)
- **sse-starlette** (Server-Sent Events)
- **scalar-fastapi** (API docs UI)
- **httpx** (async HTTP outbound)

## Environment Variables

| Variable | Description |
|---|---|
| `OPENROUTER__API_KEY` | OpenRouter / OpenAI API key (**required**) |
| `OPENROUTER__BASE_URL` | API base URL (default: `https://openrouter.ai/api/v1`) |
| `OPENROUTER__MODEL` | LLM model ID (default: `openai/gpt-oss-20b:free`) |
| `VECTOR_STORE__METADATA_INDEX_PATH` | Path to FAISS metadata index |
| `VECTOR_STORE__DATA_INDEX_PATH` | Path to FAISS data index |

## Development Commands

```bash
source .venv/bin/activate
poe serve          # run dev server (uvicorn src.main:app --reload)
poe test           # run pytest
poe lint           # run ruff check
poe typecheck      # run mypy
poe check          # lint + typecheck + test
```
