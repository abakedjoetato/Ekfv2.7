"""
Unified Cache System - Professional Data Layer
Provides comprehensive caching for all bot operations with minimal resource usage
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)

class CacheEntry:
    """Individual cache entry with TTL and metadata"""
    
    def __init__(self, data: Any, ttl: int, cache_type: str):
        self.data = data
        self.created_at = time.time()
        self.ttl = ttl
        self.cache_type = cache_type
        self.access_count = 0
        self.last_accessed = time.time()
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return time.time() - self.created_at > self.ttl
    
    def access(self) -> Any:
        """Access cached data and update statistics"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.data
    
    def get_age(self) -> int:
        """Get age of cache entry in seconds"""
        return int(time.time() - self.created_at)

class UnifiedCache:
    """
    Professional unified cache system for all bot data operations
    
    Features:
    - Multi-tier caching with different TTLs
    - Event-driven invalidation
    - Memory-efficient storage
    - LRU eviction for resource management
    - Comprehensive cache statistics
    """
    
    def __init__(self, max_memory_mb: int = 50):
        # Cache storage by category
        self.caches = {
            'premium': {},      # Premium status (1 hour TTL)
            'guild_config': {}, # Guild configurations (2 hour TTL)
            'player_stats': {}, # Player statistics (30 min TTL)
            'leaderboards': {}, # Computed leaderboards (15 min TTL)
            'player_data': {},  # Active player data (10 min TTL)
            'server_info': {},  # Server information (1 hour TTL)
            'faction_data': {}, # Faction statistics (20 min TTL)
            'economy_data': {}, # Economy balances (5 min TTL)
        }
        
        # Cache configuration
        self.ttl_config = {
            'premium': 3600,      # 1 hour
            'guild_config': 7200, # 2 hours
            'player_stats': 1800, # 30 minutes
            'leaderboards': 900,  # 15 minutes
            'player_data': 600,   # 10 minutes
            'server_info': 3600,  # 1 hour
            'faction_data': 1200, # 20 minutes
            'economy_data': 300,  # 5 minutes
        }
        
        # Memory management
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.max_entries_per_cache = 10000
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'invalidations': 0,
            'memory_usage': 0
        }
        
        # Dependency mapping for invalidation
        self.dependencies = {
            'player_stats': ['leaderboards'],
            'guild_config': ['premium'],
            'premium': ['leaderboards'],
            'faction_data': ['leaderboards'],
        }
        
        # Locks for thread safety
        self._locks = defaultdict(asyncio.Lock)
        
        logger.info("🚀 Unified cache system initialized")
    
    async def get(self, cache_type: str, key: str, default: Any = None) -> Any:
        """Get data from cache with automatic cleanup"""
        async with self._locks[cache_type]:
            cache = self.caches.get(cache_type, {})
            
            if key not in cache:
                self.stats['misses'] += 1
                return default
            
            entry = cache[key]
            
            # Check expiration
            if entry.is_expired():
                del cache[key]
                self.stats['misses'] += 1
                return default
            
            # Return cached data
            self.stats['hits'] += 1
            return entry.access()
    
    async def set(self, cache_type: str, key: str, data: Any, custom_ttl: Optional[int] = None) -> None:
        """Set data in cache with automatic memory management"""
        async with self._locks[cache_type]:
            if cache_type not in self.caches:
                logger.warning(f"Unknown cache type: {cache_type}")
                return
            
            cache = self.caches[cache_type]
            ttl = custom_ttl or self.ttl_config.get(cache_type, 1800)
            
            # Memory management - evict old entries if needed
            await self._evict_if_needed(cache_type)
            
            # Create cache entry
            entry = CacheEntry(data, ttl, cache_type)
            cache[key] = entry
            
            logger.debug(f"Cached {cache_type}:{key} (TTL: {ttl}s)")
    
    async def invalidate(self, cache_type: str, key: Optional[str] = None) -> None:
        """Invalidate cache entries with dependency cascade"""
        async with self._locks[cache_type]:
            cache = self.caches.get(cache_type, {})
            
            if key is None:
                # Clear entire cache type
                cleared_count = len(cache)
                cache.clear()
                logger.info(f"Invalidated entire {cache_type} cache ({cleared_count} entries)")
            else:
                # Clear specific key
                if key in cache:
                    del cache[key]
                    logger.debug(f"Invalidated {cache_type}:{key}")
            
            self.stats['invalidations'] += 1
            
            # Cascade invalidation to dependent caches
            await self._cascade_invalidation(cache_type, key)
    
    async def _cascade_invalidation(self, cache_type: str, key: Optional[str] = None) -> None:
        """Cascade invalidation to dependent cache types"""
        dependent_types = self.dependencies.get(cache_type, [])
        
        for dep_type in dependent_types:
            if key and dep_type == 'leaderboards':
                # For leaderboards, invalidate guild-specific entries
                guild_id = self._extract_guild_id(key)
                if guild_id:
                    await self.invalidate(dep_type, f"guild_{guild_id}")
            else:
                # Full invalidation for other dependencies
                await self.invalidate(dep_type)
    
    def _extract_guild_id(self, key: str) -> Optional[str]:
        """Extract guild ID from cache key"""
        if key.startswith('guild_'):
            return key.split('_')[1]
        return None
    
    async def _evict_if_needed(self, cache_type: str) -> None:
        """Evict oldest entries if cache is too large"""
        cache = self.caches[cache_type]
        max_entries = self.max_entries_per_cache
        
        if len(cache) >= max_entries:
            # Sort by last accessed time (LRU)
            sorted_entries = sorted(
                cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            # Remove oldest 20% of entries
            evict_count = max_entries // 5
            for key, _ in sorted_entries[:evict_count]:
                del cache[key]
                self.stats['evictions'] += 1
            
            logger.info(f"Evicted {evict_count} entries from {cache_type} cache")
    
    async def cleanup_expired(self) -> int:
        """Clean up all expired entries across all caches"""
        total_cleaned = 0
        
        for cache_type, cache in self.caches.items():
            async with self._locks[cache_type]:
                expired_keys = [
                    key for key, entry in cache.items()
                    if entry.is_expired()
                ]
                
                for key in expired_keys:
                    del cache[key]
                    total_cleaned += 1
        
        if total_cleaned > 0:
            logger.info(f"Cleaned up {total_cleaned} expired cache entries")
        
        return total_cleaned
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        total_entries = sum(len(cache) for cache in self.caches.values())
        hit_rate = (
            self.stats['hits'] / (self.stats['hits'] + self.stats['misses'])
            if (self.stats['hits'] + self.stats['misses']) > 0
            else 0
        )
        
        cache_details = {}
        for cache_type, cache in self.caches.items():
            cache_details[cache_type] = {
                'entries': len(cache),
                'avg_age': self._get_average_age(cache),
                'hit_count': sum(entry.access_count for entry in cache.values())
            }
        
        return {
            'total_entries': total_entries,
            'hit_rate': round(hit_rate * 100, 2),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'evictions': self.stats['evictions'],
            'invalidations': self.stats['invalidations'],
            'cache_details': cache_details
        }
    
    def _get_average_age(self, cache: Dict) -> int:
        """Calculate average age of cache entries"""
        if not cache:
            return 0
        
        total_age = sum(entry.get_age() for entry in cache.values())
        return total_age // len(cache)
    
    # ============================
    # SPECIALIZED CACHE METHODS
    # ============================
    
    async def get_premium_status(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get cached premium status for guild"""
        return await self.get('premium', f"guild_{guild_id}")
    
    async def set_premium_status(self, guild_id: int, premium_data: Dict[str, Any]) -> None:
        """Cache premium status for guild"""
        await self.set('premium', f"guild_{guild_id}", premium_data)
    
    async def get_player_stats(self, guild_id: int, player_name: str, server_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached player statistics"""
        key = f"guild_{guild_id}_player_{player_name}"
        if server_id:
            key += f"_server_{server_id}"
        return await self.get('player_stats', key)
    
    async def set_player_stats(self, guild_id: int, player_name: str, stats_data: Dict[str, Any], server_id: Optional[str] = None) -> None:
        """Cache player statistics"""
        key = f"guild_{guild_id}_player_{player_name}"
        if server_id:
            key += f"_server_{server_id}"
        await self.set('player_stats', key, stats_data)
    
    async def get_leaderboard(self, guild_id: int, leaderboard_type: str, server_id: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get cached leaderboard data"""
        key = f"guild_{guild_id}_type_{leaderboard_type}"
        if server_id:
            key += f"_server_{server_id}"
        return await self.get('leaderboards', key)
    
    async def set_leaderboard(self, guild_id: int, leaderboard_type: str, leaderboard_data: List[Dict[str, Any]], server_id: Optional[str] = None) -> None:
        """Cache leaderboard data"""
        key = f"guild_{guild_id}_type_{leaderboard_type}"
        if server_id:
            key += f"_server_{server_id}"
        await self.set('leaderboards', key, leaderboard_data)
    
    async def get_guild_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get cached guild configuration"""
        return await self.get('guild_config', f"guild_{guild_id}")
    
    async def set_guild_config(self, guild_id: int, config_data: Dict[str, Any]) -> None:
        """Cache guild configuration"""
        await self.set('guild_config', f"guild_{guild_id}", config_data)
    
    async def invalidate_player_data(self, guild_id: int, player_name: str) -> None:
        """Invalidate all cached data for a specific player"""
        player_key = f"guild_{guild_id}_player_{player_name}"
        
        # Invalidate player stats
        await self.invalidate('player_stats', player_key)
        
        # Invalidate related leaderboards
        await self.invalidate('leaderboards', f"guild_{guild_id}")
    
    async def invalidate_guild_data(self, guild_id: int) -> None:
        """Invalidate all cached data for a guild"""
        guild_key = f"guild_{guild_id}"
        
        # Invalidate all cache types for this guild
        for cache_type in self.caches.keys():
            # Find all keys containing the guild ID
            cache = self.caches[cache_type]
            guild_keys = [key for key in cache.keys() if guild_key in key]
            
            for key in guild_keys:
                await self.invalidate(cache_type, key)


# Global cache instance
_global_cache = None

def get_cache() -> UnifiedCache:
    """Get the global cache instance"""
    global _global_cache
    if _global_cache is None:
        _global_cache = UnifiedCache()
    return _global_cache

async def initialize_cache() -> UnifiedCache:
    """Initialize the global cache system"""
    global _global_cache
    _global_cache = UnifiedCache()
    logger.info("✅ Global cache system initialized")
    return _global_cache