import asyncio
import logging
from typing import Dict, List, Optional, Any
import yt_dlp
import aiohttp
import json
from urllib.parse import quote
import cachetools

from config import config
from utils.logger import logger
from utils.exceptions import YouTubeError

class YouTubeService:
    """YouTube service with API and yt-dlp fallback"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
        # Cache setup
        self.search_cache = cachetools.TTLCache(maxsize=500, ttl=300)
        self.video_cache = cachetools.TTLCache(maxsize=200, ttl=1800)
        self.stream_cache = cachetools.TTLCache(maxsize=100, ttl=600)
        
        # yt-dlp options
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_ipv4': True,
            'socket_timeout': 30,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],
                    'player_skip': ['configs', 'webpage'],
                }
            },
            'postprocessor_args': {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            },
        }
        
        # HTTP session
        self.session = None
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def initialize(self):
        """Initialize HTTP session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search YouTube videos"""
        cache_key = f"search:{query}:{limit}"
        
        # Check cache first
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        try:
            # Try YouTube API first
            if self.api_key:
                results = await self._search_with_api(query, limit)
            else:
                results = await self._search_without_api(query, limit)
            
            # Cache results
            self.search_cache[cache_key] = results
            return results
            
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
            raise YouTubeError(f"Search failed: {str(e)}")
    
    async def _search_with_api(self, query: str, limit: int) -> List[Dict]:
        """Search using YouTube Data API"""
        if not self.session:
            await self.initialize()
        
        url = f"{self.base_url}/search"
        params = {
            "part": "snippet",
            "q": query,
            "maxResults": limit,
            "key": self.api_key,
            "type": "video",
            "videoCategoryId": "10",  # Music category
            "relevanceLanguage": "en",
            "safeSearch": "none",
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    text = await response.text()
                    raise YouTubeError(f"API error {response.status}: {text}")
                
                data = await response.json()
                
                videos = []
                for item in data.get("items", []):
                    video_id = item["id"]["videoId"]
                    
                    # Get video details including duration
                    details = await self.get_video_details(video_id)
                    
                    video = {
                        "id": video_id,
                        "title": item["snippet"]["title"],
                        "url": f"https://youtube.com/watch?v={video_id}",
                        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                        "channel": item["snippet"]["channelTitle"],
                        "duration": details.get("duration", 0),
                        "views": details.get("views", 0),
                        "description": item["snippet"]["description"][:200],
                        "published_at": item["snippet"]["publishedAt"],
                        "source": "youtube",
                    }
                    videos.append(video)
                
                return videos
                
        except Exception as e:
            logger.error(f"YouTube API search error: {e}")
            # Fallback to non-API method
            return await self._search_without_api(query, limit)
    
    async def _search_without_api(self, query: str, limit: int) -> List[Dict]:
        """Search using yt-dlp (fallback)"""
        try:
            ydl_opts = {
                **self.ydl_opts,
                'extract_flat': True,
                'default_search': f'ytsearch{limit}:',
                'force_generic_extractor': True,
            }
            
            loop = asyncio.get_event_loop()
            
            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(query, download=False)
            
            info = await loop.run_in_executor(None, extract)
            
            videos = []
            for entry in info.get('entries', []):
                if not entry:
                    continue
                
                video = {
                    "id": entry.get('id'),
                    "title": entry.get('title', 'Unknown'),
                    "url": entry.get('url') or f"https://youtube.com/watch?v={entry.get('id')}",
                    "thumbnail": entry.get('thumbnail'),
                    "channel": entry.get('uploader', 'Unknown'),
                    "duration": entry.get('duration', 0),
                    "views": entry.get('view_count', 0),
                    "description": entry.get('description', '')[:200],
                    "source": "youtube",
                }
                videos.append(video)
            
            return videos
            
        except Exception as e:
            logger.error(f"yt-dlp search error: {e}")
            raise YouTubeError(f"Search failed: {str(e)}")
    
    async def get_video_info(self, url: str) -> Dict:
        """Get video information"""
        cache_key = f"video_info:{url}"
        
        if cache_key in self.video_cache:
            return self.video_cache[cache_key]
        
        try:
            ydl_opts = {
                **self.ydl_opts,
                'extract_flat': False,
            }
            
            loop = asyncio.get_event_loop()
            
            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await loop.run_in_executor(None, extract)
            
            video_info = {
                "id": info.get('id'),
                "title": info.get('title', 'Unknown'),
                "url": url,
                "thumbnail": info.get('thumbnail'),
                "channel": info.get('uploader', 'Unknown'),
                "duration": info.get('duration', 0),
                "views": info.get('view_count', 0),
                "description": info.get('description', '')[:200],
                "categories": info.get('categories', []),
                "tags": info.get('tags', []),
                "like_count": info.get('like_count', 0),
                "source": "youtube",
            }
            
            self.video_cache[cache_key] = video_info
            return video_info
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise YouTubeError(f"Failed to get video info: {str(e)}")
    
    async def get_stream_url(self, url: str) -> str:
        """Get direct audio stream URL"""
        cache_key = f"stream:{url}"
        
        if cache_key in self.stream_cache:
            return self.stream_cache[cache_key]
        
        try:
            ydl_opts = {
                **self.ydl_opts,
                'format': 'bestaudio[ext=webm]/bestaudio',
                'outtmpl': '%(id)s.%(ext)s',
            }
            
            loop = asyncio.get_event_loop()
            
            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                    # Get the best audio format
                    formats = info.get('formats', [])
                    audio_formats = [
                        f for f in formats 
                        if f.get('acodec') != 'none' and f.get('vcodec') == 'none'
                    ]
                    
                    if audio_formats:
                        # Sort by bitrate/quality
                        audio_formats.sort(
                            key=lambda x: (
                                x.get('abr', 0) if x.get('abr') else 0,
                                x.get('asr', 0) if x.get('asr') else 0
                            ),
                            reverse=True
                        )
                        stream_url = audio_formats[0]['url']
                    else:
                        # Fallback to any format with audio
                        for f in formats:
                            if f.get('acodec') != 'none':
                                stream_url = f['url']
                                break
                        else:
                            raise YouTubeError("No audio format found")
                    
                    return stream_url
            
            stream_url = await loop.run_in_executor(None, extract)
            
            self.stream_cache[cache_key] = stream_url
            return stream_url
            
        except Exception as e:
            logger.error(f"Failed to get stream URL: {e}")
            raise YouTubeError(f"Failed to get audio stream: {str(e)}")
    
    async def get_playlist(self, playlist_url: str) -> List[Dict]:
        """Extract all videos from a playlist"""
        try:
            ydl_opts = {
                **self.ydl_opts,
                'extract_flat': True,
                'playlist_items': '1-100',
                'ignoreerrors': True,
            }
            
            loop = asyncio.get_event_loop()
            
            def extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(playlist_url, download=False)
            
            info = await loop.run_in_executor(None, extract)
            
            videos = []
            for entry in info.get('entries', []):
                if not entry:
                    continue
                
                video = {
                    "id": entry.get('id'),
                    "title": entry.get('title', 'Unknown'),
                    "url": entry.get('url') or f"https://youtube.com/watch?v={entry.get('id')}",
                    "duration": entry.get('duration', 0),
                    "channel": entry.get('uploader', 'Unknown'),
                    "thumbnail": entry.get('thumbnail'),
                    "source": "youtube",
                }
                videos.append(video)
            
            return videos
            
        except Exception as e:
            logger.error(f"Failed to get playlist: {e}")
            raise YouTubeError(f"Failed to get playlist: {str(e)}")
    
    async def get_video_details(self, video_id: str) -> Dict:
        """Get video details using API"""
        if not self.api_key:
            return {"duration": 0, "views": 0}
        
        cache_key = f"details:{video_id}"
        
        if cache_key in self.video_cache:
            return self.video_cache[cache_key]
        
        if not self.session:
            await self.initialize()
        
        url = f"{self.base_url}/videos"
        params = {
            "part": "contentDetails,statistics",
            "id": video_id,
            "key": self.api_key,
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return {"duration": 0, "views": 0}
                
                data = await response.json()
                
                if not data.get("items"):
                    return {"duration": 0, "views": 0}
                
                item = data["items"][0]
                duration_str = item["contentDetails"]["duration"]
                duration = self._parse_duration(duration_str)
                
                details = {
                    "duration": duration,
                    "views": int(item["statistics"].get("viewCount", 0)),
                    "likes": int(item["statistics"].get("likeCount", 0)),
                    "comments": int(item["statistics"].get("commentCount", 0)),
                }
                
                self.video_cache[cache_key] = details
                return details
                
        except Exception as e:
            logger.error(f"Failed to get video details: {e}")
            return {"duration": 0, "views": 0}
    
    def _parse_duration(self, duration_str: str) -> int:
        """Parse ISO 8601 duration to seconds"""
        import re
        
        pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
        match = pattern.match(duration_str)
        
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return 0
    
    async def get_trending(self, category: str = "music") -> List[Dict]:
        """Get trending videos"""
        if not self.api_key:
            return []
        
        if not self.session:
            await self.initialize()
        
        url = f"{self.base_url}/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "chart": "mostPopular",
            "videoCategoryId": "10",  # Music
            "regionCode": "IN",
            "maxResults": 20,
            "key": self.api_key,
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                videos = []
                for item in data.get("items", []):
                    video = {
                        "id": item["id"],
                        "title": item["snippet"]["title"],
                        "url": f"https://youtube.com/watch?v={item['id']}",
                        "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                        "channel": item["snippet"]["channelTitle"],
                        "duration": self._parse_duration(item["contentDetails"]["duration"]),
                        "views": int(item["statistics"].get("viewCount", 0)),
                        "likes": int(item["statistics"].get("likeCount", 0)),
                        "source": "youtube",
                    }
                    videos.append(video)
                
                return videos
                
        except Exception as e:
            logger.error(f"Failed to get trending: {e}")
            return []
