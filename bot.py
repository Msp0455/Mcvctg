"""
🎵 Advanced Music Bot - Main Entry Point
Production-ready with all features
"""

import asyncio
import signal
import sys
import logging
from contextlib import asynccontextmanager
from typing import Optional

import uvloop
from pyrogram import idle

from config import config
from core.bot_engine import MusicBotEngine
from core.cache_manager import CacheManager
from core.database import DatabaseManager
from utils.logger import setup_logging
from api.server import start_web_server
from middleware.error_handler import setup_exception_handlers
from tasks.cleanup import CleanupManager
from tasks.monitor import SystemMonitor

# Setup logging
logger = setup_logging()

class MusicBot:
    """Main bot application"""
    
    def __init__(self):
        self.bot_engine: Optional[MusicBotEngine] = None
        self.database: Optional[DatabaseManager] = None
        self.cache: Optional[CacheManager] = None
        self.cleanup: Optional[CleanupManager] = None
        self.monitor: Optional[SystemMonitor] = None
        self.web_server = None
        
        # Signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(self.shutdown())
    
    async def initialize(self):
        """Initialize all components"""
        try:
            logger.info("🚀 Initializing Music Bot...")
            
            # 1. Setup exception handling
            setup_exception_handlers()
            
            # 2. Initialize database
            self.database = DatabaseManager()
            await self.database.connect()
            logger.info("✅ Database connected")
            
            # 3. Initialize cache
            self.cache = CacheManager()
            await self.cache.connect()
            logger.info("✅ Cache connected")
            
            # 4. Initialize bot engine
            self.bot_engine = MusicBotEngine(self.database, self.cache)
            await self.bot_engine.initialize()
            logger.info("✅ Bot engine initialized")
            
            # 5. Start background tasks
            self.cleanup = CleanupManager(self.bot_engine, self.cache)
            await self.cleanup.start()
            
            self.monitor = SystemMonitor(self.bot_engine, self.database)
            await self.monitor.start()
            
            # 6. Start web server (for health checks)
            if config.server.environment == Environment.PRODUCTION:
                self.web_server = await start_web_server()
                logger.info(f"✅ Web server started on port {config.server.port}")
            
            logger.info("🎉 Bot initialization complete!")
            
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}", exc_info=True)
            await self.shutdown()
            sys.exit(1)
    
    async def run(self):
        """Run the bot"""
        try:
            # Run idle to keep bot alive
            await idle()
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot runtime error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down bot...")
        
        shutdown_tasks = []
        
        # Stop web server
        if self.web_server:
            shutdown_tasks.append(self.web_server.shutdown())
        
        # Stop background tasks
        if self.monitor:
            shutdown_tasks.append(self.monitor.stop())
        
        if self.cleanup:
            shutdown_tasks.append(self.cleanup.stop())
        
        # Stop bot engine
        if self.bot_engine:
            shutdown_tasks.append(self.bot_engine.shutdown())
        
        # Close database connections
        if self.database:
            shutdown_tasks.append(self.database.disconnect())
        
        # Close cache connections
        if self.cache:
            shutdown_tasks.append(self.cache.disconnect())
        
        # Execute all shutdown tasks
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        logger.info("👋 Bot shutdown complete")
    
    @asynccontextmanager
    async def lifespan(self):
        """Async context manager for lifespan"""
        await self.initialize()
        try:
            yield
        finally:
            await self.shutdown()

async def main():
    """Main function"""
    # Use uvloop for better performance
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    
    # Create and run bot
    bot = MusicBot()
    
    async with bot.lifespan():
        await bot.run()

if __name__ == "__main__":
    # Entry point
    asyncio.run(main())
