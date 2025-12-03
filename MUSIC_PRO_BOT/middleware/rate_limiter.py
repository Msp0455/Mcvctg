import asyncio
import time
from typing import Dict, List, Optional
from collections import defaultdict
import cachetools

from config import config
from utils.logger import logger
from utils.exceptions import RateLimitError

class RateLimiter:
    """Rate limiter for API calls and commands"""
    
    def __init__(self):
        # User rate limits
        self.user_limits = cachetools.TTLCache(maxsize=10000, ttl=60)
        
        # IP rate limits
        self.ip_limits = cachetools.TTLCache(maxsize=10000, ttl=60)
        
        # API rate limits
        self.api_limits = {
            'youtube': cachetools.TTLCache(maxsize=1000, ttl=60),
            'spotify': cachetools.TTLCache(maxsize=1000, ttl=60),
            'genius': cachetools.TTLCache(maxsize=1000, ttl=60),
            'lastfm': cachetools.TTLCache(maxsize=1000, ttl=60),
        }
        
        # Default limits
        self.default_limits = {
            'user': {
                'commands': 30,  # commands per minute
                'messages': 60,  # messages per minute
            },
            'ip': {
                'requests': 100,  # requests per minute
            },
            'api': {
                'youtube': 100,  # YouTube API calls per minute
                'spotify': 50,   # Spotify API calls per minute
                'genius': 30,    # Genius API calls per minute
                'lastfm': 30,    # Last.fm API calls per minute
            }
        }
    
    async def check_user_limit(self, user_id: int, action: str = 'commands') -> bool:
        """Check if user has exceeded rate limit"""
        cache_key = f"user:{user_id}:{action}"
        current_time = time.time()
        
        # Get current usage
        usage = self.user_limits.get(cache_key, [])
        
        # Remove old entries (older than 60 seconds)
        usage = [t for t in usage if current_time - t < 60]
        
        # Check limit
        limit = self.default_limits['user'].get(action, 30)
        if len(usage) >= limit:
            wait_time = 60 - (current_time - usage[0])
            raise RateLimitError(
                f"Rate limit exceeded. Please wait {int(wait_time)} seconds."
            )
        
        # Add current request
        usage.append(current_time)
        self.user_limits[cache_key] = usage
        
        return True
    
    async def check_ip_limit(self, ip_address: str) -> bool:
        """Check if IP has exceeded rate limit"""
        cache_key = f"ip:{ip_address}"
        current_time = time.time()
        
        # Get current usage
        usage = self.ip_limits.get(cache_key, [])
        
        # Remove old entries
        usage = [t for t in usage if current_time - t < 60]
        
        # Check limit
        limit = self.default_limits['ip']['requests']
        if len(usage) >= limit:
            wait_time = 60 - (current_time - usage[0])
            raise RateLimitError(
                f"Too many requests from your IP. Please wait {int(wait_time)} seconds."
            )
        
        # Add current request
        usage.append(current_time)
        self.ip_limits[cache_key] = usage
        
        return True
    
    async def check_api_limit(self, api_name: str, endpoint: str = None) -> bool:
        """Check if API rate limit is exceeded"""
        if api_name not in self.api_limits:
            return True
        
        cache_key = f"api:{api_name}:{endpoint}" if endpoint else f"api:{api_name}"
        current_time = time.time()
        
        # Get current usage
        usage = self.api_limits[api_name].get(cache_key, [])
        
        # Remove old entries
        usage = [t for t in usage if current_time - t < 60]
        
        # Check limit
        limit = self.default_limits['api'].get(api_name, 30)
        if len(usage) >= limit:
            wait_time = 60 - (current_time - usage[0])
            logger.warning(
                f"API rate limit exceeded: {api_name}",
                endpoint=endpoint,
                wait_time=wait_time,
            )
            raise RateLimitError(
                f"API rate limit exceeded. Please wait {int(wait_time)} seconds."
            )
        
        # Add current request
        usage.append(current_time)
        self.api_limits[api_name][cache_key] = usage
        
        return True
    
    async def reset_user_limit(self, user_id: int, action: str = None):
        """Reset rate limit for user"""
        if action:
            cache_key = f"user:{user_id}:{action}"
            self.user_limits.pop(cache_key, None)
        else:
            # Remove all limits for user
            keys_to_remove = []
            for key in self.user_limits:
                if key.startswith(f"user:{user_id}:"):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self.user_limits.pop(key, None)
    
    async def reset_ip_limit(self, ip_address: str):
        """Reset rate limit for IP"""
        cache_key = f"ip:{ip_address}"
        self.ip_limits.pop(cache_key, None)
    
    async def reset_api_limit(self, api_name: str, endpoint: str = None):
        """Reset rate limit for API"""
        if api_name in self.api_limits:
            if endpoint:
                cache_key = f"api:{api_name}:{endpoint}"
                self.api_limits[api_name].pop(cache_key, None)
            else:
                self.api_limits[api_name].clear()
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Get rate limit statistics for user"""
        stats = {}
        
        for action in ['commands', 'messages']:
            cache_key = f"user:{user_id}:{action}"
            usage = self.user_limits.get(cache_key, [])
            current_time = time.time()
            
            # Count recent requests
            recent_usage = [t for t in usage if current_time - t < 60]
            limit = self.default_limits['user'].get(action, 30)
            
            stats[action] = {
                'used': len(recent_usage),
                'limit': limit,
                'remaining': max(0, limit - len(recent_usage)),
            }
        
        return stats
    
    async def get_api_stats(self, api_name: str) -> Dict:
        """Get rate limit statistics for API"""
        if api_name not in self.api_limits:
            return {}
        
        current_time = time.time()
        total_requests = 0
        
        for usage_list in self.api_limits[api_name].values():
            if isinstance(usage_list, list):
                recent_usage = [t for t in usage_list if current_time - t < 60]
                total_requests += len(recent_usage)
        
        limit = self.default_limits['api'].get(api_name, 30)
        
        return {
            'used': total_requests,
            'limit': limit,
            'remaining': max(0, limit - total_requests),
        }

# Global rate limiter instance
rate_limiter = RateLimiter()
