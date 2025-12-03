import asyncio
import logging
import hashlib
import time
from typing import Dict, List, Optional, Any
import pylast
import aiohttp
from datetime import datetime

from config import config
from utils.logger import logger
from utils.exceptions import LastFMError

class LastFMService:
    """Last.fm integration for scrobbling and music data"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Initialize pylast network
        self.network = pylast.LastFMNetwork(
            api_key=api_key,
            api_secret=api_secret,
        )
        
        # User sessions cache
        self.user_sessions: Dict[str, pylast.SessionKeyGenerator] = {}
        
        # Cache setup
        self.track_cache = cachetools.TTLCache(maxsize=500, ttl=1800)
        self.artist_cache = cachetools.TTLCache(maxsize=200, ttl=3600)
        self.album_cache = cachetools.TTLCache(maxsize=200, ttl=3600)
        
        # HTTP session
        self.session = None
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_user_session(self, username: str, password: str = None) -> Optional[str]:
        """Get session key for user"""
        cache_key = f"session:{username}"
        
        if cache_key in self.user_sessions:
            return self.user_sessions[cache_key].session_key
        
        try:
            if password:
                # Generate session key with password
                password_hash = pylast.md5(password)
                session_key = await self._get_mobile_session(username, password_hash)
            else:
                # Try to get existing session
                session_key = await self._get_web_session(username)
            
            if session_key:
                # Create session generator
                sg = pylast.SessionKeyGenerator(self.network)
                sg.session_key = session_key
                self.user_sessions[cache_key] = sg
            
            return session_key
            
        except Exception as e:
            logger.error(f"Failed to get user session: {e}")
            return None
    
    async def scrobble(self, track_name: str, artist: str, album: str = None, 
                      duration: int = None, user_id: int = None
