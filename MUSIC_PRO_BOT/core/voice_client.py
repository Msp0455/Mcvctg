import asyncio
import logging
from typing import Optional, Dict
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped, AudioVideoPiped, StreamAudioEnded
from pytgcalls.exceptions import GroupCallNotFound
from pytgcalls.types.input_stream import InputAudioStream

from config import config
from utils.logger import logger
from utils.exceptions import VoiceChatError

class VoiceClient:
    """Voice chat client using PyTgCalls 2.x"""
    
    def __init__(self, user_client):
        self.user_client = user_client
        self.py_tg_calls: Optional[PyTgCalls] = None
        self.active_chats: Dict[int, Dict] = {}
        
    async def initialize(self):
        """Initialize PyTgCalls"""
        self.py_tg_calls = PyTgCalls(self.user_client)
        
        # Setup event handlers for PyTgCalls 2.x
        @self.py_tg_calls.on_stream_end()
        async def stream_end_handler(client: PyTgCalls, update: StreamAudioEnded):
            await self._on_stream_end(update.chat_id)
        
        @self.py_tg_calls.on_participants_change()
        async def participants_change_handler(client: PyTgCalls, participants: int):
            logger.debug(f"Participants changed: {participants}")
        
        await self.py_tg_calls.start()
        logger.info("Voice client initialized")
    
    async def join_chat(self, chat_id: int) -> bool:
        """Join voice chat"""
        try:
            if not self.py_tg_calls:
                raise VoiceChatError("Voice client not initialized")
            
            # Check if already joined
            if await self.is_joined(chat_id):
                return True
            
            # Join with silent audio (PyTgCalls 2.x style)
            await self.py_tg_calls.join_group_call(
                chat_id,
                AudioPiped(
                    "https://github.com/TeamTelegram/TelegramMusicBot/raw/main/silent.mp3",
                    additional_ffmpeg_parameters="-re"
                )
            )
            
            self.active_chats[chat_id] = {
                "joined": True,
                "playing": False,
                "paused": False,
                "volume": 100,
            }
            
            logger.info(f"Joined voice chat: {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to join voice chat {chat_id}: {e}")
            raise VoiceChatError(f"Failed to join: {str(e)}")
    
    async def leave_chat(self, chat_id: int) -> bool:
        """Leave voice chat"""
        try:
            if not self.py_tg_calls:
                return False
            
            await self.py_tg_calls.leave_group_call(chat_id)
            
            if chat_id in self.active_chats:
                del self.active_chats[chat_id]
            
            logger.info(f"Left voice chat: {chat_id}")
            return True
            
        except GroupCallNotFound:
            # Already left
            return True
        except Exception as e:
            logger.error(f"Failed to leave voice chat {chat_id}: {e}")
            return False
    
    async def play_audio(self, chat_id: int, audio_url: str) -> bool:
        """Play audio in voice chat"""
        try:
            if not self.py_tg_calls:
                raise VoiceChatError("Voice client not initialized")
            
            if not await self.is_joined(chat_id):
                await self.join_chat(chat_id)
            
            # Change stream (PyTgCalls 2.x style)
            await self.py_tg_calls.change_stream(
                chat_id,
                AudioPiped(
                    audio_url,
                    additional_ffmpeg_parameters="-re"
                )
            )
            
            if chat_id in self.active_chats:
                self.active_chats[chat_id]["playing"] = True
                self.active_chats[chat_id]["paused"] = False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to play audio in {chat_id}: {e}")
            raise VoiceChatError(f"Failed to play: {str(e)}")
    
    async def pause(self, chat_id: int) -> bool:
        """Pause playback"""
        try:
            if not self.py_tg_calls:
                return False
            
            await self.py_tg_calls.pause_stream(chat_id)
            
            if chat_id in self.active_chats:
                self.active_chats[chat_id]["paused"] = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause in {chat_id}: {e}")
            return False
    
    async def resume(self, chat_id: int) -> bool:
        """Resume playback"""
        try:
            if not self.py_tg_calls:
                return False
            
            await self.py_tg_calls.resume_stream(chat_id)
            
            if chat_id in self.active_chats:
                self.active_chats[chat_id]["paused"] = False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume in {chat_id}: {e}")
            return False
    
    async def set_volume(self, chat_id: int, volume: int) -> bool:
        """Set volume (0-200) - PyTgCalls 2.x me direct volume control nahi hai"""
        try:
            if not self.py_tg_calls:
                return False
            
            # PyTgCalls 2.x me volume control FFmpeg parameters se karte hain
            # For now, just store the value
            if chat_id in self.active_chats:
                self.active_chats[chat_id]["volume"] = volume
            
            logger.info(f"Volume set to {volume}% for chat {chat_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set volume in {chat_id}: {e}")
            return False
    
    async def is_joined(self, chat_id: int) -> bool:
        """Check if joined to voice chat"""
        if chat_id not in self.active_chats:
            return False
        
        try:
            # Try to get call info to verify
            if self.py_tg_calls:
                # PyTgCalls 2.x me get_call method check karo
                call = await self.py_tg_calls.get_call(chat_id)
                return call is not None
        except:
            pass
        
        return self.active_chats[chat_id].get("joined", False)
    
    async def get_chat_info(self, chat_id: int) -> Optional[Dict]:
        """Get voice chat info"""
        return self.active_chats.get(chat_id)
    
    async def shutdown(self):
        """Shutdown voice client"""
        try:
            # Leave all voice chats
            for chat_id in list(self.active_chats.keys()):
                await self.leave_chat(chat_id)
            
            if self.py_tg_calls:
                await self.py_tg_calls.stop()
            
            logger.info("Voice client shutdown complete")
        except Exception as e:
            logger.error(f"Error during voice client shutdown: {e}")
    
    # Event handlers
    async def _on_stream_end(self, chat_id: int):
        """Handle stream end event"""
        logger.info(f"Stream ended in chat: {chat_id}")
        
        if chat_id in self.active_chats:
            self.active_chats[chat_id]["playing"] = False
        
        # Notify bot engine
        from core.bot_engine import MusicBotEngine
        # This would trigger next track in queue
    
    async def _on_kicked(self, chat_id: int):
        """Handle kicked from voice chat"""
        logger.info(f"Kicked from voice chat: {chat_id}")
        
        if chat_id in self.active_chats:
            del self.active_chats[chat_id]
    
    async def _on_left(self, chat_id: int):
        """Handle left voice chat"""
        logger.info(f"Left voice chat: {chat_id}")
        
        if chat_id in self.active_chats:
            del self.active_chats[chat_id]
