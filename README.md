# 🎵 Advanced Telegram Music Bot

A production-ready, feature-rich Telegram Music Bot with Voice Chat support, multiple music sources, and advanced features.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Pyrogram](https://img.shields.io/badge/Pyrogram-2.0-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Deploy](https://img.shields.io/badge/Deploy-Render-blueviolet)

## ✨ Features

### 🎵 Music Playback
- YouTube, Spotify, Deezer, SoundCloud support
- High-quality audio streaming (up to 320kbps)
- Voice Chat support with PyTgCalls
- Queue system with shuffle/repeat
- Playlists management
- Lyrics display (Genius API)

### 🔍 Search
- Multi-source search (YouTube, Spotify, etc.)
- Smart search with caching
- Search suggestions
- Trend tracking

### 📊 Analytics
- Last.fm scrobbling
- Play statistics
- User analytics
- Bot performance monitoring

### ⚙️ Advanced Features
- String Session support (Voice Chat)
- Multiple API integrations
- Redis caching for performance
- MongoDB for data persistence
- Rate limiting and throttling
- Circuit breaker pattern
- Error handling and logging
- Health checks and monitoring

### 🎨 User Experience
- Inline keyboards
- Progress bars
- Real-time updates
- Pagination
- Customizable settings

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- MongoDB database
- Redis server
- Telegram Bot Token
- Required API keys

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/music-bot.git
cd music-bot
```
2. **Install dependencies**
```bash
pip install -r requirements.txt
```
3. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your credentials
```
4. **Generate String Session (for Voice Chat)**
```bash
python start_session.py
```
5. **Run the bot**
```bash
python bot.py
```
6. **PyTgCalls install test**
```bash
pip install py-tgcalls==2.2.8
```

7. **Check if installed**
```bash
python -c "import pytgcalls; print(f'PyTgCalls version: {pytgcalls.__version__}')"
```
8. **TgCrypto install karo**
```bash
pip install TgCrypto==1.2.5
```
9. **Environment variable fix**
```bash
# .env file me
AUDIO_QUALITY=192k  # Ya "HIGH" ki jagah "192k"
```
