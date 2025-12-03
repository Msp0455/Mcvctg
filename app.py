"""
FastAPI Web Server for Render
Required to keep bot alive on free tier
"""

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn
import asyncio
from contextlib import asynccontextmanager

from config import config
from api.health import router as health_router
from api.stats import router as stats_router
from core.bot_engine import MusicBotEngine
from utils.logger import logger

# Bot instance
bot_engine = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    global bot_engine
    
    # Startup
    logger.info("🚀 Starting Web Server...")
    
    # Initialize bot engine (lightweight)
    from core.database import DatabaseManager
    from core.cache_manager import CacheManager
    
    db = DatabaseManager()
    await db.connect()
    
    cache = CacheManager()
    await cache.connect()
    
    bot_engine = MusicBotEngine(db, cache)
    await bot_engine.initialize_light()
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Web Server...")
    if bot_engine:
        await bot_engine.shutdown()
    await db.disconnect()
    await cache.disconnect()

# Create FastAPI app
app = FastAPI(
    title="Music Bot API",
    description="Advanced Telegram Music Bot",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if config.server.debug else None,
    redoc_url="/redoc" if config.server.debug else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.server.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if config.server.debug else ["your-bot.onrender.com", "localhost"]
)

# Add routers
app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(stats_router, prefix="/stats", tags=["stats"])

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🎵 Music Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 50px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255,255,255,0.1);
                padding: 30px;
                border-radius: 20px;
                backdrop-filter: blur(10px);
                max-width: 600px;
                margin: 0 auto;
            }
            h1 {
                font-size: 3em;
                margin-bottom: 20px;
            }
            .status {
                padding: 10px;
                border-radius: 10px;
                margin: 20px 0;
                font-weight: bold;
            }
            .online { background: #10b981; }
            .offline { background: #ef4444; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎵 Music Bot</h1>
            <div class="status online">✅ ONLINE</div>
            <p>Advanced Telegram Music Bot with Voice Chat Support</p>
            <p><strong>Features:</strong> YouTube, Spotify, Genius Lyrics, Last.fm, Voice Chat</p>
            <p><a href="/health" style="color: #93c5fd;">Health Check</a> | 
               <a href="/stats" style="color: #93c5fd;">Statistics</a></p>
            <p>Bot is running on Render Free Tier</p>
        </div>
    </body>
    </html>
    """

# Health endpoint for Render
@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    bot_status = "online" if bot_engine and await bot_engine.is_alive() else "offline"
    
    return JSONResponse({
        "status": "healthy",
        "bot": bot_status,
        "timestamp": asyncio.get_event_loop().time(),
        "environment": config.server.environment.value,
    })

# Error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
        log_level="info" if config.server.debug else "warning",
        access_log=False,
    )
