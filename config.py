import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram (REQUIRED for Render)
    API_ID = int(os.getenv("API_ID", 0))
    API_HASH = os.getenv("API_HASH", "")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # YouTube API (You have it)
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
    
    # Spotify (You have it)
    SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    ENABLE_SPOTIFY = bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET)
    
    # Genius (You have it)
    GENIUS_ACCESS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN", "")
    ENABLE_GENIUS = bool(GENIUS_ACCESS_TOKEN)
    
    # Last.fm (You have it)
    LASTFM_API_KEY = os.getenv("LASTFM_API_KEY", "")
    LASTFM_API_SECRET = os.getenv("LASTFM_API_SECRET", "")
    ENABLE_LASTFM = bool(LASTFM_API_KEY)
    
    # MongoDB (Optional)
    MONGODB_URI = os.getenv("MONGODB_URI", "")
    
    # Bot Settings
    ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
    BOT_NAME = os.getenv("BOT_NAME", "🎵 Music Master Pro")
    SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "")
    
    # Render specific
    RENDER = bool(os.getenv("RENDER", False))
    PORT = int(os.getenv("PORT", 8080))
