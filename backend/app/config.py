from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout: float = 120.0
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()
