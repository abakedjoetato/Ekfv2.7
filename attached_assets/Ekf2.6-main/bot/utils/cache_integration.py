"""
Cache Integration Layer - Seamless Database/Cache Interface
Provides transparent caching for all database operations
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from .unified_cache import get_cache

logger = logging.getLogger(__name__)

class CachedDatabaseManager:
    """
    Wrapper around database manager that provides transparent caching
    All database operations automatically use cache when possible
    """
    
    def __init__(self, database_manager):
        self.db = database_manager
        self.cache = get_cache()
    
    # ===============================
    # PREMIUM SYSTEM CACHING
    # ===============================
    
    async def is_premium_server(self, guild_id: int, server_id: str) -> bool:
        """Check if server is premium (cached)"""
        # Try cache first
        premium_data = await self.cache.get_premium_status(guild_id)
        if premium_data:
            return server_id in premium_data.get('premium_servers', set())
        
        # Cache miss - load from database
        is_premium = await self.db.is_premium_server(guild_id, server_id)
        
        # Update cache with fresh data
        await self._refresh_premium_cache(guild_id)
        
        return is_premium
    
    async def has_premium_access(self, guild_id: int, server_id: Optional[str] = None) -> bool:
        """Check premium access (cached)"""
        premium_data = await self.cache.get_premium_status(guild_id)
        
        if premium_data:
            if server_id:
                return server_id in premium_data.get('premium_servers', set())
            else:
                return len(premium_data.get('premium_servers', set())) > 0
        
        # Cache miss - load and cache
        await self._refresh_premium_cache(guild_id)
        return await self.has_premium_access(guild_id, server_id)
    
    async def _refresh_premium_cache(self, guild_id: int) -> None:
        """Refresh premium cache for guild"""
        try:
            # Get premium servers from database
            premium_servers = set()
            limit = 0
            
            # Load active premium servers
            if hasattr(self.db, 'client'):
                premium_docs = await self.db.client.emerald_killfeed.server_premium_status.find({
                    'guild_id': guild_id,
                    'is_active': True
                }).to_list(None)
                
                premium_servers = {doc['server_id'] for doc in premium_docs}
                
                # Get premium limit
                limit_doc = await self.db.client.emerald_killfeed.premium_limits.find_one({
                    'guild_id': guild_id
                })
                if limit_doc:
                    limit = limit_doc.get('limit', limit_doc.get('max_premium_servers', 0))
            
            # Cache the data
            premium_data = {
                'premium_servers': premium_servers,
                'limit': limit,
                'active_count': len(premium_servers)
            }
            
            await self.cache.set_premium_status(guild_id, premium_data)
            logger.debug(f"Refreshed premium cache for guild {guild_id}: {len(premium_servers)} servers")
            
        except Exception as e:
            logger.error(f"Error refreshing premium cache for guild {guild_id}: {e}")
    
    # ===============================
    # GUILD CONFIGURATION CACHING
    # ===============================
    
    async def get_guild_config(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get guild configuration (cached)"""
        # Try cache first
        config = await self.cache.get_guild_config(guild_id)
        if config:
            return config
        
        # Cache miss - load from database
        config = await self.db.get_guild_config(guild_id)
        if config:
            await self.cache.set_guild_config(guild_id, config)
        
        return config
    
    async def update_guild_config(self, guild_id: int, updates: Dict[str, Any]) -> None:
        """Update guild configuration and invalidate cache"""
        await self.db.update_guild_config(guild_id, updates)
        await self.cache.invalidate('guild_config', f"guild_{guild_id}")
    
    # ===============================
    # PLAYER STATISTICS CACHING
    # ===============================
    
    async def get_player_stats(self, guild_id: int, player_name: str, server_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get player statistics (cached)"""
        # Try cache first
        stats = await self.cache.get_player_stats(guild_id, player_name, server_id)
        if stats:
            return stats
        
        # Cache miss - load from database
        stats = await self.db.get_player_stats(guild_id, player_name, server_id)
        if stats:
            await self.cache.set_player_stats(guild_id, player_name, stats, server_id)
        
        return stats
    
    async def update_player_stats(self, guild_id: int, player_name: str, stats_update: Dict[str, Any], server_id: Optional[str] = None) -> None:
        """Update player statistics and invalidate cache"""
        await self.db.update_player_stats(guild_id, player_name, stats_update, server_id)
        
        # Invalidate related caches
        await self.cache.invalidate_player_data(guild_id, player_name)
    
    # ===============================
    # LEADERBOARD CACHING
    # ===============================
    
    async def get_top_players(self, guild_id: int, stat_type: str, limit: int = 10, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get top players leaderboard (cached)"""
        # Try cache first
        leaderboard = await self.cache.get_leaderboard(guild_id, stat_type, server_id)
        if leaderboard:
            return leaderboard[:limit]
        
        # Cache miss - compute and cache
        leaderboard = await self._compute_leaderboard(guild_id, stat_type, server_id)
        if leaderboard:
            await self.cache.set_leaderboard(guild_id, stat_type, leaderboard, server_id)
        
        return leaderboard[:limit] if leaderboard else []
    
    async def _compute_leaderboard(self, guild_id: int, stat_type: str, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Compute leaderboard from database"""
        try:
            if stat_type == 'kills':
                return await self.db.get_top_kills(guild_id, 50, server_id)
            elif stat_type == 'deaths':
                return await self.db.get_top_deaths(guild_id, 50, server_id)
            elif stat_type == 'kdr':
                return await self.db.get_top_kdr(guild_id, 50, server_id)
            elif stat_type == 'distance':
                return await self.db.get_top_distance(guild_id, 50, server_id)
            else:
                return []
        except Exception as e:
            logger.error(f"Error computing {stat_type} leaderboard for guild {guild_id}: {e}")
            return []
    
    # ===============================
    # ECONOMY DATA CACHING
    # ===============================
    
    async def get_user_balance(self, guild_id: int, user_id: int) -> int:
        """Get user balance (cached)"""
        # Try cache first
        economy_data = await self.cache.get('economy_data', f"guild_{guild_id}_user_{user_id}")
        if economy_data:
            return economy_data.get('balance', 0)
        
        # Cache miss - load from database
        balance = await self.db.get_user_balance(guild_id, user_id)
        
        # Cache the balance
        economy_data = {'balance': balance}
        await self.cache.set('economy_data', f"guild_{guild_id}_user_{user_id}", economy_data)
        
        return balance
    
    async def update_user_balance(self, guild_id: int, user_id: int, amount: int, operation: str = 'add') -> int:
        """Update user balance and invalidate cache"""
        new_balance = await self.db.update_user_balance(guild_id, user_id, amount, operation)
        
        # Invalidate cache
        await self.cache.invalidate('economy_data', f"guild_{guild_id}_user_{user_id}")
        
        return new_balance
    
    # ===============================
    # FACTION DATA CACHING
    # ===============================
    
    async def get_faction_stats(self, guild_id: int, server_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get faction statistics (cached)"""
        # Try cache first
        faction_data = await self.cache.get('faction_data', f"guild_{guild_id}_server_{server_id or 'all'}")
        if faction_data:
            return faction_data
        
        # Cache miss - load from database
        faction_stats = await self.db.get_faction_stats(guild_id, server_id)
        if faction_stats:
            await self.cache.set('faction_data', f"guild_{guild_id}_server_{server_id or 'all'}", faction_stats)
        
        return faction_stats or []
    
    # ===============================
    # SERVER INFORMATION CACHING
    # ===============================
    
    async def get_server_info(self, guild_id: int, server_id: str) -> Optional[Dict[str, Any]]:
        """Get server information (cached)"""
        # Try cache first
        server_info = await self.cache.get('server_info', f"guild_{guild_id}_server_{server_id}")
        if server_info:
            return server_info
        
        # Cache miss - load from database
        server_info = await self.db.get_server_info(guild_id, server_id)
        if server_info:
            await self.cache.set('server_info', f"guild_{guild_id}_server_{server_id}", server_info)
        
        return server_info
    
    # ===============================
    # CACHE MANAGEMENT
    # ===============================
    
    async def invalidate_all_cache(self, guild_id: int) -> None:
        """Invalidate all cache for a guild"""
        await self.cache.invalidate_guild_data(guild_id)
    
    async def invalidate_premium_cache(self, guild_id: int) -> None:
        """Invalidate premium cache for a guild"""
        await self.cache.invalidate('premium', f"guild_{guild_id}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        return await self.cache.get_stats()
    
    async def cleanup_cache(self) -> int:
        """Clean up expired cache entries"""
        return await self.cache.cleanup_expired()
    
    # ===============================
    # PASSTHROUGH METHODS
    # ===============================
    
    def __getattr__(self, name):
        """Pass through any missing methods to the underlying database manager with timeout protection"""
        attr = getattr(self.db, name)
        
        # If it's a callable method, wrap it with timeout protection
        if callable(attr):
            async def wrapped_method(*args, **kwargs):
                try:
                    if asyncio.iscoroutinefunction(attr):
                        return await asyncio.wait_for(attr(*args, **kwargs), timeout=10.0)
                    else:
                        return attr(*args, **kwargs)
                except asyncio.TimeoutError:
                    logger.error(f"Database operation {name} timed out")
                    raise
                except Exception as e:
                    logger.error(f"Database operation {name} failed: {e}")
                    raise
            
            # Return the wrapped method if it's async, otherwise return as-is
            if asyncio.iscoroutinefunction(attr):
                return wrapped_method
        
        return attr


def create_cached_database_manager(database_manager):
    """Create a cached database manager wrapper"""
    return CachedDatabaseManager(database_manager)