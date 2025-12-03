"""
Custom exceptions for Music Bot
"""

class BotError(Exception):
    """Base exception for bot errors"""
    pass

class VoiceChatError(BotError):
    """Voice chat related errors"""
    pass

class YouTubeError(BotError):
    """YouTube API related errors"""
    pass

class SpotifyError(BotError):
    """Spotify API related errors"""
    pass

class GeniusError(BotError):
    """Genius API related errors"""
    pass

class LastFMError(BotError):
    """Last.fm API related errors"""
    pass

class DatabaseError(BotError):
    """Database related errors"""
    pass

class CacheError(BotError):
    """Cache related errors"""
    pass

class QueueError(BotError):
    """Queue related errors"""
    pass

class AudioError(BotError):
    """Audio processing errors"""
    pass

class NetworkError(BotError):
    """Network related errors"""
    pass

class RateLimitError(BotError):
    """Rate limit exceeded"""
    pass

class ValidationError(BotError):
    """Input validation errors"""
    pass

class PermissionError(BotError):
    """Permission related errors"""
    pass

class ConfigurationError(BotError):
    """Configuration errors"""
    pass

class ResourceNotFoundError(BotError):
    """Resource not found"""
    pass

class TimeoutError(BotError):
    """Operation timeout"""
    pass

class CircuitBreakerError(BotError):
    """Circuit breaker open"""
    pass

class RetryExhaustedError(BotError):
    """All retry attempts exhausted"""
    pass

class InvalidStateError(BotError):
    """Invalid state error"""
    pass
