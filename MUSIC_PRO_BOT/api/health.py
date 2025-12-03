from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
import psutil
import platform
from datetime import datetime

from config import config
from core.bot_engine import MusicBotEngine
from utils.logger import logger

router = APIRouter()

@router.get("/")
async def health_check():
    """Basic health check"""
    try:
        # Check bot status
        bot_status = "unknown"
        bot_alive = False
        
        # Try to get bot engine instance
        try:
            bot_engine = MusicBotEngine.get_instance()
            if bot_engine:
                bot_alive = await bot_engine.is_alive()
                bot_status = "online" if bot_alive else "offline"
        except:
            pass
        
        # Get system info
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Get process info
        process = psutil.Process()
        process_memory = process.memory_info().rss
        
        # Count active connections (simplified)
        try:
            import psutil
            connections = len(process.connections())
        except:
            connections = 0
        
        return JSONResponse({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "music_bot",
            "version": "1.0.0",
            "environment": config.server.environment.value,
            
            "bot": {
                "status": bot_status,
                "alive": bot_alive,
            },
            
            "system": {
                "platform": platform.system(),
                "platform_release": platform.release(),
                "python_version": platform.python_version(),
                "uptime": str(datetime.utcnow() - datetime.fromtimestamp(process.create_time())),
            },
            
            "resources": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "disk_percent": disk.percent,
                "disk_used": disk.used,
                "disk_total": disk.total,
                "process_memory": process_memory,
                "connections": connections,
            },
            
            "database": {
                "mongodb": config.database.mongodb_uri != "",
                "redis": config.database.redis_url != "",
            },
            
            "features": {
                "voice_chat": config.enable_voice_chat,
                "spotify": config.enable_spotify,
                "genius": config.enable_genius,
                "lastfm": config.enable_lastfm,
            },
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
            }
        )

@router.get("/ready")
async def readiness_check():
    """Readiness check for load balancers"""
    try:
        # Check database connections
        db_ok = False
        cache_ok = False
        
        try:
            from core.database import DatabaseManager
            from core.cache_manager import CacheManager
            
            db = DatabaseManager()
            await db.connect()
            db_ok = await db.health_check()
            await db.disconnect()
            
            cache = CacheManager()
            await cache.connect()
            cache_ok = await cache.health_check()
            await cache.disconnect()
            
        except Exception as e:
            logger.error(f"Database check failed: {e}")
        
        # Check bot status
        bot_ok = False
        try:
            bot_engine = MusicBotEngine.get_instance()
            if bot_engine:
                bot_ok = await bot_engine.is_alive()
        except:
            pass
        
        # All checks must pass
        if db_ok and cache_ok and bot_ok:
            return JSONResponse({
                "status": "ready",
                "database": db_ok,
                "cache": cache_ok,
                "bot": bot_ok,
            })
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "database": db_ok,
                    "cache": cache_ok,
                    "bot": bot_ok,
                }
            )
            
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
            }
        )

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    try:
        import prometheus_client
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        
        # Create metrics registry
        registry = prometheus_client.CollectorRegistry()
        
        # Bot metrics
        bot_status = prometheus_client.Gauge(
            'bot_status',
            'Bot status (1=online, 0=offline)',
            registry=registry
        )
        
        # Try to get bot status
        try:
            bot_engine = MusicBotEngine.get_instance()
            if bot_engine and await bot_engine.is_alive():
                bot_status.set(1)
            else:
                bot_status.set(0)
        except:
            bot_status.set(0)
        
        # System metrics
        cpu_percent = prometheus_client.Gauge(
            'system_cpu_percent',
            'System CPU usage percent',
            registry=registry
        )
        cpu_percent.set(psutil.cpu_percent(interval=1))
        
        memory_percent = prometheus_client.Gauge(
            'system_memory_percent',
            'System memory usage percent',
            registry=registry
        )
        memory_percent.set(psutil.virtual_memory().percent)
        
        disk_percent = prometheus_client.Gauge(
            'system_disk_percent',
            'System disk usage percent',
            registry=registry
        )
        disk_percent.set(psutil.disk_usage('/').percent)
        
        # Process metrics
        process = psutil.Process()
        process_memory = prometheus_client.Gauge(
            'process_memory_bytes',
            'Process memory usage in bytes',
            registry=registry
        )
        process_memory.set(process.memory_info().rss)
        
        process_threads = prometheus_client.Gauge(
            'process_threads',
            'Number of process threads',
            registry=registry
        )
        process_threads.set(process.num_threads())
        
        # Bot specific metrics
        try:
            bot_engine = MusicBotEngine.get_instance()
            if bot_engine:
                stats = await bot_engine.get_bot_stats()
                
                tracks_played = prometheus_client.Gauge(
                    'bot_tracks_played',
                    'Total tracks played',
                    registry=registry
                )
                tracks_played.set(stats.get('total_plays', 0))
                
                active_chats = prometheus_client.Gauge(
                    'bot_active_chats',
                    'Number of active chats',
                    registry=registry
                )
                active_chats.set(stats.get('active_chats', 0))
                
                total_users = prometheus_client.Gauge(
                    'bot_total_users',
                    'Total number of users',
                    registry=registry
                )
                total_users.set(stats.get('total_users', 0))
        except:
            pass
        
        # Generate metrics response
        return prometheus_client.generate_latest(registry)
        
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
            }
        )

@router.get("/info")
async def service_info():
    """Service information"""
    return JSONResponse({
        "service": "Music Bot",
        "version": "1.0.0",
        "description": "Advanced Telegram Music Bot with Voice Chat",
        "repository": "https://github.com/yourusername/music-bot",
        "license": "MIT",
        "author": "Your Name",
        
        "features": {
            "voice_chat": config.enable_voice_chat,
            "spotify": config.enable_spotify,
            "genius": config.enable_genius,
            "lastfm": config.enable_lastfm,
            "youtube_api": config.enable_youtube_api,
        },
        
        "endpoints": {
            "health": "/health",
            "ready": "/ready",
            "metrics": "/metrics",
            "info": "/info",
            "stats": "/stats",
        },
        
        "contact": {
            "support": config.bot.support_chat,
            "issues": "https://github.com/yourusername/music-bot/issues",
        },
    })
