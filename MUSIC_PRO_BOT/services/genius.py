import asyncio
import logging
import re
from typing import Dict, List, Optional, Any
import lyricsgenius
import aiohttp
from bs4 import BeautifulSoup
import cachetools

from config import config
from utils.logger import logger
from utils.exceptions import GeniusError

class GeniusService:
    """Genius lyrics service"""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        
        # Initialize Genius client
        self.genius = lyricsgenius.Genius(
            access_token,
            timeout=15,
            sleep_time=0.5,
            verbose=False,
            skip_non_songs=True,
            excluded_terms=["(Remix)", "(Live)", "(Demo)", "(Acoustic)"]
        )
        
        # Remove section headers (e.g., [Chorus]) by default
        self.genius.remove_section_headers = True
        
        # Cache setup
        self.lyrics_cache = cachetools.TTLCache(maxsize=500, ttl=86400)  # 24 hours
        self.search_cache = cachetools.TTLCache(maxsize=1000, ttl=1800)  # 30 minutes
        
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
    
    async def search_lyrics(self, query: str, get_full_lyrics: bool = True) -> Optional[Dict]:
        """Search for lyrics"""
        cache_key = f"search:{query}:{get_full_lyrics}"
        
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            
            def sync_search():
                # Search for song
                song = self.genius.search_song(query, get_full_info=get_full_lyrics)
                if not song:
                    return None
                
                return self._parse_song(song)
            
            result = await loop.run_in_executor(None, sync_search)
            
            if result:
                self.search_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Genius search error: {e}")
            raise GeniusError(f"Search failed: {str(e)}")
    
    async def get_lyrics_by_id(self, song_id: int) -> Optional[Dict]:
        """Get lyrics by Genius song ID"""
        cache_key = f"lyrics:{song_id}"
        
        if cache_key in self.lyrics_cache:
            return self.lyrics_cache[cache_key]
        
        try:
            if not self.session:
                await self.initialize()
            
            # Fetch song page
            url = f"https://genius.com/songs/{song_id}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    # Try alternative API
                    return await self._get_lyrics_via_api(song_id)
                
                html = await response.text()
                lyrics = await self._extract_lyrics_from_html(html)
                
                if lyrics:
                    result = {
                        'lyrics': lyrics,
                        'source': 'genius',
                        'url': url,
                    }
                    self.lyrics_cache[cache_key] = result
                    return result
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get lyrics by ID: {e}")
            return None
    
    async def get_lyrics_for_track(self, title: str, artist: str = "") -> Optional[Dict]:
        """Get lyrics for specific track"""
        cache_key = f"track:{title}:{artist}"
        
        if cache_key in self.lyrics_cache:
            return self.lyrics_cache[cache_key]
        
        try:
            query = f"{title} {artist}".strip()
            result = await self.search_lyrics(query, get_full_lyrics=True)
            
            if result:
                self.lyrics_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Failed to get lyrics for track: {e}")
            return None
    
    async def search_multiple(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for multiple songs"""
        cache_key = f"multi_search:{query}:{limit}"
        
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            
            def sync_search():
                results = self.genius.search_albums(query, per_page=limit)
                songs = []
                
                for hit in results['sections'][0]['hits']:
                    result = hit.get('result')
                    if result:
                        song_info = {
                            'id': result.get('id'),
                            'title': result.get('title'),
                            'artist': result.get('artist_names'),
                            'thumbnail': result.get('song_art_image_thumbnail_url'),
                            'url': result.get('url'),
                            'full_title': result.get('full_title'),
                        }
                        songs.append(song_info)
                
                return songs
            
            results = await loop.run_in_executor(None, sync_search)
            
            self.search_cache[cache_key] = results
            return results
            
        except Exception as e:
            logger.error(f"Multi-search error: {e}")
            return []
    
    async def get_artist_songs(self, artist_id: int, limit: int = 20) -> List[Dict]:
        """Get songs by artist"""
        try:
            if not self.session:
                await self.initialize()
            
            url = f"https://genius.com/api/artists/{artist_id}/songs"
            params = {
                'sort': 'title',
                'per_page': limit,
                'page': 1,
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                songs = []
                
                for song_data in data['response']['songs']:
                    song = {
                        'id': song_data.get('id'),
                        'title': song_data.get('title'),
                        'artist': song_data.get('artist_names'),
                        'url': song_data.get('url'),
                        'thumbnail': song_data.get('song_art_image_thumbnail_url'),
                        'lyrics_state': song_data.get('lyrics_state'),
                    }
                    songs.append(song)
                
                return songs
            
        except Exception as e:
            logger.error(f"Failed to get artist songs: {e}")
            return []
    
    async def get_album_lyrics(self, album_id: int) -> List[Dict]:
        """Get lyrics for all songs in album"""
        try:
            if not self.session:
                await self.initialize()
            
            url = f"https://genius.com/api/albums/{album_id}/tracks"
            params = {
                'per_page': 50,
                'page': 1,
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                tracks = []
                
                for track_data in data['response']['tracks']:
                    song = track_data.get('song')
                    if song:
                        track_info = {
                            'id': song.get('id'),
                            'title': song.get('title'),
                            'artist': song.get('artist_names'),
                            'track_number': track_data.get('number'),
                            'url': song.get('url'),
                        }
                        tracks.append(track_info)
                
                return tracks
            
        except Exception as e:
            logger.error(f"Failed to get album lyrics: {e}")
            return []
    
    async def _get_lyrics_via_api(self, song_id: int) -> Optional[Dict]:
        """Get lyrics via Genius API"""
        try:
            if not self.session:
                await self.initialize()
            
            url = f"https://genius.com/api/songs/{song_id}"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                data = await response.json()
                song_data = data['response']['song']
                
                # Try to get lyrics from description or via web scraping
                lyrics = await self._extract_lyrics(song_data)
                
                if lyrics:
                    return {
                        'id': song_id,
                        'title': song_data.get('title'),
                        'artist': song_data.get('artist_names'),
                        'lyrics': lyrics,
                        'url': song_data.get('url'),
                        'thumbnail': song_data.get('song_art_image_url'),
                        'source': 'genius',
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"API lyrics fetch failed: {e}")
            return None
    
    async def _extract_lyrics(self, song_data: Dict) -> Optional[str]:
        """Extract lyrics from song data"""
        try:
            # Try to get lyrics from description
            description = song_data.get('description', {})
            if isinstance(description, dict):
                dom = description.get('dom', {})
                if dom:
                    lyrics = await self._parse_dom_content(dom)
                    if lyrics:
                        return lyrics
            
            # Fallback: scrape from URL
            url = song_data.get('url')
            if url:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        return await self._extract_lyrics_from_html(html)
            
            return None
            
        except Exception as e:
            logger.error(f"Lyrics extraction failed: {e}")
            return None
    
    async def _extract_lyrics_from_html(self, html: str) -> Optional[str]:
        """Extract lyrics from HTML page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find lyrics container (common Genius structure)
            lyrics_div = soup.find('div', {'data-lyrics-container': 'true'})
            if not lyrics_div:
                # Try alternative selectors
                lyrics_div = soup.find('div', class_=re.compile(r'lyrics$'))
                if not lyrics_div:
                    lyrics_div = soup.find('div', class_=re.compile(r'Lyrics__Container'))
            
            if lyrics_div:
                # Clean up lyrics
                lyrics = lyrics_div.get_text(separator='\n')
                
                # Remove empty lines and extra whitespace
                lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
                lyrics = '\n'.join(lines)
                
                # Remove ads and other non-lyric content
                lyrics = re.sub(r'\[.*?\]', '', lyrics)  # Remove brackets
                lyrics = re.sub(r'\(.*?\)', '', lyrics)  # Remove parentheses
                lyrics = re.sub(r'\s+', ' ', lyrics)    # Normalize whitespace
                
                return lyrics.strip()
            
            return None
            
        except Exception as e:
            logger.error(f"HTML lyrics extraction failed: {e}")
            return None
    
    async def _parse_dom_content(self, dom: Dict) -> Optional[str]:
        """Parse DOM content from Genius API"""
        try:
            def parse_node(node):
                if isinstance(node, dict):
                    tag = node.get('tag')
                    children = node.get('children', [])
                    
                    if tag == 'p':
                        # Paragraph - add newline
                        content = ''.join(parse_node(child) for child in children)
                        return content + '\n\n'
                    elif tag == 'br':
                        # Line break
                        return '\n'
                    elif tag in ['i', 'em', 'b', 'strong']:
                        # Formatting tags - ignore for lyrics
                        return ''.join(parse_node(child) for child in children)
                    elif tag == 'a':
                        # Links - just get text
                        return ''.join(parse_node(child) for child in children)
                    else:
                        # Other tags
                        return ''.join(parse_node(child) for child in children)
                elif isinstance(node, str):
                    return node
                else:
                    return ''
            
            content = parse_node(dom)
            
            # Clean up
            content = re.sub(r'\n\s*\n', '\n\n', content)  # Remove extra blank lines
            content = content.strip()
            
            return content if content else None
            
        except Exception as e:
            logger.error(f"DOM parsing failed: {e}")
            return None
    
    def _parse_song(self, song) -> Dict:
        """Parse lyricsgenius song object"""
        if not song:
            return None
        
        # Clean lyrics
        lyrics = song.lyrics
        
        # Remove section headers if present
        if self.genius.remove_section_headers:
            lyrics = re.sub(r'\[.*?\]\n?', '', lyrics)
        
        # Remove "Embed" text at the end
        lyrics = re.sub(r'\d*Embed$', '', lyrics, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        lyrics = re.sub(r'\n\s*\n', '\n\n', lyrics)
        lyrics = lyrics.strip()
        
        return {
            'id': song.id,
            'title': song.title,
            'artist': song.artist,
            'album': getattr(song, 'album', None),
            'year': getattr(song, 'year', None),
            'lyrics': lyrics,
            'url': song.url,
            'thumbnail': song.song_art_image_url,
            'source': 'genius',
            'lyrics_length': len(lyrics),
        }
    
    def format_lyrics(self, lyrics: str, max_length: int = 4000) -> str:
        """Format lyrics for Telegram message"""
        if not lyrics:
            return ""
        
        # Truncate if too long
        if len(lyrics) > max_length:
            lyrics = lyrics[:max_length] + "...\n\n📖 **Lyrics truncated due to length**"
        
        return lyrics
    
    async def get_lyrics_preview(self, query: str, preview_lines: int = 10) -> Optional[str]:
        """Get lyrics preview (first few lines)"""
        try:
            result = await self.search_lyrics(query, get_full_lyrics=False)
            if not result or not result.get('lyrics'):
                return None
            
            lyrics = result['lyrics']
            lines = lyrics.split('\n')[:preview_lines]
            preview = '\n'.join(lines)
            
            if len(lyrics.split('\n')) > preview_lines:
                preview += "\n...\n📖 **Full lyrics available with /lyrics command**"
            
            return preview
            
        except Exception as e:
            logger.error(f"Failed to get lyrics preview: {e}")
            return None
