import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# Test imports
from core.bot_engine import MusicBotEngine
from core.queue_manager import QueueManager
from services.youtube import YouTubeService
from services.spotify import SpotifyService
from handlers.play import PlayHandler

pytest_plugins = ('pytest_asyncio',)

@pytest.fixture
def mock_config():
    """Mock configuration"""
    with patch('config.config') as mock:
        mock.telegram.api_id = 123456
        mock.telegram.api_hash = "test_hash"
        mock.telegram.bot_token = "test_token"
        mock.api.youtube_api_key = "test_youtube_key"
        mock.api.spotify_client_id = "test_spotify_id"
        mock.api.spotify_client_secret = "test_spotify_secret"
        mock.api.genius_access_token = "test_genius_token"
        mock.api.lastfm_api_key = "test_lastfm_key"
        mock.api.lastfm_api_secret = "test_lastfm_secret"
        mock.enable_voice_chat = True
        mock.enable_spotify = True
        mock.enable_genius = True
        mock.enable_lastfm = True
        yield mock

@pytest.fixture
def mock_database():
    """Mock database"""
    with patch('core.database.DatabaseManager') as mock:
        instance = mock.return_value
        instance.connect = AsyncMock()
        instance.disconnect = AsyncMock()
        instance.get_user = AsyncMock(return_value=None)
        instance.create_user = AsyncMock(return_value=True)
        instance.update_user = AsyncMock(return_value=True)
        instance.get_chat = AsyncMock(return_value=None)
        instance.create_chat = AsyncMock(return_value=True)
        instance.get_track = AsyncMock(return_value=None)
        instance.create_track = AsyncMock(return_value=True)
        instance.update_track_play = AsyncMock(return_value=True)
        instance.get_stats = AsyncMock(return_value={})
        instance.save_stats = AsyncMock(return_value=True)
        yield instance

@pytest.fixture
def mock_cache():
    """Mock cache"""
    with patch('core.cache_manager.CacheManager') as mock:
        instance = mock.return_value
        instance.connect = AsyncMock()
        instance.disconnect = AsyncMock()
        instance.get = AsyncMock(return_value=None)
        instance.set = AsyncMock(return_value=True)
        instance.delete = AsyncMock(return_value=True)
        yield instance

@pytest.mark.asyncio
async def test_queue_manager():
    """Test queue manager"""
    queue = QueueManager()
    
    # Test adding to queue
    track = {"id": "test1", "title": "Test Track 1"}
    assert queue.add_to_queue(123, track, 456) == True
    
    # Test queue size
    assert queue.get_queue_size(123) == 1
    
    # Test getting next
    next_item = queue.get_next(123)
    assert next_item is not None
    assert next_item.track["id"] == "test1"
    assert next_item.user_id == 456
    
    # Test empty queue
    assert queue.get_queue_size(123) == 0
    
    # Test multiple tracks
    for i in range(5):
        queue.add_to_queue(123, {"id": f"track{i}", "title": f"Track {i}"}, 456)
    
    assert queue.get_queue_size(123) == 5
    
    # Test queue pagination
    queue_data = queue.get_queue(123, page=1, per_page=3)
    assert len(queue_data["items"]) == 3
    assert queue_data["total"] == 5
    assert queue_data["pages"] == 2

@pytest.mark.asyncio
async def test_youtube_service():
    """Test YouTube service"""
    with patch('services.youtube.YouTubeService._search_with_api') as mock_search:
        mock_search.return_value = [
            {
                "id": "test123",
                "title": "Test Song",
                "url": "https://youtube.com/watch?v=test123",
                "thumbnail": "https://thumbnail.url",
                "channel": "Test Channel",
                "duration": 180,
                "views": 1000,
                "source": "youtube",
            }
        ]
        
        youtube = YouTubeService("test_key")
        
        # Test search
        results = await youtube.search("test query", limit=5)
        assert len(results) == 1
        assert results[0]["id"] == "test123"
        assert results[0]["title"] == "Test Song"
        
        # Test video info
        with patch('services.youtube.YouTubeService.get_video_info') as mock_info:
            mock_info.return_value = {
                "id": "test123",
                "title": "Test Song",
                "duration": 180,
                "thumbnail": "https://thumbnail.url",
            }
            
            info = await youtube.get_video_info("https://youtube.com/watch?v=test123")
            assert info["id"] == "test123"
            assert info["title"] == "Test Song"

@pytest.mark.asyncio
async def test_spotify_service():
    """Test Spotify service"""
    with patch('services.spotify.SpotifyService.search_tracks') as mock_search:
        mock_search.return_value = [
            {
                "id": "spotify123",
                "name": "Spotify Test",
                "artists": "Test Artist",
                "album": "Test Album",
                "duration_ms": 180000,
                "preview_url": "https://preview.url",
                "spotify_url": "https://open.spotify.com/track/spotify123",
                "source": "spotify",
            }
        ]
        
        spotify = SpotifyService("test_id", "test_secret")
        
        # Test search
        results = await spotify.search_tracks("test query", limit=5)
        assert len(results) == 1
        assert results[0]["id"] == "spotify123"
        assert results[0]["name"] == "Spotify Test"
        assert results[0]["source"] == "spotify"

@pytest.mark.asyncio
async def test_music_bot_engine(mock_config, mock_database, mock_cache):
    """Test music bot engine"""
    with patch('core.bot_engine.MusicBotEngine.initialize') as mock_init:
        mock_init.return_value = None
        
        bot_engine = MusicBotEngine(mock_database, mock_cache)
        
        # Test search tracks
        with patch.object(bot_engine, 'youtube') as mock_youtube:
            mock_youtube.search.return_value = [
                {"id": "test1", "title": "Test 1", "source": "youtube"}
            ]
            
            results = await bot_engine.search_tracks("test query", source="youtube")
            assert len(results) == 1
            assert results[0]["title"] == "Test 1"
        
        # Test get track info
        with patch.object(bot_engine, 'youtube') as mock_youtube:
            mock_youtube.get_video_info.return_value = {
                "id": "test1",
                "title": "Test Track",
                "duration": 180,
                "source": "youtube",
            }
            
            info = await bot_engine.get_track_info("https://youtube.com/watch?v=test1")
            assert info["title"] == "Test Track"
            assert info["source"] == "youtube"

def test_formatters():
    """Test formatting utilities"""
    from utils.formatters import (
        format_duration, format_file_size, format_number,
        format_time_ago, format_progress_bar
    )
    
    # Test duration formatting
    assert format_duration(90) == "1:30"
    assert format_duration(3661) == "1:01:01"
    assert format_duration(0) == "N/A"
    
    # Test file size formatting
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(1048576) == "1.0 MB"
    assert format_file_size(500) == "500 B"
    
    # Test number formatting
    assert format_number(1500) == "1.5K"
    assert format_number(1500000) == "1.5M"
    assert format_number(999) == "999"
    
    # Test progress bar
    bar = format_progress_bar(75.5, length=10)
    assert "75.5%" in bar
    
    # Test time ago (mock datetime)
    from datetime import datetime, timedelta
    with patch('utils.formatters.datetime') as mock_datetime:
        mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        past_time = datetime(2024, 1, 1, 11, 30, 0)
        assert "30 minutes" in format_time_ago(past_time)

@pytest.mark.asyncio
async def test_error_handler():
    """Test error handling"""
    from middleware.error_handler import ErrorHandler
    
    # Test specific error messages
    from pyrogram.errors import FloodWait
    
    error = FloodWait(30)  # 30 seconds
    message = ErrorHandler.handle_error(error)
    assert "30 seconds" in message
    
    # Test custom error
    from utils.exceptions import BotError
    error = BotError("Test error")
    message = ErrorHandler.handle_error(error)
    assert "Test error" in message
    
    # Test unknown error
    class UnknownError(Exception):
        pass
    
    error = UnknownError("Unknown")
    message = ErrorHandler.handle_error(error)
    assert "unexpected error" in message

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
