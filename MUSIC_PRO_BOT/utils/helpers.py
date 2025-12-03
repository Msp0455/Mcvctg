import asyncio
import os
import re
import random
import string
import hashlib
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from config import config
from utils.logger import logger

def generate_random_string(length: int = 10) -> str:
    """Generate random string"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_hash(data: str) -> str:
    """Generate SHA256 hash"""
    return hashlib.sha256(data.encode()).hexdigest()

def sanitize_text(text: str) -> str:
    """Sanitize text for safe display"""
    # Remove markdown special characters
    text = re.sub(r'([\_\*\[\]\(\)\~\`\>\#\+\-\=\|\{\}\.\!])', r'\\\1', text)
    return text

def parse_command_args(text: str) -> Tuple[str, List[str]]:
    """Parse command and arguments from message text"""
    if not text:
        return "", []
    
    parts = text.strip().split()
    if not parts:
        return "", []
    
    command = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []
    
    return command, args

def extract_urls(text: str) -> List[str]:
    """Extract URLs from text"""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.findall(text)

def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    patterns = [
        r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^https?://youtu\.be/[\w-]+',
        r'^https?://open\.spotify\.com/(track|album|playlist|artist)/[\w]+',
        r'^spotify:(track|album|playlist|artist):[\w]+',
        r'^https?://(?:www\.)?deezer\.com/[a-z]+/(track|album|playlist|artist)/\d+',
        r'^https?://soundcloud\.com/[\w-]+/[\w-]+',
    ]
    
    for pattern in patterns:
        if re.match(pattern, url, re.IGNORECASE):
            return True
    
    return False

def get_url_type(url: str) -> str:
    """Get type of URL"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'spotify.com' in url or url.startswith('spotify:'):
        return 'spotify'
    elif 'deezer.com' in url:
        return 'deezer'
    elif 'soundcloud.com' in url:
        return 'soundcloud'
    else:
        return 'unknown'

def format_bytes(bytes_size: int) -> str:
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def format_time(seconds: int) -> str:
    """Format seconds to HH:MM:SS or MM:SS"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"

def parse_time(time_str: str) -> Optional[int]:
    """Parse time string to seconds"""
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            if len(parts) == 2:
                # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:
                # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
        else:
            # Assume seconds
            return int(time_str)
    except:
        return None

def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def get_file_extension(filename: str) -> str:
    """Get file extension"""
    return Path(filename).suffix.lower()

def is_audio_file(filename: str) -> bool:
    """Check if file is audio"""
    audio_extensions = ['.mp3', '.m4a', '.ogg', '.flac', '.wav', '.opus']
    return get_file_extension(filename) in audio_extensions

def get_file_size(filepath: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(filepath)
    except:
        return 0

async def run_command(cmd: List[str]) -> Tuple[int, str, str]:
    """Run shell command asynchronously"""
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return (
            process.returncode,
            stdout.decode('utf-8', errors='ignore').strip(),
            stderr.decode('utf-8', errors='ignore').strip()
        )
    except Exception as e:
        logger.error(f"Failed to run command {cmd}: {e}")
        return -1, "", str(e)

def calculate_progress(current: int, total: int) -> float:
    """Calculate progress percentage"""
    if total == 0:
        return 0.0
    return (current / total) * 100

def create_progress_bar(progress: float, length: int = 20) -> str:
    """Create text progress bar"""
    filled_length = int(length * progress / 100)
    bar = '█' * filled_length + '░' * (length - filled_length)
    return f"{bar} {progress:.1f}%"

def format_eta(seconds: int) -> str:
    """Format ETA in human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

def get_system_info() -> Dict[str, Any]:
    """Get system information"""
    import psutil
    import platform
    
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory
        memory = psutil.virtual_memory()
        memory_total = memory.total
        memory_used = memory.used
        memory_percent = memory.percent
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_total = disk.total
        disk_used = disk.used
        disk_percent = disk.percent
        
        # Network
        net_io = psutil.net_io_counters()
        bytes_sent = net_io.bytes_sent
        bytes_recv = net_io.bytes_recv
        
        # System
        system_info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
        }
        
        return {
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count,
            },
            'memory': {
                'total': memory_total,
                'used': memory_used,
                'percent': memory_percent,
            },
            'disk': {
                'total': disk_total,
                'used': disk_used,
                'percent': disk_percent,
            },
            'network': {
                'bytes_sent': bytes_sent,
                'bytes_recv': bytes_recv,
            },
            'system': system_info,
        }
    except Exception as e:
        logger.error(f"Failed to get system info: {e}")
        return {}

def cleanup_old_files(directory: str, max_age_hours: int = 24) -> int:
    """Cleanup old files in directory"""
    try:
        cleanup_time = datetime.now() - timedelta(hours=max_age_hours)
        deleted_count = 0
        
        for file_path in Path(directory).glob('*'):
            if file_path.is_file():
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cleanup_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except:
                        pass
        
        return deleted_count
    except Exception as e:
        logger.error(f"Failed to cleanup files: {e}")
        return 0

def calculate_audio_bitrate(file_size: int, duration: int) -> float:
    """Calculate audio bitrate in kbps"""
    if duration == 0:
        return 0.0
    # bitrate (kbps) = (file_size * 8) / (duration * 1000)
    return (file_size * 8) / (duration * 1000)

def normalize_volume_level(level: int) -> int:
    """Normalize volume level to 0-200 range"""
    return max(0, min(200, level))

def get_audio_duration(filepath: str) -> Optional[int]:
    """Get audio duration using mutagen"""
    try:
        from mutagen import File
        audio = File(filepath)
        if audio and audio.info:
            return int(audio.info.length)
    except:
        pass
    return None

def is_supported_audio_format(filename: str) -> bool:
    """Check if audio format is supported"""
    supported_formats = [
        '.mp3', '.m4a', '.ogg', '.opus', '.flac', '.wav',
        '.aac', '.wma', '.webm', '.mp4', '.m4v', '.mkv'
    ]
    return any(filename.lower().endswith(fmt) for fmt in supported_formats)

def get_youtube_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)',
        r'youtube\.com/embed/([\w-]+)',
        r'youtube\.com/v/([\w-]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_spotify_id(url: str) -> Optional[Tuple[str, str]]:
    """Extract Spotify ID and type from URL"""
    patterns = {
        'track': r'spotify\.com/track/([\w]+)',
        'album': r'spotify\.com/album/([\w]+)',
        'playlist': r'spotify\.com/playlist/([\w]+)',
        'artist': r'spotify\.com/artist/([\w]+)',
    }
    
    for type_name, pattern in patterns.items():
        match = re.search(pattern, url)
        if match:
            return type_name, match.group(1)
    
    return None

def create_temp_filename(prefix: str = "temp", extension: str = ".mp3") -> str:
    """Create temporary filename"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{prefix}_{timestamp}_{random_str}{extension}"

def safe_delete_file(filepath: str) -> bool:
    """Safely delete file"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except:
        pass
    return False

def get_mime_type(filename: str) -> str:
    """Get MIME type from filename"""
    extension = get_file_extension(filename).lower()
    
    mime_types = {
        '.mp3': 'audio/mpeg',
        '.m4a': 'audio/mp4',
        '.ogg': 'audio/ogg',
        '.opus': 'audio/opus',
        '.flac': 'audio/flac',
        '.wav': 'audio/wav',
        '.mp4': 'video/mp4',
        '.webm': 'video/webm',
    }
    
    return mime_types.get(extension, 'application/octet-stream')
