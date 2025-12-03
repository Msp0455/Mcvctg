import aiohttp
import asyncio
from typing import List, Dict

class YouTubeManager:
    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        """Search YouTube videos"""
        if not self.api_key:
            # Fallback to web scraping
            return await self._search_without_api(query, limit)
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/search"
                params = {
                    "part": "snippet",
                    "q": query,
                    "maxResults": limit,
                    "key": self.api_key,
                    "type": "video"
                }
                
                async with session.get(url, params=params) as response:
                    data = await response.json()
                    
                    videos = []
                    for item in data.get("items", []):
                        video = {
                            "id": item["id"]["videoId"],
                            "title": item["snippet"]["title"],
                            "url": f"https://youtube.com/watch?v={item['id']['videoId']}",
                            "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                            "channel": item["snippet"]["channelTitle"],
                            "duration": "N/A"  # Need another API call for duration
                        }
                        videos.append(video)
                    
                    return videos
                    
        except Exception as e:
            print(f"YouTube API error: {e}")
            return await self._search_without_api(query, limit)
    
    async def _search_without_api(self, query: str, limit: int = 5) -> List[Dict]:
        """Search without API (fallback)"""
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'default_search': 'ytsearch',
            'force_generic_extractor': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
                
                videos = []
                for entry in info.get('entries', []):
                    video = {
                        "id": entry.get('id'),
                        "title": entry.get('title', 'Unknown'),
                        "url": entry.get('url'),
                        "thumbnail": entry.get('thumbnail'),
                        "channel": entry.get('uploader', 'Unknown'),
                        "duration": self._format_duration(entry.get('duration', 0))
                    }
                    videos.append(video)
                
                return videos
        except Exception as e:
            print(f"Fallback search error: {e}")
            return []
    
    def _format_duration(self, seconds: int) -> str:
        """Format duration in seconds to HH:MM:SS"""
        if not seconds:
            return "N/A"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
