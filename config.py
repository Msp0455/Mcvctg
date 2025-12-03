import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

class Config:
    # === TELEGRAM CREDENTIALS ===
    API_ID: int = int(os.getenv("API_ID", 0))
    API_HASH: str = os.getenv("API_HASH", "")
    
    # Bot Token (BotFather)
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # String Session (User Account for VC)
    STRING_SESSION: str = os.getenv("STRING_SESSION", "")
    
    # === API KEYS ===
    # YouTube Data API v3
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    YOUTUBE_OAUTH_CLIENT_ID: str = os.getenv("YOUTUBE_OAUTH_CLIENT_ID", "")
    YOUTUBE_OAUTH_CLIENT_SECRET: str = os.getenv("YOUTUBE_OAUTH_CLIENT_SECRET", "")
    
    # Spotify
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    SPOTIFY_REDIRECT_URI: str = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
    
    # Genius Lyrics
    GENIUS_ACCESS_TOKEN: str = os.getenv("GENIUS_ACCESS_TOKEN", "")
    
    # Last.fm
    LASTFM_API_KEY: str = os.getenv("LASTFM_API_KEY", "")
    LASTFM_API_SECRET: str = os.getenv("LASTFM_API_SECRET", "")
    LASTFM_USERNAME: str = os.getenv("LASTFM_USERNAME", "")
    LASTFM_PASSWORD: str = os.getenv("LASTFM_PASSWORD", "")
    
    # === DATABASE ===
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # === BOT SETTINGS ===
    BOT_NAME: str = os.getenv("BOT_NAME", "🎵 Music Pro")
    BOT_USERNAME: str = os.getenv("BOT_USERNAME", "")
    ADMIN_IDS: list = list(map(int, os.getenv("ADMIN_IDS", "123456789").split()))
    LOG_CHANNEL: int = int(os.getenv("LOG_CHANNEL", 0))
    SUPPORT_CHAT: str = os.getenv("SUPPORT_CHAT", "https://t.me/music_support")
    
    # === PERFORMANCE ===
    MAX_DOWNLOAD_SIZE: int = int(os.getenv("MAX_DOWNLOAD_SIZE", 52428800))  # 50MB
    MAX_PLAYLIST_SIZE: int = int(os.getenv("MAX_PLAYLIST_SIZE", 50))
    WORKERS: int = int(os.getenv("WORKERS", 10))
    
    # === AUDIO SETTINGS ===
    AUDIO_BITRATE: str = os.getenv("AUDIO_BITRATE", "192k")
    AUDIO_FORMAT: str = os.getenv("AUDIO_FORMAT", "mp3")
    
    # === RENDER SPECIFIC ===
    RENDER: bool = os.getenv("RENDER", "false").lower() == "true"
    PORT: int = int(os.getenv("PORT", 8080))
    
    # === FEATURE TOGGLES ===
    @property
    def ENABLE_VOICE_CHAT(self) -> bool:
        return bool(self.STRING_SESSION)
    
    @property
    def ENABLE_SPOTIFY(self) -> bool:
        return bool(self.SPOTIFY_CLIENT_ID and self.SPOTIFY_CLIENT_SECRET)
    
    @property
    def ENABLE_GENIUS(self) -> bool:
        return bool(self.GENIUS_ACCESS_TOKEN)
    
    @property
    def ENABLE_LASTFM(self) -> bool:
        return bool(self.LASTFM_API_KEY and self.LASTFM_API_SECRET)
    
    @property
    def ENABLE_YOUTUBE_API(self) -> bool:
        return bool(self.YOUTUBE_API_KEY)

config = Config()
