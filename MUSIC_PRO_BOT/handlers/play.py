import asyncio
import logging
from typing import Optional, Dict, List
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, ChatType

from config import config
from core.bot_engine import MusicBotEngine
from utils.logger import logger
from utils.formatters import format_duration, format_size
from utils.exceptions import BotError
from utils.decorators import rate_limit, admin_only

class PlayHandler:
    """Handle play commands"""
    
    def __init__(self, bot_engine: MusicBotEngine):
        self.bot_engine = bot_engine
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup command handlers"""
        
        @self.bot_engine.bot_client.on_message(filters.command("play") & filters.group)
        @rate_limit(5, 60)  # 5 requests per minute
        async def play_command(client: Client, message: Message):
            await self.handle_play(message)
        
        @self.bot_engine.bot_client.on_message(filters.command("pause") & filters.group)
        async def pause_command(client: Client, message: Message):
            await self.handle_pause(message)
        
        @self.bot_engine.bot_client.on_message(filters.command("resume") & filters.group)
        async def resume_command(client: Client, message: Message):
            await self.handle_resume(message)
        
        @self.bot_engine.bot_client.on_message(filters.command("skip") & filters.group)
        async def skip_command(client: Client, message: Message):
            await self.handle_skip(message)
        
        @self.bot_engine.bot_client.on_message(filters.command("stop") & filters.group)
        async def stop_command(client: Client, message: Message):
            await self.handle_stop(message)
        
        @self.bot_engine.bot_client.on_message(filters.command("volume") & filters.group)
        async def volume_command(client: Client, message: Message):
            await self.handle_volume(message)
    
    async def handle_play(self, message: Message):
        """Handle /play command"""
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        if not message.command[1:]:
            await message.reply_text(
                "🎵 **Usage:** `/play <song name or URL>`\n"
                "**Examples:**\n"
                "• `/play Shape of You`\n"
                "• `/play https://youtube.com/watch?v=...`\n"
                "• `/play spotify:track:...`"
            )
            return
        
        query = " ".join(message.command[1:])
        
        # Check if query is a URL
        is_url = any(domain in query for domain in [
            "youtube.com", "youtu.be", "spotify.com", "deezer.com"
        ])
        
        # Send searching message
        status_msg = await message.reply_text(
            f"🔍 **Searching:** `{query[:50]}{'...' if len(query) > 50 else ''}`"
        )
        
        try:
            # Get track info
            if is_url:
                # Direct URL
                track = await self.bot_engine.get_track_info(query)
                if not track:
                    await status_msg.edit_text("❌ **Invalid URL or track not found**")
                    return
            else:
                # Search query
                results = await self.bot_engine.search_tracks(query, source="all", limit=5)
                if not results:
                    await status_msg.edit_text("❌ **No results found**")
                    return
                
                # Let user choose from results
                if len(results) > 1:
                    await self._show_search_results(message, results, query)
                    await status_msg.delete()
                    return
                
                track = results[0]
            
            # Update status
            await status_msg.edit_text(f"⬇️ **Downloading:** `{track['title']}`")
            
            # Play track
            await self.bot_engine.play_in_chat(chat_id, track, user_id)
            
            # Send success message
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⏸️ Pause", callback_data=f"pause_{chat_id}"),
                    InlineKeyboardButton("⏭️ Skip", callback_data=f"skip_{chat_id}"),
                ],
                [
                    InlineKeyboardButton("🔊 Volume", callback_data=f"volume_{chat_id}"),
                    InlineKeyboardButton("📜 Queue", callback_data=f"queue_{chat_id}"),
                ]
            ])
            
            caption = self._format_track_caption(track, message.from_user)
            await status_msg.edit_text(caption, reply_markup=keyboard)
            
        except BotError as e:
            await status_msg.edit_text(f"❌ **Error:** {str(e)}")
        except Exception as e:
            logger.error(f"Play error: {e}", exc_info=True)
            await status_msg.edit_text("❌ **An error occurred. Please try again.**")
    
    async def handle_pause(self, message: Message):
        """Handle /pause command"""
        chat_id = message.chat.id
        
        try:
            success = await self.bot_engine.pause_playback(chat_id)
            if success:
                await message.reply_text("⏸️ **Playback paused**")
            else:
                await message.reply_text("❌ **Nothing is playing**")
        except Exception as e:
            logger.error(f"Pause error: {e}")
            await message.reply_text("❌ **Failed to pause**")
    
    async def handle_resume(self, message: Message):
        """Handle /resume command"""
        chat_id = message.chat.id
        
        try:
            success = await self.bot_engine.resume_playback(chat_id)
            if success:
                await message.reply_text("▶️ **Playback resumed**")
            else:
                await message.reply_text("❌ **Nothing is paused**")
        except Exception as e:
            logger.error(f"Resume error: {e}")
            await message.reply_text("❌ **Failed to resume**")
    
    async def handle_skip(self, message: Message):
        """Handle /skip command"""
        chat_id = message.chat.id
        
        try:
            next_track = await self.bot_engine.skip_track(chat_id)
            if next_track:
                await message.reply_text(
                    f"⏭️ **Skipped to next track**\n"
                    f"🎵 **Now playing:** {next_track['title']}"
                )
            else:
                await message.reply_text("⏹️ **Queue is empty. Playback stopped.**")
        except Exception as e:
            logger.error(f"Skip error: {e}")
            await message.reply_text("❌ **Failed to skip**")
    
    async def handle_stop(self, message: Message):
        """Handle /stop command"""
        chat_id = message.chat.id
        
        try:
            success = await self.bot_engine.stop_playback(chat_id)
            if success:
                await message.reply_text("⏹️ **Playback stopped**")
            else:
                await message.reply_text("❌ **Nothing is playing**")
        except Exception as e:
            logger.error(f"Stop error: {e}")
            await message.reply_text("❌ **Failed to stop**")
    
    async def handle_volume(self, message: Message):
        """Handle /volume command"""
        chat_id = message.chat.id
        
        if len(message.command) < 2:
            # Show current volume
            context = await self.bot_engine.get_chat_context(chat_id)
            if context:
                await message.reply_text(f"🔊 **Current volume:** {context.volume}%")
            else:
                await message.reply_text("❌ **Not in voice chat**")
            return
        
        try:
            volume = int(message.command[1])
            success = await self.bot_engine.set_volume(chat_id, volume)
            if success:
                await message.reply_text(f"🔊 **Volume set to:** {volume}%")
            else:
                await message.reply_text("❌ **Failed to set volume**")
        except ValueError:
            await message.reply_text("❌ **Please enter a number between 0 and 200**")
        except BotError as e:
            await message.reply_text(f"❌ **Error:** {str(e)}")
        except Exception as e:
            logger.error(f"Volume error: {e}")
            await message.reply_text("❌ **Failed to set volume**")
    
    # Helper methods
    async def _show_search_results(self, message: Message, results: List[Dict], query: str):
        """Show search results for user to choose"""
        buttons = []
        
        for i, track in enumerate(results[:5], 1):
            title = track['title'][:30] + "..." if len(track['title']) > 30 else track['title']
            duration = format_duration(track.get('duration', 0))
            
            buttons.append([
                InlineKeyboardButton(
                    f"{i}. {title} ({duration})",
                    callback_data=f"play_select:{track['url']}"
                )
            ])
        
        buttons.append([
            InlineKeyboardButton("⬅️ Back", callback_data="search_back"),
            InlineKeyboardButton("Next ➡️", callback_data="search_next"),
        ])
        
        keyboard = InlineKeyboardMarkup(buttons)
        
        await message.reply_text(
            f"🔍 **Search results for:** `{query}`\n"
            f"**Select a track to play:**",
            reply_markup=keyboard
        )
    
    def _format_track_caption(self, track: Dict, user) -> str:
        """Format track caption"""
        title = track.get('title', 'Unknown')
        artist = track.get('artist') or track.get('channel', 'Unknown')
        duration = format_duration(track.get('duration', 0))
        
        caption = (
            f"🎵 **Now Playing**\n\n"
            f"**Title:** {title}\n"
            f"**Artist:** {artist}\n"
            f"**Duration:** {duration}\n"
            f"**Source:** {track.get('source', 'Unknown').title()}\n\n"
            f"👤 **Requested by:** {user.mention}\n"
            f"🕒 **Started at:** {datetime.now().strftime('%H:%M:%S')}"
        )
        
        return caption
