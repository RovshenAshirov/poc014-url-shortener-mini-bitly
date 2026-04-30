from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    BASE_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
