import os
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    STAGING = "staging"

class AudioQuality(str, Enum):
    LOW = "64k"
    MEDIUM = "128k"
    HIGH = "192k"
    VERY_HIGH = "320k"

@dataclass
class TelegramConfig:
    api_id: int = field(default_factory=lambda: int(os.getenv("API_ID", 0)))
    api_hash: str = field(default_factory=lambda: os.getenv("API_HASH", ""))
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    string_session: str = field(default_factory=lambda: os.getenv("STRING_SESSION", ""))
    workers: int = field(default_factory=lambda: int(os.getenv("WORKERS", 10)))
    proxy: Optional[Dict] = field(default_factory=lambda: json.loads(os.getenv("PROXY", "{}")) if os.getenv("PROXY") else None)

@dataclass
class APIConfig:
    youtube_api_key: str = field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY", ""))
    spotify_client_id: str = field(default_factory=lambda: os.getenv("SPOTIFY_CLIENT_ID", ""))
    spotify_client_secret: str = field(default_factory=lambda: os.getenv("SPOTIFY_CLIENT_SECRET", ""))
    genius_access_token: str = field(default_factory=lambda: os.getenv("GENIUS_ACCESS_TOKEN", ""))
    lastfm_api_key: str = field(default_factory=lambda: os.getenv("LASTFM_API_KEY", ""))
    lastfm_api_secret: str = field(default_factory=lambda: os.getenv("LASTFM_API_SECRET", ""))
    deezer_app_id: str = field(default_factory=lambda: os.getenv("DEEZER_APP_ID", ""))
    deezer_app_secret: str = field(default_factory=lambda: os.getenv("DEEZER_APP_SECRET", ""))

@dataclass
class DatabaseConfig:
    mongodb_uri: str = field(default_factory=lambda: os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
    postgres_url: str = field(default_factory=lambda: os.getenv("POSTGRES_URL", ""))
    database_name: str = field(default_factory=lambda: os.getenv("DATABASE_NAME", "music_bot"))

@dataclass
class AudioConfig:
    quality: AudioQuality = field(default_factory=lambda: AudioQuality(os.getenv("AUDIO_QUALITY", "HIGH")))
    format: str = field(default_factory=lambda: os.getenv("AUDIO_FORMAT", "mp3"))
    bitrate: str = field(default_factory=lambda: os.getenv("AUDIO_BITRATE", "192k"))
    sample_rate: int = field(default_factory=lambda: int(os.getenv("AUDIO_SAMPLE_RATE", 44100)))
    max_file_size: int = field(default_factory=lambda: int(os.getenv("MAX_FILE_SIZE", 52428800)))  # 50MB
    buffer_size: int = field(default_factory=lambda: int(os.getenv("BUFFER_SIZE", 4096)))

@dataclass
class BotConfig:
    name: str = field(default_factory=lambda: os.getenv("BOT_NAME", "🎵 Music Pro"))
    username: str = field(default_factory=lambda: os.getenv("BOT_USERNAME", ""))
    admin_ids: List[int] = field(default_factory=lambda: [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x])
    log_channel: int = field(default_factory=lambda: int(os.getenv("LOG_CHANNEL", 0)))
    support_chat: str = field(default_factory=lambda: os.getenv("SUPPORT_CHAT", ""))
    max_playlist_size: int = field(default_factory=lambda: int(os.getenv("MAX_PLAYLIST_SIZE", 100)))
    rate_limit_per_user: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT", 30)))

@dataclass
class ServerConfig:
    environment: Environment = field(default_factory=lambda: Environment(os.getenv("ENVIRONMENT", "production")))
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", 8080)))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", "your-secret-key-here"))
    cors_origins: List[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(","))

@dataclass
class CacheConfig:
    ttl: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL", 300)))
    max_size: int = field(default_factory=lambda: int(os.getenv("CACHE_MAX_SIZE", 1000)))
    enabled: bool = field(default_factory=lambda: os.getenv("CACHE_ENABLED", "true").lower() == "true")

@dataclass
class MonitoringConfig:
    sentry_dsn: str = field(default_factory=lambda: os.getenv("SENTRY_DSN", ""))
    prometheus_enabled: bool = field(default_factory=lambda: os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true")
    health_check_interval: int = field(default_factory=lambda: int(os.getenv("HEALTH_CHECK_INTERVAL", 60)))

class Config:
    def __init__(self):
        self.telegram = TelegramConfig()
        self.api = APIConfig()
        self.database = DatabaseConfig()
        self.audio = AudioConfig()
        self.bot = BotConfig()
        self.server = ServerConfig()
        self.cache = CacheConfig()
        self.monitoring = MonitoringConfig()
        
        # Paths
        self.BASE_DIR = Path(__file__).parent
        self.LOGS_DIR = self.BASE_DIR / "logs"
        self.CACHE_DIR = self.BASE_DIR / "cache"
        self.DOWNLOADS_DIR = self.BASE_DIR / "downloads"
        self.ASSETS_DIR = self.BASE_DIR / "assets"
        
        # Create directories
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.DOWNLOADS_DIR.mkdir(exist_ok=True)
        self.ASSETS_DIR.mkdir(exist_ok=True)
    
    @property
    def is_production(self) -> bool:
        return self.server.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        return self.server.environment == Environment.DEVELOPMENT
    
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
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "telegram": self.telegram.__dict__,
            "api": {k: "***" if "secret" in k or "key" in k else v 
                   for k, v in self.api.__dict__.items()},
            "database": self.database.__dict__,
            "audio": self.audio.__dict__,
            "bot": self.bot.__dict__,
            "server": self.server.__dict__,
            "cache": self.cache.__dict__,
            "monitoring": self.monitoring.__dict__,
        }

config = Config()
