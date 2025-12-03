import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import motor.motor_asyncio
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, IndexModel, TEXT
from pymongo.errors import DuplicateKeyError, ConnectionFailure

from config import config
from utils.logger import logger
from utils.exceptions import DatabaseError

class MongoDBManager:
    """MongoDB database manager"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.connected = False
        
        # Collections
        self.users = None
        self.chats = None
        self.tracks = None
        self.playlists = None
        self.queue = None
        self.history = None
        self.stats = None
        self.settings = None
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            logger.info(f"Connecting to MongoDB: {config.database.mongodb_uri}")
            
            self.client = motor.motor_asyncio.AsyncIOMotorClient(
                config.database.mongodb_uri,
                maxPoolSize=100,
                minPoolSize=10,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                serverSelectionTimeoutMS=10000,
            )
            
            # Test connection
            await self.client.admin.command('ping')
            
            self.db = self.client[config.database.database_name]
            
            # Initialize collections
            await self._init_collections()
            
            # Create indexes
            await self._create_indexes()
            
            self.connected = True
            logger.info("✅ MongoDB connected successfully")
            
        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise DatabaseError(f"Failed to connect to MongoDB: {str(e)}")
        except Exception as e:
            logger.error(f"MongoDB initialization error: {e}")
            raise DatabaseError(f"MongoDB error: {str(e)}")
    
    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("MongoDB disconnected")
    
    async def _init_collections(self):
        """Initialize all collections"""
        self.users = self.db.users
        self.chats = self.db.chats
        self.tracks = self.db.tracks
        self.playlists = self.db.playlists
        self.queue = self.db.queue
        self.history = self.db.history
        self.stats = self.db.stats
        self.settings = self.db.settings
    
    async def _create_indexes(self):
        """Create database indexes"""
        try:
            # Users collection indexes
            await self.users.create_indexes([
                IndexModel([("user_id", ASCENDING)], unique=True),
                IndexModel([("username", ASCENDING)], sparse=True),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("last_active", DESCENDING)]),
            ])
            
            # Chats collection indexes
            await self.chats.create_indexes([
                IndexModel([("chat_id", ASCENDING)], unique=True),
                IndexModel([("type", ASCENDING)]),
                IndexModel([("active", ASCENDING)]),
                IndexModel([("last_activity", DESCENDING)]),
            ])
            
            # Tracks collection indexes
            await self.tracks.create_indexes([
                IndexModel([("track_id", ASCENDING)], unique=True),
                IndexModel([("source", ASCENDING)]),
                IndexModel([("artist", TEXT), ("title", TEXT)], weights={"artist": 2, "title": 1}),
                IndexModel([("play_count", DESCENDING)]),
                IndexModel([("last_played", DESCENDING)]),
                IndexModel([("duration", ASCENDING)]),
            ])
            
            # Playlists collection indexes
            await self.playlists.create_indexes([
                IndexModel([("playlist_id", ASCENDING)], unique=True),
                IndexModel([("user_id", ASCENDING)]),
                IndexModel([("name", TEXT)]),
                IndexModel([("created_at", DESCENDING)]),
                IndexModel([("public", ASCENDING)]),
            ])
            
            # Queue collection indexes
            await self.queue.create_indexes([
                IndexModel([("chat_id", ASCENDING)]),
                IndexModel([("position", ASCENDING)]),
                IndexModel([("added_at", ASCENDING)]),
                IndexModel([("status", ASCENDING)]),
            ])
            
            # History collection indexes
            await self.history.create_indexes([
                IndexModel([("chat_id", ASCENDING), ("played_at", DESCENDING)]),
                IndexModel([("user_id", ASCENDING)]),
                IndexModel([("track_id", ASCENDING)]),
                IndexModel([("played_at", DESCENDING)]),
            ])
            
            # Stats collection indexes
            await self.stats.create_indexes([
                IndexModel([("date", ASCENDING)], unique=True),
                IndexModel([("type", ASCENDING)]),
            ])
            
            logger.info("Database indexes created")
            
        except Exception as e:
            logger.error(f"Failed to create indexes: {e}")
    
    # User operations
    async def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        try:
            user = await self.users.find_one({"user_id": user_id})
            return self._convert_objectid(user) if user else None
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            return None
    
    async def create_user(self, user_data: Dict) -> bool:
        """Create new user"""
        try:
            user_data["created_at"] = datetime.utcnow()
            user_data["last_active"] = datetime.utcnow()
            
            await self.users.insert_one(user_data)
            return True
        except DuplicateKeyError:
            logger.warning(f"User {user_data.get('user_id')} already exists")
            return False
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    async def update_user(self, user_id: int, update_data: Dict) -> bool:
        """Update user data"""
        try:
            update_data["last_active"] = datetime.utcnow()
            
            result = await self.users.update_one(
                {"user_id": user_id},
                {"$set": update_data},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return False
    
    async def update_user_stats(self, user_id: int, 
                               tracks_played: int = 1,
                               time_listened: int = 0) -> bool:
        """Update user statistics"""
        try:
            result = await self.users.update_one(
                {"user_id": user_id},
                {
                    "$inc": {
                        "stats.tracks_played": tracks_played,
                        "stats.time_listened": time_listened,
                    },
                    "$set": {"last_active": datetime.utcnow()}
                },
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Failed to update user stats {user_id}: {e}")
            return False
    
    async def get_top_users(self, limit: int = 10) -> List[Dict]:
        """Get top users by tracks played"""
        try:
            pipeline = [
                {"$match": {"stats.tracks_played": {"$exists": True}}},
                {"$sort": {"stats.tracks_played": DESCENDING}},
                {"$limit": limit},
                {"$project": {
                    "user_id": 1,
                    "first_name": 1,
                    "username": 1,
                    "tracks_played": "$stats.tracks_played",
                    "time_listened": "$stats.time_listened",
                    "last_active": 1,
                }}
            ]
            
            cursor = self.users.aggregate(pipeline)
            users = await cursor.to_list(length=limit)
            return [self._convert_objectid(user) for user in users]
        except Exception as e:
            logger.error(f"Failed to get top users: {e}")
            return []
    
    # Chat operations
    async def get_chat(self, chat_id: int) -> Optional[Dict]:
        """Get chat by ID"""
        try:
            chat = await self.chats.find_one({"chat_id": chat_id})
            return self._convert_objectid(chat) if chat else None
        except Exception as e:
            logger.error(f"Failed to get chat {chat_id}: {e}")
            return None
    
    async def create_chat(self, chat_data: Dict) -> bool:
        """Create new chat"""
        try:
            chat_data["created_at"] = datetime.utcnow()
            chat_data["last_activity"] = datetime.utcnow()
            chat_data["active"] = True
            
            await self.chats.insert_one(chat_data)
            return True
        except DuplicateKeyError:
            logger.warning(f"Chat {chat_data.get('chat_id')} already exists")
            return False
        except Exception as e:
            logger.error(f"Failed to create chat: {e}")
            return False
    
    async def update_chat(self, chat_id: int, update_data: Dict) -> bool:
        """Update chat data"""
        try:
            update_data["last_activity"] = datetime.utcnow()
            
            result = await self.chats.update_one(
                {"chat_id": chat_id},
                {"$set": update_data},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Failed to update chat {chat_id}: {e}")
            return False
    
    async def update_chat_stats(self, chat_id: int, 
                               tracks_played: int = 1,
                               active_users: int = 0) -> bool:
        """Update chat statistics"""
        try:
            result = await self.chats.update_one(
                {"chat_id": chat_id},
                {
                    "$inc": {
                        "stats.tracks_played": tracks_played,
                        "stats.active_users": active_users,
                    },
                    "$set": {"last_activity": datetime.utcnow()}
                },
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Failed to update chat stats {chat_id}: {e}")
            return False
    
    async def get_active_chats(self, days: int = 7) -> List[Dict]:
        """Get recently active chats"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            cursor = self.chats.find({
                "last_activity": {"$gte": cutoff_date},
                "active": True
            }).sort("last_activity", DESCENDING)
            
            chats = await cursor.to_list(length=100)
            return [self._convert_objectid(chat) for chat in chats]
        except Exception as e:
            logger.error(f"Failed to get active chats: {e}")
            return []
    
    # Track operations
    async def get_track(self, track_id: str) -> Optional[Dict]:
        """Get track by ID"""
        try:
            track = await self.tracks.find_one({"track_id": track_id})
            return self._convert_objectid(track) if track else None
        except Exception as e:
            logger.error(f"Failed to get track {track_id}: {e}")
            return None
    
    async def create_track(self, track_data: Dict) -> bool:
        """Create new track"""
        try:
            track_data["created_at"] = datetime.utcnow()
            track_data["last_played"] = None
            track_data["play_count"] = 0
            
            await self.tracks.insert_one(track_data)
            return True
        except DuplicateKeyError:
            logger.warning(f"Track {track_data.get('track_id')} already exists")
            return False
        except Exception as e:
            logger.error(f"Failed to create track: {e}")
            return False
    
    async def update_track_play(self, track_id: str) -> bool:
        """Update track play statistics"""
        try:
            result = await self.tracks.update_one(
                {"track_id": track_id},
                {
                    "$inc": {"play_count": 1},
                    "$set": {"last_played": datetime.utcnow()}
                },
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Failed to update track play {track_id}: {e}")
            return False
    
    async def search_tracks(self, query: str, limit: int = 20) -> List[Dict]:
        """Search tracks"""
        try:
            cursor = self.tracks.find(
                {"$text": {"$search": query}},
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            tracks = await cursor.to_list(length=limit)
            return [self._convert_objectid(track) for track in tracks]
        except Exception as e:
            logger.error(f"Failed to search tracks: {e}")
            return []
    
    async def get_popular_tracks(self, limit: int = 20, days: int = 30) -> List[Dict]:
        """Get popular tracks"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            pipeline = [
                {"$match": {"last_played": {"$gte": cutoff_date}}},
                {"$sort": {"play_count": DESCENDING}},
                {"$limit": limit},
                {"$project": {
                    "track_id": 1,
                    "title": 1,
                    "artist": 1,
                    "source": 1,
                    "duration": 1,
                    "play_count": 1,
                    "last_played": 1,
                }}
            ]
            
            cursor = self.tracks.aggregate(pipeline)
            tracks = await cursor.to_list(length=limit)
            return [self._convert_objectid(track) for track in tracks]
        except Exception as e:
            logger.error(f"Failed to get popular tracks: {e}")
            return []
    
    # Playlist operations
    async def get_playlist(self, playlist_id: str) -> Optional[Dict]:
        """Get playlist by ID"""
        try:
            playlist = await self.playlists.find_one({"playlist_id": playlist_id})
            return self._convert_objectid(playlist) if playlist else None
        except Exception as e:
            logger.error(f"Failed to get playlist {playlist_id}: {e}")
            return None
    
    async def create_playlist(self, playlist_data: Dict) -> bool:
        """Create new playlist"""
        try:
            playlist_data["created_at"] = datetime.utcnow()
            playlist_data["updated_at"] = datetime.utcnow()
            playlist_data["track_count"] = len(playlist_data.get("tracks", []))
            
            await self.playlists.insert_one(playlist_data)
            return True
        except DuplicateKeyError:
            logger.warning(f"Playlist {playlist_data.get('playlist_id')} already exists")
            return False
        except Exception as e:
            logger.error(f"Failed to create playlist: {e}")
            return False
    
    async def update_playlist(self, playlist_id: str, update_data: Dict) -> bool:
        """Update playlist"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            
            result = await self.playlists.update_one(
                {"playlist_id": playlist_id},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to update playlist {playlist_id}: {e}")
            return False
    
    async def add_track_to_playlist(self, playlist_id: str, track_data: Dict) -> bool:
        """Add track to playlist"""
        try:
            result = await self.playlists.update_one(
                {"playlist_id": playlist_id},
                {
                    "$push": {"tracks": track_data},
                    "$inc": {"track_count": 1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to add track to playlist {playlist_id}: {e}")
            return False
    
    async def remove_track_from_playlist(self, playlist_id: str, track_id: str) -> bool:
        """Remove track from playlist"""
        try:
            result = await self.playlists.update_one(
                {"playlist_id": playlist_id},
                {
                    "$pull": {"tracks": {"track_id": track_id}},
                    "$inc": {"track_count": -1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Failed to remove track from playlist {playlist_id}: {e}")
            return False
    
    async def get_user_playlists(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user's playlists"""
        try:
            cursor = self.playlists.find(
                {"user_id": user_id}
            ).sort("updated_at", DESCENDING).limit(limit)
            
            playlists = await cursor.to_list(length=limit)
            return [self._convert_objectid(playlist) for playlist in playlists]
        except Exception as e:
            logger.error(f"Failed to get user playlists {user_id}: {e}")
            return []
    
    async def get_public_playlists(self, limit: int = 20) -> List[Dict]:
        """Get public playlists"""
        try:
            cursor = self.playlists.find(
                {"public": True}
            ).sort("updated_at", DESCENDING).limit(limit)
            
            playlists = await cursor.to_list(length=limit)
            return [self._convert_objectid(playlist) for playlist in playlists]
        except Exception as e:
            logger.error(f"Failed to get public playlists: {e}")
            return []
    
    # Queue operations
    async def get_chat_queue(self, chat_id: int) -> List[Dict]:
        """Get queue for chat"""
        try:
            cursor = self.queue.find(
                {"chat_id": chat_id, "status": "pending"}
            ).sort("position", ASCENDING)
            
            queue = await cursor.to_list(length=100)
            return [self._convert_objectid(item) for item in queue]
        except Exception as e:
            logger.error(f"Failed to get chat queue {chat_id}: {e}")
            return []
    
    async def add_to_queue(self, chat_id: int, track_data: Dict, 
                          user_id: int, position: int = None) -> bool:
        """Add track to queue"""
        try:
            # Get next position if not specified
            if position is None:
                last_item = await self.queue.find_one(
                    {"chat_id": chat_id},
                    sort=[("position", DESCENDING)]
                )
                position = last_item["position"] + 1 if last_item else 1
            
            queue_item = {
                "chat_id": chat_id,
                "track": track_data,
                "user_id": user_id,
                "position": position,
                "status": "pending",
                "added_at": datetime.utcnow(),
            }
            
            await self.queue.insert_one(queue_item)
            return True
        except Exception as e:
            logger.error(f"Failed to add to queue: {e}")
            return False
    
    async def remove_from_queue(self, chat_id: int, position: int) -> bool:
        """Remove track from queue"""
        try:
            result = await self.queue.delete_one(
                {"chat_id": chat_id, "position": position}
            )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to remove from queue: {e}")
            return False
    
    async def clear_queue(self, chat_id: int) -> bool:
        """Clear chat queue"""
        try:
            result = await self.queue.delete_many({"chat_id": chat_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to clear queue {chat_id}: {e}")
            return False
    
    async def reorder_queue(self, chat_id: int) -> bool:
        """Reorder queue positions"""
        try:
            # Get all pending items
            items = await self.queue.find(
                {"chat_id": chat_id, "status": "pending"}
            ).sort("position", ASCENDING).to_list(length=100)
            
            # Update positions
            for index, item in enumerate(items, 1):
                await self.queue.update_one(
                    {"_id": item["_id"]},
                    {"$set": {"position": index}}
                )
            
            return True
        except Exception as e:
            logger.error(f"Failed to reorder queue {chat_id}: {e}")
            return False
    
    # History operations
    async def add_to_history(self, chat_id: int, track_data: Dict, 
                            user_id: int) -> bool:
        """Add track to history"""
        try:
            history_item = {
                "chat_id": chat_id,
                "track": track_data,
                "user_id": user_id,
                "played_at": datetime.utcnow(),
            }
            
            await self.history.insert_one(history_item)
            
            # Also update track play count
            await self.update_track_play(track_data.get("track_id"))
            
            return True
        except Exception as e:
            logger.error(f"Failed to add to history: {e}")
            return False
    
    async def get_chat_history(self, chat_id: int, limit: int = 50) -> List[Dict]:
        """Get chat history"""
        try:
            cursor = self.history.find(
                {"chat_id": chat_id}
            ).sort("played_at", DESCENDING).limit(limit)
            
            history = await cursor.to_list(length=limit)
            return [self._convert_objectid(item) for item in history]
        except Exception as e:
            logger.error(f"Failed to get chat history {chat_id}: {e}")
            return []
    
    async def get_user_history(self, user_id: int, limit: int = 50) -> List[Dict]:
        """Get user history"""
        try:
            cursor = self.history.find(
                {"user_id": user_id}
            ).sort("played_at", DESCENDING).limit(limit)
            
            history = await cursor.to_list(length=limit)
            return [self._convert_objectid(item) for item in history]
        except Exception as e:
            logger.error(f"Failed to get user history {user_id}: {e}")
            return []
    
    # Stats operations
    async def get_stats(self) -> Optional[Dict]:
        """Get bot statistics"""
        try:
            stats = await self.stats.find_one({"type": "bot_stats"})
            return self._convert_objectid(stats) if stats else None
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return None
    
    async def save_stats(self, stats_data: Dict) -> bool:
        """Save bot statistics"""
        try:
            stats_data["type"] = "bot_stats"
            stats_data["updated_at"] = datetime.utcnow()
            
            result = await self.stats.update_one(
                {"type": "bot_stats"},
                {"$set": stats_data},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
            return False
    
    async def update_daily_stats(self) -> bool:
        """Update daily statistics"""
        try:
            today = datetime.utcnow().date()
            date_str = today.isoformat()
            
            # Get today's stats
            daily_stats = await self.stats.find_one({
                "type": "daily_stats",
                "date": date_str
            })
            
            if not daily_stats:
                # Create new daily stats
                daily_stats = {
                    "type": "daily_stats",
                    "date": date_str,
                    "tracks_played": 0,
                    "unique_users": 0,
                    "unique_chats": 0,
                    "active_time": 0,
                    "created_at": datetime.utcnow(),
                }
                await self.stats.insert_one(daily_stats)
            
            return True
        except Exception as e:
            logger.error(f"Failed to update daily stats: {e}")
            return False
    
    async def get_daily_stats(self, days: int = 7) -> List[Dict]:
        """Get daily statistics for past days"""
        try:
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).date()
            
            cursor = self.stats.find({
                "type": "daily_stats",
                "date": {"$gte": cutoff_date.isoformat()}
            }).sort("date", ASCENDING)
            
            stats = await cursor.to_list(length=days)
            return [self._convert_objectid(stat) for stat in stats]
        except Exception as e:
            logger.error(f"Failed to get daily stats: {e}")
            return []
    
    # Settings operations
    async def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting value"""
        try:
            setting = await self.settings.find_one({"key": key})
            return setting.get("value", default) if setting else default
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {e}")
            return default
    
    async def set_setting(self, key: str, value: Any) -> bool:
        """Set setting value"""
        try:
            result = await self.settings.update_one(
                {"key": key},
                {"$set": {"value": value, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
            return False
    
    async def delete_setting(self, key: str) -> bool:
        """Delete setting"""
        try:
            result = await self.settings.delete_one({"key": key})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Failed to delete setting {key}: {e}")
            return False
    
    # Utility methods
    def _convert_objectid(self, document: Dict) -> Dict:
        """Convert ObjectId to string in document"""
        if not document:
            return document
        
        if "_id" in document and isinstance(document["_id"], ObjectId):
            document["_id"] = str(document["_id"])
        
        return document
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            if not self.connected:
                return False
            
            # Ping database
            await self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def backup_database(self, backup_path: str) -> bool:
        """Backup database (simplified version)"""
        try:
            # This would typically use mongodump in production
            # For now, just log the backup request
            logger.info(f"Database backup requested: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False
    
    async def cleanup_old_data(self, days: int = 90) -> int:
        """Cleanup old data"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Cleanup old history
            history_result = await self.history.delete_many({
                "played_at": {"$lt": cutoff_date}
            })
            
            # Cleanup old queue items
            queue_result = await self.queue.delete_many({
                "added_at": {"$lt": cutoff_date}
            })
            
            total_deleted = history_result.deleted_count + queue_result.deleted_count
            logger.info(f"Cleaned up {total_deleted} old records")
            
            return total_deleted
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0