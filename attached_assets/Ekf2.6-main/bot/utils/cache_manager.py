"""
Caching Layer Implementation
Multi-level caching for performance optimization
"""

import time
from typing import Any, Dict, Optional

class CacheManager:
    """Multi-level cache manager"""
    
    def __init__(self):
        self.guild_cache: Dict[str, Dict] = {}
        self.player_cache: Dict[str, Dict] = {}
        self.server_cache: Dict[str, Dict] = {}
        self.premium_cache: Dict[str, Dict] = {}
        
        # Cache TTL in seconds
        self.ttl_settings = {
            'guild_config': 3600,  # 1 hour
            'player_stats': 900,   # 15 minutes
            'server_status': 300,  # 5 minutes
            'premium_status': 3600 # 1 hour
        }
        
    async def get(self, cache_type: str, key: str) -> Optional[Any]:
        """Get item from cache"""
        cache = self._get_cache(cache_type)
        
        if key in cache:
            entry = cache[key]
            if time.time() - entry['timestamp'] < self.ttl_settings.get(cache_type, 300):
                return entry['data']
            else:
                # Expired, remove from cache
                del cache[key]
                
        return None
        
    async def set(self, cache_type: str, key: str, data: Any):
        """Set item in cache"""
        cache = self._get_cache(cache_type)
        cache[key] = {
            'data': data,
            'timestamp': time.time()
        }
        
        # Cleanup old entries periodically
        await self._cleanup_expired(cache, cache_type)
        
    def _get_cache(self, cache_type: str) -> Dict:
        """Get appropriate cache dictionary"""
        if cache_type == 'guild_config':
            return self.guild_cache
        elif cache_type == 'player_stats':
            return self.player_cache
        elif cache_type == 'server_status':
            return self.server_cache
        elif cache_type == 'premium_status':
            return self.premium_cache
        else:
            return {}
            
    async def _cleanup_expired(self, cache: Dict, cache_type: str):
        """Remove expired entries from cache"""
        if len(cache) > 1000:
            ttl = self.ttl_settings.get(cache_type, 300)
            current_time = time.time()
            
            expired_keys = [
                key for key, entry in cache.items()
                if current_time - entry['timestamp'] > ttl
            ]
            
            for key in expired_keys:
                del cache[key]
