import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import structlog
from structlog.processors import JSONRenderer, TimeStamper, format_exc_info
from structlog.stdlib import add_log_level, filter_by_level
from structlog.types import EventDict, Processor

from config import config

class CustomJSONRenderer(JSONRenderer):
    """Custom JSON renderer with additional fields"""
    
    def __call__(self, logger: logging.Logger, name: str, event_dict: EventDict) -> str:
        # Add timestamp if not present
        if "timestamp" not in event_dict:
            event_dict["timestamp"] = datetime.utcnow().isoformat()
        
        # Add service name
        event_dict["service"] = "music_bot"
        
        # Add environment
        event_dict["environment"] = config.server.environment.value
        
        # Add log level
        if "level" not in event_dict:
            event_dict["level"] = name
        
        # Remove exc_info if it's None
        if "exc_info" in event_dict and event_dict["exc_info"] is None:
            del event_dict["exc_info"]
        
        # Convert exception to string if present
        if "exception" in event_dict and isinstance(event_dict["exception"], Exception):
            event_dict["exception"] = str(event_dict["exception"])
        
        return super().__call__(logger, name, event_dict)

class TelegramFormatter(logging.Formatter):
    """Formatter for Telegram-style logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Create basic format
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        message = record.getMessage()
        
        # Add extra fields if present
        extras = []
        if hasattr(record, 'user_id'):
            extras.append(f"👤 User: {record.user_id}")
        if hasattr(record, 'chat_id'):
            extras.append(f"💬 Chat: {record.chat_id}")
        if hasattr(record, 'command'):
            extras.append(f"⌨️ Command: {record.command}")
        
        # Format the log message
        formatted = f"[{timestamp}] {level}: {message}"
        if extras:
            formatted += f" | {' | '.join(extras)}"
        
        # Add exception info if present
        if record.exc_info:
            formatted += f"\n{self.formatException(record.exc_info)}"
        
        return formatted

def setup_logging() -> structlog.BoundLogger:
    """Setup structured logging"""
    # Create logs directory
    logs_dir = config.LOGS_DIR
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging level
    log_level = logging.DEBUG if config.server.debug else logging.INFO
    
    # Clear existing handlers
    logging.basicConfig(level=log_level, handlers=[])
    
    # Create handlers
    handlers = []
    
    # Console handler (colorful for development)
    if config.is_development:
        import colorlog
        
        console_handler = colorlog.StreamHandler(sys.stdout)
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s[%(asctime)s] %(levelname)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            log_colors={
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'red,bg_white',
            }
        )
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)
    
    # File handler (JSON format)
    log_file = logs_dir / f"bot_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(message)s'))
    handlers.append(file_handler)
    
    # Error file handler
    error_file = logs_dir / "errors.log"
    error_handler = logging.FileHandler(error_file, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(TelegramFormatter())
    handlers.append(error_handler)
    
    # Apply handlers to root logger
    root_logger = logging.getLogger()
    root_logger.handlers = handlers
    root_logger.setLevel(log_level)
    
    # Disable verbose logging for some libraries
    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("pytgcalls").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # Configure structlog
    processors: list[Processor] = [
        filter_by_level,
        add_log_level,
        TimeStamper(fmt="iso"),
        format_exc_info,
    ]
    
    if config.is_production:
        processors.append(CustomJSONRenderer())
    else:
        # Pretty print for development
        from structlog.dev import ConsoleRenderer
        processors.append(ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Create and return bound logger
    logger = structlog.get_logger("music_bot")
    logger.info("Logging setup complete", 
                environment=config.server.environment.value,
                log_level=logging.getLevelName(log_level))
    
    return logger

class BotLogger:
    """Bot-specific logging utilities"""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
    
    def command(self, user_id: int, chat_id: int, command: str, **kwargs):
        """Log command execution"""
        self.logger.info(
            "Command executed",
            user_id=user_id,
            chat_id=chat_id,
            command=command,
            **kwargs
        )
    
    def track_played(self, track_id: str, title: str, user_id: int, chat_id: int, source: str):
        """Log track played"""
        self.logger.info(
            "Track played",
            track_id=track_id,
            title=title,
            user_id=user_id,
            chat_id=chat_id,
            source=source
        )
    
    def voice_chat_event(self, chat_id: int, event: str, **kwargs):
        """Log voice chat event"""
        self.logger.info(
            "Voice chat event",
            chat_id=chat_id,
            event=event,
            **kwargs
        )
    
    def api_call(self, service: str, endpoint: str, duration: float, success: bool, **kwargs):
        """Log API call"""
        level = "info" if success else "error"
        getattr(self.logger, level)(
            "API call",
            service=service,
            endpoint=endpoint,
            duration_ms=round(duration * 1000, 2),
            success=success,
            **kwargs
        )
    
    def error_with_context(self, error: Exception, context: Dict[str, Any]):
        """Log error with context"""
        self.logger.error(
            "Error occurred",
            error=str(error),
            error_type=type(error).__name__,
            **context
        )
    
    def performance(self, operation: str, duration: float, **kwargs):
        """Log performance metrics"""
        self.logger.info(
            "Performance metric",
            operation=operation,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def user_activity(self, user_id: int, activity: str, **kwargs):
        """Log user activity"""
        self.logger.info(
            "User activity",
            user_id=user_id,
            activity=activity,
            **kwargs
        )
    
    def bot_start(self, bot_name: str, bot_id: int, version: str = "1.0.0"):
        """Log bot startup"""
        self.logger.info(
            "Bot started",
            bot_name=bot_name,
            bot_id=bot_id,
            version=version,
            environment=config.server.environment.value
        )
    
    def bot_stop(self, reason: str, **kwargs):
        """Log bot shutdown"""
        self.logger.info(
            "Bot stopped",
            reason=reason,
            **kwargs
        )

# Global logger instance
logger = setup_logging()
bot_logger = BotLogger(logger)
