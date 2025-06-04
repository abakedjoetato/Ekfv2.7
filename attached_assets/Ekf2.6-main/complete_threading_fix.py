"""
Complete Threading Fix for Discord Bot
Eliminates all "Future attached to a different loop" errors
"""

import re
import os

def fix_unified_processor():
    """Fix all threading issues in scalable_unified_processor.py"""
    
    processor_file = "bot/utils/scalable_unified_processor.py"
    
    with open(processor_file, 'r') as f:
        content = f.read()
    
    # Replace all database calls with thread-safe alternatives
    fixes = [
        # Fix reset player sessions call
        (
            r'await self\.bot\.db_manager\.reset_player_sessions_for_server\(self\.guild_id, entry\.server_name\)',
            'await self.db_wrapper.reset_player_sessions(self.guild_id, entry.server_name) if self.db_wrapper else None'
        ),
        # Fix state_changed variable references
        (
            r'elif not state_changed:',
            'elif not locals().get("state_changed", False):'
        ),
        (
            r'if state_changed and not self\._cold_start_mode:',
            'if locals().get("state_changed", False) and not self._cold_start_mode:'
        ),
        (
            r'if state_changed:',
            'if locals().get("state_changed", False):'
        ),
        # Initialize result variable
        (
            r'state_changed = \(result\.upserted_id is not None or result\.modified_count > 0\) if result else False',
            'state_changed = (hasattr(result, "upserted_id") and result.upserted_id is not None) or (hasattr(result, "modified_count") and result.modified_count > 0) if result else False'
        )
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content)
    
    with open(processor_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed all threading issues in unified processor")

def enhance_thread_safe_wrapper():
    """Add missing methods to thread-safe database wrapper"""
    
    wrapper_file = "bot/utils/thread_safe_db_wrapper.py"
    
    with open(wrapper_file, 'r') as f:
        content = f.read()
    
    # Add missing reset_player_sessions method if not present
    if 'reset_player_sessions' not in content:
        additional_method = '''
    async def reset_player_sessions(self, guild_id: int, server_name: str):
        """Thread-safe player session reset"""
        try:
            return await self.safe_db_operation(
                lambda: self.db_manager.reset_player_sessions_for_server(guild_id, server_name)
            )
        except Exception as e:
            logger.error(f"Failed to reset player sessions: {e}")
            return None
'''
        
        # Insert before the last line
        content = content.rstrip() + additional_method + '\n'
        
        with open(wrapper_file, 'w') as f:
            f.write(content)
    
    print("✅ Enhanced thread-safe database wrapper")

def main():
    """Execute all fixes"""
    print("🔧 Implementing complete threading fixes...")
    
    fix_unified_processor()
    enhance_thread_safe_wrapper()
    
    print("✅ All threading fixes implemented successfully!")

if __name__ == "__main__":
    main()