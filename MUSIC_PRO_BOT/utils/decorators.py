import asyncio
import functools
import time
import inspect
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
import cachetools
from pyrogram.types import Message, User

from config import config
from utils.logger import logger
from utils.exceptions import BotError, RateLimitError

# Cache for rate limiting
_rate_limit_cache = cachetools.TTLCache(maxsize=10000, ttl=60)

def rate_limit(requests: int = 5, period: int = 60):
    """
    Rate limit decorator for commands
    
    Args:
        requests: Number of allowed requests
        period: Time period in seconds
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(client, message: Message, *args, **kwargs):
            if not hasattr(message, 'from_user') or not message.from_user:
                return await func(client, message, *args, **kwargs)
            
            user_id = message.from_user.id
            chat_id = message.chat.id if message.chat else 0
            
            # Create cache key
            cache_key = f"rate_limit:{user_id}:{chat_id}:{func.__name__}"
            
            # Get current usage
            current_time = time.time()
            usage = _rate_limit_cache.get(cache_key, [])
            
            # Remove old entries
            usage = [t for t in usage if current_time - t < period]
            
            # Check if limit exceeded
            if len(usage) >= requests:
                wait_time = period - (current_time - usage[0])
                raise RateLimitError(
                    f"Rate limit exceeded. Please wait {int(wait_time)} seconds."
                )
            
            # Add current request
            usage.append(current_time)
            _rate_limit_cache[cache_key] = usage
            
            # Call original function
            return await func(client, message, *args, **kwargs)
        
        return wrapper
    return decorator

def admin_only(func: Callable):
    """Only allow admin users to execute command"""
    @functools.wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        if not hasattr(message, 'from_user') or not message.from_user:
            return await func(client, message, *args, **kwargs)
        
        user_id = message.from_user.id
        
        # Check if user is admin
        if user_id not in config.bot.admin_ids:
            await message.reply_text("❌ This command is only for administrators.")
            return
        
        return await func(client, message, *args, **kwargs)
    return wrapper

def group_only(func: Callable):
    """Only allow command in groups"""
    @functools.wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        if not message.chat or message.chat.type not in ["group", "supergroup"]:
            await message.reply_text("❌ This command only works in groups.")
            return
        
        return await func(client, message, *args, **kwargs)
    return wrapper

def private_only(func: Callable):
    """Only allow command in private chats"""
    @functools.wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        if message.chat.type != "private":
            await message.reply_text("❌ This command only works in private chats.")
            return
        
        return await func(client, message, *args, **kwargs)
    return wrapper

def voice_chat_required(func: Callable):
    """Require voice chat to be joined"""
    @functools.wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        from core.bot_engine import MusicBotEngine
        
        chat_id = message.chat.id
        bot_engine = MusicBotEngine.get_instance()
        
        if not bot_engine or not await bot_engine.voice_client.is_joined(chat_id):
            await message.reply_text(
                "❌ Not in voice chat! Use `/join` first."
            )
            return
        
        return await func(client, message, *args, **kwargs)
    return wrapper

def track_playing_required(func: Callable):
    """Require track to be playing"""
    @functools.wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        from core.bot_engine import MusicBotEngine
        
        chat_id = message.chat.id
        bot_engine = MusicBotEngine.get_instance()
        
        if not bot_engine or not bot_engine.is_playing(chat_id):
            await message.reply_text("❌ Nothing is playing.")
            return
        
        return await func(client, message, *args, **kwargs)
    return wrapper

def track_paused_required(func: Callable):
    """Require track to be paused"""
    @functools.wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        from core.bot_engine import MusicBotEngine
        
        chat_id = message.chat.id
        bot_engine = MusicBotEngine.get_instance()
        
        if not bot_engine or not bot_engine.is_paused(chat_id):
            await message.reply_text("❌ Nothing is paused.")
            return
        
        return await func(client, message, *args, **kwargs)
    return wrapper

def handle_errors(func: Callable):
    """Handle errors in command functions"""
    @functools.wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        try:
            return await func(client, message, *args, **kwargs)
        except Exception as e:
            from middleware.error_handler import ErrorHandler
            
            # Extract context
            context = {
                'user_id': getattr(message.from_user, 'id', 0),
                'chat_id': getattr(message.chat, 'id', 0),
                'command': func.__name__,
            }
            
            # Get error message
            error_message = ErrorHandler.handle_error(e, context)
            
            # Send error message
            if error_message:
                await message.reply_text(error_message)
            
            # Log error
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
    
    return wrapper

def log_command(func: Callable):
    """Log command execution"""
    @functools.wraps(func)
    async def wrapper(client, message: Message, *args, **kwargs):
        start_time = time.time()
        
        # Log command start
        logger.info(
            f"Command started: {func.__name__}",
            user_id=getattr(message.from_user, 'id', 0),
            chat_id=getattr(message.chat, 'id', 0),
            chat_type=getattr(message.chat, 'type', 'unknown'),
        )
        
        try:
            result = await func(client, message, *args, **kwargs)
            
            # Log command completion
            duration = time.time() - start_time
            logger.info(
                f"Command completed: {func.__name__}",
                user_id=getattr(message.from_user, 'id', 0),
                chat_id=getattr(message.chat, 'id', 0),
                duration_ms=round(duration * 1000, 2),
                success=True,
            )
            
            return result
            
        except Exception as e:
            # Log command error
            duration = time.time() - start_time
            logger.error(
                f"Command failed: {func.__name__}",
                user_id=getattr(message.from_user, 'id', 0),
                chat_id=getattr(message.chat, 'id', 0),
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                success=False,
            )
            raise
    
    return wrapper

def cache_result(ttl: int = 300, maxsize: int = 100):
    """
    Cache function result with TTL
    
    Args:
        ttl: Time to live in seconds
        maxsize: Maximum cache size
    """
    cache = cachetools.TTLCache(maxsize=maxsize, ttl=ttl)
    
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [func.__name__]
            
            # Add args
            for arg in args:
                if isinstance(arg, (int, str, float, bool)):
                    key_parts.append(str(arg))
                elif hasattr(arg, 'id'):
                    key_parts.append(str(arg.id))
            
            # Add kwargs
            for k, v in kwargs.items():
                if isinstance(v, (int, str, float, bool)):
                    key_parts.append(f"{k}:{v}")
            
            cache_key = ":".join(key_parts)
            
            # Check cache
            if cache_key in cache:
                logger.debug(f"Cache hit: {cache_key}")
                return cache[cache_key]
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            cache[cache_key] = result
            logger.debug(f"Cache miss: {cache_key}")
            
            return result
        
        return wrapper
    return decorator

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay in seconds
        backoff: Backoff multiplier
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Don't retry on certain errors
                    if isinstance(e, (BotError, RateLimitError)):
                        raise
                    
                    # Calculate wait time
                    wait_time = delay * (backoff ** attempt)
                    
                    logger.warning(
                        f"Retry attempt {attempt + 1}/{max_attempts} for {func.__name__}",
                        error=str(e),
                        wait_time=wait_time,
                    )
                    
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(wait_time)
            
            # All attempts failed
            raise last_exception or Exception(f"Failed after {max_attempts} attempts")
        
        return wrapper
    return decorator

def timeout(seconds: float):
    """
    Timeout decorator for async functions
    
    Args:
        seconds: Timeout in seconds
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
        
        return wrapper
    return decorator

def validate_args(*validators):
    """
    Validate function arguments
    
    Args:
        validators: List of validator functions
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(client, message: Message, *args, **kwargs):
            # Get command arguments
            command_args = message.text.split()[1:] if message.text else []
            
            # Apply validators
            for validator in validators:
                try:
                    validator(command_args)
                except ValueError as e:
                    await message.reply_text(f"❌ Invalid arguments: {str(e)}")
                    return
            
            return await func(client, message, *args, **kwargs)
        
        return wrapper
    return decorator

# Argument validators
def validate_min_args(min_count: int):
    """Validate minimum number of arguments"""
    def validator(args):
        if len(args) < min_count:
            raise ValueError(f"At least {min_count} argument(s) required")
    return validator

def validate_max_args(max_count: int):
    """Validate maximum number of arguments"""
    def validator(args):
        if len(args) > max_count:
            raise ValueError(f"Maximum {max_count} argument(s) allowed")
    return validator

def validate_url_arg(position: int = 0):
    """Validate URL argument"""
    def validator(args):
        if position < len(args):
            import re
            url_pattern = re.compile(
                r'^(https?://)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
            )
            if not url_pattern.match(args[position]):
                raise ValueError(f"Argument {position + 1} must be a valid URL")
    return validator

def register_command(command_name: str, description: str = "", usage: str = ""):
    """
    Register command with metadata
    
    Args:
        command_name: Name of the command
        description: Command description
        usage: Command usage example
    """
    def decorator(func: Callable):
        func.command_name = command_name
        func.description = description
        func.usage = usage
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

class CommandRegistry:
    """Registry for all bot commands"""
    
    _commands = {}
    
    @classmethod
    def register(cls, func: Callable):
        """Register a command"""
        cls._commands[func.command_name] = {
            'function': func,
            'description': func.description,
            'usage': func.usage,
        }
        return func
    
    @classmethod
    def get_command(cls, name: str):
        """Get command by name"""
        return cls._commands.get(name)
    
    @classmethod
    def get_all_commands(cls):
        """Get all registered commands"""
        return cls._commands
    
    @classmethod
    def get_help_text(cls):
        """Generate help text from registered commands"""
        help_text = "📖 **Available Commands:**\n\n"
        
        for name, info in sorted(cls._commands.items()):
            description = info['description'] or 'No description'
            usage = info['usage'] or f"/{name}"
            
            help_text += f"**/{name}** - {description}\n"
            help_text += f"    `{usage}`\n\n"
        
        return help_text
