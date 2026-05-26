from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openrouter_api_key: str | None = None
    openrouter_model: str = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    openrouter_max_tokens: int = 300
    database_url: str = "sqlite:///./expenses.db"
    openrouter_site_url: str | None = None
    openrouter_app_name: str = "expense-tracker"

    model_config = SettingsConfigDict(
        env_file=(".env", "app/.env"),
        env_file_encoding="utf-8",
    )


settings = Settings()
