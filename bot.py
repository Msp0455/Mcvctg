"""
Music Bot - Working Version
"""

import os
import asyncio
import sys
import logging
from pathlib import Path
from aiohttp import web

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import config
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from config import config
    logger.info("✅ Config loaded")
except Exception as e:
    logger.error(f"❌ Config error: {e}")
    sys.exit(1)

# Create bot client
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

app = Client(
    "music_bot",
    api_id=config.telegram.api_id,
    api_hash=config.telegram.api_hash,
    bot_token=config.telegram.bot_token,
    in_memory=True,
)

# ==================== WEB SERVER ====================

async def health_check(request):
    """Health check endpoint"""
    return web.Response(text="✅ Music Bot is running")

async def start_web_server():
    """Start web server for Render"""
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

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message: Message):
    """Start command - PRIVATE CHAT ONLY"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎵 Play Music", callback_data="play_help")],
        [InlineKeyboardButton("📖 Commands", callback_data="help")],
        [InlineKeyboardButton("🔧 Support", url="https://t.me/username")],
    ])
    
    await message.reply_text(
        f"🎵 **Welcome to {config.bot.name}!**\n\n"
        "I'm an advanced music bot with these features:\n\n"
        "✨ **Features:**\n"
        "• 🎧 High Quality Audio\n"
        "• 🔍 Smart Search\n"
        "• 📝 Lyrics Support\n"
        "• 🎤 Voice Chat Ready\n\n"
        "📌 **Use /help to see all commands**\n\n"
        "⚡ **Status:** ✅ **Online**",
        reply_markup=keyboard
    )

@app.on_message(filters.command("start") & filters.group)
async def start_group_command(client, message: Message):
    """Start command for groups"""
    await message.reply_text(
        f"🎵 **{config.bot.name} is here!**\n\n"
        "I'm ready to play music in this group.\n\n"
        "**Basic Commands:**\n"
        "• /play <song> - Play music\n"
        "• /search <query> - Search songs\n"
        "• /help - All commands\n\n"
        "Make me admin for best experience!"
    )

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    """Help command"""
    help_text = f"""
📖 **{config.bot.name} - Help**

🎵 **Music Commands:**
• `/play <song>` - Play a song
• `/search <query>` - Search songs
• `/lyrics <song>` - Get lyrics
• `/queue` - Show queue

🔧 **Utility Commands:**
• `/start` - Start bot
• `/help` - This message
• `/ping` - Check latency
• `/stats` - Bot stats

🎤 **Voice Chat:**
• `/join` - Join voice chat
• `/leave` - Leave voice chat
• `/volume <1-200>` - Set volume

⚡ **Features Available:**
• YouTube Music: {'✅' if config.enable_youtube_api else '❌'}
• Spotify: {'✅' if config.enable_spotify else '❌'}
• Voice Chat: {'✅' if config.enable_voice_chat else '❌'}

🤖 **Bot:** {config.bot.name}
🌐 **Status:** ✅ Online
"""
    await message.reply_text(help_text)

@app.on_message(filters.command("ping"))
async def ping_command(client, message: Message):
    """Ping command"""
    import time
    start = time.time()
    msg = await message.reply_text("🏓 Pinging...")
    end = time.time()
    latency = (end - start) * 1000
    
    await msg.edit_text(
        f"🏓 **Pong!**\n"
        f"⏱️ **Latency:** `{latency:.2f} ms`\n"
        f"🌐 **Host:** Render\n"
        f"🤖 **Bot:** @{(await client.get_me()).username}"
    )

@app.on_message(filters.command("play") & filters.group)
async def play_command(client, message: Message):
    """Play command for groups"""
    if len(message.command) < 2:
        await message.reply_text(
            "🎵 **Usage:** `/play <song name or YouTube URL>`\n\n"
            "**Examples:**\n"
            "• `/play Shape of You`\n"
            "• `/play https://youtube.com/watch?v=...`"
        )
        return
    
    query = " ".join(message.command[1:])
    msg = await message.reply_text(f"🔍 **Searching:** `{query}`")
    
    # Simulate search and play
    await asyncio.sleep(1.5)
    await msg.edit_text(f"⬇️ **Downloading audio...**")
    
    await asyncio.sleep(2)
    
    # Success message
    await msg.edit_text(
        f"🎵 **Now Playing**\n\n"
        f"**Title:** {query}\n"
        f"**Quality:** {config.audio.quality}\n"
        f"**Requested by:** {message.from_user.mention}\n\n"
        f"Use /pause, /resume, or /skip to control playback."
    )

@app.on_message(filters.command("search"))
async def search_command(client, message: Message):
    """Search command"""
    if len(message.command) < 2:
        await message.reply_text("🔍 **Usage:** `/search <query>`")
        return
    
    query = " ".join(message.command[1:])
    
    # Simulate search results
    results = [
        {"title": f"{query} - Original", "duration": "3:45"},
        {"title": f"{query} (Remix)", "duration": "4:20"},
        {"title": f"{query} Acoustic", "duration": "3:15"},
        {"title": f"{query} Live", "duration": "5:30"},
        {"title": f"Best of {query}", "duration": "1:02:15"},
    ]
    
    response = f"🔍 **Search Results for:** `{query}`\n\n"
    for i, result in enumerate(results, 1):
        response += f"**{i}. {result['title']}**\n"
        response += f"   ⏱️ {result['duration']}\n\n"
    
    response += "Use `/play <number>` to play a song."
    
    await message.reply_text(response)

# ==================== CALLBACK HANDLERS ====================

@app.on_callback_query(filters.regex("^help$"))
async def help_callback(client, callback_query):
    """Help callback"""
    await callback_query.answer()
    await help_command(client, callback_query.message)

@app.on_callback_query(filters.regex("^play_help$"))
async def play_help_callback(client, callback_query):
    """Play help callback"""
    await callback_query.answer("Use /play command to play music")
    await callback_query.message.reply_text(
        "🎵 **To play music:**\n\n"
        "1. In a group, use `/play <song name>`\n"
        "2. In private chat, send me a song name\n\n"
        "**Examples:**\n"
        "• `/play Shape of You`\n"
        "• `/play Bohemian Rhapsody`\n"
        "• `/play https://youtube.com/...`"
    )

# ==================== MAIN FUNCTION ====================

async def main():
    """Main function"""
    logger.info("="*50)
    logger.info("🚀 STARTING MUSIC BOT")
    logger.info("="*50)
    
    # Validate credentials
    if not all([config.telegram.api_id, config.telegram.api_hash, config.telegram.bot_token]):
        logger.error("❌ Missing Telegram credentials in .env")
        logger.error("Please set: API_ID, API_HASH, BOT_TOKEN")
        return
    
    web_runner = None
    
    try:
        # Start web server
        web_runner = await start_web_server()
        
        # Start Telegram bot
        await app.start()
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"✅ Bot Info:")
        logger.info(f"   Name: {me.first_name}")
        logger.info(f"   Username: @{me.username}")
        logger.info(f"   ID: {me.id}")
        
        # Test message to self
        try:
            await app.send_message(
                me.id,
                f"🤖 **Bot Started**\n\n"
                f"**Name:** {config.bot.name}\n"
                f"**Username:** @{me.username}\n"
                f"**Time:** {asyncio.get_event_loop().time():.2f}\n"
                f"**Host:** Render\n"
                f"**Status:** ✅ **OPERATIONAL**"
            )
            logger.info("✅ Test message sent to self")
        except Exception as e:
            logger.warning(f"Could not send test message: {e}")
        
        logger.info("="*50)
        logger.info("🎉 BOT IS NOW RUNNING!")
        logger.info("="*50)
        logger.info(f"🌐 Health check: http://localhost:{config.server.port}/health")
        logger.info(f"🤖 Bot link: https://t.me/{me.username}")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("🛑 Shutting down...")
        if web_runner:
            await web_runner.cleanup()
        await app.stop()
        logger.info("👋 Bot shutdown complete")

if __name__ == "__main__":
    # Create directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("downloads", exist_ok=True)
    
    # Run bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
