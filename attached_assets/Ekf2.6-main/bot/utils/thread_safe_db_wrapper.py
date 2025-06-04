"""
Thread-Safe Database Wrapper
Prevents "Future attached to a different loop" errors by ensuring database operations
execute in the correct asyncio event loop context
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Optional
from functools import wraps
import threading

logger = logging.getLogger(__name__)

class ThreadSafeDBWrapper:
    """Wrapper that ensures database operations execute in the correct event loop"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self._main_loop = None
        self._thread_local = threading.local()
    
    def set_main_loop(self, loop):
        """Set the main event loop for thread-safe operations"""
        self._main_loop = loop
        logger.info(f"Main event loop set: {id(loop)}")
    
    def _get_current_loop_info(self):
        """Get current loop information safely"""
        try:
            current_loop = asyncio.get_running_loop()
            return current_loop, id(current_loop)
        except RuntimeError:
            return None, None
    
    async def safe_db_operation(self, operation: Callable, *args, **kwargs):
        """Execute database operation safely, handling thread boundary issues"""
        try:
            current_loop, current_id = self._get_current_loop_info()
            main_id = id(self._main_loop) if self._main_loop else None
            
            logger.debug(f"DB operation {operation.__name__}: current_loop={current_id}, main_loop={main_id}")
            
            # If we're in a different thread/loop and have a main loop
            if self._main_loop and current_loop and current_loop != self._main_loop:
                logger.debug(f"Cross-thread operation detected for {operation.__name__}")
                
                if asyncio.iscoroutinefunction(operation):
                    # Create a new task in the main loop
                    async def _execute_in_main():
                        try:
                            return await operation(*args, **kwargs)
                        except Exception as e:
                            logger.error(f"Main loop execution failed for {operation.__name__}: {e}")
                            raise
                    
                    # Submit to main loop
                    future = asyncio.run_coroutine_threadsafe(_execute_in_main(), self._main_loop)
                    return future.result(timeout=30)
                else:
                    # For non-coroutine functions, execute directly
                    return operation(*args, **kwargs)
            
            # We're in the correct loop or no main loop conflict
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **kwargs)
            else:
                return operation(*args, **kwargs)
                
        except asyncio.TimeoutError:
            logger.error(f"Database operation {operation.__name__} timed out after 30 seconds")
            return None
        except Exception as e:
            logger.error(f"Database operation {operation.__name__} failed: {e}")
            return None
    
    async def get_guild(self, guild_id: int):
        """Thread-safe guild retrieval"""
        return await self.safe_db_operation(self.db_manager.get_guild, guild_id)
    
    async def get_guild_servers(self, guild_id: int):
        """Thread-safe guild servers retrieval"""
        if hasattr(self.db_manager, 'get_guild_servers'):
            return await self.safe_db_operation(self.db_manager.get_guild_servers, guild_id)
        return []
    
    async def get_active_player_count(self, guild_id: int, server_name: str):
        """Thread-safe player count retrieval"""
        if hasattr(self.db_manager, 'get_active_player_count'):
            return await self.safe_db_operation(
                self.db_manager.get_active_player_count, 
                guild_id, 
                server_name
            )
        return 0
    
    async def update_player_session(self, *args, **kwargs):
        """Thread-safe player session update"""
        if hasattr(self.db_manager, 'update_player_session'):
            return await self.safe_db_operation(
                self.db_manager.update_player_session, 
                *args, 
                **kwargs
            )
        return None
    
    async def reset_player_sessions(self, *args, **kwargs):
        """Thread-safe player session reset"""
        if hasattr(self.db_manager, 'reset_player_sessions_for_server'):
            return await self.safe_db_operation(
                self.db_manager.reset_player_sessions_for_server, 
                *args, 
                **kwargs
            )
        return None

    @property
    def player_sessions(self):
        """Thread-safe access to player_sessions collection"""
        return self.db_manager.player_sessions if self.db_manager else None
    
    async def record_kill(self, *args, **kwargs):
        """Thread-safe kill recording"""
        try:
            if hasattr(self.db_manager, 'record_kill'):
                return await self.safe_db_operation(
                    self.db_manager.record_kill, 
                    *args, 
                    **kwargs
                )
            return None
        except Exception as e:
            logger.error(f"Failed to record kill: {e}")
            return None
    
    async def update_parser_state(self, *args, **kwargs):
        """Thread-safe parser state update"""
        try:
            if hasattr(self.db_manager, 'update_parser_state'):
                return await self.safe_db_operation(
                    self.db_manager.update_parser_state, 
                    *args, 
                    **kwargs
                )
            return None
        except Exception as e:
            logger.error(f"Failed to update parser state: {e}")
            return None
