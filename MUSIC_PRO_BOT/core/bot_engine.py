import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import aiohttp

from pyrogram import Client
from pyrogram.types import Message, User, Chat
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, AudioVideoPiped, StreamAudioEnded

from config import config
from core.voice_client import VoiceClient
from core.queue_manager import QueueManager
from core.cache_manager import CacheManager
from core.database import DatabaseManager
from services.youtube import YouTubeService
from services.spotify import SpotifyService
from services.genius import GeniusService
from services.lastfm import LastFMService
from utils.logger import logger
from utils.exceptions import BotError

@dataclass
class ChatContext:
    """Chat context for each group"""
    chat_id: int
    is_playing: bool = False
    is_paused: bool = False
    current_track: Optional[Dict] = None
    volume: int = 100
    repeat_mode: str = "off"  # off, one, all
    queue_position: int = 0
    last_activity: datetime = field(default_factory=datetime.now)

class MusicBotEngine:
    """Main bot engine handling all operations"""
    
    def __init__(self, database: DatabaseManager, cache: CacheManager):
        self.database = database
        self.cache = cache
        
        # Clients
        self.bot_client: Optional[Client] = None
        self.user_client: Optional[Client] = None
        self.voice_client: Optional[VoiceClient] = None
        self.py_tg_calls: Optional[PyTgCalls] = None
        
        # Services
        self.youtube: Optional[YouTubeService] = None
        self.spotify: Optional[SpotifyService] = None
        self.genius: Optional[GeniusService] = None
        self.lastfm: Optional[LastFMService] = None
        
        # Managers
        self.queue_manager = QueueManager()
        self.chat_contexts: Dict[int, ChatContext] = {}
        
        # Stats
        self.start_time = datetime.now()
        self.total_plays = 0
        self.total_users = 0
        
    async def initialize(self):
        """Initialize all components"""
        logger.info("🚀 Initializing Music Bot Engine...")
        
        # 1. Initialize Bot Client
        self.bot_client = Client(
            name="music_bot",
            api_id=config.telegram.api_id,
            api_hash=config.telegram.api_hash,
            bot_token=config.telegram.bot_token,
            in_memory=True,
            workers=config.telegram.workers
        )
        
        await self.bot_client.start()
        bot_info = await self.bot_client.get_me()
        logger.info(f"🤖 Bot: @{bot_info.username}")
        
        # 2. Initialize User Client (for Voice Chat)
        if config.enable_voice_chat:
            self.user_client = Client(
                name="assistant",
                api_id=config.telegram.api_id,
                api_hash=config.telegram.api_hash,
                session_string=config.telegram.string_session,
                in_memory=True
            )
            
            await self.user_client.start()
            user_info = await self.user_client.get_me()
            logger.info(f"👤 Assistant: @{user_info.username}")
            
            # Initialize Voice Client
            self.voice_client = VoiceClient(self.user_client)
            await self.voice_client.initialize()
            
        # 3. Initialize Services
        self.youtube = YouTubeService(config.api.youtube_api_key)
        if config.enable_spotify:
            self.spotify = SpotifyService(
                config.api.spotify_client_id,
                config.api.spotify_client_secret
            )
        if config.enable_genius:
            self.genius = GeniusService(config.api.genius_access_token)
        if config.enable_lastfm:
            self.lastfm = LastFMService(
                config.api.lastfm_api_key,
                config.api.lastfm_api_secret
            )
        
        # 4. Load stats from database
        await self.load_stats()
        
        logger.info("✅ Bot Engine initialized successfully")
        
    async def initialize_light(self):
        """Light initialization for web server"""
        self.bot_client = Client(
            name="music_bot_light",
            api_id=config.telegram.api_id,
            api_hash=config.telegram.api_hash,
            bot_token=config.telegram.bot_token,
            in_memory=True,
            no_updates=True
        )
        await self.bot_client.start()
        
    async def search_tracks(self, query: str, source: str = "youtube", limit: int = 10) -> List[Dict]:
        """Search tracks from various sources"""
        try:
            if source == "youtube":
                return await self.youtube.search(query, limit)
            elif source == "spotify" and self.spotify:
                return await self.spotify.search_tracks(query, limit)
            elif source == "all":
                # Search all available sources
                tasks = [self.youtube.search(query, limit)]
                if self.spotify:
                    tasks.append(self.spotify.search_tracks(query, limit))
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                all_tracks = []
                seen_ids = set()
                
                for result in results:
                    if isinstance(result, list):
                        for track in result:
                            track_id = track.get("id") or track.get("url")
                            if track_id and track_id not in seen_ids:
                                seen_ids.add(track_id)
                                all_tracks.append(track)
                
                return all_tracks[:limit]
            else:
                raise BotError(f"Unknown source: {source}")
                
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise BotError(f"Search failed: {str(e)}")
    
    async def get_track_info(self, url: str) -> Optional[Dict]:
        """Get track information from URL"""
        try:
            # Try YouTube first
            if "youtube.com" in url or "youtu.be" in url:
                return await self.youtube.get_video_info(url)
            
            # Try Spotify
            elif "spotify.com" in url and self.spotify:
                return await self.spotify.get_track_from_url(url)
            
            # Try other sources
            else:
                # Generic extraction
                return await self._extract_generic_info(url)
                
        except Exception as e:
            logger.error(f"Failed to get track info: {e}")
            return None
    
    async def play_in_chat(self, chat_id: int, track: Dict, user_id: int) -> bool:
        """Play track in specific chat"""
        try:
            # Get or create chat context
            if chat_id not in self.chat_contexts:
                self.chat_contexts[chat_id] = ChatContext(chat_id)
            
            context = self.chat_contexts[chat_id]
            
            # Check if voice client is available
            if not self.voice_client:
                raise BotError("Voice chat not available")
            
            # Get audio stream URL
            audio_url = await self._get_audio_stream_url(track)
            if not audio_url:
                raise BotError("Failed to get audio stream")
            
            # Join voice chat if not already joined
            if not await self.voice_client.is_joined(chat_id):
                await self.voice_client.join_chat(chat_id)
            
            # Play audio
            await self.voice_client.play_audio(chat_id, audio_url)
            
            # Update context
            context.is_playing = True
            context.is_paused = False
            context.current_track = track
            context.last_activity = datetime.now()
            
            # Add to queue history
            self.queue_manager.add_to_history(chat_id, track, user_id)
            
            # Update stats
            self.total_plays += 1
            await self.save_stats()
            
            # Scrobble to Last.fm
            if self.lastfm:
                await self._scrobble_track(track, user_id)
            
            logger.info(f"Playing track in chat {chat_id}: {track.get('title')}")
            return True
            
        except Exception as e:
            logger.error(f"Play error: {e}")
            raise BotError(f"Failed to play: {str(e)}")
    
    async def pause_playback(self, chat_id: int) -> bool:
        """Pause current playback"""
        if not self.voice_client:
            return False
        
        await self.voice_client.pause(chat_id)
        
        if chat_id in self.chat_contexts:
            self.chat_contexts[chat_id].is_paused = True
        
        return True
    
    async def resume_playback(self, chat_id: int) -> bool:
        """Resume paused playback"""
        if not self.voice_client:
            return False
        
        await self.voice_client.resume(chat_id)
        
        if chat_id in self.chat_contexts:
            self.chat_contexts[chat_id].is_paused = False
        
        return True
    
    async def stop_playback(self, chat_id: int) -> bool:
        """Stop playback and leave voice chat"""
        if not self.voice_client:
            return False
        
        await self.voice_client.leave_chat(chat_id)
        
        if chat_id in self.chat_contexts:
            context = self.chat_contexts[chat_id]
            context.is_playing = False
            context.is_paused = False
            context.current_track = None
        
        return True
    
    async def skip_track(self, chat_id: int) -> Optional[Dict]:
        """Skip to next track in queue"""
        if chat_id not in self.chat_contexts:
            return None
        
        context = self.chat_contexts[chat_id]
        next_track = self.queue_manager.get_next(chat_id)
        
        if next_track:
            await self.play_in_chat(chat_id, next_track["track"], next_track["user_id"])
            return next_track["track"]
        
        # No more tracks, stop playback
        await self.stop_playback(chat_id)
        return None
    
    async def get_lyrics(self, query: str) -> Optional[Dict]:
        """Get lyrics for a track"""
        if not self.genius:
            return None
        
        try:
            return await self.genius.search_lyrics(query)
        except Exception as e:
            logger.error(f"Lyrics error: {e}")
            return None
    
    async def get_queue(self, chat_id: int, page: int = 1, per_page: int = 10) -> Dict:
        """Get queue for chat with pagination"""
        return self.queue_manager.get_queue(chat_id, page, per_page)
    
    async def clear_queue(self, chat_id: int) -> bool:
        """Clear queue for chat"""
        return self.queue_manager.clear_queue(chat_id)
    
    async def shuffle_queue(self, chat_id: int) -> bool:
        """Shuffle queue"""
        return self.queue_manager.shuffle_queue(chat_id)
    
    async def set_volume(self, chat_id: int, volume: int) -> bool:
        """Set volume for voice chat"""
        if not self.voice_client:
            return False
        
        if volume < 0 or volume > 200:
            raise BotError("Volume must be between 0 and 200")
        
        await self.voice_client.set_volume(chat_id, volume)
        
        if chat_id in self.chat_contexts:
            self.chat_contexts[chat_id].volume = volume
        
        return True
    
    async def get_chat_context(self, chat_id: int) -> Optional[ChatContext]:
        """Get context for chat"""
        return self.chat_contexts.get(chat_id)
    
    async def get_bot_stats(self) -> Dict:
        """Get bot statistics"""
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        return {
            "uptime": f"{hours}h {minutes}m {seconds}s",
            "total_plays": self.total_plays,
            "total_users": self.total_users,
            "active_chats": len(self.chat_contexts),
            "queue_size": self.queue_manager.total_queued(),
            "start_time": self.start_time.isoformat(),
            "voice_chat_enabled": config.enable_voice_chat,
            "spotify_enabled": config.enable_spotify,
            "lyrics_enabled": config.enable_genius,
            "lastfm_enabled": config.enable_lastfm,
        }
    
    async def is_alive(self) -> bool:
        """Check if bot is alive"""
        return self.bot_client is not None and await self.bot_client.get_me() is not None
    
    async def shutdown(self):
        """Shutdown bot engine"""
        logger.info("Shutting down bot engine...")
        
        if self.voice_client:
            await self.voice_client.shutdown()
        
        if self.user_client:
            await self.user_client.stop()
        
        if self.bot_client:
            await self.bot_client.stop()
        
        await self.save_stats()
        logger.info("Bot engine shutdown complete")
    
    # Private methods
    async def _get_audio_stream_url(self, track: Dict) -> Optional[str]:
        """Get audio stream URL for track"""
        try:
            if track.get("source") == "youtube":
                return await self.youtube.get_stream_url(track["url"])
            elif track.get("source") == "spotify" and self.spotify:
                # Convert Spotify to YouTube
                yt_tracks = await self.youtube.search(
                    f"{track['title']} {track.get('artist', '')}",
                    limit=1
                )
                if yt_tracks:
                    return await self.youtube.get_stream_url(yt_tracks[0]["url"])
            else:
                # Generic URL
                return track.get("url")
        except Exception as e:
            logger.error(f"Failed to get audio stream: {e}")
            return None
    
    async def _extract_generic_info(self, url: str) -> Dict:
        """Extract info from generic URL"""
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                return {
                    "title": info.get("title", "Unknown"),
                    "url": url,
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail"),
                    "artist": info.get("uploader", "Unknown"),
                    "source": "generic",
                }
        except Exception as e:
            logger.error(f"Generic extraction failed: {e}")
            raise BotError(f"Failed to extract info: {str(e)}")
    
    async def _scrobble_track(self, track: Dict, user_id: int):
        """Scrobble track to Last.fm"""
        if not self.lastfm:
            return
        
        try:
            await self.lastfm.scrobble(
                track_name=track.get("title", ""),
                artist=track.get("artist", ""),
                user_id=user_id
            )
        except Exception as e:
            logger.error(f"Last.fm scrobble failed: {e}")
    
    async def load_stats(self):
        """Load statistics from database"""
        try:
            stats = await self.database.get_stats()
            if stats:
                self.total_plays = stats.get("total_plays", 0)
                self.total_users = stats.get("total_users", 0)
        except Exception as e:
            logger.error(f"Failed to load stats: {e}")
    
    async def save_stats(self):
        """Save statistics to database"""
        try:
            await self.database.save_stats({
                "total_plays": self.total_plays,
                "total_users": self.total_users,
                "last_updated": datetime.now(),
            })
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
