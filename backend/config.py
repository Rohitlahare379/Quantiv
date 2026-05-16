import os
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_DATABASE_URL = f"sqlite:///{BACKEND_DIR / 'quantive.db'}"

class Settings(BaseSettings):
    # API & Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "quantive-hackathon-2026-secret")
    
    # External Integrations
    SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
    GENERIC_WEBHOOK_URL: Optional[str] = os.getenv("GENERIC_WEBHOOK_URL")
    
    # Market Data
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")
    
    # Simulation Defaults
    DEFAULT_SYMBOL: str = "BTCUSDT"
    DEFAULT_TIMEFRAME: str = "1h"

settings = Settings()

def validate_environment():
    """
    Performs critical environment checks on startup.
    """
    issues = []
    if not settings.DATABASE_URL:
        issues.append("DATABASE_URL is missing.")
    
    # Optional warnings
    if not settings.SLACK_WEBHOOK_URL:
        print("[WARNING] SLACK_WEBHOOK_URL not set. Notifications will be disabled.")
        
    return issues
