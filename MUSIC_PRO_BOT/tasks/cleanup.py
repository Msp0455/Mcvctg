import asyncio
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from config import config
from utils.logger import logger
from core.bot_engine import MusicBotEngine

class CleanupManager:
    """Manager for cleanup tasks"""
    
    def __init__(self, bot_engine: MusicBotEngine = None, cache_manager = None):
        self.bot_engine = bot_engine
        self.cache_manager = cache_manager
        self.running = False
        self.tasks = []
        
    async def start(self):
        """Start cleanup tasks"""
        if self.running:
            return
        
        self.running = True
        logger.info("Starting cleanup manager...")
        
        # Schedule cleanup tasks
        self.tasks = [
            asyncio.create_task(self._cleanup_old_downloads()),
            asyncio.create_task(self._cleanup_cache()),
            asyncio.create_task(self._cleanup_logs()),
            asyncio.create_task(self._cleanup_temp_files()),
            asyncio.create_task(self._cleanup_database()),
        ]
        
        logger.info("Cleanup manager started")
    
    async def stop(self):
        """Stop cleanup tasks"""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks = []
        logger.info("Cleanup manager stopped")
    
    async def _cleanup_old_downloads(self):
        """Cleanup old downloaded files"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                downloads_dir = config.DOWNLOADS_DIR
                if not downloads_dir.exists():
                    continue
                
                cutoff_time = datetime.now() - timedelta(hours=1)
                deleted_count = 0
                
                for file_path in downloads_dir.rglob('*'):
                    if file_path.is_file():
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            try:
                                file_path.unlink()
                                deleted_count += 1
                            except Exception as e:
                                logger.debug(f"Failed to delete file {file_path}: {e}")
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old downloaded files")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in downloads cleanup: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
    
    async def _cleanup_cache(self):
        """Cleanup cache directory"""
        while self.running:
            try:
                await asyncio.sleep(1800)  # Run every 30 minutes
                
                cache_dir = config.CACHE_DIR
                if not cache_dir.exists():
                    continue
                
                cutoff_time = datetime.now() - timedelta(days=1)
                deleted_count = 0
                total_size = 0
                
                for file_path in cache_dir.rglob('*'):
                    if file_path.is_file():
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            try:
                                file_size = file_path.stat().st_size
                                file_path.unlink()
                                deleted_count += 1
                                total_size += file_size
                            except Exception as e:
                                logger.debug(f"Failed to delete cache file {file_path}: {e}")
                
                if deleted_count > 0:
                    logger.info(
                        f"Cleaned up {deleted_count} cache files "
                        f"({total_size / 1024 / 1024:.2f} MB)"
                    )
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_logs(self):
        """Cleanup old log files"""
        while self.running:
            try:
                await asyncio.sleep(86400)  # Run every 24 hours
                
                logs_dir = config.LOGS_DIR
                if not logs_dir.exists():
                    continue
                
                cutoff_time = datetime.now() - timedelta(days=7)
                deleted_count = 0
                
                for file_path in logs_dir.glob('*.log'):
                    if file_path.is_file():
                        file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_mtime < cutoff_time:
                            try:
                                file_path.unlink()
                                deleted_count += 1
                            except Exception as e:
                                logger.debug(f"Failed to delete log file {file_path}: {e}")
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old log files")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in logs cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def _cleanup_temp_files(self):
        """Cleanup temporary files"""
        while self.running:
            try:
                await asyncio.sleep(900)  # Run every 15 minutes
                
                temp_patterns = ['*.tmp', '*.temp', '*.part', '*.crdownload']
                deleted_count = 0
                
                # Check downloads directory
                for pattern in temp_patterns:
                    for file_path in config.DOWNLOADS_DIR.rglob(pattern):
                        if file_path.is_file():
                            try:
                                # Check if file is old (> 1 hour)
                                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                                if datetime.now() - file_mtime > timedelta(hours=1):
                                    file_path.unlink()
                                    deleted_count += 1
                            except Exception as e:
                                logger.debug(f"Failed to delete temp file {file_path}: {e}")
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} temporary files")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in temp files cleanup: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_database(self):
        """Cleanup old database records"""
        while self.running:
            try:
                await asyncio.sleep(43200)  # Run every 12 hours
                
                if not self.bot_engine or not self.bot_engine.database:
                    continue
                
                # Cleanup old history records
                deleted = await self.bot_engine.database.cleanup_old_data(days=30)
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old database records")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in database cleanup: {e}")
                await asyncio.sleep(3600)
    
    async def cleanup_now(self, task_name: str = None):
        """Run cleanup task immediately"""
        if task_name == 'downloads' or task_name is None:
            await self._cleanup_old_downloads()
        
        if task_name == 'cache' or task_name is None:
            await self._cleanup_cache()
        
        if task_name == 'logs' or task_name is None:
            await self._cleanup_logs()
        
        if task_name == 'temp' or task_name is None:
            await self._cleanup_temp_files()
        
        if task_name == 'database' or task_name is None:
            await self._cleanup_database()
    
    async def get_cleanup_stats(self) -> dict:
        """Get cleanup statistics"""
        stats = {
            'downloads': {
                'directory': str(config.DOWNLOADS_DIR),
                'exists': config.DOWNLOADS_DIR.exists(),
                'size': 0,
                'file_count': 0,
            },
            'cache': {
                'directory': str(config.CACHE_DIR),
                'exists': config.CACHE_DIR.exists(),
                'size': 0,
                'file_count': 0,
            },
            'logs': {
                'directory': str(config.LOGS_DIR),
                'exists': config.LOGS_DIR.exists(),
                'size': 0,
                'file_count': 0,
            },
        }
        
        # Calculate sizes
        for key, info in stats.items():
            if info['exists']:
                directory = Path(info['directory'])
                total_size = 0
                file_count = 0
                
                for file_path in directory.rglob('*'):
                    if file_path.is_file():
                        try:
                            total_size += file_path.stat().st_size
                            file_count += 1
                        except:
                            pass
                
                info['size'] = total_size
                info['size_human'] = f"{total_size / 1024 / 1024:.2f} MB"
                info['file_count'] = file_count
        
        return stats
