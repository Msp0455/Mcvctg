import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from math import floor

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format"""
    if not seconds:
        return "N/A"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def format_number(number: int) -> str:
    """Format large numbers with K, M, B suffixes"""
    if number < 1000:
        return str(number)
    elif number < 1000000:
        return f"{number/1000:.1f}K"
    elif number < 1000000000:
        return f"{number/1000000:.1f}M"
    else:
        return f"{number/1000000000:.1f}B"

def format_time_ago(timestamp: datetime) -> str:
    """Format time ago from timestamp"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"

def format_progress_bar(percentage: float, length: int = 10) -> str:
    """Format progress bar"""
    filled = floor(percentage * length / 100)
    empty = length - filled
    
    bar = "█" * filled + "░" * empty
    return f"{bar} {percentage:.1f}%"

def format_track_info(track: Dict) -> str:
    """Format track information for display"""
    title = track.get('title', 'Unknown')
    artist = track.get('artist') or track.get('channel', 'Unknown')
    duration = format_duration(track.get('duration', 0))
    
    return f"🎵 **{title}**\n👤 **{artist}**\n⏱️ **{duration}**"

def format_queue_position(position: int, total: int) -> str:
    """Format queue position"""
    return f"#{position} of {total}"

def format_volume(volume: int) -> str:
    """Format volume with emoji"""
    if volume == 0:
        return "🔇 0%"
    elif volume < 30:
        return f"🔈 {volume}%"
    elif volume < 70:
        return f"🔉 {volume}%"
    else:
        return f"🔊 {volume}%"

def format_search_results(results: List[Dict], start: int = 1) -> str:
    """Format search results list"""
    if not results:
        return "No results found."
    
    formatted = []
    for i, track in enumerate(results, start):
        title = track.get('title', 'Unknown')[:40]
        if len(track.get('title', '')) > 40:
            title += "..."
        
        artist = track.get('artist') or track.get('channel', 'Unknown')[:20]
        duration = format_duration(track.get('duration', 0))
        
        formatted.append(f"{i}. **{title}**\n   👤 {artist} • ⏱️ {duration}")
    
    return "\n\n".join(formatted)

def format_lyrics(lyrics: str, max_length: int = 4000) -> str:
    """Format lyrics for Telegram message"""
    if not lyrics:
        return "No lyrics found."
    
    # Clean up lyrics
    lyrics = lyrics.strip()
    
    # Truncate if too long
    if len(lyrics) > max_length:
        lyrics = lyrics[:max_length] + "...\n\n📖 **Lyrics truncated due to length**"
    
    return f"📝 **Lyrics:**\n\n{lyrics}"

def format_stats(stats: Dict) -> str:
    """Format bot statistics"""
    return f"""
📊 **Bot Statistics**

🤖 **General:**
• Uptime: {stats.get('uptime', 'N/A')}
• Total Plays: {format_number(stats.get('total_plays', 0))}
• Active Chats: {stats.get('active_chats', 0)}
• Total Users: {format_number(stats.get('total_users', 0))}

🎵 **Queue:**
• Tracks in Queue: {stats.get('queue_size', 0)}

⚙️ **Features:**
• Voice Chat: {'✅' if stats.get('voice_chat_enabled') else '❌'}
• Spotify: {'✅' if stats.get('spotify_enabled') else '❌'}
• Lyrics: {'✅' if stats.get('lyrics_enabled') else '❌'}
• Last.fm: {'✅' if stats.get('lastfm_enabled') else '❌'}
"""

def format_user_info(user: Dict) -> str:
    """Format user information"""
    username = f"@{user.get('username')}" if user.get('username') else "No username"
    
    return f"""
👤 **User Information**

**Name:** {user.get('first_name', '')} {user.get('last_name', '')}
**Username:** {username}
**ID:** `{user.get('id')}`
**Language:** {user.get('language_code', 'en')}

**Stats:**
• Tracks Played: {format_number(user.get('tracks_played', 0))}
• Time Listened: {format_duration(user.get('time_listened', 0))}
• Last Active: {format_time_ago(user.get('last_active', datetime.utcnow()))}
"""

def format_playlist_info(playlist: Dict) -> str:
    """Format playlist information"""
    return f"""
📁 **Playlist: {playlist.get('name', 'Unnamed')}**

**Description:** {playlist.get('description', 'No description')}
**Owner:** {playlist.get('owner', 'Unknown')}
**Tracks:** {playlist.get('track_count', 0)}
**Created:** {format_time_ago(playlist.get('created_at', datetime.utcnow()))}
**Updated:** {format_time_ago(playlist.get('updated_at', datetime.utcnow()))}
"""

def truncate_text(text: str, max_length: int, ellipsis: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(ellipsis)] + ellipsis

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file operations"""
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        name = name[:200 - len(ext) - 1]
        filename = f"{name}.{ext}" if ext else name
    
    return filename

def parse_time_string(time_str: str) -> Optional[timedelta]:
    """Parse time string like 1h30m, 2h, 45m, 30s"""
    pattern = re.compile(r'((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?')
    match = pattern.match(time_str)
    
    if not match:
        return None
    
    hours = int(match.group('hours') or 0)
    minutes = int(match.group('minutes') or 0)
    seconds = int(match.group('seconds') or 0)
    
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def humanize_time_delta(delta: timedelta) -> str:
    """Convert timedelta to human readable string"""
    total_seconds = int(delta.total_seconds())
    
    if total_seconds < 60:
        return f"{total_seconds} seconds"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def format_bitrate(bitrate: int) -> str:
    """Format bitrate in kbps"""
    return f"{bitrate} kbps"

def format_sample_rate(sample_rate: int) -> str:
    """Format sample rate in kHz"""
    return f"{sample_rate/1000:.1f} kHz"

def format_audio_quality(quality: str) -> str:
    """Format audio quality"""
    quality_map = {
        '64k': 'Low',
        '128k': 'Medium',
        '192k': 'High',
        '256k': 'Very High',
        '320k': 'Premium',
    }
    return quality_map.get(quality, quality)
