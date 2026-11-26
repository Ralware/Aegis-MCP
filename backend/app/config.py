from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    google_oauth_redirect_uri: str = "http://localhost:8000/api/integrations/google/callback"
    google_oauth_scopes: str = "openid,email,profile,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.send,https://www.googleapis.com/auth/drive.readonly"
    token_encryption_key: str = ""
    session_secret: str = ""
    database_url: str
    app_env: str = "development"
    max_document_bytes: int = 10_485_760
    approval_ttl_minutes: int = 30
    live_test_enabled: bool = False
    live_test_recipient_allowlist: str = ""

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use PostgreSQL asyncpg")
        return value

    @property
    def scopes(self) -> list[str]: return [scope.strip() for scope in self.google_oauth_scopes.split(",") if scope.strip()]

@lru_cache
def settings() -> Settings: return Settings()
