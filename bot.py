"""
Simple Music Bot - Working Version
"""

import os
import asyncio
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from pyrogram import Client, filters
from pyrogram.types import Message
import logging

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

# Basic commands
@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    """Start command"""
    await message.reply_text(
        f"🎵 **{config.bot.name}**\n\n"
        "Hello! I'm a music bot.\n"
        "Use /play to play music.\n\n"
        f"⚡ Status: **Online**"
    )

@app.on_message(filters.command("play"))
async def play_command(client, message: Message):
    """Play command"""
    if len(message.command) < 2:
        await message.reply_text("Usage: /play <song name>")
        return
    
    query = " ".join(message.command[1:])
    await message.reply_text(f"🎵 Searching: {query}")

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    """Help command"""
    await message.reply_text(
        "📖 **Commands:**\n\n"
        "/start - Start the bot\n"
        "/play <song> - Play a song\n"
        "/help - Show this help\n\n"
        f"🤖 Bot: {config.bot.name}"
    )

@app.on_message(filters.command("ping"))
async def ping_command(client, message: Message):
    """Ping command"""
    await message.reply_text("🏓 Pong!")

# Main function
async def main():
    """Main function"""
    logger.info("🚀 Starting Music Bot...")
    
    # Check credentials
    if not config.telegram.api_id or not config.telegram.api_hash or not config.telegram.bot_token:
        logger.error("❌ Missing Telegram credentials in .env file")
        return
    
    try:
        await app.start()
        
        # Get bot info
        me = await app.get_me()
        logger.info(f"✅ Bot started: @{me.username} (ID: {me.id})")
        
        # Send startup message to admin
        if config.bot.admin_ids:
            for admin_id in config.bot.admin_ids:
                try:
                    await app.send_message(
                        admin_id,
                        f"🤖 **Bot Started Successfully!**\n\n"
                        f"**Name:** {me.first_name}\n"
                        f"**Username:** @{me.username}\n"
                        f"**ID:** {me.id}\n"
                        f"**Status:** ✅ Online"
                    )
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
        
        # Keep running
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"❌ Failed to start bot: {e}")
    finally:
        await app.stop()
        logger.info("👋 Bot stopped")

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("cache", exist_ok=True)
    
    # Run the bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
