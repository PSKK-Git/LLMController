from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://llm:llm@localhost:5432/llmcontroller"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""  # set to an OpenAI-compatible proxy/gateway base URL
    admin_token: str = "dev-admin-token-change-me"


settings = Settings()
