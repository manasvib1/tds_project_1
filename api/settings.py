import os
from pydantic_settings import BaseSettings

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

class Settings(BaseSettings):
    EXPECTED_SECRET: str = "change-me"
    GITHUB_USERNAME: str = ""
    GITHUB_TOKEN: str = ""
    PREFERRED_DRIVER: str = "gh"
    DEFAULT_BRANCH: str = "main"
    PAGES_BUILD_PATH: str = "/"
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""

    class Config:
        env_file = ENV_PATH  # <- always read api/.env

settings = Settings()
