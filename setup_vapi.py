"""Setup script to create the VAPI voice agent programmatically.

Usage:
    python setup_vapi.py --vapi-key YOUR_VAPI_API_KEY --server-url YOUR_BACKEND_URL

This script will:
1. Create a VAPI assistant with the system prompt
2. Configure Deepgram STT + ElevenLabs TTS
3. Define tool calls (lookup_caller, log_interaction)
4. Set webhook URL for end-of-call reports
5. Print the assistant ID for testing
"""

import argparse
import json
import httpx

VAPI_BASE_URL = "https://api.vapi.ai"


def read_system_prompt() -> str:
    """Read the system prompt from file."""
    with open("prompts/system_prompt.txt", "r") as f:
        return f.read()


def create_assistant(vapi_key: str, server_url: str) -> dict:
    """Create the VAPI assistant with full configuration."""

    system_prompt = read_system_prompt()
    webhook_url = f"{server_url}/webhook/vapi"

    assistant_config = {
        "name": "Observe Insurance Claims Assistant",
        "model": {
            "provider": "openai",
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                }
            ],
            "temperature": 0.7,
            "maxTokens": 500,
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "lookup_caller",
                        "description": "Look up a customer by their phone number to verify their identity and retrieve their claim status. Use this whenever the caller provides their phone number.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "phone_number": {
                                    "type": "string",
                                    "description": "The caller's phone number, in any format they provide it"
                                }
                            },
                            "required": ["phone_number"]
                        }
                    },
                    "server": {
                        "url": webhook_url
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "log_interaction",
                        "description": "Log the call interaction record after the conversation ends. Call this when the caller is about to hang up or says goodbye.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "caller_name": {
                                    "type": "string",
                                    "description": "The authenticated caller's full name, or 'Unknown' if not authenticated"
                                },
                                "summary": {
                                    "type": "string",
                                    "description": "A 2-3 sentence summary of what was discussed during the call"
                                },
                                "sentiment": {
                                    "type": "string",
                                    "enum": ["positive", "neutral", "negative"],
                                    "description": "The overall sentiment of the caller during the conversation"
                                },
                                "call_id": {
                                    "type": "string",
                                    "description": "The unique call identifier"
                                }
                            },
                            "required": ["caller_name", "summary", "sentiment", "call_id"]
                        }
                    },
                    "server": {
                        "url": webhook_url
                    }
                }
            ]
        },
        "voice": {
            "provider": "11labs",
            "voiceId": "21m00Tcm4TlvDq8ikWAM",
            "stability": 0.6,
            "similarityBoost": 0.75,
        },
        "transcriber": {
            "provider": "deepgram",
            "model": "nova-2",
            "language": "en-US",
            "smartFormat": True,
        },
        "firstMessage": "Hi, thank you for calling Observe Insurance Claims Support. My name is Alex, and I'm here to help you today. To get started, could you please share the phone number associated with your account?",
        "serverUrl": webhook_url,
        "endCallMessage": "Thank you for calling Observe Insurance. Have a wonderful day!",
        "silenceTimeoutSeconds": 30,
        "maxDurationSeconds": 600,
        "endCallPhrases": ["goodbye", "bye", "that's all", "thank you bye"],
        "backgroundSound": "office",
        "hipaaEnabled": False,
        "clientMessages": [
            "transcript",
            "hang",
            "function-call",
            "speech-update",
            "status-update",
            "transfer-update",
        ],
        "serverMessages": [
            "end-of-call-report",
            "status-update",
            "hang",
            "tool-calls",
        ],
    }

    headers = {
        "Authorization": f"Bearer {vapi_key}",
        "Content-Type": "application/json",
    }

    print("Creating VAPI assistant...")
    print(f"Webhook URL: {webhook_url}")

    response = httpx.post(
        f"{VAPI_BASE_URL}/assistant",
        headers=headers,
        json=assistant_config,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        print(f"\nERROR: {response.status_code}")
        print(response.text)
        return {}

    assistant = response.json()
    assistant_id = assistant.get("id", "unknown")

    print("\n" + "=" * 60)
    print("VAPI ASSISTANT CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nAssistant ID:   {assistant_id}")
    print(f"Assistant Name: {assistant.get('name')}")
    print(f"Model:          {assistant.get('model', {}).get('model')}")
    print(f"Voice:          {assistant.get('voice', {}).get('voiceId')}")
    print(f"Transcriber:    {assistant.get('transcriber', {}).get('model')}")
    print(f"Server URL:     {webhook_url}")

    print(f"\n>> Test via VAPI Web Call:")
    print(f"   Go to https://vapi.ai/dashboard → Assistants → {assistant.get('name')} → Test")

    print(f"\n>> To provision a phone number, run:")
    print(f"   python setup_vapi.py --vapi-key YOUR_KEY --server-url {server_url} --provision-number")

    return assistant


def provision_phone_number(vapi_key: str, assistant_id: str) -> dict:
    """Provision a VAPI phone number and attach it to the assistant."""

    headers = {
        "Authorization": f"Bearer {vapi_key}",
        "Content-Type": "application/json",
    }

    phone_config = {
        "provider": "vapi",
        "assistantId": assistant_id,
        "name": "Observe Claims Support Line",
    }

    print("\nProvisioning phone number...")

    response = httpx.post(
        f"{VAPI_BASE_URL}/phone-number",
        headers=headers,
        json=phone_config,
        timeout=30,
    )

    if response.status_code not in (200, 201):
        print(f"ERROR provisioning number: {response.status_code}")
        print(response.text)
        return {}

    phone = response.json()
    phone_number = phone.get("number", "unknown")
    phone_id = phone.get("id", "unknown")

    print(f"\nPhone Number: {phone_number}")
    print(f"Phone ID:     {phone_id}")
    print(f"\n>> Add to your .env file:")
    print(f"   VAPI_PHONE_NUMBER_ID={phone_id}")
    print(f"\n>> Callers can now dial: {phone_number}")

    return phone


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up VAPI assistant for Observe Claims Agent")
    parser.add_argument("--vapi-key", required=True, help="VAPI API key")
    parser.add_argument("--server-url", required=True, help="Backend server URL (e.g., https://abc123.ngrok.io)")
    parser.add_argument("--provision-number", action="store_true", help="Also provision a phone number")
    args = parser.parse_args()

    assistant = create_assistant(args.vapi_key, args.server_url)

    if args.provision_number and assistant:
        provision_phone_number(args.vapi_key, assistant["id"])
