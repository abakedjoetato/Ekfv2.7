"""
Player Lifecycle Manager
Handles player state tracking and session management
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PlayerLifecycleManager:
    """Manages player lifecycle states and sessions"""
    
    def __init__(self):
        self.player_lifecycle: Dict[str, Dict] = {}
        self.player_sessions: Dict[str, Dict] = {}
        
    def get_lifecycle_key(self, guild_id: int, player_id: str) -> str:
        """Generate lifecycle tracking key"""
        return f"{guild_id}_{player_id}"
        
    def update_player_queue(self, guild_id: int, player_id: str, 
                           player_name: str, platform: str, timestamp: datetime):
        """Update player queue state"""
        lifecycle_key = self.get_lifecycle_key(guild_id, player_id)
        
        self.player_lifecycle[lifecycle_key] = {
            'name': player_name,
            'platform': platform,
            'state': 'queued',
            'queued_at': timestamp.isoformat()
        }
        
        logger.debug(f"Player queued: {player_id} -> '{player_name}' on {platform}")
        
    def update_player_join(self, guild_id: int, player_id: str, 
                          server_id: str, timestamp: datetime) -> Dict[str, Any]:
        """Update player join state and return session data"""
        lifecycle_key = self.get_lifecycle_key(guild_id, player_id)
        session_key = self.get_lifecycle_key(guild_id, player_id)
        
        # Get player data from lifecycle
        lifecycle_data = self.player_lifecycle.get(lifecycle_key, {})
        player_name = lifecycle_data.get('name', f"Player{player_id[:8].upper()}")
        platform = lifecycle_data.get('platform', 'Unknown')
        
        # Update lifecycle state
        if lifecycle_key in self.player_lifecycle:
            self.player_lifecycle[lifecycle_key]['state'] = 'joined'
            self.player_lifecycle[lifecycle_key]['joined_at'] = timestamp.isoformat()
        else:
            # Player joined without queue data
            self.player_lifecycle[lifecycle_key] = {
                'name': player_name,
                'platform': platform,
                'state': 'joined',
                'joined_at': timestamp.isoformat()
            }
            
        # Create session data
        session_data = {
            'player_id': player_id,
            'player_name': player_name,
            'platform': platform,
            'guild_id': guild_id,
            'server_id': server_id,
            'joined_at': timestamp.isoformat(),
            'status': 'online'
        }
        
        self.player_sessions[session_key] = session_data
        return session_data
        
    def update_player_disconnect(self, guild_id: int, player_id: str, 
                                timestamp: datetime) -> Optional[Dict[str, Any]]:
        """Update player disconnect state"""
        lifecycle_key = self.get_lifecycle_key(guild_id, player_id)
        session_key = self.get_lifecycle_key(guild_id, player_id)
        
        lifecycle_data = self.player_lifecycle.get(lifecycle_key, {})
        session_data = self.player_sessions.get(session_key, {})
        
        # Check if player was actually online
        if (lifecycle_data.get('state') == 'joined' or 
            session_data.get('status') == 'online'):
            
            player_name = lifecycle_data.get('name') or session_data.get('player_name', f"Player{player_id[:8].upper()}")
            platform = lifecycle_data.get('platform') or session_data.get('platform', 'Unknown')
            
            # Update lifecycle state
            if lifecycle_key in self.player_lifecycle:
                self.player_lifecycle[lifecycle_key]['state'] = 'disconnected'
                self.player_lifecycle[lifecycle_key]['disconnected_at'] = timestamp.isoformat()
                
            # Update session status
            if session_key in self.player_sessions:
                self.player_sessions[session_key]['status'] = 'offline'
                self.player_sessions[session_key]['left_at'] = timestamp.isoformat()
                
            return {
                'player_name': player_name,
                'platform': platform,
                'player_id': player_id
            }
            
        return None
        
    def get_active_players(self, guild_id: int) -> Dict[str, Dict]:
        """Get all active players for a guild"""
        active_players = {}
        
        logger.debug(f"🔍 Checking {len(self.player_sessions)} total sessions for guild {guild_id}")
        
        for key, session in self.player_sessions.items():
            logger.debug(f"🔍 Session {key}: guild={session.get('guild_id')}, status={session.get('status')}")
            if (session.get('guild_id') == guild_id and 
                session.get('status') == 'online'):
                active_players[key] = session
                logger.debug(f"🔍 Added active player: {session.get('player_name')} on server {session.get('server_id')}")
                
        logger.debug(f"🔍 Found {len(active_players)} active players for guild {guild_id}")
        return active_players
        
    def clear_guild_sessions(self, guild_id: int):
        """Clear all sessions for a guild (cold start)"""
        keys_to_remove = []
        
        for key in self.player_lifecycle:
            if key.startswith(f"{guild_id}_"):
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.player_lifecycle[key]
            
        keys_to_remove = []
        for key in self.player_sessions:
            if key.startswith(f"{guild_id}_"):
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            del self.player_sessions[key]