import asyncio
import logging
import traceback
from typing import Dict, Any, Optional, Callable
from functools import wraps

from pyrogram import Client
from pyrogram.errors import (
    FloodWait, UserNotParticipant, ChatAdminRequired,
    MessageNotModified, MessageDeleteForbidden, 
    MessageIdInvalid, PeerIdInvalid, ChannelInvalid,
    UsernameNotOccupied, UsernameInvalid, ChatWriteForbidden,
    SlowmodeWait, BadRequest, Unauthorized, InternalServerError
)

from utils.logger import logger, bot_logger
from utils.exceptions import (
    BotError, VoiceChatError, YouTubeError, SpotifyError,
    GeniusError, LastFMError, DatabaseError, QueueError
)

class ErrorHandler:
    """Centralized error handling for the bot"""
    
    # Error messages for different error types
    ERROR_MESSAGES = {
        FloodWait: "⏳ Please wait a few seconds before trying again.",
        UserNotParticipant: "❌ You need to join the channel/group to use this bot.",
        ChatAdminRequired: "❌ I need admin permissions to perform this action.",
        MessageNotModified: "",  # Silent error
        MessageDeleteForbidden: "❌ I don't have permission to delete messages.",
        MessageIdInvalid: "❌ The message is no longer available.",
        PeerIdInvalid: "❌ Invalid chat/user ID.",
        ChannelInvalid: "❌ Invalid channel.",
        UsernameNotOccupied: "❌ Username not found.",
        UsernameInvalid: "❌ Invalid username format.",
        ChatWriteForbidden: "❌ I can't send messages in this chat.",
        SlowmodeWait: "⏳ Please wait due to slowmode restriction.",
        BadRequest: "❌ Invalid request. Please try again.",
        Unauthorized: "❌ Authentication failed. Please contact admin.",
        InternalServerError: "❌ Server error. Please try again later.",
        
        # Custom errors
        BotError: "❌ {message}",
        VoiceChatError: "🎤 Voice chat error: {message}",
        YouTubeError: "📺 YouTube error: {message}",
        SpotifyError: "🎵 Spotify error: {message}",
        GeniusError: "📝 Lyrics error: {message}",
        LastFMError: "📊 Last.fm error: {message}",
        DatabaseError: "🗄️ Database error: {message}",
        QueueError: "📋 Queue error: {message}",
    }
    
    DEFAULT_ERROR_MESSAGE = "❌ An unexpected error occurred. Please try again."
    
    @classmethod
    def handle_error(cls, error: Exception, context: Dict[str, Any] = None) -> str:
        """Handle error and return user-friendly message"""
        context = context or {}
        
        # Log the error
        bot_logger.error_with_context(error, context)
        
        # Get error message
        error_type = type(error)
        error_message = cls._get_error_message(error, error_type)
        
        # Log to error channel if configured
        cls._log_to_error_channel(error, context, error_message)
        
        return error_message
    
    @classmethod
    def _get_error_message(cls, error: Exception, error_type: type) -> str:
        """Get user-friendly error message"""
        # Check for specific error types
        for err_type, message_template in cls.ERROR_MESSAGES.items():
            if issubclass(error_type, err_type):
                if message_template:
                    return message_template.format(message=str(error))
                return ""  # Empty string for silent errors
        
        # Handle FloodWait specially
        if isinstance(error, FloodWait):
            wait_time = error.value
            if wait_time > 60:
                return f"⏳ Please wait {wait_time//60} minutes before trying again."
            else:
                return f"⏳ Please wait {wait_time} seconds before trying again."
        
        # Default error message
        return cls.DEFAULT_ERROR_MESSAGE
    
    @classmethod
    def _log_to_error_channel(cls, error: Exception, context: Dict[str, Any], user_message: str):
        """Log error to error channel"""
        try:
            # This would send to a Telegram error channel
            # For now, just log it
            error_details = {
                "error": str(error),
                "type": type(error).__name__,
                "user_message": user_message,
                "traceback": traceback.format_exc(),
                "context": context,
            }
            
            logger.error("Error occurred", **error_details)
            
            # TODO: Send to Telegram error channel if configured
            # await cls._send_to_telegram(error_details)
            
        except Exception as e:
            logger.error(f"Failed to log error to channel: {e}")
    
    @classmethod
    async def _send_to_telegram(cls, error_details: Dict[str, Any]):
        """Send error details to Telegram channel"""
        # This would be implemented when error channel is configured
        pass

def error_handler_decorator(func: Callable):
    """Decorator to handle errors in async functions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Extract context from args
            context = {}
            
            # Try to extract message from args
            for arg in args:
                if hasattr(arg, 'chat') and hasattr(arg.chat, 'id'):
                    context['chat_id'] = arg.chat.id
                if hasattr(arg, 'from_user') and hasattr(arg.from_user, 'id'):
                    context['user_id'] = arg.from_user.id
                if hasattr(arg, 'text'):
                    context['message_text'] = arg.text
                if hasattr(arg, 'command'):
                    context['command'] = arg.command
            
            # Handle the error
            error_message = ErrorHandler.handle_error(e, context)
            
            # Send error message if needed
            if error_message:
                # Try to find message object to reply to
                for arg in args:
                    if hasattr(arg, 'reply_text'):
                        try:
                            await arg.reply_text(error_message)
                        except:
                            pass
                        break
            
            # Re-raise if it's a critical error
            if isinstance(e, (Unauthorized, InternalServerError)):
                raise
    
    return wrapper

def setup_exception_handlers():
    """Setup global exception handlers"""
    
    # Handle asyncio exceptions
    def handle_asyncio_exception(loop, context):
        msg = context.get("exception", context["message"])
        logger.error(f"Asyncio exception: {msg}")
    
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_asyncio_exception)
    
    # Handle unhandled exceptions
    def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupts
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
    
    sys.excepthook = handle_unhandled_exception
    
    logger.info("Exception handlers setup complete")

class RetryWithBackoff:
    """Retry decorator with exponential backoff"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    def __call__(self, func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(self.max_retries):
                try:
                    return await func(*args, **kwargs)
                except (FloodWait, SlowmodeWait) as e:
                    # Calculate wait time
                    if isinstance(e, FloodWait):
                        wait_time = e.value
                    else:
                        wait_time = self.base_delay * (2 ** attempt)
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{self.max_retries} "
                        f"after {wait_time}s"
                    )
                    
                    await asyncio.sleep(wait_time)
                    last_exception = e
                except Exception as e:
                    # Don't retry on other errors
                    raise
            
            # All retries failed
            if last_exception:
                raise last_exception
        
        return wrapper

class CircuitBreaker:
    """Circuit breaker pattern for external API calls"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker"""
        import time
        
        current_time = time.time()
        
        # Check if circuit is open
        if self.state == "OPEN":
            if self.last_failure_time and \
               current_time - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise BotError("Service temporarily unavailable. Please try again later.")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset circuit if half-open
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = current_time
            
            # Check if threshold reached
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit breaker OPEN for {func.__name__}")
            
            raise
    
    def reset(self):
        """Reset circuit breaker"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"

# Global circuit breaker instances
youtube_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
spotify_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
genius_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
lastfm_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
database_circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    """Decorator to apply circuit breaker to function"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit_breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator
