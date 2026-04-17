# InsureCo Claims Voice Agent

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-async-green?logo=fastapi)
![VAPI](https://img.shields.io/badge/Voice-VAPI-purple)
![LLM](https://img.shields.io/badge/LLM-GPT--4o-orange?logo=openai)
![Tests](https://img.shields.io/badge/tests-48%20passing-brightgreen)
![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)

A production-ready **Voice AI agent** that handles inbound insurance claim support calls end-to-end — authentication, claim status retrieval, FAQ handling, escalation logic, and post-call summary logging.

Built with **VAPI + FastAPI + Google Sheets + GPT-4o**, with a full async backend, retry logic, Pydantic validation, and 48 unit tests.

---

## Demo

| Path | Description |
|---|---|
| 🟢 Happy path | Caller authenticates → claim status retrieved → FAQ answered → interaction logged |
| 🔴 Error path | Number not found → fallback verification → human callback offered → logged as Unknown |

> **Watch the recordings:** [🟢 Happy path](https://share.vidyard.com/watch/NAVCQ5iQ6pvK1EohXBXtCa) · [🔴 Error path](https://share.vidyard.com/watch/pwQChg5XaAjpWMgJt2WFzc)
>
> Demo scripts: [happy_path_demo.md](demo/happy_path_demo.md) · [error_path_demo.md](demo/error_path_demo.md)

---

## Architecture

```
Caller
  ↕ (WebRTC / phone)
VAPI  ──  Deepgram STT → GPT-4o (live) → ElevenLabs TTS
  ↕ (webhooks)
FastAPI Backend                          Google Sheets
  ├── POST /webhook/vapi  ──────────────→  customers (lookup)
  │     ├── tool-calls                  └─ interactions (write)
  │     │     ├── lookup_caller
  │     │     └── schedule_callback
  │     └── end-of-call-report
  │           └── GPT-4o-mini (async summary + sentiment)
  ├── GET  /health
  └── GET  /demo  (web call UI)
```

**Why this stack:**
- **VAPI** — handles STT/TTS/turn-taking/barge-in, vendor-neutral (swap Deepgram/ElevenLabs via config), webhook-based so business logic stays in my backend
- **FastAPI** — async-first for I/O-bound webhook handlers, Pydantic validation at the boundary, free OpenAPI docs
- **GPT-4o live + GPT-4o-mini post-call** — multi-LLM pattern: right model for each task, ~30x cost difference
- **Google Sheets** — exposes every real integration concern (OAuth2 service account, retries, idempotency) behind a `CRMAdapter` protocol; swappable for Salesforce/Zendesk with one config change

---

## Quick Start

```bash
git clone https://github.com/varadnair30/insureco-claims-voice-agent.git
cd insureco-claims-voice-agent
cp .env.example .env        # Fill in your API keys
docker-compose up           # Starts on http://localhost:8000
```

Swagger UI available at `http://localhost:8000/docs`

---

## Configuration

### 1. Google Sheets

Create a spreadsheet with two sheets:

**`customers`**
| phone_number | first_name | last_name | claim_status |
|---|---|---|---|
| +15551234567 | Sarah | Johnson | pending |
| +15559876543 | Michael | Chen | approved |

**`interactions`**
| timestamp | caller_name | summary | sentiment | call_id |

Share the sheet with your service account `client_email`.

### 2. VAPI Setup

```bash
python setup_vapi.py \
  --vapi-key YOUR_VAPI_KEY \
  --server-url https://your-ngrok-url.ngrok-free.dev
```

This registers the assistant and tool definitions automatically.

### 3. Environment Variables

```bash
VAPI_API_KEY=vapi_xxxx
OPENAI_API_KEY=sk-xxxx
GOOGLE_CREDENTIALS_JSON='{"type":"service_account",...}'  # full JSON, single line
SPREADSHEET_ID=1abc...xyz
PORT=8000
LOG_LEVEL=INFO
```

### 4. Local Development (expose via ngrok)

```bash
# Terminal 1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2
ngrok http 8000
```

---

## Project Structure

```
insureco-claims-voice-agent/
├── app/
│   ├── main.py           # FastAPI app + route definitions
│   ├── config.py         # Pydantic Settings
│   ├── models.py         # Request/response models
│   ├── sheets.py         # Google Sheets CRMAdapter
│   ├── vapi_client.py    # VAPI webhook dispatcher
│   └── summarizer.py     # GPT-4o-mini post-call summarizer
├── prompts/
│   └── system_prompt.txt # Agent persona + constraints
├── tests/                # 48 pytest unit tests
├── docs/
│   ├── technical_writeup.md
│   └── architecture_diagram.png
├── demo/
│   ├── web_call.html         # Browser-based demo UI
│   ├── happy_path_demo.md
│   └── error_path_demo.md
├── docker-compose.yml
├── Dockerfile
└── setup_vapi.py         # One-command VAPI assistant setup
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/demo` | Web call UI |
| `POST` | `/webhook/vapi` | VAPI webhook handler |

---

## Engineering Decisions

| Decision | Choice | Reasoning |
|---|---|---|
| Voice orchestration | VAPI | Vendor-neutral STT/TTS, native function calling, webhook extension |
| Backend | FastAPI | Async I/O, Pydantic boundary validation, auto OpenAPI docs |
| Live LLM | GPT-4o | Low TTFT, strong tool-calling |
| Summary LLM | GPT-4o-mini | Async, no latency budget, 1/30th cost |
| CRM | Google Sheets | Real OAuth2 + retry patterns, swappable via CRMAdapter protocol |
| Retries | tenacity | Exponential backoff (1s→2s→4s), deterministic vs transient error routing |

Full write-up: [docs/technical_writeup.md](docs/technical_writeup.md)

---

## Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

48 tests covering webhook routing, summarizer edge cases, Sheets integration, and error handling. All external dependencies mocked — runs offline without consuming API quota.

---

## What I'd Add Next

- **HMAC webhook signature verification** — deferred for demo (ngrok tunnel, unshared URL); day-one for production
- **Redis cache** for repeat callers within 1 hour
- **Telephony** — SIP trunking via Twilio or Amazon Connect for real PSTN calls
- **Eval framework** — Braintrust or custom pytest suite replaying recorded transcripts against prompt changes
- **CRM swap** — `SalesforceAdapter` implementing the same `CRMAdapter` protocol

---

## Tech Stack

`Python 3.10` · `FastAPI` · `VAPI` · `GPT-4o` · `GPT-4o-mini` · `Deepgram` · `ElevenLabs` · `Google Sheets API` · `Pydantic` · `tenacity` · `structlog` · `pytest` · `Docker` · `ngrok`
