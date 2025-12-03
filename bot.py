"""
Music Bot with Web Server for Render
"""

import os
import asyncio
import sys
import logging
from pathlib import Path
from aiohttp import web

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pyrogram import Client, filters
from pyrogram.types import Message

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import config
try:
    from config import config
    logger.info("✅ Config loaded successfully")
except ImportError as e:
    logger.error(f"❌ Failed to import config: {e}")
    sys.exit(1)

# Create bot client
app = Client(
    "music_bot",
    api_id=config.telegram.api_id,
    api_hash=config.telegram.api_hash,
    bot_token=config.telegram.bot_token,
    in_memory=True,
)

# ==================== WEB SERVER FOR RENDER ====================

async def health_check(request):
    """Health check endpoint for Render"""
    return web.Response(text="✅ Bot is running")

async def start_web_server():
    """Start web server for health checks"""
    web_app = web.Application()
    web_app.router.add_get('/', health_check)
    web_app.router.add_get('/health', health_check)
    web_app.router.add_get('/ping', health_check)
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', config.server.port)
    await site.start()
    
    logger.info(f"🌐 Web server started on port {config.server.port}")
    return runner

# ==================== BOT COMMANDS ====================

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    """Start command"""
    await message.reply_text(
        f"🎵 **{config.bot.name}**\n\n"
        "Hello! I'm a music bot with advanced features.\n\n"
        "**Available Commands:**\n"
        "• /play <song> - Play music\n"
        "• /search <query> - Search songs\n"
        "• /help - Show all commands\n\n"
        f"⚡ Status: **Online**"
    )

@app.on_message(filters.command("play"))
async def play_command(client, message: Message):
    """Play command"""
    if len(message.command) < 2:
        await message.reply_text("🎵 **Usage:** `/play <song name or YouTube URL>`\n**Example:** `/play Shape of You`")
        return
    
    query = " ".join(message.command[1:])
    status_msg = await message.reply_text(f"🔍 **Searching:** `{query}`")
    
    # Simulate search and play
    await asyncio.sleep(2)
    await status_msg.edit_text(f"🎵 **Playing:** `{query}`\n⏳ Downloading audio...")
    
    await asyncio.sleep(3)
    await status_msg.edit_text(
        f"✅ **Now Playing:** `{query}`\n"
        f"👤 Requested by: {message.from_user.mention}\n"
        f"🎧 Stream quality: {config.audio.quality}"
    )

@app.on_message(filters.command("search"))
async def search_command(client, message: Message):
    """Search command"""
    if len(message.command) < 2:
        await message.reply_text("🔍 **Usage:** `/search <query>`\n**Example:** `/search Ed Sheeran`")
        return
    
    query = " ".join(message.command[1:])
    
    # Simulate search results
    results = [
        f"1. {query} - Artist 1 (3:45)",
        f"2. {query} Remix - Artist 2 (4:20)",
        f"3. {query} Acoustic - Artist 3 (3:15)",
        f"4. {query} Live - Artist 4 (5:30)",
        f"5. Best of {query} - Various Artists (1:02:15)",
    ]
    
    await message.reply_text(
        f"🔍 **Search Results for:** `{query}`\n\n" +
        "\n".join(results) +
        "\n\nUse `/play <number>` to play a song."
    )

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    """Help command"""
    help_text = f"""
📖 **{config.bot.name} - Help Guide**

🎵 **Music Commands:**
• `/play <song>` - Play a song
• `/search <query>` - Search for songs
• `/pause` - Pause playback
• `/resume` - Resume playback
• `/skip` - Skip current song

🔧 **Utility Commands:**
• `/start` - Start the bot
• `/help` - Show this help
• `/ping` - Check bot latency
• `/stats` - Bot statistics

⚙️ **Features:**
• YouTube Music
• Spotify Integration
• Voice Chat Support
• High Quality Audio
• Queue System

🌐 **Status:** ✅ Online
🤖 **Bot:** {config.bot.name}
"""
    await message.reply_text(help_text)

@app.on_message(filters.command("ping"))
async def ping_command(client, message: Message):
    """Ping command"""
    start = asyncio.get_event_loop().time()
    msg = await message.reply_text("🏓 Pinging...")
    end = asyncio.get_event_loop().time()
    latency = (end - start) * 1000
    
    await msg.edit_text(f"🏓 **Pong!**\n⏱️ Latency: `{latency:.2f} ms`\n🌐 Host: Render")

@app.on_message(filters.command("stats"))
async def stats_command(client, message: Message):
    """Stats command"""
    stats_text = f"""
📊 **Bot Statistics**

🤖 **Bot Info:**
• Name: {config.bot.name}
• Username: @{(await client.get_me()).username}
• ID: `{(await client.get_me()).id}`

⚡ **Features:**
• Voice Chat: {'✅ Enabled' if config.enable_voice_chat else '❌ Disabled'}
• Spotify: {'✅ Enabled' if config.enable_spotify else '❌ Disabled'}
• YouTube API: {'✅ Enabled' if config.enable_youtube_api else '❌ Disabled'}
• Lyrics: {'✅ Enabled' if config.enable_genius else '❌ Disabled'}

🌐 **Server:**
• Host: Render (Free Tier)
• Port: {config.server.port}
• Environment: {config.server.environment}

🔧 **Audio Settings:**
• Quality: {config.audio.quality}
• Format: {config.audio.format}
• Max Size: {config.audio.max_file_size // (1024*1024)}MB
"""
    await message.reply_text(stats_text)

# ==================== MAIN FUNCTION ====================

async def main():
    """Main function"""
    logger.info("🚀 Starting Music Bot...")
    
    # Check credentials
    if not config.telegram.api_id or not config.telegram.api_hash or not config.telegram.bot_token:
        logger.error("❌ Missing Telegram credentials in .env file")
        logger.error("Please add API_ID, API_HASH, and BOT_TOKEN to .env")
        return
    
    # Create necessary directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("cache", exist_ok=True)
    
    web_runner = None
    try:
        # Start web server for Render health checks
        web_runner = await start_web_server()
        
        # Start Telegram bot
        await app.start()
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"✅ Bot started: @{me.username} (ID: {me.id})")
        
        # Send startup message to admin (silently fail if error)
        if config.bot.admin_ids:
            for admin_id in config.bot.admin_ids:
                try:
                    if admin_id > 0:  # Valid user ID
                        await app.send_message(
                            admin_id,
                            f"🤖 **Bot Started Successfully!**\n\n"
                            f"**Name:** {me.first_name}\n"
                            f"**Username:** @{me.username}\n"
                            f"**ID:** {me.id}\n"
                            f"**Host:** Render Free Tier\n"
                            f"**Port:** {config.server.port}\n"
                            f"**Status:** ✅ Online"
                        )
                        logger.info(f"Notified admin: {admin_id}")
                except Exception as e:
                    logger.warning(f"Could not notify admin {admin_id}: {e}")
                    # Don't stop bot if admin notification fails
        
        logger.info("🎉 Bot is now running! Press Ctrl+C to stop.")
        logger.info(f"🌐 Health check: http://localhost:{config.server.port}/health")
        
        # Keep bot running
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}", exc_info=True)
    finally:
        # Cleanup
        if web_runner:
            await web_runner.cleanup()
        await app.stop()
        logger.info("👋 Bot shutdown complete")

if __name__ == "__main__":
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
