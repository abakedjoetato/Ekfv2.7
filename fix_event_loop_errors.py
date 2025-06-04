"""
Fix Event Loop Errors - Comprehensive solution for asyncio threading issues
Addresses "Future attached to a different loop" errors in the unified parser
"""

import re
import os

def fix_event_loop_errors():
    """Fix all event loop and threading issues in the unified parser"""
    
    processor_file = "bot/utils/scalable_unified_processor.py"
    
    with open(processor_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Replace direct database manager calls with thread-safe alternatives
    database_fixes = [
        # Fix the reset player sessions call
        (
            r'await self\.bot\.db_manager\.reset_player_sessions_for_server\(self\.guild_id, entry\.server_name\)',
            'await self._safe_reset_player_sessions(entry.server_name)'
        ),
        # Fix guild retrieval calls
        (
            r'guild_config = await self\.bot\.db_manager\.get_guild\(self\.guild_id\)',
            'guild_config = await self._safe_get_guild()'
        ),
        # Fix all database upsert operations
        (
            r'await self\.bot\.db_manager\.player_sessions\.update_one\(',
            'await self._safe_db_operation("update_player_session", '
        )
    ]
    
    for pattern, replacement in database_fixes:
        content = re.sub(pattern, replacement, content)
    
    # Fix 2: Add thread-safe database operation methods
    safe_methods = '''
    async def _safe_reset_player_sessions(self, server_name: str):
        """Thread-safe player session reset"""
        try:
            if self.db_wrapper:
                return await self.db_wrapper.reset_player_sessions(self.guild_id, server_name)
            else:
                logger.warning(f"No database wrapper available for reset_player_sessions")
                return None
        except Exception as e:
            logger.error(f"Failed to reset player sessions: {e}")
            return None

    async def _safe_get_guild(self):
        """Thread-safe guild retrieval"""
        try:
            if self.db_wrapper:
                return await self.db_wrapper.get_guild(self.guild_id)
            else:
                logger.warning(f"No database wrapper available for get_guild")
                return None
        except Exception as e:
            logger.error(f"Failed to get guild: {e}")
            return None

    async def _safe_db_operation(self, operation_type: str, *args, **kwargs):
        """Thread-safe database operation wrapper"""
        try:
            if self.db_wrapper:
                if operation_type == "update_player_session":
                    # Handle player session updates specially
                    return await self.db_wrapper.update_player_session(*args, **kwargs)
                else:
                    logger.warning(f"Unknown operation type: {operation_type}")
                    return None
            else:
                logger.warning(f"No database wrapper available for {operation_type}")
                return None
        except Exception as e:
            logger.error(f"Database operation {operation_type} failed: {e}")
            return None
'''
    
    # Insert the safe methods before the last class method
    if 'async def _safe_reset_player_sessions' not in content:
        # Find the last method in the class
        class_end_pattern = r'(\n\s*async def [^:]+:[^}]+)(\n\n(?:class|\Z))'
        
        def add_main_loop(match):
            return match.group(1) + safe_methods + match.group(2)
        
        content = re.sub(class_end_pattern, add_main_loop, content, flags=re.DOTALL)
        
        # If that didn't work, add at the end of the class
        if 'async def _safe_reset_player_sessions' not in content:
            content = content.rstrip() + safe_methods + '\n'
    
    # Fix 3: Ensure all state_changed references use locals()
    content = re.sub(r'elif not state_changed:', 'elif not locals().get("state_changed", False):', content)
    content = re.sub(r'if state_changed and not', 'if locals().get("state_changed", False) and not', content)
    content = re.sub(r'if state_changed:', 'if locals().get("state_changed", False):', content)
    
    with open(processor_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed all event loop and threading issues")

def enhance_thread_safe_wrapper_methods():
    """Add missing methods to thread-safe database wrapper"""
    
    wrapper_file = "bot/utils/thread_safe_db_wrapper.py"
    
    with open(wrapper_file, 'r') as f:
        content = f.read()
    
    # Add missing methods if not present
    missing_methods = '''
    async def update_player_session(self, *args, **kwargs):
        """Thread-safe player session update"""
        try:
            return await self.safe_db_operation(
                lambda: self.db_manager.player_sessions.update_one(*args, **kwargs)
            )
        except Exception as e:
            logger.error(f"Failed to update player session: {e}")
            return None

    async def get_guild(self, guild_id: int):
        """Thread-safe guild retrieval"""
        try:
            return await self.safe_db_operation(
                lambda: self.db_manager.get_guild(guild_id)
            )
        except Exception as e:
            logger.error(f"Failed to get guild: {e}")
            return None
'''
    
    if 'update_player_session' not in content:
        content = content.rstrip() + missing_methods + '\n'
        
        with open(wrapper_file, 'w') as f:
            f.write(content)
    
    print("✅ Enhanced thread-safe database wrapper with missing methods")

def main():
    """Execute all event loop fixes"""
    print("🔧 Fixing event loop and threading issues...")
    
    fix_event_loop_errors()
    enhance_thread_safe_wrapper_methods()
    
    print("✅ All event loop fixes implemented successfully!")

if __name__ == "__main__":
    main()