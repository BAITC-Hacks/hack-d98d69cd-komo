from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'postgresql+asyncpg://career:career-local-only@localhost:5432/career_quest'
    redis_url: str = 'redis://localhost:6379/0'
    dataset_path: str = '../career_quest_dataset'
    app_origin: str = 'http://localhost:3000'
    openai_api_key: str = ''
    openai_key: str = ''
    openai_model: str = 'gpt-4.1-mini-2025-04-14'
    session_secret: str = ''
    employee_password: str = 'employee-demo-2026'
    hr_password: str = 'hr-demo-2026'
    employee_id: str = 'E0028'

    @property
    def api_key(self) -> str:
        return self.openai_api_key or self.openai_key


@lru_cache
def settings() -> Settings:
    return Settings()
