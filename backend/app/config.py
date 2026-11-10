from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://jobs:jobs@localhost:5432/jobs"
    redis_url: str = "redis://localhost:6379/0"
    admin_api_key: str = "change-me"
    user_agent: str = "JobBoardIndexer/0.1"
    http_timeout_seconds: float = 30.0
    expire_after_missed_runs: int = 3
    default_schedule_minutes: int = 360
    cors_origins: str = "http://localhost:3000"


settings = Settings()
