import json
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # VAPI
    vapi_api_key: str = Field(..., description="VAPI API key")
    vapi_phone_number_id: str = Field("", description="VAPI phone number ID")
    vapi_webhook_secret: str = Field("", description="VAPI webhook secret for verification")

    # OpenAI
    openai_api_key: str = Field(..., description="OpenAI API key")

    # Google Sheets
    google_credentials_json: str = Field(..., description="Google service account JSON credentials")
    spreadsheet_id: str = Field(..., description="Google Sheets spreadsheet ID")

    # Server
    port: int = Field(8000, description="Server port")
    log_level: str = Field("INFO", description="Logging level")

    @property
    def google_credentials(self) -> dict:
        return json.loads(self.google_credentials_json)

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
