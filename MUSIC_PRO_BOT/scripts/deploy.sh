#!/bin/bash

# Deployment script for Music Bot
set -e

echo "🚀 Starting Music Bot Deployment..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found!"
    exit 1
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        error "Python3 is not installed"
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        error "pip3 is not installed"
    fi
    
    # Check FFmpeg
    if ! command -v ffmpeg &> /dev/null; then
        warn "FFmpeg is not installed. Audio conversion may not work properly."
    fi
    
    # Check MongoDB (if local)
    if [ "$MONGODB_URI" == "mongodb://localhost:27017" ]; then
        if ! command -v mongod &> /dev/null; then
            warn "MongoDB is not installed locally. Using remote MongoDB."
        fi
    fi
    
    # Check Redis (if local)
    if [ "$REDIS_URL" == "redis://localhost:6379" ]; then
        if ! command -v redis-cli &> /dev/null; then
            warn "Redis is not installed locally. Using remote Redis."
        fi
    fi
    
    log "Prerequisites check complete."
}

# Setup virtual environment
setup_venv() {
    log "Setting up virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    log "Virtual environment setup complete."
}

# Install dependencies
install_dependencies() {
    log "Installing dependencies..."
    
    pip install -r requirements.txt
    
    if [ "$ENVIRONMENT" == "development" ]; then
        pip install -r requirements-dev.txt
    fi
    
    log "Dependencies installed."
}

# Setup database
setup_database() {
    log "Setting up database..."
    
    # Create database directories
    mkdir -p logs cache downloads
    
    # Initialize MongoDB if local
    if [ "$MONGODB_URI" == "mongodb://localhost:27017" ]; then
        if command -v mongod &> /dev/null; then
            log "Starting MongoDB..."
            if ! pgrep -x "mongod" > /dev/null; then
                mongod --fork --logpath ./logs/mongodb.log --dbpath ./data/db
                sleep 5
            fi
            
            # Create indexes
            log "Creating database indexes..."
            python -c "
from database.mongodb import MongoDBManager
import asyncio

async def setup():
    db = MongoDBManager()
    await db.connect()
    print('✅ Database indexes created')

asyncio.run(setup())
            "
        fi
    fi
    
    # Initialize Redis if local
    if [ "$REDIS_URL" == "redis://localhost:6379" ]; then
        if command -v redis-server &> /dev/null; then
            log "Starting Redis..."
            if ! pgrep -x "redis-server" > /dev/null; then
                redis-server --daemonize yes
                sleep 2
            fi
        fi
    fi
    
    log "Database setup complete."
}

# Run migrations
run_migrations() {
    log "Running migrations..."
    
    # Placeholder for future migrations
    # python scripts/migrate.py
    
    log "Migrations complete."
}

# Generate String Session
generate_session() {
    if [ ! -z "$STRING_SESSION" ]; then
        log "String session already exists in .env"
        return
    fi
    
    read -p "Do you want to generate a string session for voice chat? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log "Generating string session..."
        python start_session.py
        
        if [ $? -eq 0 ]; then
            log "String session generated successfully."
        else
            warn "Failed to generate string session. Voice chat will be disabled."
        fi
    fi
}

# Start the bot
start_bot() {
    log "Starting Music Bot..."
    
    # Check if bot is already running
    if pgrep -f "python bot.py" > /dev/null; then
        warn "Bot is already running. Stopping first..."
        stop_bot
    fi
    
    # Start the bot
    if [ "$ENVIRONMENT" == "production" ]; then
        # Production mode with logging
        nohup python bot.py > logs/bot.log 2>&1 &
        echo $! > bot.pid
        
        # Start web server
        nohup gunicorn app:app --workers 1 --worker-class uvicorn.workers.UvicornWorker \
            --bind 0.0.0.0:$PORT --timeout 120 > logs/web.log 2>&1 &
        echo $! > web.pid
        
        log "Bot started in production mode (PID: $(cat bot.pid))"
        log "Web server started (PID: $(cat web.pid))"
    else
        # Development mode
        python bot.py &
        echo $! > bot.pid
        
        log "Bot started in development mode (PID: $(cat bot.pid))"
    fi
    
    # Wait a bit and check status
    sleep 5
    if pgrep -f "python bot.py" > /dev/null; then
        log "✅ Bot is running successfully!"
        log "📊 Check logs: tail -f logs/bot.log"
        log "🌐 Health check: curl http://localhost:$PORT/health"
    else
        error "Failed to start bot. Check logs for details."
    fi
}

# Stop the bot
stop_bot() {
    log "Stopping Music Bot..."
    
    if [ -f "bot.pid" ]; then
        kill $(cat bot.pid) 2>/dev/null || true
        rm -f bot.pid
    fi
    
    if [ -f "web.pid" ]; then
        kill $(cat web.pid) 2>/dev/null || true
        rm -f web.pid
    fi
    
    # Kill any remaining python processes
    pkill -f "python bot.py" 2>/dev/null || true
    pkill -f "gunicorn" 2>/dev/null || true
    
    log "Bot stopped."
}

# Restart the bot
restart_bot() {
    log "Restarting Music Bot..."
    stop_bot
    sleep 2
    start_bot
}

# Backup data
backup_data() {
    log "Creating backup..."
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_DIR="backups/$TIMESTAMP"
    
    mkdir -p $BACKUP_DIR
    
    # Backup database
    if command -v mongodump &> /dev/null && [ "$MONGODB_URI" == "mongodb://localhost:27017" ]; then
        mongodump --out $BACKUP_DIR/mongodb
        log "MongoDB backup created."
    fi
    
    # Backup Redis
    if command -v redis-cli &> /dev/null && [ "$REDIS_URL" == "redis://localhost:6379" ]; then
        redis-cli --rdb $BACKUP_DIR/redis.rdb
        log "Redis backup created."
    fi
    
    # Backup logs and configuration
    cp -r logs $BACKUP_DIR/
    cp .env $BACKUP_DIR/
    cp config.py $BACKUP_DIR/
    
    # Create archive
    tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
    rm -rf $BACKUP_DIR
    
    log "✅ Backup created: $BACKUP_DIR.tar.gz"
}

# Monitor bot status
monitor_bot() {
    log "Monitoring bot status..."
    
    if pgrep -f "python bot.py" > /dev/null; then
        log "✅ Bot is running"
        
        # Check health endpoint
        if curl -s -f http://localhost:$PORT/health > /dev/null; then
            log "✅ Health check passed"
        else
            warn "⚠️ Health check failed"
        fi
    else
        error "❌ Bot is not running"
    fi
}

# Show logs
show_logs() {
    if [ ! -f "logs/bot.log" ]; then
        error "No log file found"
    fi
    
    case "$1" in
        "bot")
            tail -f logs/bot.log
            ;;
        "web")
            tail -f logs/web.log
            ;;
        "error")
            tail -f logs/errors.log
            ;;
        *)
            echo "Usage: $0 logs [bot|web|error]"
            ;;
    esac
}

# Main menu
show_menu() {
    echo "========================================="
    echo "       🎵 Music Bot Deployment Menu      "
    echo "========================================="
    echo "1. Deploy Bot (Full Setup)"
    echo "2. Start Bot"
    echo "3. Stop Bot"
    echo "4. Restart Bot"
    echo "5. Monitor Status"
    echo "6. Backup Data"
    echo "7. Show Logs"
    echo "8. Generate String Session"
    echo "9. Install Dependencies"
    echo "10. Setup Database"
    echo "0. Exit"
    echo "========================================="
    
    read -p "Enter choice: " choice
    
    case $choice in
        1) deploy_full ;;
        2) start_bot ;;
        3) stop_bot ;;
        4) restart_bot ;;
        5) monitor_bot ;;
        6) backup_data ;;
        7) 
            echo "1. Bot logs"
            echo "2. Web logs"
            echo "3. Error logs"
            read -p "Select log type: " log_type
            case $log_type in
                1) show_logs "bot" ;;
                2) show_logs "web" ;;
                3) show_logs "error" ;;
                *) echo "Invalid choice" ;;
            esac
            ;;
        8) generate_session ;;
        9) install_dependencies ;;
        10) setup_database ;;
        0) exit 0 ;;
        *) echo "Invalid choice" ;;
    esac
}

# Full deployment
deploy_full() {
    log "Starting full deployment..."
    
    check_prerequisites
    setup_venv
    install_dependencies
    setup_database
    generate_session
    run_migrations
    start_bot
    
    log "✅ Full deployment complete!"
}

# Parse command line arguments
if [ $# -eq 0 ]; then
    show_menu
else
    case "$1" in
        "deploy")
            deploy_full
            ;;
        "start")
            start_bot
            ;;
        "stop")
            stop_bot
            ;;
        "restart")
            restart_bot
            ;;
        "status")
            monitor_bot
            ;;
        "backup")
            backup_data
            ;;
        "logs")
            show_logs "$2"
            ;;
        "session")
            generate_session
            ;;
        "install")
            install_dependencies
            ;;
        "setup-db")
            setup_database
            ;;
        *)
            echo "Usage: $0 {deploy|start|stop|restart|status|backup|logs|session|install|setup-db}"
            exit 1
            ;;
    esac
fi