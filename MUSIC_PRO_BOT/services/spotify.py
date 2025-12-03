import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import aiohttp
from urllib.parse import urlparse, parse_qs
import cachetools

from config import config
from utils.logger import logger
from utils.exceptions import SpotifyError

class SpotifyService:
    """Spotify integration service"""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        
        # Initialize Spotipy clients
        self.client_credentials = SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        )
        self.sp = spotipy.Spotify(auth_manager=self.client_credentials)
        
        # Cache setup
        self.track_cache = cachetools.TTLCache(maxsize=500, ttl=3600)
        self.album_cache = cachetools.TTLCache(maxsize=200, ttl=1800)
        self.playlist_cache = cachetools.TTLCache(maxsize=100, ttl=3600)
        self.search_cache = cachetools.TTLCache(maxsize=1000, ttl=300)
        
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
    
    async def search_tracks(self, query: str, limit: int = 10) -> List[Dict]:
        """Search tracks on Spotify"""
        cache_key = f"search_tracks:{query}:{limit}"
        
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            
            def sync_search():
                results = self.sp.search(q=query, type='track', limit=limit)
                tracks = []
                for item in results['tracks']['items']:
                    tracks.append(self._parse_track(item))
                return tracks
            
            tracks = await loop.run_in_executor(None, sync_search)
            
            self.search_cache[cache_key] = tracks
            return tracks
            
        except Exception as e:
            logger.error(f"Spotify search error: {e}")
            raise SpotifyError(f"Search failed: {str(e)}")
    
    async def search_playlists(self, query: str, limit: int = 10) -> List[Dict]:
        """Search playlists on Spotify"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_search():
                results = self.sp.search(q=query, type='playlist', limit=limit)
                playlists = []
                for item in results['playlists']['items']:
                    playlists.append(self._parse_playlist(item))
                return playlists
            
            return await loop.run_in_executor(None, sync_search)
            
        except Exception as e:
            logger.error(f"Playlist search error: {e}")
            raise SpotifyError(f"Playlist search failed: {str(e)}")
    
    async def search_albums(self, query: str, limit: int = 10) -> List[Dict]:
        """Search albums on Spotify"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_search():
                results = self.sp.search(q=query, type='album', limit=limit)
                albums = []
                for item in results['albums']['items']:
                    albums.append(self._parse_album(item))
                return albums
            
            return await loop.run_in_executor(None, sync_search)
            
        except Exception as e:
            logger.error(f"Album search error: {e}")
            raise SpotifyError(f"Album search failed: {str(e)}")
    
    async def search_artists(self, query: str, limit: int = 10) -> List[Dict]:
        """Search artists on Spotify"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_search():
                results = self.sp.search(q=query, type='artist', limit=limit)
                artists = []
                for item in results['artists']['items']:
                    artists.append(self._parse_artist(item))
                return artists
            
            return await loop.run_in_executor(None, sync_search)
            
        except Exception as e:
            logger.error(f"Artist search error: {e}")
            raise SpotifyError(f"Artist search failed: {str(e)}")
    
    async def get_track(self, track_id: str) -> Optional[Dict]:
        """Get track by ID"""
        cache_key = f"track:{track_id}"
        
        if cache_key in self.track_cache:
            return self.track_cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            
            def sync_get():
                track = self.sp.track(track_id)
                return self._parse_track(track)
            
            track_info = await loop.run_in_executor(None, sync_get)
            
            self.track_cache[cache_key] = track_info
            return track_info
            
        except Exception as e:
            logger.error(f"Failed to get track: {e}")
            return None
    
    async def get_album(self, album_id: str) -> Tuple[Optional[Dict], List[Dict]]:
        """Get album and its tracks"""
        cache_key = f"album:{album_id}"
        
        if cache_key in self.album_cache:
            return self.album_cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            
            def sync_get():
                album = self.sp.album(album_id)
                album_tracks = self.sp.album_tracks(album_id)
                
                # Parse album info
                album_info = self._parse_album(album)
                
                # Parse tracks
                tracks = []
                for item in album_tracks['items']:
                    track = self._parse_track(item, album_info=album_info)
                    tracks.append(track)
                
                return album_info, tracks
            
            result = await loop.run_in_executor(None, sync_get)
            
            self.album_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Failed to get album: {e}")
            return None, []
    
    async def get_playlist(self, playlist_id: str) -> Tuple[Optional[Dict], List[Dict]]:
        """Get playlist and its tracks"""
        cache_key = f"playlist:{playlist_id}"
        
        if cache_key in self.playlist_cache:
            return self.playlist_cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            
            def sync_get():
                playlist = self.sp.playlist(playlist_id)
                
                # Parse playlist info
                playlist_info = self._parse_playlist(playlist)
                
                # Get all tracks (handle pagination)
                tracks = []
                results = playlist['tracks']
                
                for item in results['items']:
                    if item['track']:
                        track = self._parse_track(item['track'])
                        tracks.append(track)
                
                # Get remaining tracks if any
                while results['next']:
                    results = self.sp.next(results)
                    for item in results['items']:
                        if item['track']:
                            track = self._parse_track(item['track'])
                            tracks.append(track)
                
                return playlist_info, tracks
            
            result = await loop.run_in_executor(None, sync_get)
            
            self.playlist_cache[cache_key] = result
            return result
            
        except Exception as e:
            logger.error(f"Failed to get playlist: {e}")
            return None, []
    
    async def get_artist_top_tracks(self, artist_id: str, country: str = "US") -> List[Dict]:
        """Get artist's top tracks"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_get():
                results = self.sp.artist_top_tracks(artist_id, country=country)
                tracks = []
                for item in results['tracks']:
                    tracks.append(self._parse_track(item))
                return tracks
            
            return await loop.run_in_executor(None, sync_get)
            
        except Exception as e:
            logger.error(f"Failed to get artist top tracks: {e}")
            return []
    
    async def get_artist_albums(self, artist_id: str, limit: int = 20) -> List[Dict]:
        """Get artist's albums"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_get():
                results = self.sp.artist_albums(artist_id, limit=limit)
                albums = []
                for item in results['items']:
                    albums.append(self._parse_album(item))
                return albums
            
            return await loop.run_in_executor(None, sync_get)
            
        except Exception as e:
            logger.error(f"Failed to get artist albums: {e}")
            return []
    
    async def get_track_from_url(self, url: str) -> Optional[Dict]:
        """Extract track info from Spotify URL"""
        try:
            # Parse URL to get track ID
            parsed = urlparse(url)
            
            if 'spotify.com/track/' in url:
                # Track URL
                track_id = parsed.path.split('/')[-1].split('?')[0]
                return await self.get_track(track_id)
            
            elif 'spotify.com/album/' in url:
                # Album URL - get first track
                album_id = parsed.path.split('/')[-1].split('?')[0]
                album_info, tracks = await self.get_album(album_id)
                if tracks:
                    return tracks[0]
            
            elif 'spotify.com/playlist/' in url:
                # Playlist URL - get first track
                playlist_id = parsed.path.split('/')[-1].split('?')[0]
                playlist_info, tracks = await self.get_playlist(playlist_id)
                if tracks:
                    return tracks[0]
            
            elif 'spotify.com/artist/' in url:
                # Artist URL - get top track
                artist_id = parsed.path.split('/')[-1].split('?')[0]
                top_tracks = await self.get_artist_top_tracks(artist_id)
                if top_tracks:
                    return top_tracks[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get track from URL: {e}")
            return None
    
    async def get_recommendations(self, seed_tracks: List[str] = None, 
                                 seed_artists: List[str] = None,
                                 seed_genres: List[str] = None,
                                 limit: int = 20) -> List[Dict]:
        """Get track recommendations"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_get():
                recommendations = self.sp.recommendations(
                    seed_tracks=seed_tracks or [],
                    seed_artists=seed_artists or [],
                    seed_genres=seed_genres or [],
                    limit=limit,
                    country='IN'
                )
                
                tracks = []
                for item in recommendations['tracks']:
                    tracks.append(self._parse_track(item))
                return tracks
            
            return await loop.run_in_executor(None, sync_get)
            
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []
    
    async def get_category_playlists(self, category_id: str = "toplists", 
                                    country: str = "IN", limit: int = 20) -> List[Dict]:
        """Get playlists from category"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_get():
                playlists = self.sp.category_playlists(
                    category_id=category_id,
                    country=country,
                    limit=limit
                )
                
                result = []
                for item in playlists['playlists']['items']:
                    result.append(self._parse_playlist(item))
                return result
            
            return await loop.run_in_executor(None, sync_get)
            
        except Exception as e:
            logger.error(f"Failed to get category playlists: {e}")
            return []
    
    async def get_new_releases(self, country: str = "IN", limit: int = 20) -> List[Dict]:
        """Get new releases"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_get():
                new_releases = self.sp.new_releases(
                    country=country,
                    limit=limit
                )
                
                albums = []
                for item in new_releases['albums']['items']:
                    albums.append(self._parse_album(item))
                return albums
            
            return await loop.run_in_executor(None, sync_get)
            
        except Exception as e:
            logger.error(f"Failed to get new releases: {e}")
            return []
    
    def _parse_track(self, track_data: Dict, album_info: Dict = None) -> Dict:
        """Parse Spotify track data"""
        # Get album info if not provided
        if not album_info and track_data.get('album'):
            album_info = self._parse_album(track_data['album'])
        
        # Get artists
        artists = []
        artist_names = []
        for artist in track_data.get('artists', []):
            artists.append({
                'id': artist.get('id'),
                'name': artist.get('name'),
                'url': artist.get('external_urls', {}).get('spotify'),
            })
            artist_names.append(artist.get('name'))
        
        # Get album images
        images = []
        if track_data.get('album') and track_data['album'].get('images'):
            images = track_data['album']['images']
        
        # Get preview URL
        preview_url = track_data.get('preview_url')
        
        # Calculate duration in seconds
        duration_ms = track_data.get('duration_ms', 0)
        duration = duration_ms // 1000
        
        return {
            'id': track_data.get('id'),
            'name': track_data.get('name'),
            'artists': ', '.join(artist_names),
            'artist_list': artists,
            'album': track_data.get('album', {}).get('name', 'Unknown'),
            'album_id': track_data.get('album', {}).get('id'),
            'duration_ms': duration_ms,
            'duration': duration,
            'popularity': track_data.get('popularity', 0),
            'track_number': track_data.get('track_number', 0),
            'disc_number': track_data.get('disc_number', 1),
            'explicit': track_data.get('explicit', False),
            'preview_url': preview_url,
            'spotify_url': track_data.get('external_urls', {}).get('spotify'),
            'images': images,
            'thumbnail': images[0]['url'] if images else None,
            'source': 'spotify',
            'url': track_data.get('external_urls', {}).get('spotify'),
        }
    
    def _parse_album(self, album_data: Dict) -> Dict:
        """Parse Spotify album data"""
        # Get artists
        artists = []
        artist_names = []
        for artist in album_data.get('artists', []):
            artists.append({
                'id': artist.get('id'),
                'name': artist.get('name'),
                'url': artist.get('external_urls', {}).get('spotify'),
            })
            artist_names.append(artist.get('name'))
        
        # Get images
        images = album_data.get('images', [])
        
        # Get release date
        release_date = album_data.get('release_date', '')
        release_date_precision = album_data.get('release_date_precision', 'day')
        
        # Parse release date
        if release_date_precision == 'day' and len(release_date) >= 10:
            year = release_date[:4]
        elif release_date_precision == 'month' and len(release_date) >= 7:
            year = release_date[:4]
        elif release_date_precision == 'year' and len(release_date) >= 4:
            year = release_date[:4]
        else:
            year = 'Unknown'
        
        return {
            'id': album_data.get('id'),
            'name': album_data.get('name'),
            'artists': ', '.join(artist_names),
            'artist_list': artists,
            'release_date': release_date,
            'year': year,
            'total_tracks': album_data.get('total_tracks', 0),
            'type': album_data.get('album_type'),
            'images': images,
            'thumbnail': images[0]['url'] if images else None,
            'spotify_url': album_data.get('external_urls', {}).get('spotify'),
            'source': 'spotify',
        }
    
    def _parse_playlist(self, playlist_data: Dict) -> Dict:
        """Parse Spotify playlist data"""
        # Get owner info
        owner = playlist_data.get('owner', {})
        
        # Get images
        images = playlist_data.get('images', [])
        
        # Get tracks info
        tracks_info = playlist_data.get('tracks', {})
        
        return {
            'id': playlist_data.get('id'),
            'name': playlist_data.get('name'),
            'description': playlist_data.get('description', ''),
            'owner': owner.get('display_name', 'Unknown'),
            'owner_id': owner.get('id'),
            'total_tracks': tracks_info.get('total', 0),
            'public': playlist_data.get('public', False),
            'collaborative': playlist_data.get('collaborative', False),
            'images': images,
            'thumbnail': images[0]['url'] if images else None,
            'spotify_url': playlist_data.get('external_urls', {}).get('spotify'),
            'source': 'spotify',
        }
    
    def _parse_artist(self, artist_data: Dict) -> Dict:
        """Parse Spotify artist data"""
        # Get images
        images = artist_data.get('images', [])
        
        # Get genres
        genres = artist_data.get('genres', [])
        
        # Get popularity
        popularity = artist_data.get('popularity', 0)
        
        # Get followers
        followers = artist_data.get('followers', {}).get('total', 0)
        
        return {
            'id': artist_data.get('id'),
            'name': artist_data.get('name'),
            'genres': genres,
            'popularity': popularity,
            'followers': followers,
            'images': images,
            'thumbnail': images[0]['url'] if images else None,
            'spotify_url': artist_data.get('external_urls', {}).get('spotify'),
            'source': 'spotify',
        }
    
    def ms_to_time(self, milliseconds: int) -> str:
        """Convert milliseconds to MM:SS format"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
