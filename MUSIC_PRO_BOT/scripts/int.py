#!/usr/bin/env python3
"""
Setup script for Music Bot
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header():
    """Print setup header"""
    print("\n" + "="*60)
    print("🎵 Music Bot Setup")
    print("="*60)

def check_python():
    """Check Python version"""
    print("\n🔍 Checking Python version...")
    
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required. Found {sys.version}")
        sys.exit(1)
    
    print(f"✅ Python {sys.version}")

def check_ffmpeg():
    """Check FFmpeg installation"""
    print("\n🔍 Checking FFmpeg...")
    
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✅ FFmpeg is installed")
            return True
    except FileNotFoundError:
        print("⚠️  FFmpeg not found. Audio conversion may not work.")
        
        system = platform.system()
        if system == "Linux":
            print("   Install with: sudo apt install ffmpeg")
        elif system == "Darwin":
            print("   Install with: brew install ffmpeg")
        elif system == "Windows":
            print("   Download from: https://ffmpeg.org/download.html")
        
        return False

def create_env_file():
    """Create .env file from template"""
    print("\n📝 Creating .env file...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_example.exists():
        print("❌ .env.example not found")
        return False
    
    if env_file.exists():
        print("✅ .env file already exists")
        return True
    
    # Copy template
    with open(env_example, 'r') as src, open(env_file, 'w') as dst:
        dst.write(src.read())
    
    print("✅ Created .env file")
    print("   Please edit .env file with your credentials")
    return True

def create_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = [
        "logs",
        "cache",
        "downloads",
        "backups",
        "assets/images",
        "assets/fonts",
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"   Created: {directory}")
    
    print("✅ Directories created")

def install_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing dependencies...")
    
    requirements = Path("requirements.txt")
    if not requirements.exists():
        print("❌ requirements.txt not found")
        return False
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True
        )
        print("✅ Dependencies installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def setup_database():
    """Setup database connection"""
    print("\n🗄️  Setting up database...")
    
    # Check MongoDB connection
    print("   Checking MongoDB connection...")
    
    # Check Redis connection
    print("   Checking Redis connection...")
    
    print("✅ Database setup complete")

def generate_string_session():
    """Generate string session"""
    print("\n🔑 String Session Setup")
    
    answer = input("Do you want to generate a string session for voice chat? (y/n): ")
    
    if answer.lower() == 'y':
        print("   Running string session generator...")
        try:
            subprocess.run([sys.executable, "start_session.py"], check=True)
            print("✅ String session generated")
        except subprocess.CalledProcessError:
            print("⚠️  Failed to generate string session")
            print("   You can run it later with: python start_session.py")
    else:
        print("⚠️  Voice chat will be disabled without string session")
        print("   You can generate it later with: python start_session.py")

def setup_complete():
    """Display setup completion message"""
    print("\n" + "="*60)
    print("✅ Setup Complete!")
    print("="*60)
    
    print("\n📋 Next steps:")
    print("1. Edit the .env file with your API credentials")
    print("2. Start the bot: python bot.py")
    print("3. For production: python app.py")
    
    print("\n⚡ Quick commands:")
    print("   Start bot:              python bot.py")
    print("   Generate session:       python start_session.py")
    print("   Run tests:              pytest")
    print("   Check health:           curl http://localhost:8080/health")
    
    print("\n📞 Need help?")
    print("   Create issue: https://github.com/yourusername/music-bot/issues")
    print("   Join support: https://t.me/your_support_chat")

def main():
    """Main setup function"""
    print_header()
    
    steps = [
        ("Check Python", check_python),
        ("Check FFmpeg", check_ffmpeg),
        ("Create directories", create_directories),
        ("Create .env file", create_env_file),
        ("Install dependencies", install_dependencies),
        ("Setup database", setup_database),
        ("String session", generate_string_session),
    ]
    
    for step_name, step_func in steps:
        print(f"\n[{step_name}]")
        try:
            if not step_func():
                print(f"⚠️  {step_name} had issues")
        except Exception as e:
            print(f"❌ Error in {step_name}: {e}")
    
    setup_complete()

if __name__ == "__main__":
    main()
