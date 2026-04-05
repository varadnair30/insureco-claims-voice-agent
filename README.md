# Observe Insurance Claims Voice Agent

A production-quality VoiceAI agent that handles inbound customer support calls for insurance claim status inquiries. Built with VAPI, FastAPI, and Google Sheets.

## Quick Start (3 commands)

```bash
cp .env.example .env        # Fill in your API keys (see Configuration below)
docker-compose build         # Build the container
docker-compose up            # Start the server at http://localhost:8000
```

The API docs are available at `http://localhost:8000/docs` (Swagger UI).

## What It Does

- **Greets callers** and authenticates them by phone number lookup
- **Retrieves claim status** (approved, pending, requires documentation) from Google Sheets
- **Answers FAQs** about office hours, mailing address, claims process
- **Escalates gracefully** when authentication fails or caller requests a human
- **Logs every interaction** (summary, sentiment, timestamp) to Google Sheets post-call

## Architecture

```
Caller ←→ VAPI (Deepgram STT → GPT-4o → ElevenLabs TTS)
                ↓ webhooks
          FastAPI Backend
           ├── /lookup-caller    → Google Sheets (customers)
           ├── /log-interaction  → Google Sheets (interactions)
           └── /webhook/vapi     → Routes tool calls + end-of-call events
                                    ↓
                              GPT-4o-mini (post-call summary + sentiment)
```

Full architecture diagram with Mermaid: [docs/architecture.md](docs/architecture.md)

## Configuration

### 1. Google Sheets Setup

1. Create a Google Cloud project and enable the **Google Sheets API**
2. Create a **Service Account** and download the JSON key
3. Create a Google Spreadsheet with two sheets:

**Sheet 1: `customers`** (columns in row 1):
| phone_number | first_name | last_name | claim_status |
|---|---|---|---|
| +15551234567 | Sarah | Johnson | pending |
| +15559876543 | Michael | Chen | approved |
| +15551112222 | Emily | Davis | requires_documentation |

**Sheet 2: `interactions`** (columns in row 1):
| timestamp | caller_name | summary | sentiment | call_id |

4. Share the spreadsheet with your service account email (found in the JSON key as `client_email`)

### 2. VAPI Setup

1. Sign up at [vapi.ai](https://vapi.ai)
2. Create a new assistant with the system prompt from [prompts/system_prompt.txt](prompts/system_prompt.txt)
3. Add two tool definitions to your VAPI assistant:

**Tool 1: lookup_caller**
```json
{
  "type": "function",
  "function": {
    "name": "lookup_caller",
    "description": "Look up a customer by their phone number to verify identity and retrieve claim status",
    "parameters": {
      "type": "object",
      "properties": {
        "phone_number": {
          "type": "string",
          "description": "The caller's phone number"
        }
      },
      "required": ["phone_number"]
    }
  },
  "server": {
    "url": "YOUR_BACKEND_URL/webhook/vapi"
  }
}
```

**Tool 2: log_interaction**
```json
{
  "type": "function",
  "function": {
    "name": "log_interaction",
    "description": "Log the call interaction after the call ends",
    "parameters": {
      "type": "object",
      "properties": {
        "caller_name": { "type": "string", "description": "Authenticated caller name or 'Unknown'" },
        "summary": { "type": "string", "description": "2-3 sentence summary of the call" },
        "sentiment": { "type": "string", "enum": ["positive", "neutral", "negative"] },
        "call_id": { "type": "string", "description": "The call ID" }
      },
      "required": ["caller_name", "summary", "sentiment", "call_id"]
    }
  },
  "server": {
    "url": "YOUR_BACKEND_URL/webhook/vapi"
  }
}
```

4. Set the webhook URL for end-of-call reports: `YOUR_BACKEND_URL/webhook/vapi`
5. (Optional) Provision a phone number in VAPI for live calling

### 3. Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
VAPI_API_KEY=vapi_xxxx                    # From VAPI dashboard
VAPI_PHONE_NUMBER_ID=                      # From VAPI phone number config
OPENAI_API_KEY=sk-xxxx                     # From OpenAI platform
GOOGLE_CREDENTIALS_JSON='{"type":...}'     # Entire service account JSON (single line)
SPREADSHEET_ID=1abc...xyz                  # From the Google Sheet URL
PORT=8000
LOG_LEVEL=INFO
```

**Tip:** For `GOOGLE_CREDENTIALS_JSON`, paste the entire JSON file content as a single line string.

### 4. Exposing Locally (for development)

VAPI needs a public URL to send webhooks. Use ngrok:

```bash
ngrok http 8000
```

Then update your VAPI tool server URLs with the ngrok URL.

## Running Without Docker

```bash
python -m venv venv
source venv/bin/activate          # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/lookup-caller` | Look up customer by phone number |
| `POST` | `/log-interaction` | Log a post-call interaction record |
| `POST` | `/webhook/vapi` | VAPI webhook handler (tool calls + events) |

## Project Structure

```
observe-claims-agent/
├── README.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py              # FastAPI app + route definitions
│   ├── config.py             # Pydantic Settings (env var management)
│   ├── models.py             # Request/response Pydantic models
│   ├── sheets.py             # Google Sheets client (lookup + logging)
│   ├── vapi_client.py        # VAPI webhook event dispatcher
│   └── summarizer.py         # GPT-4o-mini post-call summarizer
├── prompts/
│   └── system_prompt.txt     # VAPI agent system prompt
├── docs/
│   ├── architecture.md       # Mermaid architecture diagrams
│   └── technical_writeup.md  # Full technical write-up
└── demo/
    ├── happy_path_demo.md    # Happy path demo script
    └── error_path_demo.md    # Error/fallback demo script
```

## Demo Videos

- **Happy path:** Caller authenticates successfully, receives claim status, asks FAQ questions, call logged with positive sentiment
- **Error path:** Caller's number not found, alternative verification attempted, human callback offered, call logged with "Unknown" caller

See [demo/](demo/) for detailed scripts.

## Technical Documentation

- [Architecture Diagram](docs/architecture.md) — Mermaid diagrams of the full system
- [Technical Write-Up](docs/technical_writeup.md) — Architecture choices, debugging challenges, metrics framework
