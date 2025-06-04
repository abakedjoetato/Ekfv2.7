"""
Database Security Manager
Implements guild isolation and audit trails
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class DatabaseSecurityManager:
    """Enforces guild isolation and security patterns"""
    
    def __init__(self, bot):
        self.bot = bot
        
    async def validate_guild_access(self, guild_id: int, operation: str, resource: str) -> bool:
        """Validate guild access to specific resources"""
        try:
            # Log access attempt
            await self.log_access_attempt(guild_id, operation, resource)
            
            # Check if guild exists and is active
            guild_config = await self.bot.db_manager.get_guild(guild_id)
            if not guild_config:
                logger.warning(f"Access denied: Guild {guild_id} not found")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Guild access validation failed: {e}")
            return False
            
    async def log_access_attempt(self, guild_id: int, operation: str, resource: str):
        """Log database access attempts for auditing"""
        try:
            audit_entry = {
                'guild_id': guild_id,
                'operation': operation,
                'resource': resource,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'success': True
            }
            
            # Store in audit collection
            await self.bot.db_manager.add_audit_log(audit_entry)
        except Exception as e:
            logger.error(f"Failed to log access attempt: {e}")
            
    def apply_guild_filter(self, query: Dict[str, Any], guild_id: int) -> Dict[str, Any]:
        """Apply guild_id filter to database queries"""
        if isinstance(query, dict):
            query['guild_id'] = guild_id
        return query
        
    async def sanitize_query_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize query parameters to prevent injection"""
        sanitized = {}
        
        for key, value in params.items():
            if isinstance(value, str):
                # Remove potentially dangerous characters
                sanitized_value = value.replace('$', '').replace('{', '').replace('}', '')
                sanitized[key] = sanitized_value
            else:
                sanitized[key] = value
                
        return sanitized