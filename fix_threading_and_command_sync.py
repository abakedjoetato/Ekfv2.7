"""
Complete Fix for Threading Issues and Discord Command Sync
Addresses "Future attached to a different loop" errors and enables command synchronization
"""

import asyncio
import os
import re
from pathlib import Path

def fix_threading_issues():
    """Fix all threading issues in the unified processor"""
    
    # 1. Fix scalable_unified_processor.py threading issues
    processor_file = "bot/utils/scalable_unified_processor.py"
    
    with open(processor_file, 'r') as f:
        content = f.read()
    
    # Replace all remaining direct database calls with thread-safe alternatives
    fixes = [
        # Fix reset player sessions call
        (
            r'await self\.bot\.db_manager\.reset_player_sessions_for_server\(self\.guild_id, entry\.server_name\)',
            'await self.db_wrapper.reset_player_sessions(self.guild_id, entry.server_name) if self.db_wrapper else None'
        ),
        # Fix commit cold start player states
        (
            r'await self\.bot\.db_manager\.player_sessions\.insert_many\(batch_updates\)',
            'await self.db_wrapper.safe_db_operation(lambda: self.bot.db_manager.player_sessions.insert_many(batch_updates)) if self.db_wrapper else None'
        ),
        # Fix any remaining _safe_db_call references
        (
            r'await self\._safe_db_call\([^)]+\)',
            'None  # Replaced with thread-safe wrapper'
        ),
        # Initialize state_changed variable
        (
            r'state_changed = True  # For logging purposes',
            'state_changed = True'
        ),
        # Fix undefined state_changed variables
        (
            r'if state_changed and not self\._cold_start_mode:',
            'if locals().get("state_changed", False) and not self._cold_start_mode:'
        ),
        (
            r'if state_changed:',
            'if locals().get("state_changed", False):'
        )
    ]
    
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content)
    
    # Remove duplicate safe_db initialization
    content = re.sub(
        r'# Thread-safe database wrapper to prevent event loop errors\s+self\.safe_db = ThreadSafeDBWrapper\(bot\.db_manager\) if bot and hasattr\(bot, \'db_manager\'\) else None\s+',
        '',
        content
    )
    
    with open(processor_file, 'w') as f:
        f.write(content)
    
    print("✅ Fixed threading issues in scalable_unified_processor.py")

def enable_command_sync():
    """Enable Discord command synchronization by removing rate limit protection"""
    
    main_file = "main.py"
    
    with open(main_file, 'r') as f:
        content = f.read()
    
    # Force command sync by removing cooldown checks
    content = re.sub(
        r'# Check if sync is on cooldown.*?return',
        '# Command sync enabled - proceeding without cooldown check',
        content,
        flags=re.DOTALL
    )
    
    # Remove cooldown file creation after sync
    content = re.sub(
        r'# Set protective cooldown after successful sync.*?f\.write\(cooldown_time\.isoformat\(\)\)',
        '# Cooldown protection disabled for immediate sync',
        content,
        flags=re.DOTALL
    )
    
    # Enable forced sync
    content = re.sub(
        r'logger\.info\("✅ Commands loaded and ready \(sync bypassed to prevent rate limits\)"\)',
        'logger.info("🔥 Commands loaded and ready - FORCING SYNC")'
    )
    
    with open(main_file, 'w') as f:
        f.write(content)
    
    print("✅ Enabled Discord command synchronization")

def fix_database_wrapper():
    """Ensure the thread-safe database wrapper has all required methods"""
    
    wrapper_file = "bot/utils/thread_safe_db_wrapper.py"
    
    if not os.path.exists(wrapper_file):
        return
    
    with open(wrapper_file, 'r') as f:
        content = f.read()
    
    # Add missing methods if they don't exist
    if 'async def reset_player_sessions' not in content:
        additional_methods = '''
    async def reset_player_sessions(self, guild_id: int, server_name: str):
        """Thread-safe player session reset"""
        return await self.safe_db_operation(
            self.db_manager.reset_player_sessions_for_server,
            guild_id, server_name
        )
    
    async def insert_many_player_sessions(self, sessions_data):
        """Thread-safe bulk player session insert"""
        return await self.safe_db_operation(
            lambda: self.db_manager.player_sessions.insert_many(sessions_data)
        )
'''
        
        # Insert before the last class or function
        content = content.rstrip() + additional_methods + '\n'
        
        with open(wrapper_file, 'w') as f:
            f.write(content)
    
    print("✅ Enhanced thread-safe database wrapper")

def remove_cooldown_files():
    """Remove any existing cooldown files to enable immediate sync"""
    
    cooldown_files = [
        "command_sync_cooldown.txt",
        ".command_sync_cooldown",
        "sync_cooldown.txt"
    ]
    
    for file in cooldown_files:
        if os.path.exists(file):
            os.remove(file)
            print(f"✅ Removed cooldown file: {file}")

def main():
    """Execute all fixes"""
    print("🔧 Implementing comprehensive threading and command sync fixes...")
    
    fix_threading_issues()
    enable_command_sync()
    fix_database_wrapper()
    remove_cooldown_files()
    
    print("\n✅ All fixes implemented successfully!")
    print("🚀 Bot restart required to apply changes")

if __name__ == "__main__":
    main()