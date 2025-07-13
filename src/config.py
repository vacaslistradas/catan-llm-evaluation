import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = Path(__file__).parent.parent
    
    # OpenRouter Configuration
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Application Configuration
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", 5000))
    APP_DEBUG = os.getenv("APP_DEBUG", "false").lower() == "true"
    
    # Database Configuration
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/catan_evaluation.db")
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = Path(os.getenv("LOG_FILE", f"{BASE_DIR}/logs/catan_evaluation.log"))
    LOG_FILE.parent.mkdir(exist_ok=True)
    
    # Game Configuration
    DEFAULT_NUM_GAMES = int(os.getenv("DEFAULT_NUM_GAMES", 10))
    MAX_TURNS_PER_GAME = int(os.getenv("MAX_TURNS_PER_GAME", 200))
    GAME_TIMEOUT_SECONDS = int(os.getenv("GAME_TIMEOUT_SECONDS", 300))
    
    # Model Configuration
    DEFAULT_MODELS = [
        "openai/gpt-3.5-turbo",
        "anthropic/claude-3-haiku",
        "meta-llama/llama-3.1-8b-instruct",
        "mistralai/mistral-7b-instruct"
    ]
    
    # Elo Configuration
    INITIAL_ELO = 1500
    ELO_K_FACTOR = 32
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.OPENROUTER_API_KEY:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        return True