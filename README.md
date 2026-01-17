# Dilcore AI Core

A FastAPI-based AI Agent API with RFC 7807 Problem Details error handling.

## Features

- **RFC 7807 Problem Details**: Standardized error responses following [RFC 7807](https://tools.ietf.org/html/rfc7807)
- **Comprehensive Error Handling**: Custom exception classes for different error scenarios
- **Type-Safe**: Built with Pydantic models for request/response validation
- **Well-Tested**: Comprehensive test suite with pytest
- **Modern Python**: Built with Python 3.11+ and FastAPI

## Problem Details Error Handling

This API implements RFC 7807 Problem Details for HTTP APIs, providing a standardized way to communicate errors to clients. All error responses follow this format:

```json
{
  "type": "https://api.dilcore.ai/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed. Please check the errors field for details.",
  "instance": "/api/v1/generate",
  "errors": {
    "prompt": ["Field required"]
  }
}
```

### Error Response Fields

- **type**: A URI reference identifying the problem type
- **title**: A short, human-readable summary of the problem
- **status**: The HTTP status code
- **detail**: A human-readable explanation specific to this occurrence
- **instance**: A URI reference identifying the specific occurrence of the problem
- **errors**: (Optional) Additional details about the error, such as validation errors

### Supported Error Types

| Error Type | Status Code | Description |
|------------|-------------|-------------|
| `validation-error` | 422 | Request validation failed |
| `template-generation` | 500 | Template generation failed |
| `llm-api` | 502 | LLM API call failed |
| `parsing` | 500 | Failed to parse LLM response |
| `internal-server-error` | 500 | Unexpected server error |
| `not-found` | 404 | Resource not found |
| `bad-request` | 400 | Invalid request |
| `service-unavailable` | 503 | Service temporarily unavailable |

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/aytymchuk/Dilcore-AI-Core.git
cd Dilcore-AI-Core
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the API

Start the development server:

```bash
uvicorn ai_agent.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

Once the server is running, you can access:

- **Interactive API docs (Swagger UI)**: http://localhost:8000/docs
- **Alternative API docs (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI schema**: http://localhost:8000/openapi.json

## API Endpoints

### Health Check

```bash
GET /api/v1/health
```

Returns the health status of the API.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### Generate Template

```bash
POST /api/v1/generate
```

Generate a template from a prompt.

**Request Body:**
```json
{
  "prompt": "Create a user registration form",
  "options": {}
}
```

**Success Response (200):**
```json
{
  "template": "Generated template for: Create a user registration form",
  "metadata": {
    "prompt_length": 32,
    "template_length": 55,
    "model": "example-model",
    "timestamp": "2026-01-17T00:00:00Z"
  }
}
```

**Error Response (422):**
```json
{
  "type": "https://api.dilcore.ai/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Request validation failed. Please check the errors field for details.",
  "instance": "/api/v1/generate",
  "errors": {
    "prompt": ["String should have at least 1 character"]
  }
}
```

### Test Error Responses

```bash
GET /api/v1/error/{error_type}
```

Trigger different error types for testing. Available error types:
- `validation` - Validation error (422)
- `llm` - LLM API error (502)
- `parsing` - Parsing error (500)
- `template` - Template generation error (500)
- `http` - HTTP error (404)
- `unhandled` - Unhandled exception (500)

## Running Tests

Run the test suite:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=ai_agent --cov-report=html
```

View coverage report:

```bash
open htmlcov/index.html  # On macOS
# or
xdg-open htmlcov/index.html  # On Linux
# or
start htmlcov/index.html  # On Windows
```

## Project Structure

```
Dilcore-AI-Core/
├── src/
│   └── ai_agent/
│       ├── __init__.py
│       ├── main.py                 # FastAPI application
│       ├── exceptions.py           # Custom exception classes
│       ├── api/
│       │   ├── __init__.py
│       │   ├── routes.py           # API endpoints
│       │   └── exception_handlers.py  # Exception handlers
│       └── schemas/
│           ├── __init__.py
│           └── problem_details.py  # Problem Details schema
├── tests/
│   ├── __init__.py
│   └── test_problem_details.py     # Tests for error handling
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Project configuration
└── README.md                       # This file
```

## Implementation Details

### Custom Exceptions

All custom exceptions inherit from `AIAgentException`:

```python
from ai_agent.exceptions import ValidationError, TemplateGenerationError

# Raise a validation error
raise ValidationError(
    message="Invalid prompt content",
    errors={"prompt": ["Prompt cannot be empty"]}
)

# Raise a template generation error
raise TemplateGenerationError(
    message="Failed to generate template",
    errors={"reason": "invalid_format"}
)
```

### Exception Handlers

Exception handlers are registered in `main.py` and automatically convert exceptions to Problem Details responses:

```python
app.add_exception_handler(AIAgentException, ai_agent_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
```

### Response Headers

All error responses include the correct `Content-Type` header:

```
Content-Type: application/problem+json
```

## Development

### Code Quality

This project uses:
- **ruff**: Fast Python linter and formatter
- **mypy**: Static type checker
- **pytest**: Testing framework

Run code quality checks:

```bash
# Linting
ruff check src tests

# Type checking
mypy src

# Formatting
ruff format src tests
```

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
