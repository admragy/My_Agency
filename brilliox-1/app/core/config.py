"""Centralized Configuration Settings"""
import os
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Settings:
    # App
    APP_NAME: str = "Hunter Pro CRM"
    APP_VERSION: str = "3.0.0"
    VERSION: str = "3.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Directories
    UPLOAD_DIR: str = "uploads"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    
    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    SUPABASE_URL: Optional[str] = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: Optional[str] = os.getenv("SUPABASE_KEY")
    
    # AI APIs
    OPENAI_API_KEY: Optional[str] = os.getenv("AI_INTEGRATIONS_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL: str = os.getenv("AI_INTEGRATIONS_OPENAI_BASE_URL") or "https://api.openai.com/v1"
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY")
    
    # Cache
    CACHE_TTL: int = 3600
    
    # Search
    SERPER_API_KEY: Optional[str] = None
    
    # Payment
    PAYMOB_API_KEY: Optional[str] = os.getenv("PAYMOB_API_KEY")
    PAYMOB_INTEGRATION_ID: Optional[str] = os.getenv("PAYMOB_INTEGRATION_ID")
    PAYMOB_IFRAME_ID: Optional[str] = os.getenv("PAYMOB_IFRAME_ID")
    PAYMOB_HMAC_SECRET: Optional[str] = os.getenv("PAYMOB_HMAC_SECRET")
    
    # WhatsApp
    WHATSAPP_API_KEY: Optional[str] = os.getenv("WHATSAPP_API_KEY")
    WHATSAPP_PHONE_ID: Optional[str] = os.getenv("WHATSAPP_PHONE_ID")
    
    # Security
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "P@$$w0rd@1982")
    RATE_LIMIT_REQUESTS: int = 60
    RATE_LIMIT_WINDOW: int = 60
    BLOCK_DURATION: int = 300
    
    # Token Costs
    CHAT_COST: int = 2
    HUNT_COST: int = 20
    AD_COST: int = 15
    CAMPAIGN_COST: int = 50
    DEFAULT_BALANCE: int = 100
    
    # Language
    DEFAULT_LANGUAGE: str = "ar"
    SUPPORTED_LANGUAGES: List[str] = None
    
    def __post_init__(self):
        if self.SUPPORTED_LANGUAGES is None:
            self.SUPPORTED_LANGUAGES = ["ar", "en"]
        
        serper_keys = os.getenv("SERPER_KEYS", "")
        if serper_keys:
            self.SERPER_API_KEY = serper_keys.split(",")[0].strip()


settings = Settings()
