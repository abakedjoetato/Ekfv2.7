"""
Dedicated Killfeed State Manager
Manages parser state specifically for killfeed CSV files, separate from unified parser state
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass
import motor.motor_asyncio
import os

logger = logging.getLogger(__name__)

@dataclass
class KillfeedState:
    """Represents the current state of killfeed parsing for a specific server"""
    guild_id: int
    server_name: str
    last_file: str
    last_line: int
    last_byte_position: int
    last_update: datetime
    file_timestamp: Optional[str] = None

class KillfeedStateManager:
    """Manages parsing state for killfeed CSV files only"""
    
    def __init__(self):
        self.active_sessions: Dict[str, bool] = {}
        self._db = None
    
    @property
    def db(self):
        """Get database connection"""
        if self._db is None:
            mongo_uri = os.getenv('MONGO_URI')
            if mongo_uri:
                client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
                self._db = client.EmeraldDB
        return self._db
    
    def _get_session_key(self, guild_id: int, server_name: str) -> str:
        """Generate unique session key"""
        return f"{guild_id}_{server_name}_killfeed"
    
    async def register_session(self, guild_id: int, server_name: str) -> bool:
        """Register a killfeed parsing session"""
        session_key = self._get_session_key(guild_id, server_name)
        
        if session_key in self.active_sessions:
            logger.warning(f"Killfeed session already active for {server_name} in guild {guild_id}")
            return False
        
        self.active_sessions[session_key] = True
        logger.debug(f"Registered killfeed session: {session_key}")
        return True
    
    async def unregister_session(self, guild_id: int, server_name: str):
        """Unregister a killfeed parsing session"""
        session_key = self._get_session_key(guild_id, server_name)
        self.active_sessions.pop(session_key, None)
        logger.debug(f"Unregistered killfeed session: {session_key}")
    
    async def get_killfeed_state(self, guild_id: int, server_name: str) -> Optional[KillfeedState]:
        """Get current killfeed state for a server"""
        try:
            if self.db is None:
                logger.error("Database connection not available")
                return None
                
            # Look for killfeed-specific state document
            state_doc = await self.db.killfeed_states.find_one({
                "guild_id": guild_id,
                "server_name": server_name
            })
            
            if not state_doc:
                logger.debug(f"No killfeed state found for {server_name} in guild {guild_id}")
                return None
            
            return KillfeedState(
                guild_id=state_doc["guild_id"],
                server_name=state_doc["server_name"],
                last_file=state_doc["last_file"],
                last_line=state_doc["last_line"],
                last_byte_position=state_doc["last_byte_position"],
                last_update=state_doc["last_update"],
                file_timestamp=state_doc.get("file_timestamp")
            )
            
        except Exception as e:
            logger.error(f"Failed to get killfeed state for {server_name}: {e}")
            return None
    
    async def update_killfeed_state(self, guild_id: int, server_name: str, 
                                  filename: str, line: int, byte_position: int,
                                  file_timestamp: Optional[str] = None) -> bool:
        """Update killfeed parsing state"""
        try:
            if self.db is None:
                logger.error("Database connection not available for killfeed state update")
                return False
                
            state_data = {
                "guild_id": guild_id,
                "server_name": server_name,
                "last_file": filename,
                "last_line": line,
                "last_byte_position": byte_position,
                "last_update": datetime.now(timezone.utc),
                "file_timestamp": file_timestamp
            }
            
            # Upsert the state document
            await self.db.killfeed_states.update_one(
                {"guild_id": guild_id, "server_name": server_name},
                {"$set": state_data},
                upsert=True
            )
            
            logger.debug(f"Updated killfeed state for {server_name}: {filename} line {line}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update killfeed state for {server_name}: {e}")
            return False
    
    async def reset_killfeed_state(self, guild_id: int, server_name: str) -> bool:
        """Reset killfeed state for a server (force reprocessing)"""
        try:
            if self.db is None:
                logger.error("Database connection not available for killfeed state reset")
                return False
                
            await self.db.killfeed_states.delete_one({
                "guild_id": guild_id,
                "server_name": server_name
            })
            
            logger.info(f"Reset killfeed state for {server_name} in guild {guild_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset killfeed state for {server_name}: {e}")
            return False
    
    async def is_session_active(self, guild_id: int, server_name: str) -> bool:
        """Check if a killfeed parsing session is currently active"""
        session_key = self._get_session_key(guild_id, server_name)
        return session_key in self.active_sessions
    
    async def cleanup_stale_sessions(self):
        """Clean up any stale sessions (should be called periodically)"""
        # For now, just clear all sessions - in production you might want more sophisticated cleanup
        cleared_count = len(self.active_sessions)
        self.active_sessions.clear()
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} potentially stale killfeed sessions")

# Global instance
killfeed_state_manager = KillfeedStateManager()