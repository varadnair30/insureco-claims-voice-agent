# InsureCo Claims Voice Agent — CLAUDE.md

## Project overview

Production-grade voice AI agent for inbound insurance claims support.
Stack: VAPI (voice) + FastAPI (backend) + GPT-4o (LLM) + Google Sheets (data).

Key flows:
- Caller authentication via `lookup_caller` tool → Google Sheets customers tab
- Claim status retrieval after successful auth
- FAQ answers from system prompt knowledge base
- Escalation: agent offers human callback verbally; no `schedule_callback` tool exists in production — logging is handled via the `end-of-call-report` webhook, not a mid-call tool call
- Post-call: VAPI fires `end-of-call-report` → GPT-4o-mini summarizes transcript → `log_interaction` writes to interactions tab

Entry points:
- `app/main.py` — FastAPI app, route definitions
- `app/vapi_client.py` — webhook dispatcher (tool-calls + end-of-call-report)
- `app/sheets.py` — Google Sheets read/write with tenacity retry
- `app/summarizer.py` — GPT-4o-mini post-call analysis
- `prompts/system_prompt.txt` — live system prompt loaded by setup_vapi.py
- `setup_vapi.py` — creates VAPI assistant; contains the two production tool schemas (lookup_caller, log_interaction) inline as dicts

Test suite: `tests/test_agent.py` — 48 unit tests, all external deps mocked, run with `pytest -m "not eval"`.

---

## Eval suite (evals/)

This repo contains an LLM-simulated-caller evaluation suite for regression-testing the
voice agent's prompt + tool behavior in CI. Text-mode only: we do NOT place real Vapi
calls in tests. Instead, `evals/agent_adapter.py` re-creates the agent loop locally —
same system prompt (prompts/system_prompt.txt), same tool definitions, same backend
handlers — with Google Sheets mocked via fixture data.

### Critical boundary rule (extraction-readiness)
- `evals/engine/` is a self-contained mini-library: simulator, judge, metrics,
  transcript, runner, report. It must NEVER import from `app/` or reference anything
  InsureCo-specific. It only consumes: a Scenario object, and an agent callable with
  the signature `async respond(history: list[Turn]) -> AgentReply`.
- `evals/agent_adapter.py` is the ONLY file that knows about InsureCo. It bridges the
  repo's prompt/tools/handlers into that callable.
- If a change requires engine/ to know something about InsureCo, the answer is to pass
  it through the Scenario or the adapter — never to import app code into engine/.

### Conventions
- Same standards as the rest of the repo: Pydantic v2, async, tenacity retries,
  structlog, full type hints, pytest with everything mocked except the eval LLM calls.
- Eval runs that hit real LLM APIs are marked `@pytest.mark.eval` and excluded from
  the default unit-test run. CI runs them in a separate job.
- Judges return structured JSON validated by Pydantic — never free text.

---

## Known issues / tech debt

- `setup_vapi.py` still contains the string `"Observe Claims Support Line"` in
  `provision_phone_number()` — rename to `"InsureCo Claims Support Line"`.
- `tests/test_agent.py` line 317: `HealthResponse.service` hardcoded as
  `"observe-claims-agent"` — update if the service name changes.
- Tool schemas for `lookup_caller` and `log_interaction` are inline dicts in
  `setup_vapi.py`. Before building the eval adapter, extract them to a shared module
  (e.g., `app/tool_schemas.py`) so adapter and production both read from one source.
