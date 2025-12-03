import asyncio
import logging
import hashlib
import time
from typing import Dict, List, Optional, Any
import pylast
import aiohttp
from datetime import datetime

from config import config
from utils.logger import logger
from utils.exceptions import LastFMError

class LastFMService:
    """Last.fm integration for scrobbling and music data"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Initialize pylast network
        self.network = pylast.LastFMNetwork(
            api_key=api_key,
            api_secret=api_secret,
        )
        
        # User sessions cache
        self.user_sessions: Dict[str, pylast.SessionKeyGenerator] = {}
        
        # Cache setup
        self.track_cache = cachetools.TTLCache(maxsize=500, ttl=1800)
        self.artist_cache = cachetools.TTLCache(maxsize=200, ttl=3600)
        self.album_cache = cachetools.TTLCache(maxsize=200, ttl=3600)
        
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
    
    async def get_user_session(self, username: str, password: str = None) -> Optional[str]:
        """Get session key for user"""
        cache_key = f"session:{username}"
        
        if cache_key in self.user_sessions:
            return self.user_sessions[cache_key].session_key
        
        try:
            if password:
                # Generate session key with password
                password_hash = pylast.md5(password)
                session_key = await self._get_mobile_session(username, password_hash)
            else:
                # Try to get existing session
                session_key = await self._get_web_session(username)
            
            if session_key:
                # Create session generator
                sg = pylast.SessionKeyGenerator(self.network)
                sg.session_key = session_key
                self.user_sessions[cache_key] = sg
            
            return session_key
            
        except Exception as e:
            logger.error(f"Failed to get user session: {e}")
            return None
    
    async def scrobble(self, track_name: str, artist: str, album: str = None, 
                      duration: int = None, user_id: int = None) -> bool:
        """Scrobble a track"""
        try:
            # Get timestamp (current time)
            timestamp = int(time.time())
            
            # Prepare track data
            track = self.network.get_track(artist, track_name)
            
            # Scrobble
            loop = asyncio.get_event_loop()
            
            def sync_scrobble():
                track.scrobble(
                    timestamp=timestamp,
                    album=album,
                    duration=duration,
                    album_artist=artist
                )
                return True
            
            await loop.run_in_executor(None, sync_scrobble)
            
            logger.info(f"Scrobbled: {artist} - {track_name}")
            return True
            
        except Exception as e:
            logger.error(f"Scrobble failed: {e}")
            return False
    
    async def update_now_playing(self, track_name: str, artist: str, 
                               album: str = None, duration: int = None) -> bool:
        """Update now playing status"""
        try:
            track = self.network.get_track(artist, track_name)
            
            loop = asyncio.get_event_loop()
            
            def sync_update():
                track.update_now_playing(
                    album=album,
                    duration=duration,
                    album_artist=artist
                )
                return True
            
            await loop.run_in_executor(None, sync_update)
            
            logger.debug(f"Now playing updated: {artist} - {track_name}")
            return True
            
        except Exception as e:
            logger.error(f"Now playing update failed: {e}")
            return False
    
    async def love_track(self, track_name: str, artist: str, user_session: str = None) -> bool:
        """Love a track"""
        try:
            track = self.network.get_track(artist, track_name)
            
            loop = asyncio.get_event_loop()
            
            def sync_love():
                if user_session:
                    track.love(session_key=user_session)
                else:
                    track.love()
                return True
            
            await loop.run_in_executor(None, sync_love)
            
            logger.debug(f"Loved track: {artist} - {track_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to love track: {e}")
            return False
    
    async def unlove_track(self, track_name: str, artist: str, user_session: str = None) -> bool:
        """Unlove a track"""
        try:
            track = self.network.get_track(artist, track_name)
            
            loop = asyncio.get_event_loop()
            
            def sync_unlove():
                if user_session:
                    track.unlove(session_key=user_session)
                else:
                    track.unlove()
                return True
            
            await loop.run_in_executor(None, sync_unlove)
            
            logger.debug(f"Unloved track: {artist} - {track_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unlove track: {e}")
            return False
    
    async def get_track_info(self, track_name: str, artist: str) -> Optional[Dict]:
        """Get track information"""
        cache_key = f"track_info:{artist}:{track_name}"
        
        if cache_key in self.track_cache:
            return self.track_cache[cache_key]
        
        try:
            track = self.network.get_track(artist, track_name)
            
            loop = asyncio.get_event_loop()
            
            def sync_get():
                track_info = track.get_info()
                
                # Get additional data
                playcount = track.get_playcount()
                listeners = track.get_listener_count()
                userplaycount = track.get_userplaycount() if hasattr(track, 'get_userplaycount') else 0
                
                # Get similar tracks
                similar_tracks = []
                try:
                    for similar in track.get_similar()[:5]:
                        similar_tracks.append({
                            'name': similar.item.name,
                            'artist': similar.item.artist.name,
                            'match': similar.match,
                        })
                except:
                    pass
                
                # Get tags
                tags = []
                try:
                    for tag in track.get_top_tags()[:5]:
                        tags.append({
                            'name': tag.item.get_name(),
                            'count': tag.count,
                        })
                except:
                    pass
                
                return {
                    'name': track_info.name,
                    'artist': track_info.artist.name,
                    'album': getattr(track_info, 'album', None),
                    'duration': getattr(track_info, 'duration', 0),
                    'playcount': playcount,
                    'listeners': listeners,
                    'userplaycount': userplaycount,
                    'url': track_info.get_url(),
                    'similar_tracks': similar_tracks,
                    'tags': tags,
                    'wiki': getattr(track_info, 'wiki', {}),
                }
            
            info = await loop.run_in_executor(None, sync_get)
            
            self.track_cache[cache_key] = info
            return info
            
        except Exception as e:
            logger.error(f"Failed to get track info: {e}")
            return None
    
    async def get_artist_info(self, artist_name: str) -> Optional[Dict]:
        """Get artist information"""
        cache_key = f"artist_info:{artist_name}"
        
        if cache_key in self.artist_cache:
            return self.artist_cache[cache_key]
        
        try:
            artist = self.network.get_artist(artist_name)
            
            loop = asyncio.get_event_loop()
            
            def sync_get():
                artist_info = artist.get_info()
                
                # Get stats
                playcount = artist.get_playcount()
                listeners = artist.get_listener_count()
                
                # Get similar artists
                similar_artists = []
                try:
                    for similar in artist.get_similar()[:5]:
                        similar_artists.append({
                            'name': similar.item.name,
                            'match': similar.match,
                        })
                except:
                    pass
                
                # Get top tracks
                top_tracks = []
                try:
                    for track in artist.get_top_tracks(limit=5):
                        top_tracks.append({
                            'name': track.item.name,
                            'playcount': track.weight,
                        })
                except:
                    pass
                
                # Get top albums
                top_albums = []
                try:
                    for album in artist.get_top_albums(limit=5):
                        top_albums.append({
                            'name': album.item.name,
                            'playcount': album.weight,
                        })
                except:
                    pass
                
                # Get tags
                tags = []
                try:
                    for tag in artist.get_top_tags()[:5]:
                        tags.append({
                            'name': tag.item.get_name(),
                            'count': tag.count,
                        })
                except:
                    pass
                
                return {
                    'name': artist_info.name,
                    'playcount': playcount,
                    'listeners': listeners,
                    'similar_artists': similar_artists,
                    'top_tracks': top_tracks,
                    'top_albums': top_albums,
                    'tags': tags,
                    'bio': getattr(artist_info, 'bio', {}),
                    'url': artist_info.get_url(),
                }
            
            info = await loop.run_in_executor(None, sync_get)
            
            self.artist_cache[cache_key] = info
            return info
            
        except Exception as e:
            logger.error(f"Failed to get artist info: {e}")
            return None
    
    async def get_album_info(self, album_name: str, artist_name: str) -> Optional[Dict]:
        """Get album information"""
        cache_key = f"album_info:{artist_name}:{album_name}"
        
        if cache_key in self.album_cache:
            return self.album_cache[cache_key]
        
        try:
            album = self.network.get_album(artist_name, album_name)
            
            loop = asyncio.get_event_loop()
            
            def sync_get():
                album_info = album.get_info()
                
                # Get stats
                playcount = album.get_playcount()
                listeners = album.get_listener_count()
                
                # Get tracks
                tracks = []
                try:
                    for track in album.get_tracks():
                        tracks.append({
                            'name': track.title,
                            'artist': track.artist.name,
                            'duration': track.duration,
                        })
                except:
                    pass
                
                # Get tags
                tags = []
                try:
                    for tag in album.get_top_tags()[:5]:
                        tags.append({
                            'name': tag.item.get_name(),
                            'count': tag.count,
                        })
                except:
                    pass
                
                return {
                    'name': album_info.name,
                    'artist': album_info.artist.name,
                    'playcount': playcount,
                    'listeners': listeners,
                    'tracks': tracks,
                    'tags': tags,
                    'wiki': getattr(album_info, 'wiki', {}),
                    'url': album_info.get_url(),
                }
            
            info = await loop.run_in_executor(None, sync_get)
            
            self.album_cache[cache_key] = info
            return info
            
        except Exception as e:
            logger.error(f"Failed to get album info: {e}")
            return None
    
    async def get_user_info(self, username: str) -> Optional[Dict]:
        """Get user information"""
        try:
            user = self.network.get_user(username)
            
            loop = asyncio.get_event_loop()
            
            def sync_get():
                user_info = user.get_info()
                
                # Get stats
                playcount = user.get_playcount()
                registered = user.get_registered()
                country = user.get_country()
                
                # Get recent tracks
                recent_tracks = []
                try:
                    for track in user.get_recent_tracks(limit=5):
                        recent_tracks.append({
                            'name': track.track.title,
                            'artist': track.track.artist.name,
                            'album': track.album,
                            'timestamp': track.timestamp,
                            'loved': track.loved,
                        })
                except:
                    pass
                
                # Get top artists
                top_artists = []
                try:
                    for artist in user.get_top_artists(period=pylast.PERIOD_7DAYS, limit=5):
                        top_artists.append({
                            'name': artist.item.name,
                            'playcount': artist.weight,
                        })
                except:
                    pass
                
                # Get top tracks
                top_tracks = []
                try:
                    for track in user.get_top_tracks(period=pylast.PERIOD_7DAYS, limit=5):
                        top_tracks.append({
                            'name': track.item.name,
                            'artist': track.item.artist.name,
                            'playcount': track.weight,
                        })
                except:
                    pass
                
                # Get top albums
                top_albums = []
                try:
                    for album in user.get_top_albums(period=pylast.PERIOD_7DAYS, limit=5):
                        top_albums.append({
                            'name': album.item.name,
                            'artist': album.item.artist.name,
                            'playcount': album.weight,
                        })
                except:
                    pass
                
                return {
                    'username': user_info.name,
                    'realname': getattr(user_info, 'realname', ''),
                    'playcount': playcount,
                    'registered': registered,
                    'country': country,
                    'recent_tracks': recent_tracks,
                    'top_artists': top_artists,
                    'top_tracks': top_tracks,
                    'top_albums': top_albums,
                    'url': user_info.get_url(),
                }
            
            return await loop.run_in_executor(None, sync_get)
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None
    
    async def get_user_weekly_chart(self, username: str) -> Dict:
        """Get user's weekly chart"""
        try:
            user = self.network.get_user(username)
            
            loop = asyncio.get_event_loop()
            
            def sync_get():
                # Get charts for different periods
                charts = {}
                
                for period_name, period in [
                    ('7days', pylast.PERIOD_7DAYS),
                    ('1month', pylast.PERIOD_1MONTH),
                    ('3months', pylast.PERIOD_3MONTHS),
                    ('6months', pylast.PERIOD_6MONTHS),
                    ('12months', pylast.PERIOD_12MONTHS),
                    ('overall', pylast.PERIOD_OVERALL),
                ]:
                    try:
                        # Top artists
                        top_artists = []
                        for artist in user.get_top_artists(period=period, limit=10):
                            top_artists.append({
                                'name': artist.item.name,
                                'playcount': artist.weight,
                            })
                        
                        # Top tracks
                        top_tracks = []
                        for track in user.get_top_tracks(period=period, limit=10):
                            top_tracks.append({
                                'name': track.item.name,
                                'artist': track.item.artist.name,
                                'playcount': track.weight,
                            })
                        
                        # Top albums
                        top_albums = []
                        for album in user.get_top_albums(period=period, limit=10):
                            top_albums.append({
                                'name': album.item.name,
                                'artist': album.item.artist.name,
                                'playcount': album.weight,
                            })
                        
                        charts[period_name] = {
                            'artists': top_artists,
                            'tracks': top_tracks,
                            'albums': top_albums,
                        }
                    except:
                        pass
                
                return charts
            
            return await loop.run_in_executor(None, sync_get)
            
        except Exception as e:
            logger.error(f"Failed to get weekly chart: {e}")
            return {}
    
    async def get_track_similar(self, track_name: str, artist: str, limit: int = 10) -> List[Dict]:
        """Get similar tracks"""
        try:
            track = self.network.get_track(artist, track_name)
            
            loop = asyncio.get_event_loop()
            
            def sync_get():
                similar = track.get_similar(limit=limit)
                tracks = []
                
                for item in similar:
                    tracks.append({
                        'name': item.item.name,
                        'artist': item.item.artist.name,
                        'match': item.match,
                        'url': item.item.get_url(),
                    })
                
                return tracks
            
            return await loop.run_in_executor(None, sync_get)
            
        except Exception as e:
            logger.error(f"Failed to get similar tracks: {e}")
            return []
    
    async def search_tracks(self, query: str, limit: int = 10) -> List[Dict]:
        """Search tracks on Last.fm"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_search():
                results = self.network.search_for_track(query, limit=limit)
                tracks = []
                
                for track in results:
                    tracks.append({
                        'name': track.name,
                        'artist': track.artist.name,
                        'listeners': track.listeners,
                        'url': track.get_url(),
                    })
                
                return tracks
            
            return await loop.run_in_executor(None, sync_search)
            
        except Exception as e:
            logger.error(f"Track search failed: {e}")
            return []
    
    async def search_artists(self, query: str, limit: int = 10) -> List[Dict]:
        """Search artists on Last.fm"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_search():
                results = self.network.search_for_artist(query, limit=limit)
                artists = []
                
                for artist in results:
                    artists.append({
                        'name': artist.name,
                        'listeners': artist.listeners,
                        'url': artist.get_url(),
                    })
                
                return artists
            
            return await loop.run_in_executor(None, sync_search)
            
        except Exception as e:
            logger.error(f"Artist search failed: {e}")
            return []
    
    async def search_albums(self, query: str, limit: int = 10) -> List[Dict]:
        """Search albums on Last.fm"""
        try:
            loop = asyncio.get_event_loop()
            
            def sync_search():
                results = self.network.search_for_album(query, limit=limit)
                albums = []
                
                for album in results:
                    albums.append({
                        'name': album.name,
                        'artist': album.artist.name,
                        'listeners': album.listeners,
                        'url': album.get_url(),
                    })
                
                return albums
            
            return await loop.run_in_executor(None, sync_search)
            
        except Exception as e:
            logger.error(f"Album search failed: {e}")
            return []
    
    async def _get_mobile_session(self, username: str, password_hash: str) -> Optional[str]:
        """Get mobile session key"""
        try:
            api_sig = hashlib.md5(
                f"api_key{self.api_key}methodauth.getMobileSessionpassword{password_hash}username{username}{self.api_secret}".encode()
            ).hexdigest()
            
            params = {
                'method': 'auth.getMobileSession',
                'username': username,
                'password': password_hash,
                'api_key': self.api_key,
                'api_sig': api_sig,
                'format': 'json',
            }
            
            async with self.session.post('https://ws.audioscrobbler.com/2.0/', data=params) as response:
                data = await response.json()
                if 'session' in data:
                    return data['session']['key']
            
            return None
            
        except Exception as e:
            logger.error(f"Mobile session failed: {e}")
            return None
    
    async def _get_web_session(self, username: str) -> Optional[str]:
        """Get web session key (for already authenticated users)"""
        # This would require storing user session keys in database
        # For now, return None and require password
        return None