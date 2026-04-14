import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

# Find .env file - check parent directory (project root) first
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
if not os.path.exists(env_path):
    env_path = ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=env_path, extra='ignore')

    DATABASE_URL: str = "sqlite+aiosqlite:///./union_rights.db"
    SECRET_KEY: str = "your-secret-key-here"
    QWEN_API_KEY: str = ""
    UPLOAD_DIR: str = "/data/uploads"
    # OpenAI compatible API (DashScope)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    OPENAI_MODEL_NAME: str = "deepseek-v32"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()
