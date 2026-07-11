"""
Central configuration manager for Sentinel-Agent.
Loads environment variables safely for the entire application.
"""

import os
from dotenv import load_dotenv

# Load the .env file explicitly from the project root
# This ensures it works no matter where you run your scripts from
load_dotenv()

class Settings:
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-1.5-flash")
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    
    # Tool Routing URLs
    GITHUB_BASE_URL: str = os.getenv("GITHUB_BASE_URL", "https://api.github.com")
    DATADOG_BASE_URL: str = os.getenv("DATADOG_BASE_URL", "https://api.datadoghq.com")
    
    # Internal Limits
    MAX_RETRY_LOOPS: int = 3
    DEBUG_MODE: bool = True

# Instantiate a global settings object to be imported across the app
settings = Settings()

# Validate critical keys on startup
if not settings.OPENROUTER_API_KEY and settings.LLM_PROVIDER == "openrouter":
    print(" WARNING: OPENROUTER_API_KEY is missing from the .env file!")