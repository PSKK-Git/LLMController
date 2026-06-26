from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://llm:llm@localhost:5432/llmcontroller"
    redis_url: str = "redis://localhost:6379/0"
    admin_token: str = "dev-admin-token-change-me"

    # Per-provider credentials + endpoints (each model family routes to its own).
    anthropic_api_key: str = ""

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    mistral_api_key: str = ""
    mistral_base_url: str = "https://api.mistral.ai/v1"

    proxy_api_key: str = ""
    proxy_base_url: str = ""


settings = Settings()
