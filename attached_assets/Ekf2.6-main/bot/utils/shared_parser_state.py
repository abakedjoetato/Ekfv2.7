"""
Shared Parser State Management
Coordinates state between historical and killfeed parsers to ensure seamless data continuity
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ParserState:
    """Represents the parsing state for a specific server"""
    guild_id: int
    server_name: str
    last_file: str
    last_line: int
    last_byte_position: int
    last_update_time: datetime
    updated_by_parser: str  # 'historical' or 'killfeed'
    file_timestamp: Optional[str] = None

class SharedParserStateManager:
    """Manages shared state between historical and killfeed parsers"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.state_lock = asyncio.Lock()
    
    def _get_server_key(self, guild_id: int, server_name: str) -> str:
        """Generate unique key for server identification"""
        return f"{guild_id}_{server_name}"
    
    async def is_server_locked(self, guild_id: int, server_name: str) -> bool:
        """Check if server is currently being processed by historical parser"""
        server_key = self._get_server_key(guild_id, server_name)
        
        async with self.state_lock:
            if server_key in self.active_sessions:
                session = self.active_sessions[server_key]
                # Check if session is still active (not timed out)
                if session['parser_type'] == 'historical':
                    session_age = (datetime.now(timezone.utc) - session['start_time']).total_seconds()
                    if session_age < 3600:  # 1 hour timeout
                        return True
                    else:
                        # Clean up stale session
                        del self.active_sessions[server_key]
        
        return False
    
    async def register_session(self, guild_id: int, server_name: str, parser_type: str) -> bool:
        """Register an active parsing session for a server"""
        server_key = self._get_server_key(guild_id, server_name)
        
        async with self.state_lock:
            if server_key in self.active_sessions:
                existing = self.active_sessions[server_key]
                session_age = (datetime.now(timezone.utc) - existing['start_time']).total_seconds()
                if session_age < 3600:  # Still active
                    return False
            
            self.active_sessions[server_key] = {
                'guild_id': guild_id,
                'server_name': server_name,
                'parser_type': parser_type,
                'start_time': datetime.now(timezone.utc)
            }
            return True
    
    async def unregister_session(self, guild_id: int, server_name: str, parser_type: str):
        """Unregister a parsing session when complete"""
        server_key = self._get_server_key(guild_id, server_name)
        
        async with self.state_lock:
            if server_key in self.active_sessions:
                session = self.active_sessions[server_key]
                if session['parser_type'] == parser_type:
                    del self.active_sessions[server_key]
    
    async def get_parser_state(self, guild_id: int, server_name: str) -> Optional[ParserState]:
        """Get the current parsing state for a server using direct database connection"""
        try:
            # Use direct MongoDB connection for thread safety
            import os
            from motor.motor_asyncio import AsyncIOMotorClient
            
            mongo_uri = os.environ.get('MONGO_URI')
            if not mongo_uri:
                logger.error("MONGO_URI not available")
                return None
            
            client = AsyncIOMotorClient(mongo_uri)
            database = client.emerald_killfeed
            collection = database.shared_parser_states
            
            state_doc = await collection.find_one({
                'guild_id': guild_id,
                'server_name': server_name
            })
            
            try:
                await client.close()
            except Exception:
                pass  # Client may already be closed
            
            if state_doc:
                return ParserState(
                    guild_id=state_doc['guild_id'],
                    server_name=state_doc['server_name'],
                    last_file=state_doc.get('last_file', ''),
                    last_line=state_doc.get('last_line', 0),
                    last_byte_position=state_doc.get('last_byte_position', 0),
                    last_update_time=state_doc.get('last_update_time', datetime.now(timezone.utc)),
                    updated_by_parser=state_doc.get('updated_by_parser', 'unknown'),
                    file_timestamp=state_doc.get('file_timestamp')
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get parser state for {guild_id}/{server_name}: {e}")
            return None
    
    async def update_parser_state(self, guild_id: int, server_name: str, 
                                last_file: str, last_line: int, last_byte_position: int,
                                parser_type: str, file_timestamp: Optional[str] = None) -> bool:
        """Update the parsing state for a server"""
        try:
            # Use direct MongoDB connection for thread safety
            import os
            from motor.motor_asyncio import AsyncIOMotorClient
            
            mongo_uri = os.environ.get('MONGO_URI')
            if not mongo_uri:
                logger.error("MONGO_URI not available")
                return False
            
            client = AsyncIOMotorClient(mongo_uri)
            database = client.emerald_killfeed
            collection = database.shared_parser_states
            
            state_data = {
                'guild_id': guild_id,
                'server_name': server_name,
                'last_file': last_file,
                'last_line': last_line,
                'last_byte_position': last_byte_position,
                'last_update_time': datetime.now(timezone.utc),
                'updated_by_parser': parser_type
            }
            
            if file_timestamp is not None:
                state_data['file_timestamp'] = file_timestamp
            
            await collection.replace_one(
                {'guild_id': guild_id, 'server_name': server_name},
                state_data,
                upsert=True
            )
            
            try:
                await client.close()
            except Exception:
                pass  # Client may already be closed
            logger.debug(f"Updated parser state for {guild_id}/{server_name} by {parser_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update parser state for {guild_id}/{server_name}: {e}")
            return False
    
    async def get_available_servers_for_killfeed(self, server_configs: list) -> list:
        """Filter server configs to exclude those currently under historical processing"""
        available_servers = []
        
        for server_config in server_configs:
            guild_id = server_config.get('guild_id')
            server_name = server_config.get('name', server_config.get('server_name', 'default'))
            
            if not await self.is_server_locked(guild_id, server_name):
                available_servers.append(server_config)
            else:
                logger.info(f"Skipping server {server_name} for guild {guild_id} - under historical processing")
        
        return available_servers
    
    async def cleanup_stale_sessions(self):
        """Clean up sessions that have been running too long"""
        current_time = datetime.now(timezone.utc)
        stale_keys = []
        
        async with self.state_lock:
            for key, session in self.active_sessions.items():
                session_age = (current_time - session['start_time']).total_seconds()
                if session_age > 3600:  # 1 hour timeout
                    stale_keys.append(key)
            
            for key in stale_keys:
                del self.active_sessions[key]
                logger.info(f"Cleaned up stale session: {key}")
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently active sessions for monitoring"""
        return dict(self.active_sessions)

# Global instance to be shared across parsers
shared_state_manager = None

def initialize_shared_state_manager(db_manager):
    """Initialize the global shared state manager"""
    global shared_state_manager
    shared_state_manager = SharedParserStateManager(db_manager)
    return shared_state_manager

def get_shared_state_manager() -> Optional[SharedParserStateManager]:
    """Get the global shared state manager instance"""
    return shared_state_manager