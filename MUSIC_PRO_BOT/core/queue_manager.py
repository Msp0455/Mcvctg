import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import random
from collections import deque
import json

from utils.logger import logger
from utils.exceptions import QueueError

class QueueItem:
    """Queue item data class"""
    
    def __init__(self, track: Dict, user_id: int, added_at: datetime = None):
        self.track = track
        self.user_id = user_id
        self.added_at = added_at or datetime.now()
        self.played = False
    
    def to_dict(self) -> Dict:
        return {
            "track": self.track,
            "user_id": self.user_id,
            "added_at": self.added_at.isoformat(),
            "played": self.played,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'QueueItem':
        item = cls(
            track=data["track"],
            user_id=data["user_id"],
            added_at=datetime.fromisoformat(data["added_at"])
        )
        item.played = data.get("played", False)
        return item

class QueueManager:
    """Advanced queue manager with persistence"""
    
    def __init__(self, max_queue_size: int = 100, max_history: int = 50):
        self.max_queue_size = max_queue_size
        self.max_history = max_history
        
        # Chat ID -> Queue
        self.queues: Dict[int, deque] = {}
        self.history: Dict[int, List[QueueItem]] = {}
        
        # Cache for quick access
        self._cache = {}
        
    def add_to_queue(self, chat_id: int, track: Dict, user_id: int) -> bool:
        """Add track to queue"""
        try:
            if chat_id not in self.queues:
                self.queues[chat_id] = deque(maxlen=self.max_queue_size)
            
            if len(self.queues[chat_id]) >= self.max_queue_size:
                raise QueueError(f"Queue is full (max {self.max_queue_size} tracks)")
            
            item = QueueItem(track, user_id)
            self.queues[chat_id].append(item)
            
            logger.debug(f"Added track to queue: {chat_id} - {track.get('title')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add to queue: {e}")
            raise QueueError(f"Failed to add to queue: {str(e)}")
    
    def get_next(self, chat_id: int) -> Optional[QueueItem]:
        """Get next track from queue"""
        if chat_id not in self.queues or not self.queues[chat_id]:
            return None
        
        item = self.queues[chat_id].popleft()
        item.played = True
        
        # Add to history
        self.add_to_history(chat_id, item)
        
        return item
    
    def peek_next(self, chat_id: int) -> Optional[QueueItem]:
        """Peek at next track without removing"""
        if chat_id not in self.queues or not self.queues[chat_id]:
            return None
        
        return self.queues[chat_id][0]
    
    def remove_track(self, chat_id: int, position: int) -> Optional[QueueItem]:
        """Remove track from specific position"""
        if chat_id not in self.queues:
            return None
        
        queue = self.queues[chat_id]
        if position < 0 or position >= len(queue):
            return None
        
        # Convert to list, remove, convert back
        items = list(queue)
        removed_item = items.pop(position)
        self.queues[chat_id] = deque(items, maxlen=self.max_queue_size)
        
        return removed_item
    
    def move_track(self, chat_id: int, from_pos: int, to_pos: int) -> bool:
        """Move track to different position"""
        if chat_id not in self.queues:
            return False
        
        queue = self.queues[chat_id]
        if from_pos < 0 or from_pos >= len(queue) or to_pos < 0 or to_pos >= len(queue):
            return False
        
        items = list(queue)
        item = items.pop(from_pos)
        items.insert(to_pos, item)
        self.queues[chat_id] = deque(items, maxlen=self.max_queue_size)
        
        return True
    
    def shuffle_queue(self, chat_id: int) -> bool:
        """Shuffle queue"""
        if chat_id not in self.queues or len(self.queues[chat_id]) < 2:
            return False
        
        items = list(self.queues[chat_id])
        random.shuffle(items)
        self.queues[chat_id] = deque(items, maxlen=self.max_queue_size)
        
        return True
    
    def clear_queue(self, chat_id: int) -> bool:
        """Clear queue"""
        if chat_id in self.queues:
            self.queues[chat_id].clear()
            return True
        return False
    
    def get_queue(self, chat_id: int, page: int = 1, per_page: int = 10) -> Dict:
        """Get queue with pagination"""
        if chat_id not in self.queues or not self.queues[chat_id]:
            return {
                "items": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
                "pages": 0,
            }
        
        items = list(self.queues[chat_id])
        total = len(items)
        pages = (total + per_page - 1) // per_page
        
        # Validate page
        if page < 1:
            page = 1
        if page > pages:
            page = pages
        
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            "items": [item.to_dict() for item in items[start:end]],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
        }
    
    def add_to_history(self, chat_id: int, item: QueueItem):
        """Add track to history"""
        if chat_id not in self.history:
            self.history[chat_id] = []
        
        self.history[chat_id].append(item)
        
        # Trim history if too long
        if len(self.history[chat_id]) > self.max_history:
            self.history[chat_id] = self.history[chat_id][-self.max_history:]
    
    def get_history(self, chat_id: int, limit: int = 10) -> List[Dict]:
        """Get playback history"""
        if chat_id not in self.history:
            return []
        
        history = self.history[chat_id][-limit:]
        return [item.to_dict() for item in reversed(history)]
    
    def get_queue_size(self, chat_id: int) -> int:
        """Get queue size for chat"""
        if chat_id not in self.queues:
            return 0
        return len(self.queues[chat_id])
    
    def total_queued(self) -> int:
        """Get total queued tracks across all chats"""
        return sum(len(queue) for queue in self.queues.values())
    
    def save_state(self, filepath: str):
        """Save queue state to file"""
        try:
            state = {
                "queues": {
                    chat_id: [item.to_dict() for item in queue]
                    for chat_id, queue in self.queues.items()
                },
                "history": {
                    chat_id: [item.to_dict() for item in history]
                    for chat_id, history in self.history.items()
                }
            }
            
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Queue state saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save queue state: {e}")
    
    def load_state(self, filepath: str):
        """Load queue state from file"""
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            # Load queues
            self.queues = {}
            for chat_id_str, items in state.get("queues", {}).items():
                chat_id = int(chat_id_str)
                self.queues[chat_id] = deque(
                    [QueueItem.from_dict(item) for item in items],
                    maxlen=self.max_queue_size
                )
            
            # Load history
            self.history = {}
            for chat_id_str, items in state.get("history", {}).items():
                chat_id = int(chat_id_str)
                self.history[chat_id] = [
                    QueueItem.from_dict(item) for item in items
                ]
            
            logger.info(f"Queue state loaded from {filepath}")
            
        except FileNotFoundError:
            logger.warning(f"Queue state file not found: {filepath}")
        except Exception as e:
            logger.error(f"Failed to load queue state: {e}")
