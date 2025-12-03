#!/usr/bin/env python3
"""
Generate String Session for Telegram User Account
Required for Voice Chat features
"""

import asyncio
import sys
import json
from pathlib import Path
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid
from config import config

async def generate_session():
    """Generate string session"""
    print("\n" + "="*60)
    print("🔑 TELEGRAM STRING SESSION GENERATOR")
    print("="*60 + "\n")
    
    # Get credentials
    api_id = config.telegram.api_id
    api_hash = config.telegram.api_hash
    
    if not api_id or not api_hash:
        print("❌ API_ID or API_HASH not found in .env file")
        print("Get them from: https://my.telegram.org")
        return
    
    print(f"API ID: {api_id}")
    print(f"API Hash: {api_hash[:10]}...\n")
    
    # Get phone number
    phone_number = input("📱 Enter your phone number (with country code): ").strip()
    
    # Create client
    client = Client(
        name="session_generator",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True
    )
    
    try:
        await client.connect()
        
        # Send code
        sent_code = await client.send_code(phone_number)
        print(f"\n📲 Code sent via: {sent_code.type.value}")
        
        # Get code
        phone_code = input("Enter the code you received: ").strip()
        
        # Sign in
        try:
            signed_in = await client.sign_in(
                phone_number=phone_number,
                phone_code_hash=sent_code.phone_code_hash,
                phone_code=phone_code
            )
        except SessionPasswordNeeded:
            # 2FA required
            print("\n🔒 Two-factor authentication enabled")
            password = input("Enter your 2FA password: ").strip()
            signed_in = await client.check_password(password)
        except PhoneCodeInvalid:
            print("\n❌ Invalid code. Please try again.")
            return
        
        # Get string session
        session_string = await client.export_session_string()
        
        # Get user info
        me = await client.get_me()
        
        print("\n" + "="*60)
        print("✅ SESSION GENERATED SUCCESSFULLY!")
        print("="*60)
        
        print(f"\n👤 User Info:")
        print(f"   Name: {me.first_name} {me.last_name or ''}")
        print(f"   Username: @{me.username}")
        print(f"   ID: {me.id}")
        
        print(f"\n🔑 String Session:\n")
        print(session_string)
        
        print(f"\n" + "="*60)
        print("📝 Save this in your .env file:")
        print("="*60)
        print(f"\nSTRING_SESSION={session_string}")
        
        # Save to file
        save = input("\n💾 Save to .env file? (y/n): ").lower()
        if save == 'y':
            env_file = Path(".env")
            if env_file.exists():
                with open(env_file, "a") as f:
                    f.write(f"\nSTRING_SESSION={session_string}")
                print("✅ Saved to .env file")
            else:
                print("❌ .env file not found")
        
        print("\n🎉 Done! You can now use voice chat features.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(generate_session())
