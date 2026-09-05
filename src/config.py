import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Settings:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    API_KEY: str = os.getenv("API_KEY", "qwen3-direct-access")
    MODEL_ID: str = os.getenv("MODEL_ID", "stabilityai/sd-turbo")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "sd-turbo")
    DEFAULT_STEPS: int = int(os.getenv("DEFAULT_STEPS", "1"))
    DEFAULT_GUIDANCE_SCALE: float = float(os.getenv("DEFAULT_GUIDANCE_SCALE", "0.0"))
    DEFAULT_WIDTH: int = int(os.getenv("DEFAULT_WIDTH", "512"))
    DEFAULT_HEIGHT: int = int(os.getenv("DEFAULT_HEIGHT", "512"))
    MOCK_MODEL: bool = os.getenv("MOCK_MODEL", "false").lower() in ("true", "1", "yes")
    RESTART_INTERVAL_SECONDS: int = int(os.getenv("RESTART_INTERVAL_SECONDS", "18000"))

settings = Settings()
