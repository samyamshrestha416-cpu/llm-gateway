from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",extra = "ignore")

    gemini_api_key : str
    default_model : str = "gemini-3.5-flash-lite"
    max_retries : int = 4

settings = Settings()
# run to check :uv run python -c "from app.config import settings; print(settings.default_model)"