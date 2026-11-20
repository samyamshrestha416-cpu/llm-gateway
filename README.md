# LLM Gateway

A small web API that sits between client apps and Google's Gemini API. Clients send a conversation to the gateway, and the gateway validates it, calls Gemini asynchronously, retries temporary failures, and returns a clean JSON response. Every request is logged as structured JSON with a request ID.

I built it to learn how an AI backend works: FastAPI, async code, validation, error handling, streaming, and logging. It is Project 2 of my series on building AI applications (the first was a [terminal chatbot](https://github.com/YOUR_USERNAME/llm-playground)).

## Features

- **Validated requests.** Pydantic checks every request: allowed roles, message length, number of messages, temperature range, and that the conversation ends with a user message. Bad requests are rejected before they reach Gemini.
- **Async Gemini calls.** The server uses `async` and `await`, so it can handle other requests while it waits for the model.
- **Retries with exponential backoff and jitter.** Only temporary failures are retried (rate limits, server errors, lost connection). Bad keys and bugs fail immediately.
- **Consistent JSON errors.** Every error has the same shape and the right status code (422, 429, 500, 502, 503).
- **Structured logs.** One JSON line per request, with a request ID, status, and duration. Model calls log the token counts and latency. Message text and API keys are never logged.
- **Request IDs.** Each response carries an `X-Request-ID` header, and error bodies include the same ID, so one request can be found in the logs.
- **Streaming (SSE).** `/chat/stream` sends the reply piece by piece as Server-Sent Events.

## Endpoints

| Method | Path | What it does |
| --- | --- | --- |
| GET | `/health` | Returns `{"status": "ok"}` |
| POST | `/chat` | Returns one complete reply with token counts and latency |
| POST | `/chat/stream` | Streams the reply as Server-Sent Events |
| GET | `/docs` | Interactive Swagger UI, built by FastAPI |

### Example: `POST /chat`

Request:

```json
{
  "messages": [
    {"role": "user", "text": "My name is Sita"},
    {"role": "assistant", "text": "Nice to meet you, Sita!"},
    {"role": "user", "text": "What is my name?"}
  ],
  "system": "You are a patient tutor.",
  "temperature": 0.7
}
```

Response:

```json
{
  "reply": "Your name is Sita.",
  "model": "gemini-3.5-flash-lite",
  "usage": {"input_tokens": 38, "output_tokens": 6, "total_tokens": 44},
  "latency_ms": 912
}
```

The server stores no conversation. The client sends the full history on each request.

### Request fields

| Field | Type | Rules |
| --- | --- | --- |
| `messages` | list | 1 to 50 items, and the last one must have the role `user` |
| `messages[].role` | text | `user` or `assistant` |
| `messages[].text` | text | 1 to 8000 characters |
| `system` | text, optional | up to 2000 characters |
| `temperature` | number, optional | 0 to 2, default 0.7 |

### Example: `POST /chat/stream`

The response is a stream of Server-Sent Events:

```
data: {"text": "An API is"}

data: {"text": " a way for programs to talk"}

event: usage
data: {"input_tokens": 12, "output_tokens": 30, "total_tokens": 42}

event: done
data: {}
```

If something fails after the stream has started, the status code is already sent, so the server sends an `event: error` instead.

## Error format

Every error returns the same shape:

```json
{
  "error": {
    "type": "validation_error",
    "message": "The request is not valid.",
    "request_id": "a1b2c3d4",
    "details": [{"field": "body.messages", "problem": "List should have at least 1 item"}]
  }
}
```

| Status | `type` | Meaning |
| --- | --- | --- |
| 422 | `validation_error` | The request is invalid. Fix it, do not retry the same one. |
| 429 | `provider_error` | The AI provider is rate limiting. Slow down. |
| 502 | `provider_error` | The AI provider returned an error. |
| 503 | `provider_unreachable` | Cannot reach the provider. Try again. |
| 500 | `internal_error` | A bug on the server side. |

## Setup

1. Install [uv](https://docs.astral.sh/uv/) and Python 3.12 or newer.
2. Clone the repo and install the libraries:
   ```bash
   git clone https://github.com/YOUR_USERNAME/llm-gateway.git
   cd llm-gateway
   uv sync
   ```
3. Get a free API key from [Google AI Studio](https://aistudio.google.com).
4. Create a `.env` file in the project folder:
   ```
   GEMINI_API_KEY=your_key_here
   ```
   Never commit this file. It is listed in `.gitignore`.

Optional settings in `.env`: `DEFAULT_MODEL` (default `gemini-3.5-flash-lite`) and `MAX_RETRIES` (default `4`).

## Run

From the project root:

```bash
uv run python -m uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000/docs` to try the endpoints.

## Test

With the server running, run the test script in a second terminal:

```bash
uv run python test_client.py
```

It checks:

- `/health` responds
- `/chat` returns a reply with token counts
- an invalid request returns a 422 with the standard error shape
- `/chat/stream` delivers pieces gradually, and prints the time to the first piece
- 5 simultaneous `/chat` requests finish in about the time of one, which shows the server is really async

Streaming is easiest to see with `curl.exe -N` on Windows (put the JSON body in `body.json`):

```bash
curl.exe -N -X POST http://127.0.0.1:8000/chat/stream -H "Content-Type: application/json" -d "@body.json"
```

## Project structure

```
llm-gateway/
  app/
    main.py           # routes, middleware, error handlers
    config.py         # settings loaded from .env
    schemas.py        # request and response models
    llm.py            # async Gemini calls and retries
    logging_setup.py  # JSON log formatter
  test_client.py      # test script
  .env.example
  README.md
```

## Log example

```json
{"time": "2026-11-18T18:49:25", "level": "INFO", "logger": "gateway", "message": "chat_completed", "request_id": "bf41891f", "model": "gemini-3.5-flash-lite", "input_tokens": 4, "output_tokens": 9, "latency_ms": 912}
{"time": "2026-11-18T18:49:25", "level": "INFO", "logger": "gateway", "message": "request", "request_id": "bf41891f", "method": "POST", "path": "/chat", "status": 200, "duration_ms": 914}
```

Both lines share one `request_id`, so everything about a request can be found by searching for it.

## What I learned

- **Async is about waiting.** Calling an LLM takes seconds, and `await` lets the server serve other users meanwhile. A blocking call like `time.sleep` inside `async def` freezes the whole server.
- **Validate at the door.** Describing the allowed shape with Pydantic rejects bad input with a clear error before any money is spent on the model.
- **Status codes tell the client what to do.** 4xx means the request needs fixing, 5xx means the server or the provider failed. I return a different code for each case, with one JSON shape.
- **Hide provider details.** The API uses neutral roles (`assistant`) and general error messages, so clients do not depend on Gemini and no internals leak.
- **Retry only what can recover.** Rate limits and outages are worth retrying with growing waits. Bad keys and bugs are not. A stream that has already started must not be retried.
- **Request IDs make logs useful.** One short ID connects the request log, the model call log, and the error shown to the client.
- **Small typos cause most errors.** Almost every bug I hit (`user_metadata`, `token_tokens`, a missing `request` parameter) was a name that did not match another name. Reading the last line of the error found each one quickly.

## Next

Project 3 adds signup and login with JWT, a Postgres database with SQLAlchemy and Alembic migrations, and saved conversations for each user, so the client no longer has to send the full history.
