#!/usr/bin/env python3
"""
Debug script for Music Bot
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

async def debug_bot():
    print("🔍 Debugging Music Bot...")
    print("="*50)
    
    # Check config
    try:
        from config import config
        print("✅ Config loaded")
        print(f"   Bot Name: {config.bot.name}")
        print(f"   API ID: {config.telegram.api_id}")
        print(f"   API Hash: {config.telegram.api_hash[:10]}...")
        print(f"   Bot Token: {config.telegram.bot_token[:10]}...")
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False
    
    # Check credentials
    if not config.telegram.bot_token:
        print("❌ Bot token missing")
        return False
    
    # Test Telegram API
    try:
        from pyrogram import Client
        
        app = Client(
            "debug_session",
            api_id=config.telegram.api_id,
            api_hash=config.telegram.api_hash,
            bot_token=config.telegram.bot_token,
            in_memory=True,
        )
        
        await app.start()
        me = await app.get_me()
        
        print("✅ Telegram connection successful!")
        print(f"   Bot: @{me.username}")
        print(f"   ID: {me.id}")
        print(f"   Name: {me.first_name}")
        
        # Send test message
        test_msg = await app.send_message(
            me.id,  # Send to self
            f"🤖 **Bot Test**\n\n"
            f"Name: {config.bot.name}\n"
            f"Status: ✅ Online\n"
            f"Time: {asyncio.get_event_loop().time()}"
        )
        print(f"✅ Test message sent (ID: {test_msg.id})")
        
        await app.stop()
        return True
        
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_bot())
    sys.exit(0 if success else 1)
