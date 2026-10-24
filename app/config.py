import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "Bengaluru Local Delivery Route Planner"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # MySQL Configuration (Default connection or environment overrides)
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DB: str = os.getenv("MYSQL_DB", "bengaluru_routing")

    # Override with full DATABASE_URL if provided
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Traffic Delays CSV Path
    TRAFFIC_CSV_PATH: Path = BASE_DIR / "data" / "traffic_delays.csv"

    # Static and maps directory
    STATIC_DIR: Path = BASE_DIR / "static"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
