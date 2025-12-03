import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load env first
load_dotenv()

# Configure logging for Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Import after logging setup
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode

# Import utils
from utils.youtube import YouTubeManager
from utils.audio import AudioProcessor
from config import Config

# Ensure logs directory exists
os.makedirs('logs', exist_ok=True)
os.makedirs('downloads', exist_ok=True)

class MusicBot:
    def __init__(self):
        self.config = Config()
        self.client = None
        self.youtube = YouTubeManager(self.config.YOUTUBE_API_KEY)
        self.audio_processor = AudioProcessor()
        
    async def start(self):
        """Start the bot"""
        logger.info("🚀 Starting Music Bot...")
        
        # Create Pyrogram client
        self.client = Client(
            name="music_bot",
            api_id=self.config.API_ID,
            api_hash=self.config.API_HASH,
            bot_token=self.config.BOT_TOKEN,
            parse_mode=ParseMode.HTML,
            in_memory=True  # Save memory on Render
        )
        
        # Setup handlers
        self.setup_handlers()
        
        # Start the client
        await self.client.start()
        
        bot_info = await self.client.get_me()
        logger.info(f"✅ Bot Started: @{bot_info.username}")
        logger.info(f"🆔 Bot ID: {bot_info.id}")
        
        # Send startup message to admin
        if self.config.ADMIN_ID:
            try:
                await self.client.send_message(
                    self.config.ADMIN_ID,
                    f"🤖 **Bot Started Successfully!**\n\n"
                    f"**Name:** {bot_info.first_name}\n"
                    f"**Username:** @{bot_info.username}\n"
                    f"**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"**Host:** Render Free Tier\n"
                    f"**Status:** ✅ Online"
                )
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")
        
        # Keep alive
        await idle()
        
    def setup_handlers(self):
        """Setup all command handlers"""
        
        @self.client.on_message(filters.command("start") & filters.private)
        async def start_command(client, message: Message):
            """Stylish start command"""
            user = message.from_user
            
            welcome_text = f"""
🎵 **Welcome to {self.config.BOT_NAME}!** 🎵

✨ **Hello {user.first_name}!** I'm an advanced music bot with premium features.

🔥 **Features:**
• 🎧 High Quality Audio (320kbps)
• 🔍 Smart Search (YouTube + Spotify)
• 📝 Lyrics with Genius API
• 📊 Last.fm Scrobbling
• 💾 Playlist Support
• ⚡ Fast Downloads

📌 **Available Commands:**
/play - Play any song
/search - Search songs
/lyrics - Get song lyrics
/spotify - Search on Spotify
/top - Top tracks from Last.fm
/help - All commands

⚙️ **Status:** ✅ **Online** | 🎶 **Ready to Play!**
            """
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎵 Play Music", callback_data="play_help"),
                    InlineKeyboardButton("📖 Help", callback_data="help_main")
                ],
                [
                    InlineKeyboardButton("🌟 GitHub", url="https://github.com"),
                    InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/yourusername")
                ]
            ])
            
            await message.reply_text(
                welcome_text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        
        @self.client.on_message(filters.command("play"))
        async def play_command(client, message: Message):
            """Play music with progress"""
            if len(message.command) < 2:
                await message.reply_text(
                    "🎵 **Usage:** `/play <song name>`\n"
                    "**Example:** `/play Shape of You`"
                )
                return
            
            query = " ".join(message.command[1:])
            msg = await message.reply_text(f"🔍 **Searching:** `{query}`")
            
            try:
                # Search YouTube
                results = await self.youtube.search(query, limit=1)
                if not results:
                    await msg.edit_text("❌ **No results found!**")
                    return
                
                video = results[0]
                await msg.edit_text(f"⬇️ **Downloading:** `{video['title']}`")
                
                # Download audio
                audio_path = await self.audio_processor.download_audio(
                    video['url'],
                    message.chat.id
                )
                
                if not audio_path:
                    await msg.edit_text("❌ **Download failed!**")
                    return
                
                # Send audio with stylish caption
                caption = f"""
🎵 **{video['title']}**
👤 **Channel:** {video.get('channel', 'Unknown')}
⏱️ **Duration:** {video.get('duration', 'N/A')}
🔗 **Source:** YouTube

✨ **Requested by:** {message.from_user.mention}
                """
                
                await message.reply_audio(
                    audio_path,
                    caption=caption,
                    title=video['title'][:64],
                    performer=video.get('channel', 'YouTube'),
                    thumb=video.get('thumbnail')
                )
                
                await msg.delete()
                os.remove(audio_path)
                
            except Exception as e:
                logger.error(f"Play error: {e}")
                await msg.edit_text("❌ **An error occurred!**")
        
        @self.client.on_message(filters.command("lyrics"))
        async def lyrics_command(client, message: Message):
            """Get lyrics using Genius API"""
            if not self.config.ENABLE_GENIUS:
                await message.reply_text("❌ **Lyrics feature is disabled!**")
                return
            
            query = " ".join(message.command[1:]) if len(message.command) > 1 else None
            
            if not query:
                # Try to get from currently playing
                await message.reply_text("🎶 **Usage:** `/lyrics <song name>`\n**Example:** `/lyrics Bohemian Rhapsody`")
                return
            
            msg = await message.reply_text(f"📝 **Searching lyrics:** `{query}`")
            
            try:
                # You'll need to implement Genius API integration
                lyrics = await self.get_genius_lyrics(query)
                
                if len(lyrics) > 4000:
                    lyrics = lyrics[:4000] + "...\n\n📖 **Lyrics truncated due to length**"
                
                await msg.edit_text(
                    f"🎵 **Lyrics for:** `{query}`\n\n"
                    f"{lyrics}\n\n"
                    f"📚 **Source:** Genius API",
                    disable_web_page_preview=True
                )
            except Exception as e:
                logger.error(f"Lyrics error: {e}")
                await msg.edit_text("❌ **Failed to fetch lyrics!**")
        
        @self.client.on_message(filters.command("ping"))
        async def ping_command(client, message: Message):
            """Check bot latency"""
            start = datetime.now()
            msg = await message.reply_text("🏓 **Pinging...**")
            end = datetime.now()
            latency = (end - start).microseconds / 1000
            
            await msg.edit_text(
                f"🏓 **Pong!**\n"
                f"⏱️ **Latency:** `{latency:.2f} ms`\n"
                f"🕒 **Uptime:** `{self.get_uptime()}`\n"
                f"💾 **Memory:** `{self.get_memory_usage()} MB`"
            )
        
        @self.client.on_message(filters.command("stats"))
        async def stats_command(client, message: Message):
            """Bot statistics"""
            stats_text = f"""
📊 **Bot Statistics**

🤖 **Bot Info:**
• **Name:** {self.config.BOT_NAME}
• **Username:** @{(await client.get_me()).username}
• **ID:** `{(await client.get_me()).id}`

⚡ **Performance:**
• **Uptime:** {self.get_uptime()}
• **Ping:** Calculating...
• **Memory:** {self.get_memory_usage()} MB

🎵 **Features Status:**
• **YouTube API:** {'✅ Enabled' if self.config.YOUTUBE_API_KEY else '❌ Disabled'}
• **Spotify:** {'✅ Enabled' if self.config.ENABLE_SPOTIFY else '❌ Disabled'}
• **Genius Lyrics:** {'✅ Enabled' if self.config.ENABLE_GENIUS else '❌ Disabled'}
• **Last.fm:** {'✅ Enabled' if self.config.ENABLE_LASTFM else '❌ Disabled'}

🌐 **Host:** Render (Free Tier)
🔄 **Status:** ✅ **Operational**
            """
            
            await message.reply_text(stats_text)
    
    def get_uptime(self):
        """Get bot uptime"""
        if hasattr(self, 'start_time'):
            delta = datetime.now() - self.start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m {seconds}s"
        return "Unknown"
    
    def get_memory_usage(self):
        """Get memory usage"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return f"{process.memory_info().rss / 1024 / 1024:.2f}"
        except:
            return "N/A"

async def main():
    """Main function"""
    bot = MusicBot()
    bot.start_time = datetime.now()
    await bot.start()

if __name__ == "__main__":
    # Create event loop for Render
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
