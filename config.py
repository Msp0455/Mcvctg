import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =========================================
# SIMPLE CONFIGURATION (NO ENUM ERRORS)
# =========================================

@dataclass
class TelegramConfig:
    api_id: int = int(os.getenv("API_ID", 0))
    api_hash: str = os.getenv("API_HASH", "")
    bot_token: str = os.getenv("BOT_TOKEN", "")
    string_session: str = os.getenv("STRING_SESSION", "")
    workers: int = int(os.getenv("WORKERS", 10))

@dataclass
class APIConfig:
    youtube_api_key: str = os.getenv("YOUTUBE_API_KEY", "")
    spotify_client_id: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    spotify_client_secret: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    genius_access_token: str = os.getenv("GENIUS_ACCESS_TOKEN", "")
    lastfm_api_key: str = os.getenv("LASTFM_API_KEY", "")
    lastfm_api_secret: str = os.getenv("LASTFM_API_SECRET", "")

@dataclass
class DatabaseConfig:
    mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")

@dataclass
class AudioConfig:
    quality: str = os.getenv("AUDIO_QUALITY", "192k")  # 64k, 128k, 192k, 320k
    format: str = os.getenv("AUDIO_FORMAT", "mp3")
    bitrate: str = os.getenv("AUDIO_BITRATE", "192k")
    sample_rate: int = int(os.getenv("AUDIO_SAMPLE_RATE", 44100))
    max_file_size: int = int(os.getenv("MAX_FILE_SIZE", 52428800))  # 50MB

@dataclass
class BotConfig:
    name: str = os.getenv("BOT_NAME", "🎵 Music Bot")
    username: str = os.getenv("BOT_USERNAME", "")
    admin_ids: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])
    log_channel: int = int(os.getenv("LOG_CHANNEL", 0))
    support_chat: str = os.getenv("SUPPORT_CHAT", "")

@dataclass
class ServerConfig:
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", 8080))
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    environment: str = os.getenv("ENVIRONMENT", "production")

class Config:
    """Main configuration class"""
    
    def __init__(self):
        self.telegram = TelegramConfig()
        self.api = APIConfig()
        self.database = DatabaseConfig()
        self.audio = AudioConfig()
        self.bot = BotConfig()
        self.server = ServerConfig()
        
        # Create directories
        self.BASE_DIR = Path(__file__).parent
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.CACHE_DIR = self.BASE_DIR / "cache"
        self.DOWNLOADS_DIR = self.BASE_DIR / "downloads"
        self.ASSETS_DIR = self.BASE_DIR / "assets"
        
        # Create directories if they don't exist
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.DOWNLOADS_DIR.mkdir(exist_ok=True)
        self.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    
    @property
    def enable_voice_chat(self) -> bool:
        return bool(self.telegram.string_session)
    
    @property
    def enable_spotify(self) -> bool:
        return bool(self.api.spotify_client_id and self.api.spotify_client_secret)
    
    @property
    def enable_genius(self) -> bool:
        return bool(self.api.genius_access_token)
    
    @property
    def enable_lastfm(self) -> bool:
        return bool(self.api.lastfm_api_key and self.api.lastfm_api_secret)
    
    @property
    def enable_youtube_api(self) -> bool:
        return bool(self.api.youtube_api_key)
    
    @property
    def is_production(self) -> bool:
        return self.server.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.server.environment == "development"

# Create global config instance
config = Config()
